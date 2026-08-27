"""docs/A3-DESIGN.md §8: for EACH of R1-R8, one synthetic adversarial
Proposal engineered to trigger it (assert reject, assert the correct
rule_fired), and one engineered not to (assert accept).

Proposals are constructed IN THIS TEST - never driven by a policy.
A3-D is gate-compliant by construction (it never proposes a violation),
so a gate tested only against a real policy's output would never
exercise a single rejection path (§8's own "Gate test driver" note).
"""

from __future__ import annotations

from rrx.agent.gate import evaluate_gate
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


def _view(
    *,
    subscription_state: str = "pending",
    decline_code: str = "card_expired",
    budget_remaining: int = 3,
) -> EpisodeView:
    return EpisodeView(
        subscription_id="dev-1000",
        subscription_state=subscription_state,
        invoice_amount_inr=50000,
        days_since_first_failure=0,
        auto_retries_remaining=3,
        next_auto_retry_day=1,
        decline_code=decline_code,
        billing_amount_inr=50000,
        contact_history=(),
        budget_remaining=budget_remaining,
    )


def _proposal(action_type: str, remedy: str | None = None) -> Proposal:
    return Proposal(
        action_type=action_type, remedy=remedy, rationale="test", reason_code="test"
    )


# --------------------------------------------------------------------------
# R1 - agent-initiated retries: reject any action_type outside the
# 3-value schema (CONTACT|WAIT|STOP) - "no such value exists in the
# schema", so an out-of-schema value is the only way to construct one.
# --------------------------------------------------------------------------

def test_r1_rejects_out_of_schema_action_type():
    verdict = evaluate_gate(_proposal("RETRY"), _view())
    assert not verdict.accepted
    assert verdict.rule_fired == "R1"


def test_r1_accepts_in_schema_action_type():
    verdict = evaluate_gate(_proposal("WAIT"), _view())
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R2 - contacts to cancelled/expired subscriptions: 0.
# --------------------------------------------------------------------------

def test_r2_rejects_contact_to_cancelled_subscription():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(subscription_state="cancelled")
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R2"


def test_r2_accepts_contact_to_non_terminal_subscription():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(subscription_state="pending")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R3 - card_change for insufficient_funds/transaction_limit_exceeded: 0.
# --------------------------------------------------------------------------

def test_r3_rejects_card_change_for_insufficient_funds():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(decline_code="insufficient_funds")
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R3"


def test_r3_accepts_card_change_for_card_expired():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(decline_code="card_expired")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R4 - contacts after payment_risk_check_failed: 0.
# --------------------------------------------------------------------------

def test_r4_rejects_contact_for_payment_risk_check_failed():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"),
        _view(decline_code="payment_risk_check_failed"),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R4"


def test_r4_accepts_contact_for_a_non_risk_decline_code():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"), _view(decline_code="insufficient_funds")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R5 - budget cap: 0. Enforcement-by-construction at the runner level
# (the real runner never calls the gate once budget_remaining == 0 -
# tick_type=budget_exhausted instead); still checked defensively here.
# --------------------------------------------------------------------------

def test_r5_rejects_contact_when_budget_exhausted():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(budget_remaining=0)
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R5"


def test_r5_accepts_contact_when_budget_remains():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(budget_remaining=1)
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R6 - quiet hours: 0. Declared vacuous in sim-v1 (no intraday model) -
# the executor always stamps the fixed AGENT_SEND_HOUR ("10:00"), which
# is always within the window, so the real runner never triggers this.
# `send_hour` is a testability-only override to exercise the branch.
# --------------------------------------------------------------------------

def test_r6_rejects_an_out_of_window_send_hour():
    verdict = evaluate_gate(_proposal("WAIT"), _view(), send_hour="23:00")
    assert not verdict.accepted
    assert verdict.rule_fired == "R6"


def test_r6_accepts_the_fixed_in_window_send_hour():
    verdict = evaluate_gate(_proposal("WAIT"), _view())  # default send_hour="10:00"
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R8 - unverified/attended-only codes: 0. Defensive only - cohort
# generation already guarantees view.decline_code is always a known-good
# value; this exercises the gate's own defensive check directly.
# --------------------------------------------------------------------------

def test_r8_rejects_contact_for_an_unverified_decline_code():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"),
        _view(decline_code="incorrect_otp"),  # data/decline_codes.yaml unverified.codes
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R8"


def test_r8_accepts_contact_for_a_known_good_decline_code():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"), _view(decline_code="insufficient_funds")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None
