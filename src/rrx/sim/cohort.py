"""Cohort generation (Day 2 Stage 3): opening-condition selection and
invoice-amount sampling.

Failure-mix authority (resolved in Stage 2, re-confirmed here): population.
yaml#/failure_mix/conditions is authoritative - model_params.yaml's
owner_path names it, rrx.spec.registry.expand_to_conditions/resolve_owner_
path read it, rrx.spec.resolver writes it for the failure_mix_weights sweep
cells. population.yaml#/opening_conditions[*]/weight is a derived,
currently-agreeing duplicate (tests/test_failure_mix_representations_agree.py
enforces the agreement). This module selects opening conditions from the
authoritative representation only.

Invoice-amount authority (resolved here, first real consumer): population.
yaml#/invoice_amount_inr, by the same owner_path convention that resolved
failure-mix - model_params.yaml#/parameters/invoice_amount#owner_path names
exactly this location. episode.yaml#/invoice_amount_inr is a numerically
identical, currently-unused duplicate (tests/test_invoice_amount_
representations_agree.py enforces the agreement).

RNG: uses the frozen `invoice_amount` substream directly (first real use -
Stage 1 never consumed it), and a `failure_condition` CHILD stream
(`failure_condition:opening_condition_select`, via rrx.sim.rng) for opening-
condition selection, kept independent of the existing `failure_condition`
draw (the ambiguous-cause Bernoulli inside draw_latent_state) so that
perturbing failure-mix bucket masses cannot shift the ambiguous-cause draw,
and vice versa - see rrx.sim.rng's module docstring for why this holds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from rrx.sim.latent import MASTER_SEED, rng_for_substream
from rrx.sim.rng import rng_for_child_stream

# opening_conditions[*].key -> failure_mix.conditions key it represents.
# Not mechanically derivable: 'ambiguous_decline' groups two codes into one
# failure_mix.conditions entry ('card_declined_or_payment_failed') that
# doesn't share either code's name, and 'card_not_enabled_group' groups
# three codes but matches only the single 'card_not_enrolled' entry (the
# other two grouped codes have no failure_mix.conditions entry at all).
# Declared explicitly from inspection of population.yaml; agreement with
# the authoritative weights is enforced by
# tests/test_failure_mix_representations_agree.py.
OPENING_CONDITION_TO_FAILURE_MIX_KEY: dict[str, str] = {
    "insufficient_funds": "insufficient_funds",
    "ambiguous_decline": "card_declined_or_payment_failed",
    "card_expired": "card_expired",
    "debit_instrument_blocked": "debit_instrument_blocked",
    "card_not_enabled_group": "card_not_enrolled",
    "subscription_cancelled_by_customer": "subscription_cancelled",
    "bank_technical_error": "bank_technical_error",
    "transaction_limit_exceeded": "transaction_limit_exceeded",
    "payment_risk_check_failed": "payment_risk_check_failed",
}


@dataclass(frozen=True, slots=True)
class CohortEpisode:
    opening_condition_key: str
    invoice_amount_inr: int


def _canonical_condition_keys(population_cfg: dict[str, Any]) -> list[str]:
    """Sorted opening_conditions keys - never dict/list iteration order."""
    return sorted(c["key"] for c in population_cfg["opening_conditions"])


def sample_opening_condition_key(
    split: str, i: int, population_cfg: dict[str, Any], master_seed: int = MASTER_SEED
) -> str:
    """Categorical draw over opening_conditions, weighted by the
    AUTHORITATIVE population.yaml#/failure_mix/conditions (via the mapping
    above), using a failure_condition CHILD stream distinct from the
    existing ambiguous-cause Bernoulli's bare `failure_condition` draw."""
    keys = _canonical_condition_keys(population_cfg)
    conditions = population_cfg["failure_mix"]["conditions"]
    weights = [conditions[OPENING_CONDITION_TO_FAILURE_MIX_KEY[k]] for k in keys]

    rng = rng_for_child_stream(
        split, i, "failure_condition", "opening_condition_select", master_seed
    )
    choice = rng.choice(len(keys), p=weights)
    return keys[int(choice)]


def sample_invoice_amount_inr(
    split: str, i: int, population_cfg: dict[str, Any], master_seed: int = MASTER_SEED
) -> int:
    """EVAL.md §3.1 / population.yaml#/invoice_amount_inr: LogNormal(mu=ln(
    median_inr), sigma), rejection-sampled into [lower, upper], rounded to
    the nearest rupee. Uses the frozen `invoice_amount` substream."""
    cfg = population_cfg["invoice_amount_inr"]
    median_inr = cfg["median_inr"]
    sigma = cfg["sigma"]
    lower, upper = cfg["support"]
    mu = math.log(median_inr)

    rng = rng_for_substream(split, i, "invoice_amount", master_seed)
    while True:
        draw = rng.lognormal(mean=mu, sigma=sigma)
        if lower <= draw <= upper:
            return round(draw)


def sample_cohort_episode(
    split: str, i: int, population_cfg: dict[str, Any], master_seed: int = MASTER_SEED
) -> CohortEpisode:
    return CohortEpisode(
        opening_condition_key=sample_opening_condition_key(split, i, population_cfg, master_seed),
        invoice_amount_inr=sample_invoice_amount_inr(split, i, population_cfg, master_seed),
    )
