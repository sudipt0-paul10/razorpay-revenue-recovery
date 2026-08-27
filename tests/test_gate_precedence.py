"""docs/A3-DESIGN.md §8: "Precedence: R2, R4 -> R3 -> R1, R8 -> R5, R6."
A proposal that violates multiple rules must fire only the
highest-precedence one.

Note there is no "R7" gate rule (EVAL.md §5.2 row 7, "no audit record: 0",
is a structural runner invariant - one ledger record per tick - not a
rejectable gate rule; see tests/test_ledger_completeness.py). The
precedence chain therefore covers exactly R1-R6 and R8 (7 rules), which
is what src/rrx/agent/gate.py implements and what this file checks.
"""

from __future__ import annotations

from rrx.agent.gate import evaluate_gate
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


def _view(**overrides) -> EpisodeView:
    base = dict(
        subscription_id="dev-1000",
        subscription_state="pending",
        invoice_amount_inr=50000,
        days_since_first_failure=0,
        auto_retries_remaining=3,
        next_auto_retry_day=1,
        decline_code="card_expired",
        billing_amount_inr=50000,
        contact_history=(),
        budget_remaining=3,
    )
    base.update(overrides)
    return EpisodeView(**base)


def _proposal(action_type: str, remedy: str | None = None) -> Proposal:
    return Proposal(
        action_type=action_type, remedy=remedy, rationale="test", reason_code="test"
    )


def test_r3_beats_r5_when_both_violated():
    """CONTACT(card_change) for insufficient_funds (violates R3) with
    budget_remaining=0 (would also violate R5). R3 > R5 in precedence -
    only R3 should fire."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"),
        _view(decline_code="insufficient_funds", budget_remaining=0),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R3"


def test_r4_beats_r3_when_both_violated():
    """CONTACT(card_change) for payment_risk_check_failed - R3's forbidden
    set is {insufficient_funds, transaction_limit_exceeded}, so R3 does
    NOT fire here on decline_code alone; R4 fires on decline_code ==
    payment_risk_check_failed regardless of remedy. This proves R4 (tier
    1) preempts what would otherwise reach R3 (tier 2) for ANY remedy,
    including one that would look R3-like if the decline_code differed."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"),
        _view(decline_code="payment_risk_check_failed"),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R4"


def test_r2_beats_r4_precedence_tie_broken_deterministically():
    """subscription_state=cancelled (R2) AND decline_code=
    payment_risk_check_failed (R4) simultaneously - both tier-1 rules.
    The implementation's fixed sub-order (R2 checked before R4) must fire
    R2, deterministically, every call."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"),
        _view(subscription_state="cancelled", decline_code="payment_risk_check_failed"),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R2"


def test_r1_beats_r8_precedence_tie_broken_deterministically():
    """An out-of-schema action_type (R1) is, by construction, never
    action_type == "CONTACT", so R8 (which requires CONTACT) can never
    actually co-fire with R1 in practice. This proves R1 alone still
    fires cleanly (not silently swallowed by the R8 check that follows it
    in the same precedence tier)."""
    verdict = evaluate_gate(
        _proposal("RETRY"), _view(decline_code="incorrect_otp")
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R1"


def test_r5_beats_r6_when_both_violated():
    """CONTACT with budget_remaining=0 (R5) plus an out-of-window
    send_hour override (R6, testability-only). R5 > R6 in precedence -
    only R5 should fire."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"),
        _view(budget_remaining=0),
        send_hour="23:00",
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R5"
