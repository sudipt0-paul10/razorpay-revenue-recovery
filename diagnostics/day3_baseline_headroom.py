"""Day 3 baseline resolution + headroom check (ANALYSIS ONLY).

NON-CANONICAL DIAGNOSTIC OUTPUT. Nothing printed by this script is an
evaluation result: not logged to results/, not part of the frozen A0-A4
arm registry, not a change to sim-v1. engine.py's SOURCE FILE is never
modified - scratch policies are registered into engine._POLICIES at
runtime only (the same technique tests/test_stage5_falsification.py
uses), and reverted before this script exits.

Reuses run_a4_episode from tests/test_stage5_falsification.py by direct
import (read-only - the test file itself is never modified) rather than
re-deriving the oracle's decision logic, to avoid divergence risk.

Uses the SAME dev split, indices (range(1000, 3000), N=2000), and
MASTER_SEED (20260825) as Stage 5 Test 1 / the prior Day 3 diagnostic.

Run with:  python diagnostics/day3_baseline_headroom.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from rrx.sim import engine
from rrx.sim.engine import EpisodeResult, run_episode
from rrx.sim.latent import MASTER_SEED, load_configs
from rrx.sim.run_stage3 import paired_bootstrap_ci

SPLIT = "dev"
N = 2000
INDICES = range(1000, 1000 + N)

EPISODE_CFG, POPULATION_CFG = load_configs()

# ---------------------------------------------------------------------------
# Import tests/test_stage5_falsification.py directly (read-only) for
# run_a4_episode / A4_MAX_CONTACTS - not modified, just reused, to keep the
# oracle definition single-sourced.
# ---------------------------------------------------------------------------
_TEST_FILE = Path(__file__).resolve().parent.parent / "tests" / "test_stage5_falsification.py"
_spec = importlib.util.spec_from_file_location("_stage5_falsification_ro", _TEST_FILE)
_stage5 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _stage5
_spec.loader.exec_module(_stage5)

run_a4_episode = _stage5.run_a4_episode
A4_MAX_CONTACTS = _stage5.A4_MAX_CONTACTS
a1_action_for_day = _stage5.a1_action_for_day


# ===========================================================================
# Phase 2 - baseline candidate policies
# ===========================================================================
# A2-corrected-v1: identical to engine.a2_action_for_day except the
# card-broken bucket's second (invoice-relevant) card-change contact moves
# from T+5 to T+3 - the last invoice-eligible retry day per EVAL.md
# §1.1/§1.3 (auto-retries T+1..T+3; halt_boundary_day=3 in episode.yaml).
# Scope: ONLY the card-broken bucket's T+5, as explicitly specified. Does
# NOT touch ambiguous_decline's T+7 second contact or transaction_limit_
# exceeded's T+5 fallback (both flagged as separate, out-of-scope
# observations in the report - not corrected here).

def a2_corrected_v1_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3) else None
    return engine.a2_action_for_day(opening_condition_key, day, subscription_state)


# A2-strengthened: A2-corrected-v1 PLUS a third contact at T+3's boundary
# restored at T+5 for the card-broken bucket only - post-halt, this cannot
# help invoice recovery (structurally impossible past halt_boundary_day),
# but CAN still trigger subscription rescue (episode.yaml#/payment_method_
# change_effect/while_halted names subscription_rescued as an outcome, and
# engine.py's post-halt rescue block fires for exactly this bucket, since
# card_chargeable_at_opening=False for all three card-broken keys). Uses
# the full 3-contact budget (episode.yaml#/agent_budget/max_contacts_per_
# episode = 3), matching A4's budget.

def a2_strengthened_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3, 5) else None
    return engine.a2_action_for_day(opening_condition_key, day, subscription_state)


SCRATCH_ARMS = {
    "A2_CORRECTED_V1": a2_corrected_v1_action_for_day,
    "A2_STRENGTHENED": a2_strengthened_action_for_day,
}


def register_scratch_arms() -> None:
    engine._POLICIES["A1"] = a1_action_for_day
    for name, fn in SCRATCH_ARMS.items():
        engine._POLICIES[name] = fn


def unregister_scratch_arms() -> None:
    del engine._POLICIES["A1"]
    for name in SCRATCH_ARMS:
        del engine._POLICIES[name]


# ===========================================================================
# Helpers
# ===========================================================================

def run_arm(arm: str) -> list[EpisodeResult]:
    return [run_episode(SPLIT, i, arm, EPISODE_CFG, POPULATION_CFG) for i in INDICES]


def run_a4() -> list[EpisodeResult]:
    frozen_budget = EPISODE_CFG["agent_budget"]["max_contacts_per_episode"]
    assert A4_MAX_CONTACTS == frozen_budget, (
        f"A4_MAX_CONTACTS ({A4_MAX_CONTACTS}) != frozen agent budget ({frozen_budget})"
    )
    return [run_a4_episode(SPLIT, i, EPISODE_CFG, POPULATION_CFG) for i in INDICES]


def rate(results, attr: str) -> float:
    return sum(getattr(r, attr) for r in results) / len(results) if results else float("nan")


def print_header(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


# ===========================================================================
# Phase 1 - static verification of the three A2 discrepancies
# ===========================================================================

def phase1():
    print_header("PHASE 1 - Verify the three A2 discrepancies (static + one dev-split check)")

    print("EVAL.md heading scan (confirms whether a written §4 policy section exists):")
    import subprocess
    out = subprocess.run(
        ["grep", "-n", "^#", str(Path(__file__).resolve().parent.parent / "EVAL.md")],
        capture_output=True, text=True,
    ).stdout
    print(out)
    print("-> No '## 4.' heading exists (headings run 0,1,2,3,5,10). EVAL.md never specified")
    print("   a written A2 contact schedule. a2_action_for_day's own docstring (engine.py)")
    print("   already documents this and states the schedule was dictated in conversation,")
    print("   not derived from EVAL.md/SIM.md.")

    print()
    print("1. insufficient_funds:")
    print("   a2_action_for_day: topup_reminder at day==1 ONLY, never card_change.")
    print("   EVAL.md §5.2 gate: 'Card-change prompts for insufficient_funds: 0'.")
    print("   engine.py's own docstring: a T+5 card-change fallback was originally dictated")
    print("   and EXPLICITLY DROPPED to satisfy this real, written gate.")
    print("   -> NOT a discrepancy: implementation correctly complies with the gate.")
    for day in range(0, 8):
        a = engine.a2_action_for_day("insufficient_funds", day, "pending")
        if a:
            print(f"     day={day}: {a}")

    print()
    print("2. transaction_limit_exceeded:")
    print("   a2_action_for_day: topup_reminder@T+1, PLUS card_change@T+5 if still pending/halted.")
    for day in range(0, 8):
        a = engine.a2_action_for_day("transaction_limit_exceeded", day, "pending")
        if a:
            print(f"     day={day}: {a}")
    print("   Latent mechanics (latent.py _MECHANISM_ISOLATED_KEYS branch):")
    print("     card_chargeable=True at opening (same as insufficient_funds) ->")
    print("     card_change is EQUALLY a structural no-op here (_apply_card_naming_effect")
    print("     no-ops whenever card_chargeable is already True).")
    print("     blocked_until=BLOCKED_INDEFINITELY -> invoice can NEVER recover in-window,")
    print("     regardless of any action.")
    print("   Gate text names ONLY 'insufficient_funds' - transaction_limit_exceeded is not")
    print("   named in §5.2 or anywhere else, so sending card_change to it is not a literal")
    print("   gate violation. But it IS the same underlying no-op remedy that the gate exists")
    print("   to prevent, applied inconsistently across two mechanically-identical conditions.")
    print("   -> GENUINE INCONSISTENCY, but NOT a P0 safety violation (gate's literal text")
    print("      is satisfied) and NOT a recovery-metric error (structurally 0% either way).")
    print("      Classification: policy-design inconsistency, not an implementation bug and")
    print("      not a spec violation.")

    print()
    print("3. bank_technical_error:")
    print("   a2_action_for_day: card_change@T+5, UNCONDITIONAL (no 'if still pending/halted'")
    print("   guard - unlike transaction_limit_exceeded's T+5, which does carry that guard).")
    for day in range(0, 8):
        a = engine.a2_action_for_day("bank_technical_error", day, "pending")
        if a:
            print(f"     day={day}: {a}")
    print("   Latent mechanics: blocked_until ~ Uniform[0,2] (episode.yaml), card_chargeable=True,")
    print("   funds_available_from=0, mandate_alive=True -> _retry_succeeds is guaranteed True")
    print("   by day=2 at the latest (retry_days=[1,2,3], all <= halt_boundary_day=3).")
    print("   -> By construction, recovery is ALWAYS already resolved before day 5.")
    print("   Empirical check on this dev cohort (N=2000, seeds 1000-2999):")

    a0_all = [run_episode(SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    a2_all = [run_episode(SPLIT, i, "A2", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    bte_pairs = [
        (a0, a2) for a0, a2 in zip(a0_all, a2_all)
        if a0.opening_condition_key == "bank_technical_error"
    ]
    n_bte = len(bte_pairs)
    always_recovered_by_a0 = sum(1 for a0, _ in bte_pairs if a0.invoice_recovered)
    a2_contacts_for_bte = sum(a2.contacts_sent for _, a2 in bte_pairs)
    print(f"     N(bank_technical_error)={n_bte}")
    print(f"     A0 (no contact at all) already recovers: {always_recovered_by_a0}/{n_bte} "
          f"({always_recovered_by_a0 / n_bte:.4f}) - i.e. recovery needs NO agent action.")
    print(f"     A2 total contacts sent to this bucket: {a2_contacts_for_bte} "
          f"(== {a2_contacts_for_bte / n_bte:.2f} per episode)")
    print("   -> IMPLEMENTATION ISSUE (schedule oversight, not a gate/spec violation): every")
    print("      bank_technical_error episode receives a guaranteed-useless T+5 card_change")
    print("      contact, spending 1 of 3 budget slots and incurring fatigue/annoyance-hazard")
    print("      cost for zero possible benefit, because recovery is already certain by day 2")
    print("      and the contact carries no 'already recovered' guard.")


def main():
    print("Day 3 baseline resolution + headroom check - NON-CANONICAL DIAGNOSTIC OUTPUT")
    print(f"MASTER_SEED={MASTER_SEED}, split={SPLIT!r}, N={N}, "
          f"indices={INDICES.start}-{INDICES.stop - 1}")

    phase1()

    print_header("PHASE 3 - Baseline / headroom pass (dev, N=%d)" % N)
    register_scratch_arms()
    try:
        arms = {
            "A0": run_arm("A0"),
            "A1": run_arm("A1"),
            "A2_ORIGINAL": run_arm("A2"),
            "A2_CORRECTED_V1": run_arm("A2_CORRECTED_V1"),
            "A2_STRENGTHENED": run_arm("A2_STRENGTHENED"),
        }
    finally:
        unregister_scratch_arms()
    arms["A4"] = run_a4()

    order = ["A0", "A1", "A2_ORIGINAL", "A2_CORRECTED_V1", "A2_STRENGTHENED", "A4"]
    header = f"{'arm':<18}{'inv_rate':>10}{'res_rate':>10}{'contacts':>10}{'ct/ep':>8}"
    print(header)
    print("-" * len(header))
    for name in order:
        rs = arms[name]
        inv = rate(rs, "invoice_recovered")
        res = rate(rs, "subscription_rescued")
        contacts = sum(r.contacts_sent for r in rs)
        print(f"{name:<18}{inv:>10.4f}{res:>10.4f}{contacts:>10}{contacts / N:>8.3f}")

    # Subgroup: card-broken (combined) and insufficient_funds.
    card_broken = frozenset({"card_expired", "debit_instrument_blocked", "card_not_enabled_group"})

    def subgroup_rate(results, keys, attr):
        rs = [r for r in results if r.opening_condition_key in keys]
        return rate(rs, attr), len(rs)

    print()
    print("Card-broken bucket (combined, N shown per arm) - invoice / rescue:")
    for name in order:
        r_inv, n = subgroup_rate(arms[name], card_broken, "invoice_recovered")
        r_res, _ = subgroup_rate(arms[name], card_broken, "subscription_rescued")
        rs = [r for r in arms[name] if r.opening_condition_key in card_broken]
        contacts = sum(r.contacts_sent for r in rs)
        print(f"  {name:<18} N={n:<6} inv={r_inv:.4f}  res={r_res:.4f}  contacts={contacts}")

    print()
    print("insufficient_funds - invoice / rescue (sanity: A2 variants shouldn't touch this):")
    for name in order:
        r_inv, n = subgroup_rate(arms[name], {"insufficient_funds"}, "invoice_recovered")
        r_res, _ = subgroup_rate(arms[name], {"insufficient_funds"}, "subscription_rescued")
        print(f"  {name:<18} N={n:<6} inv={r_inv:.4f}  res={r_res:.4f}")

    # Cancelled-at-open canary across all arms.
    print()
    print("Cancelled-at-open canary (all arms):")
    for name in order:
        cancelled = [
            r for r in arms[name]
            if r.opening_condition_key == "subscription_cancelled_by_customer"
        ]
        bad = [r for r in cancelled if r.invoice_recovered or r.subscription_rescued]
        print(f"  {name:<18} N={len(cancelled)}  anomalous={len(bad)}")

    # ------------------------------------------------------------------
    # Phase 4 - headroom analysis
    # ------------------------------------------------------------------
    print_header("PHASE 4 - Headroom analysis (A4 vs each bounded arm)")

    bounded = ["A0", "A1", "A2_ORIGINAL", "A2_CORRECTED_V1", "A2_STRENGTHENED"]
    a4_inv = [float(r.invoice_recovered) for r in arms["A4"]]
    a4_res = [float(r.subscription_rescued) for r in arms["A4"]]

    print("Invoice recovery: A4 - bounded_arm")
    best_inv_name, best_inv_val = None, -1.0
    for name in bounded:
        b_inv = [float(r.invoice_recovered) for r in arms[name]]
        d, lo, hi = paired_bootstrap_ci(b_inv, a4_inv, n_resamples=5000)
        arm_rate = sum(b_inv) / N
        print(f"  A4({rate(arms['A4'],'invoice_recovered'):.4f}) - {name}({arm_rate:.4f}): "
              f"diff={d:+.4f} CI=[{lo:+.4f},{hi:+.4f}]")
        if arm_rate > best_inv_val:
            best_inv_val, best_inv_name = arm_rate, name

    print(f"  Best bounded arm on invoice recovery: {best_inv_name} ({best_inv_val:.4f})")
    d, lo, hi = paired_bootstrap_ci(
        [float(r.invoice_recovered) for r in arms[best_inv_name]], a4_inv, n_resamples=5000
    )
    rel_gap_inv = d / best_inv_val if best_inv_val > 0 else float("nan")
    print(f"  A4 - best_bounded (invoice) = {d:+.4f}  CI=[{lo:+.4f},{hi:+.4f}]  "
          f"relative gap = {rel_gap_inv:+.2%} of best-bounded rate")

    print()
    print("Subscription rescue: A4 - bounded_arm")
    best_res_name, best_res_val = None, -1.0
    for name in bounded:
        b_res = [float(r.subscription_rescued) for r in arms[name]]
        d, lo, hi = paired_bootstrap_ci(b_res, a4_res, n_resamples=5000)
        arm_rate = sum(b_res) / N
        print(f"  A4({rate(arms['A4'],'subscription_rescued'):.4f}) - {name}({arm_rate:.4f}): "
              f"diff={d:+.4f} CI=[{lo:+.4f},{hi:+.4f}]")
        if arm_rate > best_res_val:
            best_res_val, best_res_name = arm_rate, name

    print(f"  Best bounded arm on subscription rescue: {best_res_name} ({best_res_val:.4f})")
    d2, lo2, hi2 = paired_bootstrap_ci(
        [float(r.subscription_rescued) for r in arms[best_res_name]], a4_res, n_resamples=5000
    )
    rel_gap_res = d2 / best_res_val if best_res_val > 0 else float("nan")
    print(f"  A4 - best_bounded (rescue) = {d2:+.4f}  CI=[{lo2:+.4f},{hi2:+.4f}]  "
          f"relative gap = {rel_gap_res:+.2%} of best-bounded rate")

    print()
    print("=" * 90)
    print("END OF NON-CANONICAL DIAGNOSTIC OUTPUT")
    print("=" * 90)


if __name__ == "__main__":
    main()
