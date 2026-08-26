"""Latent physical-state sampling (SIM.md §1, §2).

Samples the four hidden physical-state variables SIM.md §1 defines from a
decline code / opening condition, plus the two per-customer latent traits
Stage 3 will need (channel_response_propensity's customer trait,
card_change_completion_propensity), drawn once per customer.

Pure function of (seed, config): every distribution and constant is read
from configs/episode.yaml or configs/population.yaml at runtime. Random
draws use model_params.yaml's frozen `substream_isolation: per_variable`
design (SUBSTREAM_NAMES below) - each named variable gets its own
independent, name-keyed numpy Generator, never a single shared stream
threaded sequentially through unrelated draws. No wall-clock, no unseeded
RNG, no module-level mutable state.

Does not advance time, resolve retries, or handle actions - the clock and
action mechanics are SIM.md §3/§4 (Stage 3), not this module.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import yaml

from rrx.spec.registry import config_dir

# SIM.md §2: for `transaction_limit_exceeded` and `payment_risk_check_failed`,
# "never" means blocked_until is set beyond every auto-retry day (T+1..T+3),
# so §4's `t >= blocked_until` gate can never be satisfied within the
# episode. A sentinel, not a [MODEL] magnitude.
BLOCKED_INDEFINITELY: float = math.inf

# EVAL.md §6: master seed for the CRN scheme. Not a distribution parameter;
# given directly by EVAL.md §6, not derived from episode.yaml/population.yaml.
MASTER_SEED: int = 20260825

# model_params.yaml#/sweep/common_random_numbers/substreams, verbatim - the
# frozen substream_isolation: per_variable design. Exactly these eight;
# tests/test_latent_sampling.py checks set equality against the frozen
# config. Stage 1 draws from four of them (failure_condition,
# balance_restore, channel_response, card_change_completion); the other
# four (invoice_amount, topup_acceleration, cancellation_hazard,
# remaining_lifetime) belong to later stages / Regime A and are declared
# here for completeness only - nothing in this module invokes them.
SUBSTREAM_NAMES: tuple[str, ...] = (
    "invoice_amount",
    "failure_condition",
    "balance_restore",
    "topup_acceleration",
    "channel_response",
    "card_change_completion",
    "cancellation_hazard",
    "remaining_lifetime",
)

# population.yaml opening_conditions whose SIM.md §2 row sets
# card_chargeable = FALSE, funds_available_from = day 0 unconditionally.
_CARD_BROKEN_KEYS = ("card_expired", "debit_instrument_blocked", "card_not_enabled_group")

# population.yaml opening_conditions whose SIM.md §2 row says nothing about
# card_chargeable/funds_available_from at all (only about blocked_until or
# mandate_alive). Derived as "not the bottleneck" - card_chargeable=True,
# funds_available_from=0.0 - so the row's own named mechanism (blocked_until
# or mandate_alive) is the sole blocking factor in SIM.md §4's AND-gate.
_MECHANISM_ISOLATED_KEYS = (
    "subscription_cancelled_by_customer",
    "bank_technical_error",
    "transaction_limit_exceeded",
    "payment_risk_check_failed",
)


@dataclass(frozen=True)
class LatentState:
    card_chargeable: bool
    funds_available_from: float
    mandate_alive: bool
    blocked_until: float
    channel_response_trait: float
    card_change_completion_propensity: float


def _load_yaml(name: str) -> dict[str, Any]:
    with open(config_dir() / name) as fh:
        return yaml.safe_load(fh)


def load_configs() -> tuple[dict[str, Any], dict[str, Any]]:
    """Fresh (episode_cfg, population_cfg), loaded from disk each call."""
    return _load_yaml("episode.yaml"), _load_yaml("population.yaml")


def seed_for_substream(
    split: str, i: int, substream: str, master_seed: int = MASTER_SEED
) -> int:
    """EVAL.md §6 CRN, combined with model_params.yaml's
    `substream_isolation: per_variable`.

    Stable and name-keyed: derived from (master_seed, split, i, substream)
    via sha256, never from a positional spawn index. A variable's stream
    depends only on its own name - never on call order, or on how many
    draws any other variable's stream has consumed - which is what makes
    per-variable isolation actually hold. Python's built-in hash() is also
    unsuitable here regardless: it is salted per-process for strings, so it
    would not reproduce across separate runs.
    """
    digest = hashlib.sha256(f"{master_seed}:{split}:{i}:{substream}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def rng_for_substream(
    split: str, i: int, substream: str, master_seed: int = MASTER_SEED
) -> np.random.Generator:
    if substream not in SUBSTREAM_NAMES:
        raise KeyError(f"not a frozen substream name: {substream!r}")
    return np.random.default_rng(seed_for_substream(split, i, substream, master_seed))


def _beta_from_mean_concentration(
    rng: np.random.Generator, mean: float, concentration: float
) -> float:
    if not (0.0 < mean < 1.0):
        raise ValueError(f"Beta mean must be in (0, 1): {mean}")
    if concentration <= 0:
        raise ValueError(f"Beta concentration must be > 0: {concentration}")
    alpha = mean * concentration
    beta_param = (1.0 - mean) * concentration
    return float(rng.beta(alpha, beta_param))


def _sample_channel_response_trait(
    rng: np.random.Generator, episode_cfg: dict[str, Any]
) -> float:
    cfg = episode_cfg["latent"]["channel_response_propensity"]["customer_trait"]
    return _beta_from_mean_concentration(rng, cfg["mean"], cfg["concentration"])


def _sample_card_change_completion_propensity(
    rng: np.random.Generator, episode_cfg: dict[str, Any]
) -> float:
    cfg = episode_cfg["latent"]["card_change_completion_propensity"]
    return _beta_from_mean_concentration(rng, cfg["mean"], cfg["concentration"])


def _sample_truncated_exponential(
    rng: np.random.Generator, mean_days: float, lo: float, hi: float
) -> float:
    """Inverse-CDF truncation onto [lo, hi], not rejection sampling.

    A fixed single rng.random() call, never an unbounded loop. For
    Exponential(mean_days) with CDF F(x) = 1 - exp(-x/mean_days), the
    truncated inverse is X = -mean_days * ln(a - u*(a - b)) where
    a = exp(-lo/mean_days), b = exp(-hi/mean_days), u ~ Uniform(0, 1).
    """
    u = rng.random()
    a = math.exp(-lo / mean_days)
    b = math.exp(-hi / mean_days)
    return -mean_days * math.log(a - u * (a - b))


def _canonical_pmf_arrays(pmf: dict[Any, float]) -> tuple[list[Any], list[float]]:
    """Sort a {day: probability} mapping by numeric day, so the resulting
    arrays never depend on the dict's insertion order (e.g. YAML key order).

    list(pmf.keys())/list(pmf.values()) keeps each key paired with its own
    probability regardless of order, but the ORDER of the resulting arrays
    still varied with insertion order - a violation of Stage 1's purity
    rule (results must not depend on dict ordering), even though it never
    broke correctness by itself.
    """
    items = sorted(pmf.items(), key=lambda item: item[0])
    return [day for day, _ in items], [prob for _, prob in items]


def _sample_balance_restore_delay(rng: np.random.Generator, episode_cfg: dict[str, Any]) -> float:
    """episode.yaml#/latent/balance_restore_delay. ORIGINAL (unaccelerated)
    draw only - top-up acceleration is per-engagement and belongs to Stage 3.
    """
    mixture = episode_cfg["latent"]["balance_restore_delay"]["mixture"]
    transient = mixture["transient"]
    salary_cycle = mixture["salary_cycle"]

    if rng.random() < transient["weight"]:
        lo, hi = transient["support_days"]
        return _sample_truncated_exponential(rng, transient["mean_days"], lo, hi)

    days, probs = _canonical_pmf_arrays(salary_cycle["salary_day_pmf"])
    salary_day = rng.choice(days, p=probs)

    jitter_cfg = salary_cycle["jitter"]
    shape = jitter_cfg["shape"]
    scale = jitter_cfg["mean_days"] / shape
    jitter = rng.gamma(shape, scale)

    return float(salary_day) + float(jitter)


def _sample_bank_technical_error_clearance(
    rng: np.random.Generator, episode_cfg: dict[str, Any]
) -> float:
    lo, hi = episode_cfg["latent"]["bank_technical_error_clearance"]["support_days"]
    return float(rng.uniform(lo, hi))


def draw_latent_state(
    split: str,
    i: int,
    opening_condition_key: str,
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    master_seed: int = MASTER_SEED,
) -> LatentState:
    """Sample the hidden physical state (SIM.md §1) for episode `i` of
    `split`, opening on `opening_condition_key` (a
    population.yaml#/opening_conditions key), plus the two per-customer
    latent traits Stage 3 needs.

    Each random quantity is drawn from its own named substream
    (rng_for_substream), derived solely from (split, i, substream_name) -
    never from a shared generator threaded through by the caller, and never
    from a positional spawn index. The arm is never an input to any of them.
    """
    conditions = {c["key"]: c for c in population_cfg["opening_conditions"]}
    if opening_condition_key not in conditions:
        raise KeyError(f"unknown opening condition: {opening_condition_key!r}")
    condition = conditions[opening_condition_key]

    channel_response_trait = _sample_channel_response_trait(
        rng_for_substream(split, i, "channel_response", master_seed), episode_cfg
    )
    card_change_completion_propensity = _sample_card_change_completion_propensity(
        rng_for_substream(split, i, "card_change_completion", master_seed), episode_cfg
    )

    # SIM.md §2: "Unless stated otherwise, mandate_alive = TRUE and
    # blocked_until = never at T=0 for all rows except cancelled." SIM.md's
    # own "Discovered semantic clarification" scopes the indefinite-block
    # (BLOCKED_INDEFINITELY) reading of "never" to transaction_limit_exceeded
    # and payment_risk_check_failed ONLY - for every other row, "no block"
    # must default to non-blocking (0.0), or SIM.md §4's t >= blocked_until
    # gate could never be satisfied for those rows regardless of
    # card_chargeable/funds_available_from, contradicting SIM.md §3's
    # explicit statement that transient-mode insufficient_funds customers
    # recover "with no agent action" inside T+1...T+3.
    #
    # DEFECT FIX (2026-08-26, discovered building Day 2 Stage 3): this
    # default was previously BLOCKED_INDEFINITELY unconditionally, which
    # silently blocked auto-retry success for insufficient_funds,
    # ambiguous_decline, and all three card-broken keys - 91% of the
    # population - regardless of any other state. Confirmed empirically: a
    # 2000-episode A0 dev run recovered invoices ONLY via
    # bank_technical_error (51/51), zero via insufficient_funds. The two
    # rows the clarification actually names now set BLOCKED_INDEFINITELY
    # explicitly, below.
    mandate_alive = True
    blocked_until = 0.0

    key = condition["key"]

    if key == "insufficient_funds":
        card_chargeable = True
        funds_available_from = _sample_balance_restore_delay(
            rng_for_substream(split, i, "balance_restore", master_seed), episode_cfg
        )

    elif key == "ambiguous_decline":
        # ambiguous_cause_split lives inside failure_mix_weights
        # (model_params.yaml) - "failure_condition" is that family's
        # substream, not a new one.
        p_card_cause = condition["p_card_cause"]
        failure_rng = rng_for_substream(split, i, "failure_condition", master_seed)
        card_chargeable = bool(failure_rng.random() < p_card_cause)
        if card_chargeable:
            funds_available_from = _sample_balance_restore_delay(
                rng_for_substream(split, i, "balance_restore", master_seed), episode_cfg
            )
        else:
            # SIM.md §2: card-problem rows get funds_available_from = day 0.
            funds_available_from = 0.0

    elif key in _CARD_BROKEN_KEYS:
        card_chargeable = False
        funds_available_from = 0.0

    elif key in _MECHANISM_ISOLATED_KEYS:
        # Not a card or funds problem - see _MECHANISM_ISOLATED_KEYS comment.
        card_chargeable = True
        funds_available_from = 0.0
        if key == "subscription_cancelled_by_customer":
            mandate_alive = False
        elif key == "bank_technical_error":
            # transient_block_clearance is nested inside balance_restore_timing
            # (model_params.yaml), alongside balance_restore_delay - both
            # share the "balance_restore" substream. The two never fire for
            # the same episode (an episode has exactly one opening
            # condition), so there is nothing for them to contaminate.
            blocked_until = _sample_bank_technical_error_clearance(
                rng_for_substream(split, i, "balance_restore", master_seed), episode_cfg
            )
        elif key in ("transaction_limit_exceeded", "payment_risk_check_failed"):
            # SIM.md's "Discovered semantic clarification": for these two
            # rows only, "never" means blocked_until is set beyond every
            # auto-retry day, so §4's t >= blocked_until gate can never be
            # satisfied for them within the episode.
            blocked_until = BLOCKED_INDEFINITELY

    else:
        raise KeyError(f"opening condition {key!r} has no SIM.md §2 mapping")

    return LatentState(
        card_chargeable=card_chargeable,
        funds_available_from=funds_available_from,
        mandate_alive=mandate_alive,
        blocked_until=blocked_until,
        channel_response_trait=channel_response_trait,
        card_change_completion_propensity=card_change_completion_propensity,
    )
