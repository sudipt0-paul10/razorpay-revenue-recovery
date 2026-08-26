"""Day 2 Stage 3, test items 3, 14, 15, 16: same latent world across arms,
A0's exact (empty) policy, A2's exact schedule, and invoice-recovery /
subscription-rescue staying separate outcomes.
"""

from __future__ import annotations

import inspect

import pytest

from rrx.sim.engine import a0_action_for_day, a2_action_for_day, run_episode
from rrx.sim.latent import load_configs


@pytest.fixture(scope="module")
def configs():
    return load_configs()


# -- item 3: same latent episode across A0/A2 --------------------------------

def test_same_episode_world_across_arms(configs):
    episode_cfg, population_cfg = configs
    for i in range(1000, 1150):
        a0 = run_episode("dev", i, "A0", episode_cfg, population_cfg)
        a2 = run_episode("dev", i, "A2", episode_cfg, population_cfg)
        assert a0.opening_condition_key == a2.opening_condition_key
        assert a0.invoice_amount_inr == a2.invoice_amount_inr


def test_run_episode_never_threads_arm_into_cohort_or_latent_draws():
    """Structural regression guard: the cohort/latent calls inside
    run_episode() must never receive `arm`, which is what makes the CRN
    pairing above hold in the first place, not just an empirical accident of
    the current policies."""
    src = inspect.getsource(run_episode)
    assert "sample_cohort_episode(split, i, population_cfg, master_seed)" in src
    assert "draw_latent_state(" in src
    # The draw_latent_state call site's argument list (captured across the
    # wrapped call) must not mention `arm`.
    call_start = src.index("draw_latent_state(")
    call_text = src[call_start:src.index(")", call_start) + 1]
    assert "arm" not in call_text


# -- item 14: A0 exact policy behavior ---------------------------------------

@pytest.mark.parametrize("day", range(0, 31))
@pytest.mark.parametrize("subscription_state", ["pending", "halted", "active", "cancelled"])
def test_a0_never_schedules_any_action(day, subscription_state):
    for key in [
        "insufficient_funds", "ambiguous_decline", "card_expired",
        "debit_instrument_blocked", "card_not_enabled_group",
        "subscription_cancelled_by_customer", "bank_technical_error",
        "transaction_limit_exceeded", "payment_risk_check_failed",
    ]:
        assert a0_action_for_day(key, day, subscription_state) is None


def test_a0_episodes_have_zero_contacts_regardless_of_outcome(configs):
    episode_cfg, population_cfg = configs
    for i in range(1000, 1200):
        r = run_episode("dev", i, "A0", episode_cfg, population_cfg)
        assert r.contacts_sent == 0
        assert r.wasted_attempts == 0  # no agent contacts => nothing to waste


# -- item 15: A2 exact policy behavior ---------------------------------------

def test_a2_card_broken_bucket_schedule():
    for key in ("card_expired", "debit_instrument_blocked", "card_not_enabled_group"):
        for day in range(0, 31):
            action = a2_action_for_day(key, day, "pending")
            if day in (0, 5):
                assert action == "card_change"
            else:
                assert action is None


def test_a2_insufficient_funds_schedule_has_no_fallback():
    """Approved fix: insufficient_funds gets ONLY the T+1 top-up, ever - no
    card-change fallback, so EVAL.md §5.2's gate is true by construction."""
    for day in range(0, 31):
        for state in ("pending", "halted", "active"):
            action = a2_action_for_day("insufficient_funds", day, state)
            if day == 1:
                assert action == "topup_reminder"
            else:
                assert action is None


def test_a2_transaction_limit_exceeded_schedule_keeps_fallback():
    assert a2_action_for_day("transaction_limit_exceeded", 1, "pending") == "topup_reminder"
    assert a2_action_for_day("transaction_limit_exceeded", 5, "pending") == "card_change"
    assert a2_action_for_day("transaction_limit_exceeded", 5, "halted") == "card_change"
    assert a2_action_for_day("transaction_limit_exceeded", 5, "active") is None
    assert a2_action_for_day("transaction_limit_exceeded", 3, "pending") is None


def test_a2_ambiguous_decline_schedule():
    for day in range(0, 31):
        action = a2_action_for_day("ambiguous_decline", day, "pending")
        assert action == ("card_change" if day in (0, 7) else None)


def test_a2_bank_technical_error_schedule_no_contact_before_t3():
    for day in range(0, 5):
        assert a2_action_for_day("bank_technical_error", day, "pending") is None
    assert a2_action_for_day("bank_technical_error", 5, "pending") == "card_change"


def test_a2_no_contact_for_cancelled_or_risk_check_failed():
    for day in range(0, 31):
        assert a2_action_for_day("subscription_cancelled_by_customer", day, "cancelled") is None
        assert a2_action_for_day("payment_risk_check_failed", day, "pending") is None


def test_a2_never_exceeds_three_contact_cap(configs):
    episode_cfg, population_cfg = configs
    for i in range(1000, 1300):
        r = run_episode("dev", i, "A2", episode_cfg, population_cfg)
        assert r.contacts_sent <= episode_cfg["agent_budget"]["max_contacts_per_episode"]


def test_a2_never_sends_card_change_for_insufficient_funds(configs):
    """Structural EVAL.md §5.2 gate check, over an actual batch run."""
    episode_cfg, population_cfg = configs
    for i in range(1000, 1300):
        r = run_episode("dev", i, "A2", episode_cfg, population_cfg)
        if r.opening_condition_key == "insufficient_funds":
            assert r.card_change_sent_for_insufficient_funds is False


def test_a2_send_subscription_link_not_in_action_space():
    src = inspect.getsource(a2_action_for_day)
    assert "send_subscription_link" not in src
    assert "subscription_link" not in src


# -- item 16: invoice recovery and subscription rescue stay separate --------

def test_invoice_recovery_and_rescue_are_independent_fields(configs):
    """Both possible combinations besides (recovered, not-rescued) - which
    the outcome model forbids by construction (successful retry sets both) -
    must be observed somewhere in a large-enough batch: (not recovered, not
    rescued) and (not recovered, rescued)."""
    episode_cfg, population_cfg = configs
    seen = set()
    for i in range(1000, 1500):
        for arm in ("A0", "A2"):
            r = run_episode("dev", i, arm, episode_cfg, population_cfg)
            seen.add((r.invoice_recovered, r.subscription_rescued))
            if r.invoice_recovered:
                assert r.subscription_rescued  # forbidden combination
    assert (False, False) in seen
    assert (False, True) in seen
    assert (True, True) in seen
