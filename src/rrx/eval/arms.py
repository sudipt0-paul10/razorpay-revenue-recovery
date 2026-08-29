"""Stage B: arm-dispatch mechanism making the canonical comparator arms
runnable through the same evaluation infrastructure Stage A already built
for A3-D, without forking or modifying src/rrx/sim/.

Two structurally different runners exist in this repository, by design
(docs/A3-DESIGN.md §2 - not something this module changes):

  - rrx.sim.engine.run_episode(split, i, arm_key, episode_cfg,
    population_cfg, master_seed) - the day-schedule interface A0/A1/A2 and
    its variants use, dispatched through the engine._POLICIES dict. No
    EpisodeView, no gate, no ledger.
  - rrx.harness.runner.run_episode_a3(split, i, policy, episode_cfg,
    population_cfg, master_seed, ledger_record) - A3-D/A3-LLM's
    EpisodeView-driven, gated, ledger-recording runner.

Both already return the identical rrx.sim.engine.EpisodeResult dataclass
(harness/runner.py reuses engine._finalize unmodified) - that shared
return type is what lets a single dispatcher unify them for aggregation
purposes, without merging their day-loop mechanics (which frozen
docs/A3-DESIGN.md §2 explicitly keeps separate).

Canonical arms wired here:
  - A0            - already a permanent key in engine._POLICIES.
  - A1             - EVAL.md §4's frozen T+0/T+3 schedule, content/remedy
    (card_change, both contacts) formally adopted at eval-spec-v1.6
    (EVAL.md §4.3, [CONSEQUENTIAL-2]). Implementation: rrx.baselines.a1.
    a1_action_for_day - see ARM_A1_PROVENANCE below.
  - A2             (A2-original) - ditto. Frozen, "not used in the
    headline comparator" per EVAL.md §4.1, but kept runnable for
    transparency, matching the project's own existing convention.
  - A2_STRENGTHENED - EVAL.md §4.1.2: "Adopted as 'the' A2 - the final
    bounded A2 used in the §7 comparator." Full schedule given in that
    section's own prose. Implementation: rrx.baselines.a2_variants.
    a2_strengthened_action_for_day (production code, untouched here).
  - A3-D           - dispatches to Stage A's run_a3d_dev_cohort.
  - A4             (Stage 7.3 addition) - EVAL.md §4's oracle arm, full
    latent access, same 3-contact budget. Not a `_POLICIES`-registrable
    policy (needs latent state the standard interface never exposes) - its
    own episode-loop function, rrx.baselines.a4.run_a4_episode, dispatched
    directly by run_arm_cohort below, exactly as A3-D is.

Stage 7.3 addition: every dispatch/writer function below now takes an
explicit `split` parameter (default DEV_SPLIT, so every pre-existing call
site that omits it is unaffected) rather than hardcoding the "dev" string
literal - required so this same machinery can run EVAL.md §3.5's `stress`
split (rrx.harness.splits.stress_indices(), seeds 5000-5299) without
silently drawing the wrong (non-canonical) CRN world for those indices.
See rrx.eval.stress for the stress-specific driver that uses this.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator

from rrx.agent.ledger import LedgerRecord, to_json_line
from rrx.baselines.a1 import a1_action_for_day
from rrx.baselines.a2_variants import a2_strengthened_action_for_day
from rrx.baselines.a4 import run_a4_episode
from rrx.eval import runner as eval_runner
from rrx.eval.runner import run_a3d_dev_cohort
from rrx.harness.splits import DEV_SPLIT, dev_indices
from rrx.sim import engine
from rrx.sim.engine import MASTER_SEED, EpisodeResult, run_episode
from rrx.sim.latent import load_configs
from rrx.spec.manifest import RunManifest, config_hash, current_git_sha, write_manifest

ARM_A0 = "A0"
ARM_A1 = "A1"  # Content/remedy adopted eval-spec-v1.6 - see ARM_A1_PROVENANCE.
ARM_A2 = "A2"  # A2-original, frozen in engine._POLICIES already.
ARM_A2_STRENGTHENED = "A2_STRENGTHENED"  # EVAL.md §4.1.2's adopted A2.
ARM_A3D = "A3-D"
ARM_A4 = "A4"  # EVAL.md §4: oracle, empirical upper reference, not a target.

# Arm keys already permanently registered in engine._POLICIES - no
# temporary registration needed for these.
_PERMANENT_POLICY_ARMS = frozenset({ARM_A0, ARM_A2})

# Arm keys this module can register temporarily (scoped to one cohort run)
# via `registered_policy` below, and the production policy callable each
# one maps to. rrx.sim.engine.py itself is never edited to add these.
_REGISTERABLE_POLICY_ARMS: dict[str, Callable[[str, int, str], str | None]] = {
    ARM_A1: a1_action_for_day,
    ARM_A2_STRENGTHENED: a2_strengthened_action_for_day,
}

# RESOLVED (was a Stage B hard-stop / open question): EVAL.md §4's A1 row
# ("Same two contacts to everyone at T+0 and T+3, regardless of state or
# reason") pinned A1's SCHEDULE from original authorship, but left its
# CONTENT/remedy unspecified. The only implementation at Stage B time,
# tests/test_stage5_falsification.py's self-labelled "A1-ish"
# a1_action_for_day, was diagnostic-only and not asserted as canonical
# anywhere. `eval-spec-v1.6` (EVAL.md §4.3, [CONSEQUENTIAL-2], commit
# c75d548, tag eval-spec-v1.6) formally adopted that exact
# operationalization (card_change, T+0/T+3) as canonical A1 - a new
# consequential decision, not a recovered specification. The
# implementation now lives in src/rrx/baselines/a1.py, byte-for-byte
# behaviorally identical to the original diagnostic (tests/test_a1.py
# enforces this). Preserved here as a record of the resolution, not
# deleted - the investigation and its outcome are both provenance.
ARM_A1_PROVENANCE = (
    "RESOLVED at eval-spec-v1.6 (EVAL.md §4.3, [CONSEQUENTIAL-2]): "
    "canonical A1 = card_change at T+0/T+3, regardless of state or "
    "reason. Implementation: rrx.baselines.a1.a1_action_for_day, "
    "behaviorally identical to the original 'A1-ish' diagnostic "
    "construction (tests/test_stage5_falsification.py, commit cdd118a)."
)


class UnknownArmError(ValueError):
    pass


@contextmanager
def registered_policy(
    arm_key: str, policy_fn: Callable[[str, int, str], str | None]
) -> Iterator[None]:
    """Temporarily registers `policy_fn` into engine._POLICIES under
    `arm_key`, exactly mirroring the pattern already established twice in
    this repository (tests/test_stage5_falsification.py's
    _register_test_arms, tests/test_a2_variants.py's
    _register_variant_arms) - never engine.py's own source. Raises if
    `arm_key` is already registered (defends against clobbering a frozen
    arm or a concurrent registration) and always deregisters on exit, even
    on error."""
    if arm_key in engine._POLICIES:
        raise RuntimeError(
            f"engine._POLICIES[{arm_key!r}] is already registered - refusing "
            "to overwrite it. If this arm should be permanently registered, "
            "that is a decision for src/rrx/sim/engine.py, not this module."
        )
    engine._POLICIES[arm_key] = policy_fn
    try:
        yield
    finally:
        del engine._POLICIES[arm_key]


def run_policies_cohort(
    arm_key: str,
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    indices: list[int] | range,
    master_seed: int = MASTER_SEED,
    split: str = DEV_SPLIT,
) -> list[EpisodeResult]:
    """Runs `arm_key` through the frozen rrx.sim.engine.run_episode for
    every index, in order. `arm_key` must already be resolvable in
    engine._POLICIES (either permanently, or via `registered_policy` used
    by the caller / by run_arm_cohort below).

    `split` (Stage 7.3) defaults to DEV_SPLIT - every existing call site
    that omits it is unaffected - but is threaded through to `run_episode`
    rather than hardcoded, since `split` feeds the CRN seed derivation
    (EVAL.md §6) and this dispatcher is not dev-only anymore."""
    return [
        run_episode(split, i, arm_key, episode_cfg, population_cfg, master_seed=master_seed)
        for i in indices
    ]


def run_arm_cohort(
    arm_key: str,
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    indices: list[int] | range,
    master_seed: int = MASTER_SEED,
    split: str = DEV_SPLIT,
) -> tuple[list[EpisodeResult], list[LedgerRecord] | None]:
    """Single dispatch point for every wired arm. Returns (results, ledger)
    - ledger is None (not []) for arms with no ledger mechanism at all,
    signalling "not applicable" rather than "zero records produced" (see
    rrx.eval.runner.LEDGER_METRICS_UNAVAILABLE_FOR_POLICIES_ARMS).

    A0/A1/A2/A3-D/A4 all draw from the identical cohort/latent CRN before
    any policy is consulted (rrx.sim.cohort.sample_cohort_episode /
    rrx.sim.latent.draw_latent_state, called with the same split/i/
    master_seed regardless of arm) - this dispatcher does not, and does
    not need to, do anything additional to guarantee that; it is already
    true of every underlying runner and is not re-implemented here.

    `split` (Stage 7.3) defaults to DEV_SPLIT - every existing call site
    that omits it is unaffected - and is threaded to whichever runner
    `arm_key` dispatches to, so this same function runs the `stress` split
    (or any other) correctly rather than silently drawing "dev" worlds for
    non-dev indices.
    """
    if arm_key == ARM_A3D:
        results, ledger = run_a3d_dev_cohort(
            episode_cfg, population_cfg, indices, master_seed=master_seed, split=split
        )
        return results, ledger

    if arm_key == ARM_A4:
        results = [
            run_a4_episode(split, i, episode_cfg, population_cfg, master_seed=master_seed)
            for i in indices
        ]
        return results, None

    if arm_key in _PERMANENT_POLICY_ARMS:
        return run_policies_cohort(
            arm_key, episode_cfg, population_cfg, indices, master_seed=master_seed, split=split
        ), None

    if arm_key in _REGISTERABLE_POLICY_ARMS:
        with registered_policy(arm_key, _REGISTERABLE_POLICY_ARMS[arm_key]):
            return run_policies_cohort(
                arm_key, episode_cfg, population_cfg, indices,
                master_seed=master_seed, split=split,
            ), None

    raise UnknownArmError(
        f"{arm_key!r} is not a wired arm. Wired: "
        f"{sorted(_PERMANENT_POLICY_ARMS | set(_REGISTERABLE_POLICY_ARMS) | {ARM_A3D, ARM_A4})}."
    )


def load_dev_configs() -> tuple[dict[str, Any], dict[str, Any]]:
    """Thin re-export of rrx.sim.latent.load_configs for callers of this
    module that don't want a second direct rrx.sim.latent import."""
    return load_configs()


# Provenance strings recorded in run_params.json (§7's reproducibility
# sidecar - see rrx.eval.runner.write_run_params) for each wired
# policies-arm. Not used for dispatch - dispatch is entirely
# run_arm_cohort()'s job via engine._POLICIES.
_POLICY_QUALNAME: dict[str, str] = {
    ARM_A0: "rrx.sim.engine.a0_action_for_day",
    ARM_A1: "rrx.baselines.a1.a1_action_for_day",
    ARM_A2: "rrx.sim.engine.a2_action_for_day",
    ARM_A2_STRENGTHENED: "rrx.baselines.a2_variants.a2_strengthened_action_for_day",
    ARM_A4: "rrx.baselines.a4.run_a4_episode",
}
_POLICIES_RUNNER_PATH = "rrx.sim.engine.run_episode"
_A4_RUNNER_PATH = "rrx.baselines.a4.run_a4_episode"  # A4 has no separate policy/runner split.


def run_official_arm(
    arm_key: str,
    run_id: str,
    results_dir: Path | None = None,
    indices: list[int] | None = None,
    master_seed: int = MASTER_SEED,
    split: str = DEV_SPLIT,
) -> Path:
    """Generalization of rrx.eval.runner.main() to any wired arm - §7's
    requirement that eventual A1/A2 runs produce run_id/manifest/
    run_params/metrics "using the same basic structure" as
    results/a3d-dev-20260828-01/. Reuses Stage A's manifest/run_params/
    metrics machinery verbatim (rrx.eval.runner.write_manifest call,
    write_run_params, compute_metrics_results_only, the same
    ResultsDirectoryExistsError guard) rather than a second, incompatible
    writer.

    `split` (Stage 7.3) defaults to DEV_SPLIT - every existing call site
    that omits it keeps its exact prior behavior - and is threaded to
    run_arm_cohort/audit_coverage_check/write_run_params, so this same
    writer also produces correct EVAL.md §3.5 `stress` (or any other
    split's) artifacts rather than mislabeling them "dev".

    Refuses arm_key == ARM_A3D only when split == DEV_SPLIT: the already-
    executed DEV A3-D result must only ever be produced via
    rrx.eval.runner.main(), never through this generalized path (even
    though the ResultsDirectoryExistsError guard below would already
    refuse to overwrite that specific run_id). That guard's purpose was
    always about not re-producing THAT dev result a second, possibly
    divergent way - it never meant "A3-D can only ever run through
    main()" - so a non-dev split (e.g. `stress`, which has never been run
    through either path) is not refused here. This function writes NO
    ledger.jsonl for policies-arms with no ledger mechanism at all
    (A0/A2/A2_STRENGTHENED/A4): rrx.sim.engine.run_episode and
    rrx.baselines.a4.run_a4_episode have no ledger mechanism (see
    rrx.eval.runner.LEDGER_METRICS_UNAVAILABLE_FOR_POLICIES_ARMS) - there
    is nothing to serialize, not an omission. `episode_results.jsonl`
    (rrx.eval.runner.write_episode_results, Day 8 pre-holdout provenance
    fix) is written for every arm regardless, since `results` always
    exists for every arm this dispatcher supports.

    Per the Stage B brief §8: intended for smoke-scale (≤10-episode)
    exercise via tmp_path in tests, not for the official 2,000-episode
    comparator runs - Stage B itself did not invoke it at that scale.
    Stage 7.3 is the first caller to run it at official scale, for the
    300-episode `stress` split specifically (rrx.eval.stress).
    """
    if arm_key == ARM_A3D and split == DEV_SPLIT:
        raise UnknownArmError(
            "run_official_arm refuses arm_key='A3-D' for split='dev' - the "
            "existing dev A3-D result must only be produced via "
            "rrx.eval.runner.main(), never rerun through this generalized "
            "path. Pass a non-dev split (e.g. stress) if that is genuinely "
            "what is intended."
        )

    results_dir = results_dir or eval_runner.RESULTS_DIR
    run_dir = results_dir / run_id

    if run_dir.exists():
        raise eval_runner.ResultsDirectoryExistsError(
            f"{run_dir} already exists - stopping rather than overwriting a "
            "prior run's artifacts. Choose a different run_id or remove the "
            "existing directory deliberately, outside this driver."
        )

    episode_cfg, population_cfg = load_configs()
    resolved_indices = list(indices if indices is not None else dev_indices())

    start = time.monotonic()
    results, ledger_records = run_arm_cohort(
        arm_key, episode_cfg, population_cfg, resolved_indices,
        master_seed=master_seed, split=split,
    )
    wall_clock_seconds = time.monotonic() - start

    if len(results) != len(resolved_indices):
        raise RuntimeError(
            f"episode count mismatch for {arm_key}: expected {len(resolved_indices)}, "
            f"got {len(results)} - an episode was dropped rather than raising, which "
            "should not happen."
        )

    if ledger_records is None:
        metrics = eval_runner.compute_metrics_results_only(results)
    else:
        metrics = eval_runner.compute_metrics(results, ledger_records)
        window_days = episode_cfg["episode"]["window_days"]
        metrics["audit_coverage"] = eval_runner.audit_coverage_check(
            results, resolved_indices, ledger_records, window_days, split=split
        )

    run_dir.mkdir(parents=True, exist_ok=False)

    if ledger_records is not None:
        ledger_path = run_dir / "ledger.jsonl"
        with open(ledger_path, "w", encoding="utf-8") as fh:
            for rec in ledger_records:
                fh.write(to_json_line(rec) + "\n")

    # Day 8 pre-holdout provenance fix (docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md
    # Issue 1): same writer eval_runner.main() uses for A3-D, so every wired
    # arm (A0/A1/A2-strengthened/A3-D/A4) persists the identical per-episode
    # artifact through the identical function - no per-arm variant.
    eval_runner.write_episode_results(run_dir, resolved_indices, results)

    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))

    manifest = RunManifest(
        git_sha=current_git_sha(eval_runner.REPO_ROOT),
        spec_version=eval_runner.SPEC_VERSION,
        config_hash=config_hash(
            *(
                eval_runner.REPO_ROOT / "configs" / f
                for f in eval_runner.CONFIG_FILES_IN_SCOPE
            )
        ),
        seed=master_seed,
        arm=arm_key,
        regime=eval_runner.REGIME,
        sweep_cell="baseline",
        model_version=None,
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        wall_clock_seconds=wall_clock_seconds,
        llm_cost_inr=None,
    )
    manifest_path = write_manifest(manifest, run_id, results_dir)
    eval_runner.write_run_params(
        run_dir,
        split=split,
        indices=resolved_indices,
        master_seed=master_seed,
        arm=arm_key,
        policy=_POLICY_QUALNAME.get(arm_key, "<unknown>"),
        runner_path=_A4_RUNNER_PATH if arm_key == ARM_A4 else _POLICIES_RUNNER_PATH,
    )

    print(
        f"Run {run_id} ({arm_key}) complete: "
        f"n={len(results)}, wall_clock={wall_clock_seconds:.1f}s"
    )
    print(f"  manifest: {manifest_path}")
    print(f"  metrics:  {metrics_path}")

    return run_dir
