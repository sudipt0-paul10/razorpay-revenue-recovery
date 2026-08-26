"""Day 2 Stage 3 §0(c): the two failure-mix representations in
population.yaml must agree at baseline.

Authority decision (given, not investigated here): population.yaml#/failure_
mix/conditions is authoritative - model_params.yaml's owner_path names it,
rrx.spec.registry.expand_to_conditions/resolve_owner_path read it, and
rrx.spec.resolver writes it for the failure_mix_weights sweep cells (see
tests/test_sweep_materialization.py). population.yaml#/opening_conditions[*]/
weight is derived and MUST be kept numerically consistent with it;
rrx.sim.cohort - the real consumer - selects opening conditions from the
authoritative representation only, via the mapping this test imports from
there rather than duplicating.

There is no per-code correspondence to compute mechanically: opening_
conditions groups two codes (card_declined, payment_failed) into one
'ambiguous_decline' entry that matches failure_mix.conditions'
'card_declined_or_payment_failed' key by VALUE, not by name, and groups three
codes into 'card_not_enabled_group' that matches only the single
'card_not_enrolled' entry in failure_mix.conditions (the other two grouped
codes - card_disabled_for_online_payments, debit_instrument_inactive - do not
appear in failure_mix.conditions at all). The mapping is therefore declared
explicitly in rrx.sim.cohort, from human inspection of population.yaml, not
derived.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rrx.sim.cohort import OPENING_CONDITION_TO_FAILURE_MIX_KEY
from rrx.spec.registry import config_dir

REPO_ROOT = config_dir().parent


def _load(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


population = _load(REPO_ROOT / "configs" / "population.yaml")
CONDITIONS = population["failure_mix"]["conditions"]
OPENING_CONDITIONS = population["opening_conditions"]


def test_mapping_is_a_bijection_onto_failure_mix_conditions():
    """Every failure_mix.conditions key is claimed by exactly one
    opening_conditions entry, and vice versa - no orphan on either side."""
    opening_keys = {c["key"] for c in OPENING_CONDITIONS}
    assert opening_keys == set(OPENING_CONDITION_TO_FAILURE_MIX_KEY)
    assert set(OPENING_CONDITION_TO_FAILURE_MIX_KEY.values()) == set(CONDITIONS)


@pytest.mark.parametrize("condition", OPENING_CONDITIONS, ids=lambda c: c["key"])
def test_opening_condition_weight_matches_authoritative_failure_mix(condition):
    fm_key = OPENING_CONDITION_TO_FAILURE_MIX_KEY[condition["key"]]
    assert condition["weight"] == pytest.approx(CONDITIONS[fm_key], abs=1e-9), (
        f"{condition['key']} (weight={condition['weight']}) disagrees with "
        f"the authoritative failure_mix.conditions[{fm_key!r}]="
        f"{CONDITIONS[fm_key]}. population.yaml#/opening_conditions[*]/weight "
        "is supposed to be derived from population.yaml#/failure_mix/"
        "conditions; this is a discovered validity defect, not something to "
        "silently patch."
    )
