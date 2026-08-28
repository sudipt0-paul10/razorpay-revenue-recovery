"""Stage A: the minimal orchestration needed to run the frozen A3-D policy
(`rrx.agent.policy.a3d_policy`) over the official `dev` cohort and produce
one reproducible raw A3-D result.

Entry point for `make eval` (`python -m rrx.eval.runner`).

Explicitly OUT of scope in this pass (Stage B/C work, per the architecture
review): A1/A2-strengthened standalone execution, comparator registration,
EVAL.md §7 comparator selection, A3-LLM, Regime A / cancellation-hazard
valuation, time-to-rescue (EpisodeResult carries no day-of-outcome field -
see UNAVAILABLE_METRICS below), and the full §22 audit-sample deliverable.

This module does not modify src/rrx/sim/*, src/rrx/agent/policy.py,
src/rrx/agent/reason_codes.py, docs/A3-DESIGN.md, EVAL.md, or SIM.md - it
only calls the already-frozen run_episode_a3/a3d_policy in a loop and
records what comes out.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rrx.agent.ledger import LedgerRecord, default_ledger_record, to_json_line
from rrx.agent.policy import a3d_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_SPLIT, dev_indices
from rrx.sim.engine import EpisodeResult, MASTER_SEED
from rrx.sim.latent import load_configs
from rrx.spec.manifest import RunManifest, config_hash, current_git_sha, write_manifest

# ---------------------------------------------------------------------------
# Fixed identity for this first official run (per instruction, not invented
# as a general run-id scheme - a real naming convention is Stage B/C work).
# ---------------------------------------------------------------------------
RUN_ID = "a3d-dev-20260828-01"
ARM = "A3-D"
REGIME = "B"
# The currently-governing eval-spec version at the time a NEW run executes
# via this module (main(), or rrx.eval.arms.run_official_arm(), which
# reads this same constant). Distinct from, and more precise than,
# configs/model_params.yaml's stale `spec_version: eval-spec-v1-draft`
# field, which is not updated here - not this module's file to edit.
#
# Bumped eval-spec-v1.5 -> eval-spec-v1.6 (Stage 5D pre-run validation,
# A.4): eval-spec-v1.6 (EVAL.md §4.3, [CONSEQUENTIAL-2], commit c75d548,
# tag eval-spec-v1.6) is HEAD's tagged state as of any run launched now.
# The ALREADY-WRITTEN results/a3d-dev-20260828-01/manifest.json correctly
# still says "eval-spec-v1.5" - that run executed under, and reports, the
# spec version that actually governed it at the time (main() must never
# be called again per the standing "do not rerun A3-D" rule, so this
# constant's only live consumer going forward is the comparator-arm path).
SPEC_VERSION = "eval-spec-v1.6"
# No sweep cell is applied in this run - baseline configs only.
SWEEP_CELL = "baseline"
# A3-D never calls an LLM (rrx.agent.policy.a3d_policy is a pure function);
# model_version/llm_cost_inr are the frozen schema's LLM-only fields.
MODEL_VERSION: str | None = None
LLM_COST_INR: float | None = None

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "results"

# config_hash scope decision (rrx.spec.manifest.config_hash's docstring
# leaves "which configs are in scope" to the caller): exactly the two files
# rrx.sim.latent.load_configs() reads and that materially determine this
# run's cohort/latent draws and episode mechanics. model_params.yaml is not
# included - no sweep cell is applied (SWEEP_CELL = "baseline"). costs.yaml
# is not included - this run computes no Regime-A/cost figures. Documented
# here rather than decided silently; see the architecture review's item 11.
CONFIG_FILES_IN_SCOPE: tuple[str, ...] = ("episode.yaml", "population.yaml")


class ResultsDirectoryExistsError(RuntimeError):
    """Raised instead of silently overwriting a prior run's artifacts."""


# ---------------------------------------------------------------------------
# 1. Run the real A3-D path over the dev cohort, capturing every ledger tick.
# ---------------------------------------------------------------------------

def run_a3d_dev_cohort(
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    indices: list[int] | range,
    master_seed: int = MASTER_SEED,
) -> tuple[list[EpisodeResult], list[LedgerRecord]]:
    """Runs the frozen a3d_policy through the frozen run_episode_a3 for every
    index in `indices`, in order. Uses run_episode_a3's existing
    `ledger_record` injection point to capture every LedgerRecord as a side
    effect - no change to rrx.harness.runner or rrx.agent.ledger (the
    injected callable's return value is what the runner already discards;
    the wrapper below only adds a side effect, mirroring the exact pattern
    tests/test_ledger_completeness.py already uses).

    Does not catch per-episode exceptions: if simulating any single episode
    raises, this function raises too, and the whole run stops - episodes
    are never silently dropped.
    """
    results: list[EpisodeResult] = []
    ledger_records: list[LedgerRecord] = []

    for i in indices:
        episode_ledger: list[LedgerRecord] = []

        def _capturing_ledger_record(**kwargs: Any) -> LedgerRecord:
            record = default_ledger_record(**kwargs)
            episode_ledger.append(record)
            return record

        result = run_episode_a3(
            DEV_SPLIT,
            i,
            a3d_policy,
            episode_cfg,
            population_cfg,
            master_seed=master_seed,
            ledger_record=_capturing_ledger_record,
        )
        results.append(result)
        ledger_records.extend(episode_ledger)

    return results, ledger_records


# ---------------------------------------------------------------------------
# 2. Metrics - only what is already directly computable from EpisodeResult /
#    LedgerRecord as they exist today. Nothing here is a new metric
#    definition; each one cites the EVAL.md/docs/A3-DESIGN.md source it
#    reproduces.
# ---------------------------------------------------------------------------

# EVAL.md §5's pre-registered primary metric this run cannot produce, and
# why: EpisodeResult (frozen in src/rrx/sim/engine.py) carries no
# day-of-outcome field for ANY arm, so "median and p90 time-to-rescue"
# has no data source without either extending that frozen dataclass or
# re-simulating every episode once per day via capture_view_at_day (~30x
# cost). Neither is done in this pass - see the architecture review's
# item 11.4. Regime A (net value, cancellation-hazard valuation) is out of
# scope per instruction, and separately: the cancellation-hazard mechanic
# EVAL.md §3.3 describes is not implemented anywhere in src/rrx/sim/
# (confirmed: src/rrx/sim/latent.py's own SUBSTREAM_NAMES docstring states
# the "cancellation_hazard" substream is "declared here for completeness
# only - nothing in this module invokes them") - a pre-existing simulator
# gap, not something Stage A introduces or can work around.
UNAVAILABLE_METRICS: dict[str, str] = {
    "median_time_to_rescue_days": (
        "EpisodeResult has no day-of-outcome field for any arm; would "
        "require extending the frozen dataclass or re-simulating every "
        "episode per-day. Not implemented in this pass."
    ),
    "p90_time_to_rescue_days": (
        "Same cause as median_time_to_rescue_days."
    ),
    "regime_a_net_value": (
        "Out of scope for Stage A. Separately: EVAL.md §3.3's "
        "cancellation-hazard mechanic is not implemented in "
        "src/rrx/sim/ (latent.py's cancellation_hazard substream is "
        "reserved but never drawn) - a pre-existing simulator gap."
    ),
    "card_change_for_transaction_limit_exceeded": (
        "EpisodeResult only tracks the insufficient_funds remedy-match "
        "case (card_change_sent_for_insufficient_funds); LedgerRecord "
        "does not store decline_code (only a view_hash), so this specific "
        "row of EVAL.md §5.2's remedy-match gate cannot be independently "
        "re-verified from this run's own aggregate outputs. It is already "
        "exhaustively proven at the policy level by "
        "tests/test_a3d_policy.py's totality tests (40/40)."
    ),
}


def _rate(numerator: int, denominator: int) -> float | None:
    return (numerator / denominator) if denominator else None


def _result_based_metrics(results: list[EpisodeResult]) -> dict[str, Any]:
    """The subset of compute_metrics' output derivable from EpisodeResult
    alone, with no ledger involved - identical for every arm, since every
    arm (A0/A1/A2-family via rrx.sim.engine.run_episode, A3-D via
    rrx.harness.runner.run_episode_a3) returns the same EpisodeResult
    dataclass (rrx.sim.engine._finalize is reused unmodified by both
    runners). Extracted so Stage B's ledger-less arms (§7: rrx.sim.engine
    has no gate/ledger mechanism at all - see compute_metrics_results_only)
    reuse this exact logic rather than a second copy of it."""
    n = len(results)
    invoice_recovered_count = sum(r.invoice_recovered for r in results)
    rescued_count = sum(r.subscription_rescued for r in results)
    total_contacts = sum(r.contacts_sent for r in results)
    return {
        "n": n,
        "invoice_recovery_rate": invoice_recovered_count / n if n else None,
        "subscription_rescue_rate": rescued_count / n if n else None,
        "total_contacts": total_contacts,
        "contacts_per_invoice_recovered": _rate(total_contacts, invoice_recovered_count),
        "contacts_per_subscription_rescued": _rate(total_contacts, rescued_count),
        "card_change_for_insufficient_funds": sum(
            r.card_change_sent_for_insufficient_funds for r in results
        ),
        "max_contacts_sent_observed": max((r.contacts_sent for r in results), default=0),
    }


def compute_metrics(
    results: list[EpisodeResult],
    ledger_records: list[LedgerRecord],
) -> dict[str, Any]:
    base = _result_based_metrics(results)

    wakeup_records = [r for r in ledger_records if r.tick_type == "wakeup"]
    n_wakeups = len(wakeup_records)

    tick_type_distribution: dict[str, int] = {}
    for rec in ledger_records:
        tick_type_distribution[rec.tick_type] = tick_type_distribution.get(rec.tick_type, 0) + 1

    reason_code_distribution: dict[str, int] = {}
    for rec in wakeup_records:
        code = rec.reason_code or "<missing>"
        reason_code_distribution[code] = reason_code_distribution.get(code, 0) + 1

    gate_rejections = [r for r in wakeup_records if r.gate_verdict == "reject"]
    gate_rule_fired_distribution: dict[str, int] = {}
    for rec in gate_rejections:
        rule = rec.gate_rule_fired or "<missing>"
        gate_rule_fired_distribution[rule] = gate_rule_fired_distribution.get(rule, 0) + 1

    # EVAL.md §5.3 amendment 3: escalation rate = STOP decisions with
    # reason_code=risk_flagged, over wake-up decisions.
    escalation_count = sum(1 for r in wakeup_records if r.reason_code == "risk_flagged")

    # EVAL.md §5.3 amendment 2: wait_rate = WAIT decisions / wake-up decisions
    # ("This is the restraint metric."). executed_action is a dict with
    # "action_type"; WAIT is recorded there whenever the executed action was
    # WAIT (including a rejected/unexecutable proposal - see
    # rrx.harness.runner's executor step, which maps those to WAIT too).
    wait_count = sum(
        1 for r in wakeup_records
        if r.executed_action is not None and r.executed_action.get("action_type") == "WAIT"
    )

    # --- Safety invariants (EVAL.md §5.2), each directly re-verifiable from
    # this run's own outputs (see UNAVAILABLE_METRICS for the one row that
    # is not independently re-derivable this way). ---
    safety_invariants = {
        "gate_rejections_total": len(gate_rejections),  # must be 0, §10A.6
        "contacts_to_cancelled_or_expired__R2_fired": gate_rule_fired_distribution.get("R2", 0),
        "contacts_after_risk_flagged__R4_fired": gate_rule_fired_distribution.get("R4", 0),
        "card_change_for_insufficient_funds": base["card_change_for_insufficient_funds"],
        "contacts_exceeding_budget__R5_fired": gate_rule_fired_distribution.get("R5", 0),
        "max_contacts_sent_observed": base["max_contacts_sent_observed"],
        "contacts_outside_quiet_hours__R6_fired": gate_rule_fired_distribution.get("R6", 0),
        "unverified_codes_emitted__R8_fired": gate_rule_fired_distribution.get("R8", 0),
    }

    # Audit coverage (§5.2 row 7) needs the real episode indices to build
    # episode_id -> expected-tick-count, which this function does not
    # receive - computed separately by audit_coverage_check() below and
    # merged into this dict by the caller (main()).

    return {
        "n": base["n"],
        "invoice_recovery_rate": base["invoice_recovery_rate"],
        "subscription_rescue_rate": base["subscription_rescue_rate"],
        "total_contacts": base["total_contacts"],
        "contacts_per_invoice_recovered": base["contacts_per_invoice_recovered"],
        "contacts_per_subscription_rescued": base["contacts_per_subscription_rescued"],
        "tick_type_distribution": tick_type_distribution,
        "reason_code_distribution_wakeup_ticks": reason_code_distribution,
        "gate_rejection_count": len(gate_rejections),
        "gate_rejection_rate_of_wakeups": _rate(len(gate_rejections), n_wakeups),
        "gate_rule_fired_distribution": gate_rule_fired_distribution,
        "escalation_count": escalation_count,
        "escalation_rate_of_wakeups": _rate(escalation_count, n_wakeups),
        "wait_count": wait_count,
        "wait_rate_of_wakeups": _rate(wait_count, n_wakeups),
        "n_wakeup_ticks": n_wakeups,
        "n_ledger_records_total": len(ledger_records),
        "safety_invariants": safety_invariants,
        "unavailable_metrics": UNAVAILABLE_METRICS,
    }


# rrx.sim.engine.run_episode / the _POLICIES arm interface (A0, A1, A2 and
# its variants) has NO gate, NO EpisodeView, NO Proposal/reason_code
# taxonomy, and NO per-tick ledger of any kind - docs/A3-DESIGN.md §2
# deliberately keeps that machinery A3-only. So for these arms,
# tick_type/reason_code distributions, gate rejections, escalation rate,
# and wait_rate are not "zero" (which would wrongly imply "checked, none
# found") - they are UNDEFINED for this arm's architecture. This dict names
# each ledger-derived key compute_metrics() reports and why it has no
# counterpart here, rather than silently reporting zeros for a concept
# that does not exist for this arm.
LEDGER_METRICS_UNAVAILABLE_FOR_POLICIES_ARMS: dict[str, str] = {
    key: (
        "rrx.sim.engine.run_episode (the arm interface A0/A1/A2-family use) "
        "has no gate/ledger/reason_code mechanism at all - only A3-D/A3-LLM, "
        "run via rrx.harness.runner.run_episode_a3, produce per-tick ledger "
        "records. Not zero-because-verified; not applicable to this arm."
    )
    for key in (
        "tick_type_distribution",
        "reason_code_distribution_wakeup_ticks",
        "gate_rejection_count",
        "gate_rejection_rate_of_wakeups",
        "gate_rule_fired_distribution",
        "escalation_count",
        "escalation_rate_of_wakeups",
        "wait_count",
        "wait_rate_of_wakeups",
        "n_wakeup_ticks",
        "n_ledger_records_total",
        "audit_coverage",
        "contacts_to_cancelled_or_expired__R2_fired",
        "contacts_after_risk_flagged__R4_fired",
        "contacts_exceeding_budget__R5_fired",
        "contacts_outside_quiet_hours__R6_fired",
        "unverified_codes_emitted__R8_fired",
    )
}


def compute_metrics_results_only(results: list[EpisodeResult]) -> dict[str, Any]:
    """The metrics computable for arms run through rrx.sim.engine.run_episode
    (A0, A1 once canonical, A2, A2_CORRECTED_V1, A2_STRENGTHENED) - every
    EpisodeResult-derived figure compute_metrics() reports for A3-D, using
    the identical shared logic (_result_based_metrics), plus an explicit
    manifest of which of compute_metrics()'s ledger-derived fields have no
    counterpart here and why (see LEDGER_METRICS_UNAVAILABLE_FOR_POLICIES_
    ARMS) rather than silently omitting them."""
    base = _result_based_metrics(results)
    base["safety_invariants"] = {
        "card_change_for_insufficient_funds": base["card_change_for_insufficient_funds"],
        "max_contacts_sent_observed": base["max_contacts_sent_observed"],
    }
    base["unavailable_metrics"] = dict(UNAVAILABLE_METRICS)
    base["ledger_derived_metrics_unavailable_for_this_arm"] = (
        LEDGER_METRICS_UNAVAILABLE_FOR_POLICIES_ARMS
    )
    return base


def audit_coverage_check(
    results: list[EpisodeResult],
    indices: list[int],
    ledger_records: list[LedgerRecord],
    window_days: int,
) -> dict[str, Any]:
    """EVAL.md §5.2 row 7 ("actions with no audit record: 0"), reproduced at
    full-cohort scale via the same check tests/test_ledger_completeness.py
    already performs at n=100."""
    ticks_per_episode: dict[str, int] = {}
    for rec in ledger_records:
        ticks_per_episode[rec.episode_id] = ticks_per_episode.get(rec.episode_id, 0) + 1

    expected_full = window_days + 1
    violations = []
    for i, result in zip(indices, results):
        episode_id = f"{DEV_SPLIT}-{i}"
        n_records = ticks_per_episode.get(episode_id, 0)
        is_cancelled_at_open = result.opening_condition_key == "subscription_cancelled_by_customer"
        expected = 0 if is_cancelled_at_open else expected_full
        if n_records != expected:
            violations.append(
                {"episode_id": episode_id, "expected": expected, "actual": n_records}
            )
    return {
        "episodes_checked": len(indices),
        "violations": violations,
        "ok": not violations,
    }


# ---------------------------------------------------------------------------
# 3. Manifest + the run-parameter record the frozen 11-field schema cannot
#    hold (split/index range - see the architecture review's item 11.3).
# ---------------------------------------------------------------------------

def write_run_params(
    run_dir: Path,
    *,
    split: str,
    indices: list[int],
    master_seed: int,
    arm: str = ARM,
    policy: str = "rrx.agent.policy.a3d_policy",
    runner_path: str = "rrx.harness.runner.run_episode_a3",
) -> Path:
    """rrx.spec.manifest.RunManifest is frozen at exactly 11 fields and has
    no split/index-range field; adding a 12th requires an EVAL.md §6
    amendment, which is not this module's call to make. This sidecar file
    is NOT part of that frozen schema and does not modify it - it exists
    only because EVAL.md §6 also requires every run to be "reproducible via
    `make eval RUN=<run_id>`", and a manifest with seed=20260825 alone
    cannot satisfy that without also recording which split/indices were
    used. Deliberately separate from manifest.json; flagged in the final
    report as a Stage A addition, not a silent schema change.

    `arm`/`policy`/`runner_path` default to Stage A's A3-D-specific values
    so main()'s existing call site (below) is unaffected - this
    generalization is what Stage B's arms.py reuses for A0/A2-family runs,
    which use a different policy callable and rrx.sim.engine.run_episode
    (not run_episode_a3) as their runner."""
    out_path = run_dir / "run_params.json"
    out_path.write_text(
        json.dumps(
            {
                "split": split,
                "index_start": indices[0],
                "index_end": indices[-1],
                "n": len(indices),
                "master_seed": master_seed,
                "arm": arm,
                "policy": policy,
                "runner": runner_path,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return out_path


# ---------------------------------------------------------------------------
# 4. main()
# ---------------------------------------------------------------------------

def main(
    results_dir: Path | None = None,
    run_id: str = RUN_ID,
    indices: list[int] | None = None,
) -> Path:
    results_dir = results_dir or RESULTS_DIR
    run_dir = results_dir / run_id

    if run_dir.exists():
        raise ResultsDirectoryExistsError(
            f"{run_dir} already exists - stopping rather than overwriting a "
            "prior run's artifacts. Choose a different run_id or remove the "
            "existing directory deliberately, outside this driver."
        )

    episode_cfg, population_cfg = load_configs()
    window_days = episode_cfg["episode"]["window_days"]
    resolved_indices = list(indices if indices is not None else dev_indices())

    start = time.monotonic()
    results, ledger_records = run_a3d_dev_cohort(
        episode_cfg, population_cfg, resolved_indices, master_seed=MASTER_SEED
    )
    wall_clock_seconds = time.monotonic() - start

    if len(results) != len(resolved_indices):
        raise RuntimeError(
            f"episode count mismatch: expected {len(resolved_indices)}, got {len(results)} "
            "- an episode was dropped rather than raising, which should not happen."
        )

    metrics = compute_metrics(results, ledger_records)
    audit = audit_coverage_check(results, resolved_indices, ledger_records, window_days)
    metrics["audit_coverage"] = audit

    run_dir.mkdir(parents=True, exist_ok=False)

    ledger_path = run_dir / "ledger.jsonl"
    with open(ledger_path, "w", encoding="utf-8") as fh:
        for rec in ledger_records:
            fh.write(to_json_line(rec) + "\n")

    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))

    manifest = RunManifest(
        git_sha=current_git_sha(REPO_ROOT),
        spec_version=SPEC_VERSION,
        config_hash=config_hash(*(REPO_ROOT / "configs" / f for f in CONFIG_FILES_IN_SCOPE)),
        seed=MASTER_SEED,
        arm=ARM,
        regime=REGIME,
        sweep_cell=SWEEP_CELL,
        model_version=MODEL_VERSION,
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        wall_clock_seconds=wall_clock_seconds,
        llm_cost_inr=LLM_COST_INR,
    )
    manifest_path = write_manifest(manifest, run_id, results_dir)
    write_run_params(
        run_dir, split=DEV_SPLIT, indices=resolved_indices, master_seed=MASTER_SEED
    )

    print(f"Run {run_id} complete: n={len(results)}, wall_clock={wall_clock_seconds:.1f}s")
    print(f"  manifest: {manifest_path}")
    print(f"  ledger:   {ledger_path}")
    print(f"  metrics:  {metrics_path}")
    print(json.dumps(metrics, indent=2, sort_keys=True))

    return run_dir


if __name__ == "__main__":
    main()
