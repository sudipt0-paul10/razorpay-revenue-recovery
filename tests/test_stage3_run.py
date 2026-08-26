"""Day 2 Stage 3, test item 17: paired A0/A2 metric calculation and CI."""

from __future__ import annotations

import numpy as np
import pytest

from rrx.sim.latent import load_configs
from rrx.sim.run_stage3 import paired_bootstrap_ci, run_batch


def test_paired_bootstrap_ci_recovers_a_known_constant_difference():
    """If A2 always beats A0 by exactly 0.3 on every episode, the point
    estimate must be exactly 0.3 and the CI must exclude zero."""
    rng = np.random.default_rng(0)
    a0 = rng.random(500).tolist()
    a2 = [x + 0.3 for x in a0]
    point, lo, hi = paired_bootstrap_ci(a0, a2, n_resamples=2000)
    assert point == pytest.approx(0.3, abs=1e-9)
    assert lo > 0
    assert hi > 0


def test_paired_bootstrap_ci_includes_zero_when_arms_are_identical():
    rng = np.random.default_rng(1)
    a0 = rng.random(500).tolist()
    a2 = list(a0)  # identical, paired
    point, lo, hi = paired_bootstrap_ci(a0, a2, n_resamples=2000)
    assert point == pytest.approx(0.0, abs=1e-12)
    assert lo <= 0.0 <= hi


def test_paired_bootstrap_ci_is_deterministic():
    rng = np.random.default_rng(2)
    a0 = rng.random(300).tolist()
    a2 = (rng.random(300) + 0.1).tolist()
    r1 = paired_bootstrap_ci(a0, a2, n_resamples=1000)
    r2 = paired_bootstrap_ci(a0, a2, n_resamples=1000)
    assert r1 == r2


def test_paired_bootstrap_ci_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        paired_bootstrap_ci([1.0, 2.0], [1.0])


def test_run_batch_produces_paired_same_length_arms():
    episode_cfg, population_cfg = load_configs()
    batch = run_batch("dev", range(1000, 1050), episode_cfg, population_cfg)
    assert len(batch.a0) == len(batch.a2) == 50
    for a0_r, a2_r in zip(batch.a0, batch.a2):
        assert a0_r.opening_condition_key == a2_r.opening_condition_key
        assert a0_r.invoice_amount_inr == a2_r.invoice_amount_inr
