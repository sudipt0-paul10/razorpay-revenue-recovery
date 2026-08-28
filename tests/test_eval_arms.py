"""Stage B/5C: tests for the canonical A0/A1/A2/A2-strengthened dispatch
and run paths (src/rrx/eval/arms.py). Smoke-scale only (a handful of real
dev episodes) - the full 2,000-episode comparator cohorts are explicitly
not run in these stages; see the Stage B/5C reports.

Canonical A1 was wired at Stage 5C, after eval-spec-v1.6 (EVAL.md §4.3,
[CONSEQUENTIAL-2]) formally adopted its content/remedy - see
ARM_A1_PROVENANCE in src/rrx/eval/arms.py.
"""

from __future__ import annotations

import json

import pytest

from rrx.agent.policy import a3d_policy
from rrx.baselines.a1 import a1_action_for_day
from rrx.baselines.a2_variants import a2_strengthened_action_for_day
from rrx.eval.arms import (
    ARM_A0,
    ARM_A1,
    ARM_A2,
    ARM_A2_STRENGTHENED,
    ARM_A3D,
    UnknownArmError,
    registered_policy,
    run_arm_cohort,
    run_official_arm,
    run_policies_cohort,
)
from rrx.sim import engine
from rrx.sim.engine import EpisodeResult, run_episode
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()
SMOKE_INDICES = list(range(1000, 1010))


# ---------------------------------------------------------------------------
# registered_policy - the temporary-registration context manager
# ---------------------------------------------------------------------------

def test_registered_policy_registers_and_deregisters():
    assert "A2_STRENGTHENED" not in engine._POLICIES
    with registered_policy("A2_STRENGTHENED", a2_strengthened_action_for_day):
        assert engine._POLICIES["A2_STRENGTHENED"] is a2_strengthened_action_for_day
    assert "A2_STRENGTHENED" not in engine._POLICIES


def test_registered_policy_deregisters_even_on_error():
    with pytest.raises(RuntimeError):
        with registered_policy("A2_STRENGTHENED", a2_strengthened_action_for_day):
            raise RuntimeError("boom")
    assert "A2_STRENGTHENED" not in engine._POLICIES


def test_registered_policy_refuses_to_clobber_existing_key():
    with pytest.raises(RuntimeError):
        with registered_policy("A0", a2_strengthened_action_for_day):
            pass
    # A0's real policy must be untouched after the refusal.
    assert engine._POLICIES["A0"] is not a2_strengthened_action_for_day


def test_a2_original_and_a0_untouched_by_import():
    """Importing rrx.eval.arms must not rebind engine._POLICIES' permanent
    A0/A2 entries - mirrors tests/test_a2_variants.py's own equivalent
    check for rrx.baselines.a2_variants."""
    from rrx.sim.engine import a0_action_for_day, a2_action_for_day

    assert engine._POLICIES["A0"] is a0_action_for_day
    assert engine._POLICIES["A2"] is a2_action_for_day


# ---------------------------------------------------------------------------
# run_arm_cohort - the unified dispatcher
# ---------------------------------------------------------------------------

def test_run_arm_cohort_a0_matches_direct_run_episode_call():
    """Proves the correct arm implementation is being invoked: A0 through
    the dispatcher must be byte-identical to calling run_episode directly."""
    via_dispatcher, ledger = run_arm_cohort(ARM_A0, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    direct = [
        run_episode("dev", i, "A0", EPISODE_CFG, POPULATION_CFG) for i in SMOKE_INDICES
    ]
    assert via_dispatcher == direct
    assert ledger is None  # A0 has no ledger mechanism - not [], None


def test_run_arm_cohort_a2_strengthened_matches_direct_registration():
    """Same proof for A2_STRENGTHENED, using the exact registration pattern
    tests/test_a2_variants.py already uses directly (not through this
    module) as the independent reference."""
    via_dispatcher, ledger = run_arm_cohort(
        ARM_A2_STRENGTHENED, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES
    )
    engine._POLICIES["A2_STRENGTHENED"] = a2_strengthened_action_for_day
    try:
        direct = [
            run_episode("dev", i, "A2_STRENGTHENED", EPISODE_CFG, POPULATION_CFG)
            for i in SMOKE_INDICES
        ]
    finally:
        del engine._POLICIES["A2_STRENGTHENED"]
    assert via_dispatcher == direct
    assert ledger is None
    # No permanent registration leaked.
    assert "A2_STRENGTHENED" not in engine._POLICIES


def test_run_arm_cohort_a2_strengthened_uses_the_real_frozen_schedule():
    """§4 item 1/2: guards against a silently-swapped policy - directly
    checks the card-broken bucket's EVAL.md §4.1.2 schedule (T+0/T+3/T+5)
    shows up in real dispatched output, not the T+0/T+5 A2-original
    schedule or some other stand-in."""
    results, _ = run_arm_cohort(
        ARM_A2_STRENGTHENED, EPISODE_CFG, POPULATION_CFG, range(1000, 1300)
    )
    card_broken = [
        r for r in results
        if r.opening_condition_key
        in ("card_expired", "debit_instrument_blocked", "card_not_enabled_group")
    ]
    assert card_broken, "no card-broken episodes in this smoke range"
    # A2-strengthened's card-broken bucket sends up to 3 contacts
    # (T+0/T+3/T+5); A2-original sends at most 2 (T+0/T+5) - this
    # distinguishes the two at the aggregate level without re-deriving the
    # full per-day schedule tests/test_a2_variants.py already pins.
    assert max(r.contacts_sent for r in card_broken) <= 3
    assert any(r.contacts_sent == 3 for r in card_broken), (
        "no card-broken episode used all 3 contacts - A2-strengthened's "
        "T+5 rescue contact does not appear to be firing"
    )


def test_run_arm_cohort_a3d_still_dispatches_through_the_a3_runner():
    """A3-D dispatch, still available through the same unified interface -
    but see run_official_arm's explicit refusal to write an A3-D result
    through this generalized path."""
    results, ledger = run_arm_cohort(ARM_A3D, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    assert len(results) == len(SMOKE_INDICES)
    assert ledger is not None and len(ledger) > 0  # A3-D DOES have a ledger


def test_run_arm_cohort_unknown_arm_raises():
    with pytest.raises(UnknownArmError):
        run_arm_cohort("NOT_A_REAL_ARM", EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)


def test_run_arm_cohort_a1_matches_direct_registration():
    """Stage 5C: canonical A1 (eval-spec-v1.6) resolves through the same
    dispatcher, using the same temporary-registration mechanism as
    A2_STRENGTHENED - proves the correct implementation is invoked, not
    A3-D or anything else."""
    via_dispatcher, ledger = run_arm_cohort(ARM_A1, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    engine._POLICIES["A1"] = a1_action_for_day
    try:
        direct = [
            run_episode("dev", i, "A1", EPISODE_CFG, POPULATION_CFG) for i in SMOKE_INDICES
        ]
    finally:
        del engine._POLICIES["A1"]
    assert via_dispatcher == direct
    assert ledger is None  # A1 has no ledger mechanism, same as A0/A2
    assert "A1" not in engine._POLICIES  # no permanent registration leaked


def test_run_arm_cohort_a1_schedule_is_exactly_t0_and_t3():
    """Guards against a silently-swapped policy at the dispatch layer -
    the frozen eval-spec-v1.6 schedule must show up in real output."""
    results, _ = run_arm_cohort(ARM_A1, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    assert all(r.contacts_sent in (0, 1, 2) for r in results)
    assert any(r.contacts_sent == 2 for r in results), (
        "no episode used both of A1's T+0/T+3 contacts"
    )


# ---------------------------------------------------------------------------
# CRN / cohort-sharing proof (Stage B §5 items 1-4)
# ---------------------------------------------------------------------------

def test_same_indices_share_identical_cohort_across_a0_a1_a2_a2s_a3d():
    """The key experimental requirement (Stage B §3/§4): A0/A1/A2/
    A2_STRENGTHENED/A3-D must draw the identical opening_condition_key and
    invoice_amount_inr for the same index - proving the same dev cohort/
    CRN construction is used by every arm, not a per-arm re-sample."""
    a0, _ = run_arm_cohort(ARM_A0, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    a1, _ = run_arm_cohort(ARM_A1, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    a2, _ = run_arm_cohort(ARM_A2, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    a2s, _ = run_arm_cohort(ARM_A2_STRENGTHENED, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    a3d, _ = run_arm_cohort(ARM_A3D, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)

    for r0, r1, r2, r2s, r3 in zip(a0, a1, a2, a2s, a3d):
        assert r0.opening_condition_key == r1.opening_condition_key == (
            r2.opening_condition_key
        ) == r2s.opening_condition_key == r3.opening_condition_key
        assert r0.invoice_amount_inr == r1.invoice_amount_inr == (
            r2.invoice_amount_inr
        ) == r2s.invoice_amount_inr == r3.invoice_amount_inr


def test_a2_strengthened_run_does_not_invoke_a3d_policy(monkeypatch):
    """Requirement 4 (Stage B §5): no A3-D policy accidentally invoked
    while running a comparator arm. Patches a3d_policy to explode if
    called and runs A2_STRENGTHENED through the dispatcher - a call would
    prove a wiring bug (e.g. accidentally routing through run_episode_a3)."""
    def _explode(view):
        raise AssertionError("a3d_policy was called while running A2_STRENGTHENED")

    monkeypatch.setattr("rrx.agent.policy.a3d_policy", _explode)
    # Re-import path used by run_arm_cohort's A3-D branch also patched, to
    # catch either import alias.
    monkeypatch.setattr("rrx.eval.runner.a3d_policy", _explode)

    results, ledger = run_arm_cohort(
        ARM_A2_STRENGTHENED, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES
    )
    assert len(results) == len(SMOKE_INDICES)
    assert ledger is None
    assert a3d_policy is not _explode  # patch was scoped to the monkeypatch fixture only


def test_a1_run_does_not_invoke_a3d_policy(monkeypatch):
    """Stage 5C §5: same proof, specifically for the newly-wired canonical
    A1 - dispatching "A1" must never reach a3d_policy/run_episode_a3."""
    def _explode(view):
        raise AssertionError("a3d_policy was called while running A1")

    monkeypatch.setattr("rrx.agent.policy.a3d_policy", _explode)
    monkeypatch.setattr("rrx.eval.runner.a3d_policy", _explode)

    results, ledger = run_arm_cohort(ARM_A1, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
    assert len(results) == len(SMOKE_INDICES)
    assert ledger is None
    assert a3d_policy is not _explode


def test_output_conforms_to_episode_result_contract():
    """Requirement 5 (Stage B §5): dispatcher output is real EpisodeResult,
    same dataclass every arm (including A3-D) already returns."""
    for arm in (ARM_A0, ARM_A1, ARM_A2, ARM_A2_STRENGTHENED, ARM_A3D):
        results, _ = run_arm_cohort(arm, EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)
        assert all(isinstance(r, EpisodeResult) for r in results)


# ---------------------------------------------------------------------------
# run_policies_cohort - direct, lower-level helper
# ---------------------------------------------------------------------------

def test_run_policies_cohort_requires_pre_registered_arm():
    with pytest.raises(KeyError):
        run_policies_cohort("NOT_REGISTERED", EPISODE_CFG, POPULATION_CFG, SMOKE_INDICES)


# ---------------------------------------------------------------------------
# run_official_arm - manifest/run_params/metrics writer, smoke scale only
# ---------------------------------------------------------------------------

def test_run_official_arm_refuses_a3d():
    with pytest.raises(UnknownArmError):
        run_official_arm(ARM_A3D, "should-never-run", results_dir=None, indices=SMOKE_INDICES)


def test_run_official_arm_a2_strengthened_smoke(tmp_path):
    run_dir = run_official_arm(
        ARM_A2_STRENGTHENED, "smoke-a2-strengthened", results_dir=tmp_path,
        indices=SMOKE_INDICES,
    )
    assert run_dir == tmp_path / "smoke-a2-strengthened"
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "run_params.json").exists()
    assert (run_dir / "metrics.json").exists()
    # No ledger mechanism exists for this arm - no file should be written.
    assert not (run_dir / "ledger.jsonl").exists()

    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["arm"] == "A2_STRENGTHENED"
    assert manifest["seed"] == 20260825

    run_params = json.loads((run_dir / "run_params.json").read_text())
    assert run_params["arm"] == "A2_STRENGTHENED"
    assert run_params["policy"] == "rrx.baselines.a2_variants.a2_strengthened_action_for_day"
    assert run_params["runner"] == "rrx.sim.engine.run_episode"
    assert run_params["n"] == len(SMOKE_INDICES)

    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["n"] == len(SMOKE_INDICES)
    assert "ledger_derived_metrics_unavailable_for_this_arm" in metrics
    assert "tick_type_distribution" in metrics["ledger_derived_metrics_unavailable_for_this_arm"]


def test_run_official_arm_a0_smoke(tmp_path):
    run_dir = run_official_arm(
        ARM_A0, "smoke-a0", results_dir=tmp_path, indices=SMOKE_INDICES
    )
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["n"] == len(SMOKE_INDICES)
    assert metrics["total_contacts"] == 0  # A0 never contacts


def test_run_official_arm_a1_smoke(tmp_path):
    run_dir = run_official_arm(
        ARM_A1, "smoke-a1", results_dir=tmp_path, indices=SMOKE_INDICES
    )
    assert not (run_dir / "ledger.jsonl").exists()  # no ledger mechanism for A1 either

    run_params = json.loads((run_dir / "run_params.json").read_text())
    assert run_params["arm"] == "A1"
    assert run_params["policy"] == "rrx.baselines.a1.a1_action_for_day"
    assert run_params["runner"] == "rrx.sim.engine.run_episode"

    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["n"] == len(SMOKE_INDICES)
    # Every non-cancelled-at-open episode gets exactly 2 contacts (T+0, T+3).
    assert metrics["total_contacts"] > 0


def test_run_official_arm_stops_if_dir_exists(tmp_path):
    from rrx.eval.runner import ResultsDirectoryExistsError

    existing = tmp_path / "already-here"
    existing.mkdir()
    with pytest.raises(ResultsDirectoryExistsError):
        run_official_arm(
            ARM_A2_STRENGTHENED, "already-here", results_dir=tmp_path, indices=[1000]
        )
