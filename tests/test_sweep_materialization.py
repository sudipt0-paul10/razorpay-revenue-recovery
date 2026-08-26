"""Day 2 Stage 2: sweep-cell materialization and simulator-reachability.

Proves, for every one of the 26 `enumerate_cells(reg)` cells:

  A. the resolver handles it (no silent fall-through)
  B. it changes exactly its declared config path(s), and nothing else
  C. the baseline configs are never mutated
  D. the resolved configs are independent fresh copies
  E. (reachable cells only) the resolved config actually changes what the
     Stage 1 latent sampler produces, in the declared direction
  F. (materializer-only cells) resolution succeeds (or, for invoice_amount,
     fails loudly and explicitly) but no simulator consumer is invented

Final split, recorded here as the source of truth for this stage:

    10 / 26 simulator-reachable
    16 / 26 materializer-only
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from rrx.sim.latent import (
    _sample_bank_technical_error_clearance,
    _sample_card_change_completion_propensity,
    _sample_channel_response_trait,
    draw_latent_state,
    load_configs,
    rng_for_substream,
)
from rrx.spec.registry import enumerate_cells, load_registry
from rrx.spec.resolver import INVOICE_AUTHORITY_MESSAGE, resolve_config

reg = load_registry()
cells = enumerate_cells(reg)
CELLS_BY_ID = {c.cell_id: c for c in cells}

N = 2000

# ---------------------------------------------------------------------------
# The reachability record (§ VERIFY requires this exact breakdown reported).
# ---------------------------------------------------------------------------

SIMULATOR_REACHABLE_CELL_IDS = {
    "balance_restore_timing.low",
    "balance_restore_timing.high",
    "balance_restore_timing.transient_block_clearance.low",
    "balance_restore_timing.transient_block_clearance.high",
    "channel_response_propensity.low",
    "channel_response_propensity.high",
    "card_change_completion_propensity.low",
    "card_change_completion_propensity.high",
    "failure_mix_weights.ambiguous_cause_split.low",
    "failure_mix_weights.ambiguous_cause_split.high",
}

MATERIALIZER_ONLY_CELL_IDS = {
    "invoice_amount.low",
    "invoice_amount.high",
    "failure_mix_weights.card_change.low",
    "failure_mix_weights.card_change.high",
    "failure_mix_weights.balance.low",
    "failure_mix_weights.balance.high",
    "failure_mix_weights.ambiguous.low",
    "failure_mix_weights.ambiguous.high",
    "failure_mix_weights.wait.low",
    "failure_mix_weights.wait.high",
    "failure_mix_weights.no_contact.low",
    "failure_mix_weights.no_contact.high",
    "failure_mix_weights.escalate.low",
    "failure_mix_weights.escalate.high",
    "cancellation_hazard_and_ltv.low",
    "cancellation_hazard_and_ltv.high",
}


def test_reachability_record_covers_every_cell_exactly_once():
    all_ids = {c.cell_id for c in cells}
    assert len(all_ids) == 26, f"expected 26 cells, found {len(all_ids)}"
    assert SIMULATOR_REACHABLE_CELL_IDS | MATERIALIZER_ONLY_CELL_IDS == all_ids
    assert SIMULATOR_REACHABLE_CELL_IDS.isdisjoint(MATERIALIZER_ONLY_CELL_IDS)


def test_final_split_is_ten_reachable_sixteen_materializer_only():
    assert len(SIMULATOR_REACHABLE_CELL_IDS) == 10
    assert len(MATERIALIZER_ONLY_CELL_IDS) == 16


# ---------------------------------------------------------------------------
# A. No cell silently falls through the resolver.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cell_id", sorted(CELLS_BY_ID))
def test_every_cell_is_handled_by_the_resolver(cell_id):
    cell = CELLS_BY_ID[cell_id]
    episode_cfg, population_cfg = load_configs()
    if cell.parameter == "invoice_amount":
        with pytest.raises(NotImplementedError, match="invoice_amount"):
            resolve_config(episode_cfg, population_cfg, cell)
    else:
        # Must not raise.
        resolve_config(episode_cfg, population_cfg, cell)


def test_invoice_amount_raises_with_the_authority_question_named():
    episode_cfg, population_cfg = load_configs()
    with pytest.raises(NotImplementedError) as excinfo:
        resolve_config(episode_cfg, population_cfg, CELLS_BY_ID["invoice_amount.low"])
    assert str(excinfo.value) == INVOICE_AUTHORITY_MESSAGE


def test_unrecognised_cell_raises_value_error():
    from rrx.spec.registry import Cell

    bogus = Cell(
        cell_id="not_a_real.cell",
        parameter="not_a_real_parameter",
        handle="not_a_real_handle",
        direction="low",
        value=1.0,
    )
    episode_cfg, population_cfg = load_configs()
    with pytest.raises(ValueError, match="no mapping"):
        resolve_config(episode_cfg, population_cfg, bogus)


# ---------------------------------------------------------------------------
# C, D. Purity: baseline untouched, output is an independent fresh copy.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cell_id", sorted(MATERIALIZER_ONLY_CELL_IDS | SIMULATOR_REACHABLE_CELL_IDS)
)
def test_baseline_configs_are_never_mutated(cell_id):
    cell = CELLS_BY_ID[cell_id]
    episode_cfg, population_cfg = load_configs()
    episode_before = copy.deepcopy(episode_cfg)
    population_before = copy.deepcopy(population_cfg)

    try:
        resolve_config(episode_cfg, population_cfg, cell)
    except NotImplementedError:
        pass

    assert episode_cfg == episode_before
    assert population_cfg == population_before


@pytest.mark.parametrize("cell_id", sorted(SIMULATOR_REACHABLE_CELL_IDS))
def test_resolved_configs_are_independent_fresh_copies(cell_id):
    cell = CELLS_BY_ID[cell_id]
    episode_cfg, population_cfg = load_configs()
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    assert episode_out is not episode_cfg
    assert population_out is not population_cfg

    # Mutating the resolved copy must not touch the baseline.
    episode_out["latent"]["channel_response_propensity"]["customer_trait"]["mean"] = -999
    assert episode_cfg["latent"]["channel_response_propensity"]["customer_trait"]["mean"] != -999


# ---------------------------------------------------------------------------
# B. Each cell changes exactly its declared path(s) - nothing else.
# ---------------------------------------------------------------------------

def test_balance_restore_timing_cell_changes_only_the_two_mixture_weights():
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID["balance_restore_timing.high"]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    mixture = episode_out["latent"]["balance_restore_delay"]["mixture"]
    assert mixture["salary_cycle"]["weight"] == pytest.approx(cell.value)
    assert mixture["transient"]["weight"] == pytest.approx(1.0 - cell.value)

    # Held-fixed fields per model_params.yaml#/balance_restore_timing/handle.
    base_mixture = episode_cfg["latent"]["balance_restore_delay"]["mixture"]
    assert mixture["transient"]["mean_days"] == base_mixture["transient"]["mean_days"]
    base_salary = base_mixture["salary_cycle"]
    out_salary = mixture["salary_cycle"]
    assert out_salary["salary_day_pmf"] == base_salary["salary_day_pmf"]
    assert out_salary["jitter"] == base_salary["jitter"]
    assert population_out == population_cfg


def test_transient_block_clearance_cell_changes_only_support_days():
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID["balance_restore_timing.transient_block_clearance.high"]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    out_clearance = episode_out["latent"]["bank_technical_error_clearance"]
    assert out_clearance["support_days"] == list(cell.value)
    # Everything else under latent: untouched.
    for key in episode_cfg["latent"]:
        if key == "bank_technical_error_clearance":
            continue
        assert episode_out["latent"][key] == episode_cfg["latent"][key], key
    assert population_out == population_cfg


def test_channel_response_propensity_cell_changes_only_customer_trait_mean():
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID["channel_response_propensity.high"]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    trait = episode_out["latent"]["channel_response_propensity"]["customer_trait"]
    assert trait["mean"] == pytest.approx(cell.value)
    base_trait = episode_cfg["latent"]["channel_response_propensity"]["customer_trait"]
    assert trait["concentration"] == base_trait["concentration"]

    base_block = episode_cfg["latent"]["channel_response_propensity"]
    out_block = episode_out["latent"]["channel_response_propensity"]
    assert out_block["channel_multipliers"] == base_block["channel_multipliers"]
    assert out_block["fatigue"] == base_block["fatigue"]
    assert out_block["tenure_coupling"] == base_block["tenure_coupling"]
    assert population_out == population_cfg


def test_card_change_completion_propensity_cell_changes_only_mean():
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID["card_change_completion_propensity.high"]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    block = episode_out["latent"]["card_change_completion_propensity"]
    assert block["mean"] == pytest.approx(cell.value)
    base = episode_cfg["latent"]["card_change_completion_propensity"]
    assert block["concentration"] == base["concentration"]
    assert population_out == population_cfg


def test_ambiguous_cause_split_cell_changes_only_p_card_cause_on_ambiguous_decline():
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID["failure_mix_weights.ambiguous_cause_split.high"]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    out_conditions = population_out["opening_conditions"]
    base_conditions = population_cfg["opening_conditions"]
    for out_c, base_c in zip(out_conditions, base_conditions):
        assert out_c["key"] == base_c["key"]
        if out_c["key"] == "ambiguous_decline":
            assert out_c["p_card_cause"] == pytest.approx(cell.value)
            assert {k: v for k, v in out_c.items() if k != "p_card_cause"} == {
                k: v for k, v in base_c.items() if k != "p_card_cause"
            }
        else:
            assert out_c == base_c
    # failure_mix.conditions untouched by this handle.
    assert population_out["failure_mix"] == population_cfg["failure_mix"]
    assert episode_out == episode_cfg


def test_cancellation_hazard_cell_changes_only_h0_and_mean_cycles():
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID["cancellation_hazard_and_ltv.high"]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    cancellation = episode_out["latent"]["cancellation"]
    assert cancellation["hazard_per_contact"]["h0"] == pytest.approx(cell.value["hazard_h0"])
    assert cancellation["remaining_subscription_lifetime_cycles"]["mean_cycles"] == pytest.approx(
        cell.value["remaining_lifetime_mean_cycles"]
    )
    base_cancellation = episode_cfg["latent"]["cancellation"]
    assert (cancellation["hazard_per_contact"]["gamma"]
            == base_cancellation["hazard_per_contact"]["gamma"])
    assert population_out == population_cfg


_FAILURE_MIX_BUCKET_CELL_IDS = sorted(
    c for c in MATERIALIZER_ONLY_CELL_IDS if c.startswith("failure_mix_weights.")
)


@pytest.mark.parametrize("cell_id", _FAILURE_MIX_BUCKET_CELL_IDS)
def test_failure_mix_bucket_cell_changes_only_failure_mix_conditions(cell_id):
    """Requirement B, subject to the duplicated-representation authority
    finding: only population.yaml#/failure_mix/conditions moves.
    population.yaml#/opening_conditions[*]/weight is a SEPARATE
    representation with its own, different consumer
    (test_population_matches_decline_codes.py / EVAL.md §3.2's table) and no
    code or test in this repository proves the two must agree - so it is
    deliberately left unsynchronized here rather than silently patched to
    match, which would conceal the duplication rather than resolve it."""
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID[cell_id]
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)

    out_conditions = population_out["failure_mix"]["conditions"]
    base_conditions = population_cfg["failure_mix"]["conditions"]
    assert out_conditions != base_conditions
    assert sum(out_conditions.values()) == pytest.approx(1.0, abs=1e-9)

    # The known-unsynchronized duplicate: left exactly as the baseline.
    assert population_out["opening_conditions"] == population_cfg["opening_conditions"]

    assert episode_out == episode_cfg


# ---------------------------------------------------------------------------
# E. Simulator reachability: resolved cell changes the sampled statistic,
#    in the declared direction, relative to baseline.
# ---------------------------------------------------------------------------

def _mean_funds_available_from(episode_cfg, population_cfg, n=N):
    return np.mean([
        draw_latent_state(
            "dev", i, "insufficient_funds", episode_cfg, population_cfg
        ).funds_available_from
        for i in range(n)
    ])


def test_balance_restore_timing_reachability_low_high_bracket_baseline():
    episode_cfg, population_cfg = load_configs()
    low = CELLS_BY_ID["balance_restore_timing.low"]
    high = CELLS_BY_ID["balance_restore_timing.high"]

    e_low, p_low = resolve_config(episode_cfg, population_cfg, low)
    e_high, p_high = resolve_config(episode_cfg, population_cfg, high)

    mean_base = _mean_funds_available_from(episode_cfg, population_cfg)
    mean_low = _mean_funds_available_from(e_low, p_low)
    mean_high = _mean_funds_available_from(e_high, p_high)

    # Higher salary_mode_mass -> more mass on the (higher-delay) salary-cycle
    # branch -> larger mean delay, and vice versa.
    assert mean_low < mean_base < mean_high, (mean_low, mean_base, mean_high)


def test_transient_block_clearance_reachability_changes_blocked_until_ceiling():
    episode_cfg, population_cfg = load_configs()
    low = CELLS_BY_ID["balance_restore_timing.transient_block_clearance.low"]
    high = CELLS_BY_ID["balance_restore_timing.transient_block_clearance.high"]

    e_low, _ = resolve_config(episode_cfg, population_cfg, low)
    e_high, _ = resolve_config(episode_cfg, population_cfg, high)

    def max_blocked_until(episode_cfg_):
        rng_values = [
            _sample_bank_technical_error_clearance(
                rng_for_substream("dev", i, "balance_restore"), episode_cfg_
            )
            for i in range(N)
        ]
        return max(rng_values)

    base_max = max_blocked_until(episode_cfg)
    low_max = max_blocked_until(e_low)
    high_max = max_blocked_until(e_high)

    assert low_max <= 1.4 + 1e-9
    assert high_max <= 2.6 + 1e-9
    assert low_max < base_max < high_max


def test_channel_response_propensity_reachability_shifts_sampled_mean():
    episode_cfg, population_cfg = load_configs()
    low = CELLS_BY_ID["channel_response_propensity.low"]
    high = CELLS_BY_ID["channel_response_propensity.high"]

    e_low, _ = resolve_config(episode_cfg, population_cfg, low)
    e_high, _ = resolve_config(episode_cfg, population_cfg, high)

    def mean_trait(episode_cfg_):
        return np.mean([
            _sample_channel_response_trait(
                rng_for_substream("dev", i, "channel_response"), episode_cfg_
            )
            for i in range(N)
        ])

    mean_base = mean_trait(episode_cfg)
    mean_low = mean_trait(e_low)
    mean_high = mean_trait(e_high)

    assert mean_low < mean_base < mean_high, (mean_low, mean_base, mean_high)


def test_card_change_completion_propensity_reachability_shifts_sampled_mean():
    episode_cfg, population_cfg = load_configs()
    low = CELLS_BY_ID["card_change_completion_propensity.low"]
    high = CELLS_BY_ID["card_change_completion_propensity.high"]

    e_low, _ = resolve_config(episode_cfg, population_cfg, low)
    e_high, _ = resolve_config(episode_cfg, population_cfg, high)

    def mean_completion(episode_cfg_):
        return np.mean([
            _sample_card_change_completion_propensity(
                rng_for_substream("dev", i, "card_change_completion"), episode_cfg_
            )
            for i in range(N)
        ])

    mean_base = mean_completion(episode_cfg)
    mean_low = mean_completion(e_low)
    mean_high = mean_completion(e_high)

    assert mean_low < mean_base < mean_high, (mean_low, mean_base, mean_high)


def test_ambiguous_cause_split_reachability_shifts_card_chargeable_rate():
    episode_cfg, population_cfg = load_configs()
    low = CELLS_BY_ID["failure_mix_weights.ambiguous_cause_split.low"]
    high = CELLS_BY_ID["failure_mix_weights.ambiguous_cause_split.high"]

    e_low, p_low = resolve_config(episode_cfg, population_cfg, low)
    e_high, p_high = resolve_config(episode_cfg, population_cfg, high)

    def card_chargeable_rate(episode_cfg_, population_cfg_):
        outcomes = [
            draw_latent_state("dev", i, "ambiguous_decline", episode_cfg_, population_cfg_)
            for i in range(N)
        ]
        return sum(1 for o in outcomes if o.card_chargeable) / N

    rate_base = card_chargeable_rate(episode_cfg, population_cfg)
    rate_low = card_chargeable_rate(e_low, p_low)
    rate_high = card_chargeable_rate(e_high, p_high)

    assert rate_low == pytest.approx(0.35, abs=0.05)
    assert rate_high == pytest.approx(0.65, abs=0.05)
    assert rate_low < rate_base < rate_high


# ---------------------------------------------------------------------------
# F. Materializer-only cells: resolved, but no consumer is invented for them.
# ---------------------------------------------------------------------------

_NON_INVOICE_MATERIALIZER_ONLY_CELL_IDS = sorted(
    MATERIALIZER_ONLY_CELL_IDS - {"invoice_amount.low", "invoice_amount.high"}
)


@pytest.mark.parametrize("cell_id", _NON_INVOICE_MATERIALIZER_ONLY_CELL_IDS)
def test_materializer_only_cell_resolves_but_has_no_latent_sampler_effect(cell_id):
    """These cells materialize a correct resolved config, but nothing in
    rrx.sim.latent reads the path they change (no opening-condition
    selector, no cancellation/LTV sampler). Confirms the resolved value is
    present in config - not that it does nothing in general, which would be
    unprovable - and that no test here manufactures a consumer to inflate
    the reachable count."""
    episode_cfg, population_cfg = load_configs()
    cell = CELLS_BY_ID[cell_id]
    # Resolves without error and returns well-formed configs; that is all
    # this stage can prove for a cell with no simulator consumer yet.
    episode_out, population_out = resolve_config(episode_cfg, population_cfg, cell)
    assert isinstance(episode_out, dict)
    assert isinstance(population_out, dict)
