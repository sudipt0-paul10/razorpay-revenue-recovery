"""Task 4A primary deliverable (docs/A3-DESIGN.md §16): byte-identity /
mechanics-parity proof between the frozen sim-v1 A0 arm (run_episode)
and the new A3 runner (rrx.harness.runner.run_episode_a3) driven by a
NULL POLICY that always returns WAIT.

This is NOT a proof that the null policy's "logic" matches A0's - it is
a proof that the new runner reproduces sim-v1's day-loop mechanics
EXACTLY: day ordering, within-day ordering, retry mechanics, halt
mechanics, contact budget, channel handling, RNG/CRN behavior,
latent-state handling, episode termination, contact history,
subscription-state transitions. A0 is the correct comparator because A0
also never contacts (its policy always returns None), so both arms
should be mechanically indistinguishable at the level of executed
actions, whatever the runner's internal wakeup/tick_type bookkeeping
looks like.

Comparison is EXACT EpisodeResult equality plus exact contact_history
equality (via capture_view_at_day=30), for every dev episode (seeds
1000-2999, N=2000) - no tolerances, no aggregate-only comparison, no
excluded episodes. If this fails, the acceptance gate is failed and
nothing past this point (gate, ledger, A3-D, A3-LLM) may proceed - see
this file's module-level STOP condition below.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from rrx.agent.null_policy import null_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.engine import run_episode
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

REPO_ROOT = Path(__file__).resolve().parents[1]
SIM_DIR = REPO_ROOT / "src" / "rrx" / "sim"
EPISODE_VIEW_FILE = REPO_ROOT / "src" / "rrx" / "features" / "episode_view.py"


def _hash_frozen_files() -> dict[str, str]:
    paths = sorted(SIM_DIR.glob("*.py")) + [EPISODE_VIEW_FILE]
    return {
        str(p.relative_to(REPO_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }


def _format_view(view) -> str:
    if view is None:
        return "None"
    return (
        f"EpisodeView(subscription_id={view.subscription_id!r}, "
        f"subscription_state={view.subscription_state!r}, "
        f"invoice_amount_inr={view.invoice_amount_inr}, "
        f"days_since_first_failure={view.days_since_first_failure}, "
        f"auto_retries_remaining={view.auto_retries_remaining}, "
        f"next_auto_retry_day={view.next_auto_retry_day}, "
        f"decline_code={view.decline_code!r}, "
        f"billing_amount_inr={view.billing_amount_inr}, "
        f"contact_history={view.contact_history}, "
        f"budget_remaining={view.budget_remaining})"
    )


def _first_divergent_day(i: int) -> tuple[int | None, str, str]:
    """Best-effort diagnostic, invoked ONLY after a mismatch has already
    been found for episode i: re-runs both arms with capture_view_at_day
    for each day 0..window_days, returning the first day at which the two
    EpisodeViews differ (day, expected-repr, actual-repr)."""
    window_days = EPISODE_CFG["episode"]["window_days"]
    for day in range(0, window_days + 1):
        a0 = run_episode(DEV_SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG, capture_view_at_day=day)
        a3 = run_episode_a3(
            DEV_SPLIT, i, null_policy, EPISODE_CFG, POPULATION_CFG, capture_view_at_day=day
        )
        a0_view = a0[1]
        a3_view = a3[1]
        if a0_view != a3_view:
            return day, _format_view(a0_view), _format_view(a3_view)
    return None, "", ""


def test_a3_runner_null_policy_exact_parity_with_a0_over_dev():
    """The acceptance gate for Task 4A. See module docstring."""
    hashes_before = _hash_frozen_files()

    first_mismatch = None
    for i in DEV_INDICES:
        a0_result, a0_view = run_episode(
            DEV_SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG, capture_view_at_day=30
        )
        a3_result, a3_view = run_episode_a3(
            DEV_SPLIT, i, null_policy, EPISODE_CFG, POPULATION_CFG, capture_view_at_day=30
        )
        if a0_result != a3_result or a0_view != a3_view:
            first_mismatch = (i, a0_result, a3_result, a0_view, a3_view)
            break  # report the FIRST failing episode only

    hashes_after = _hash_frozen_files()
    assert hashes_before == hashes_after, (
        "src/rrx/sim/*.py or episode_view.py changed during the parity run - "
        "these are frozen; this test suite must never modify them."
    )

    if first_mismatch is None:
        return

    i, a0_result, a3_result, a0_view, a3_view = first_mismatch
    day, a0_view_at_day, a3_view_at_day = _first_divergent_day(i)

    report = [
        "PARITY FAILURE - A3 runner (NULL POLICY) diverges from A0 (run_episode).",
        "Per docs/A3-DESIGN.md Task 4A: do NOT weaken this assertion, add "
        "tolerances, exclude this episode, change seeds, or modify the "
        "simulator. Report this and stop.",
        f"first failing episode index / seed: {i}",
        f"first divergent day (day-by-day capture_view_at_day scan): {day}",
        f"expected (A0) EpisodeResult: {a0_result}",
        f"actual   (A3-null) EpisodeResult: {a3_result}",
        f"expected (A0) EpisodeView @ day 30: {_format_view(a0_view)}",
        f"actual   (A3-null) EpisodeView @ day 30: {_format_view(a3_view)}",
    ]
    if day is not None:
        report.append(f"expected (A0) EpisodeView @ day {day}: {a0_view_at_day}")
        report.append(f"actual   (A3-null) EpisodeView @ day {day}: {a3_view_at_day}")

    pytest.fail("\n".join(report))


def test_sim_directory_has_no_uncommitted_diff():
    """docs/A3-DESIGN.md §16 / Task 4A section 6: `git diff --stat --
    src/rrx/sim/` must be empty - the simulator is untouched by this
    task."""
    result = subprocess.run(
        ["git", "diff", "--stat", "--", "src/rrx/sim/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"git diff failed: {result.stderr}"
    assert result.stdout.strip() == "", (
        f"src/rrx/sim/ has uncommitted changes, which must not exist for this task:\n"
        f"{result.stdout}"
    )
