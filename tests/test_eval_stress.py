"""Stage 7.3: focused tests for the stress-split wiring, run BEFORE the
actual 300-episode stress execution (`python -m rrx.eval.stress`).

Smoke-scale only (a handful of real stress-seed episodes via tmp_path) -
mirrors tests/test_eval_arms.py's own convention for run_official_arm.
Three things are checked that did not exist, or were silently wrong,
before Stage 7.3:

1. `split` is genuinely threaded into the CRN seed (not hardcoded "dev")
   for every dispatch path this stage generalized.
2. `run_official_arm` now permits A3-D and A4 for the `stress` split
   (previously A3-D was refused unconditionally; A4 was not wired at all).
3. `audit_coverage_check`'s episode_id lookup matches the ledger's actual
   `f"{split}-{i}"` stamp for a non-dev split.
"""

from __future__ import annotations

import json

import pytest

from rrx.agent.ledger import default_ledger_record
from rrx.agent.policy import a3d_policy
from rrx.baselines.a4 import run_a4_episode
from rrx.eval.arms import (
    ARM_A0,
    ARM_A1,
    ARM_A2_STRENGTHENED,
    ARM_A3D,
    ARM_A4,
    UnknownArmError,
    run_arm_cohort,
    run_official_arm,
)
from rrx.eval.runner import audit_coverage_check, run_a3d_dev_cohort
from rrx.eval.stress import STRESS_ARMS, _arm_violations, _run_id_for
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import STRESS_N, STRESS_SEED_START, STRESS_SPLIT, stress_indices
from rrx.sim.engine import run_episode
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()
STRESS_SMOKE_INDICES = list(range(STRESS_SEED_START, STRESS_SEED_START + 10))


# ---------------------------------------------------------------------------
# frozen definition sanity - EVAL.md §3.5's seeds/N, not invented here
# ---------------------------------------------------------------------------


def test_stress_indices_matches_the_frozen_5000_5299_definition():
    indices = list(stress_indices())
    assert indices[0] == 5000
    assert indices[-1] == 5299
    assert len(indices) == 300 == STRESS_N
    assert STRESS_SEED_START == 5000


# ---------------------------------------------------------------------------
# split threading actually changes the CRN world (the bug this stage fixes)
# ---------------------------------------------------------------------------


def test_run_episode_dev_vs_stress_same_index_diverge():
    """Before Stage 7.3, every dispatcher hardcoded split="dev" - so
    running "the stress split" at index 5000 would have silently reused
    whatever rng_for_substream("dev", 5000, ...) draws, not the canonical
    "stress" world. If this test ever finds them equal, CRN independence
    between splits has broken, which would be a real regression."""
    dev_result = run_episode("dev", 5000, ARM_A0, EPISODE_CFG, POPULATION_CFG)
    stress_result = run_episode(STRESS_SPLIT, 5000, ARM_A0, EPISODE_CFG, POPULATION_CFG)
    assert (
        dev_result.opening_condition_key != stress_result.opening_condition_key
        or dev_result.invoice_amount_inr != stress_result.invoice_amount_inr
    ), "dev and stress draws at the same numeric index must not coincide"


def test_run_a3d_dev_cohort_honors_explicit_split():
    dev_results, _ = run_a3d_dev_cohort(
        EPISODE_CFG, POPULATION_CFG, [5000], split="dev",
    )
    stress_results, _ = run_a3d_dev_cohort(
        EPISODE_CFG, POPULATION_CFG, [5000], split=STRESS_SPLIT,
    )
    assert dev_results[0].opening_condition_key != stress_results[0].opening_condition_key or (
        dev_results[0].invoice_amount_inr != stress_results[0].invoice_amount_inr
    )


def test_run_arm_cohort_a3d_stress_matches_direct_run_episode_a3_call():
    via_dispatcher, ledger = run_arm_cohort(
        ARM_A3D, EPISODE_CFG, POPULATION_CFG, STRESS_SMOKE_INDICES, split=STRESS_SPLIT,
    )
    direct = [
        run_episode_a3(STRESS_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG)
        for i in STRESS_SMOKE_INDICES
    ]
    assert via_dispatcher == direct
    assert ledger  # A3-D always produces per-tick ledger records


def test_run_arm_cohort_a4_stress_matches_direct_call():
    via_dispatcher, ledger = run_arm_cohort(
        ARM_A4, EPISODE_CFG, POPULATION_CFG, STRESS_SMOKE_INDICES, split=STRESS_SPLIT,
    )
    direct = [
        run_a4_episode(STRESS_SPLIT, i, EPISODE_CFG, POPULATION_CFG)
        for i in STRESS_SMOKE_INDICES
    ]
    assert via_dispatcher == direct
    assert ledger is None  # A4 has no ledger mechanism


def test_audit_coverage_check_uses_the_given_split_not_dev():
    """Before this stage's fix, this function hardcoded "dev-{i}" - so
    checking a stress run's coverage would have found zero matching
    records for every episode and reported spurious violations."""
    i = 5000
    episode_ledger = []

    def _capturing(**kwargs):
        rec = default_ledger_record(**kwargs)
        episode_ledger.append(rec)
        return rec

    result = run_episode_a3(
        STRESS_SPLIT, i, a3d_policy, EPISODE_CFG, POPULATION_CFG, ledger_record=_capturing,
    )
    window_days = EPISODE_CFG["episode"]["window_days"]

    wrong_split = audit_coverage_check([result], [i], episode_ledger, window_days, split="dev")
    right_split = audit_coverage_check(
        [result], [i], episode_ledger, window_days, split=STRESS_SPLIT
    )
    assert wrong_split["ok"] is False, "sanity: mismatched split must show spurious violations"
    assert right_split["ok"] is True


# ---------------------------------------------------------------------------
# run_official_arm now permits A3-D/A4 for a non-dev split
# ---------------------------------------------------------------------------


def test_run_official_arm_still_refuses_a3d_for_dev_split():
    with pytest.raises(UnknownArmError):
        run_official_arm(ARM_A3D, "should-never-run-dev", indices=[1000, 1001])


def test_run_official_arm_a3d_smoke_for_stress_split(tmp_path):
    run_dir = run_official_arm(
        ARM_A3D, "smoke-a3d-stress", results_dir=tmp_path,
        indices=STRESS_SMOKE_INDICES, split=STRESS_SPLIT,
    )
    metrics = json.loads((run_dir / "metrics.json").read_text())
    run_params = json.loads((run_dir / "run_params.json").read_text())
    assert metrics["n"] == len(STRESS_SMOKE_INDICES)
    assert run_params["split"] == STRESS_SPLIT
    assert (run_dir / "ledger.jsonl").exists()
    assert metrics["audit_coverage"]["ok"] is True


def test_run_official_arm_a4_smoke_for_stress_split(tmp_path):
    run_dir = run_official_arm(
        ARM_A4, "smoke-a4-stress", results_dir=tmp_path,
        indices=STRESS_SMOKE_INDICES, split=STRESS_SPLIT,
    )
    metrics = json.loads((run_dir / "metrics.json").read_text())
    run_params = json.loads((run_dir / "run_params.json").read_text())
    assert metrics["n"] == len(STRESS_SMOKE_INDICES)
    assert run_params["split"] == STRESS_SPLIT
    assert run_params["policy"] == "rrx.baselines.a4.run_a4_episode"
    assert not (run_dir / "ledger.jsonl").exists()  # A4 has no ledger mechanism


def test_run_official_arm_a0_smoke_for_stress_split(tmp_path):
    run_dir = run_official_arm(
        ARM_A0, "smoke-a0-stress", results_dir=tmp_path,
        indices=STRESS_SMOKE_INDICES, split=STRESS_SPLIT,
    )
    run_params = json.loads((run_dir / "run_params.json").read_text())
    assert run_params["split"] == STRESS_SPLIT


# ---------------------------------------------------------------------------
# rrx.eval.stress module-level wiring
# ---------------------------------------------------------------------------


def test_stress_arms_is_exactly_the_five_required_arms():
    assert set(STRESS_ARMS) == {ARM_A0, ARM_A1, ARM_A2_STRENGTHENED, ARM_A3D, ARM_A4}
    assert "A3-LLM" not in STRESS_ARMS
    assert len(STRESS_ARMS) == 5


def test_run_id_for_is_stable_and_arm_specific():
    ids = {_run_id_for(arm) for arm in STRESS_ARMS}
    assert len(ids) == 5  # no collisions


def test_arm_violations_flags_a_nonzero_gate_rejection():
    metrics = {"safety_invariants": {"gate_rejections_total": 2, "max_contacts_sent_observed": 1}}
    violations = _arm_violations("A3-D", metrics, max_contacts=3)
    assert violations == {"gate_rejections_total": 2}


def test_arm_violations_flags_audit_coverage_failure():
    metrics = {
        "safety_invariants": {"max_contacts_sent_observed": 1},
        "audit_coverage": {"ok": False, "violations": [{"episode_id": "stress-5000"}]},
    }
    violations = _arm_violations("A3-D", metrics, max_contacts=3)
    assert "audit_coverage" in violations


def test_arm_violations_a1_card_change_for_insufficient_funds_is_exempt():
    """EVAL.md §4.3: A1 is a deliberately naive, ungated strawman - a
    non-zero card_change_for_insufficient_funds count for A1 specifically
    is expected behavior, not a §5.2 violation. This is the exact
    Stage 7.3 false-positive this correction fixes."""
    metrics = {
        "safety_invariants": {
            "card_change_for_insufficient_funds": 82,
            "max_contacts_sent_observed": 2,
        },
    }
    assert _arm_violations("A1", metrics, max_contacts=3) == {}


def test_arm_violations_card_change_for_insufficient_funds_not_exempt_for_other_arms():
    """The exemption is narrowly scoped to A1 - A2-strengthened/A3-D/A4
    all perform genuine remedy matching by design and must still be
    flagged if this ever comes back non-zero for them."""
    metrics = {
        "safety_invariants": {
            "card_change_for_insufficient_funds": 1,
            "max_contacts_sent_observed": 2,
        },
    }
    for arm in ("A0", "A2_STRENGTHENED", "A3-D", "A4"):
        violations = _arm_violations(arm, metrics, max_contacts=3)
        assert violations == {"card_change_for_insufficient_funds": 1}, arm


def test_arm_violations_flags_budget_cap_exceeded():
    metrics = {"safety_invariants": {"max_contacts_sent_observed": 4}}
    violations = _arm_violations("A0", metrics, max_contacts=3)
    assert violations == {"max_contacts_sent_observed": 4}


def test_arm_violations_clean_run_is_empty():
    metrics = {
        "safety_invariants": {
            "gate_rejections_total": 0,
            "contacts_to_cancelled_or_expired__R2_fired": 0,
            "contacts_after_risk_flagged__R4_fired": 0,
            "card_change_for_insufficient_funds": 0,
            "contacts_exceeding_budget__R5_fired": 0,
            "contacts_outside_quiet_hours__R6_fired": 0,
            "unverified_codes_emitted__R8_fired": 0,
            "max_contacts_sent_observed": 3,
        },
        "audit_coverage": {"ok": True, "violations": []},
    }
    assert _arm_violations("A3-D", metrics, max_contacts=3) == {}


def test_run_stress_suite_refuses_a_drifted_index_range(monkeypatch):
    """Defends against a future edit to splits.py silently changing the
    stress range without this module noticing."""
    import rrx.eval.stress as stress_mod

    monkeypatch.setattr(stress_mod, "STRESS_SEED_START", 9999)
    with pytest.raises(RuntimeError):
        stress_mod.run_stress_suite()
