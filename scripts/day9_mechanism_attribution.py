"""Day 9, Stage 3 diagnostic: mechanism attribution.

NOT part of the evaluation harness. Does not import rrx.agent or rrx.sim.
Read-only with respect to every file under results/holdout/. Writes only
to results/day9_decomposition/.

Attributes A3-D's holdout ledger records to the three EVAL.md §3.4
pre-registered advantage sources (retry-window timing, remedy matching,
within-episode adaptive contact) using the `rationale` field (the exact
decision-table rule id, docs/A3-DESIGN.md §10A.4) and the frozen §10A.5
"basis" text for each rule -- both fixed before this script was written,
not inferred from holdout outcomes.

Reuses the identical Stage 2 pairing/bucket logic (episode_index join,
Bucket A = fewer contacts + comparator recovered + A3-D did not) to
recover the full episode-index membership of Stage 2's Bucket A, so this
script's counts can be cross-checked against the committed Stage 2
counts (47 vs A1, 59 vs A2-strengthened) as an integrity check -- this is
not a redefinition or a rerun of Stage 2, only a re-derivation of the
member list from the same, already-committed rule.

Usage: python scripts/day9_mechanism_attribution.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_ROOT = REPO_ROOT / "results" / "holdout" / "4d45db461943"
OUT_DIR = REPO_ROOT / "results" / "day9_decomposition"

RETRY_DAYS = [1, 2, 3]
HALT_BOUNDARY_DAY = 3

# docs/A3-DESIGN.md §10A.4 (decision table) x §10A.5 (per-rule basis),
# transcribed verbatim -- fixed before this script ran, not fitted to any
# result. Mechanism tags use the EVAL.md §3.4 names exactly:
#   RWT = retry-window timing
#   RM  = remedy matching
#   AC  = within-episode adaptive contact (the withhold_applies predicate)
#   NONE = none of the three (defensive/forced/default, unrelated to any
#          advantage source)
RULE_MECHANISM = {
    "R-01": {"tags": [], "note": "defensive, structurally unreachable on a real tick (§10A.5)"},
    "R-02": {"tags": [], "note": "FORCED by gate R4; not an advantage-source mechanism"},
    "R-03": {"tags": ["RWT"], "note": "FORCED mechanically -- no retry window ever exists for this code"},
    "R-04": {"tags": ["RWT"], "note": "FORCED -- WAIT because auto-retry window still open"},
    "R-05": {"tags": ["RWT"], "note": "retries exhausted, window closed"},
    "R-06": {"tags": ["RWT"], "note": "halted -- window closed"},
    "R-07": {"tags": ["RWT"], "note": "day>=3 -- window mechanically dead (funds-acceleration proof)"},
    "R-08": {"tags": ["RWT", "RM"], "note": "topup remedy sent on the earliest in-window day"},
    "R-09": {"tags": ["RWT", "RM", "AC"], "note": "topup remedy, last in-window day, gated by withhold_applies"},
    "R-10": {"tags": ["RWT", "AC"], "note": "WAIT; reason_code itself distinguishes RWT (retry_window_open) from AC (no_engagement_restraint)"},
    "R-11": {"tags": ["RM"], "note": "post-halt remedy match, explicitly EXEMPT from the withhold test (§10A.5 [D-7])"},
    "R-12": {"tags": ["RM"], "note": "day-0 remedy match, fixed schedule (adopted from A2), not withhold-gated"},
    "R-13": {"tags": ["RM", "AC"], "note": "day-3 remedy match, gated by withhold_applies -- the Stage 2 divergence rule"},
    "R-14": {"tags": ["RM"], "note": "day-0 fail-safe remedy, not withhold-gated"},
    "R-15": {"tags": ["RM", "AC"], "note": "day-2 hedge remedy, gated by withhold_applies"},
    "R-16": {"tags": [], "note": "named default/fallthrough -- diagnostic only, not itself an advantage-source mechanism"},
}


def load_episode_results(arm_dir: Path) -> dict[int, dict]:
    out = {}
    with open(arm_dir / "episode_results.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            out[row["episode_index"]] = row
    return out


def load_a3d_ledger(ledger_path: Path) -> list[dict]:
    out = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def bucket_a_indices(a3d_results, comp_results) -> list[int]:
    """Reproduces Stage 2's Bucket A membership exactly (fewer contacts,
    comparator recovered, A3-D did not) -- same rule, not a new one."""
    out = []
    for idx in sorted(a3d_results):
        a3d_row = a3d_results[idx]
        comp_row = comp_results[idx]
        if comp_row["invoice_recovered"] and not a3d_row["invoice_recovered"]:
            if a3d_row["contacts_sent"] < comp_row["contacts_sent"]:
                out.append(idx)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    a3d_results = load_episode_results(HOLDOUT_ROOT / "a3_d")
    ledger = load_a3d_ledger(HOLDOUT_ROOT / "a3_d" / "ledger.jsonl")
    wakeups = [r for r in ledger if r["tick_type"] == "wakeup"]

    # ---- Overall rule-firing distribution (whole holdout) ----
    rule_counts = Counter(r["rationale"] for r in wakeups)

    # ---- Mechanism tag totals (a wakeup can count toward >1 tag) ----
    mechanism_totals = Counter()
    for rule, cnt in rule_counts.items():
        for tag in RULE_MECHANISM.get(rule, {}).get("tags", []):
            mechanism_totals[tag] += cnt

    # ---- Contact timing relative to the retry/halt boundary (day 3) ----
    contacts = [r for r in wakeups if r["executed_action"]["action_type"] == "CONTACT"]
    contact_tick_hist = Counter(r["tick"] for r in contacts)
    contacts_within_or_at_boundary = sum(v for k, v in contact_tick_hist.items() if k <= HALT_BOUNDARY_DAY)
    contacts_after_boundary = sum(v for k, v in contact_tick_hist.items() if k > HALT_BOUNDARY_DAY)

    # ---- Withhold-at-T+3: WAIT/STOP with reason_code=no_engagement_restraint at tick==3 ----
    withhold_at_t3 = [
        r for r in wakeups
        if r["tick"] == 3
        and r["executed_action"]["action_type"] in ("WAIT", "STOP")
        and r["reason_code"] == "no_engagement_restraint"
    ]
    withhold_at_t3_by_rule = Counter(r["rationale"] for r in withhold_at_t3)

    # withhold occurring inside the declared retry window (tick in 1..3) vs after (tick>3)
    withhold_all = [
        r for r in wakeups
        if r["executed_action"]["action_type"] in ("WAIT", "STOP")
        and r["reason_code"] == "no_engagement_restraint"
    ]
    withhold_in_window = sum(1 for r in withhold_all if 1 <= r["tick"] <= HALT_BOUNDARY_DAY)
    withhold_after_window = sum(1 for r in withhold_all if r["tick"] > HALT_BOUNDARY_DAY)
    withhold_at_day0 = sum(1 for r in withhold_all if r["tick"] == 0)

    # ---- Remedy-match verification (structural cross-check, not new logic) ----
    import sys
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from rrx.agent.reason_codes import ADMISSIBLE_DECLINE_CODES  # noqa: E402

    mismatches = []
    for r in contacts:
        idx = int(r["episode_id"].split("-")[1])
        decline_code = a3d_results[idx]["opening_condition_key"]
        reason_code = r["reason_code"]
        admissible = ADMISSIBLE_DECLINE_CODES.get(reason_code, frozenset())
        if decline_code not in admissible:
            mismatches.append({"episode_id": r["episode_id"], "tick": r["tick"], "reason_code": reason_code, "decline_code": decline_code})

    # ---- Mechanism-3: adaptive-contact firing by day (AC-tagged rules only) ----
    ac_rules = {rid for rid, m in RULE_MECHANISM.items() if "AC" in m["tags"]}
    ac_firings_by_tick = Counter(r["tick"] for r in wakeups if r["rationale"] in ac_rules)
    # AC rules fire in two branches: the gated CONTACT branch (predicate false -> contact
    # sent) and, when the predicate is true, control falls through to a later rule
    # (typically R-16) rather than "R-13 firing false" -- so we also report, for each
    # AC-gated day, how often the *fallthrough* rule (R-16 at that tick) carries
    # reason_code=no_engagement_restraint, which is the observable trace of the predicate
    # having suppressed the contact.
    fallthrough_no_engagement_by_tick_rule = Counter(
        (r["tick"], r["rationale"])
        for r in wakeups
        if r["reason_code"] == "no_engagement_restraint" and r["rationale"] == "R-16"
    )

    result = {
        "rule_firing_distribution_all_wakeups": dict(rule_counts),
        "mechanism_totals_all_wakeups": dict(mechanism_totals),
        "n_wakeups_total": len(wakeups),
        "contact_tick_histogram": {str(k): v for k, v in sorted(contact_tick_hist.items())},
        "contacts_within_or_at_retry_boundary_day3": contacts_within_or_at_boundary,
        "contacts_after_retry_boundary_day3": contacts_after_boundary,
        "n_contacts_total": len(contacts),
        "withhold_at_t3_count": len(withhold_at_t3),
        "withhold_at_t3_by_rule": dict(withhold_at_t3_by_rule),
        "withhold_all_count": len(withhold_all),
        "withhold_in_declared_retry_window_ticks_1_to_3": withhold_in_window,
        "withhold_after_retry_window_tick_gt_3": withhold_after_window,
        "withhold_at_day0": withhold_at_day0,
        "remedy_mismatch_count": len(mismatches),
        "remedy_mismatch_examples": mismatches[:5],
        "n_contacts_checked_for_remedy_match": len(contacts),
        "ac_rule_firings_by_tick": {str(k): v for k, v in sorted(ac_firings_by_tick.items())},
        "fallthrough_no_engagement_R16_by_tick": {
            str(k): v for k, v in sorted(
                Counter(tick for tick, rule in fallthrough_no_engagement_by_tick_rule).items()
            )
        },
    }

    # ---- Stage 2 Bucket A cross-check + rule-id stratification ----
    stage2_cross = {}
    for comp_key in ["a1", "a2_strengthened"]:
        comp_results = load_episode_results(HOLDOUT_ROOT / comp_key)
        bucket_a = bucket_a_indices(a3d_results, comp_results)
        bucket_a_set = set(bucket_a)

        # last wakeup record per Bucket A episode
        last_wakeup_by_ep: dict[int, dict] = {}
        for r in wakeups:
            idx = int(r["episode_id"].split("-")[1])
            if idx in bucket_a_set:
                if idx not in last_wakeup_by_ep or r["tick"] > last_wakeup_by_ep[idx]["tick"]:
                    last_wakeup_by_ep[idx] = r

        rule_at_last_wakeup = Counter(rec["rationale"] for rec in last_wakeup_by_ep.values())

        stage2_cross[comp_key] = {
            "bucket_a_count_rederived": len(bucket_a),
            "rule_at_last_wakeup_distribution": dict(rule_at_last_wakeup),
        }

    result["stage2_bucket_a_mechanism_crosscheck"] = stage2_cross
    result["rule_mechanism_map"] = RULE_MECHANISM

    out_path = OUT_DIR / "mechanism_attribution.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {out_path}")

    print("\n=== Summary ===")
    print("rule_firing_distribution_all_wakeups:", rule_counts)
    print("mechanism_totals_all_wakeups:", mechanism_totals)
    print("contacts within/at day3:", contacts_within_or_at_boundary, "after day3:", contacts_after_boundary)
    print("withhold_at_t3_count:", len(withhold_at_t3), "by rule:", withhold_at_t3_by_rule)
    print("withhold_in_window(1-3):", withhold_in_window, "after_window(>3):", withhold_after_window, "at_day0:", withhold_at_day0)
    print("remedy_mismatch_count:", len(mismatches), "of", len(contacts), "contacts checked")
    print("Stage2 Bucket A rederivation + rule-at-last-wakeup:", json.dumps(stage2_cross, indent=2))


if __name__ == "__main__":
    main()
