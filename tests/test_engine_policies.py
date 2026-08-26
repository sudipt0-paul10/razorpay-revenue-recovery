"""Day 2 Stage 3, test items 3, 14, 15, 16: same latent world across arms,
A0's exact (empty) policy, A2's exact schedule, and invoice-recovery /
subscription-rescue staying separate outcomes.

Day 3 evaluation cleanup (2026-08-27): most of this file still pins
A2-original (`rrx.sim.engine.a2_action_for_day`, frozen and untouched
under `sim-v1`) - e.g. `insufficient_funds`, `ambiguous_decline`, the
cancelled/risk-check exclusions, the 3-contact cap, and the §5.2
insufficient_funds gate check are all unchanged and still exercise
A2-original directly. Only the three tests naming card-broken,
`bank_technical_error`, and `transaction_limit_exceeded` schedules are
updated to pin the ADOPTED schedule instead - see the comment directly
above `test_a2_card_broken_bucket_schedule`.
"""

from __future__ import annotations

import inspect

import pytest

from rrx.baselines.a2_variants import a2_strengthened_action_for_day
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
#
# Day 3 evaluation cleanup (2026-08-27): the three tests below are updated to
# pin the ADOPTED A2 schedule (rrx.baselines.a2_variants.
# a2_strengthened_action_for_day - EVAL.md §4.1.2), not A2-original
# (rrx.sim.engine.a2_action_for_day, still frozen/untouched under sim-v1).
# test_a2_transaction_limit_exceeded_schedule_keeps_fallback was renamed to
# test_a2_transaction_limit_exceeded_schedule_fallback_removed (2026-08-27)
# once its old name started describing the opposite of what it asserts; the
# other two names still accurately describe their (unchanged) subject matter
# and are kept as-is. A2-original's own exact schedule for all three
# conditions remains separately pinned, unchanged, by
# tests/test_a2_variants.py::test_a2_original_schedule_preserved_for_
# transparency, so A2-original stays documented and runnable.

def test_a2_card_broken_bucket_schedule():
    """Adopted schedule (A2-strengthened): T+0/T+3/T+5, not A2-original's
    T+0/T+5. T+3 is the T+5->T+3 validity correction (EVAL.md §4.1.1 item
    1); T+5 is the separate post-halt rescue strengthening (EVAL.md
    §4.1.2), restored as a third contact, not a replacement for T+3."""
    for key in ("card_expired", "debit_instrument_blocked", "card_not_enabled_group"):
        for day in range(0, 31):
            action = a2_strengthened_action_for_day(key, day, "pending")
            if day in (0, 3, 5):
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


def test_a2_transaction_limit_exceeded_schedule_fallback_removed():
    """Renamed from test_a2_transaction_limit_exceeded_schedule_keeps_
    fallback (2026-08-27) - the old name described A2-original's T+5
    card-change fallback, which the adopted schedule below no longer has.
    EVAL.md §5.2's remedy-match gate is widened (EVAL.md §4.1.1 item 3) to
    cover transaction_limit_exceeded exactly like insufficient_funds,
    since card_chargeable=True at opening makes card-change an equally
    guaranteed no-op for both. The T+5 card-change fallback is REMOVED -
    only the T+1 top-up reminder remains."""
    for day in range(0, 31):
        for state in ("pending", "halted", "active"):
            action = a2_strengthened_action_for_day("transaction_limit_exceeded", day, state)
            if day == 1:
                assert action == "topup_reminder"
            else:
                assert action is None


def test_a2_ambiguous_decline_schedule():
    for day in range(0, 31):
        action = a2_action_for_day("ambiguous_decline", day, "pending")
        assert action == ("card_change" if day in (0, 7) else None)


def test_a2_bank_technical_error_schedule_no_contact_before_t3():
    """The T+5 contact now carries the restored 'if still pending/halted'
    guard (EVAL.md §4.1.1 item 2) - a contact fires at T+5 only if the
    condition has not already auto-resolved. It always has by day 2 for
    this condition (episode.yaml's bank_technical_error_clearance support
    is [0, 2]), so the guarded version never actually fires in practice -
    that is the point of the fix (dev diagnostic: 51/51 A0 episodes for
    this condition already recover with zero contact)."""
    for day in range(0, 5):
        assert a2_strengthened_action_for_day("bank_technical_error", day, "pending") is None
    assert a2_strengthened_action_for_day("bank_technical_error", 5, "pending") == "card_change"
    assert a2_strengthened_action_for_day("bank_technical_error", 5, "active") is None


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
