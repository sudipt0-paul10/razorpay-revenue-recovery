"""SIM.md §1/§2 latent physical-state sampling.

Covers: CRN identity, in-process and cross-process determinism, independence
of funds_available_from from billing_cycle_day, the nine SIM.md §2
opening-condition mappings, the balance-restore mixture's component weights
and salary-cycle moment, Beta-parameter guards, salary-PMF key/probability
pairing, and the frozen eight-substream registry.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from rrx.sim.latent import (
    BLOCKED_INDEFINITELY,
    SUBSTREAM_NAMES,
    _beta_from_mean_concentration,
    _canonical_pmf_arrays,
    _sample_balance_restore_delay,
    draw_latent_state,
    load_configs,
    seed_for_substream,
)

N = 2000
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def configs():
    return load_configs()


def _keys(population_cfg):
    return [c["key"] for c in population_cfg["opening_conditions"]]


class _BranchTrackingRNG:
    """Wraps a real Generator, recording whether the balance-restore
    mixture's salary-cycle branch fired.

    Recovering component membership from output values alone is unreliable -
    the transient branch (truncated Exponential(mean 2.0) on [0, 30]) and the
    salary-cycle branch (salary_day in {1,7,25,30} + Gamma jitter) overlap in
    range. `.choice()` is called if and only if the salary-cycle branch
    fires (the transient branch now uses inverse-CDF, i.e. `.random()` only),
    so it is an exact discriminator.
    """

    def __init__(self, seed: int):
        self._rng = np.random.default_rng(seed)
        self.used_salary_branch = False

    def random(self):
        return self._rng.random()

    def choice(self, *a, **k):
        self.used_salary_branch = True
        return self._rng.choice(*a, **k)

    def gamma(self, *a, **k):
        return self._rng.gamma(*a, **k)

    def beta(self, *a, **k):
        return self._rng.beta(*a, **k)

    def uniform(self, *a, **k):
        return self._rng.uniform(*a, **k)


# -- CRN identity and determinism -------------------------------------------

def test_crn_identity_same_split_and_index_is_byte_identical(configs):
    episode_cfg, population_cfg = configs
    key = "insufficient_funds"
    a = draw_latent_state("dev", 7, key, episode_cfg, population_cfg)
    b = draw_latent_state("dev", 7, key, episode_cfg, population_cfg)
    assert a == b


def test_crn_identity_holds_across_all_nine_conditions(configs):
    episode_cfg, population_cfg = configs
    for key in _keys(population_cfg):
        a = draw_latent_state("dev", 42, key, episode_cfg, population_cfg)
        b = draw_latent_state("dev", 42, key, episode_cfg, population_cfg)
        assert a == b, key


def test_determinism_across_a_fresh_registry_load():
    key = "bank_technical_error"

    episode_cfg_1, population_cfg_1 = load_configs()
    a = draw_latent_state("holdout", 3, key, episode_cfg_1, population_cfg_1)

    episode_cfg_2, population_cfg_2 = load_configs()  # fresh disk read
    b = draw_latent_state("holdout", 3, key, episode_cfg_2, population_cfg_2)

    assert a == b


def test_cross_process_determinism():
    """CRN must hold across process boundaries, not just within one
    interpreter session (the fresh-registry-load test above stays in this
    same process). sha256-based substream seeding - not Python's built-in
    hash(), which is salted per-process for strings - is what makes this
    possible."""
    script = (
        "from rrx.sim.latent import draw_latent_state, load_configs\n"
        "episode_cfg, population_cfg = load_configs()\n"
        "s = draw_latent_state('dev', 11, 'insufficient_funds', episode_cfg, population_cfg)\n"
        "print((s.card_chargeable, s.funds_available_from, s.mandate_alive,\n"
        "       s.blocked_until, s.channel_response_trait,\n"
        "       s.card_change_completion_propensity))\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT, env=env,
        )
        outputs.append(result.stdout.strip())

    assert outputs[0] == outputs[1]
    assert outputs[0] != ""


def test_seed_for_substream_is_a_pure_function_of_its_inputs():
    assert seed_for_substream("dev", 1, "balance_restore") == \
        seed_for_substream("dev", 1, "balance_restore")
    assert seed_for_substream("dev", 1, "balance_restore") != \
        seed_for_substream("dev", 2, "balance_restore")
    assert seed_for_substream("dev", 1, "balance_restore") != \
        seed_for_substream("holdout", 1, "balance_restore")
    # Name-keyed, not positional: same (split, i), different substream name.
    assert seed_for_substream("dev", 1, "balance_restore") != \
        seed_for_substream("dev", 1, "channel_response")


def test_different_episode_indices_do_not_collide(configs):
    """The arm is not an input to any RNG call - only (split, i) is. Two
    different i's should (almost certainly) draw different latent state."""
    episode_cfg, population_cfg = configs
    draws = [
        draw_latent_state("dev", i, "insufficient_funds", episode_cfg, population_cfg)
        for i in range(5)
    ]
    funds = [d.funds_available_from for d in draws]
    assert len(set(funds)) == len(funds)


# -- Independence from billing_cycle_day -------------------------------------

def test_funds_available_from_independent_of_billing_cycle_day(configs):
    """billing_cycle_day is generated independently here, from a separate
    RNG stream that never touches latent.py - it is not an input to
    draw_latent_state at all, by construction (SIM.md §6)."""
    episode_cfg, population_cfg = configs

    funds = [
        draw_latent_state("dev", i, "insufficient_funds",
                           episode_cfg, population_cfg).funds_available_from
        for i in range(N)
    ]

    billing_rng = np.random.default_rng(999_999)  # unrelated to latent.py's seeding
    billing_cycle_day = billing_rng.integers(1, 29, size=N)

    corr = np.corrcoef(np.array(funds), billing_cycle_day)[0, 1]
    assert abs(corr) < 0.05, corr


# -- Decline-code mapping (SIM.md §2) -----------------------------------------

@pytest.mark.parametrize(
    "key", ["card_expired", "debit_instrument_blocked", "card_not_enabled_group"]
)
def test_card_broken_rows_match_sim_md(configs, key):
    episode_cfg, population_cfg = configs
    state = draw_latent_state("dev", 0, key, episode_cfg, population_cfg)
    assert state.card_chargeable is False
    assert state.funds_available_from == 0.0
    assert state.mandate_alive is True
    # Discovered-defect fix, 2026-08-26: "never" (no transient block) is
    # non-blocking (0.0), not BLOCKED_INDEFINITELY - SIM.md's own semantic
    # clarification scopes indefinite-block to transaction_limit_exceeded /
    # payment_risk_check_failed only. See test_never_blocked_rows_match_sim_md.
    assert state.blocked_until == 0.0


def test_insufficient_funds_matches_sim_md(configs):
    episode_cfg, population_cfg = configs
    state = draw_latent_state(
        "dev", 0, "insufficient_funds", episode_cfg, population_cfg
    )
    assert state.card_chargeable is True
    assert state.funds_available_from >= 0.0
    assert math.isfinite(state.funds_available_from)
    assert state.mandate_alive is True
    # Discovered-defect fix, 2026-08-26: see test_card_broken_rows_match_sim_md.
    assert state.blocked_until == 0.0


def test_ambiguous_decline_bernoulli_rate_matches_p_card_cause(configs):
    episode_cfg, population_cfg = configs
    p_card_cause = next(
        c for c in population_cfg["opening_conditions"] if c["key"] == "ambiguous_decline"
    )["p_card_cause"]

    outcomes = [
        draw_latent_state("dev", i, "ambiguous_decline", episode_cfg, population_cfg)
        for i in range(N)
    ]
    observed = sum(1 for o in outcomes if o.card_chargeable) / N
    assert observed == pytest.approx(p_card_cause, abs=0.05)

    # SIM.md §2: card-problem branch (card_chargeable False) gets
    # funds_available_from = day 0, matching the other card-broken rows.
    for o in outcomes:
        if not o.card_chargeable:
            assert o.funds_available_from == 0.0
        assert o.mandate_alive is True
        # Discovered-defect fix, 2026-08-26: see test_card_broken_rows_match_sim_md.
        assert o.blocked_until == 0.0


def test_cancelled_matches_sim_md(configs):
    episode_cfg, population_cfg = configs
    state = draw_latent_state(
        "dev", 0, "subscription_cancelled_by_customer", episode_cfg, population_cfg
    )
    assert state.mandate_alive is False


def test_bank_technical_error_matches_sim_md(configs):
    episode_cfg, population_cfg = configs
    lo, hi = episode_cfg["latent"]["bank_technical_error_clearance"]["support_days"]
    for i in range(50):
        state = draw_latent_state(
            "dev", i, "bank_technical_error", episode_cfg, population_cfg
        )
        assert state.card_chargeable is True
        assert state.funds_available_from == 0.0
        assert state.mandate_alive is True
        assert lo <= state.blocked_until <= hi


@pytest.mark.parametrize("key", ["transaction_limit_exceeded", "payment_risk_check_failed"])
def test_never_blocked_rows_match_sim_md(configs, key):
    episode_cfg, population_cfg = configs
    state = draw_latent_state("dev", 0, key, episode_cfg, population_cfg)
    assert state.card_chargeable is True
    assert state.funds_available_from == 0.0
    assert state.mandate_alive is True
    assert state.blocked_until == BLOCKED_INDEFINITELY


def test_all_nine_opening_conditions_are_covered(configs):
    """Exact set equality against SIM.md §2 / population.yaml, not just
    'enough' coverage."""
    _, population_cfg = configs
    covered = set(_keys(population_cfg))
    expected = {
        "insufficient_funds", "ambiguous_decline", "card_expired",
        "debit_instrument_blocked", "card_not_enabled_group",
        "subscription_cancelled_by_customer", "bank_technical_error",
        "transaction_limit_exceeded", "payment_risk_check_failed",
    }
    assert covered == expected


# -- Balance-restore mixture: weights, moments, and PMF pairing -------------

def test_balance_restore_mixture_weights_recovered(configs):
    episode_cfg, _ = configs
    mixture = episode_cfg["latent"]["balance_restore_delay"]["mixture"]
    transient_weight = mixture["transient"]["weight"]

    salary_draws = 0
    for idx in range(N):
        rng = _BranchTrackingRNG(seed_for_substream("dev", idx, "balance_restore"))
        _sample_balance_restore_delay(rng, episode_cfg)
        if rng.used_salary_branch:
            salary_draws += 1

    observed_transient_weight = (N - salary_draws) / N
    assert observed_transient_weight == pytest.approx(transient_weight, abs=0.03)


def test_balance_restore_salary_cycle_mean_matches_theory(configs):
    """Moment check, not just branch-selection frequency: the salary-cycle
    branch's own output distribution (salary_day + Gamma jitter) must have
    the mean the config implies."""
    episode_cfg, _ = configs
    salary_cfg = episode_cfg["latent"]["balance_restore_delay"]["mixture"]["salary_cycle"]
    pmf = salary_cfg["salary_day_pmf"]
    jitter_mean = salary_cfg["jitter"]["mean_days"]
    theoretical_mean = sum(day * p for day, p in pmf.items()) + jitter_mean

    salary_values = []
    for idx in range(N):
        rng = _BranchTrackingRNG(seed_for_substream("dev", idx, "balance_restore"))
        value = _sample_balance_restore_delay(rng, episode_cfg)
        if rng.used_salary_branch:
            salary_values.append(value)

    assert len(salary_values) > 500  # sanity: enough salary-branch draws in N
    observed_mean = float(np.mean(salary_values))
    assert observed_mean == pytest.approx(theoretical_mean, abs=1.0)


def test_salary_day_pmf_canonicalization_is_sorted_and_paired(configs):
    """_canonical_pmf_arrays must sort by numeric day and keep each day's
    own probability attached to it - not merely reconstruct whatever order
    the dict happened to iterate in (which is what the old version of this
    test did, and which a YAML key reorder would still have passed)."""
    episode_cfg, _ = configs
    salary_cycle = episode_cfg["latent"]["balance_restore_delay"]["mixture"]["salary_cycle"]
    pmf = salary_cycle["salary_day_pmf"]

    days, probs = _canonical_pmf_arrays(pmf)

    assert days == sorted(days)
    assert dict(zip(days, probs)) == pmf
    assert sum(probs) == pytest.approx(1.0, abs=1e-9)


def test_pmf_canonicalization_is_insertion_order_independent():
    """Regression: an equivalent PMF built with keys inserted in a
    different order must canonicalize to identical day/probability arrays.
    Proves the fix actually removes the dict-ordering dependency, rather
    than merely happening to pass because today's config iterates sorted."""
    forward = {1: 0.55, 7: 0.20, 25: 0.10, 30: 0.15}
    reversed_insertion = {30: 0.15, 1: 0.55, 25: 0.10, 7: 0.20}
    shuffled_insertion = {25: 0.10, 30: 0.15, 7: 0.20, 1: 0.55}

    days_a, probs_a = _canonical_pmf_arrays(forward)
    days_b, probs_b = _canonical_pmf_arrays(reversed_insertion)
    days_c, probs_c = _canonical_pmf_arrays(shuffled_insertion)

    assert days_a == days_b == days_c
    assert probs_a == probs_b == probs_c


def test_transient_branch_never_exceeds_support(configs):
    """Inverse-CDF truncation replaces the old rejection loop - confirm it
    actually stays within [lo, hi], not just that it terminates."""
    episode_cfg, _ = configs
    transient = episode_cfg["latent"]["balance_restore_delay"]["mixture"]["transient"]
    lo, hi = transient["support_days"]

    for idx in range(N):
        rng = _BranchTrackingRNG(seed_for_substream("dev", idx, "balance_restore"))
        value = _sample_balance_restore_delay(rng, episode_cfg)
        if not rng.used_salary_branch:
            assert lo <= value <= hi, value


# -- Beta-parameter guards ----------------------------------------------------

def test_beta_parameters_are_valid_for_frozen_config(configs):
    episode_cfg, _ = configs
    for cfg in (
        episode_cfg["latent"]["channel_response_propensity"]["customer_trait"],
        episode_cfg["latent"]["card_change_completion_propensity"],
    ):
        mean, concentration = cfg["mean"], cfg["concentration"]
        assert 0.0 < mean < 1.0
        assert concentration > 0
        assert mean * concentration > 0
        assert (1.0 - mean) * concentration > 0


def test_beta_helper_rejects_invalid_mean():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        _beta_from_mean_concentration(rng, 1.0, 6)
    with pytest.raises(ValueError):
        _beta_from_mean_concentration(rng, 0.0, 6)


def test_beta_helper_rejects_invalid_concentration():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        _beta_from_mean_concentration(rng, 0.5, 0)
    with pytest.raises(ValueError):
        _beta_from_mean_concentration(rng, 0.5, -1)


# -- Substream registry -------------------------------------------------------

def test_substream_names_match_frozen_model_params_registry():
    """model_params.yaml#/sweep/common_random_numbers/substreams is the
    single source of truth. SUBSTREAM_NAMES must be exactly it - no
    invented names, none missing."""
    from rrx.spec.registry import load_registry

    reg = load_registry()
    frozen = set(reg.sweep["common_random_numbers"]["substreams"])
    assert set(SUBSTREAM_NAMES) == frozen


def test_rng_for_substream_rejects_unknown_names():
    from rrx.sim.latent import rng_for_substream

    with pytest.raises(KeyError):
        rng_for_substream("dev", 0, "not_a_real_substream")
