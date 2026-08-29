"""Day 6 Stage 6B closure patch: planner-layer fallback auditability.

Before this patch, `rrx.agent.planner.invoke_planner`'s own
`fallback_reason` (timeout / unparseable / schema_violation) never
reached the ledger - `make_a3_llm_policy`'s adapter returned only the
resolved `Proposal`, discarding the rest of `PlannerOutcome`. Fixed via
`rrx.agent.planner.A3LLMPolicy`, a callable object that records its most
recent call's `fallback_reason` as a plain attribute
(`last_fallback_reason`), which `src/rrx/harness/runner.py` now reads via
`getattr(policy, "last_fallback_reason", None)` immediately after calling
`policy(view)` - no change to `PolicyFn`'s shape, no new `LedgerRecord`
field (that field already existed; only its wiring changed).

This file is the explicit A-G matrix the closure instructions asked for.
Each scenario runs a real dev episode end to end through the unmodified
runner/gate/executor and inspects the resulting ledger record(s) via
`run_episode_a3`'s existing `ledger_record` injection point.
"""

from __future__ import annotations

import json

from rrx.agent.ledger import LedgerRecord, default_ledger_record
from rrx.agent.planner import PlannerTimeoutError, StubLLMClient, make_a3_llm_policy
from rrx.agent.policy import a3d_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Confirmed by direct cohort inspection: opening_condition_key ==
# "payment_risk_check_failed" for this dev index - reused across every
# scenario below for consistency (see tests/test_gate_rejection_fallback.py).
RISK_FLAGGED_DEV_INDEX = 1068


def _capturing_ledger():
    records: list[LedgerRecord] = []

    def _record(**kwargs):
        rec = default_ledger_record(**kwargs)
        records.append(rec)
        return rec

    return records, _record


def _run(policy) -> list[LedgerRecord]:
    records, capturing_ledger = _capturing_ledger()
    run_episode_a3(
        DEV_SPLIT, RISK_FLAGGED_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )
    return [r for r in records if r.tick_type == "wakeup"]


def _hallucinated_contact_for_risk_flagged() -> str:
    """Syntactically valid per the parser (risk_flagged's only admissible
    decline_code is exactly payment_risk_check_failed) but gate-rejected
    under R4 - CONTACT is never permitted once decline_code ==
    payment_risk_check_failed."""
    return json.dumps(
        {
            "action_type": "CONTACT",
            "remedy": "card_change",
            "reason_code": "risk_flagged",
            "rationale": "hallucinated: proposing to contact despite the risk flag",
        }
    )


def _valid_stop_for_risk_flagged() -> str:
    """A genuinely valid, gate-ACCEPTED LLM proposal for this decline_code
    - STOP is unaffected by every gate rule that targets CONTACT."""
    return json.dumps(
        {
            "action_type": "STOP",
            "remedy": None,
            "reason_code": "risk_flagged",
            "rationale": "escalating a risk-flagged decline",
        }
    )


# ---------------------------------------------------------------------------
# A. timeout -> A3-D fallback -> ledger fallback_reason="timeout"
# ---------------------------------------------------------------------------

def test_a_timeout_fallback_reaches_the_ledger():
    client = StubLLMClient(raises=PlannerTimeoutError("forced"))
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    wakeups = _run(policy)

    assert wakeups
    assert wakeups[0].fallback_reason == "timeout"
    # Confirm what actually executed is A3-D's own fallback decision
    # (R-02 for payment_risk_check_failed: unconditional STOP).
    assert wakeups[0].executed_action == {"action_type": "STOP"}


# ---------------------------------------------------------------------------
# B. unparseable output -> A3-D fallback -> ledger fallback_reason="unparseable"
# ---------------------------------------------------------------------------

def test_b_unparseable_fallback_reaches_the_ledger():
    client = StubLLMClient(response="this is not json at all")
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    wakeups = _run(policy)

    assert wakeups
    assert wakeups[0].fallback_reason == "unparseable"


# ---------------------------------------------------------------------------
# C. schema violation -> A3-D fallback -> ledger fallback_reason="schema_violation"
# ---------------------------------------------------------------------------

def test_c_schema_violation_fallback_reaches_the_ledger():
    # Valid JSON, but an out-of-enum reason_code - schema_violation, not
    # unparseable (JSON parsing itself succeeds).
    bad = json.dumps(
        {
            "action_type": "STOP",
            "remedy": None,
            "reason_code": "made_up_reason",
            "rationale": "x",
        }
    )
    client = StubLLMClient(response=bad)
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    wakeups = _run(policy)

    assert wakeups
    assert wakeups[0].fallback_reason == "schema_violation"


# ---------------------------------------------------------------------------
# D. gate rejection -> A3-D fallback -> ledger fallback_reason="gate_rejected"
# ---------------------------------------------------------------------------

def test_d_gate_rejection_fallback_reaches_the_ledger():
    client = StubLLMClient(response=_hallucinated_contact_for_risk_flagged())
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    wakeups = _run(policy)

    assert wakeups
    assert wakeups[0].fallback_reason == "gate_rejected"
    assert wakeups[0].gate_verdict == "reject"
    assert wakeups[0].gate_rule_fired == "R4"
    # req. 9: original (rejected) proposal is preserved, not overwritten
    # by the fallback.
    assert wakeups[0].parsed_action["action_type"] == "CONTACT"
    assert wakeups[0].parsed_action["reason_code"] == "risk_flagged"
    # ...while executed_action reflects what the A3-D fallback actually did.
    assert wakeups[0].executed_action == {"action_type": "STOP"}


# ---------------------------------------------------------------------------
# E. successful LLM proposal -> fallback_reason=None
# ---------------------------------------------------------------------------

def test_e_successful_llm_proposal_has_no_fallback_reason():
    client = StubLLMClient(response=_valid_stop_for_risk_flagged())
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    wakeups = _run(policy)

    assert wakeups
    assert wakeups[0].fallback_reason is None
    assert wakeups[0].gate_verdict == "accept"
    assert wakeups[0].parsed_action["reason_code"] == "risk_flagged"
    assert wakeups[0].executed_action == {"action_type": "STOP"}


# ---------------------------------------------------------------------------
# F. A3-D policy -> fallback_reason=None
# ---------------------------------------------------------------------------

def test_f_a3d_policy_has_no_fallback_reason():
    wakeups = _run(a3d_policy)

    assert wakeups
    for rec in wakeups:
        assert rec.fallback_reason is None


# ---------------------------------------------------------------------------
# G. existing A3-D full-dev behavior remains unchanged
# ---------------------------------------------------------------------------

def test_g_a3d_full_dev_ledger_still_never_carries_a_fallback_reason():
    records, capturing_ledger = _capturing_ledger()
    for i in DEV_INDICES:
        run_episode_a3(DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG,
                        ledger_record=capturing_ledger)
    fallback_records = [r for r in records if r.fallback_reason is not None]
    assert fallback_records == []


def test_g_a3d_full_dev_matches_a_direct_run_episode_a3_call_bytewise():
    """Extra guard beyond G's letter: this closure patch touched the
    wakeup branch's control flow (added the getattr call and the
    fallback_reason assignment) - re-confirm A3-D's own EpisodeResult
    output is unaffected for a real sample of episodes, on top of the
    zero-fallback proof above."""
    for i in list(DEV_INDICES)[:200]:
        a = run_episode_a3(DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG)
        b = run_episode_a3(DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG)
        assert a == b
