"""EVAL.md §7.1 item E (eval-spec-v1.8): a gate-accepted proposal must
have a legal executor mapping. Before this invariant, an accepted
CONTACT with `remedy=None` or an unrecognized remedy fell through
`src/rrx/harness/runner.py`'s catch-all branch into ordinary
`{"action_type": "WAIT"}`, indistinguishable in the ledger from both a
genuine WAIT decision and a gate rejection.

This module proves the closed gap: such a proposal now produces a
distinct `fallback_reason` ("no_executor_mapping") and a distinct
`executed_action` ("ENFORCEMENT_FAILURE"), never conflated with either
of the two pre-existing outcomes, while leaving state/budget accounting
and episode continuity untouched - exactly as the amendment requires.

Dev index 1000's opening_condition_key is `debit_instrument_blocked`
(confirmed by direct cohort inspection, matching the style of
tests/test_gate_rejection_fallback.py's own RISK_FLAGGED_DEV_INDEX
comment) - a card-broken bucket, so R2 (terminal subscription state),
R3 (card_change forbidden for balance-only decline codes), R4 (risk
hard-stop) and R8 (unverified decline code) all pass at day 0, and the
gate has no other rule that inspects `remedy` - exactly the gap this
suite targets.
"""

from __future__ import annotations

from rrx.agent.gate import evaluate_gate
from rrx.agent.ledger import LedgerRecord, default_ledger_record
from rrx.agent.proposal import Proposal
from rrx.agent.reason_codes import REMEDY_MATCH_CARD, RISK_FLAGGED
from rrx.features.episode_view import EpisodeView
from rrx.harness.runner import (
    FALLBACK_NO_EXECUTOR_MAPPING,
    run_episode_a3,
)
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Confirmed by direct cohort inspection: dev index 1000's
# opening_condition_key is debit_instrument_blocked - a card-broken
# bucket, gate-safe for a CONTACT of any remedy at day 0.
CARD_BROKEN_DEV_INDEX = 1000

# Same risk-flagged index tests/test_gate_rejection_fallback.py already
# established, reused here for the rejection-path control case.
RISK_FLAGGED_DEV_INDEX = 1068


def _capturing_ledger(base_fn=default_ledger_record):
    records: list[LedgerRecord] = []

    def _record(**kwargs):
        rec = base_fn(**kwargs)
        records.append(rec)
        return rec

    return records, _record


def _unmapped_contact_policy(remedy: str | None):
    """A synthetic PolicyFn that always proposes an accepted-shape CONTACT
    with an illegal remedy - standing in for a policy that bypasses both
    a3d_policy's gate-compliance-by-construction and the A3-LLM parser's
    schema validation (neither of which this project's real callers can
    otherwise produce), so the enforcement-layer gap is exercised
    directly rather than left unreachable-and-untested."""

    def _policy(view: EpisodeView) -> Proposal:
        return Proposal(
            action_type="CONTACT",
            remedy=remedy,
            rationale="synthetic: exercising the executor-mapping gap",
            reason_code=REMEDY_MATCH_CARD,
        )

    return _policy


# ---------------------------------------------------------------------------
# Gate-level proof: neither case is rejected by R1-R8 (the gate is not the
# layer that catches this - the executor must be).
# ---------------------------------------------------------------------------


def test_gate_accepts_contact_with_remedy_none():
    view = EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=1000,
        days_since_first_failure=0, auto_retries_remaining=3, next_auto_retry_day=1,
        decline_code="debit_instrument_blocked", billing_amount_inr=1000,
        contact_history=(), budget_remaining=3,
    )
    proposal = Proposal(
        action_type="CONTACT", remedy=None, rationale="r", reason_code=REMEDY_MATCH_CARD,
    )
    verdict = evaluate_gate(proposal, view)
    assert verdict.accepted, "R3 only inspects remedy=='card_change' - remedy=None must pass"


def test_gate_accepts_contact_with_unrecognized_remedy():
    view = EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=1000,
        days_since_first_failure=0, auto_retries_remaining=3, next_auto_retry_day=1,
        decline_code="debit_instrument_blocked", billing_amount_inr=1000,
        contact_history=(), budget_remaining=3,
    )
    proposal = Proposal(
        action_type="CONTACT", remedy="not_a_real_remedy", rationale="r",
        reason_code=REMEDY_MATCH_CARD,
    )
    verdict = evaluate_gate(proposal, view)
    assert verdict.accepted, "no R1-R8 rule validates remedy against the legal remedy set"


# ---------------------------------------------------------------------------
# Executor-level proof, end to end through the real runner: accepted +
# unmapped is neither WAIT nor gate_rejected.
# ---------------------------------------------------------------------------


def test_accepted_contact_remedy_none_is_enforcement_failure_not_wait():
    records, capturing_ledger = _capturing_ledger()
    policy = _unmapped_contact_policy(remedy=None)

    result = run_episode_a3(
        "dev", CARD_BROKEN_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )

    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    assert wakeup_records
    first = wakeup_records[0]

    assert first.gate_verdict == "accept"
    assert first.parsed_action["action_type"] == "CONTACT"
    assert first.parsed_action["remedy"] is None
    assert first.fallback_reason == FALLBACK_NO_EXECUTOR_MAPPING
    assert first.fallback_reason != "gate_rejected"
    assert first.executed_action == {"action_type": "ENFORCEMENT_FAILURE"}
    assert first.executed_action != {"action_type": "WAIT"}

    # Episode continuity: every window day still produced a ledger record.
    window_days = EPISODE_CFG["episode"]["window_days"]
    assert len(records) == window_days + 1
    assert result is not None


def test_accepted_contact_unrecognized_remedy_is_enforcement_failure_not_wait():
    records, capturing_ledger = _capturing_ledger()
    policy = _unmapped_contact_policy(remedy="not_a_real_remedy")

    result = run_episode_a3(
        "dev", CARD_BROKEN_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )

    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    assert wakeup_records
    first = wakeup_records[0]

    assert first.gate_verdict == "accept"
    assert first.parsed_action["remedy"] == "not_a_real_remedy"
    assert first.fallback_reason == FALLBACK_NO_EXECUTOR_MAPPING
    assert first.executed_action == {"action_type": "ENFORCEMENT_FAILURE"}

    window_days = EPISODE_CFG["episode"]["window_days"]
    assert len(records) == window_days + 1
    assert result is not None


def test_enforcement_failure_sends_no_message_and_does_not_consume_budget():
    """No legal mapping means nothing was actually sent - accounting must
    show exactly that, not a phantom contact and not a phantom WAIT."""
    records, capturing_ledger = _capturing_ledger()
    policy = _unmapped_contact_policy(remedy=None)

    result = run_episode_a3(
        "dev", CARD_BROKEN_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )

    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    first = wakeup_records[0]
    assert first.budget_before == first.budget_after, (
        "an enforcement failure must not consume contact budget"
    )
    assert first.send_hour is None, "no message was sent, so send_hour must not be stamped"
    # No arm sends a contact for this decline_code+remedy pairing, so the
    # episode's own contact count must be zero.
    assert result.contacts_sent == 0


def test_enforcement_failure_never_produces_a_wait_executed_action():
    """Sweeps every wakeup tick of the episode, not just the first, so a
    later-day proposal cannot silently slip back into ordinary WAIT."""
    records, capturing_ledger = _capturing_ledger()
    policy = _unmapped_contact_policy(remedy=None)

    run_episode_a3(
        "dev", CARD_BROKEN_DEV_INDEX, policy, EPISODE_CFG, POPULATION_CFG,
        ledger_record=capturing_ledger,
    )

    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    assert wakeup_records
    for rec in wakeup_records:
        assert rec.executed_action == {"action_type": "ENFORCEMENT_FAILURE"}
        assert rec.fallback_reason == FALLBACK_NO_EXECUTOR_MAPPING


# ---------------------------------------------------------------------------
# Control case: the pre-existing gate-rejection path is untouched and
# remains distinguishable from the new enforcement-failure path.
# ---------------------------------------------------------------------------


def test_gate_rejected_proposal_still_distinct_from_enforcement_failure():
    """A gate REJECTION (a proposal with a legal remedy that R1-R8
    forbids outright) must still follow its existing fallback_reason=
    "gate_rejected" path, never "no_executor_mapping" - the two failure
    modes stay distinguishable."""

    def _risk_flagged_card_change_policy(view: EpisodeView) -> Proposal:
        return Proposal(
            action_type="CONTACT", remedy="card_change",
            rationale="hallucinated: proposing to contact despite the risk flag",
            reason_code=RISK_FLAGGED,
        )

    records, capturing_ledger = _capturing_ledger()
    run_episode_a3(
        "dev", RISK_FLAGGED_DEV_INDEX, _risk_flagged_card_change_policy,
        EPISODE_CFG, POPULATION_CFG, ledger_record=capturing_ledger,
    )

    wakeup_records = [r for r in records if r.tick_type == "wakeup"]
    assert wakeup_records
    first = wakeup_records[0]

    assert first.gate_verdict == "reject"
    assert first.gate_rule_fired == "R4"
    assert first.fallback_reason == "gate_rejected"
    assert first.fallback_reason != FALLBACK_NO_EXECUTOR_MAPPING
    assert first.executed_action != {"action_type": "ENFORCEMENT_FAILURE"}


def test_accepted_unmapped_and_rejected_cases_are_ledger_distinguishable():
    """Direct side-by-side proof that the two cases the amendment
    requires to be distinguishable actually are, using the SAME
    (decline_code-compatible) shape of proposal wherever possible so the
    distinction comes from gate_verdict/fallback_reason, not from an
    unrelated confound."""
    unmapped_records, unmapped_ledger = _capturing_ledger()
    run_episode_a3(
        "dev", CARD_BROKEN_DEV_INDEX, _unmapped_contact_policy(remedy=None),
        EPISODE_CFG, POPULATION_CFG, ledger_record=unmapped_ledger,
    )
    unmapped_first = next(r for r in unmapped_records if r.tick_type == "wakeup")

    def _risk_flagged_card_change_policy(view: EpisodeView) -> Proposal:
        return Proposal(
            action_type="CONTACT", remedy="card_change",
            rationale="hallucinated", reason_code=RISK_FLAGGED,
        )

    rejected_records, rejected_ledger = _capturing_ledger()
    run_episode_a3(
        "dev", RISK_FLAGGED_DEV_INDEX, _risk_flagged_card_change_policy,
        EPISODE_CFG, POPULATION_CFG, ledger_record=rejected_ledger,
    )
    rejected_first = next(r for r in rejected_records if r.tick_type == "wakeup")

    # gate_verdict alone already distinguishes the two cases...
    assert unmapped_first.gate_verdict == "accept"
    assert rejected_first.gate_verdict == "reject"
    # ...and fallback_reason gives a second, independent distinguishing signal.
    assert unmapped_first.fallback_reason == FALLBACK_NO_EXECUTOR_MAPPING
    assert rejected_first.fallback_reason == "gate_rejected"
    assert unmapped_first.fallback_reason != rejected_first.fallback_reason
    # ...and executed_action never collapses the two into the same value.
    assert unmapped_first.executed_action != rejected_first.executed_action


def test_a3d_policy_never_triggers_no_executor_mapping_over_full_dev():
    """Empirical companion to a3d_policy's exhaustive gate-compliance
    proof (tests/test_a3d_policy.py): running the real deterministic
    policy through the amended runner over the full dev cohort produces
    zero no_executor_mapping fallbacks - the new branch is genuinely
    dead code for A3-D, exactly as the module docstring's other
    unreachability claims already are for their own branches."""
    from rrx.agent.policy import a3d_policy
    from rrx.harness.splits import DEV_INDICES, DEV_SPLIT

    records, capturing_ledger = _capturing_ledger()
    for i in DEV_INDICES:
        run_episode_a3(
            DEV_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG,
            ledger_record=capturing_ledger,
        )
    no_mapping_records = [
        r for r in records if r.fallback_reason == FALLBACK_NO_EXECUTOR_MAPPING
    ]
    assert no_mapping_records == []


def test_ledger_record_shape_unchanged_by_the_new_branch():
    """The new branch reuses the existing fallback_reason/executed_action
    fields - it must not add, remove, or rename any LedgerRecord field."""
    import dataclasses

    assert len(dataclasses.fields(LedgerRecord)) == 22


def test_new_fallback_reason_is_not_the_frozen_five_planner_values():
    """The new value must be genuinely distinct from every pre-existing
    fallback_reason - not a coincidental reuse of an unrelated string."""
    from rrx.agent.planner import FALLBACK_REASONS

    assert FALLBACK_NO_EXECUTOR_MAPPING not in FALLBACK_REASONS
