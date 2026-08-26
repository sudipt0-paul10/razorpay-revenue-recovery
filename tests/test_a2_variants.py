"""Day 3 baseline resolution: tests for the approved A2-corrected-v1 /
A2-strengthened policy variants (`rrx.baselines.a2_variants`).

`rrx.sim.engine` is never modified by this file or by the module under
test - variants are registered into `engine._POLICIES` at test runtime
only, via a fixture that reverts on teardown, exactly the pattern
`tests/test_stage5_falsification.py` already established for "A1". A2-
original's own tests (`tests/test_engine_policies.py`) are untouched and
still pass unmodified, since `engine.a2_action_for_day` itself was never
edited - this is the direct evidence that A2-original stays reproducible.
"""

from __future__ import annotations

import pytest

from rrx.baselines.a2_variants import (
    a2_corrected_v1_action_for_day,
    a2_strengthened_action_for_day,
)
from rrx.sim import engine
from rrx.sim.engine import a2_action_for_day, run_episode
from rrx.sim.latent import load_configs


@pytest.fixture(scope="module")
def configs():
    return load_configs()


@pytest.fixture(autouse=True)
def _register_variant_arms():
    engine._POLICIES["A2_CORRECTED_V1"] = a2_corrected_v1_action_for_day
    engine._POLICIES["A2_STRENGTHENED"] = a2_strengthened_action_for_day
    yield
    del engine._POLICIES["A2_CORRECTED_V1"]
    del engine._POLICIES["A2_STRENGTHENED"]


# -- card-broken bucket: (1) T+5->T+3 correction, (2) T+5 strengthening -----

def test_corrected_v1_card_broken_bucket_schedule():
    for key in ("card_expired", "debit_instrument_blocked", "card_not_enabled_group"):
        for day in range(0, 31):
            action = a2_corrected_v1_action_for_day(key, day, "pending")
            if day in (0, 3):
                assert action == "card_change"
            else:
                assert action is None


def test_strengthened_card_broken_bucket_schedule():
    for key in ("card_expired", "debit_instrument_blocked", "card_not_enabled_group"):
        for day in range(0, 31):
            action = a2_strengthened_action_for_day(key, day, "pending")
            if day in (0, 3, 5):
                assert action == "card_change"
            else:
                assert action is None


# -- bank_technical_error: (3) restored "if still failing" guard ------------

def test_corrected_v1_bank_technical_error_guarded():
    for day in range(0, 5):
        assert a2_corrected_v1_action_for_day("bank_technical_error", day, "pending") is None
    assert a2_corrected_v1_action_for_day("bank_technical_error", 5, "pending") == "card_change"
    assert a2_corrected_v1_action_for_day("bank_technical_error", 5, "halted") == "card_change"
    # The restored guard: no contact once already recovered.
    assert a2_corrected_v1_action_for_day("bank_technical_error", 5, "active") is None


def test_strengthened_bank_technical_error_guarded():
    assert a2_strengthened_action_for_day("bank_technical_error", 5, "active") is None
    assert a2_strengthened_action_for_day("bank_technical_error", 5, "pending") == "card_change"


# -- transaction_limit_exceeded: (4) gate-scope widened, no card_change ever --

def test_corrected_v1_transaction_limit_exceeded_no_card_change():
    for day in range(0, 31):
        for state in ("pending", "halted", "active"):
            action = a2_corrected_v1_action_for_day("transaction_limit_exceeded", day, state)
            if day == 1:
                assert action == "topup_reminder"
            else:
                assert action is None


def test_strengthened_transaction_limit_exceeded_no_card_change():
    for day in range(0, 31):
        action = a2_strengthened_action_for_day("transaction_limit_exceeded", day, "pending")
        assert action != "card_change"


# -- unchanged conditions delegate to engine.a2_action_for_day exactly ------

@pytest.mark.parametrize(
    "key",
    [
        "insufficient_funds",
        "ambiguous_decline",
        "subscription_cancelled_by_customer",
        "payment_risk_check_failed",
    ],
)
def test_unchanged_conditions_match_a2_original(key):
    for day in range(0, 31):
        for state in ("pending", "halted", "active", "cancelled"):
            original = a2_action_for_day(key, day, state)
            assert a2_corrected_v1_action_for_day(key, day, state) == original
            assert a2_strengthened_action_for_day(key, day, state) == original


# -- extended remedy-match gate: insufficient_funds AND transaction_limit_ -
# exceeded never get a card_change contact under either new variant, over a
# real batch run (not just the pure-function table above).

@pytest.mark.parametrize("arm", ["A2_CORRECTED_V1", "A2_STRENGTHENED"])
def test_never_sends_card_change_for_balance_conditions(configs, arm):
    episode_cfg, population_cfg = configs
    for i in range(1000, 1300):
        r = run_episode("dev", i, arm, episode_cfg, population_cfg)
        if r.opening_condition_key == "insufficient_funds":
            assert r.card_change_sent_for_insufficient_funds is False


@pytest.mark.parametrize("arm", ["A2_CORRECTED_V1", "A2_STRENGTHENED"])
def test_never_exceeds_three_contact_cap(configs, arm):
    episode_cfg, population_cfg = configs
    for i in range(1000, 1300):
        r = run_episode("dev", i, arm, episode_cfg, population_cfg)
        assert r.contacts_sent <= episode_cfg["agent_budget"]["max_contacts_per_episode"]


@pytest.mark.parametrize("arm", ["A2_CORRECTED_V1", "A2_STRENGTHENED"])
def test_no_contact_for_cancelled_or_risk_check_failed(configs, arm):
    episode_cfg, population_cfg = configs
    for i in range(1000, 1300):
        r = run_episode("dev", i, arm, episode_cfg, population_cfg)
        if r.opening_condition_key in (
            "subscription_cancelled_by_customer",
            "payment_risk_check_failed",
        ):
            assert r.contacts_sent == 0


# -- A2-original stays reproducible: engine.a2_action_for_day is untouched --

def test_a2_original_schedule_preserved_for_transparency():
    """A2-original must remain documented and runnable for transparency
    (Day 3 evaluation cleanup). tests/test_engine_policies.py's three
    schedule-pinning tests for the card-broken bucket, bank_technical_
    error, and transaction_limit_exceeded were repointed to the ADOPTED
    (A2-strengthened) schedule as part of that cleanup - this test is
    their replacement for A2-original: it pins engine.a2_action_for_day's
    own, exact, unmodified original schedule for the three conditions
    that changed, so A2-original's card-broken T+0/T+5, bank_technical_
    error's unconditional T+5, and transaction_limit_exceeded's T+1 +
    conditional-T+5 remain independently verified, not just documented in
    EVAL.md §4.1 prose."""
    for key in ("card_expired", "debit_instrument_blocked", "card_not_enabled_group"):
        for day in range(0, 31):
            action = a2_action_for_day(key, day, "pending")
            if day in (0, 5):
                assert action == "card_change"
            else:
                assert action is None

    for day in range(0, 5):
        assert a2_action_for_day("bank_technical_error", day, "pending") is None
    assert a2_action_for_day("bank_technical_error", 5, "pending") == "card_change"
    assert a2_action_for_day("bank_technical_error", 5, "active") == "card_change"  # unguarded

    assert a2_action_for_day("transaction_limit_exceeded", 1, "pending") == "topup_reminder"
    assert a2_action_for_day("transaction_limit_exceeded", 5, "pending") == "card_change"
    assert a2_action_for_day("transaction_limit_exceeded", 5, "halted") == "card_change"
    assert a2_action_for_day("transaction_limit_exceeded", 5, "active") is None
    assert a2_action_for_day("transaction_limit_exceeded", 3, "pending") is None


def test_a2_original_unmodified_by_this_module():
    """rrx.baselines.a2_variants must never rebind rrx.sim.engine.a2_action_
    for_day or mutate rrx.sim.engine._CARD_BROKEN_KEYS - importing it and
    exercising both variants must leave A2-original's own function object
    and behavior byte-identical."""
    from rrx.sim.engine import a2_action_for_day as a2_after_import

    assert a2_after_import is a2_action_for_day
    for key in ("card_expired", "bank_technical_error", "transaction_limit_exceeded"):
        for day in (0, 1, 3, 5):
            a2_action_for_day(key, day, "pending")  # must not raise / must not have moved
