"""Stage 7.4: focused tests for `src/rrx/spec/sensitivity_doc.py`, the
generator that fixes `results/sensitivity.md`'s stale 22-cell structure.

Covers exactly what the stage's objective requires:
1. the registry enumerates 26 cells (already pinned by the locked
   `tests/test_model_params_swept.py::test_cell_count_matches_locked_design`
   — reasserted here as this module's own precondition, not a duplicate
   claim of authority over that number);
2. the generated documentation reports 26 cells;
3. the 80% pass criterion is represented as 21/26;
4. cell membership in the generated doc is exactly `enumerate_cells()`'s
   own membership — no invented, dropped, or reordered cell.

No experiment result is asserted anywhere here: every outcome column
this module renders is the literal string "PENDING", and these tests
check exactly that, never a fabricated win/loss.
"""

from __future__ import annotations

import re

from rrx.spec.registry import enumerate_cells, load_registry, required_wins
from rrx.spec.sensitivity_doc import PENDING, main, render_sensitivity_md

REG = load_registry()
CELLS = enumerate_cells(REG)


def test_registry_enumerates_26_cells():
    """Precondition this module depends on - pinned independently of, but
    consistent with, the locked test_model_params_swept.py assertion."""
    assert len(CELLS) == 26


def test_rendered_doc_reports_26_total_cells():
    doc = render_sensitivity_md(REG)
    assert "Pass mark: 21 / 26 cells" in doc
    assert "Cells won: PENDING / 26. Pass mark 21." in doc


def test_eighty_percent_pass_criterion_is_21_of_26():
    assert required_wins(26, REG) == 21
    doc = render_sensitivity_md(REG)
    assert "21 / 26" in doc
    assert "18 / 22" not in doc
    assert "/ 22" not in doc


def test_rendered_table_has_exactly_26_data_rows():
    doc = render_sensitivity_md(REG)
    lines = doc.splitlines()
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.startswith("| cell_id |")
    )
    # header line + separator line, then exactly 26 data rows before the
    # blank line that ends the table.
    data_rows = []
    for ln in lines[header_idx + 2:]:
        if not ln.startswith("|"):
            break
        data_rows.append(ln)
    assert len(data_rows) == 26


def test_rendered_cell_ids_match_enumerate_cells_exactly_and_in_order():
    """The generated doc must not add, drop, or reorder a single cell
    relative to enumerate_cells()'s own output - the exact property Stage
    7.4 requires ('cell membership remains exactly the membership already
    produced by enumerate_cells()')."""
    doc = render_sensitivity_md(REG)
    rendered_ids = re.findall(r"^\| `([^`]+)` \|", doc, flags=re.MULTILINE)
    expected_ids = [c.cell_id for c in CELLS]
    assert rendered_ids == expected_ids


def test_no_experiment_result_is_fabricated():
    """Every outcome column (clamped / invoice CI / rescue CI / win) is
    PENDING for every single row - no win/loss is ever invented by this
    generator, since no real dev-split sweep has been executed."""
    doc = render_sensitivity_md(REG)
    data_rows = [ln for ln in doc.splitlines() if ln.startswith("| `")]
    assert len(data_rows) == 26
    for row in data_rows:
        cols = [c.strip() for c in row.strip("|").split("|")]
        # cols: cell_id, parameter, handle, dir, clamped, invoice CI, rescue CI, win, low-info
        clamped, invoice_ci, rescue_ci, win = cols[4], cols[5], cols[6], cols[7]
        assert clamped == PENDING
        assert invoice_ci == PENDING
        assert rescue_ci == PENDING
        assert win == PENDING


def test_low_information_cells_flagged_exactly_where_the_registry_says():
    doc = render_sensitivity_md(REG)
    data_rows = [ln for ln in doc.splitlines() if ln.startswith("| `")]
    rendered_low_info = {
        cols[0].strip("` ")
        for row in data_rows
        for cols in [[c.strip() for c in row.strip("|").split("|")]]
        if cols[8] == "yes"
    }
    expected_low_info = {c.cell_id for c in CELLS if c.low_information}
    assert rendered_low_info == expected_low_info
    assert len(expected_low_info) == 4  # locked decision 13, unchanged


def test_main_writes_the_regenerated_file_deterministically(tmp_path):
    out_path = tmp_path / "sensitivity.md"
    returned = main(output_path=out_path)
    assert returned == out_path
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert content == render_sensitivity_md(REG)


def test_generator_never_touches_the_real_registry_or_configs(tmp_path):
    """The generator is read-only with respect to configs/model_params.yaml
    - it must be safe to call repeatedly without perturbing the frozen
    sweep grid it reads from."""
    before = enumerate_cells(load_registry())
    main(output_path=tmp_path / "sensitivity.md")
    after = enumerate_cells(load_registry())
    assert [c.cell_id for c in before] == [c.cell_id for c in after]
