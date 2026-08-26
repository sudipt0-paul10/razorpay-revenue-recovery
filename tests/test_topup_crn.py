"""Day 2 Stage 3, test items 10-12: top-up acceleration mechanics and its
per-engagement CRN-isolation property.
"""

from __future__ import annotations

import pytest

from rrx.sim.engine import _apply_dues_naming_effect, _EpisodeState
from rrx.sim.latent import LatentState, load_configs
from rrx.sim.rng import rng_for_child_stream


def _make_latent(**overrides) -> LatentState:
    base = dict(
        card_chargeable=True,
        funds_available_from=10.0,
        mandate_alive=True,
        blocked_until=0.0,
        channel_response_trait=0.95,
        card_change_completion_propensity=0.95,
    )
    base.update(overrides)
    return LatentState(**base)


def _apply_topup(state, day, episode_cfg, i):
    return _apply_dues_naming_effect(
        state, day=day, episode_cfg=episode_cfg, split="dev", i=i, master_seed=20260825
    )


# -- item 10: min(original_delay, t_engage + draw) ---------------------------

def test_topup_never_increases_funds_available_from():
    episode_cfg, _ = load_configs()
    for i in range(200):
        latent = _make_latent(funds_available_from=10.0)
        state = _EpisodeState(latent, condition_kind="decline_code")
        original = state.funds_available_from
        _apply_topup(state, 1, episode_cfg, i)
        assert state.funds_available_from <= original


def test_topup_result_equals_min_of_original_and_accelerated():
    """Reproduce the exact draw manually (same child-stream seed) and check
    the function's output matches min(original, t_engage + draw)."""
    episode_cfg, _ = load_configs()
    topup_cfg = episode_cfg["latent"]["balance_restore_delay"]["topup_acceleration"]

    for i in range(50):
        latent = _make_latent(funds_available_from=10.0)
        state = _EpisodeState(latent, condition_kind="decline_code")
        original = state.funds_available_from

        rng = rng_for_child_stream("dev", i, "topup_acceleration", "0")
        triggered = rng.random() < topup_cfg["p_topup_action"]
        if triggered:
            accel_draw = rng.exponential(topup_cfg["accelerated_delay"]["mean_days"])
            expected = min(original, 1 + accel_draw)
        else:
            expected = original

        _apply_topup(state, 1, episode_cfg, i)
        assert state.funds_available_from == pytest.approx(expected, abs=1e-12)


def test_topup_does_not_fire_after_halt_boundary():
    """Precondition: 'engagement occurs strictly before next auto-retry'.
    Post-halt (day > halt_boundary_day) there is no next auto-retry left."""
    episode_cfg, _ = load_configs()
    halt_boundary_day = episode_cfg["payment_method_change_effect"]["halt_boundary_day"]
    latent = _make_latent(funds_available_from=10.0)
    for i in range(20):
        state = _EpisodeState(latent, condition_kind="decline_code")
        changed = _apply_topup(state, halt_boundary_day + 1, episode_cfg, i)
        assert changed is False
        assert state.funds_available_from == 10.0
        assert state.topup_engagement_index == 0  # no draw consumed


# -- item 11: acceleration is per engagement, not a persistent trait --------

def test_topup_is_a_fresh_trial_each_engagement_not_cached():
    """Two consecutive dues-naming engagements in the same episode must each
    get their own independent Bernoulli + Exponential draw (topup_engagement_
    index increments), not reuse the first result."""
    episode_cfg, _ = load_configs()
    latent = _make_latent(funds_available_from=10.0)
    state = _EpisodeState(latent, condition_kind="decline_code")

    _apply_topup(state, 1, episode_cfg, 7)
    assert state.topup_engagement_index == 1
    after_first = state.funds_available_from

    _apply_topup(state, 1, episode_cfg, 7)
    assert state.topup_engagement_index == 2

    # Independently reproduce draw #1 (index "1") and confirm the second
    # call used it, not a repeat of draw #0.
    rng1 = rng_for_child_stream("dev", 7, "topup_acceleration", "1")
    topup_cfg = episode_cfg["latent"]["balance_restore_delay"]["topup_acceleration"]
    triggered = rng1.random() < topup_cfg["p_topup_action"]
    expected_second = after_first
    if triggered:
        accel_draw = rng1.exponential(topup_cfg["accelerated_delay"]["mean_days"])
        expected_second = min(after_first, 1 + accel_draw)
    assert state.funds_available_from == pytest.approx(expected_second, abs=1e-12)


# -- item 12: per-engagement RNG indexing preserves CRN across differing
# engagement counts between arms -------------------------------------------

def test_engagement_index_zero_is_independent_of_how_many_draws_precede_it():
    """episode i, engagement index 0 must map to the SAME draw regardless of
    whether some other arm/run consumed zero or several prior engagements -
    since each child stream is independently hashed from (split, i, root,
    child), never from a shared Generator's call-order position."""
    rng_a = rng_for_child_stream("dev", 3, "topup_acceleration", "0")
    rng_b = rng_for_child_stream("dev", 3, "topup_acceleration", "0")
    assert rng_a.random() == rng_b.random()


def test_engagement_index_one_unaffected_by_whether_index_zero_was_ever_drawn():
    """Simulates the exact scenario the ruling describes: arm X takes zero
    engagements before this one (never calls index 0), arm Y takes one
    engagement before it (calls index 0 first). Index 1's draw must be
    identical either way."""
    # Arm "skips" index 0 entirely - just draws index 1 directly.
    skip_rng = rng_for_child_stream("dev", 9, "topup_acceleration", "1")
    skip_value = skip_rng.random()

    # Arm draws index 0 first (consuming it), THEN index 1.
    consume_rng0 = rng_for_child_stream("dev", 9, "topup_acceleration", "0")
    consume_rng0.random()  # consume index 0's stream - must not affect index 1's
    full_rng1 = rng_for_child_stream("dev", 9, "topup_acceleration", "1")
    full_value = full_rng1.random()

    assert skip_value == full_value
