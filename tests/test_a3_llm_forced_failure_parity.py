"""Day 6 Stage 6C-8: THE PRIMARY STAGE 6C GATE.

FORCED A3-LLM FAILURE -> A3-D FALLBACK -> SAME GATE -> SAME EXECUTOR ->
SAME SIMULATOR must produce the same underlying episode outcomes as
frozen A3-D, over the full DEV split (N=2,000, seeds 1000-2999) - the
same split, same episodes, same seeds, same runner
(rrx.harness.runner.run_episode_a3), same simulator, same gate, same
executor A3-D itself uses.

Why this must hold, structurally (not just empirically): under a forced
timeout, rrx.agent.planner.invoke_planner's ONLY code path is
`client.complete(...)` raises `PlannerTimeoutError` -> `a3d_policy(view)`
is returned AS the policy's own return value, before the runner-level
gate-rejection hook (src/rrx/harness/runner.py, Day 6 Stage 6B) is even
reached. The runner therefore receives, on every single wakeup tick,
EXACTLY the Proposal `a3d_policy(view)` would have returned directly -
gate-compliant by construction (tests/test_a3d_policy.py's exhaustive
proof), so the gate always accepts it on the first try, and the
gate-rejection fallback hook is never entered either. The two runs are
executing IDENTICAL decision logic at every tick; only the audit metadata
around that decision differs.

If this test finds ANY divergence beyond the explicitly-allowed
LLM-audit-metadata fields, that is the "first divergence" the Stage 6C
instructions require reporting - not explained away, not tuned around.
"""

from __future__ import annotations

from rrx.agent.ledger import LedgerRecord, default_ledger_record
from rrx.agent.planner import PlannerTimeoutError, StubLLMClient, make_a3_llm_policy
from rrx.agent.policy import a3d_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Fields that are STRUCTURALLY expected to differ between an A3-D-direct
# ledger record and its forced-timeout A3-LLM counterpart, per the module
# docstring's argument: fallback_reason (None vs "timeout"), and the
# metadata a live-but-failed call attempt produces that a3d_policy's own
# direct invocation never touches at all (prompt_hash/latency_ms/
# model_version/template_version). raw_output/tokens_in/tokens_out/cost
# are explicitly NOT in this set - a timeout produces no response, so
# these must be None/None/None/0.0 on BOTH sides, identically.
_ALLOWED_DIVERGENT_FIELDS = frozenset(
    {"fallback_reason", "prompt_hash", "latency_ms", "model_version", "template_version"}
)


def _capturing_ledger():
    records: list[LedgerRecord] = []

    def _record(**kwargs):
        rec = default_ledger_record(**kwargs)
        records.append(rec)
        return rec

    return records, _record


def _run_and_capture(policy, i: int):
    records, capturing_ledger = _capturing_ledger()
    result = run_episode_a3(
        DEV_SPLIT, i, policy, EPISODE_CFG, POPULATION_CFG, ledger_record=capturing_ledger,
    )
    return result, records


def _first_divergent_field(a: LedgerRecord, b: LedgerRecord) -> str | None:
    import dataclasses

    for f in dataclasses.fields(LedgerRecord):
        if f.name in _ALLOWED_DIVERGENT_FIELDS:
            continue
        if getattr(a, f.name) != getattr(b, f.name):
            return f.name
    return None


def test_forced_timeout_a3_llm_reproduces_a3d_over_the_full_dev_split():
    """THE PRIMARY STAGE 6C GATE. N=2,000 (full dev split, seeds
    1000-2999) - not a sample."""
    always_times_out = StubLLMClient(raises=PlannerTimeoutError("Stage 6C forced failure"))
    llm_policy = make_a3_llm_policy(
        client=always_times_out, model="stub", temperature=0.0, allow_live=True,
    )

    n_compared = 0
    n_ledger_records_compared = 0
    n_timeout_fallbacks_observed = 0

    for i in DEV_INDICES:
        a3d_result, a3d_records = _run_and_capture(a3d_policy, i)
        llm_result, llm_records = _run_and_capture(llm_policy, i)
        n_compared += 1

        # --- (1) full EpisodeResult byte-for-byte equality ---
        if a3d_result != llm_result:
            raise AssertionError(
                f"FIRST DIVERGENCE at dev index {i}: EpisodeResult differs.\n"
                f"  A3-D:    {a3d_result}\n"
                f"  A3-LLM:  {llm_result}"
            )

        # --- (2) tick-by-tick ledger equality on every field EXCEPT the
        # explicitly-allowed LLM-audit-metadata set ---
        assert len(a3d_records) == len(llm_records), (
            f"FIRST DIVERGENCE at dev index {i}: ledger record COUNT differs "
            f"({len(a3d_records)} vs {len(llm_records)})"
        )
        for tick, (a_rec, l_rec) in enumerate(zip(a3d_records, llm_records)):
            n_ledger_records_compared += 1
            field = _first_divergent_field(a_rec, l_rec)
            if field is not None:
                raise AssertionError(
                    f"FIRST DIVERGENCE at dev index {i}, tick {tick}, field {field!r}:\n"
                    f"  A3-D:    {getattr(a_rec, field)!r}\n"
                    f"  A3-LLM:  {getattr(l_rec, field)!r}\n"
                    f"  full A3-D record:   {a_rec}\n"
                    f"  full A3-LLM record: {l_rec}"
                )
            if a_rec.tick_type == "wakeup":
                # (3) the ONE expected difference actually shows up, on
                # every wakeup tick - confirms this is a real forced-
                # failure exercise, not a vacuously-passing no-op scan.
                assert a_rec.fallback_reason is None
                assert l_rec.fallback_reason == "timeout"
                n_timeout_fallbacks_observed += 1

    assert n_compared == 2000, f"expected full dev split (N=2000), compared {n_compared}"
    assert n_timeout_fallbacks_observed > 0, "scan never hit a single wakeup tick - broken fixture"

    print(
        f"6C-8 primary gate: {n_compared} episodes, "
        f"{n_ledger_records_compared} ledger records, "
        f"{n_timeout_fallbacks_observed} forced-timeout fallbacks - all reproduced A3-D exactly "
        "outside the allowed LLM-audit-metadata fields."
    )
