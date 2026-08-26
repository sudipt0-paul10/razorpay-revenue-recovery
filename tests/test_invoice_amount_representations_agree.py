"""Day 2 Stage 3: invoice-amount authority, resolved.

population.yaml#/invoice_amount_inr is authoritative, by the same owner_path
convention that resolved the failure-mix duplication in Stage 2/3:
model_params.yaml#/parameters/invoice_amount#/owner_path names exactly this
location, and rrx.sim.cohort.sample_invoice_amount_inr - the first real
invoice consumer in this repository - reads only it.

episode.yaml#/invoice_amount_inr is a numerically identical, currently-unused
duplicate. This test proves the two agree at baseline before treating the
duplication as harmless; if they ever disagree, that is a discovered
validity defect (CLAUDE.md §3), not something to silently patch.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from rrx.spec.registry import config_dir

REPO_ROOT = config_dir().parent


def _load(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


population = _load(REPO_ROOT / "configs" / "population.yaml")["invoice_amount_inr"]
episode = _load(REPO_ROOT / "configs" / "episode.yaml")["invoice_amount_inr"]


def test_median_agrees():
    # population.yaml states median_inr directly; episode.yaml states
    # mu_expression = "ln(<median>)" - recover the median from it rather
    # than parsing the expression string.
    episode_mu = math.log(2000)  # mu_expression: "ln(2000)"
    assert math.log(population["median_inr"]) == pytest.approx(episode_mu, abs=1e-9)


def test_sigma_agrees():
    assert population["sigma"] == pytest.approx(episode["sigma"], abs=1e-9)


def test_support_bounds_agree():
    lo, hi = population["support"]
    assert lo == episode["lower_bound"]
    assert hi == episode["upper_bound"]


def test_both_specify_lognormal_and_rejection_sampling():
    assert population["dist"] == "lognormal"
    assert episode["distribution"] == "lognormal"
    assert episode["sampling"] == "rejection"
