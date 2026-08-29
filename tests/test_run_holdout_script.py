"""Focused tests for scripts/run_holdout.py (Day 8 §C3 guarded entry point).

scripts/ is not part of the rrx package and has no __init__.py, so the
script is loaded by file path rather than by package import - the same
approach used to test any standalone script in this repository's layout.

All git/filesystem/simulation interaction is mocked; no test in this file
touches the real git repository state, the real results/ directory, or
calls holdout_indices(authorized=True) against the real guard for
anything other than the one direct, isolated check in
test_no_direct_reconstruction_of_holdout_range.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_holdout.py"


def _load_run_holdout():
    spec = importlib.util.spec_from_file_location("run_holdout_script_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_holdout = _load_run_holdout()


def _make_fake_git(*, head=None, freeze=None, spec=None, status=""):
    """Builds a fake `_git(*args)` matching run_holdout's own call shape."""
    head = head or run_holdout.IMPLEMENTATION_SHA
    freeze = freeze or run_holdout.CODE_FREEZE_HOLDOUT_SHA
    spec = spec or run_holdout.EVAL_SPEC_V1_10_SHA

    def _fake_git(*args):
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("rev-parse", "code-freeze-holdout^{commit}"):
            return freeze
        if args == ("rev-parse", "eval-spec-v1.10^{commit}"):
            return spec
        if args == ("status", "--porcelain"):
            return status
        raise AssertionError(f"unexpected _git call: {args}")

    return _fake_git


def _boom_if_called(name):
    def _fn(*args, **kwargs):
        raise AssertionError(f"{name} must not be called on this path")
    return _fn


# ---------------------------------------------------------------------------
# 1. Refusal without the authorization flag
# ---------------------------------------------------------------------------

def test_refuses_without_authorization_flag(monkeypatch, capsys):
    monkeypatch.setattr(run_holdout, "_git", _boom_if_called("_git"))
    monkeypatch.setattr(run_holdout, "holdout_indices", _boom_if_called("holdout_indices"))
    monkeypatch.setattr(run_holdout, "run_official_arm", _boom_if_called("run_official_arm"))

    exit_code = run_holdout.main([])

    assert exit_code == 2
    assert "authorized" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------------------
# 2. Refusal on a dirty working tree
# ---------------------------------------------------------------------------

def test_refuses_on_dirty_working_tree(monkeypatch, tmp_path):
    monkeypatch.setattr(run_holdout, "_git", _make_fake_git(status=" M EVAL.md\n"))
    monkeypatch.setattr(run_holdout, "holdout_indices", _boom_if_called("holdout_indices"))
    monkeypatch.setattr(run_holdout, "run_official_arm", _boom_if_called("run_official_arm"))
    monkeypatch.setattr(run_holdout, "HOLDOUT_OUTPUT_ROOT", tmp_path / "holdout-out")

    exit_code = run_holdout.main(["--i-have-authorized-the-holdout"])

    assert exit_code == 1


# ---------------------------------------------------------------------------
# 3. Refusal on the wrong HEAD
# ---------------------------------------------------------------------------

def test_refuses_on_wrong_head(monkeypatch, tmp_path):
    monkeypatch.setattr(run_holdout, "_git", _make_fake_git(head="0" * 40))
    monkeypatch.setattr(run_holdout, "holdout_indices", _boom_if_called("holdout_indices"))
    monkeypatch.setattr(run_holdout, "run_official_arm", _boom_if_called("run_official_arm"))
    monkeypatch.setattr(run_holdout, "HOLDOUT_OUTPUT_ROOT", tmp_path / "holdout-out")

    exit_code = run_holdout.main(["--i-have-authorized-the-holdout"])

    assert exit_code == 1


def test_refuses_on_wrong_freeze_or_spec_tag(monkeypatch, tmp_path):
    monkeypatch.setattr(run_holdout, "_git", _make_fake_git(freeze="1" * 40))
    monkeypatch.setattr(run_holdout, "holdout_indices", _boom_if_called("holdout_indices"))
    monkeypatch.setattr(run_holdout, "run_official_arm", _boom_if_called("run_official_arm"))
    monkeypatch.setattr(run_holdout, "HOLDOUT_OUTPUT_ROOT", tmp_path / "holdout-out")

    assert run_holdout.main(["--i-have-authorized-the-holdout"]) == 1

    monkeypatch.setattr(run_holdout, "_git", _make_fake_git(spec="2" * 40))
    assert run_holdout.main(["--i-have-authorized-the-holdout"]) == 1


# ---------------------------------------------------------------------------
# 4. Refusal when output already contains a run for this arm
# ---------------------------------------------------------------------------

def test_refuses_when_output_already_contains_a_run(monkeypatch, tmp_path):
    monkeypatch.setattr(run_holdout, "_git", _make_fake_git())
    monkeypatch.setattr(run_holdout, "holdout_indices", _boom_if_called("holdout_indices"))
    monkeypatch.setattr(run_holdout, "run_official_arm", _boom_if_called("run_official_arm"))

    output_root = tmp_path / "holdout-out"
    output_root.mkdir()
    (output_root / "a0").mkdir()  # pre-existing directory for one arm
    monkeypatch.setattr(run_holdout, "HOLDOUT_OUTPUT_ROOT", output_root)

    exit_code = run_holdout.main(["--i-have-authorized-the-holdout"])

    assert exit_code == 1


def test_verify_no_existing_run_directories_passes_when_clean(tmp_path):
    output_root = tmp_path / "holdout-out"
    output_root.mkdir()
    # Should not raise - none of the five arm subdirectories exist.
    run_holdout.verify_no_existing_run_directories(output_root, run_holdout.HOLDOUT_ARMS)


# ---------------------------------------------------------------------------
# 5. Exactly one `authorized=True` call site exists outside tests
# ---------------------------------------------------------------------------

def _authorized_true_call_lines(py_file: Path) -> list[int]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if (
                    kw.arg == "authorized"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    lines.append(node.lineno)
    return lines


def test_exactly_one_authorized_true_call_site_outside_tests():
    hits: dict[Path, list[int]] = {}
    for py_file in REPO_ROOT.rglob("*.py"):
        parts = py_file.relative_to(REPO_ROOT).parts
        if parts[0] in (".venv", "tests") or "__pycache__" in parts:
            continue
        call_lines = _authorized_true_call_lines(py_file)
        if call_lines:
            hits[py_file.relative_to(REPO_ROOT)] = call_lines

    assert set(hits) == {Path("scripts/run_holdout.py")}, (
        f"unexpected file(s) with a real authorized=True call site: {hits}"
    )
    assert len(hits[Path("scripts/run_holdout.py")]) == 1, (
        f"expected exactly one authorized=True call site, found: {hits}"
    )


# ---------------------------------------------------------------------------
# 6. Correct five-arm list
# ---------------------------------------------------------------------------

def test_holdout_arms_match_eval_md_section_7_1_item_a():
    from rrx.eval.arms import ARM_A0, ARM_A1, ARM_A2_STRENGTHENED, ARM_A3D, ARM_A4

    assert run_holdout.HOLDOUT_ARMS == (ARM_A0, ARM_A1, ARM_A2_STRENGTHENED, ARM_A3D, ARM_A4)
    for excluded in ("A3-LLM", "A1-U", "A2", "A2_CORRECTED_V1"):
        assert excluded not in run_holdout.HOLDOUT_ARMS


# ---------------------------------------------------------------------------
# 7. Correct master seed / split
# ---------------------------------------------------------------------------

def test_master_seed_and_split_are_correct():
    assert run_holdout.MASTER_SEED == 20260825
    assert run_holdout.HOLDOUT_SPLIT == "holdout"


# ---------------------------------------------------------------------------
# 8. No direct reconstruction of the holdout range
# ---------------------------------------------------------------------------

def test_no_direct_reconstruction_of_holdout_range():
    """AST-based, not a raw substring search: the module docstring itself
    names range(9000, 11000) as the exact thing NOT to do, which a plain
    `"range(9000" not in source` check would misfire on. What must never
    exist is an actual `range(...)` CALL seeded with the holdout start
    index anywhere in the executable code."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SCRIPT_PATH))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "range"
        ):
            first_arg = node.args[0] if node.args else None
            if isinstance(first_arg, ast.Constant) and first_arg.value == 9000:
                pytest.fail(f"found a real range(9000, ...) call at line {node.lineno}")

    assert "holdout_indices(authorized=True)" in source


# ---------------------------------------------------------------------------
# Extra: end-to-end orchestration, fully mocked (no real git/filesystem/sim)
# ---------------------------------------------------------------------------

def test_main_happy_path_calls_all_five_arms_correctly(monkeypatch, tmp_path):
    calls = []

    def fake_run_official_arm(arm, run_id, *, results_dir, indices, master_seed, split):
        calls.append(dict(
            arm=arm, run_id=run_id, results_dir=results_dir,
            indices=indices, master_seed=master_seed, split=split,
        ))

    monkeypatch.setattr(run_holdout, "_git", _make_fake_git())
    monkeypatch.setattr(run_holdout, "holdout_indices", lambda *, authorized: range(9000, 9010))
    monkeypatch.setattr(run_holdout, "run_official_arm", fake_run_official_arm)
    output_root = tmp_path / "holdout-out"
    monkeypatch.setattr(run_holdout, "HOLDOUT_OUTPUT_ROOT", output_root)
    log_path = tmp_path / "holdout_runs.md"
    log_path.write_text("# Holdout run log\n")
    monkeypatch.setattr(run_holdout, "HOLDOUT_LOG_PATH", log_path)

    exit_code = run_holdout.main(["--i-have-authorized-the-holdout"])

    assert exit_code == 0
    assert [c["arm"] for c in calls] == list(run_holdout.HOLDOUT_ARMS)
    for c in calls:
        assert c["split"] == "holdout"
        assert c["master_seed"] == 20260825
        assert list(c["indices"]) == list(range(9000, 9010))
        assert c["results_dir"] == output_root
    assert len({c["run_id"] for c in calls}) == 5  # all unique

    log_text = log_path.read_text()
    assert "Holdout execution session started" in log_text
    assert log_text.count("status=COMPLETE") == 5


def test_main_logs_and_reraises_on_arm_crash(monkeypatch, tmp_path):
    def crashing_run_official_arm(arm, run_id, **kwargs):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(run_holdout, "_git", _make_fake_git())
    monkeypatch.setattr(run_holdout, "holdout_indices", lambda *, authorized: range(9000, 9010))
    monkeypatch.setattr(run_holdout, "run_official_arm", crashing_run_official_arm)
    monkeypatch.setattr(run_holdout, "HOLDOUT_OUTPUT_ROOT", tmp_path / "holdout-out")
    log_path = tmp_path / "holdout_runs.md"
    log_path.write_text("# Holdout run log\n")
    monkeypatch.setattr(run_holdout, "HOLDOUT_LOG_PATH", log_path)

    with pytest.raises(RuntimeError, match="simulated crash"):
        run_holdout.main(["--i-have-authorized-the-holdout"])

    assert "status=CRASHED" in log_path.read_text()
