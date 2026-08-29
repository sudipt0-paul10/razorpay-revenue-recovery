"""Day 6 Stage 6C-1 / 6C-7: every A3-LLM-specific §14 ledger field is
correctly populated through the real runner, and A3-D's own path
continues to produce null/0.0 for all of them, exactly as before.

6C-1's audit trace (reported in the Stage 6C deliverable): before this
stage, prompt_hash/raw_output/latency_ms/tokens_in/tokens_out/
model_version/template_version were hardcoded None and cost was
hardcoded 0.0 in rrx.agent.ledger.default_ledger_record, regardless of
caller. Fixed by threading rrx.agent.planner.PlannerOutcome's own fields
through rrx.agent.planner.A3LLMPolicy's last_* attributes and
src/rrx/harness/runner.py's existing getattr(policy, ...) mechanism
(the same one Stage 6B's closure patch already used for fallback_reason)
into default_ledger_record's now-extended (but not reshaped -
LedgerRecord's 22 fields are unchanged) keyword arguments.
"""

from __future__ import annotations

import json

from rrx.agent.ledger import LedgerRecord, default_ledger_record
from rrx.agent.planner import StubLLMClient, make_a3_llm_policy
from rrx.agent.policy import a3d_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Confirmed by direct cohort inspection: opens payment_risk_check_failed,
# reused across the closure/6C test files for a consistent, deterministic
# fixture episode.
RISK_FLAGGED_DEV_INDEX = 1068

STUB_TOKENS_IN = 4321       # explicitly fake, never a real tokenizer count
STUB_TOKENS_OUT = 17        # explicitly fake
STUB_COST_INR = 0.0042      # explicitly a stub/test value - see module docstring
STUB_MODEL = "stub-model-6c-not-a-real-provider"


def _capturing_ledger():
    records: list[LedgerRecord] = []

    def _record(**kwargs):
        rec = default_ledger_record(**kwargs)
        records.append(rec)
        return rec

    return records, _record


def _valid_stop_for_risk_flagged() -> str:
    return json.dumps(
        {
            "action_type": "STOP",
            "remedy": None,
            "reason_code": "risk_flagged",
            "rationale": "escalating",
        }
    )


def _run(policy) -> list[LedgerRecord]:
    records, capturing_ledger = _capturing_ledger()
    run_episode_a3(
        DEV_SPLIT, RISK_FLAGGED_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )
    return [r for r in records if r.tick_type == "wakeup"]


# ---------------------------------------------------------------------------
# A3-LLM: every field populated, from an explicitly-marked stub source.
# ---------------------------------------------------------------------------

def test_successful_llm_call_populates_every_llm_only_ledger_field():
    client = StubLLMClient(
        response=_valid_stop_for_risk_flagged(),
        tokens_in=STUB_TOKENS_IN, tokens_out=STUB_TOKENS_OUT, cost_inr=STUB_COST_INR,
    )
    policy = make_a3_llm_policy(
        client=client, model=STUB_MODEL, temperature=0.0, allow_live=True,
    )
    wakeups = _run(policy)
    assert wakeups
    rec = wakeups[0]

    assert rec.prompt_hash is not None and len(rec.prompt_hash) == 64  # sha256 hexdigest
    assert rec.raw_output == _valid_stop_for_risk_flagged()
    assert rec.latency_ms is not None and rec.latency_ms >= 0.0
    assert rec.tokens_in == STUB_TOKENS_IN
    assert rec.tokens_out == STUB_TOKENS_OUT
    assert rec.cost == STUB_COST_INR
    assert rec.model_version == STUB_MODEL
    assert rec.template_version is not None
    assert rec.fallback_reason is None


def test_gate_rejected_fallback_still_populates_the_original_llm_call_metadata():
    """The metadata describes the ORIGINAL LLM call attempt (what was
    proposed and what it would have cost/taken), not the a3d_policy
    fallback that actually executed - preserving the same
    proposed-vs-executed distinction 6C-6/6C-9 require for
    parsed_action/executed_action, extended to the audit metadata."""
    hallucinated = json.dumps(
        {
            "action_type": "CONTACT", "remedy": "card_change",
            "reason_code": "risk_flagged", "rationale": "hallucinated",
        }
    )
    client = StubLLMClient(
        response=hallucinated,
        tokens_in=STUB_TOKENS_IN, tokens_out=STUB_TOKENS_OUT, cost_inr=STUB_COST_INR,
    )
    policy = make_a3_llm_policy(client=client, model=STUB_MODEL, temperature=0.0, allow_live=True)
    wakeups = _run(policy)
    assert wakeups
    rec = wakeups[0]

    assert rec.fallback_reason == "gate_rejected"
    assert rec.raw_output == hallucinated  # the rejected attempt, preserved
    assert rec.tokens_in == STUB_TOKENS_IN
    assert rec.tokens_out == STUB_TOKENS_OUT
    assert rec.cost == STUB_COST_INR
    assert rec.executed_action == {"action_type": "STOP"}  # A3-D's fallback, not CONTACT


def test_timeout_fallback_has_no_response_metadata_but_has_latency():
    """No raw_output/tokens/cost - nothing came back. latency_ms is still
    populated: it measures how long the call took before failing, which
    is real, measured elapsed time, not fabricated."""
    from rrx.agent.planner import PlannerTimeoutError

    client = StubLLMClient(raises=PlannerTimeoutError("forced"))
    policy = make_a3_llm_policy(client=client, model=STUB_MODEL, temperature=0.0, allow_live=True)
    wakeups = _run(policy)
    assert wakeups
    rec = wakeups[0]

    assert rec.fallback_reason == "timeout"
    assert rec.raw_output is None
    assert rec.tokens_in is None
    assert rec.tokens_out is None
    assert rec.cost == 0.0
    assert rec.latency_ms is not None and rec.latency_ms >= 0.0
    assert rec.prompt_hash is not None  # the prompt WAS built and hashed before the call


def test_cache_hit_reports_zero_cost_and_no_live_call_metadata():
    """No live call happened in THIS execution - nothing was spent or
    measured by it (see rrx.agent.planner.invoke_planner's accounting-note
    docstring)."""
    from rrx.agent.llm_cache import CacheKey, LLMCache, compute_prompt_hash
    from rrx.agent.prompt import TEMPLATE_VERSION, render_prompt
    from rrx.features.episode_view import EpisodeView

    view = EpisodeView(
        subscription_id="dev-1068", subscription_state="pending", invoice_amount_inr=1,
        days_since_first_failure=0, auto_retries_remaining=1, next_auto_retry_day=1,
        decline_code="payment_risk_check_failed", billing_amount_inr=1,
        contact_history=(), budget_remaining=3,
    )
    raw = _valid_stop_for_risk_flagged()
    key = CacheKey(
        template_version=TEMPLATE_VERSION, model=STUB_MODEL, temperature=0.0,
        prompt_hash=compute_prompt_hash(render_prompt(view, template_version=TEMPLATE_VERSION)),
    )
    cache = LLMCache()
    cache.put(key, raw)

    poison = StubLLMClient(response="SHOULD NOT BE CALLED", tokens_in=99999, cost_inr=99.0)
    policy = make_a3_llm_policy(
        client=poison, model=STUB_MODEL, temperature=0.0, cache=cache, allow_live=False,
    )
    proposal = policy(view)
    assert proposal.action_type == "STOP"
    assert policy.last_tokens_in is None
    assert policy.last_cost_inr == 0.0
    assert policy.last_latency_ms is None


# ---------------------------------------------------------------------------
# A3-D: every LLM-only field stays null/0.0, exactly as before Stage 6C.
# ---------------------------------------------------------------------------

def test_a3d_ledger_fields_stay_null_and_zero_over_full_dev():
    records, capturing_ledger = _capturing_ledger()
    for i in DEV_INDICES:
        run_episode_a3(DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG,
                        ledger_record=capturing_ledger)

    for rec in records:
        assert rec.prompt_hash is None
        assert rec.raw_output is None
        assert rec.latency_ms is None
        assert rec.tokens_in is None
        assert rec.tokens_out is None
        assert rec.cost == 0.0
        assert rec.model_version is None
        assert rec.template_version is None
        assert rec.fallback_reason is None


def test_ledger_record_schema_still_has_exactly_22_fields():
    """No LedgerRecord field was added, renamed, or removed by this
    stage - only the wiring that populates the existing ones changed."""
    import dataclasses

    assert len(dataclasses.fields(LedgerRecord)) == 22
