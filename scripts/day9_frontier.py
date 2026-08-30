"""Day 9, Stage 4, Part B: dev-only A3-D restraint-threshold frontier.

DEV-ONLY. Never calls rrx.harness.splits.holdout_indices() -- only
dev_indices(). Does not modify src/rrx/agent/, src/rrx/sim/, EVAL.md, the
cost model, holdout artifacts, or the frozen A3-D result. Does not select
a new production policy or create "A3.1" -- this is descriptive evidence
only, per the Stage 4 authorization.

The swept parameter (the literal `2` in src/rrx/agent/policy.py's
`withhold_applies = observations >= 2 and not any_engaged`,
docs/A3-DESIGN.md SS10A.3) has no config key. Rather than edit the frozen
policy module, this script defines a mechanically identical copy of the
16-rule decision table (docs/A3-DESIGN.md SS10A.4) with that one literal
replaced by a parameter -- the same "variant outside the frozen module"
pattern rrx.baselines.a2_variants already established for A2's schedule
variants. src/rrx/agent/policy.py is not imported for its policy logic
(only reason_codes/proposal types are reused) and is never modified.

Grid, seed, and rationale are pre-declared in CHANGELOG.md ("Day 9 Stage
4 -- R-16 adjudication + dev-only frontier, pre-declaration") before this
script was run.

Usage: python scripts/day9_frontier.py
Exact command used to produce results/day9_frontier/: as above, no args.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "day9_frontier"

import sys  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from rrx.agent.proposal import Proposal  # noqa: E402
from rrx.agent.reason_codes import (  # noqa: E402
    ENGAGEMENT_OBSERVED,
    NO_ENGAGEMENT_RESTRAINT,
    POST_HALT_RESCUE,
    REMEDY_MATCH_CARD,
    REMEDY_MATCH_TOPUP,
    RETRY_WINDOW_OPEN,
    RISK_FLAGGED,
)
from rrx.eval.arms import load_dev_configs  # noqa: E402
from rrx.eval.runner import audit_coverage_check, compute_metrics  # noqa: E402
from rrx.features.episode_view import EpisodeView  # noqa: E402
from rrx.harness.runner import run_episode_a3  # noqa: E402
from rrx.harness.splits import DEV_SPLIT, dev_indices  # noqa: E402
from rrx.sim.engine import MASTER_SEED  # noqa: E402

CARD_BROKEN = frozenset({"card_expired", "debit_instrument_blocked", "card_not_enabled_group"})

GRID = [1, 2, 3, 4, 5, 6, 7]
BASELINE_THRESHOLD = 2
BASELINE_REFERENCE_METRICS_PATH = REPO_ROOT / "results" / "a3d-dev-20260828-01" / "metrics.json"


def make_a3d_policy_variant(withhold_threshold: int):
    """Mechanically identical to rrx.agent.policy.a3d_policy (verified by
    the parity check in main()), except the withhold_applies threshold is
    a parameter instead of the literal 2. Every other rule, condition, and
    reason_code is byte-identical to the frozen policy."""

    def _policy(view: EpisodeView) -> Proposal:
        day = view.days_since_first_failure

        observations = len(view.contact_history)
        any_engaged = any(rec.engaged for rec in view.contact_history)
        withhold_applies = observations >= withhold_threshold and not any_engaged

        if view.subscription_state == "active":
            return Proposal(action_type="STOP", remedy=None, rationale="R-01", reason_code=NO_ENGAGEMENT_RESTRAINT)

        if view.decline_code == "payment_risk_check_failed":
            return Proposal(action_type="STOP", remedy=None, rationale="R-02", reason_code=RISK_FLAGGED)

        if view.decline_code == "transaction_limit_exceeded":
            return Proposal(action_type="STOP", remedy=None, rationale="R-03", reason_code=NO_ENGAGEMENT_RESTRAINT)

        if view.decline_code == "bank_technical_error" and view.auto_retries_remaining > 0:
            return Proposal(action_type="WAIT", remedy=None, rationale="R-04", reason_code=RETRY_WINDOW_OPEN)

        if view.decline_code == "bank_technical_error":
            return Proposal(action_type="STOP", remedy=None, rationale="R-05", reason_code=NO_ENGAGEMENT_RESTRAINT)

        if view.decline_code == "insufficient_funds" and view.subscription_state == "halted":
            return Proposal(action_type="STOP", remedy=None, rationale="R-06", reason_code=NO_ENGAGEMENT_RESTRAINT)

        if view.decline_code == "insufficient_funds" and day >= 3:
            return Proposal(action_type="STOP", remedy=None, rationale="R-07", reason_code=NO_ENGAGEMENT_RESTRAINT)

        if view.decline_code == "insufficient_funds" and day == 0:
            return Proposal(action_type="CONTACT", remedy="topup_reminder", rationale="R-08", reason_code=REMEDY_MATCH_TOPUP)

        if view.decline_code == "insufficient_funds" and day == 2 and not withhold_applies:
            return Proposal(
                action_type="CONTACT", remedy="topup_reminder", rationale="R-09",
                reason_code=ENGAGEMENT_OBSERVED if any_engaged else REMEDY_MATCH_TOPUP,
            )

        if view.decline_code == "insufficient_funds":
            return Proposal(
                action_type="WAIT", remedy=None, rationale="R-10",
                reason_code=NO_ENGAGEMENT_RESTRAINT if withhold_applies else RETRY_WINDOW_OPEN,
            )

        if (
            (view.decline_code in CARD_BROKEN or view.decline_code == "ambiguous_decline")
            and view.subscription_state == "halted"
            and day == 5
            and view.budget_remaining >= 1
        ):
            return Proposal(action_type="CONTACT", remedy="card_change", rationale="R-11", reason_code=POST_HALT_RESCUE)

        if view.decline_code in CARD_BROKEN and day == 0:
            return Proposal(action_type="CONTACT", remedy="card_change", rationale="R-12", reason_code=REMEDY_MATCH_CARD)

        if view.decline_code in CARD_BROKEN and day == 3 and not withhold_applies:
            return Proposal(
                action_type="CONTACT", remedy="card_change", rationale="R-13",
                reason_code=ENGAGEMENT_OBSERVED if any_engaged else REMEDY_MATCH_CARD,
            )

        if view.decline_code == "ambiguous_decline" and day == 0:
            return Proposal(action_type="CONTACT", remedy="card_change", rationale="R-14", reason_code=REMEDY_MATCH_CARD)

        if view.decline_code == "ambiguous_decline" and day == 2 and not withhold_applies:
            return Proposal(action_type="CONTACT", remedy="topup_reminder", rationale="R-15", reason_code=REMEDY_MATCH_TOPUP)

        return Proposal(action_type="WAIT", remedy=None, rationale="R-16", reason_code=NO_ENGAGEMENT_RESTRAINT)

    return _policy


def run_variant_over_dev(withhold_threshold: int):
    episode_cfg, population_cfg = load_dev_configs()
    policy = make_a3d_policy_variant(withhold_threshold)
    indices = list(dev_indices())

    results = []
    ledger_records = []
    for i in indices:
        episode_ledger = []

        def _capturing_ledger_record(**kwargs):
            from rrx.agent.ledger import default_ledger_record
            record = default_ledger_record(**kwargs)
            episode_ledger.append(record)
            return record

        result = run_episode_a3(
            DEV_SPLIT, i, policy, episode_cfg, population_cfg,
            master_seed=MASTER_SEED, ledger_record=_capturing_ledger_record,
        )
        results.append(result)
        ledger_records.extend(episode_ledger)

    metrics = compute_metrics(results, ledger_records)
    window_days = episode_cfg["episode"]["window_days"]
    audit = audit_coverage_check(results, indices, ledger_records, window_days, split=DEV_SPLIT)
    metrics["audit_coverage"] = audit
    return metrics


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Parity check: withhold_threshold=2 must reproduce results/a3d-dev-20260828-01/metrics.json ===")
    baseline_metrics = run_variant_over_dev(BASELINE_THRESHOLD)
    with open(BASELINE_REFERENCE_METRICS_PATH, encoding="utf-8") as f:
        reference = json.load(f)

    parity_fields = [
        "invoice_recovery_rate", "subscription_rescue_rate", "total_contacts",
        "contacts_per_invoice_recovered", "contacts_per_subscription_rescued",
        "n", "n_wakeup_ticks", "n_ledger_records_total", "wait_count",
        "escalation_count", "gate_rejection_count",
    ]
    mismatches = []
    for field in parity_fields:
        if baseline_metrics.get(field) != reference.get(field):
            mismatches.append((field, baseline_metrics.get(field), reference.get(field)))

    if mismatches:
        print("PARITY CHECK FAILED. Mismatches:")
        for field, got, expected in mismatches:
            print(f"  {field}: variant={got!r} reference={expected!r}")
        print("STOPPING -- not trusting sweep results. Fix the variant transcription before rerunning.")
        with open(OUT_DIR / "PARITY_CHECK_FAILED.json", "w", encoding="utf-8") as f:
            json.dump({"mismatches": mismatches}, f, indent=2)
        return

    print("PARITY CHECK PASSED -- variant at threshold=2 reproduces the published A3-D dev result exactly.")

    frontier = {}
    for threshold in GRID:
        print(f"\n=== Running dev sweep at withhold_threshold={threshold} ===")
        metrics = run_variant_over_dev(threshold)
        frontier[threshold] = metrics
        out_path = OUT_DIR / f"threshold_{threshold}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        print(f"  invoice_recovery_rate={metrics['invoice_recovery_rate']:.4f}  "
              f"subscription_rescue_rate={metrics['subscription_rescue_rate']:.4f}  "
              f"total_contacts={metrics['total_contacts']}  "
              f"gate_rejections={metrics['safety_invariants']['gate_rejections_total']}")
        print(f"  Wrote {out_path}")

    with open(OUT_DIR / "frontier_all.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in frontier.items()}, f, indent=2)
    print(f"\nWrote {OUT_DIR / 'frontier_all.json'}")

    print("\n=== Distinct behavioral regimes (dedup by outcome signature) ===")
    seen = {}
    for threshold, m in frontier.items():
        sig = (m["invoice_recovery_rate"], m["subscription_rescue_rate"], m["total_contacts"])
        seen.setdefault(sig, []).append(threshold)
    for sig, thresholds in seen.items():
        print(f"  thresholds {thresholds}: invoice={sig[0]:.4f} rescue={sig[1]:.4f} contacts={sig[2]}")


if __name__ == "__main__":
    main()
