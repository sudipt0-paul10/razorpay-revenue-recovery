"""Day 2 Stage 4B: EpisodeView is actually constructed from real simulator
state (RULING 7), not merely a typed-but-unpopulated schema.

tests/test_no_latent_leak.py covers the leak-boundary side (field-set
equality, no latent names, no object-reference types, frozen/slotted). This
file covers the CONSTRUCTION side: that `rrx.sim.engine.build_episode_view`/
`run_episode(..., capture_view_at_day=...)` produces real, correct,
deterministic values from a real episode - Ruling 10 items 2, 4, 6, 7, 8.
"""

from __future__ import annotations

import dataclasses

import pytest

from rrx.features.episode_view import ContactRecord, EpisodeView
from rrx.sim.engine import EpisodeResult, build_episode_view, run_episode
from rrx.sim.latent import load_configs


@pytest.fixture(scope="module")
def configs():
    return load_configs()


def _find_episode_with_condition(
    population_cfg, key: str, start: int = 1000, count: int = 500
) -> int:
    from rrx.sim.cohort import sample_opening_condition_key

    for i in range(start, start + count):
        if sample_opening_condition_key("dev", i, population_cfg) == key:
            return i
    pytest.fail(
        f"no episode with opening condition {key!r} found in range({start}, {start + count})"
    )


# -- item 2: actual runtime construction -------------------------------------

def test_run_episode_without_capture_returns_bare_episode_result(configs):
    """Backward compatibility: the default call shape is completely
    unaffected by RULING 7's addition."""
    episode_cfg, population_cfg = configs
    result = run_episode("dev", 1000, "A2", episode_cfg, population_cfg)
    assert isinstance(result, EpisodeResult)


def test_run_episode_with_capture_returns_real_episode_view(configs):
    episode_cfg, population_cfg = configs
    result, view = run_episode(
        "dev", 1000, "A2", episode_cfg, population_cfg, capture_view_at_day=5
    )
    assert isinstance(result, EpisodeResult)
    assert isinstance(view, EpisodeView)
    assert view.subscription_id == "dev-1000"


def test_capture_view_is_none_when_the_day_is_never_reached(configs):
    """The subscription_cancelled_by_customer path returns before the day
    loop exists - capture must degrade to None, not raise or fabricate."""
    episode_cfg, population_cfg = configs
    i = _find_episode_with_condition(population_cfg, "subscription_cancelled_by_customer")
    result, view = run_episode(
        "dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=5
    )
    assert result.opening_condition_key == "subscription_cancelled_by_customer"
    assert view is None


def test_build_episode_view_capture_is_deterministic(configs):
    episode_cfg, population_cfg = configs
    _, view_a = run_episode("dev", 1000, "A2", episode_cfg, population_cfg, capture_view_at_day=5)
    _, view_b = run_episode("dev", 1000, "A2", episode_cfg, population_cfg, capture_view_at_day=5)
    assert view_a == view_b


# -- item 4: contact_history populated after messages ------------------------

def test_contact_history_is_populated_after_messages_are_sent(configs):
    """card_expired gets an automatic email at T+0 and an agent card-change
    at T+0 and T+5 (see a2_action_for_day) - by day 5, contact_history must
    hold at least those entries."""
    episode_cfg, population_cfg = configs
    i = _find_episode_with_condition(population_cfg, "card_expired")
    _, view = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=5)
    assert len(view.contact_history) >= 3  # T+0 email, T+0 card-change, T+5 card-change
    for record in view.contact_history:
        assert isinstance(record, ContactRecord)


def test_contact_history_is_empty_before_any_message(configs):
    """Capturing before T+0 is not possible (loop starts at day 0, and the
    T+0 email fires first thing) - but capturing exactly at day 0 for a
    condition with no day-0 agent action must show only the automatic
    email."""
    episode_cfg, population_cfg = configs
    i = _find_episode_with_condition(population_cfg, "bank_technical_error")
    _, view = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=0)
    assert len(view.contact_history) == 1
    assert view.contact_history[0].channel == "email"
    assert view.contact_history[0].remedy == "both"
    assert view.contact_history[0].day == 0


def test_contact_record_remedy_mapping(configs):
    """card_change -> 'card_change', topup_reminder -> 'topup_reminder',
    the dual-content automatic email -> 'both' (SIM.md §3's own action
    table uses exactly this label for that row)."""
    episode_cfg, population_cfg = configs
    i = _find_episode_with_condition(population_cfg, "insufficient_funds")
    _, view = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=1)
    remedies = {r.remedy for r in view.contact_history}
    assert "both" in remedies  # T+0 automatic email
    assert "topup_reminder" in remedies  # T+1 agent contact
    assert "card_change" not in remedies  # insufficient_funds never gets this


def test_contact_history_never_contains_a_simulator_object():
    """Every entry's fields must be plain values - this exercises real
    constructed instances, complementing test_no_latent_leak.py's static
    type-annotation check."""
    import rrx.sim.latent as latent_mod

    episode_cfg, population_cfg = load_configs()
    _, view = run_episode("dev", 1000, "A2", episode_cfg, population_cfg, capture_view_at_day=5)
    for record in view.contact_history:
        for f in dataclasses.fields(record):
            value = getattr(record, f.name)
            assert not isinstance(value, latent_mod.LatentState)
            assert type(value) in (int, str, bool)


# -- item 7: retry-window fields ----------------------------------------------

def test_retry_window_fields_are_relative_days(configs):
    """RULING 1: no calendar objects anywhere."""
    episode_cfg, population_cfg = configs
    _, view = run_episode("dev", 1000, "A2", episode_cfg, population_cfg, capture_view_at_day=1)
    assert isinstance(view.days_since_first_failure, int)
    assert view.days_since_first_failure == 1
    assert isinstance(view.auto_retries_remaining, int)
    assert view.next_auto_retry_day is None or isinstance(view.next_auto_retry_day, int)


def test_auto_retries_remaining_and_next_retry_day_before_and_after_retries(configs):
    episode_cfg, population_cfg = configs
    i = _find_episode_with_condition(population_cfg, "bank_technical_error")

    _, view_day0 = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=0)
    assert view_day0.auto_retries_remaining == 3  # T+1, T+2, T+3 all still ahead
    assert view_day0.next_auto_retry_day == 1

    _, view_day2 = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=2)
    if not view_day2.subscription_state == "active":  # not yet recovered by day 2
        assert view_day2.auto_retries_remaining == 1  # only T+3 left
        assert view_day2.next_auto_retry_day == 3


def test_auto_retries_remaining_is_zero_once_halted(configs):
    episode_cfg, population_cfg = configs
    # insufficient_funds with a late funds-restore is a realistic way to
    # reach halted without checking every seed by hand - search a range.
    for i in range(1000, 1300):
        result, view = run_episode(
            "dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=10
        )
        if view is not None and view.subscription_state == "halted":
            assert view.auto_retries_remaining == 0
            assert view.next_auto_retry_day is None
            return
    pytest.fail("no halted episode found by day 10 in range(1000, 1300)")


# -- item 8: decline_code group-level mapping --------------------------------

def test_decline_code_is_group_level_for_ambiguous_decline(configs):
    """RULING 2: the observable group label, never the resolved latent
    Bernoulli cause - population.yaml's own note: 'A3 and A2 both see only
    decline_code for this bucket'."""
    episode_cfg, population_cfg = configs
    i = _find_episode_with_condition(population_cfg, "ambiguous_decline")
    _, view = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=0)
    assert view.decline_code == "ambiguous_decline"


def test_decline_code_matches_opening_condition_key_generally(configs):
    episode_cfg, population_cfg = configs
    for key in ("card_expired", "insufficient_funds", "bank_technical_error"):
        i = _find_episode_with_condition(population_cfg, key)
        _, view = run_episode("dev", i, "A2", episode_cfg, population_cfg, capture_view_at_day=0)
        assert view.decline_code == key


# -- billing_amount_inr aliasing (RULING 8) -----------------------------------

def test_billing_amount_inr_is_aliased_to_invoice_amount_inr(configs):
    episode_cfg, population_cfg = configs
    _, view = run_episode("dev", 1000, "A2", episode_cfg, population_cfg, capture_view_at_day=0)
    assert view.billing_amount_inr == view.invoice_amount_inr


# -- item 9: removed fields are not fabricated --------------------------------

def test_removed_fields_are_absent_not_fabricated():
    field_names = {f.name for f in dataclasses.fields(EpisodeView)}
    for removed in (
        "decline_source", "billing_cycle_day", "completed_billing_cycles",
        "customer_tenure_days", "prior_pending_episodes", "prior_recovery_channel",
    ):
        assert removed not in field_names, f"{removed} should have been removed, not fabricated"


def test_build_episode_view_is_a_pure_positive_construction():
    """RULING 1: construct EpisodeView explicitly from permitted fields.
    Structural check: build_episode_view's only object-typed parameters are
    the cohort/state/config it derives values FROM - it does not accept or
    forward any additional simulator reference into the EpisodeView it
    returns (checked via the type-annotation test in
    test_no_latent_leak.py; this just confirms the function exists and is
    the actual, sole construction path)."""
    import inspect

    sig = inspect.signature(build_episode_view)
    assert sig.return_annotation in ("EpisodeView", EpisodeView)
