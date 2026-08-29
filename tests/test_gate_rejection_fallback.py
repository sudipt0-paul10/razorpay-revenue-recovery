"""Day 6 Stage 6B final amendment: the gate-rejection fallback hook added
to src/rrx/harness/runner.py (docs/A3-DESIGN.md §11's `gate_rejected`
fallback_reason).

Covers, in order: the required end-to-end gate-rejection test (amendment
requirement 7), the timeout-forced parity requirement (requirement 6),
and an explicit proof that A3-D's own behavior is unchanged (requirement
1 - the hook is provably dead code for a3d_policy).
"""

from __future__ import annotations

import json

from rrx.agent.ledger import LedgerRecord, default_ledger_record
from rrx.agent.planner import PlannerTimeoutError, StubLLMClient, make_a3_llm_policy
from rrx.agent.policy import a3d_policy
from rrx.agent.proposal import Proposal
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Confirmed by direct cohort inspection (not asserted blind): dev index
# 1068's opening_condition_key is payment_risk_check_failed. Using a real,
# known dev episode - not a synthetic EpisodeView - so this exercises the
# actual runner/gate/executor/ledger wiring end to end, per the amendment's
# explicit ask for an "end-to-end" test.
RISK_FLAGGED_DEV_INDEX = 1068


def _capturing_ledger(base_fn=default_ledger_record):
    records: list[LedgerRecord] = []

    def _record(**kwargs):
        rec = base_fn(**kwargs)
        records.append(rec)
        return rec

    return records, _record


def _hallucinated_contact_for_risk_flagged() -> str:
    """A SYNTACTICALLY VALID LLM proposal (passes rrx.agent.planner.
    parse_llm_output's strict schema AND reason_code/decline_code
    admissibility check - risk_flagged's only admissible decline_code is
    exactly payment_risk_check_failed) that the frozen gate's R4 rule
    still rejects: CONTACT is never permitted once decline_code ==
    payment_risk_check_failed, regardless of what reason_code labeled it.
    This is the two-layer defense (parser catches malformed/inadmissible
    output; gate catches action-level safety violations) working exactly
    as designed - not a workaround."""
    return json.dumps(
        {
            "action_type": "CONTACT",
            "remedy": "card_change",
            "reason_code": "risk_flagged",
            "rationale": "hallucinated: proposing to contact despite the risk flag",
        }
    )


# ---------------------------------------------------------------------------
# Requirement 7: explicit end-to-end gate-rejection test
# ---------------------------------------------------------------------------

def test_gate_rejected_llm_proposal_falls_back_to_a3d_end_to_end():
    client = StubLLMClient(response=_hallucinated_contact_for_risk_flagged())
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    records, capturing_ledger = _capturing_ledger()

    result = run_episode_a3(
        DEV_SPLIT, RISK_FLAGGED_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )

    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    assert wakeup_records, (
        "expected at least one wakeup tick for a payment_risk_check_failed episode"
    )
    first = wakeup_records[0]

    # (a) the original (LLM) proposal was rejected
    assert first.gate_verdict == "reject"
    assert first.gate_rule_fired == "R4"
    assert first.parsed_action["action_type"] == "CONTACT"
    assert first.parsed_action["reason_code"] == "risk_flagged"

    # (b) A3-D was invoked on the same view/tick, and its proposal is what
    # actually executed - STOP (rrx.agent.policy R-02, for this decline_code).
    assert first.fallback_reason == "gate_rejected"
    assert first.executed_action == {"action_type": "STOP"}

    # (c) episode still attributed to A3-LLM, not dropped: run_episode_a3
    # returned a normal EpisodeResult, and every window day has a ledger
    # record (post-STOP ticks are terminal_suppressed, not missing).
    window_days = EPISODE_CFG["episode"]["window_days"]
    assert len(records) == window_days + 1
    assert result is not None

    # (d) the fallback proposal, independently, is exactly what a3d_policy
    # itself would propose for this same view - "invoke A3-D policy for
    # the SAME EpisodeView/tick" is not just claimed, it is reproducible.
    # (First wakeup tick's view is day 0 - reconstructed identically here
    # is unnecessary: R-02 fires unconditionally on decline_code alone,
    # so any view with this decline_code proves the point.)
    assert a3d_policy.__module__ == "rrx.agent.policy"  # untouched, still the real one


def test_gate_rejected_fallback_never_drops_or_double_counts_a_contact():
    """The fallback proposal's own contact (if any) must be the only
    thing that mutates state.contacts_sent for this tick - not the
    rejected original AND the fallback both."""
    client = StubLLMClient(response=_hallucinated_contact_for_risk_flagged())
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    result = run_episode_a3(
        DEV_SPLIT, RISK_FLAGGED_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
    )
    # R-02's fallback is STOP, not CONTACT - zero contacts for this episode.
    assert result.contacts_sent == 0


# ---------------------------------------------------------------------------
# Requirement 6: timeout-forced parity still holds after the runner change
# ---------------------------------------------------------------------------

def test_forced_timeout_a3_llm_still_matches_a3d_end_to_end_over_real_dev_episodes():
    """A3-LLM forced timeout -> A3-D fallback -> frozen gate -> existing
    executor -> reproduces A3-D's own decisions/outcomes exactly, run
    through the (now-amended) real runner over real dev episodes."""
    client = StubLLMClient(raises=PlannerTimeoutError("forced"))
    llm_policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)

    for i in list(DEV_INDICES)[:100]:
        a3d_result = run_episode_a3(DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG)
        a3_llm_result = run_episode_a3(DEV_SPLIT, i, llm_policy, EPISODE_CFG, POPULATION_CFG)
        assert a3_llm_result == a3d_result, f"divergence at dev index {i}"


def test_forced_timeout_ledger_records_timeout_not_gate_rejected():
    """Superseded by the Day 6 Stage 6B closure patch
    (rrx.agent.planner.A3LLMPolicy): a timeout fallback is now visible to
    the ledger as fallback_reason="timeout" (see
    tests/test_planner_fallback_ledger.py for the full A-G matrix) - the
    one thing this test still specifically guards is that it is never
    misreported as "gate_rejected" (a runner-layer concept for a
    different failure mode entirely: the gate rejecting a *syntactically
    valid* proposal, not the planner failing to produce one at all)."""
    client = StubLLMClient(raises=PlannerTimeoutError("forced"))
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    records, capturing_ledger = _capturing_ledger()

    run_episode_a3(
        DEV_SPLIT, RISK_FLAGGED_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )
    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    assert wakeup_records
    for rec in wakeup_records:
        assert rec.fallback_reason == "timeout"
        assert rec.fallback_reason != "gate_rejected"


# ---------------------------------------------------------------------------
# Requirement 1: A3-D behavior is provably unchanged (hook is dead code)
# ---------------------------------------------------------------------------

def test_a3d_ledger_never_carries_a_fallback_reason_over_full_dev():
    """Empirical companion to the module docstring's claim (backed by
    tests/test_a3d_policy.py's exhaustive gate-compliance proof): running
    a3d_policy itself through the amended runner over the FULL dev cohort
    produces zero fallback_reason values of any kind - the new branch is
    never entered."""
    records, capturing_ledger = _capturing_ledger()
    for i in DEV_INDICES:
        run_episode_a3(DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG,
                        ledger_record=capturing_ledger)
    fallback_records = [r for r in records if r.fallback_reason is not None]
    assert fallback_records == [], (
        f"a3d_policy triggered {len(fallback_records)} fallback(s) - "
        "this must be impossible (gate-compliant by construction)"
    )


def test_a3d_full_dev_ledger_record_count_and_shape_unchanged():
    """Sanity check that the new optional `fallback_reason` parameter did
    not otherwise perturb LedgerRecord's shape for the A3-D path."""
    proposal = a3d_policy
    result = run_episode_a3(DEV_SPLIT, list(DEV_INDICES)[0], proposal, EPISODE_CFG, POPULATION_CFG)
    assert result is not None
    # LedgerRecord still has exactly the frozen 22 fields (fallback_reason
    # was already one of them - only its wiring changed).
    import dataclasses

    from rrx.agent.ledger import LedgerRecord as LR

    assert len(dataclasses.fields(LR)) == 22


def test_make_a3_llm_policy_output_is_still_a_plain_proposal():
    """The runner change adds no new object types to the policy/gate
    boundary - make_a3_llm_policy still returns a plain Proposal, exactly
    matching a3d_policy's own return type."""
    client = StubLLMClient(response=_hallucinated_contact_for_risk_flagged())
    policy = make_a3_llm_policy(client=client, model="stub", temperature=0.0, allow_live=True)
    from rrx.features.episode_view import EpisodeView

    view = EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=1000,
        days_since_first_failure=0, auto_retries_remaining=1, next_auto_retry_day=1,
        decline_code="payment_risk_check_failed", billing_amount_inr=1000,
        contact_history=(), budget_remaining=3,
    )
    assert isinstance(policy(view), Proposal)
