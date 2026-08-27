"""Task 4A file-plan correction: src/rrx/harness/ needs full rrx.sim
access (it drives the day loop and must obtain a LatentState via
_EpisodeState's construction) and is deliberately NOT a member of
tests/test_no_latent_leak.py's GUARDED_PACKAGES - that locked file is not
modified by this task.

This is a NEW test, narrower and appropriate to harness code: the
harness's own import statements must never directly name
rrx.sim.latent - only rrx.sim.engine / rrx.sim.cohort / rrx.sim.rng.
src/rrx/harness/runner.py obtains draw_latent_state and MASTER_SEED via
rrx.sim.engine's own re-export instead, keeping the harness's coupling to
raw latent-state access minimal even though it legitimately needs full
rrx.sim mechanics otherwise.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
HARNESS_DIR = SRC / "rrx" / "harness"
FORBIDDEN = ("rrx.sim.latent",)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import, not a rrx.* path
                continue
            mod = node.module or ""
            names.add(mod)
    return names


def _violates(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in FORBIDDEN)


def _harness_source_files() -> list[Path]:
    if not HARNESS_DIR.is_dir():
        return []
    return sorted(HARNESS_DIR.rglob("*.py"))


def test_harness_package_exists():
    assert HARNESS_DIR.is_dir(), "src/rrx/harness missing - Task 4A creates it."


@pytest.mark.parametrize(
    "path", _harness_source_files() or [pytest.param(None, marks=pytest.mark.skip(
        reason="no source files in rrx/harness yet"))],
    ids=lambda p: str(p.relative_to(SRC)) if p else "none",
)
def test_harness_never_imports_rrx_sim_latent_directly(path):
    bad = sorted(n for n in _imported_modules(path) if _violates(n))
    assert not bad, (
        f"{path.relative_to(SRC)} imports {bad} directly. The harness obtains "
        "latent-drawing functionality (draw_latent_state, MASTER_SEED) via "
        "rrx.sim.engine's own re-export, not by naming rrx.sim.latent directly."
    )
