"""EVAL.md §5.2 row 7 ("No audit record: 0"): the runner must emit
exactly one ledger record per tick, structurally - every day, every
episode, no exceptions and no drops.

Runs the real A3 runner (src/rrx/harness/runner.py) with the NULL POLICY
over 100 dev episodes, wrapping the real default_ledger_record (not a
bare no-op mock) with a spy that captures every record emitted, then
checks:

  - exactly one record per day per episode (0..window_days inclusive)
  - every record has a valid (one of the 4) tick_type
  - every wakeup-tick record has a non-null reason_code

subscription_cancelled_by_customer episodes are excluded from the
per-day-count check: they terminate at T=0 before any tick exists at all
(docs/A3-DESIGN.md §7, §20) - zero records is the correct, structural
outcome for that bucket, not a completeness violation.
"""

from __future__ import annotations

from rrx.agent.ledger import LedgerRecord, default_ledger_record
from rrx.agent.null_policy import null_policy
from rrx.harness.runner import (
    TICK_BUDGET_EXHAUSTED,
    TICK_NO_WAKEUP,
    TICK_TERMINAL_SUPPRESSED,
    TICK_WAKEUP,
    run_episode_a3,
)
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.cohort import sample_cohort_episode
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

VALID_TICK_TYPES = frozenset(
    {TICK_WAKEUP, TICK_NO_WAKEUP, TICK_BUDGET_EXHAUSTED, TICK_TERMINAL_SUPPRESSED}
)

_N_EPISODES = 100
_INDICES = list(DEV_INDICES)[:_N_EPISODES]


def test_ledger_completeness_over_100_dev_episodes():
    window_days = EPISODE_CFG["episode"]["window_days"]
    records_by_episode: dict[int, list[LedgerRecord]] = {i: [] for i in _INDICES}

    for i in _INDICES:

        def spy_ledger_record(*, _i=i, **kwargs):
            record = default_ledger_record(**kwargs)
            records_by_episode[_i].append(record)
            return record

        run_episode_a3(
            DEV_SPLIT, i, null_policy, EPISODE_CFG, POPULATION_CFG,
            ledger_record=spy_ledger_record,
        )

    cancelled_at_open = {
        i for i in _INDICES
        if sample_cohort_episode(DEV_SPLIT, i, POPULATION_CFG).opening_condition_key
        == "subscription_cancelled_by_customer"
    }

    for i in _INDICES:
        records = records_by_episode[i]

        if i in cancelled_at_open:
            assert records == [], (
                f"episode {i}: subscription_cancelled_by_customer must emit zero "
                f"ledger records (terminal at T=0, before any tick), got {len(records)}"
            )
            continue

        assert len(records) == window_days + 1, (
            f"episode {i}: expected exactly one ledger record per day "
            f"(0..{window_days}), got {len(records)}"
        )

        ticks_seen = sorted(r.tick for r in records)
        assert ticks_seen == list(range(0, window_days + 1)), (
            f"episode {i}: ledger record ticks {ticks_seen} != 0..{window_days}"
        )

        for record in records:
            assert record.tick_type in VALID_TICK_TYPES, (
                f"episode {i}, tick {record.tick}: invalid tick_type {record.tick_type!r}"
            )
            if record.tick_type == TICK_WAKEUP:
                assert record.reason_code is not None, (
                    f"episode {i}, tick {record.tick}: wakeup tick has a null reason_code"
                )
