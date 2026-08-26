"""Day 2 Stage 3: the first reproducible A0-vs-A2 result.

dev split, 2,000 episodes (indices 1000-2999), paired CRN (episode i's world
is byte-identical across arms - see rrx.sim.engine.run_episode), paired
bootstrap 95% CI (model_params.yaml#/sweep/win_criterion#/test:
paired_bootstrap_95ci_excludes_zero - the project's existing statistical
convention, reused here rather than inventing a new one).

No manifest, no results directory, no formatting infrastructure - prints a
plain report to stdout. Run with:

    python -m rrx.sim.run_stage3
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np

from rrx.sim.engine import EpisodeResult, run_episode
from rrx.sim.latent import load_configs
from rrx.spec.registry import config_dir

SPLIT = "dev"
EPISODE_INDICES = range(1000, 3000)  # 2,000 episodes, seeds 1000-2999
N_BOOTSTRAP_RESAMPLES = 10_000
CI_LEVEL = 0.95
# Fixed, distinct from the episode-world MASTER_SEED - resampling only.
BOOTSTRAP_SEED = 20260826


@dataclass(frozen=True, slots=True)
class PairedBatch:
    a0: tuple[EpisodeResult, ...]
    a2: tuple[EpisodeResult, ...]


def run_batch(split: str, indices: range, episode_cfg, population_cfg) -> PairedBatch:
    a0 = tuple(run_episode(split, i, "A0", episode_cfg, population_cfg) for i in indices)
    a2 = tuple(run_episode(split, i, "A2", episode_cfg, population_cfg) for i in indices)
    return PairedBatch(a0=a0, a2=a2)


def paired_bootstrap_ci(
    a: list[float] | tuple[float, ...],
    b: list[float] | tuple[float, ...],
    n_resamples: int = N_BOOTSTRAP_RESAMPLES,
    ci: float = CI_LEVEL,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float, float]:
    """Paired bootstrap on mean(b) - mean(a). Returns (point_estimate, lo, hi).

    Resamples EPISODE INDICES (not a/b independently) - the pairing (same
    episode i's world under both arms) is what CRN buys, and resampling
    indices together is what preserves it in the bootstrap.
    """
    if len(a) != len(b):
        raise ValueError("paired arrays must be the same length")
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    n = len(a_arr)
    point = float(np.mean(b_arr - a_arr))

    rng = np.random.default_rng(seed)
    diffs = np.empty(n_resamples)
    for k in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        diffs[k] = np.mean(b_arr[idx] - a_arr[idx])

    alpha = 1.0 - ci
    lo, hi = np.quantile(diffs, [alpha / 2, 1.0 - alpha / 2])
    return point, float(lo), float(hi)


def _rate(results: tuple[EpisodeResult, ...], attr: str) -> float:
    return sum(getattr(r, attr) for r in results) / len(results)


def _whatsapp_cost_inr() -> float:
    import yaml

    with open(config_dir() / "costs.yaml") as fh:
        costs = yaml.safe_load(fh)
    return costs["messaging"]["whatsapp"]["cost_inr"]


def main() -> None:
    episode_cfg, population_cfg = load_configs()
    batch = run_batch(SPLIT, EPISODE_INDICES, episode_cfg, population_cfg)
    n = len(EPISODE_INDICES)

    a0_invoice = [float(r.invoice_recovered) for r in batch.a0]
    a2_invoice = [float(r.invoice_recovered) for r in batch.a2]
    a0_rescue = [float(r.subscription_rescued) for r in batch.a0]
    a2_rescue = [float(r.subscription_rescued) for r in batch.a2]

    invoice_point, invoice_lo, invoice_hi = paired_bootstrap_ci(a0_invoice, a2_invoice)
    rescue_point, rescue_lo, rescue_hi = paired_bootstrap_ci(a0_rescue, a2_rescue)

    a2_recovered_count = sum(r.invoice_recovered for r in batch.a2)
    a2_rescued_count = sum(r.subscription_rescued for r in batch.a2)
    a2_total_contacts = sum(r.contacts_sent for r in batch.a2)
    # Contacts whose engagement+effect resolution changed no physical state -
    # not "payment retry attempts": the agent has no retry action at all
    # (EVAL.md §1.1/§1.2), only Razorpay's automatic auto-retry retries.
    a2_no_op_contacts = sum(r.wasted_attempts for r in batch.a2)
    a2_rupees_recovered = sum(
        r.invoice_amount_inr for r in batch.a2 if r.invoice_recovered
    )
    a0_rupees_recovered = sum(
        r.invoice_amount_inr for r in batch.a0 if r.invoice_recovered
    )

    insufficient_funds_total = sum(
        1 for r in batch.a2 if r.opening_condition_key == "insufficient_funds"
    )
    # Rate of card-change prompts sent for insufficient_funds - a remedy/
    # decline-code mismatch, not a "retry" of any kind (see above).
    remedy_mismatch_count = sum(r.card_change_sent_for_insufficient_funds for r in batch.a2)
    remedy_mismatch_rate = (
        remedy_mismatch_count / insufficient_funds_total if insufficient_funds_total else 0.0
    )

    cancelled_contacts = sum(
        r.contacts_sent for r in batch.a2
        if r.opening_condition_key == "subscription_cancelled_by_customer"
    )

    no_op_cost_inr = a2_no_op_contacts * _whatsapp_cost_inr()

    print(
        f"Day 2 Stage 3 - A0 vs A2, split={SPLIT!r}, n={n}, "
        f"seeds {EPISODE_INDICES.start}-{EPISODE_INDICES.stop - 1}"
    )
    print()
    print("PRIMARY (Regime B)")
    print(
        f"  invoice recovery rate   A0={statistics.mean(a0_invoice):.4f}"
        f"  A2={statistics.mean(a2_invoice):.4f}"
        f"  diff(A2-A0)={invoice_point:+.4f}  95% CI=[{invoice_lo:+.4f}, {invoice_hi:+.4f}]"
    )
    print(
        f"  subscription rescue rate A0={statistics.mean(a0_rescue):.4f}"
        f"  A2={statistics.mean(a2_rescue):.4f}"
        f"  diff(A2-A0)={rescue_point:+.4f}  95% CI=[{rescue_lo:+.4f}, {rescue_hi:+.4f}]"
    )
    print()
    print("SECONDARY / A2")
    print(f"  Rupees recovered: A0=Rs{a0_rupees_recovered:,}  A2=Rs{a2_rupees_recovered:,}")
    print(f"  total contacts (A2): {a2_total_contacts}")
    print(f"  contacts per invoice recovered (A2): "
          f"{a2_total_contacts / a2_recovered_count if a2_recovered_count else float('nan'):.4f}")
    print(f"  contacts per rescue (A2): "
          f"{a2_total_contacts / a2_rescued_count if a2_rescued_count else float('nan'):.4f}")
    print(f"  no_op_contacts (A2): {a2_no_op_contacts}  cost: Rs{no_op_cost_inr:.2f}")
    print(
        "  remedy_mismatch_rate (card-change prompts for insufficient_funds / "
        f"insufficient_funds episodes): {remedy_mismatch_count}/{insufficient_funds_total}"
        f" = {remedy_mismatch_rate:.4f}"
    )
    print(f"  cancelled-at-open bucket contacts (A2): {cancelled_contacts} (must be 0)")


if __name__ == "__main__":
    main()
