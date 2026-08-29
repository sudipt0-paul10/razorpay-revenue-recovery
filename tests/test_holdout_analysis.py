"""Tests for src/rrx/eval/holdout_analysis.py - all synthetic data.

No real holdout artifact is read anywhere in this file: every ArmData /
episode_results.jsonl / metrics.json used below is fabricated in tmp_path
or in-memory, at small N, with hand-chosen deterministic outcome patterns
- never rrx.harness.splits.holdout_indices, never a real simulator run
against holdout seeds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rrx.eval.holdout_analysis import (
    ArmData,
    ArtifactError,
    BOOTSTRAP_SEED,
    N_BOOTSTRAP_RESAMPLES,
    analyze_holdout,
    evaluate_criterion_2,
    evaluate_criterion_3_contacts,
    evaluate_target,
    load_arm_data,
    recompute_metrics,
    select_comparator,
    verify_episode_indices,
    verify_recomputed_matches_committed,
)


def _record(i, *, invoice_recovered, subscription_rescued, contacts_sent):
    return {
        "episode_index": i,
        "opening_condition_key": "card_expired",
        "invoice_amount_inr": 2000,
        "invoice_recovered": invoice_recovered,
        "subscription_rescued": subscription_rescued,
        "contacts_sent": contacts_sent,
        "wasted_attempts": 0,
        "card_change_sent_for_insufficient_funds": False,
    }


def _synthetic_records(indices, rate: float, contacts: int = 2):
    """First round(rate*n) episodes (by position) are wins on both primary
    metrics - a simple, fully deterministic pattern, not randomly drawn."""
    indices = list(indices)
    n_wins = round(rate * len(indices))
    return [
        _record(idx, invoice_recovered=(pos < n_wins), subscription_rescued=(pos < n_wins),
                contacts_sent=contacts)
        for pos, idx in enumerate(indices)
    ]


def _write_arm(tmp_path: Path, arm_dirname: str, records: list[dict], metrics: dict | None = None):
    run_dir = tmp_path / arm_dirname
    run_dir.mkdir()
    with open(run_dir / "episode_results.jsonl", "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    if metrics is None:
        metrics = recompute_metrics(records)
    (run_dir / "metrics.json").write_text(json.dumps(metrics))
    return run_dir


def _arm_data(arm: str, run_dir: Path, records: list[dict], metrics: dict | None = None) -> ArmData:
    if metrics is None:
        metrics = recompute_metrics(records)
    return ArmData(arm=arm, run_dir=run_dir, episode_results=tuple(records), metrics=metrics)


# ---------------------------------------------------------------------------
# recompute_metrics
# ---------------------------------------------------------------------------

def test_recompute_metrics_matches_hand_computed():
    records = [
        _record(1, invoice_recovered=True, subscription_rescued=True, contacts_sent=2),
        _record(2, invoice_recovered=False, subscription_rescued=False, contacts_sent=1),
        _record(3, invoice_recovered=True, subscription_rescued=False, contacts_sent=3),
        _record(4, invoice_recovered=False, subscription_rescued=True, contacts_sent=0),
    ]
    metrics = recompute_metrics(records)
    assert metrics["n"] == 4
    assert metrics["invoice_recovery_rate"] == 0.5
    assert metrics["subscription_rescue_rate"] == 0.5
    assert metrics["total_contacts"] == 6
    assert metrics["contacts_per_invoice_recovered"] == 3.0  # 6 / 2
    assert metrics["contacts_per_subscription_rescued"] == 3.0  # 6 / 2


def test_recompute_metrics_handles_zero_wins():
    records = [_record(1, invoice_recovered=False, subscription_rescued=False, contacts_sent=0)]
    metrics = recompute_metrics(records)
    assert metrics["contacts_per_invoice_recovered"] is None
    assert metrics["contacts_per_subscription_rescued"] is None


# ---------------------------------------------------------------------------
# verify_episode_indices - missing / duplicate / extra detection
# ---------------------------------------------------------------------------

def test_verify_episode_indices_passes_when_exact():
    records = [_record(i, invoice_recovered=True, subscription_rescued=True, contacts_sent=1)
               for i in range(9000, 9010)]
    verify_episode_indices(records, range(9000, 9010), "A0")  # must not raise


def test_verify_episode_indices_detects_missing():
    records = [_record(i, invoice_recovered=True, subscription_rescued=True, contacts_sent=1)
               for i in range(9000, 9009)]  # one short
    with pytest.raises(ArtifactError, match="missing episode indices"):
        verify_episode_indices(records, range(9000, 9010), "A0")


def test_verify_episode_indices_detects_duplicates():
    records = [_record(i, invoice_recovered=True, subscription_rescued=True, contacts_sent=1)
               for i in range(9000, 9009)]
    records.append(
        _record(9000, invoice_recovered=True, subscription_rescued=True, contacts_sent=1)
    )
    with pytest.raises(ArtifactError, match="duplicate episode_index"):
        verify_episode_indices(records, range(9000, 9009), "A0")


def test_verify_episode_indices_detects_extra():
    records = [_record(i, invoice_recovered=True, subscription_rescued=True, contacts_sent=1)
               for i in range(9000, 9011)]  # one beyond the declared range
    with pytest.raises(ArtifactError, match="unexpected episode indices"):
        verify_episode_indices(records, range(9000, 9010), "A0")


# ---------------------------------------------------------------------------
# verify_recomputed_matches_committed - aggregate mismatch detection
# ---------------------------------------------------------------------------

def test_verify_recomputed_matches_committed_passes_when_equal():
    recomputed = {"n": 2, "invoice_recovery_rate": 0.5}
    verify_recomputed_matches_committed(recomputed, dict(recomputed), "A0")  # must not raise


def test_verify_recomputed_matches_committed_detects_mismatch():
    recomputed = {"n": 2, "invoice_recovery_rate": 0.5}
    committed = {"n": 2, "invoice_recovery_rate": 0.75}  # tampered/stale aggregate
    with pytest.raises(ArtifactError, match="disagree with committed"):
        verify_recomputed_matches_committed(recomputed, committed, "A0")


# ---------------------------------------------------------------------------
# load_arm_data - missing / malformed artifact detection (fail loud)
# ---------------------------------------------------------------------------

def test_load_arm_data_raises_on_missing_episode_results_file(tmp_path):
    run_dir = tmp_path / "a0"
    run_dir.mkdir()
    (run_dir / "metrics.json").write_text("{}")
    with pytest.raises(ArtifactError, match="missing required artifact"):
        load_arm_data("A0", run_dir, range(9000, 9010))


def test_load_arm_data_raises_on_missing_metrics_file(tmp_path):
    run_dir = tmp_path / "a0"
    run_dir.mkdir()
    records = _synthetic_records(range(9000, 9010), rate=0.5)
    with open(run_dir / "episode_results.jsonl", "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    with pytest.raises(ArtifactError, match="missing required artifact"):
        load_arm_data("A0", run_dir, range(9000, 9010))


def test_load_arm_data_raises_on_malformed_json_line(tmp_path):
    run_dir = tmp_path / "a0"
    run_dir.mkdir()
    (run_dir / "episode_results.jsonl").write_text('{"episode_index": 9000, not json}\n')
    (run_dir / "metrics.json").write_text("{}")
    with pytest.raises(ArtifactError, match="malformed JSON"):
        load_arm_data("A0", run_dir, range(9000, 9001))


def test_load_arm_data_raises_when_aggregate_disagrees(tmp_path):
    records = _synthetic_records(range(9000, 9010), rate=0.5)
    run_dir = _write_arm(tmp_path, "a0", records, metrics={"n": 999})  # deliberately wrong
    with pytest.raises(ArtifactError, match="disagree with committed"):
        load_arm_data("A0", run_dir, range(9000, 9010))


def test_load_arm_data_succeeds_on_consistent_artifacts(tmp_path):
    records = _synthetic_records(range(9000, 9010), rate=0.5)
    run_dir = _write_arm(tmp_path, "a0", records)
    arm_data = load_arm_data("A0", run_dir, range(9000, 9010))
    assert arm_data.arm == "A0"
    assert arm_data.metrics["n"] == 10


# ---------------------------------------------------------------------------
# compare() - bootstrap invocation parameters
# ---------------------------------------------------------------------------

def test_compare_invokes_paired_bootstrap_ci_with_frozen_parameters(monkeypatch):
    captured = {}

    def fake_paired_bootstrap_ci(a, b, n_resamples, seed):
        captured["n_resamples"] = n_resamples
        captured["seed"] = seed
        captured["len_a"] = len(a)
        captured["len_b"] = len(b)
        return (0.05, 0.01, 0.09)

    import rrx.eval.holdout_analysis as mod
    monkeypatch.setattr(mod, "paired_bootstrap_ci", fake_paired_bootstrap_ci)

    records_a = _synthetic_records(range(9000, 9010), rate=0.3)
    records_b = _synthetic_records(range(9000, 9010), rate=0.5)
    arm_a = _arm_data("A0", Path("."), records_a)
    arm_b = _arm_data("A1", Path("."), records_b)

    result = mod.compare(arm_a, arm_b, "invoice_recovery_rate")

    assert captured["n_resamples"] == N_BOOTSTRAP_RESAMPLES == 10_000
    assert captured["seed"] == BOOTSTRAP_SEED == 20260826
    assert captured["len_a"] == captured["len_b"] == 10
    assert result.diff == 0.05 and result.lo == 0.01 and result.hi == 0.09
    assert result.excludes_zero is True


# ---------------------------------------------------------------------------
# select_comparator - no-tie and tie scenarios (real bootstrap, synthetic data)
# ---------------------------------------------------------------------------

_BOUNDED_INDICES = list(range(9000, 9300))  # N=300, real bootstrap runs fast at this size


def test_select_comparator_no_tie_picks_clear_leader():
    bounded = {
        "A0": _arm_data("A0", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.20)),
        "A1": _arm_data("A1", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.40)),
        "A2-strengthened": _arm_data(
            "A2-strengthened", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.42)
        ),
    }
    result = select_comparator(bounded, "invoice_recovery_rate")
    assert result.leader == "A2-strengthened"
    # A1 (0.40) vs A2-strengthened (0.42) over N=300 with this pattern is a
    # real, large, non-overlapping separation - not tied.
    assert result.tied_set == ("A2-strengthened",)


def test_select_comparator_detects_a_real_tie():
    # A1 and A2-strengthened have IDENTICAL outcome patterns -> the paired
    # bootstrap difference is exactly zero every resample -> CI is a point
    # at zero -> unambiguously "includes zero".
    shared_records = _synthetic_records(_BOUNDED_INDICES, rate=0.40)
    bounded = {
        "A0": _arm_data("A0", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.10)),
        "A1": _arm_data("A1", Path("."), shared_records),
        "A2-strengthened": _arm_data("A2-strengthened", Path("."), list(shared_records)),
    }
    result = select_comparator(bounded, "invoice_recovery_rate")
    assert set(result.tied_set) == {"A1", "A2-strengthened"}


def test_select_comparator_rejects_wrong_arm_set():
    bounded = {"A0": _arm_data("A0", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.2))}
    with pytest.raises(ArtifactError, match="requires exactly the bounded arms"):
        select_comparator(bounded, "invoice_recovery_rate")


# ---------------------------------------------------------------------------
# criterion 2 / criterion 3 / target - built against a hand-constructed
# ComparatorResult so each is tested in isolation from comparator selection.
# ---------------------------------------------------------------------------

def _hand_built_comparator(tied_set):
    from rrx.eval.holdout_analysis import ComparatorResult
    return ComparatorResult(
        metric="invoice_recovery_rate", leader=tied_set[0], leader_rate=0.40,
        tied_set=tuple(tied_set), pairwise_vs_leader={},
    )


def test_evaluate_criterion_2_passes_when_candidate_clearly_beats_tied_set():
    bounded = {
        "A1": _arm_data("A1", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.40)),
        "A2-strengthened": _arm_data(
            "A2-strengthened", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.40)
        ),
    }
    candidate = _arm_data("A3-D", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.70))
    comparator = _hand_built_comparator(["A1", "A2-strengthened"])

    result = evaluate_criterion_2(candidate, comparator, bounded)

    assert result["passed"] is True
    assert set(result["per_member"]) == {"A1", "A2-strengthened"}


def test_evaluate_criterion_2_fails_when_candidate_does_not_beat_one_member():
    bounded = {
        "A1": _arm_data("A1", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.40)),
        "A2-strengthened": _arm_data(
            "A2-strengthened", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.60)
        ),
    }
    # Candidate beats A1 but is statistically indistinguishable from
    # A2-strengthened (identical pattern) - criterion 2 requires beating
    # EVERY tied-set member, so this must fail.
    candidate = _arm_data(
        "A3-D", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.60)
    )
    comparator = _hand_built_comparator(["A1", "A2-strengthened"])

    result = evaluate_criterion_2(candidate, comparator, bounded)

    assert result["passed"] is False


def test_evaluate_criterion_3_contacts_passes_when_candidate_uses_fewer():
    a1_records = _synthetic_records(_BOUNDED_INDICES, rate=0.4, contacts=3)
    bounded = {"A1": _arm_data("A1", Path("."), a1_records)}
    candidate = _arm_data(
        "A3-D", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.7, contacts=1)
    )
    comparator = _hand_built_comparator(["A1"])

    result = evaluate_criterion_3_contacts(candidate, comparator, bounded)

    assert result["passed"] is True
    assert result["violations"] == []


def test_evaluate_criterion_3_contacts_fails_when_candidate_uses_more():
    a1_records = _synthetic_records(_BOUNDED_INDICES, rate=0.4, contacts=1)
    bounded = {"A1": _arm_data("A1", Path("."), a1_records)}
    candidate = _arm_data(
        "A3-D", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.7, contacts=3)
    )
    comparator = _hand_built_comparator(["A1"])

    result = evaluate_criterion_3_contacts(candidate, comparator, bounded)

    assert result["passed"] is False
    assert result["violations"]


def test_evaluate_target_arithmetic():
    oracle = _arm_data("A4", Path("."), _synthetic_records(_BOUNDED_INDICES, rate=0.60))
    comparator = _hand_built_comparator(["A1"])  # leader_rate = 0.40 (hand-built above)

    result = evaluate_target(oracle, comparator, fraction=0.40)

    assert result["oracle_rate"] == pytest.approx(0.60)
    assert result["best_bounded_rate"] == pytest.approx(0.40)
    assert result["gap"] == pytest.approx(0.20)
    assert result["threshold"] == pytest.approx(0.40 + 0.40 * 0.20)  # 0.48


# ---------------------------------------------------------------------------
# analyze_holdout - full synthetic 5-arm orchestration
# ---------------------------------------------------------------------------

def test_analyze_holdout_end_to_end_synthetic(tmp_path):
    indices = range(9000, 9200)  # N=200, all five arms
    run_dirs = {
        "A0": _write_arm(tmp_path, "a0", _synthetic_records(indices, rate=0.20, contacts=0)),
        "A1": _write_arm(tmp_path, "a1", _synthetic_records(indices, rate=0.30, contacts=2)),
        "A2-strengthened": _write_arm(
            tmp_path, "a2s", _synthetic_records(indices, rate=0.35, contacts=2)
        ),
        "A3-D": _write_arm(tmp_path, "a3d", _synthetic_records(indices, rate=0.60, contacts=1)),
        "A4": _write_arm(tmp_path, "a4", _synthetic_records(indices, rate=0.70, contacts=3)),
    }

    result = analyze_holdout(run_dirs, indices)

    assert result["arms_verified"] == ["A0", "A1", "A2-strengthened", "A3-D", "A4"]
    assert result["n_episodes_per_arm"] == 200
    for metric in ("invoice_recovery_rate", "subscription_rescue_rate"):
        block = result["per_metric"][metric]
        assert block["comparator"]["leader"] == "A2-strengthened"
        assert block["criterion_2"]["passed"] is True  # A3-D (0.60) clearly beats 0.35
        assert block["criterion_3_contacts"]["passed"] is True  # A3-D uses fewer contacts
        assert block["target"]["threshold"] == pytest.approx(0.35 + 0.40 * (0.70 - 0.35))


def test_analyze_holdout_raises_on_missing_arm(tmp_path):
    indices = range(9000, 9010)
    run_dirs = {
        "A0": _write_arm(tmp_path, "a0", _synthetic_records(indices, rate=0.2)),
        "A1": _write_arm(tmp_path, "a1", _synthetic_records(indices, rate=0.3)),
        # A2-strengthened, A3-D, A4 deliberately omitted
    }
    with pytest.raises(ArtifactError, match="missing run directories"):
        analyze_holdout(run_dirs, indices)


def test_analyze_holdout_raises_on_index_mismatch_in_one_arm(tmp_path):
    indices = range(9000, 9010)
    short_indices = range(9000, 9009)  # A4 is one episode short
    run_dirs = {
        "A0": _write_arm(tmp_path, "a0", _synthetic_records(indices, rate=0.2)),
        "A1": _write_arm(tmp_path, "a1", _synthetic_records(indices, rate=0.3)),
        "A2-strengthened": _write_arm(tmp_path, "a2s", _synthetic_records(indices, rate=0.35)),
        "A3-D": _write_arm(tmp_path, "a3d", _synthetic_records(indices, rate=0.6)),
        "A4": _write_arm(tmp_path, "a4", _synthetic_records(short_indices, rate=0.7)),
    }
    with pytest.raises(ArtifactError, match="missing episode indices"):
        analyze_holdout(run_dirs, indices)
