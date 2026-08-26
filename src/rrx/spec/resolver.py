"""Cell -> resolved-config materialization (Day 2 Stage 2).

Pure function: takes a baseline (episode_cfg, population_cfg) pair and one
model_params.yaml sweep Cell (from `enumerate_cells`), and returns a FRESH,
deep-copied (episode_cfg, population_cfg) pair with exactly that cell's
target path(s) perturbed. Never mutates its inputs. Does not run the
simulator, the agent, or a policy - it only produces the config a consumer
would read.

Dispatch is by the cell's declared `handle` (and `parameter` for the
vector-simplex case), not by pattern-matching `cell_id` strings - handles are
the stable, declared identity `enumerate_cells` assigns; cell_id is a
derived label.

Two deliberate non-resolutions, both explained in the module they concern:

  - `invoice_amount` cells raise NotImplementedError. Two independent runtime
    representations exist (population.yaml#/invoice_amount_inr and
    episode.yaml#/invoice_amount_inr#mu_expression) and neither has a
    simulator consumer today, so there is no evidence to establish either as
    authoritative. Inventing an authority here would be exactly the kind of
    silent decision CLAUDE.md §4 and this stage's brief forbid.

  - `failure_mix_weights` bucket-mass cells update ONLY
    population.yaml#/failure_mix/conditions (the representation
    model_params.yaml's owner_path names, and the one
    rrx.spec.registry.expand_to_conditions/resolve_owner_path actually
    consume). population.yaml#/opening_conditions[*]/weight is a SEPARATE,
    non-derived representation - it is read only by
    tests/test_population_matches_decline_codes.py and appears to back
    EVAL.md §3.2's table, not by any resolver or simulator code path - and is
    left untouched here. There is no test or code in this repository proving
    the two agree, so synchronizing them here would conceal, not resolve, an
    existing duplication. See tests/test_sweep_materialization.py for the
    cell-by-cell reachability/authority record.
"""

from __future__ import annotations

import copy
from typing import Any

from rrx.spec.registry import Cell, expand_to_conditions, load_registry

INVOICE_AUTHORITY_MESSAGE = (
    "invoice_amount has two independent, uncorrelated runtime representations "
    "(population.yaml#/invoice_amount_inr, episode.yaml#/invoice_amount_inr) "
    "and no simulator consumer exists for either today, so there is no basis "
    "to pick one as authoritative. Resolve this when the invoice sampler is "
    "built (not in Stage 2)."
)


def _bucket_members_and_baseline() -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
    reg = load_registry()
    buckets = reg.parameters["failure_mix_weights"]["handle"]["buckets"]
    members = {b: s["members"] for b, s in buckets.items()}
    return members, buckets


def resolve_config(
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    cell: Cell,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a fresh (episode_cfg, population_cfg) pair with `cell` applied.

    Raises NotImplementedError for invoice_amount cells (see module
    docstring) and ValueError for any cell whose (parameter, handle) this
    resolver does not recognise.
    """
    if cell.parameter == "invoice_amount":
        raise NotImplementedError(INVOICE_AUTHORITY_MESSAGE)

    episode_out = copy.deepcopy(episode_cfg)
    population_out = copy.deepcopy(population_cfg)

    if cell.parameter == "failure_mix_weights" and cell.handle.startswith("bucket_mass:"):
        members, _ = _bucket_members_and_baseline()
        baseline_conditions = population_out["failure_mix"]["conditions"]
        resolved_conditions = expand_to_conditions(cell.value, members, baseline_conditions)
        population_out["failure_mix"]["conditions"] = resolved_conditions
        return episode_out, population_out

    if cell.parameter == "failure_mix_weights" and cell.handle == "p_card_cause":
        found = False
        for condition in population_out["opening_conditions"]:
            if condition["key"] == "ambiguous_decline":
                condition["p_card_cause"] = cell.value
                found = True
                break
        if not found:
            raise ValueError("opening_conditions has no 'ambiguous_decline' entry")
        return episode_out, population_out

    if cell.parameter == "balance_restore_timing" and cell.handle == "salary_mode_mass":
        mixture = episode_out["latent"]["balance_restore_delay"]["mixture"]
        mixture["salary_cycle"]["weight"] = cell.value
        mixture["transient"]["weight"] = 1.0 - cell.value
        return episode_out, population_out

    if cell.parameter == "balance_restore_timing" and cell.handle == "support_days_upper_bound":
        episode_out["latent"]["bank_technical_error_clearance"]["support_days"] = list(cell.value)
        return episode_out, population_out

    if cell.parameter == "channel_response_propensity" and cell.handle == "trait_mean":
        episode_out["latent"]["channel_response_propensity"]["customer_trait"]["mean"] = cell.value
        return episode_out, population_out

    if cell.parameter == "card_change_completion_propensity" and cell.handle == "completion_mean":
        episode_out["latent"]["card_change_completion_propensity"]["mean"] = cell.value
        return episode_out, population_out

    if cell.parameter == "cancellation_hazard_and_ltv" and cell.handle == "joint_multiplier":
        cancellation = episode_out["latent"]["cancellation"]
        cancellation["hazard_per_contact"]["h0"] = cell.value["hazard_h0"]
        cancellation["remaining_subscription_lifetime_cycles"]["mean_cycles"] = (
            cell.value["remaining_lifetime_mean_cycles"]
        )
        return episode_out, population_out

    raise ValueError(
        f"resolve_config: no mapping for cell {cell.cell_id!r} "
        f"(parameter={cell.parameter!r}, handle={cell.handle!r})"
    )
