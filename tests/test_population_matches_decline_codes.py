"""Population failure-mix vs. the decline-code taxonomy.

EVAL.md §3.2: every failure-mix entry must exist in data/decline_codes.yaml,
be verified: true, be in_v1_cohort: true, be absent from every `unverified`
list, and the weights must sum to 1.0.

`in_v1_cohort` is the v4 schema's replacement for the v3
`context: unattended_capable` field (see EVAL.md §3.2's note) - checked
here, not the retired field.

configs/population.yaml has one entry, `subscription_cancelled_by_customer`,
that is a `subscription_state` rather than a `decline_code`: it opens on the
Subscription already being `cancelled`, not on a card decline. It has no
`in_v1_cohort`/`verified` fields to check because it isn't a code; it is
checked against `subscriptions.states` instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rrx.spec.registry import config_dir

REPO_ROOT = config_dir().parent


def _load(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


population = _load(REPO_ROOT / "configs" / "population.yaml")
decline = _load(REPO_ROOT / "data" / "decline_codes.yaml")

OPENING_CONDITIONS = population["opening_conditions"]
CODES_BY_NAME = {c["code"]: c for c in decline["codes"]}
UNVERIFIED_CODES = set(decline["unverified"]["codes"])

DECLINE_CODE_CONDITIONS = [
    c for c in OPENING_CONDITIONS if c["kind"] in ("decline_code", "decline_code_group")
]
SUBSCRIPTION_STATE_CONDITIONS = [
    c for c in OPENING_CONDITIONS if c["kind"] == "subscription_state"
]


def _codes_of(condition: dict) -> list[str]:
    return condition["codes"] if condition["kind"] == "decline_code_group" else [condition["code"]]


@pytest.mark.parametrize("condition", DECLINE_CODE_CONDITIONS, ids=lambda c: c["key"])
def test_every_decline_code_exists_in_taxonomy(condition):
    missing = [code for code in _codes_of(condition) if code not in CODES_BY_NAME]
    assert not missing, f"{condition['key']}: {missing} not in data/decline_codes.yaml codes"


@pytest.mark.parametrize("condition", DECLINE_CODE_CONDITIONS, ids=lambda c: c["key"])
def test_every_decline_code_is_verified(condition):
    unverified = [code for code in _codes_of(condition) if not CODES_BY_NAME[code]["verified"]]
    assert not unverified, f"{condition['key']}: {unverified} not verified: true"


@pytest.mark.parametrize("condition", DECLINE_CODE_CONDITIONS, ids=lambda c: c["key"])
def test_every_decline_code_is_in_v1_cohort(condition):
    excluded = [code for code in _codes_of(condition) if not CODES_BY_NAME[code]["in_v1_cohort"]]
    assert not excluded, f"{condition['key']}: {excluded} not in_v1_cohort: true"


@pytest.mark.parametrize("condition", DECLINE_CODE_CONDITIONS, ids=lambda c: c["key"])
def test_no_decline_code_is_in_the_unverified_list(condition):
    leaked = [code for code in _codes_of(condition) if code in UNVERIFIED_CODES]
    assert not leaked, f"{condition['key']}: {leaked} present in unverified.codes"


@pytest.mark.parametrize("condition", SUBSCRIPTION_STATE_CONDITIONS, ids=lambda c: c["key"])
def test_every_subscription_state_condition_is_a_documented_state(condition):
    assert condition["state"] in decline["subscriptions"]["states"]["values"]
    assert condition["state"] in decline["subscriptions"]["states"], (
        f"{condition['key']}: subscriptions.states has no detail block for "
        f"{condition['state']!r}"
    )


def test_failure_mix_weights_sum_to_one():
    total = sum(c["weight"] for c in OPENING_CONDITIONS)
    assert total == pytest.approx(1.0, abs=1e-9)
