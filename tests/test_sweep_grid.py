"""Sweep-grid readiness.

The second half of the old test_model_params_swept.py. Asserts that every
specified parameter actually reaches the grid, that cell ids are unique,
and that the majority threshold is fixed arithmetically rather than
chosen after the run.
"""

import pytest

from rrx.spec.registry import (
    CANONICAL_MODEL_PARAMS,
    enumerate_cells,
    load_registry,
    required_wins,
)

reg = load_registry()
cells = enumerate_cells(reg)


def test_every_specified_parameter_reaches_the_grid():
    covered = {c.parameter for c in cells}
    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        if p["status"] == "specified" and p["sweep"].get("swept"):
            assert name in covered, f"{name} declared swept but has no cells"


def test_no_parameter_is_unspecified_before_freeze():
    """Locked decision 11 specified all four remaining latents. If any
    reverts to unspecified, sim-v1 cannot freeze and EVAL.md §8.1's
    ordering (simulator frozen before any agent policy) breaks."""
    assert reg.unspecified() == {}, (
        f"still unspecified: {sorted(reg.unspecified())}"
    )


def test_cell_ids_unique():
    ids = [c.cell_id for c in cells]
    assert len(ids) == len(set(ids))


def test_cell_count_matches_locked_design():
    """22 with the topup toggle off; 24 with it on (DEFECT 1)."""
    expected = 24 if reg.sweep["include_topup_acceleration_cells"] else 22
    assert len(cells) == expected, (
        f"{len(cells)} cells, expected {expected}. "
        "Changing the count changes the pass mark - update EVAL.md §8.2."
    )


def test_failure_mix_contributes_twelve_cells():
    """Six buckets x two directions (locked decision 3)."""
    n = len([c for c in cells if c.parameter == "failure_mix_weights"])
    assert n == 12


def test_required_wins_is_ceil_of_eighty_percent():
    """Locked decision 5. Pinned here so the pass mark cannot be chosen
    after seeing which cells failed."""
    assert required_wins(22, reg) == 18
    assert required_wins(24, reg) == 20
    assert required_wins(len(cells), reg) == (
        20 if len(cells) == 24 else 18
    )


def test_low_information_cells_stay_in_denominator():
    """Locked decision 13: the wait and escalate buckets are swept and
    kept in the denominator, flagged rather than dropped."""
    low = {c.cell_id for c in cells if c.low_information}
    assert len(low) == 4, low
    assert all(("wait" in c or "escalate" in c) for c in low)


@pytest.mark.parametrize("name", [
    n for n in CANONICAL_MODEL_PARAMS if n != "failure_mix_weights"
])
def test_scalar_handles_have_two_directional_cells(name):
    got = sorted(c.direction for c in cells
                 if c.parameter == name and c.handle != "p_topup_action")
    assert got == ["high", "low"]


def test_scalar_cells_are_thirty_percent_from_baseline():
    """Guards against a baseline being edited without its cells."""
    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        if p["kind"] in ("vector_simplex", "composite"):
            continue
        base = p["handle"]["baseline"]
        mag = p["sweep"]["magnitude"]
        assert p["sweep"]["cells"]["low"] == pytest.approx(base * (1 - mag), rel=1e-6)
        assert p["sweep"]["cells"]["high"] == pytest.approx(base * (1 + mag), rel=1e-6)


def test_composite_hazard_cells_scale_both_components():
    """Locked decision 9: one joint multiplier on hazard and lifetime."""
    p = reg.parameters["cancellation_hazard_and_ltv"]
    d = p["definition"]
    mag = p["sweep"]["magnitude"]
    h0 = d["hazard_per_contact"]["h0"]
    cyc = d["remaining_lifetime_cycles"]["mean_cycles"]
    for direction, f in (("low", 1 - mag), ("high", 1 + mag)):
        cell = p["sweep"]["cells"][direction]
        assert cell["hazard_h0"] == pytest.approx(h0 * f, rel=1e-6)
        assert cell["remaining_lifetime_mean_cycles"] == pytest.approx(cyc * f, rel=1e-6)


def test_probability_cells_within_clamp():
    lo, hi = reg.sweep["probability_clamp"]
    for name in ("channel_response_propensity",
                 "card_change_completion_propensity",
                 "balance_restore_timing"):
        for v in reg.parameters[name]["sweep"]["cells"].values():
            assert lo <= v <= hi, f"{name}: {v} outside clamp"
