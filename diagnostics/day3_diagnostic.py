"""Day 3 pre-agent diagnostic (ANALYSIS ONLY).

NON-CANONICAL DIAGNOSTIC OUTPUT. Nothing printed by this script is an
evaluation result: not logged to results/, not part of the frozen A0-A4
arm registry, not a change to sim-v1.

This script:
  - reuses rrx.sim.engine.run_episode / rrx.sim.engine._POLICIES exactly
    the way tests/test_stage5_falsification.py does (temporary dict-key
    registration of scratch policies, reverted at the end of the run) -
    engine.py's SOURCE FILE is never modified.
  - uses the SAME dev split, indices (range(1000, 3000), N=2000), and
    MASTER_SEED (20260825) as Stage 5 Test 1, for direct comparability.
  - writes nothing to results/, configs/, or any locked file.

Run with:  python diagnostics/day3_diagnostic.py
"""

from __future__ import annotations

from collections import defaultdict

from rrx.sim import engine
from rrx.sim.engine import EpisodeResult, run_episode
from rrx.sim.latent import MASTER_SEED, load_configs
from rrx.sim.run_stage3 import paired_bootstrap_ci

SPLIT = "dev"
N = 2000
INDICES = range(1000, 1000 + N)

EPISODE_CFG, POPULATION_CFG = load_configs()


# ===========================================================================
# Arm definitions
# ===========================================================================
# A1 (Stage 5's a1_action_for_day, reproduced here verbatim for
# reproducibility of this script - not imported, since it is test-module
# local): naive fixed-contact policy, card_change at T+0 and T+3, for every
# non-terminal episode, unconditional on opening_condition_key.

def a1_action_for_day(opening_condition_key: str, day: int, subscription_state: str) -> str | None:
    return "card_change" if day in (0, 3) else None


# A2 is engine.a2_action_for_day, used as-is (frozen, unmodified).

# ---------------------------------------------------------------------------
# Task 3 scratch arms - COUNTERFACTUAL, NOT part of A0-A4.
# ---------------------------------------------------------------------------

def scratch_a2_topup_at_t0(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """A2 timing-shifted: identical to engine.a2_action_for_day in every
    branch EXCEPT insufficient_funds, whose top-up moves from T+1 to T+0."""
    if opening_condition_key == "insufficient_funds":
        return "topup_reminder" if day == 0 else None
    return engine.a2_action_for_day(opening_condition_key, day, subscription_state)


def scratch_a1_card_change_t1_only(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """A1 timing-shifted: single card_change contact at T+1 (vs A1's
    T+0/T+3 pair), universal/unconditional like A1 itself."""
    return "card_change" if day == 1 else None


def scratch_a2_cardbroken_second_contact_t3(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """EXTRA diagnostic arm (not one of the 4 required ablation arms) -
    added after Task 2's subgroup table showed A2 actually WINS on
    insufficient_funds and the aggregate A1>A2 gap is concentrated in the
    card-broken conditions instead. Identical to engine.a2_action_for_day
    in every branch EXCEPT the card-broken keys, whose second card_change
    contact moves from T+5 (after halt_boundary_day=3 - structurally too
    late to help invoice recovery, since invoice recovery only checks
    retry_days=[1,2,3]) to T+3 (before/at the halt boundary, same as A1's
    second contact day). Isolates whether THIS specific schedule choice -
    not the insufficient_funds topup day - explains the aggregate gap."""
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3) else None
    return engine.a2_action_for_day(opening_condition_key, day, subscription_state)


SCRATCH_ARMS = {
    "SCRATCH_A2_ASIS": engine.a2_action_for_day,
    "SCRATCH_A2_T0": scratch_a2_topup_at_t0,
    "SCRATCH_A1_ASIS": a1_action_for_day,
    "SCRATCH_A1_T1": scratch_a1_card_change_t1_only,
    "SCRATCH_A2_CARDBROKEN_T3": scratch_a2_cardbroken_second_contact_t3,
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


def rate(results, attr: str) -> float:
    return sum(getattr(r, attr) for r in results) / len(results) if results else float("nan")


def terminal_state(r: EpisodeResult) -> str:
    """Derived, not stored directly on EpisodeResult (see module docstring
    of rrx.sim.engine: subscription_state only ever becomes 'active' via
    successful retry or post-halt card-rescue; 'cancelled' is terminal-at-
    open; otherwise the episode is 'halted' by day 30 (halt_boundary_day=3
    << window_days=30, and no further transition exists post-halt except
    the card-rescue path already captured by subscription_rescued)."""
    if r.opening_condition_key == "subscription_cancelled_by_customer":
        return "cancelled"
    if r.invoice_recovered or r.subscription_rescued:
        return "active"
    return "halted"


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ===========================================================================
# Task 2 - subgroup breakdown
# ===========================================================================

def task2(a1, a2):
    print_header("TASK 2 - Opening-condition subgroup breakdown (dev, N=%d, seeds %d-%d)"
                  % (N, INDICES.start, INDICES.stop - 1))

    by_cond = defaultdict(list)
    for i, (r1, r2) in enumerate(zip(a1, a2)):
        assert r1.opening_condition_key == r2.opening_condition_key  # CRN sanity
        by_cond[r1.opening_condition_key].append((r1, r2))

    header = (
        f"{'condition':<32}{'N':>6}{'A1_inv':>8}{'A2_inv':>8}{'d_inv':>8}"
        f"{'A1_res':>8}{'A2_res':>8}{'d_res':>8}{'A1_ct':>7}{'A2_ct':>7}"
    )
    print(header)
    print("-" * len(header))

    for cond in sorted(by_cond):
        pairs = by_cond[cond]
        n = len(pairs)
        r1s = [p[0] for p in pairs]
        r2s = [p[1] for p in pairs]
        a1_inv = rate(r1s, "invoice_recovered")
        a2_inv = rate(r2s, "invoice_recovered")
        a1_res = rate(r1s, "subscription_rescued")
        a2_res = rate(r2s, "subscription_rescued")
        a1_ct = sum(r.contacts_sent for r in r1s)
        a2_ct = sum(r.contacts_sent for r in r2s)
        print(
            f"{cond:<32}{n:>6}{a1_inv:>8.4f}{a2_inv:>8.4f}{a1_inv - a2_inv:>+8.4f}"
            f"{a1_res:>8.4f}{a2_res:>8.4f}{a1_res - a2_res:>+8.4f}{a1_ct:>7}{a2_ct:>7}"
        )

    print()
    a1_total_contacts = sum(r.contacts_sent for r in a1)
    a2_total_contacts = sum(r.contacts_sent for r in a2)
    print(f"Total contacts: A1={a1_total_contacts}  A2={a2_total_contacts}")

    # Recovery rate conditioned on contacts sent (per-arm).
    print()
    print("Recovery rate conditioned on contacts_sent:")
    for arm_name, results in (("A1", a1), ("A2", a2)):
        by_contacts = defaultdict(list)
        for r in results:
            by_contacts[r.contacts_sent].append(r)
        parts = []
        for c in sorted(by_contacts):
            rs = by_contacts[c]
            parts.append(f"contacts={c}: N={len(rs)} inv_rate={rate(rs, 'invoice_recovered'):.4f}")
        print(f"  {arm_name}: " + " | ".join(parts))

    # Cancelled-at-open canary.
    print()
    cancelled_a1 = [
        r for r in a1 if r.opening_condition_key == "subscription_cancelled_by_customer"
    ]
    cancelled_a2 = [
        r for r in a2 if r.opening_condition_key == "subscription_cancelled_by_customer"
    ]
    bad_a1 = [r for r in cancelled_a1 if r.invoice_recovered or r.subscription_rescued]
    bad_a2 = [r for r in cancelled_a2 if r.invoice_recovered or r.subscription_rescued]
    print(
        f"Cancelled-at-open canary: N(A1)={len(cancelled_a1)} N(A2)={len(cancelled_a2)} "
        f"anomalous_recoveries(A1)={len(bad_a1)} anomalous_recoveries(A2)={len(bad_a2)}"
    )
    if bad_a1 or bad_a2:
        print("  *** P0 CANARY TRIPPED: recovery recorded for a cancelled-at-open episode ***")
    else:
        print("  canary clean: no cancelled-at-open episode recorded any recovery.")

    return by_cond


# ===========================================================================
# Task 3 - unconfounding ablation
# ===========================================================================

def task3():
    print_header("TASK 3 - Unconfounding ablation (scratch arms, dev, N=%d)" % N)

    register_scratch_arms()
    try:
        results = {name: run_arm(name) for name in SCRATCH_ARMS}
    finally:
        unregister_scratch_arms()

    header = (
        f"{'arm':<20}{'inv_rate':>10}{'res_rate':>10}{'contacts':>10}"
        f"{'active':>8}{'halted':>8}{'cancelled':>10}"
    )
    print(header)
    print("-" * len(header))
    for name in ("SCRATCH_A2_ASIS", "SCRATCH_A2_T0", "SCRATCH_A1_ASIS", "SCRATCH_A1_T1"):
        rs = results[name]
        inv = rate(rs, "invoice_recovered")
        res = rate(rs, "subscription_rescued")
        contacts = sum(r.contacts_sent for r in rs)
        states = defaultdict(int)
        for r in rs:
            states[terminal_state(r)] += 1
        print(
            f"{name:<20}{inv:>10.4f}{res:>10.4f}{contacts:>10}"
            f"{states['active']:>8}{states['halted']:>8}{states['cancelled']:>10}"
        )

    # insufficient_funds-only comparison for the topup timing shift.
    print()
    print("insufficient_funds subgroup only (topup timing shift):")
    for name in ("SCRATCH_A2_ASIS", "SCRATCH_A2_T0"):
        rs = [r for r in results[name] if r.opening_condition_key == "insufficient_funds"]
        print(f"  {name}: N={len(rs)} inv_rate={rate(rs, 'invoice_recovered'):.4f} "
              f"res_rate={rate(rs, 'subscription_rescued'):.4f} "
              f"contacts={sum(r.contacts_sent for r in rs)}")

    asis_inv = [
        float(r.invoice_recovered) for r in results["SCRATCH_A2_ASIS"]
        if r.opening_condition_key == "insufficient_funds"
    ]
    t0_inv = [
        float(r.invoice_recovered) for r in results["SCRATCH_A2_T0"]
        if r.opening_condition_key == "insufficient_funds"
    ]
    d, lo, hi = paired_bootstrap_ci(asis_inv, t0_inv, n_resamples=5000)
    print(f"  SCRATCH_A2_T0 - SCRATCH_A2_ASIS (insufficient_funds only) "
          f"diff={d:+.4f} CI=[{lo:+.4f},{hi:+.4f}]")

    # Whole-cohort A1-style comparison for the card-change timing shift.
    print()
    print("Whole cohort (card-change timing shift, A1-style universal policy):")
    asis_inv_full = [float(r.invoice_recovered) for r in results["SCRATCH_A1_ASIS"]]
    t1_inv_full = [float(r.invoice_recovered) for r in results["SCRATCH_A1_T1"]]
    d2, lo2, hi2 = paired_bootstrap_ci(asis_inv_full, t1_inv_full, n_resamples=5000)
    print(f"  SCRATCH_A1_T1 - SCRATCH_A1_ASIS (whole cohort) "
          f"diff={d2:+.4f} CI=[{lo2:+.4f},{hi2:+.4f}]")

    # The critical unconfounded pairing: topup@T+0 vs card-change@T+1,
    # matched on insufficient_funds subgroup, same "single early contact"
    # shape.
    print()
    print("Matched single-contact comparison on insufficient_funds "
          "(topup@T+0 vs card_change@T+1):")
    t1_card_if = [
        r for r in results["SCRATCH_A1_T1"] if r.opening_condition_key == "insufficient_funds"
    ]
    print(f"  SCRATCH_A2_T0 (topup@T+0):      N={len(t0_inv)} "
          f"inv_rate={sum(t0_inv)/len(t0_inv):.4f}")
    print(f"  SCRATCH_A1_T1 (card_change@T+1): N={len(t1_card_if)} "
          f"inv_rate={rate(t1_card_if, 'invoice_recovered'):.4f}")

    # EXTRA: does moving A2's card-broken second contact from T+5 to T+3
    # (matching A1's schedule) close the AGGREGATE A1-vs-A2 gap?
    print()
    print("EXTRA - aggregate effect of A2's card-broken second-contact day (T+5 vs T+3):")
    a2_asis_inv_full = [float(r.invoice_recovered) for r in results["SCRATCH_A2_ASIS"]]
    a2_cb_t3_inv_full = [float(r.invoice_recovered) for r in results["SCRATCH_A2_CARDBROKEN_T3"]]
    print(f"  SCRATCH_A2_ASIS (T+5):        whole-cohort inv_rate={sum(a2_asis_inv_full)/N:.4f}")
    print(f"  SCRATCH_A2_CARDBROKEN_T3 (T+3): whole-cohort inv_rate={sum(a2_cb_t3_inv_full)/N:.4f}")
    d3, lo3, hi3 = paired_bootstrap_ci(a2_asis_inv_full, a2_cb_t3_inv_full, n_resamples=5000)
    print(f"  SCRATCH_A2_CARDBROKEN_T3 - SCRATCH_A2_ASIS diff={d3:+.4f} CI=[{lo3:+.4f},{hi3:+.4f}]")
    a1_asis_full = sum(float(r.invoice_recovered) for r in results["SCRATCH_A1_ASIS"]) / N
    print(f"  (for reference) SCRATCH_A1_ASIS whole-cohort inv_rate={a1_asis_full:.4f}")
    d4, lo4, hi4 = paired_bootstrap_ci(
        [float(r.invoice_recovered) for r in results["SCRATCH_A1_ASIS"]],
        a2_cb_t3_inv_full,
        n_resamples=5000,
    )
    print(f"  SCRATCH_A2_CARDBROKEN_T3 - SCRATCH_A1_ASIS diff={d4:+.4f} CI=[{lo4:+.4f},{hi4:+.4f}] "
          f"(remaining gap to A1 after fixing only the card-broken schedule)")

    return results


def main():
    print("Day 3 pre-agent diagnostic - NON-CANONICAL DIAGNOSTIC OUTPUT")
    print(f"MASTER_SEED={MASTER_SEED}, split={SPLIT!r}, N={N}, "
          f"indices={INDICES.start}-{INDICES.stop - 1}")

    register_scratch_arms()
    try:
        a1 = run_arm("A1")
        a2 = run_arm("A2")
    finally:
        unregister_scratch_arms()

    d, lo, hi = paired_bootstrap_ci(
        [float(r.invoice_recovered) for r in a1],
        [float(r.invoice_recovered) for r in a2],
        n_resamples=5000,
    )
    print(f"\nReproduction check - A2-A1 invoice recovery diff={d:+.4f} CI=[{lo:+.4f},{hi:+.4f}] "
          f"(Stage 5 Test 1 recorded A1-A2=-0.0355, i.e. A2-A1=+0.0355)")

    task2(a1, a2)
    task3()

    print()
    print("=" * 78)
    print("END OF NON-CANONICAL DIAGNOSTIC OUTPUT")
    print("=" * 78)


if __name__ == "__main__":
    main()
