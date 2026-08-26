"""Sweep-grid readiness.

The second half of the old test_model_params_swept.py. Asserts that every
specified parameter actually reaches the grid, that cell ids are unique,
and that the majority threshold is fixed arithmetically rather than
chosen after the run.

eval-spec-v1.1 (2026-08-26): the cell count moved from 22 to 26. This is an
INCREASE in sweep coverage, not a relaxation - the previous count of 22
omitted two [MODEL] parameters (ambiguous_cause_split, transient_block_
clearance) that were marked sweep_required: true but nested inside a
definition: block that enumerate_cells() did not read, so they silently
contributed zero cells. Nothing here was loosened to make a run go green;
the grid got bigger because two magnitudes that should always have been in
it now are.
"""

import copy

import pytest

from rrx.spec.registry import (
    CANONICAL_MODEL_PARAMS,
    Registry,
    enumerate_cells,
    find_sweep_required_nodes,
    load_registry,
    required_wins,
    unswept_required_entries,
)

reg = load_registry()
cells = enumerate_cells(reg)


def _resolve_definition_node(reg, parameter, path):
    """Walk a dotted path (from find_sweep_required_nodes) down a
    parameter's definition: block to the actual node dict."""
    node = reg.parameters[parameter]["definition"]
    for key in path.split("."):
        node = node[key]
    return node


def _mismatched_sweep_required_cells(reg):
    """'{parameter}.{path}' for every definition-nested sweep_required node
    whose cells are not +/-30% from its own declared baseline.

    Companion to test_scalar_cells_are_thirty_percent_from_baseline's
    top-level loop, which reads only p["handle"]["baseline"] / p["sweep"] -
    invisible to anything nested inside definition:, which is exactly the
    blindness find_sweep_required_nodes() was written to fix. A list-valued
    cell (transient_block_clearance's [lower, upper] day bounds) is checked
    on its upper bound only - see the docstring on the caller for why.
    """
    mismatched = []
    for name, path in find_sweep_required_nodes(reg):
        node = _resolve_definition_node(reg, name, path)
        sweep = node.get("sweep") or {}
        node_cells = sweep.get("cells")
        if not node_cells:
            continue  # the zero-cells case is unswept_required_entries's job
        mag = sweep["magnitude"]
        handle = sweep.get("handle", path)
        low, high = node_cells.get("low"), node_cells.get("high")
        if isinstance(low, list):
            base = node["support_days"][1]
            got_low, got_high = low[1], high[1]
        else:
            base = node[handle]
            got_low, got_high = low, high
        want_low, want_high = base * (1 - mag), base * (1 + mag)
        if (got_low != pytest.approx(want_low, rel=1e-6)
                or got_high != pytest.approx(want_high, rel=1e-6)):
            mismatched.append(f"{name}.{path}")
    return mismatched


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
    """26 with the topup toggle off; 28 with it on (DEFECT 1).

    eval-spec-v1.1: was 22/24. The +4 is ambiguous_cause_split (low, high)
    and transient_block_clearance (low, high) - two Q1 gap-resolution
    [MODEL] magnitudes that were marked sweep_required: true from the start
    but, until this fix, contributed no cells. See module docstring."""
    expected = 28 if reg.sweep["include_topup_acceleration_cells"] else 26
    assert len(cells) == expected, (
        f"{len(cells)} cells, expected {expected}. "
        "Changing the count changes the pass mark - update EVAL.md §8.2."
    )


def test_failure_mix_contributes_fourteen_cells():
    """Six buckets x two directions (locked decision 3), plus
    ambiguous_cause_split's own two directional cells (eval-spec-v1.1)."""
    n = len([c for c in cells if c.parameter == "failure_mix_weights"])
    assert n == 14


def test_required_wins_is_ceil_of_eighty_percent():
    """Locked decision 5. Pinned here so the pass mark cannot be chosen
    after seeing which cells failed."""
    assert required_wins(26, reg) == 21
    assert required_wins(28, reg) == 23
    assert required_wins(len(cells), reg) == (
        23 if len(cells) == 28 else 21
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
    """Every distinct handle under a parameter contributes exactly one low
    and one high cell - checked per handle, not per parameter, because
    eval-spec-v1.1 gives balance_restore_timing a second independent handle
    (transient_block_clearance) alongside its top-level salary_mode_mass."""
    handles = {c.handle for c in cells if c.parameter == name}
    for handle in handles:
        got = sorted(c.direction for c in cells
                     if c.parameter == name and c.handle == handle)
        assert got == ["high", "low"], f"{name}.{handle}: {got}"


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

    # eval-spec-v1.1: the loop above reads only a parameter's top-level
    # handle/sweep, so a scalar magnitude nested inside definition: (e.g.
    # ambiguous_cause_split.p_card_cause) was invisible to this check - the
    # same blindness find_sweep_required_nodes() exists to fix, left in
    # place here until now. transient_block_clearance's cells are [lower,
    # upper] day-bound lists rather than a bare scalar (option 2a, chosen
    # over a silent exemption): the +/-30% check applies to the upper bound
    # against the baseline's own upper bound, since the lower bound is fixed
    # at 0 by design and is not what the magnitude sweeps.
    mismatched = _mismatched_sweep_required_cells(reg)
    assert mismatched == [], (
        f"definition-nested sweep_required cells not +/-30% from baseline: "
        f"{mismatched}"
    )


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

    # eval-spec-v1.1: same blindness as test_scalar_cells_are_thirty_percent_
    # from_baseline - the loop above reads only top-level sweep.cells, so a
    # probability-valued nested magnitude (ambiguous_cause_split.p_card_cause)
    # was invisible here too. transient_block_clearance's cells are
    # day-count bounds, not probabilities (its low/high are [0, 1.4] /
    # [0, 2.6] lists) - a day count of 2.6 failing a [0, 1] clamp would be a
    # false positive, not a real defect, so list-valued cells are explicitly
    # skipped rather than checked against a clamp that does not apply to them.
    for name, path in find_sweep_required_nodes(reg):
        node = _resolve_definition_node(reg, name, path)
        node_cells = (node.get("sweep") or {}).get("cells") or {}
        if not node_cells or isinstance(node_cells.get("low"), list):
            continue
        for v in node_cells.values():
            assert lo <= v <= hi, f"{name}.{path}: {v} outside clamp"


def test_all_sweep_required_entries_produce_cells():
    """EVAL.md §0: every [MODEL] magnitude must reach the sweep grid,
    including one nested inside a definition: block. This is the check
    today's bug needed: ambiguous_cause_split and transient_block_clearance
    were both marked sweep_required: true in configs/model_params.yaml but
    enumerate_cells() did not read anything inside definition:, so they
    silently contributed zero cells and no prior test noticed."""
    missing = unswept_required_entries(reg, cells)
    assert missing == [], (
        f"sweep_required: true but zero cells in enumerate_cells(): {missing}"
    )


def test_sweep_required_with_zero_cells_is_detected():
    """Regression test for today's bug, reproduced on a synthetic registry
    rather than the real config - proves the detection mechanism itself
    works, not just that today's two entries happen to be fixed now.

    Grafts a sweep_required: true node with no sweep.cells onto a real,
    valid parameter (invoice_amount) and asserts unswept_required_entries
    reports exactly that node. Before this fix, enumerate_cells() had no
    code path that read anything under definition: at all (other than the
    special-cased, opt-in topup_acceleration block), so a node in this
    exact shape would have passed silently."""
    broken_params = copy.deepcopy(dict(reg.raw["parameters"]))
    broken_params["invoice_amount"]["definition"] = {
        "orphaned_gap_param": {
            "value": 1.0,
            "sweep_required": True,
            # deliberately no "sweep" key - this is today's exact bug shape
        },
    }
    broken_reg = Registry({"sweep": reg.raw["sweep"], "parameters": broken_params})
    broken_cells = enumerate_cells(broken_reg)

    missing = unswept_required_entries(broken_reg, broken_cells)
    assert missing == ["invoice_amount.orphaned_gap_param"], missing


def test_thirty_percent_check_catches_a_bad_definition_nested_cell():
    """Regression, same shape as test_sweep_required_with_zero_cells_is_
    detected above: proves _mismatched_sweep_required_cells actually catches
    a definition-nested scalar cell that has drifted off its +/-30%
    baseline, not just that today's two real entries currently happen to be
    correct. Before this turn's fix, neither
    test_scalar_cells_are_thirty_percent_from_baseline nor
    test_probability_cells_within_clamp looked inside definition: at all, so
    a corrupted cell in this exact shape would have passed both silently."""
    broken_params = copy.deepcopy(dict(reg.raw["parameters"]))
    broken_params["failure_mix_weights"]["definition"]["ambiguous_cause_split"][
        "sweep"]["cells"]["high"] = 0.99  # should be 0.65 (0.50 * 1.30)
    broken_reg = Registry({"sweep": reg.raw["sweep"], "parameters": broken_params})

    mismatched = _mismatched_sweep_required_cells(broken_reg)
    assert mismatched == ["failure_mix_weights.ambiguous_cause_split"], mismatched
