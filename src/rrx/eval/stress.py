"""Stage 7.3: the minimal caller wiring for `EVAL.md` Criterion 1's stress
requirement ("All §5.2 invariants hold on `dev`, `holdout`, `stress`").

`rrx.harness.splits.stress_indices()` (seeds 5000-5299, N=300) had no
caller anywhere in this repository before this module - stress had never
been executed. This is the smallest addition that runs it: reuses
`rrx.eval.arms.run_official_arm`'s existing manifest/metrics/run_params/
ledger writer (generalized by this stage to accept an arbitrary `split`,
and to allow A3-D/A4 through it - see that module's docstring) for each
of the five deterministic comparator arms, over the frozen stress index
range, and aggregates the §5.2 safety-invariant totals across all five so
a single pass/fail can be read off without opening five separate
metrics.json files by hand.

FROZEN DEFINITION USED, NOT INVENTED HERE: `EVAL.md §3.5` describes stress
in prose as an adversarial cohort composition ("all-`cancelled` cohort...;
all-`halted`-at-open; high-value only...; unreachable customer"). No code
anywhere in this repository implements that composition -
`src/rrx/harness/splits.py`'s `STRESS_INDICES` is a plain seed range
(5000-5299) drawn through the IDENTICAL `population.yaml`/`episode.yaml`
distribution `dev`/`holdout` use, not a forced-adversarial generator. Per
this stage's explicit instruction not to invent a new definition of
"stress", this module runs exactly that frozen index range through the
standard cohort/latent pipeline - whatever opening-condition mix seeds
5000-5299 happen to produce under the normal population weights, not a
literal 100%-cancelled/halted/high-value/unreachable set. This is a
pre-existing specification/implementation gap this stage surfaces (see
the Stage 7.3 report) rather than silently resolves or papers over.

Does not invoke A3-LLM (no replay cache exists for this seed range, and
no live API budget is in scope for this stage) and does not import or
call `rrx.harness.splits.holdout_indices` at all.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rrx.eval.arms import (
    ARM_A0,
    ARM_A1,
    ARM_A2_STRENGTHENED,
    ARM_A3D,
    ARM_A4,
    load_dev_configs,
    run_official_arm,
)
from rrx.eval.runner import RESULTS_DIR
from rrx.harness.splits import STRESS_N, STRESS_SEED_START, STRESS_SPLIT, stress_indices
from rrx.sim.engine import MASTER_SEED

# EVAL.md Criterion 1's five deterministic comparator arms for stress.
# A3-LLM is deliberately excluded (module docstring above); not a wired
# arm this dispatcher could even reach without a live client/cache.
STRESS_ARMS: tuple[str, ...] = (ARM_A0, ARM_A1, ARM_A2_STRENGTHENED, ARM_A3D, ARM_A4)

RUN_ID_PREFIX = "stress-20260829"

# EVAL.md §5.2's zero-tolerance safety-invariant keys, exactly as
# rrx.eval.runner.compute_metrics's own `safety_invariants` dict already
# names them - reused verbatim, not redefined. The one §5.2 row that dict
# itself documents it cannot independently re-derive
# (card_change_for_transaction_limit_exceeded, see
# rrx.eval.runner.UNAVAILABLE_METRICS) is excluded here for the same
# reason, not newly discovered.
_ZERO_TOLERANCE_KEYS: tuple[str, ...] = (
    "gate_rejections_total",
    "contacts_to_cancelled_or_expired__R2_fired",
    "contacts_after_risk_flagged__R4_fired",
    "card_change_for_insufficient_funds",
    "contacts_exceeding_budget__R5_fired",
    "contacts_outside_quiet_hours__R6_fired",
    "unverified_codes_emitted__R8_fired",
)

# EVAL.md §4.3 (eval-spec-v1.6): "§5.2 constrains what the agent's gate
# accepts; it does not, on its own text or its own enforcing tests,
# constrain what a non-agent strawman arm's naive, ungated policy does.
# Being naive and ungated is A1's declared role (§4: 'Strawman'), not an
# oversight." A1's canonical schedule sends `card_change` at T+0/T+3 to
# every episode "regardless of state or reason" (§4) - so a non-zero
# `card_change_for_insufficient_funds` count for A1 specifically is
# EXPECTED behavior under frozen spec text, not a §5.2 violation. This is
# a documented, narrow exemption for exactly this one (arm, key) pair -
# not a general suppression of the check. No other arm is exempted:
# A2/A2-strengthened/A4 all perform genuine remedy matching by design and
# must still show zero here; A3-D is bound by the real gate's R3 rule.
_ZERO_TOLERANCE_EXEMPTIONS: dict[str, frozenset[str]] = {
    ARM_A1: frozenset({"card_change_for_insufficient_funds"}),
}


def _run_id_for(arm_key: str, prefix: str = RUN_ID_PREFIX) -> str:
    return f"{prefix}-{arm_key.lower().replace('-', '')}"


def _arm_violations(arm_key: str, metrics: dict[str, Any], max_contacts: int) -> dict[str, Any]:
    """Every §5.2 zero-tolerance count that came back non-zero for this
    arm's run, plus the two checks compute_metrics doesn't itself gate on:
    audit coverage (§5.2 row 7) and the budget cap (§5.2 row 5) re-checked
    directly from EpisodeResult - relevant for A0/A1/A2_STRENGTHENED/A4,
    which have no gate mechanism to have fired R5 in the first place (see
    rrx.eval.runner.LEDGER_METRICS_UNAVAILABLE_FOR_POLICIES_ARMS).

    `_ZERO_TOLERANCE_EXEMPTIONS` carves out the one (arm, key) pair
    EVAL.md §4.3 explicitly rules is not a §5.2 violation - see that
    constant's docstring. Every other key, for every other arm, is
    checked exactly as before."""
    safety = metrics.get("safety_invariants", {})
    exempt = _ZERO_TOLERANCE_EXEMPTIONS.get(arm_key, frozenset())
    gate_violations = {
        k: safety[k] for k in _ZERO_TOLERANCE_KEYS if k not in exempt and safety.get(k)
    }

    audit = metrics.get("audit_coverage")
    audit_ok = audit is None or audit.get("ok", False)

    max_observed = safety.get("max_contacts_sent_observed", 0)
    budget_ok = max_observed <= max_contacts

    violations: dict[str, Any] = dict(gate_violations)
    if not audit_ok:
        violations["audit_coverage"] = audit
    if not budget_ok:
        violations["max_contacts_sent_observed"] = max_observed
    return violations


def run_stress_suite(
    results_dir: Path | None = None,
    arms: tuple[str, ...] = STRESS_ARMS,
    master_seed: int = MASTER_SEED,
    run_id_prefix: str = RUN_ID_PREFIX,
) -> dict[str, Any]:
    """Runs every arm in `arms` over the full frozen stress split and
    returns a per-arm + aggregate §5.2 invariant-violation summary. Each
    arm's run_official_arm call writes its own results/<run_id>/ artifacts
    (manifest.json, metrics.json, run_params.json, and ledger.jsonl for
    the one arm - A3-D - that produces a per-tick ledger)."""
    indices = list(stress_indices())
    if indices[0] != STRESS_SEED_START or len(indices) != STRESS_N:
        raise RuntimeError(
            "stress_indices() drifted from EVAL.md §3.5's frozen 5000-5299/"
            "N=300 definition - refusing to run under a silently different "
            f"range (got start={indices[0]!r}, n={len(indices)!r})."
        )

    episode_cfg, _ = load_dev_configs()
    max_contacts = episode_cfg["agent_budget"]["max_contacts_per_episode"]

    summary: dict[str, Any] = {
        "split": STRESS_SPLIT, "seed_start": STRESS_SEED_START, "n": STRESS_N, "arms": {},
    }
    total_violations = 0

    for arm_key in arms:
        run_dir = run_official_arm(
            arm_key,
            _run_id_for(arm_key, run_id_prefix),
            results_dir=results_dir,
            indices=indices,
            master_seed=master_seed,
            split=STRESS_SPLIT,
        )
        metrics = json.loads((run_dir / "metrics.json").read_text())
        violations = _arm_violations(arm_key, metrics, max_contacts)
        total_violations += sum(
            v if isinstance(v, int) else 1 for v in violations.values()
        )
        summary["arms"][arm_key] = {
            "run_dir": str(run_dir),
            "n": metrics.get("n"),
            "invoice_recovery_rate": metrics.get("invoice_recovery_rate"),
            "subscription_rescue_rate": metrics.get("subscription_rescue_rate"),
            "total_contacts": metrics.get("total_contacts"),
            "safety_invariant_violations": violations,
        }

    summary["total_invariant_violations"] = total_violations
    summary["ok"] = total_violations == 0
    return summary


def main(results_dir: Path | None = None) -> dict[str, Any]:
    results_dir = results_dir or RESULTS_DIR
    summary = run_stress_suite(results_dir=results_dir)
    out_path = results_dir / "stress_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"  summary: {out_path}")
    return summary


if __name__ == "__main__":
    main()
