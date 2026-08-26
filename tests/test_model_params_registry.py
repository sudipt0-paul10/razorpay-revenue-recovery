"""Registry completeness.

This is the test EVAL.md §0 actually describes: it fails the build if a
[MODEL] parameter is MISSING. A flag-scanner cannot do this, because
scanning finds only what is present. Absence is detectable only against a
declared canonical list.

Split out from the old test_model_params_swept.py, which conflated two
different lifecycle questions (does the parameter exist? is it ready to
run holdout?). Nothing was weakened: both halves are now strictly
enforced, at the right time.
"""

import pytest

from rrx.spec.registry import (
    CANONICAL_MODEL_PARAMS,
    REQUIRED_FIELDS,
    VALID_STATUS,
    load_registry,
    resolve_owner_path,
)

reg = load_registry()


def test_exactly_six_parameters():
    assert len(reg.parameters) == 6, (
        f"EVAL.md §8.2 declares six [MODEL] parameters; registry has "
        f"{len(reg.parameters)}: {sorted(reg.parameters)}"
    )


def test_ids_match_eval_section_8_2_verbatim():
    assert set(reg.parameters) == set(CANONICAL_MODEL_PARAMS)


@pytest.mark.parametrize("name", CANONICAL_MODEL_PARAMS)
def test_required_fields_present(name):
    p = reg.parameters[name]
    missing = [f for f in REQUIRED_FIELDS if f not in p]
    assert not missing, f"{name} missing {missing}"
    assert p["status"] in VALID_STATUS


@pytest.mark.parametrize("name", CANONICAL_MODEL_PARAMS)
def test_owner_path_resolves(name):
    """Stops the registry silently drifting from the configs."""
    resolve_owner_path(reg.parameters[name]["owner_path"])


@pytest.mark.parametrize("name", CANONICAL_MODEL_PARAMS)
def test_provenance_declared_invented(name):
    """Every [MODEL] parameter is a synthetic design choice, never an
    observed Razorpay statistic. EVAL.md §8 threat 6 depends on this."""
    assert reg.parameters[name]["provenance"] == "invented_synthetic"


def test_lifetime_cycles_is_not_a_seventh_parameter():
    """Locked decision 7."""
    assert "remaining_subscription_lifetime_cycles" not in reg.parameters
    comp = reg.parameters["cancellation_hazard_and_ltv"]["handle"]["applies_to"]
    assert "remaining_lifetime_mean_cycles" in comp


def test_hazard_is_a_world_mechanic():
    """Locked decision 8. If hazard were Regime-A-only pricing, Regime B
    would be blind to the cost of over-contacting and the restraint
    thesis would have no headline-regime justification."""
    p = reg.parameters["cancellation_hazard_and_ltv"]
    assert p["regime_split"]["hazard"] == "world_mechanic"
    assert "B" in p["regime"]
    assert p["regime_split"]["ltv"] == "regime_a_pricing_only"


def test_razorpay_auto_email_carries_no_hazard():
    """EVAL.md §1.2: the automatic email is part of the world, not a
    contact. So A0's cancellation hazard is exactly zero and A0 stays a
    clean floor."""
    d = reg.parameters["cancellation_hazard_and_ltv"]["definition"]
    assert d["hazard_per_contact"]["applies_to_razorpay_auto_email"] is False


def test_card_change_completion_has_no_visible_correlate():
    """EVAL.md §3.4 pre-registers exactly three sources of A3 advantage.
    Coupling completion to a visible signal would create an unattributable
    fourth."""
    d = reg.parameters["card_change_completion_propensity"]["definition"]
    assert d["independent_of_visible_signals"] is True


def test_sweep_runs_on_dev_only():
    """Locked decision 1. EVAL.md §3.5 allows ONE holdout use per
    candidate release; a 22-cell sweep on holdout would be 22 uses."""
    assert reg.sweep["split"] == "dev"


def test_policies_frozen_across_cells():
    """Locked decision 14. Per-cell retuning of A3 would invalidate the
    entire sensitivity analysis."""
    # eval-spec-v1.4: "A3" split into its two pre-registered named arms
    # (EVAL.md §4.2) -- propagated, not relaxed: pins three names now.
    assert set(reg.sweep["frozen_policies"]) == {"A2", "A3-D", "A3-LLM"}


def test_crn_uses_per_variable_substreams():
    """Locked decision 14 + defect fix: shared streams would let a change
    to one parameter reshuffle unrelated draws, so the cell would no
    longer be a one-at-a-time comparison."""
    crn = reg.sweep["common_random_numbers"]
    assert crn["enabled"] is True
    assert crn["substream_isolation"] == "per_variable"


def test_win_criterion_requires_both_metrics():
    """Locked decision 4."""
    w = reg.sweep["win_criterion"]
    assert w["require"] == "all"
    assert set(w["metrics"]) == {"invoice_recovery_rate",
                                 "subscription_rescue_rate"}
    assert w["comparator"] == "A2"
