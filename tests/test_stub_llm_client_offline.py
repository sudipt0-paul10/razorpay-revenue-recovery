"""Day 6 Stage 6C-2: the offline StubLLMClient's five required behaviors
(A-E), and an explicit proof it never performs network I/O.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from rrx.agent.gate import evaluate_gate
from rrx.agent.planner import (
    ParseFailure,
    PlannerTimeoutError,
    StubLLMClient,
    invoke_planner,
    parse_llm_output,
)
from rrx.agent.policy import a3d_policy
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView

SRC = Path(__file__).resolve().parents[1] / "src"


def _view(
    *, decline_code: str = "card_expired", subscription_state: str = "pending"
) -> EpisodeView:
    return EpisodeView(
        subscription_id="dev-1000",
        subscription_state=subscription_state,
        invoice_amount_inr=50000,
        days_since_first_failure=0,
        auto_retries_remaining=1,
        next_auto_retry_day=1,
        decline_code=decline_code,
        billing_amount_inr=50000,
        contact_history=(),
        budget_remaining=3,
    )


def _valid_json(**overrides) -> str:
    obj = {
        "action_type": "CONTACT",
        "remedy": "card_change",
        "reason_code": "remedy_match_card",
        "rationale": "card is broken",
    }
    obj.update(overrides)
    return json.dumps(obj)


# --- A. valid LLM proposal ---------------------------------------------------

def test_a_valid_llm_proposal():
    client = StubLLMClient(response=_valid_json())
    raw = client.complete("prompt text", model="stub", temperature=0.0)
    result = parse_llm_output(raw, _view())
    assert isinstance(result, Proposal)


# --- B. malformed JSON --------------------------------------------------------

def test_b_malformed_json():
    client = StubLLMClient(response="{not valid json")
    raw = client.complete("prompt text", model="stub", temperature=0.0)
    result = parse_llm_output(raw, _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "unparseable"


# --- C. schema-invalid JSON ---------------------------------------------------

def test_c_schema_invalid_json():
    client = StubLLMClient(response=_valid_json(action_type="RETRY"))
    raw = client.complete("prompt text", model="stub", temperature=0.0)
    result = parse_llm_output(raw, _view())
    assert isinstance(result, ParseFailure)
    assert result.fallback_reason == "schema_violation"


# --- D. timeout/failure -------------------------------------------------------

def test_d_timeout_failure():
    client = StubLLMClient(raises=PlannerTimeoutError("simulated"))
    with pytest.raises(PlannerTimeoutError):
        client.complete("prompt text", model="stub", temperature=0.0)

    # Through the planner, this resolves to A3-D's fallback, not a raised
    # exception - the exception is the CLIENT's contract, not the planner's.
    view = _view()
    outcome = invoke_planner(view, client=client, model="stub", temperature=0.0, allow_live=True)
    assert outcome.fallback_reason == "timeout"
    assert outcome.proposal == a3d_policy(view)


# --- E. syntactically valid but gate-rejected proposal -----------------------

def test_e_syntactically_valid_but_gate_rejected():
    view = _view(decline_code="payment_risk_check_failed")
    client = StubLLMClient(
        response=_valid_json(reason_code="risk_flagged")  # admissible, but CONTACT is R4-forbidden
    )
    raw = client.complete("prompt text", model="stub", temperature=0.0)
    result = parse_llm_output(raw, view)
    assert isinstance(result, Proposal), "must be syntactically VALID to test gate rejection"
    verdict = evaluate_gate(result, view)
    assert not verdict.accepted
    assert verdict.rule_fired == "R4"


# --- No network I/O ------------------------------------------------------------

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


def test_stub_client_source_imports_no_networking_library():
    path = SRC / "rrx" / "agent" / "planner.py"
    imported = _imported_modules(path)
    bad = sorted(
        m for m in imported
        for forbidden in _FORBIDDEN_NETWORK_MODULES
        if m == forbidden or m.startswith(forbidden + ".")
    )
    assert not bad, f"planner.py (StubLLMClient's home module) imports: {bad}"


def test_stub_client_complete_is_a_pure_in_process_call():
    """A stronger, behavioral proof than the import scan: 1000 calls to
    the stub complete synchronously with no observable I/O latency
    pattern (network calls, even fast ones, do not resolve in
    microseconds in a tight loop the way an in-process function call
    does) - this is a sanity check on "never network", not a strict
    timing assertion."""
    import time

    client = StubLLMClient(response=_valid_json())
    start = time.monotonic()
    for _ in range(1000):
        client.complete("x", model="stub", temperature=0.0)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, (
        f"1000 stub calls took {elapsed:.3f}s - too slow for a pure in-process "
        "call, investigate for accidental I/O"
    )
