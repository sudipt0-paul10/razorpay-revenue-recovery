"""Day 10 - monetary invoice-value recovery, read from the sealed holdout artifacts.

POST-HOC DESCRIPTIVE ANALYSIS OF ALREADY-SEALED HOLDOUT ARTIFACTS; NOT A
PRE-REGISTERED PRIMARY METRIC AND NOT A NEW EVALUATION.

This script is strictly read-only with respect to `results/holdout/`. It opens
files for reading only, writes nothing to disk anywhere, and never imports
`rrx.sim`, `rrx.harness` or `rrx.eval` - it cannot re-simulate, re-run or
re-generate any artifact even accidentally. Every number it prints is an
aggregation of fields already present in the sealed, checksummed
`episode_results.jsonl` files produced by the single holdout run
`4d45db461943` (`EVAL.md §3.5`, `RESULTS.md §2`).

It refuses to report anything unless the seal verifies first: the SHA-256 of
every one of the 21 artifacts listed in `SHA256SUMS` must match, exactly as
`sha256sum -c` would check it. A single mismatch aborts with a non-zero exit
status before any aggregation is attempted.

Rescue-side value is deliberately absent. No cancellation-value or LTV
parameter is registered anywhere in `configs/`, so no monetary value is
assigned to a subscription rescue here - not a placeholder, not an assumed
figure. Invoice value only.

Usage:
    python scripts/day10_value.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_DIR = REPO_ROOT / "results" / "holdout" / "4d45db461943"
SHA256SUMS = HOLDOUT_DIR / "SHA256SUMS"
COSTS_YAML = REPO_ROOT / "configs" / "costs.yaml"

# Display label -> sealed artifact subdirectory. Order is the RESULTS.md §4 order.
ARMS = [
    ("A0", "a0"),
    ("A1", "a1"),
    ("A2-strengthened", "a2_strengthened"),
    ("A3-D", "a3_d"),
    ("A4", "a4"),
]

AMOUNT_FIELD = "invoice_amount_inr"
RECOVERED_FIELD = "invoice_recovered"
CONTACTS_FIELD = "contacts_sent"
INDEX_FIELD = "episode_index"


def inr(value: int | float, decimals: int = 0) -> str:
    """Format an amount with Indian digit grouping, e.g. 6466221 -> '64,66,221'."""
    negative = value < 0
    if decimals:
        whole_text, _, frac = f"{abs(value):.{decimals}f}".partition(".")
    else:
        whole_text, frac = str(int(round(abs(value)))), ""
    if len(whole_text) > 3:
        head, tail = whole_text[:-3], whole_text[-3:]
        chunks = []
        while len(head) > 2:
            chunks.insert(0, head[-2:])
            head = head[:-2]
        if head:
            chunks.insert(0, head)
        whole_text = ",".join(chunks) + "," + tail
    out = whole_text + ("." + frac if frac else "")
    return ("-" if negative else "") + "Rs" + out


def verify_seal() -> tuple[int, int, list[str]]:
    """Recompute SHA-256 for every artifact listed in SHA256SUMS. Read-only."""
    ok = 0
    total = 0
    failures: list[str] = []
    for line in SHA256SUMS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # GNU sha256sum writes "<hash>  <path>" in text mode and
        # "<hash> *<path>" in binary mode. This file uses the binary form;
        # accept either rather than assuming one.
        expected, _, relative = line.partition(" ")
        relative = relative.strip().lstrip("*").strip()
        total += 1
        target = HOLDOUT_DIR / relative
        if not target.is_file():
            failures.append(f"{relative}: MISSING")
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest == expected.strip():
            ok += 1
        else:
            failures.append(f"{relative}: FAILED")
    return ok, total, failures


def load_arm(subdir: str) -> list[dict]:
    """Read one arm's sealed episode_results.jsonl. Read-only."""
    path = HOLDOUT_DIR / subdir / "episode_results.jsonl"
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sealed_metric(subdir: str, key: str) -> float:
    """Read a published metric straight out of the sealed metrics.json."""
    path = HOLDOUT_DIR / subdir / "metrics.json"
    return json.loads(path.read_text(encoding="utf-8"))[key]


def registered_contact_cost() -> tuple[float, float, float]:
    """Effective contact cost as registered in configs/costs.yaml.

    Returns (whatsapp_cash_price, annoyance_penalty, effective_total). The
    effective figure is the one `RESULTS.md §14.1` and
    `docs/analysis/DAY9-NET-VALUE.md §3` already register: the WhatsApp
    utility price plus the synthetic per-contact annoyance penalty. The two
    components are returned separately because only the first is a cited
    cash price; the second is a labelled ASSUMPTION in costs.yaml.
    """
    costs = yaml.safe_load(COSTS_YAML.read_text(encoding="utf-8"))
    cash = float(costs["messaging"]["whatsapp"]["cost_inr"])
    annoyance = float(costs["annoyance"]["per_contact_inr"])
    return cash, annoyance, cash + annoyance


def cross_check(per_arm: dict[str, list[dict]]) -> list[str]:
    """Integrity checks over the loaded rows. Returns a list of failure strings."""
    problems: list[str] = []
    reference_label, reference_subdir = ARMS[0][0], ARMS[0][1]
    reference = [row[AMOUNT_FIELD] for row in per_arm[reference_subdir]]
    reference_indices = [row[INDEX_FIELD] for row in per_arm[reference_subdir]]

    for label, subdir in ARMS:
        rows = per_arm[subdir]
        if len(rows) != 2000:
            problems.append(f"{label}: expected N=2000, found {len(rows)}")
        indices = [row[INDEX_FIELD] for row in rows]
        if len(set(indices)) != len(indices):
            problems.append(f"{label}: duplicate {INDEX_FIELD} values present")
        if indices != reference_indices:
            problems.append(f"{label}: episode index vector differs from {reference_label}")
        for field in (AMOUNT_FIELD, RECOVERED_FIELD, CONTACTS_FIELD):
            missing = sum(1 for row in rows if row.get(field) is None)
            if missing:
                problems.append(f"{label}: {missing} rows missing {field}")
        amounts = [row[AMOUNT_FIELD] for row in rows]
        if amounts != reference:
            problems.append(f"{label}: {AMOUNT_FIELD} vector differs from {reference_label}")
    return problems


def main() -> int:
    ok, total, failures = verify_seal()
    print("=" * 78)
    print("DAY 10 - MONETARY INVOICE-VALUE RECOVERY (post-hoc, descriptive)")
    print("Sealed holdout run: results/holdout/4d45db461943/")
    print("=" * 78)
    print(f"\n[1] Seal verification: {ok}/{total} artifacts OK")
    if failures:
        for failure in failures:
            print(f"    {failure}")
        print("\nSEAL VERIFICATION FAILED - aborting without reading any episode data.")
        return 1

    per_arm = {subdir: load_arm(subdir) for _, subdir in ARMS}

    problems = cross_check(per_arm)
    print(f"\n[2] Cross-checks: {'PASS' if not problems else 'FAIL'}")
    if problems:
        for problem in problems:
            print(f"    {problem}")
        return 1
    at_risk = sum(row[AMOUNT_FIELD] for row in per_arm["a0"])
    print("    N=2000 per arm, 5 arms, no duplicate indices, no missing fields")
    print(f"    {AMOUNT_FIELD} vector identical across all 5 arms (CRN pairing intact)")

    summary = {}
    for label, subdir in ARMS:
        rows = per_arm[subdir]
        recovered = sum(row[AMOUNT_FIELD] for row in rows if row[RECOVERED_FIELD])
        contacts = sum(row[CONTACTS_FIELD] for row in rows)
        count_rate = sum(1 for row in rows if row[RECOVERED_FIELD]) / len(rows)
        summary[label] = {
            "recovered": recovered,
            "contacts": contacts,
            "value_rate": recovered / at_risk,
            "count_rate": count_rate,
            "published_rate": sealed_metric(subdir, "invoice_recovery_rate"),
            "published_contacts": sealed_metric(subdir, "total_contacts"),
        }

    baseline = summary["A0"]["recovered"]
    print(f"\n[3] Total invoice value at risk (all arms): {inr(at_risk)}\n")
    header = f"{'Arm':<18}{'Recovered':>14}{'Value rate':>12}{'vs A0':>14}{'Contacts':>10}"
    print(header)
    print("-" * len(header))
    for label, _ in ARMS:
        row = summary[label]
        print(
            f"{label:<18}{inr(row['recovered']):>14}{row['value_rate']:>12.4f}"
            f"{inr(row['recovered'] - baseline):>14}{row['contacts']:>10,}"
        )

    print("\n[4] Value-weighted rate vs published episode-count rate (RESULTS.md §4)")
    print(f"{'Arm':<18}{'Value rate':>12}{'Count rate':>12}{'Delta':>10}")
    for label, _ in ARMS:
        row = summary[label]
        assert abs(row["count_rate"] - row["published_rate"]) < 1e-12, (
            f"{label}: recomputed count rate does not match sealed metrics.json"
        )
        assert row["contacts"] == row["published_contacts"], (
            f"{label}: recomputed contact total does not match sealed metrics.json"
        )
        delta = row["value_rate"] - row["count_rate"]
        print(f"{label:<18}{row['value_rate']:>12.4f}{row['count_rate']:>12.4f}{delta:>+10.4f}")

    cash, annoyance, effective = registered_contact_cost()
    print(f"\n[5] Registered contact cost (configs/costs.yaml): "
          f"Rs{cash:.3f} cash + Rs{annoyance:.2f} annoyance = Rs{effective:.3f}/contact")
    for comparator in ("A1", "A2-strengthened"):
        a3d = summary["A3-D"]
        other = summary[comparator]
        value_gap = a3d["recovered"] - other["recovered"]
        contact_gap = other["contacts"] - a3d["contacts"]
        print(f"\n    A3-D vs {comparator}")
        print(f"      recovered-value difference : {inr(value_gap)}")
        print(f"      contacts saved             : {contact_gap:,}")
        print(f"      cash contact saving        : {inr(contact_gap * cash, 2)}")
        print(f"      effective contact saving   : {inr(contact_gap * effective, 2)}")
        if value_gap < 0:
            ratio = abs(value_gap) / (contact_gap * effective)
            print(f"      deficit / effective saving : {ratio:,.0f}x")

    # Day 9 Stage 1 could not measure the arm-conditional value of a marginal
    # recovery (docs/analysis/DAY9-NET-VALUE.md §7 limitation 1) and bracketed
    # it with two registered reference points instead. Those brackets are
    # quoted here so the measured figure can be checked against them.
    costs = yaml.safe_load(COSTS_YAML.read_text(encoding="utf-8"))
    fee_rate = float(costs["gateway"]["successful_capture_fee_rate"])
    day9_brackets = {"A1": (92.58, 152.64), "A2-strengthened": (134.50, 221.75)}
    print("\n[6] Measured marginal-recovery value vs the DAY9-NET-VALUE §5 bracket")
    print(f"    (net of the registered {fee_rate:.2%} successful-capture fee)")
    for comparator, (low, high) in day9_brackets.items():
        a3d = summary["A3-D"]
        other = summary[comparator]
        gross_gap = other["recovered"] - a3d["recovered"]
        net_gap = gross_gap * (1.0 - fee_rate)
        recovery_gap = round((other["count_rate"] - a3d["count_rate"]) * 2000)
        contact_gap = other["contacts"] - a3d["contacts"]
        print(f"\n    A3-D vs {comparator}")
        print(f"      marginal recoveries forfeited : {recovery_gap}")
        print(f"      measured net value each       : {inr(net_gap / recovery_gap, 2)}")
        print(f"      measured break-even contact   : {inr(net_gap / contact_gap, 2)}")
        print(f"      DAY9 bracketed break-even     : Rs{low:,.2f} - Rs{high:,.2f}")
        verdict = "ABOVE" if net_gap / contact_gap > high else "inside"
        print(f"      measured value is {verdict} the DAY9 bracket")
        print(f"      multiple of registered cost   : "
              f"{net_gap / contact_gap / effective:,.0f}x")

    print("\nNo monetary value is assigned to subscription rescue: no cancellation-value")
    print("parameter is registered in configs/, and none is invented here.")
    print("Figures are gross recovered invoice value, before the registered 2.36%")
    print("successful-capture processing fee (configs/costs.yaml gateway section).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
