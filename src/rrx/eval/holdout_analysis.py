"""Deterministic post-sealing analysis of holdout artifacts.

EVAL.md §7 (success criteria), the eval-spec-v1.7 comparator tie-set rule
(EVAL.md:821-841, confirmed unmodified through eval-spec-v1.10 - see
docs/DAY8-CONTRACT-EXTRACT.md Q6), and docs/DAY8-HOLDOUT-PLAN.md §F.

Reads ONLY already-written, already-sealed `results/<run_id>/` artifacts:
  - `episode_results.jsonl` (this project's own Day 8 per-episode
    persistence fix) - the per-episode outcome vector every metric and
    the paired bootstrap are recomputed from.
  - `metrics.json` - the run's own committed aggregate, cross-checked
    against an independent recomputation, never trusted blindly.

Never reads stdout, `ledger.jsonl`, or any LLM cache. Never executes a
simulation, calls a policy, or touches `rrx.harness.splits.holdout_indices`
- this module has no way to access or authorize a holdout run; it only
analyzes artifacts a run already produced. Every check raises
`ArtifactError` on the first problem found - nothing here silently
continues past a missing, malformed, or internally inconsistent
artifact, and nothing here invents a metric, comparator, or threshold
beyond what EVAL.md §7 and the eval-spec-v1.7 tie-set rule already
specify.

Deliberately out of scope (not requested, and each has its own reason
this module cannot honestly cover it from episode_results.jsonl alone):
  - EVAL.md §5.2 gate/safety invariants - those live in `ledger.jsonl`
    (A3-D only) and `metrics.json`'s own `safety_invariants` block; this
    module does not read ledgers at all.
  - Criterion 4 (A3-LLM - A3-D attribution) and criterion 5 (failure
    injection) - both are dev-only / not-holdout per EVAL.md §7.1 item A
    and the Day 8 contract extraction; holdout has no A3-LLM run to
    attribute against.
  - Audit-sample selection - see docs/DAY8-AUDIT-SAMPLE-RULING.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rrx.sim.run_stage3 import BOOTSTRAP_SEED, N_BOOTSTRAP_RESAMPLES, paired_bootstrap_ci

# EVAL.md §7 criterion 2: "Bounded non-agent arms = {A0, A1, A2 (as
# finally adopted, §4.1)}." A4 is excluded (oracle/reference only,
# EVAL.md:774); A3-LLM has no holdout run to include (EVAL.md §7.1 item A).
BOUNDED_ARMS: tuple[str, ...] = ("A0", "A1", "A2-strengthened")

# EVAL.md §7.1 item A: "Where §7's criteria say 'A3,' they are evaluated
# on holdout against A3-D."
CANDIDATE_ARM = "A3-D"

# EVAL.md §7: "A4 is excluded - oracle/reference, not a deployable
# comparator" - used only for the §7 target's gap calculation.
ORACLE_ARM = "A4"

REQUIRED_ARMS: tuple[str, ...] = (*BOUNDED_ARMS, CANDIDATE_ARM, ORACLE_ARM)

# EVAL.md §5: the two Regime-B primary metrics criterion 2 is evaluated on.
PRIMARY_METRICS: tuple[str, ...] = ("invoice_recovery_rate", "subscription_rescue_rate")

_EPISODE_KEY_FOR_METRIC = {
    "invoice_recovery_rate": "invoice_recovered",
    "subscription_rescue_rate": "subscription_rescued",
}
_CONTACTS_KEY_FOR_METRIC = {
    "invoice_recovery_rate": "contacts_per_invoice_recovered",
    "subscription_rescue_rate": "contacts_per_subscription_rescued",
}


class ArtifactError(RuntimeError):
    """A required artifact is missing, malformed, or internally
    inconsistent. Always raised, never caught-and-continued by any
    function in this module - the caller decides what to do next."""


@dataclass(frozen=True)
class ArmData:
    arm: str
    run_dir: Path
    episode_results: tuple[dict[str, Any], ...]
    metrics: dict[str, Any]


@dataclass(frozen=True)
class BootstrapResult:
    """One paired_bootstrap_ci call's result. `diff` is mean(arm_b) -
    mean(arm_a) - paired_bootstrap_ci's own convention, preserved here
    rather than silently flipped, so a caller reading `diff`'s sign
    against `arm_a`/`arm_b` gets the same meaning the underlying frozen
    procedure produces."""

    arm_a: str
    arm_b: str
    metric: str
    diff: float
    lo: float
    hi: float

    @property
    def excludes_zero(self) -> bool:
        return self.lo > 0 or self.hi < 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm_a": self.arm_a, "arm_b": self.arm_b, "metric": self.metric,
            "diff": self.diff, "lo": self.lo, "hi": self.hi,
            "excludes_zero": self.excludes_zero,
        }


@dataclass(frozen=True)
class ComparatorResult:
    """EVAL.md §7 criterion 2 + the eval-spec-v1.7 tie-set rule's output
    for one metric: the highest-point-estimate bounded arm, plus every
    other bounded arm statistically tied with it on holdout."""

    metric: str
    leader: str
    leader_rate: float
    tied_set: tuple[str, ...]  # includes leader; length 1 = no tie
    pairwise_vs_leader: dict[str, BootstrapResult]  # every OTHER bounded arm vs leader

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "leader": self.leader,
            "leader_rate": self.leader_rate,
            "tied_set": list(self.tied_set),
            "pairwise_vs_leader": {k: v.to_dict() for k, v in self.pairwise_vs_leader.items()},
        }


# ---------------------------------------------------------------------------
# 1. Load + verify (fail loud, never silently continue)
# ---------------------------------------------------------------------------

def _load_episode_results(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "episode_results.jsonl"
    if not path.exists():
        raise ArtifactError(f"missing required artifact: {path}")
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ArtifactError(f"{path}:{lineno}: malformed JSON line: {exc}") from exc
    if not records:
        raise ArtifactError(f"{path}: contains zero records")
    return records


def _load_metrics(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "metrics.json"
    if not path.exists():
        raise ArtifactError(f"missing required artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"{path}: malformed JSON: {exc}") from exc


def verify_episode_indices(
    records: list[dict[str, Any]], expected_indices: Iterable[int], arm: str
) -> None:
    """Raises ArtifactError unless `records` contains exactly one entry
    per index in `expected_indices` - no duplicates, no gaps, no extras.
    Order-independent (holdout is 9000-10999; the writer already
    preserves order, but this check does not rely on it)."""
    expected = set(expected_indices)
    seen = [r["episode_index"] for r in records]
    seen_set = set(seen)

    if len(seen) != len(seen_set):
        dupes = sorted({i for i in seen if seen.count(i) > 1})
        raise ArtifactError(f"{arm}: duplicate episode_index values: {dupes}")

    missing = sorted(expected - seen_set)
    if missing:
        shown = missing[:10]
        suffix = f" ... ({len(missing)} total)" if len(missing) > 10 else ""
        raise ArtifactError(f"{arm}: missing episode indices: {shown}{suffix}")

    extra = sorted(seen_set - expected)
    if extra:
        shown = extra[:10]
        suffix = f" ... ({len(extra)} total)" if len(extra) > 10 else ""
        raise ArtifactError(
            f"{arm}: unexpected episode indices outside the declared range: {shown}{suffix}"
        )

    if len(seen) != len(expected):
        raise ArtifactError(f"{arm}: expected {len(expected)} records, found {len(seen)}")


def recompute_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Independently recomputes the EVAL.md §5 aggregate figures that
    `episode_results.jsonl` alone can derive - the same computation
    `rrx.eval.runner._result_based_metrics` performs, reimplemented here
    from the raw per-episode file rather than imported, so a bug shared
    between the writer and this checker cannot cancel out undetected."""
    n = len(records)
    invoice_recovered = sum(1 for r in records if r["invoice_recovered"])
    rescued = sum(1 for r in records if r["subscription_rescued"])
    total_contacts = sum(r["contacts_sent"] for r in records)
    return {
        "n": n,
        "invoice_recovery_rate": (invoice_recovered / n) if n else None,
        "subscription_rescue_rate": (rescued / n) if n else None,
        "total_contacts": total_contacts,
        "contacts_per_invoice_recovered": (
            (total_contacts / invoice_recovered) if invoice_recovered else None
        ),
        "contacts_per_subscription_rescued": (
            (total_contacts / rescued) if rescued else None
        ),
    }


def verify_recomputed_matches_committed(
    recomputed: dict[str, Any], committed: dict[str, Any], arm: str
) -> None:
    """Exact-match check - no float tolerance is smuggled in, since both
    sides compute the identical ratio the identical way. Mirrors EVAL.md
    §5.2's "a non-zero value is a P0 bug, not a score" discipline, applied
    here to provenance rather than safety."""
    mismatches = [
        (key, recomputed_value, committed.get(key))
        for key, recomputed_value in recomputed.items()
        if committed.get(key) != recomputed_value
    ]
    if mismatches:
        detail = "; ".join(
            f"{k}: recomputed={rv!r} vs committed={cv!r}" for k, rv, cv in mismatches
        )
        raise ArtifactError(
            f"{arm}: recomputed metrics disagree with committed metrics.json: {detail}"
        )


def load_arm_data(arm: str, run_dir: Path, expected_indices: Iterable[int]) -> ArmData:
    """One arm's full load -> verify indices -> recompute -> cross-check
    pass. Raises ArtifactError on the first problem; never returns
    partially-validated data."""
    records = _load_episode_results(run_dir)
    verify_episode_indices(records, expected_indices, arm)
    metrics = _load_metrics(run_dir)
    recomputed = recompute_metrics(records)
    verify_recomputed_matches_committed(recomputed, metrics, arm)
    return ArmData(arm=arm, run_dir=run_dir, episode_results=tuple(records), metrics=metrics)


# ---------------------------------------------------------------------------
# 2. Paired bootstrap - the frozen procedure, invoked with EVAL.md §6's
#    pinned parameters, never a locally-adjusted variant.
# ---------------------------------------------------------------------------

def _values_for(arm_data: ArmData, metric: str) -> list[float]:
    """Per-episode 0/1 vector for a primary metric, sorted by
    episode_index - required for paired_bootstrap_ci's pairing-by-position
    contract. Safe across arms because verify_episode_indices already
    proved every arm shares the identical index set."""
    key = _EPISODE_KEY_FOR_METRIC[metric]
    ordered = sorted(arm_data.episode_results, key=lambda r: r["episode_index"])
    return [float(r[key]) for r in ordered]


def compare(arm_a: ArmData, arm_b: ArmData, metric: str) -> BootstrapResult:
    """paired_bootstrap_ci(a, b) with EVAL.md §6's frozen parameters made
    explicit at the call site (seed 20260826, 10,000 resamples), never
    relying on paired_bootstrap_ci's own defaults happening to still
    match if they ever changed."""
    diff, lo, hi = paired_bootstrap_ci(
        _values_for(arm_a, metric), _values_for(arm_b, metric),
        n_resamples=N_BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED,
    )
    return BootstrapResult(arm_a=arm_a.arm, arm_b=arm_b.arm, metric=metric, diff=diff, lo=lo, hi=hi)


# ---------------------------------------------------------------------------
# 3. Comparator selection + tie-set rule (eval-spec-v1.7, EVAL.md:821-841)
# ---------------------------------------------------------------------------

def select_comparator(bounded_arms: dict[str, ArmData], metric: str) -> ComparatorResult:
    """1. Identify the bounded arm with the highest HOLDOUT point estimate.
    2. The comparator set is that arm plus every other bounded arm whose
    pairwise 95% CI against it (on holdout) includes zero. Computed from
    the HOLDOUT ArmData the caller passes in - this function has no way
    to reach dev data and does not accept it."""
    if set(bounded_arms) != set(BOUNDED_ARMS):
        raise ArtifactError(
            f"select_comparator requires exactly the bounded arms {BOUNDED_ARMS}, "
            f"got {sorted(bounded_arms)}"
        )
    rates = {arm: data.metrics[metric] for arm, data in bounded_arms.items()}
    leader = max(rates, key=rates.get)
    leader_data = bounded_arms[leader]

    pairwise: dict[str, BootstrapResult] = {}
    tied = [leader]
    for arm, data in bounded_arms.items():
        if arm == leader:
            continue
        result = compare(data, leader_data, metric)  # diff = leader - arm
        pairwise[arm] = result
        if not result.excludes_zero:
            tied.append(arm)

    return ComparatorResult(
        metric=metric, leader=leader, leader_rate=rates[leader],
        tied_set=tuple(tied), pairwise_vs_leader=pairwise,
    )


def evaluate_criterion_2(
    candidate: ArmData, comparator: ComparatorResult, bounded_arms: dict[str, ArmData]
) -> dict[str, Any]:
    """A3 (here, A3-D) satisfies criterion 2 on this metric only if its
    holdout rate exceeds EVERY member of the tied set, CI excluding zero
    (eval-spec-v1.7 rule item 4). A single-arm tied set reduces exactly to
    the pre-v1.7 criterion, per rule item 7."""
    per_member: dict[str, Any] = {}
    passed = True
    for member in comparator.tied_set:
        # diff = candidate - member (compare(a, b) returns mean(b) - mean(a))
        result = compare(bounded_arms[member], candidate, comparator.metric)
        per_member[member] = result.to_dict()
        if not (result.excludes_zero and result.diff > 0):
            passed = False
    return {
        "metric": comparator.metric,
        "tied_set": list(comparator.tied_set),
        "per_member": per_member,
        "passed": passed,
    }


def evaluate_criterion_3_contacts(
    candidate: ArmData,
    comparator: ComparatorResult,
    bounded_arms: dict[str, ArmData],
) -> dict[str, Any]:
    """Total contacts and contacts-per-rescue/recovered must be <= EVERY
    tied-set member's (eval-spec-v1.7 rule item 6) - a deterministic
    integer/rate comparison, no bootstrap involved."""
    contacts_key = _CONTACTS_KEY_FOR_METRIC[comparator.metric]
    violations: list[str] = []
    for member in comparator.tied_set:
        m = bounded_arms[member]
        candidate_contacts = candidate.metrics["total_contacts"]
        member_contacts = m.metrics["total_contacts"]
        if candidate_contacts > member_contacts:
            violations.append(
                f"{member}: total_contacts {candidate_contacts} > {member_contacts}"
            )
        c_val, m_val = candidate.metrics.get(contacts_key), m.metrics.get(contacts_key)
        if c_val is not None and m_val is not None and c_val > m_val:
            violations.append(f"{member}: {contacts_key} {c_val} > {m_val}")
    return {
        "metric": comparator.metric,
        "tied_set": list(comparator.tied_set),
        "violations": violations,
        "passed": not violations,
    }


def evaluate_target(
    oracle: ArmData, comparator: ComparatorResult, fraction: float = 0.40
) -> dict[str, Any]:
    """EVAL.md §7's revised target: candidate rate >= best-bounded rate +
    fraction * (A4 rate - best-bounded rate) - computed on HOLDOUT's own
    A4 and best-bounded values only. Dev's illustrative 0.5090/0.5499
    figures (EVAL.md:845-846) are never reused here, per EVAL.md:245's own
    explicit warning against doing so."""
    oracle_rate = oracle.metrics[comparator.metric]
    gap = oracle_rate - comparator.leader_rate
    threshold = comparator.leader_rate + fraction * gap
    return {
        "metric": comparator.metric,
        "oracle_rate": oracle_rate,
        "best_bounded_rate": comparator.leader_rate,
        "gap": gap,
        "fraction": fraction,
        "threshold": threshold,
    }


# ---------------------------------------------------------------------------
# 4. Top-level orchestration - one call, one machine-readable result.
# ---------------------------------------------------------------------------

def analyze_holdout(run_dirs: dict[str, Path], expected_indices: Iterable[int]) -> dict[str, Any]:
    """Loads, verifies, and analyzes all five required holdout arms.
    Raises ArtifactError immediately on any missing arm, missing/malformed
    artifact, index mismatch, or aggregate disagreement - never proceeds
    past a problem to produce a partial result."""
    missing_arms = set(REQUIRED_ARMS) - set(run_dirs)
    if missing_arms:
        raise ArtifactError(f"missing run directories for required arms: {sorted(missing_arms)}")

    expected_indices = list(expected_indices)
    arm_data = {
        arm: load_arm_data(arm, run_dirs[arm], expected_indices) for arm in REQUIRED_ARMS
    }
    bounded = {arm: arm_data[arm] for arm in BOUNDED_ARMS}
    candidate = arm_data[CANDIDATE_ARM]
    oracle = arm_data[ORACLE_ARM]

    per_metric: dict[str, Any] = {}
    for metric in PRIMARY_METRICS:
        comparator = select_comparator(bounded, metric)
        per_metric[metric] = {
            "comparator": comparator.to_dict(),
            "criterion_2": evaluate_criterion_2(candidate, comparator, bounded),
            "criterion_3_contacts": evaluate_criterion_3_contacts(candidate, comparator, bounded),
            "target": evaluate_target(oracle, comparator),
        }

    return {
        "arms_verified": sorted(arm_data),
        "n_episodes_per_arm": len(expected_indices),
        "per_metric": per_metric,
    }
