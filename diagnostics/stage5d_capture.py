"""Stage 5D — capture-only reproduction of official DEV run per-episode
outcomes (diagnostics/stage5d_capture_plan.md).

Additive, output-layer-only: reuses each arm's already-frozen computation
path exactly as-is and persists (episode_index, invoice_recovered,
subscription_rescued) - the EpisodeResult booleans those paths already
compute and previously discarded after aggregation. No change to policy
logic, simulator logic, RNG behavior, episode iteration order, or the
existing official metrics computation.

A0/A1/A2-strengthened run against whatever `rrx` resolves to on
sys.path/PYTHONPATH (must be invoked with the original SHA f5c992a - i.e.
current HEAD at the time this script was authored - on PYTHONPATH). A3-D
must be invoked with PYTHONPATH pointed at a `git worktree` checked out at
e829161 (its original manifest.json git_sha), per the pre-registered plan's
requirement to pin A3-D's capture to its own recorded SHA rather than HEAD.

Usage:
    python diagnostics/stage5d_capture.py a0
    python diagnostics/stage5d_capture.py a1
    python diagnostics/stage5d_capture.py a2s
    python diagnostics/stage5d_capture.py a3d
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = REPO_ROOT / "results" / "capture"

DEV_INDEX_START = 1000
DEV_INDEX_END = 2999  # inclusive
MASTER_SEED = 20260825

_ORIGINAL_RUN_ID = {
    "a0": "a0-dev-20260828-01",
    "a1": "a1-dev-20260828-01",
    "a2s": "a2s-dev-20260828-01",
    "a3d": "a3d-dev-20260828-01",
}
_ORIGINAL_SPEC_VERSION = {
    "a0": "eval-spec-v1.6",
    "a1": "eval-spec-v1.6",
    "a2s": "eval-spec-v1.6",
    "a3d": "eval-spec-v1.5",
}
# The git_sha literally recorded in each arm's OWN original manifest.json
# (diagnostics/stage5d_capture_plan.md §4) - never re-derived from "whatever
# HEAD happens to be at capture time", which would silently drift once any
# later commit (e.g. this plan's own pre-registration commit) lands.
_ORIGINAL_GIT_SHA = {
    "a0": "f5c992ae6fc98ff1230e8e0e91cf1f361a589f43",
    "a1": "f5c992ae6fc98ff1230e8e0e91cf1f361a589f43",
    "a2s": "f5c992ae6fc98ff1230e8e0e91cf1f361a589f43",
    "a3d": "e829161b8b174d2afca317f571048810b426b587",
}


def _write_capture(arm_key, indices, results, *, original_git_sha, capture_git_sha,
                    config_hash_value):
    run_id = _ORIGINAL_RUN_ID[arm_key]
    out_dir = CAPTURE_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=False)

    episodes_path = out_dir / "episodes.jsonl"
    with open(episodes_path, "w", encoding="utf-8") as fh:
        for idx, r in zip(indices, results):
            fh.write(
                json.dumps(
                    {
                        "episode_index": idx,
                        "invoice_recovered": bool(r.invoice_recovered),
                        "subscription_rescued": bool(r.subscription_rescued),
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    manifest = {
        "original_run_id": run_id,
        "original_git_sha": original_git_sha,
        "capture_git_sha": capture_git_sha,
        "split": "dev",
        "index_start": DEV_INDEX_START,
        "index_end": DEV_INDEX_END,
        "n": len(indices),
        "master_seed": MASTER_SEED,
        "config_hash": config_hash_value,
        "spec_version": _ORIGINAL_SPEC_VERSION[arm_key],
        "capture_timestamp": datetime.now().astimezone().isoformat(),
    }
    (out_dir / "capture_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )

    invoice_count = sum(1 for r in results if r.invoice_recovered)
    rescue_count = sum(1 for r in results if r.subscription_rescued)
    print(f"{arm_key} ({run_id}): n={len(results)} invoice={invoice_count} rescue={rescue_count}")
    print(f"  wrote {episodes_path}")
    print(f"  wrote {out_dir / 'capture_manifest.json'}")
    return out_dir


def capture_policy_arm(arm_key: str) -> Path:
    """A0 / A1 / A2-strengthened: run via rrx.eval.arms.run_arm_cohort,
    exactly the dispatch path already used for the official runs."""
    from rrx.eval import arms as eval_arms
    from rrx.harness.splits import dev_indices
    from rrx.sim.latent import load_configs
    from rrx.spec.manifest import config_hash, current_git_sha

    arm_key_map = {
        "a0": eval_arms.ARM_A0,
        "a1": eval_arms.ARM_A1,
        "a2s": eval_arms.ARM_A2_STRENGTHENED,
    }
    dispatch_key = arm_key_map[arm_key]

    episode_cfg, population_cfg = load_configs()
    indices = list(dev_indices())
    assert indices[0] == DEV_INDEX_START and indices[-1] == DEV_INDEX_END and len(indices) == 2000

    results, ledger_records = eval_arms.run_arm_cohort(
        dispatch_key, episode_cfg, population_cfg, indices, master_seed=MASTER_SEED
    )
    assert ledger_records is None, f"{arm_key}: expected no ledger (policies-arm), got one"

    config_hash_value = config_hash(
        REPO_ROOT / "configs" / "episode.yaml", REPO_ROOT / "configs" / "population.yaml"
    )
    # Explicit repo_root=REPO_ROOT (this script's own location, the main
    # repo) regardless of which worktree `rrx.spec.manifest` itself was
    # imported from - this is the actual HEAD the capture orchestration ran
    # at, distinct from the pinned original_git_sha below.
    capture_sha = current_git_sha(REPO_ROOT)

    return _write_capture(
        arm_key,
        indices,
        results,
        original_git_sha=_ORIGINAL_GIT_SHA[arm_key],
        capture_git_sha=capture_sha,
        config_hash_value=config_hash_value,
    )


def capture_a3d() -> Path:
    """A3-D: run via the frozen run_episode_a3/a3d_policy resolved from
    whatever is on PYTHONPATH at invocation time (the caller is responsible
    for pointing PYTHONPATH at the e829161 worktree's src/, per the plan)."""
    from rrx.agent.policy import a3d_policy
    from rrx.harness.runner import run_episode_a3
    from rrx.harness.splits import DEV_SPLIT, dev_indices
    from rrx.sim.latent import load_configs
    from rrx.spec.manifest import config_hash, current_git_sha

    episode_cfg, population_cfg = load_configs()
    indices = list(dev_indices())
    assert indices[0] == DEV_INDEX_START and indices[-1] == DEV_INDEX_END and len(indices) == 2000

    results = []
    for i in indices:
        result = run_episode_a3(
            DEV_SPLIT, i, a3d_policy, episode_cfg, population_cfg, master_seed=MASTER_SEED
        )
        results.append(result)

    # current_git_sha()/config_hash() here resolve against whatever repo
    # root the imported rrx.spec.manifest module itself lives under - the
    # e829161 worktree when PYTHONPATH points there, so this independently
    # reports e829161 rather than assuming it.
    original_sha = current_git_sha()
    assert original_sha == _ORIGINAL_GIT_SHA["a3d"], (
        f"worktree HEAD {original_sha} does not match a3d's recorded original "
        f"manifest.json git_sha {_ORIGINAL_GIT_SHA['a3d']} - PYTHONPATH is not "
        "pointed at the correct worktree."
    )
    config_hash_value = config_hash(
        Path(__file__).resolve().parents[1] / "configs" / "episode.yaml",
        Path(__file__).resolve().parents[1] / "configs" / "population.yaml",
    )

    from rrx.spec.manifest import current_git_sha as head_git_sha_fn

    return _write_capture(
        "a3d",
        indices,
        results,
        original_git_sha=original_sha,
        capture_git_sha=head_git_sha_fn(REPO_ROOT),
        config_hash_value=config_hash_value,
    )


if __name__ == "__main__":
    arm = sys.argv[1]
    if arm == "a3d":
        capture_a3d()
    elif arm in ("a0", "a1", "a2s"):
        capture_policy_arm(arm)
    else:
        raise SystemExit(f"unknown arm: {arm!r} (expected a0/a1/a2s/a3d)")
