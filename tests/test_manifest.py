"""Day 3: tests for the restored per-run manifest writer (EVAL.md §6,
eval-spec-v1.3). Verifies the schema matches the historical eleven-field
spec exactly and that writing a manifest never touches the repository's
real results/ directory."""

from __future__ import annotations

import json
from pathlib import Path

from rrx.spec.manifest import RunManifest, config_hash, current_git_sha, write_manifest

REQUIRED_FIELDS = (
    "git_sha",
    "spec_version",
    "config_hash",
    "seed",
    "arm",
    "regime",
    "sweep_cell",
    "model_version",
    "timestamp",
    "wall_clock_seconds",
    "llm_cost_inr",
)


def _sample_manifest() -> RunManifest:
    return RunManifest(
        git_sha="deadbeef",
        spec_version="eval-spec-v1.3",
        config_hash="cafef00d",
        seed=20260825,
        arm="A0",
        regime="B",
        sweep_cell="baseline",
        model_version=None,
        timestamp="2026-08-26T00:00:00+05:30",
        wall_clock_seconds=1.23,
        llm_cost_inr=None,
    )


def test_manifest_has_exactly_the_historical_ten_fields():
    d = _sample_manifest().to_dict()
    assert set(d.keys()) == set(REQUIRED_FIELDS), (
        f"manifest schema drifted from the restored EVAL.md §6 spec: {sorted(d.keys())}"
    )


def test_write_manifest_writes_expected_path_and_content(tmp_path):
    manifest = _sample_manifest()
    out_path = write_manifest(manifest, run_id="test-run-001", results_dir=tmp_path)

    assert out_path == tmp_path / "test-run-001" / "manifest.json"
    assert out_path.exists()

    loaded = json.loads(out_path.read_text())
    assert loaded == manifest.to_dict()


def test_write_manifest_never_touches_real_results_dir(tmp_path):
    """results_dir is always explicit - calling write_manifest without
    pointing it at the repo's real results/ directory must not create
    anything there."""
    import rrx.spec.manifest as manifest_module

    real_results = Path(manifest_module.__file__).resolve().parents[3] / "results"
    before = set(real_results.iterdir()) if real_results.exists() else set()

    write_manifest(_sample_manifest(), run_id="scratch", results_dir=tmp_path)

    after = set(real_results.iterdir()) if real_results.exists() else set()
    assert before == after


def test_current_git_sha_is_a_real_hex_sha():
    sha = current_git_sha()
    assert len(sha) == 40
    int(sha, 16)  # raises ValueError if not hex


def test_config_hash_is_order_and_content_sensitive(tmp_path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text("x: 1\n")
    b.write_text("y: 2\n")

    h_ab = config_hash(a, b)
    h_ba = config_hash(b, a)
    assert h_ab != h_ba  # order-sensitive, since config content order matters for reproducibility

    b.write_text("y: 3\n")
    h_ab_changed = config_hash(a, b)
    assert h_ab_changed != h_ab
