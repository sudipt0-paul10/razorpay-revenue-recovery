"""The single guarded holdout execution entry point.

EVAL.md §3.5 ("holdout runs once per candidate release, every run -
successful or not - logged in results/holdout_runs.md") and
docs/DAY8-HOLDOUT-PLAN.md §C3 ("exactly one call site in the entire
repository passes authorized=True... requires an explicit CLI flag with
no default... refuses to run if git status is dirty or HEAD is wrong...
refuses to run if the output already contains a completed run").

What this script does:
  - Requires --i-have-authorized-the-holdout (no default). Without it,
    refuses immediately, before touching git, the filesystem, or the
    holdout index range at all.
  - Re-verifies, at the moment of execution (not just at the last
    preflight pass): HEAD, the code-freeze-holdout and eval-spec-v1.10
    tags, and a clean working tree.
  - Refuses to start if any of the five arms' output directories already
    exist (complete or partial) under this implementation's holdout
    output root.
  - Obtains the holdout index range ONLY via
    rrx.harness.splits.holdout_indices(authorized=True) - never by
    reconstructing range(9000, 11000) or similar from the public
    HOLDOUT_SEED_START/HOLDOUT_N constants.
  - Runs exactly the EVAL.md §7.1 item A five arms - A0, A1,
    A2-strengthened, A3-D, A4 - via the existing
    rrx.eval.arms.run_official_arm(), never a duplicated simulation path.
  - Appends a session-start entry, then a per-arm outcome line as each
    arm finishes or raises, to results/holdout_runs.md.

What this script deliberately does NOT do:
  - It does NOT write the §C1 authorization declaration (the arm list
    freeze, the exact command record, the "Holdout has not been accessed
    prior to this entry" statement, the signed authorization sentence).
    That is a human/repository act, committed and tagged BEFORE this
    script is ever invoked with the authorization flag - this script
    only checks that the tree is in the state that pre-declaration
    describes, not that the pre-declaration exists at all.
  - It does NOT implement retry/resume logic. On any exception from a
    given arm, the failure is logged and re-raised - never caught and
    retried, automatically or otherwise. Whether and how to replay that
    arm is the human decision the already-committed retry policy in
    results/holdout_runs.md governs (max 2 attempts, identical inputs,
    never triggered by an observed result) - carried out by deliberately
    clearing that arm's output directory and re-invoking this script,
    not by anything inside this file.
  - It does NOT aggregate results across arms, select a comparator, or
    evaluate any EVAL.md §7 criterion. Those are separate, later stages.
  - It does NOT select or write the results/audit_sample/ deliverable.
  - It does NOT invent any new metric, comparator, threshold, or policy.

IMPORTANT: HoldoutNotAuthorizedError is caught below only to fail with a
clean message - never to retry with authorized=True. The only
authorized=True call site in this file passes it unconditionally, having
already required the --i-have-authorized-the-holdout flag first.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    # rrx is not installed into the interpreter (no editable install exists
    # in this project - only pytest's own `pythonpath = ["src"]` ini option
    # resolves it under test). This script must be runnable standalone via
    # `python scripts/run_holdout.py`, so it puts src/ on sys.path itself
    # rather than depending on the invoker's environment being set up
    # correctly - the exact class of mistake §B5's rehearsal exists to
    # catch ahead of time, applied here to the script itself.
    sys.path.insert(0, str(SRC_ROOT))

from rrx.eval.arms import (  # noqa: E402
    ARM_A0,
    ARM_A1,
    ARM_A2_STRENGTHENED,
    ARM_A3D,
    ARM_A4,
    run_official_arm,
)
from rrx.harness.splits import HoldoutNotAuthorizedError, holdout_indices  # noqa: E402
from rrx.sim.engine import MASTER_SEED  # noqa: E402

# Pinned to the exact implementation this script is authorized to run
# under. Updating these three constants is itself a reviewed change to
# make deliberately if a later provenance-fixing commit supersedes this
# state - never silently, and never as part of carrying out a holdout
# attempt.
#
# IMPLEMENTATION_SHA must equal whatever commit the CURRENT §C1
# authorization declaration (results/holdout_runs.md, "FINAL
# AUTHORIZATION DECLARATION" section) names as its Implementation SHA -
# not whatever HEAD happened to be when this script was last edited.
#
# Corrected 86930b2 -> 53bd122 (Day 8 SHA-mismatch fix): this script was
# originally written against 86930b2 (HEAD at the time), but the
# authorization declaration committed afterward - itself a new commit,
# `53bd1223691f0c1c09cce7bb754f123c3f38f38b`, "Authorize Day 8 holdout
# evaluation" - names 53bd122 as the authorized implementation SHA and is
# anchored by the annotated tag `holdout-authorized-20260830`. The first
# authorized invocation was correctly refused by this exact mismatch
# (HEAD 53bd122 != the then-pinned 86930b2) - the guard did its job; this
# is the deliberate, reviewed correction to the pinned constant, not a
# weakening of the check itself.
IMPLEMENTATION_SHA = "53bd1223691f0c1c09cce7bb754f123c3f38f38b"
CODE_FREEZE_HOLDOUT_SHA = "4d45db461943978637673a5611a429e0fe826065"
EVAL_SPEC_V1_10_SHA = "125eae8841562f6d5eccab58e055400340e71af6"

HOLDOUT_LOG_PATH = REPO_ROOT / "results" / "holdout_runs.md"
# Namespaced by implementation SHA (not by an invocation date this script
# cannot know in advance) so "does this output directory already contain
# a completed run for this implementation SHA" (requirement 3) is answered
# by the directory's own location, not a separately-tracked lookup.
HOLDOUT_OUTPUT_ROOT = REPO_ROOT / "results" / "holdout" / IMPLEMENTATION_SHA[:12]

HOLDOUT_SPLIT = "holdout"

# EVAL.md §7.1 item A's exact five-arm holdout set, in this fixed order.
# No A3-LLM (excluded from holdout entirely, budget reason), no A1-U, no
# A2-original, no A2-corrected-v1 - none of the four appear anywhere in
# this file.
HOLDOUT_ARMS: tuple[str, ...] = (ARM_A0, ARM_A1, ARM_A2_STRENGTHENED, ARM_A3D, ARM_A4)


class PreflightError(RuntimeError):
    """A precondition checked at execution time did not hold. Always
    surfaced and refused - never worked around, never retried here."""


def _run_id_for(arm_key: str) -> str:
    return arm_key.lower().replace("-", "_")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def verify_preconditions() -> None:
    """Re-verifies, at the moment of execution, the same repository-state
    facts §B1 already checked at the last preflight pass: this is not a
    substitute for §B, it is the belt to that suspenders - preflight could
    have passed minutes or days before this invocation, and the tree could
    have drifted since. Raises PreflightError on the first failure."""
    head = _git("rev-parse", "HEAD")
    if head != IMPLEMENTATION_SHA:
        raise PreflightError(
            f"HEAD is {head}, expected the authorized implementation "
            f"{IMPLEMENTATION_SHA}. Refusing to run against a different SHA."
        )

    freeze_sha = _git("rev-parse", "code-freeze-holdout^{commit}")
    if freeze_sha != CODE_FREEZE_HOLDOUT_SHA:
        raise PreflightError(
            f"code-freeze-holdout resolves to {freeze_sha}, expected "
            f"{CODE_FREEZE_HOLDOUT_SHA}. The freeze tag has moved - refusing."
        )

    spec_sha = _git("rev-parse", "eval-spec-v1.10^{commit}")
    if spec_sha != EVAL_SPEC_V1_10_SHA:
        raise PreflightError(
            f"eval-spec-v1.10 resolves to {spec_sha}, expected "
            f"{EVAL_SPEC_V1_10_SHA}. The spec tag has moved - refusing."
        )

    status = _git("status", "--porcelain")
    if status:
        raise PreflightError(
            "Working tree is not clean:\n" + status + "\n"
            "Refusing to run a holdout attempt against an uncommitted/dirty tree."
        )


def verify_no_existing_run_directories(
    output_root: Path, arms: tuple[str, ...] = HOLDOUT_ARMS
) -> None:
    """Refuses if ANY arm's output directory already exists under
    `output_root` - complete or partial. This script has no retry/resume
    logic (module docstring): deciding whether a pre-existing directory is
    a safe-to-replay crash remnant under the committed retry policy is a
    human decision, carried out by deliberately clearing that one arm's
    directory before invoking this script again - never by this script
    silently continuing into or overwriting it."""
    existing = [
        output_root / _run_id_for(arm) for arm in arms
        if (output_root / _run_id_for(arm)).exists()
    ]
    if existing:
        raise PreflightError(
            "Refusing to start: the following output directories already "
            "exist for this implementation SHA:\n"
            + "\n".join(f"  {p}" for p in existing)
            + "\nRemove or relocate them deliberately, as a reviewed human "
            "action under the committed retry policy, before re-running."
        )


def _append_session_start_log(indices_n: int) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = (
        f"\n## Holdout execution session started — {timestamp}\n\n"
        f"- Implementation SHA: {IMPLEMENTATION_SHA}\n"
        f"- Spec version: eval-spec-v1.10 ({EVAL_SPEC_V1_10_SHA})\n"
        f"- Split: {HOLDOUT_SPLIT} | N: {indices_n} | Master seed: {MASTER_SEED}\n"
        f"- Arms, execution order: {', '.join(HOLDOUT_ARMS)}\n"
        f"- Started via: scripts/run_holdout.py (--i-have-authorized-the-holdout)\n"
        f"- Per-arm outcomes appended below as each arm completes or fails.\n"
    )
    with open(HOLDOUT_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(entry)


def _append_arm_outcome(arm: str, run_id: str, status: str, detail: str = "") -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"- {timestamp} | arm={arm} | run_id={run_id} | status={status}"
    if detail:
        line += f" | {detail}"
    with open(HOLDOUT_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_holdout.py",
        description=(
            "The single guarded holdout execution entry point (EVAL.md "
            "§3.5, docs/DAY8-HOLDOUT-PLAN.md §C3). Runs A0, A1, "
            "A2-strengthened, A3-D, A4 over the frozen holdout split. Does "
            "NOT write the §C1 authorization declaration itself - that is "
            "a separate, pre-committed human action."
        ),
    )
    parser.add_argument(
        "--i-have-authorized-the-holdout",
        dest="authorized",
        action="store_true",
        default=False,
        help=(
            "Required, no default. Confirms a human has already committed "
            "and tagged the §C1 authorization pre-declaration before this "
            "invocation."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.authorized:
        print(
            "Refusing to run: --i-have-authorized-the-holdout was not "
            "passed. No git check, no holdout index access, and no log "
            "entry have been made.",
            file=sys.stderr,
        )
        return 2

    try:
        verify_preconditions()
        verify_no_existing_run_directories(HOLDOUT_OUTPUT_ROOT, HOLDOUT_ARMS)
        indices = list(holdout_indices(authorized=True))
    except (PreflightError, HoldoutNotAuthorizedError) as exc:
        print(f"Refusing to run: {exc}", file=sys.stderr)
        return 1

    _append_session_start_log(len(indices))

    for arm in HOLDOUT_ARMS:
        run_id = _run_id_for(arm)
        try:
            run_official_arm(
                arm,
                run_id,
                results_dir=HOLDOUT_OUTPUT_ROOT,
                indices=indices,
                master_seed=MASTER_SEED,
                split=HOLDOUT_SPLIT,
            )
        except Exception as exc:  # noqa: BLE001 - logged, then re-raised, never retried
            _append_arm_outcome(arm, run_id, "CRASHED", detail=str(exc))
            raise
        _append_arm_outcome(arm, run_id, "COMPLETE")

    return 0


if __name__ == "__main__":
    sys.exit(main())
