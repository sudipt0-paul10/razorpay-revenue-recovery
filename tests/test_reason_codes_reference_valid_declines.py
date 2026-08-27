"""Every decline_code referenced in src/rrx/agent/reason_codes.py's
admissible-decline_code mapping (docs/A3-DESIGN.md §7) must resolve,
through configs/population.yaml's opening_conditions, to code(s) that
exist in data/decline_codes.yaml with verified: true.

Reads data/decline_codes.yaml and configs/population.yaml; never writes
either - both are locked (CLAUDE.md §3).

Follows the same resolution pattern as the existing
tests/test_population_matches_decline_codes.py: a population.yaml
opening_condition of kind `decline_code` maps to exactly one
data/decline_codes.yaml `code:` entry (its own `code` field); one of kind
`decline_code_group` maps to several (its `codes` list) - EVAL.md 3.2
lists near-duplicate/ambiguous codes as one row each, but decline_codes.yaml
records them as distinct, un-collapsed entries.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rrx.agent.reason_codes import ADMISSIBLE_DECLINE_CODES, ALL_DECLINE_CODES
from rrx.spec.registry import config_dir

REPO_ROOT = config_dir().parent


def _load(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


POPULATION = _load(REPO_ROOT / "configs" / "population.yaml")
DECLINE = _load(REPO_ROOT / "data" / "decline_codes.yaml")

CONDITIONS_BY_KEY = {c["key"]: c for c in POPULATION["opening_conditions"]}
CODES_BY_NAME = {c["code"]: c for c in DECLINE["codes"]}

# Every decline_code string appearing anywhere in reason_codes.py's
# admissible mapping.
REFERENCED_KEYS = frozenset(
    key for keys in ADMISSIBLE_DECLINE_CODES.values() for key in keys
)


def _resolve_to_decline_codes_yaml_codes(opening_condition_key: str) -> list[str]:
    condition = CONDITIONS_BY_KEY[opening_condition_key]
    if condition["kind"] == "decline_code_group":
        return condition["codes"]
    assert condition["kind"] == "decline_code", (
        f"{opening_condition_key} is kind={condition['kind']!r}, not a decline_code "
        "- reason_codes.py's ALL_DECLINE_CODES must not reference non-decline-code "
        "opening conditions (e.g. subscription_cancelled_by_customer)"
    )
    return [condition["code"]]


def test_admissible_mapping_only_references_all_decline_codes():
    """Every key used across ADMISSIBLE_DECLINE_CODES's value sets must be
    a member of ALL_DECLINE_CODES - no reason_code may admit a decline_code
    outside the known set (e.g. a typo, or subscription_cancelled_by_customer
    smuggled in as a positive member instead of an exclusion)."""
    unknown = REFERENCED_KEYS - ALL_DECLINE_CODES
    assert not unknown, f"reason_codes.py references unknown decline_code(s): {unknown}"


@pytest.mark.parametrize(
    "opening_condition_key", sorted(ALL_DECLINE_CODES), ids=lambda k: k
)
def test_every_referenced_decline_code_exists_in_population_yaml(opening_condition_key):
    assert opening_condition_key in CONDITIONS_BY_KEY, (
        f"{opening_condition_key} is not an opening_condition key in configs/population.yaml"
    )


@pytest.mark.parametrize(
    "opening_condition_key", sorted(ALL_DECLINE_CODES), ids=lambda k: k
)
def test_every_referenced_decline_code_resolves_to_a_known_taxonomy_code(opening_condition_key):
    resolved = _resolve_to_decline_codes_yaml_codes(opening_condition_key)
    missing = [code for code in resolved if code not in CODES_BY_NAME]
    assert not missing, (
        f"{opening_condition_key} resolves to {missing}, not in data/decline_codes.yaml codes"
    )


@pytest.mark.parametrize(
    "opening_condition_key", sorted(ALL_DECLINE_CODES), ids=lambda k: k
)
def test_every_referenced_decline_code_is_verified(opening_condition_key):
    resolved = _resolve_to_decline_codes_yaml_codes(opening_condition_key)
    unverified = [code for code in resolved if not CODES_BY_NAME[code]["verified"]]
    assert not unverified, (
        f"{opening_condition_key} resolves to {unverified}, not verified: true "
        "in data/decline_codes.yaml"
    )
