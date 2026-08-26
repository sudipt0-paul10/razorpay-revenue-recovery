"""Per-run manifest writer — restores EVAL.md §6 (eval-spec-v1.3).

The requirement ("Every run writes `results/<run_id>/manifest.json`: git
SHA, spec version, config hash, seed, arm, regime, sweep cell, model
version, timestamp, wall-clock, LLM cost.") was present in EVAL.md from
its first committed version and was deleted, undocumented, in commit
337e0060e9f5af013e4b8362623a06d47a5ee67a. This module reproduces exactly
that eleven-field schema — no field is added, renamed in meaning, or
dropped; field names below are only a snake_case spelling of the same
eleven concepts for JSON/Python use.

Minimal on purpose: this builds and writes the manifest dict only. It does
not decide when a run is "canonical", does not import anything from
`rrx.sim` or `rrx.agent`, and never writes into the repository's real
`results/` directory unless the caller passes that path explicitly — no
A3/evaluation harness exists yet to wire this into.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Exactly the eleven fields EVAL.md §6 names. Adding a twelfth requires
    an EVAL.md §6 amendment first, not a silent extension here."""

    git_sha: str
    spec_version: str
    config_hash: str
    seed: int
    arm: str
    regime: str
    sweep_cell: str
    model_version: str | None
    timestamp: str
    wall_clock_seconds: float
    llm_cost_inr: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def current_git_sha(repo_root: Path | None = None) -> str:
    """git SHA of HEAD. Raises if git is unavailable or this isn't a repo —
    a manifest with a fabricated placeholder SHA would be worse than no
    manifest at all."""
    cwd = repo_root or Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def config_hash(*config_paths: Path) -> str:
    """sha256 over the concatenated bytes of the given config file(s), in
    the order given. Which configs are in scope for a run (episode.yaml,
    population.yaml, model_params.yaml, costs.yaml, ...) is the caller's
    decision, not this function's."""
    digest = hashlib.sha256()
    for p in config_paths:
        digest.update(Path(p).read_bytes())
    return digest.hexdigest()


def write_manifest(manifest: RunManifest, run_id: str, results_dir: Path) -> Path:
    """Writes <results_dir>/<run_id>/manifest.json. `results_dir` is always
    supplied by the caller — never defaulted to the repository's real
    `results/` — so exercising or testing this function cannot produce a
    canonical-looking artifact."""
    run_dir = Path(results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "manifest.json"
    out_path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return out_path
