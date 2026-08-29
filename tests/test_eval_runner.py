"""Stage A: tests for the minimal A3-D dev-run orchestration driver
(src/rrx/eval/runner.py). Covers the pure metrics/audit-coverage functions
against synthetic fixtures, plus small smoke tests of the real
run_a3d_dev_cohort/main() path over a handful of dev episodes (not the
full 2,000 - that is the actual official run, executed once, separately).
"""

from __future__ import annotations

import json

import pytest

from rrx.agent.ledger import LedgerRecord
from rrx.eval.runner import (
    ResultsDirectoryExistsError,
    audit_coverage_check,
    compute_metrics,
    main,
    run_a3d_dev_cohort,
)
from rrx.harness.splits import DEV_SPLIT
from rrx.sim.engine import EpisodeResult
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()


def _record(**overrides) -> LedgerRecord:
    base = dict(
        episode_id="dev-1000",
        tick=0,
        tick_type="wakeup",
        view_hash="deadbeef",
        prompt_hash=None,
        raw_output=None,
        parsed_action={"action_type": "CONTACT", "remedy": "card_change"},
        reason_code="remedy_match_card",
        rationale="R-12",
        gate_verdict="accept",
        gate_rule_fired=None,
        fallback_reason=None,
        executed_action={"action_type": "CONTACT", "remedy": "card_change"},
        budget_before=3,
        budget_after=2,
        send_hour="10:00",
        latency_ms=None,
        tokens_in=None,
        tokens_out=None,
        cost=0.0,
        model_version=None,
        template_version=None,
    )
    base.update(overrides)
    return LedgerRecord(**base)


def _result(**overrides) -> EpisodeResult:
    base = dict(
        opening_condition_key="card_expired",
        invoice_amount_inr=2000,
        invoice_recovered=True,
        subscription_rescued=True,
        contacts_sent=2,
        wasted_attempts=0,
        card_change_sent_for_insufficient_funds=False,
    )
    base.update(overrides)
    return EpisodeResult(**base)


# ---------------------------------------------------------------------------
# compute_metrics - synthetic fixtures, no simulator call
# ---------------------------------------------------------------------------

def test_compute_metrics_basic_rates():
    results = [
        _result(invoice_recovered=True, subscription_rescued=True, contacts_sent=2),
        _result(invoice_recovered=False, subscription_rescued=False, contacts_sent=1),
    ]
    ledger = [
        _record(episode_id="dev-1000", reason_code="remedy_match_card"),
        _record(episode_id="dev-1001", tick_type="no_wakeup", reason_code=None,
                gate_verdict=None, executed_action=None),
    ]
    metrics = compute_metrics(results, ledger)
    assert metrics["n"] == 2
    assert metrics["invoice_recovery_rate"] == 0.5
    assert metrics["subscription_rescue_rate"] == 0.5
    assert metrics["total_contacts"] == 3
    assert metrics["contacts_per_invoice_recovered"] == 3.0  # 3 contacts / 1 recovered
    assert metrics["tick_type_distribution"] == {"wakeup": 1, "no_wakeup": 1}
    assert metrics["n_wakeup_ticks"] == 1
    assert metrics["gate_rejection_count"] == 0


def test_compute_metrics_gate_rejection_and_escalation_counted():
    ledger = [
        _record(episode_id="dev-1000", gate_verdict="reject", gate_rule_fired="R3",
                executed_action={"action_type": "WAIT"}),
        _record(episode_id="dev-1001", reason_code="risk_flagged",
                executed_action={"action_type": "STOP"}),
        _record(episode_id="dev-1002", reason_code="no_engagement_restraint",
                executed_action={"action_type": "WAIT"}),
    ]
    metrics = compute_metrics([_result(), _result(), _result()], ledger)
    assert metrics["gate_rejection_count"] == 1
    assert metrics["gate_rule_fired_distribution"] == {"R3": 1}
    assert metrics["escalation_count"] == 1
    assert metrics["wait_count"] == 2
    assert metrics["n_wakeup_ticks"] == 3
    assert metrics["gate_rejection_rate_of_wakeups"] == 1 / 3


def test_compute_metrics_safety_invariants_present_and_zero_when_clean():
    results = [_result(card_change_sent_for_insufficient_funds=False, contacts_sent=3)]
    ledger = [_record(episode_id="dev-1000")]
    metrics = compute_metrics(results, ledger)
    inv = metrics["safety_invariants"]
    assert inv["gate_rejections_total"] == 0
    assert inv["contacts_to_cancelled_or_expired__R2_fired"] == 0
    assert inv["contacts_after_risk_flagged__R4_fired"] == 0
    assert inv["card_change_for_insufficient_funds"] == 0
    assert inv["contacts_exceeding_budget__R5_fired"] == 0
    assert inv["max_contacts_sent_observed"] == 3
    assert inv["contacts_outside_quiet_hours__R6_fired"] == 0
    assert inv["unverified_codes_emitted__R8_fired"] == 0


def test_compute_metrics_reports_unavailable_metrics():
    metrics = compute_metrics([_result()], [_record()])
    assert "median_time_to_rescue_days" in metrics["unavailable_metrics"]
    assert "p90_time_to_rescue_days" in metrics["unavailable_metrics"]
    assert "regime_a_net_value" in metrics["unavailable_metrics"]


def test_compute_metrics_handles_zero_episodes():
    metrics = compute_metrics([], [])
    assert metrics["n"] == 0
    assert metrics["invoice_recovery_rate"] is None
    assert metrics["contacts_per_invoice_recovered"] is None


# ---------------------------------------------------------------------------
# audit_coverage_check
# ---------------------------------------------------------------------------

def test_audit_coverage_check_flags_missing_records():
    window_days = 30
    results = [
        _result(opening_condition_key="card_expired"),
        _result(opening_condition_key="subscription_cancelled_by_customer"),
    ]
    indices = [1000, 1001]
    ledger = [
        _record(episode_id="dev-1000", tick=d) for d in range(window_days + 1)
    ]  # dev-1001 (cancelled-at-open) correctly has zero records
    result = audit_coverage_check(results, indices, ledger, window_days)
    assert result["ok"], result["violations"]
    assert result["episodes_checked"] == 2


def test_audit_coverage_check_catches_a_real_gap():
    window_days = 30
    results = [_result(opening_condition_key="card_expired")]
    indices = [1000]
    ledger = [_record(episode_id="dev-1000", tick=d) for d in range(window_days)]  # one short
    result = audit_coverage_check(results, indices, ledger, window_days)
    assert not result["ok"]
    assert result["violations"] == [{"episode_id": "dev-1000", "expected": 31, "actual": 30}]


# ---------------------------------------------------------------------------
# Smoke tests over a handful of real dev episodes (not the full 2,000 run)
# ---------------------------------------------------------------------------

def test_run_a3d_dev_cohort_smoke_over_five_episodes():
    indices = list(range(1000, 1005))
    results, ledger = run_a3d_dev_cohort(EPISODE_CFG, POPULATION_CFG, indices)
    assert len(results) == 5
    assert all(isinstance(r, EpisodeResult) for r in results)
    assert ledger  # at least one tick across 5 episodes
    assert all(r.episode_id.startswith(f"{DEV_SPLIT}-") for r in ledger)


def test_main_end_to_end_smoke(tmp_path):
    indices = list(range(1000, 1010))
    run_dir = main(results_dir=tmp_path, run_id="smoke-test-run", indices=indices)

    assert run_dir == tmp_path / "smoke-test-run"
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "ledger.jsonl").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "run_params.json").exists()

    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["arm"] == "A3-D"
    assert manifest["seed"] == 20260825
    assert len(manifest["git_sha"]) == 40

    run_params = json.loads((run_dir / "run_params.json").read_text())
    assert run_params["index_start"] == 1000
    assert run_params["index_end"] == 1009
    assert run_params["n"] == 10

    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["n"] == 10
    assert metrics["audit_coverage"]["ok"], metrics["audit_coverage"]["violations"]


def test_main_stops_if_results_dir_already_exists(tmp_path):
    existing = tmp_path / "already-here"
    existing.mkdir()
    try:
        main(results_dir=tmp_path, run_id="already-here", indices=[1000])
        assert False, "expected ResultsDirectoryExistsError"
    except ResultsDirectoryExistsError:
        pass


# ---------------------------------------------------------------------------
# Day 8 pre-holdout provenance fixes (docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md):
#   Issue 1 - episode_results.jsonl (per-episode outcome persistence)
#   Issue 2 - manifest.json's spec_version
# Covers the A3-D / main() path here; A0/A1/A2-strengthened/A4's shared
# run_official_arm() path is covered in test_eval_arms.py.
# ---------------------------------------------------------------------------

_EPISODE_RESULT_FIELDS = {
    "opening_condition_key",
    "invoice_amount_inr",
    "invoice_recovered",
    "subscription_rescued",
    "contacts_sent",
    "wasted_attempts",
    "card_change_sent_for_insufficient_funds",
}


def test_write_episode_results_direct(tmp_path):
    from rrx.eval.runner import write_episode_results

    results = [_result(invoice_recovered=True), _result(invoice_recovered=False)]
    indices = [1000, 1001]
    out_path = write_episode_results(tmp_path, indices, results)

    assert out_path == tmp_path / "episode_results.jsonl"
    lines = out_path.read_text().strip().splitlines()
    assert len(lines) == 2

    records = [json.loads(line) for line in lines]
    assert records[0]["episode_index"] == 1000
    assert records[0]["invoice_recovered"] is True
    assert records[1]["episode_index"] == 1001
    assert records[1]["invoice_recovered"] is False
    for record in records:
        assert set(record) == {"episode_index"} | _EPISODE_RESULT_FIELDS


def test_write_episode_results_rejects_length_mismatch(tmp_path):
    from rrx.eval.runner import write_episode_results

    with pytest.raises(ValueError):
        write_episode_results(tmp_path, [1000, 1001], [_result()])


def test_main_writes_episode_results_jsonl_for_a3d(tmp_path):
    indices = list(range(1000, 1010))
    run_dir = main(results_dir=tmp_path, run_id="smoke-episode-results-a3d", indices=indices)

    episode_results_path = run_dir / "episode_results.jsonl"
    assert episode_results_path.exists()

    lines = episode_results_path.read_text().strip().splitlines()
    assert len(lines) == len(indices)

    records = [json.loads(line) for line in lines]
    assert [r["episode_index"] for r in records] == indices
    for record in records:
        assert set(record) == {"episode_index"} | _EPISODE_RESULT_FIELDS


def test_main_manifest_reports_eval_spec_v1_10(tmp_path):
    run_dir = main(results_dir=tmp_path, run_id="smoke-spec-version-a3d", indices=[1000])
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["spec_version"] == "eval-spec-v1.10"
