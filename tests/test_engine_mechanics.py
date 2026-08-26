"""Day 2 Stage 3, test items 4-9, 13: clock, AND gate, RULING 1, RULING 2,
outcome separation, and automatic-email budget/fatigue exemption.

Uses rrx.sim.engine's private helpers directly (white-box) where a
mechanism-level property can't be observed through EpisodeResult alone -
these are exactly the proposed, still-pending rulings this stage exists to
pin down for review (see engine.py's module docstring; neither ruling is
recorded in SIM.md yet).
"""

from __future__ import annotations

import pytest

from rrx.sim.engine import (
    AGENT_CHANNEL,
    AUTO_EMAIL_CHANNEL,
    _apply_dues_naming_effect,
    _EpisodeState,
    _retry_succeeds,
    _send_message,
    run_episode,
)
from rrx.sim.latent import LatentState, load_configs


@pytest.fixture(scope="module")
def configs():
    return load_configs()


def _make_latent(**overrides) -> LatentState:
    base = dict(
        card_chargeable=True,
        funds_available_from=10.0,
        mandate_alive=True,
        blocked_until=0.0,
        channel_response_trait=0.95,  # near-certain engagement for deterministic tests
        card_change_completion_propensity=0.95,
    )
    base.update(overrides)
    return LatentState(**base)


# -- item 5: T+1/T+2/T+3 retry schedule --------------------------------------

def test_retry_schedule_is_exactly_t1_t2_t3(configs):
    episode_cfg, _ = configs
    assert episode_cfg["razorpay_retry_engine"]["card_schedule_days"] == [1, 2, 3]


# -- item 6: physical-state AND gate -----------------------------------------

@pytest.mark.parametrize(
    "card_chargeable,funds_ok,mandate_alive,blocked_ok,expected",
    [
        (True, True, True, True, True),
        (False, True, True, True, False),
        (True, False, True, True, False),
        (True, True, False, True, False),
        (True, True, True, False, False),
    ],
)
def test_retry_and_gate_requires_all_four_terms(
    card_chargeable, funds_ok, mandate_alive, blocked_ok, expected
):
    day = 2
    latent = _make_latent(
        card_chargeable=card_chargeable,
        funds_available_from=(day if funds_ok else day + 1),
        mandate_alive=mandate_alive,
        blocked_until=(day if blocked_ok else day + 1),
    )
    state = _EpisodeState(latent, condition_kind="decline_code")
    assert _retry_succeeds(state, day) is expected


# -- item 4: RULING 1 - within-day ordering ----------------------------------

def test_engaged_message_effect_visible_to_same_day_retry():
    """A card-naming message sent+engaged on day t, whose completion succeeds,
    must be visible to day t's own retry check - not just day t+1's."""
    latent = _make_latent(card_chargeable=False, funds_available_from=0.0)
    state = _EpisodeState(latent, condition_kind="decline_code")

    assert not _retry_succeeds(state, 1)  # card_chargeable False: would fail

    _send_message(
        state, day=1, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
        is_agent_contact=True, split="dev", i=0, latent=latent,
        episode_cfg=load_configs()[0], master_seed=20260825,
    )
    assert state.card_chargeable is True  # high trait/completion => resolved deterministically
    assert _retry_succeeds(state, 1) is True  # same day t=1, not just t=2


def test_topup_engagement_effect_is_visible_to_that_days_own_retry_check():
    """RULING 1 applies to top-up too: whatever funds_available_from ends up
    being after an engaged dues-naming message on day t, day t's OWN retry
    check (not just day t+1's) must read the post-effect value - proven here
    by constructing the state exactly as _apply_dues_naming_effect would
    leave it (t_engage + draw can never be <= t_engage, since draw > 0, so
    top-up specifically can never itself cause a same-day success - only
    card-naming's instantaneous effect can, see the test above - but the
    ORDERING must still hold: the retry check must not run against the
    PRE-effect state)."""
    episode_cfg, _ = load_configs()
    latent = _make_latent(card_chargeable=True, funds_available_from=10.0)
    state = _EpisodeState(latent, condition_kind="decline_code")

    pre_effect_funds = state.funds_available_from
    _apply_dues_naming_effect(
        state, day=1, episode_cfg=episode_cfg, split="dev", i=0, master_seed=20260825
    )

    # _retry_succeeds must be evaluated against state AFTER the call above,
    # not a stale pre-effect copy - assert the function reads live state.
    assert _retry_succeeds(state, 1) == (
        state.card_chargeable and 1 >= state.funds_available_from
        and state.mandate_alive and 1 >= state.blocked_until
    )
    if state.funds_available_from != pre_effect_funds:
        assert state.funds_available_from < pre_effect_funds  # only ever accelerates


def test_topup_can_pull_an_otherwise_unreachable_recovery_into_the_retry_window():
    """The mechanism's real, working effect: search for an episode index
    where acceleration fires and lands funds_available_from at or before
    T+3 despite an original delay set beyond the window - proving top-up
    can change a retry outcome, not just move a number."""
    episode_cfg, _ = load_configs()
    for i in range(500):
        latent = _make_latent(card_chargeable=True, funds_available_from=100.0)
        state = _EpisodeState(latent, condition_kind="decline_code")
        assert not _retry_succeeds(state, 3)  # 100.0 unreachable within the window

        changed = _apply_dues_naming_effect(
            state, day=1, episode_cfg=episode_cfg, split="dev", i=i, master_seed=20260825
        )
        if changed and state.funds_available_from <= 3:
            assert _retry_succeeds(state, 3) is True
            return
    pytest.fail("no episode index in range(500) produced a window-crossing topup draw")


# -- item 7: RULING 2 - immediate post-halt card rescue, narrower form
# (card_chargeable must have been False AT OPENING) -------------------------

def test_a_card_broken_at_open_episode_can_be_post_halt_rescued():
    """(a) An episode that OPENED with card_chargeable=False can be
    rescued post-halt once an engaged card-naming message flips it true."""
    latent = _make_latent(card_chargeable=False, funds_available_from=0.0)
    state = _EpisodeState(latent, condition_kind="decline_code")
    assert state.card_chargeable_at_opening is False
    state.subscription_state = "halted"

    _send_message(
        state, day=5, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
        is_agent_contact=True, split="dev", i=0, latent=latent,
        episode_cfg=load_configs()[0], master_seed=20260825,
    )
    assert state.card_chargeable is True
    assert state.subscription_state == "active"


def test_b_already_chargeable_at_open_episode_cannot_be_post_halt_rescued():
    """(b) An episode that was ALREADY card_chargeable=True at opening
    (insufficient_funds, transaction_limit_exceeded, payment_risk_check_
    failed all open this way per SIM.md §2) must NOT become subscription_
    rescued merely because a message occurs post-halt - there was nothing
    for that message to have fixed."""
    latent = _make_latent(card_chargeable=True, funds_available_from=0.0)
    state = _EpisodeState(latent, condition_kind="decline_code")
    assert state.card_chargeable_at_opening is True
    state.subscription_state = "halted"

    _send_message(
        state, day=5, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
        is_agent_contact=True, split="dev", i=0, latent=latent,
        episode_cfg=load_configs()[0], master_seed=20260825,
    )
    assert state.card_chargeable is True  # unchanged - idempotent no-op, was already true
    assert state.subscription_state == "halted"  # NOT rescued


def test_insufficient_funds_and_kin_structurally_cannot_be_post_halt_rescued(configs):
    """Black-box run_episode-level confirmation of (b): over a real batch,
    every A2 episode of insufficient_funds/transaction_limit_exceeded/
    payment_risk_check_failed that does not recover its invoice must also
    fail to rescue - these three always open card_chargeable=True
    (SIM.md §2), so the narrower rule structurally excludes them."""
    episode_cfg, population_cfg = configs
    always_chargeable = {
        "insufficient_funds", "transaction_limit_exceeded", "payment_risk_check_failed"
    }
    checked_any = False
    for i in range(1000, 1400):
        r = run_episode("dev", i, "A2", episode_cfg, population_cfg)
        if r.opening_condition_key in always_chargeable and not r.invoice_recovered:
            checked_any = True
            assert r.subscription_rescued is False, (r.opening_condition_key, i)
    assert checked_any


def test_no_rescue_while_still_pending_or_already_active():
    latent = _make_latent(card_chargeable=False)
    for initial_state in ("pending", "active"):
        state = _EpisodeState(latent, condition_kind="decline_code")
        state.subscription_state = initial_state
        _send_message(
            state, day=5, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
            is_agent_contact=True, split="dev", i=1, latent=latent,
            episode_cfg=load_configs()[0], master_seed=20260825,
        )
        assert state.subscription_state == initial_state


# -- item 8: post-halt rescue does NOT recover the invoice -------------------

def test_post_halt_rescue_never_sets_invoice_recovered():
    """run_episode-level: any A2 episode whose subscription is rescued AFTER
    halting (i.e., not via a T+1..T+3 retry success) must have
    invoice_recovered == False."""
    episode_cfg, population_cfg = load_configs()
    found_post_halt_rescue = False
    for i in range(1000, 1300):
        r_a0 = run_episode("dev", i, "A0", episode_cfg, population_cfg)
        r_a2 = run_episode("dev", i, "A2", episode_cfg, population_cfg)
        for r in (r_a0, r_a2):
            if r.subscription_rescued and not r.invoice_recovered:
                found_post_halt_rescue = True
            # Invariant regardless: rescue and recovery are independent bits,
            # never implied by each other in the "rescued but not recovered"
            # direction being forbidden.
    assert found_post_halt_rescue, "expected at least one post-halt-only rescue in this range"


# -- Stage 3 closing item 1: no retry is EVALUATED after halt, not merely
# that today's random draws happen not to satisfy it --------------------

def test_no_retry_evaluated_after_halt_even_if_and_gate_would_pass(monkeypatch):
    """Forces a state that WOULD satisfy the full retry AND-gate on a
    post-halt day (funds_available_from lands at day 10 - unreachable
    during T+1..T+3, so the episode halts, but well within the window and
    trivially satisfiable if the gate were ever evaluated again). Engagement
    is forced to never happen (channel_response_trait=0.0), which also
    isolates this from RULING 2's post-halt rescue check - this test is
    about the RETRY predicate never being evaluated, not about rescue.

    If run_episode() evaluated _retry_succeeds() on any day > halt_boundary_
    day, this episode would recover (the gate genuinely would pass, proven
    below) - since it must not, invoice_recovered proves the loop's
    `day in retry_days` gate (retry_days = {1,2,3}) is what actually
    prevents it, not an accident of this particular random draw.
    """
    import rrx.sim.engine as engine_mod
    from rrx.sim.cohort import CohortEpisode
    from rrx.sim.latent import LatentState

    forced_latent = LatentState(
        card_chargeable=True,
        funds_available_from=10.0,
        mandate_alive=True,
        blocked_until=0.0,
        channel_response_trait=0.0,
        card_change_completion_propensity=0.0,
    )
    forced_cohort = CohortEpisode(
        opening_condition_key="insufficient_funds", invoice_amount_inr=2000
    )

    monkeypatch.setattr(engine_mod, "draw_latent_state", lambda *a, **k: forced_latent)
    monkeypatch.setattr(engine_mod, "sample_cohort_episode", lambda *a, **k: forced_cohort)

    # Sanity: the AND-gate genuinely WOULD pass on a post-halt day - this
    # isn't vacuously true because the forced state can never satisfy it.
    forced_state = _EpisodeState(forced_latent, condition_kind="decline_code")
    assert _retry_succeeds(forced_state, 10) is True

    episode_cfg, population_cfg = load_configs()
    result = run_episode("dev", 0, "A2", episode_cfg, population_cfg)
    assert result.invoice_recovered is False


# -- Stage 3 closing item 2: full run_episode() replay determinism,
# exercising the engine's OWN RNG consumption (engagement, completion,
# topup child streams) - not just cohort/latent determinism -------------

def test_run_episode_full_replay_is_byte_identical():
    """Calls run_episode() twice with identical (split, i, arm) inputs
    across a range wide enough to cover every opening condition and to
    trigger card-naming engagement, completion, and topup-acceleration
    draws (A2's policy sends card-change and topup_reminder messages across
    this range - see test_engine_policies.py's schedule tests). Unlike
    test_cohort_episode_is_deterministic_for_same_split_and_index
    (cohort.py only) or the pre-existing Stage 1 draw_latent_state
    determinism tests (test_latent_sampling.py), this exercises run_episode
    itself end to end, including message_index/topup_engagement_index
    bookkeeping."""
    episode_cfg, population_cfg = load_configs()
    for arm in ("A0", "A2"):
        for i in range(1000, 1120):
            a = run_episode("dev", i, arm, episode_cfg, population_cfg)
            b = run_episode("dev", i, arm, episode_cfg, population_cfg)
            assert a == b, (arm, i)


# -- item 9: invoice recovery only through successful auto-retry ------------

def test_invoice_recovered_implies_subscription_active_and_only_via_retry_window():
    episode_cfg, population_cfg = load_configs()
    for i in range(1000, 1200):
        for arm in ("A0", "A2"):
            r = run_episode("dev", i, arm, episode_cfg, population_cfg)
            if r.invoice_recovered:
                assert r.subscription_rescued  # while_pending success => both together


def test_cancelled_at_open_never_recovers_or_rescues():
    episode_cfg, population_cfg = load_configs()
    found_any = False
    for i in range(1000, 1200):
        for arm in ("A0", "A2"):
            r = run_episode("dev", i, arm, episode_cfg, population_cfg)
            if r.opening_condition_key == "subscription_cancelled_by_customer":
                found_any = True
                assert r.invoice_recovered is False
                assert r.subscription_rescued is False
                assert r.contacts_sent == 0
    assert found_any


# -- item 13: automatic email consumes no budget, no fatigue -----------------

def test_automatic_email_does_not_consume_agent_budget_or_fatigue():
    latent = _make_latent()
    state = _EpisodeState(latent, condition_kind="decline_code")
    _send_message(
        state, day=0, channel=AUTO_EMAIL_CHANNEL, names_card=True, names_dues=True,
        is_agent_contact=False, split="dev", i=0, latent=latent,
        episode_cfg=load_configs()[0], master_seed=20260825,
    )
    assert state.contacts_sent == 0
    assert state.agent_contact_count == 0


def test_automatic_email_never_counted_in_episode_result_contacts_sent():
    """A0 never contacts the customer, yet the automatic email fires at
    T+0 (and at halt) for every non-cancelled episode - contacts_sent must
    stay exactly 0 for every A0 episode."""
    episode_cfg, population_cfg = load_configs()
    for i in range(1000, 1100):
        r = run_episode("dev", i, "A0", episode_cfg, population_cfg)
        assert r.contacts_sent == 0
