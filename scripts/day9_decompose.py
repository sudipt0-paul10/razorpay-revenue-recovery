"""Day 9, Stage 2 diagnostic: paired recovery-deficit decomposition.

NOT part of the evaluation harness. Does not import rrx.agent or rrx.sim.
Read-only with respect to every file under results/holdout/ -- opens them
in read ("r") mode only, never writes to results/holdout/, never touches
results/holdout/*/SHA256SUMS, and never calls anything resembling
holdout_indices(authorized=True). Writes exclusively to
results/day9_decomposition/.

Implements the bucket decomposition pre-declared in CHANGELOG.md
("Day 9 Stage 2 -- paired recovery-deficit decomposition, pre-declaration")
BEFORE this script is executed against real data. Do not edit the bucket
logic after seeing results; if the logic needs to change, that is a new
pre-declaration, not a silent edit here.

Usage: python scripts/day9_decompose.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_ROOT = REPO_ROOT / "results" / "holdout" / "4d45db461943"
OUT_DIR = REPO_ROOT / "results" / "day9_decomposition"

COMPARATORS = ["a1", "a2_strengthened"]


def load_episode_results(arm_dir: Path) -> dict[int, dict]:
    out = {}
    with open(arm_dir / "episode_results.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            out[row["episode_index"]] = row
    return out


def load_a3d_ledger_by_episode(ledger_path: Path) -> dict[int, list[dict]]:
    by_ep: dict[int, list[dict]] = defaultdict(list)
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            ep_id = rec["episode_id"]  # "holdout-9000"
            idx = int(ep_id.split("-")[1])
            by_ep[idx].append(rec)
    return by_ep


def summarize_a3d_episode(records: list[dict]) -> dict:
    """Derive STOP flag, last-wakeup-tick day, reason-code trail, tick_type counts."""
    records_sorted = sorted(records, key=lambda r: r["tick"])
    wakeups = [r for r in records_sorted if r["tick_type"] == "wakeup"]
    stop_ticks = [
        r["tick"]
        for r in wakeups
        if (r.get("executed_action") or {}).get("action_type") == "STOP"
    ]
    tick_type_counts = Counter(r["tick_type"] for r in records_sorted)
    reason_code_trail = [r.get("reason_code") for r in wakeups if r.get("reason_code")]
    last_wakeup_tick = wakeups[-1]["tick"] if wakeups else None
    last_wakeup_reason = wakeups[-1].get("reason_code") if wakeups else None
    return {
        "stop_flag": len(stop_ticks) > 0,
        "first_stop_tick": min(stop_ticks) if stop_ticks else None,
        "n_wakeups": len(wakeups),
        "last_wakeup_tick": last_wakeup_tick,
        "last_wakeup_reason_code": last_wakeup_reason,
        "reason_code_trail": reason_code_trail,
        "tick_type_counts": dict(tick_type_counts),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    a3d_results = load_episode_results(HOLDOUT_ROOT / "a3_d")
    a3d_ledger_by_ep = load_a3d_ledger_by_episode(HOLDOUT_ROOT / "a3_d" / "ledger.jsonl")
    a3d_summary_by_ep = {
        idx: summarize_a3d_episode(recs) for idx, recs in a3d_ledger_by_ep.items()
    }

    n_a3d = len(a3d_results)
    assert n_a3d == 2000, f"expected 2000 A3-D episodes, got {n_a3d}"

    all_out = {}

    for comp_key in COMPARATORS:
        comp_results = load_episode_results(HOLDOUT_ROOT / comp_key)
        assert len(comp_results) == 2000, (
            f"expected 2000 {comp_key} episodes, got {len(comp_results)}"
        )

        # Exact index-set parity check (join integrity)
        idx_a3d = set(a3d_results.keys())
        idx_comp = set(comp_results.keys())
        assert idx_a3d == idx_comp, f"index mismatch between a3_d and {comp_key}"

        both = []
        neither = []
        comp_only = []  # comparator recovered, A3-D did not (the deficit population)
        a3d_only = []  # A3-D recovered, comparator did not

        for idx in sorted(idx_a3d):
            a3d_row = a3d_results[idx]
            comp_row = comp_results[idx]
            a3d_rec = a3d_row["invoice_recovered"]
            comp_rec = comp_row["invoice_recovered"]
            if a3d_rec and comp_rec:
                both.append(idx)
            elif (not a3d_rec) and (not comp_rec):
                neither.append(idx)
            elif comp_rec and not a3d_rec:
                comp_only.append(idx)
            elif a3d_rec and not comp_rec:
                a3d_only.append(idx)

        n_total = len(idx_a3d)
        rate_diff_from_pairs = (len(comp_only) - len(a3d_only)) / n_total

        # ---- Bucket decomposition of comp_only (the deficit population) ----
        bucket_A = []  # fewer contacts, lost
        bucket_A_D1 = []  # STOP-attributable subset of A
        bucket_A_D2 = []  # other fewer-contact loss subset of A
        bucket_E_same_contacts = []  # equal contacts (Bucket C candidate, NOT IDENTIFIABLE -> E)
        bucket_E_more_contacts = []  # A3-D used MORE contacts yet still lost

        for idx in comp_only:
            a3d_contacts = a3d_results[idx]["contacts_sent"]
            comp_contacts = comp_results[idx]["contacts_sent"]
            if a3d_contacts < comp_contacts:
                bucket_A.append(idx)
                if a3d_summary_by_ep.get(idx, {}).get("stop_flag"):
                    bucket_A_D1.append(idx)
                else:
                    bucket_A_D2.append(idx)
            elif a3d_contacts == comp_contacts:
                bucket_E_same_contacts.append(idx)
            else:
                bucket_E_more_contacts.append(idx)

        # ---- Bucket B: context only, both recovered, A3-D fewer contacts ----
        bucket_B = [
            idx
            for idx in both
            if a3d_results[idx]["contacts_sent"] < comp_results[idx]["contacts_sent"]
        ]

        # reconciliation
        reconciled_comp_only = (
            len(bucket_A) + len(bucket_E_same_contacts) + len(bucket_E_more_contacts)
        )
        recon_ok = reconciled_comp_only == len(comp_only)

        # ---- Stratifications over comp_only (deficit population) ----
        def decline_strat(indices):
            c = Counter(a3d_results[i]["opening_condition_key"] for i in indices)
            return dict(c)

        def day_strat(indices):
            c = Counter()
            for i in indices:
                d = a3d_summary_by_ep.get(i, {}).get("last_wakeup_tick")
                c[d] += 1
            return {str(k): v for k, v in sorted(c.items(), key=lambda kv: (kv[0] is None, kv[0]))}

        def reason_code_strat(indices):
            c = Counter()
            for i in indices:
                rc = a3d_summary_by_ep.get(i, {}).get("last_wakeup_reason_code")
                c[rc] += 1
            return dict(c)

        def tick_type_strat(indices):
            agg = Counter()
            for i in indices:
                for k, v in a3d_summary_by_ep.get(i, {}).get("tick_type_counts", {}).items():
                    agg[k] += v
            return dict(agg)

        def examples(indices, n=3):
            out = []
            for i in indices[:n]:
                s = a3d_summary_by_ep.get(i, {})
                out.append(
                    {
                        "episode_index": i,
                        "opening_condition_key": a3d_results[i]["opening_condition_key"],
                        "invoice_amount_inr": a3d_results[i]["invoice_amount_inr"],
                        "a3d_contacts_sent": a3d_results[i]["contacts_sent"],
                        "comp_contacts_sent": comp_results[i]["contacts_sent"],
                        "a3d_stop_flag": s.get("stop_flag"),
                        "a3d_last_wakeup_tick": s.get("last_wakeup_tick"),
                        "a3d_last_wakeup_reason_code": s.get("last_wakeup_reason_code"),
                        "a3d_reason_code_trail": s.get("reason_code_trail"),
                    }
                )
            return out

        result = {
            "comparator": comp_key,
            "n_total": n_total,
            "confusion_matrix": {
                "both_recovered": len(both),
                "neither_recovered": len(neither),
                "comparator_only_recovered": len(comp_only),
                "a3d_only_recovered": len(a3d_only),
            },
            "rate_diff_from_pairs_comparator_minus_a3d": rate_diff_from_pairs,
            "buckets": {
                "A_fewer_contacts_lost": {
                    "count": len(bucket_A),
                    "pct_of_paired": len(bucket_A) / n_total,
                    "contribution_to_rate_diff": len(bucket_A) / n_total,
                    "D1_stop_attributable": {
                        "count": len(bucket_A_D1),
                        "pct_of_paired": len(bucket_A_D1) / n_total,
                        "examples": examples(bucket_A_D1),
                    },
                    "D2_other_fewer_contact_loss": {
                        "count": len(bucket_A_D2),
                        "pct_of_paired": len(bucket_A_D2) / n_total,
                        "examples": examples(bucket_A_D2),
                    },
                    "decline_code_strat": decline_strat(bucket_A),
                    "day_strat_last_a3d_wakeup_tick": day_strat(bucket_A),
                },
                "B_fewer_contacts_recovery_preserved_context_only": {
                    "count": len(bucket_B),
                    "pct_of_paired": len(bucket_B) / n_total,
                    "contribution_to_rate_diff": 0.0,
                },
                "C_same_contacts_timing": {
                    "status": "NOT IDENTIFIABLE from available artifacts",
                    "reason": (
                        "Neither a1 nor a2_strengthened produces a ledger or any "
                        "per-day contact record; only a total contacts_sent per "
                        "episode exists for those arms. Episodes with equal contact "
                        "counts but differing outcomes are routed to Bucket E and "
                        "reported there as 'same_contacts' for transparency."
                    ),
                    "would_be_count_if_not_excluded": len(bucket_E_same_contacts),
                },
                "E_other_unexplained": {
                    "same_contacts_subtotal": {
                        "count": len(bucket_E_same_contacts),
                        "pct_of_paired": len(bucket_E_same_contacts) / n_total,
                        "decline_code_strat": decline_strat(bucket_E_same_contacts),
                        "examples": examples(bucket_E_same_contacts),
                    },
                    "more_contacts_subtotal": {
                        "count": len(bucket_E_more_contacts),
                        "pct_of_paired": len(bucket_E_more_contacts) / n_total,
                        "decline_code_strat": decline_strat(bucket_E_more_contacts),
                        "examples": examples(bucket_E_more_contacts),
                    },
                    "total_count": len(bucket_E_same_contacts) + len(bucket_E_more_contacts),
                    "total_pct_of_paired": (
                        (len(bucket_E_same_contacts) + len(bucket_E_more_contacts)) / n_total
                    ),
                    "total_contribution_to_rate_diff": (
                        (len(bucket_E_same_contacts) + len(bucket_E_more_contacts)) / n_total
                    ),
                },
            },
            "reconciliation": {
                "comp_only_count": len(comp_only),
                "sum_A_plus_E": reconciled_comp_only,
                "matches": recon_ok,
                "a3d_only_count": len(a3d_only),
                "signed_check_rate_diff": (
                    (
                        len(bucket_A) + len(bucket_E_same_contacts)
                        + len(bucket_E_more_contacts) - len(a3d_only)
                    ) / n_total
                ),
                "matches_pairwise_rate_diff": abs(
                    (
                        (
                            len(bucket_A) + len(bucket_E_same_contacts)
                            + len(bucket_E_more_contacts) - len(a3d_only)
                        ) / n_total
                    )
                    - rate_diff_from_pairs
                )
                < 1e-12,
            },
            "stop_divergence_subgroup": {
                "count": len(bucket_A_D1),
                "pct_of_comp_only": len(bucket_A_D1) / len(comp_only) if comp_only else None,
                "decline_code_strat": decline_strat(bucket_A_D1),
                "day_strat_first_stop_tick": {
                    str(k): v
                    for k, v in sorted(
                        Counter(
                            a3d_summary_by_ep[i]["first_stop_tick"] for i in bucket_A_D1
                        ).items(),
                        key=lambda kv: (kv[0] is None, kv[0]),
                    )
                },
                "reason_code_at_stop": reason_code_strat(bucket_A_D1),
            },
            "reason_code_mechanism_all_comp_only": reason_code_strat(comp_only),
            "tick_type_mechanism_all_comp_only": tick_type_strat(comp_only),
            "bucket_B_examples": examples(bucket_B),
            "a3d_only_examples": examples(a3d_only),
        }

        all_out[comp_key] = result

        out_path = OUT_DIR / f"decomposition_{comp_key}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {out_path}")

    with open(OUT_DIR / "decomposition_all.json", "w", encoding="utf-8") as f:
        json.dump(all_out, f, indent=2)
    print(f"Wrote {OUT_DIR / 'decomposition_all.json'}")

    # Console summary
    for comp_key, r in all_out.items():
        print(f"\n=== {comp_key} ===")
        print("confusion_matrix:", r["confusion_matrix"])
        print(
            "rate_diff_from_pairs (comparator - a3d):",
            r["rate_diff_from_pairs_comparator_minus_a3d"],
        )
        b = r["buckets"]
        a_bucket = b["A_fewer_contacts_lost"]
        print("Bucket A (fewer contacts, lost):", a_bucket["count"])
        print("  D1 (STOP-attributable):", a_bucket["D1_stop_attributable"]["count"])
        print(
            "  D2 (other fewer-contact loss):",
            a_bucket["D2_other_fewer_contact_loss"]["count"],
        )
        print(
            "Bucket B (fewer contacts, preserved, context):",
            b["B_fewer_contacts_recovery_preserved_context_only"]["count"],
        )
        print(
            "Bucket C: NOT IDENTIFIABLE; same-contacts count folded into E:",
            b["C_same_contacts_timing"]["would_be_count_if_not_excluded"],
        )
        print(
            "Bucket E total (same-contacts + more-contacts):",
            b["E_other_unexplained"]["total_count"],
        )
        print("Reconciliation:", r["reconciliation"])


if __name__ == "__main__":
    main()
