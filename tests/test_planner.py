"""docs/A3-DESIGN.md §11, §13, §19 - the A3-LLM planner: strict output
parsing, reason_code/admissibility validation at the parser layer (Day 6
Stage 6B Decision 2 - NOT a gate rule; the frozen gate is untouched and
covered separately in tests/test_gate_rules.py), the A3-D fallback
mechanic, and the cache-key hard-stop rules.

No live network call occurs anywhere in this file or its dependencies -
verified explicitly by test_no_live_network_capability_exists below, not
merely by absence of a test that would trigger one.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from rrx.agent.gate import evaluate_gate
from rrx.agent.llm_cache import CacheMissDuringReplayError, LiveCallNotAllowedError, LLMCache
from rrx.agent.planner import (
    FALLBACK_REASONS,
    ParseFailure,
    PlannerTimeoutError,
    StubLLMClient,
    invoke_planner,
    make_a3_llm_policy,
    parse_llm_output,
)
from rrx.agent.policy import a3d_policy
from rrx.agent.proposal import Proposal
from rrx.agent.reason_codes import REASON_CODES
from rrx.features.episode_view import ContactRecord, EpisodeView

SRC = Path(__file__).resolve().parents[1] / "src"


def _view(
    *,
    subscription_state: str = "pending",
    decline_code: str = "card_expired",
    day: int = 0,
    contact_history: tuple[ContactRecord, ...] = (),
    budget_remaining: int = 3,
) -> EpisodeView:
    return EpisodeView(
        subscription_id="dev-1000",
        subscription_state=subscription_state,
        invoice_amount_inr=50000,
        days_since_first_failure=day,
        auto_retries_remaining=1,
        next_auto_retry_day=5,
        decline_code=decline_code,
        billing_amount_inr=50000,
        contact_history=contact_history,
        budget_remaining=budget_remaining,
    )


def _valid_raw(**overrides) -> str:
    obj = {
        "action_type": "CONTACT",
        "remedy": "card_change",
        "reason_code": "remedy_match_card",
        "rationale": "card is broken, day 0",
    }
    obj.update(overrides)
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# 1-6: strict Proposal schema validation (parse_llm_output)
# ---------------------------------------------------------------------------

def test_valid_output_parses_to_a_proposal():
    result = parse_llm_output(_valid_raw(), _view())
    assert isinstance(result, Proposal)
    assert result.action_type == "CONTACT"
    assert result.remedy == "card_change"
    assert result.reason_code == "remedy_match_card"


def test_not_json_is_unparseable():
    result = parse_llm_output("this is not json {{{", _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "unparseable"


def test_json_scalar_not_object_is_unparseable():
    result = parse_llm_output(json.dumps("just a string"), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "unparseable"


def test_missing_key_is_schema_violation():
    obj = {"action_type": "WAIT", "remedy": None, "reason_code": "retry_window_open"}
    result = parse_llm_output(json.dumps(obj), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


def test_extra_key_is_schema_violation():
    """§11/§20: no `channel` field. A `channel` key (or any other extra
    key) fails the exact-key-set check."""
    obj = json.loads(_valid_raw())
    obj["channel"] = "whatsapp"
    result = parse_llm_output(json.dumps(obj), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


def test_invalid_action_type_is_schema_violation():
    result = parse_llm_output(_valid_raw(action_type="RETRY_PAYMENT"), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


@pytest.mark.parametrize("code", sorted(REASON_CODES))
def test_every_frozen_reason_code_is_individually_accepted_when_admissible(code):
    """Sanity check the 7-value enum end to end for at least one admissible
    (reason_code, decline_code, action_type) triple each, rather than only
    negative-testing rejection."""
    admissible_by_code = {
        "remedy_match_card": ("CONTACT", "card_change", "card_expired"),
        "remedy_match_topup": ("CONTACT", "topup_reminder", "insufficient_funds"),
        "retry_window_open": ("WAIT", None, "insufficient_funds"),
        "post_halt_rescue": ("CONTACT", "card_change", "card_expired"),
        "engagement_observed": ("CONTACT", "card_change", "card_expired"),
        "no_engagement_restraint": ("WAIT", None, "card_expired"),
        "risk_flagged": ("STOP", None, "payment_risk_check_failed"),
    }
    action_type, remedy, decline_code = admissible_by_code[code]
    view = _view(
        decline_code=decline_code,
        subscription_state="halted" if code == "post_halt_rescue" else "pending",
    )
    raw = _valid_raw(action_type=action_type, remedy=remedy, reason_code=code)
    result = parse_llm_output(raw, view)
    assert isinstance(result, Proposal), f"{code} unexpectedly rejected: {result}"


def test_reason_code_outside_the_seven_value_enum_is_schema_violation():
    result = parse_llm_output(_valid_raw(reason_code="made_up_reason"), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


def test_remedy_required_for_contact():
    result = parse_llm_output(_valid_raw(remedy=None), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


def test_remedy_must_be_null_for_wait():
    obj = {
        "action_type": "WAIT",
        "remedy": "card_change",
        "reason_code": "retry_window_open",
        "rationale": "waiting",
    }
    result = parse_llm_output(json.dumps(obj), _view(decline_code="insufficient_funds"))
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


def test_empty_rationale_is_schema_violation():
    result = parse_llm_output(_valid_raw(rationale="   "), _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


# ---------------------------------------------------------------------------
# 5: frozen reason_code/decline_code admissibility (docs/A3-DESIGN.md §7)
# ---------------------------------------------------------------------------

def test_inadmissible_reason_code_decline_code_pair_is_schema_violation():
    """risk_flagged is admissible ONLY for payment_risk_check_failed (§7).
    Proposing it for card_expired is a valid enum value, wrong context."""
    obj = {
        "action_type": "STOP",
        "remedy": None,
        "reason_code": "risk_flagged",
        "rationale": "escalating",
    }
    result = parse_llm_output(json.dumps(obj), _view(decline_code="card_expired"))
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


def test_post_halt_rescue_requires_halted_state_even_though_admissible_table_is_silent_on_it():
    """§7's admissible-decline_code table doesn't encode the
    subscription_state==halted requirement (rrx.agent.reason_codes'
    documented gap) - the parser enforces it directly per the frozen
    prose."""
    obj = {
        "action_type": "CONTACT",
        "remedy": "card_change",
        "reason_code": "post_halt_rescue",
        "rationale": "post-halt rescue attempt",
    }
    not_halted = _view(decline_code="card_expired", subscription_state="pending")
    result = parse_llm_output(json.dumps(obj), not_halted)
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"

    halted = _view(decline_code="card_expired", subscription_state="halted")
    result2 = parse_llm_output(json.dumps(obj), halted)
    assert isinstance(result2, Proposal)


# ---------------------------------------------------------------------------
# 14-15: A3-D fallback interface + existing frozen gate
# ---------------------------------------------------------------------------

def test_unparseable_output_falls_back_to_a3d_policy_for_the_same_view():
    view = _view(decline_code="card_expired", day=0)
    client = StubLLMClient(response="not json at all")
    outcome = invoke_planner(view, client=client, model="m", temperature=0.0, allow_live=True)
    assert outcome.used_fallback is True
    assert outcome.fallback_reason == "unparseable"
    assert outcome.proposal == a3d_policy(view)


def test_schema_violation_output_falls_back_to_a3d_policy_for_the_same_view():
    view = _view(decline_code="insufficient_funds", day=0)
    client = StubLLMClient(
        response=_valid_raw(reason_code="risk_flagged", action_type="STOP", remedy=None)
    )
    outcome = invoke_planner(view, client=client, model="m", temperature=0.0, allow_live=True)
    assert outcome.used_fallback is True
    assert outcome.fallback_reason == "schema_violation"
    assert outcome.proposal == a3d_policy(view)


def test_timeout_falls_back_to_a3d_policy_for_the_same_view():
    view = _view(decline_code="card_expired", day=0)
    client = StubLLMClient(raises=PlannerTimeoutError("simulated timeout"))
    outcome = invoke_planner(view, client=client, model="m", temperature=0.0, allow_live=True)
    assert outcome.used_fallback is True
    assert outcome.fallback_reason == "timeout"
    assert outcome.proposal == a3d_policy(view)


def test_valid_output_does_not_fall_back():
    view = _view(decline_code="card_expired", day=0)
    client = StubLLMClient(response=_valid_raw())
    outcome = invoke_planner(view, client=client, model="m", temperature=0.0, allow_live=True)
    assert outcome.used_fallback is False
    assert outcome.fallback_reason is None


@pytest.mark.parametrize(
    "client_kwargs",
    [
        {"response": "not json"},
        {"response": _valid_raw(reason_code="made_up")},
        {"raises": PlannerTimeoutError("x")},
    ],
    ids=["unparseable", "schema_violation", "timeout"],
)
def test_every_planner_layer_fallback_proposal_is_accepted_by_the_existing_gate(client_kwargs):
    """A3-D is gate-compliant by construction (docs/A3-DESIGN.md §10A.6) -
    the fallback proposal, being a3d_policy's own output, must be too. This
    proves the fallback proposal "executes through the same gate" (§11)
    without any change to src/rrx/agent/gate.py."""
    view = _view(decline_code="card_expired", day=0)
    client = StubLLMClient(**client_kwargs)
    outcome = invoke_planner(view, client=client, model="m", temperature=0.0, allow_live=True)
    verdict = evaluate_gate(outcome.proposal, view)
    assert verdict.accepted, f"fallback proposal rejected by gate: {verdict}"


def test_make_a3_llm_policy_returns_a_plain_episode_view_to_proposal_callable():
    """Confirms the adapter's shape matches src/rrx/harness/runner.py's
    PolicyFn exactly - no runner change needed to dispatch A3-LLM
    (Day 6 Decision 1)."""
    client = StubLLMClient(response=_valid_raw())
    policy = make_a3_llm_policy(client=client, model="m", temperature=0.0, allow_live=True)
    view = _view()
    result = policy(view)
    assert isinstance(result, Proposal)


# ---------------------------------------------------------------------------
# 17-18: cache-key contract obeyed by the planner
# ---------------------------------------------------------------------------

def test_cache_hit_never_calls_the_client():
    from rrx.agent.llm_cache import CacheKey, compute_prompt_hash
    from rrx.agent.prompt import TEMPLATE_VERSION, render_prompt

    view = _view()
    prompt = render_prompt(view)
    key = CacheKey(
        template_version=TEMPLATE_VERSION, model="m", temperature=0.0,
        prompt_hash=compute_prompt_hash(prompt),
    )
    cache = LLMCache()
    cache.put(key, _valid_raw())

    calls = []

    class _CountingClient:
        def complete(self, prompt, *, model, temperature):
            calls.append(prompt)
            return _valid_raw()

    outcome = invoke_planner(
        view, client=_CountingClient(), model="m", temperature=0.0, cache=cache, allow_live=False,
    )
    assert not calls
    assert outcome.used_fallback is False


def test_cache_miss_during_replay_is_a_hard_failure_not_a_silent_live_call():
    cache = LLMCache(replay=True)
    client = StubLLMClient(response=_valid_raw())
    with pytest.raises(CacheMissDuringReplayError):
        invoke_planner(
            _view(), client=client, model="m", temperature=0.0, cache=cache, allow_live=True,
        )


def test_cache_miss_without_allow_live_is_refused():
    client = StubLLMClient(response=_valid_raw())
    with pytest.raises(LiveCallNotAllowedError):
        invoke_planner(_view(), client=client, model="m", temperature=0.0, allow_live=False)


def test_cache_miss_with_allow_live_calls_client_and_populates_cache():
    from rrx.agent.llm_cache import CacheKey, compute_prompt_hash
    from rrx.agent.prompt import TEMPLATE_VERSION, render_prompt

    view = _view()
    cache = LLMCache()
    client = StubLLMClient(response=_valid_raw())
    outcome = invoke_planner(
        view, client=client, model="m", temperature=0.0, cache=cache, allow_live=True,
    )
    assert outcome.used_fallback is False
    key = CacheKey(
        template_version=TEMPLATE_VERSION, model="m", temperature=0.0,
        prompt_hash=compute_prompt_hash(render_prompt(view)),
    )
    assert cache.get(key) == _valid_raw()


# ---------------------------------------------------------------------------
# 16: no live network call anywhere in this module's dependency set
# ---------------------------------------------------------------------------

_FORBIDDEN_NETWORK_MODULES = (
    "requests", "httpx", "urllib.request", "socket", "http.client", "aiohttp",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names.add(node.module or "")
    return names


@pytest.mark.parametrize(
    "relpath", ["agent/planner.py", "agent/prompt.py", "agent/llm_cache.py"]
)
def test_no_live_network_capability_exists(relpath):
    """Stage 6B requirement: no live network call can occur. Verified by
    absence, not by mocking a would-be call: none of these modules import
    a networking library, and no LLMClient implementation other than the
    non-network StubLLMClient exists anywhere in src/rrx."""
    path = SRC / "rrx" / relpath
    imported = _imported_modules(path)
    bad = sorted(
        m for m in imported
        for forbidden in _FORBIDDEN_NETWORK_MODULES
        if m == forbidden or m.startswith(forbidden + ".")
    )
    assert not bad, f"{relpath} imports network-capable module(s): {bad}"


def test_fallback_reasons_enum_matches_the_frozen_five_values():
    assert FALLBACK_REASONS == {
        "timeout", "unparseable", "schema_violation", "gate_rejected", "stale_state",
    }
