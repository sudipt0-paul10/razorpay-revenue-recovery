"""dev / holdout / stress split definitions (EVAL.md §3.5, restored
verbatim in eval-spec-v1.4).

Not a guarded package - this is harness bookkeeping, not agent logic, and
holds no rrx.sim import regardless. Cross-checked against
rrx.sim.run_stage3.EPISODE_INDICES (range(1000, 3000)) and
tests/test_stage5_falsification.py's INDICES, per EVAL.md §3.5's own
cross-check note.

Holdout must never run accidentally: EVAL.md §3.5 - "Once per candidate
release", every run (successful or not) logged in
results/holdout_runs.md. `holdout_indices()` requires an explicit
`authorized=True` to return anything, rather than exposing the range as
a plain module-level constant that any caller could iterate without
thinking.
"""

from __future__ import annotations

DEV_SPLIT = "dev"
DEV_SEED_START = 1000
DEV_N = 2000
DEV_INDICES = range(DEV_SEED_START, DEV_SEED_START + DEV_N)  # 1000-2999

HOLDOUT_SPLIT = "holdout"
HOLDOUT_SEED_START = 9000
HOLDOUT_N = 2000
_HOLDOUT_INDICES = range(HOLDOUT_SEED_START, HOLDOUT_SEED_START + HOLDOUT_N)  # 9000-10999

STRESS_SPLIT = "stress"
STRESS_SEED_START = 5000
STRESS_N = 300
STRESS_INDICES = range(STRESS_SEED_START, STRESS_SEED_START + STRESS_N)  # 5000-5299


class HoldoutNotAuthorizedError(RuntimeError):
    """Raised when holdout indices are requested without explicit
    authorization. Do not catch-and-retry this with authorized=True
    unless the user has actually authorized a holdout run."""


def dev_indices() -> range:
    return DEV_INDICES


def stress_indices() -> range:
    return STRESS_INDICES


def holdout_indices(*, authorized: bool = False) -> range:
    """EVAL.md §3.5: holdout runs 'once per candidate release', and every
    run - successful or not - must be logged in results/holdout_runs.md.
    This is the only way this module exposes the holdout index range;
    callers must pass authorized=True deliberately, never as a default."""
    if not authorized:
        raise HoldoutNotAuthorizedError(
            "Holdout split access requires authorized=True. EVAL.md §3.5: holdout "
            "runs once per candidate release, and every run (successful or not) "
            "must be logged in results/holdout_runs.md. Do not set authorized=True "
            "without the user's explicit go-ahead for a real holdout run."
        )
    return _HOLDOUT_INDICES
