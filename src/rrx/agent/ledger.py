"""The audit ledger (docs/A3-DESIGN.md §14) - one JSONL-serializable
record per tick.

`default_ledger_record` is a pure function: given the runner's per-tick
bookkeeping (episode_id, tick, tick_type, the EpisodeView used, the
Proposal if any, the gate's verdict if any, what actually executed, and
the pre/post budget), it constructs and returns a LedgerRecord with
every one of §14's fields populated per that table's Mandatory?/A3-D
columns. No I/O - persisting a run's records to results/<run_id>/
ledger.jsonl (§22) is run-orchestration infrastructure that does not
exist yet and is out of scope here; `to_json_line` is provided for when
it does.

A3-D calls this with none of the LLM-only keyword arguments below
supplied, so it still gets every LLM-only field null and `cost=0.0` -
"never omitted" per §17, matching A3-D's own applicability column -
exactly as before Stage 6C.

Day 6 Stage 6B: `fallback_reason` is an optional caller-supplied
parameter (default None) rather than a hardcoded constant.

Day 6 Stage 6C (6C-1/6C-7): the remaining LLM-only fields - `prompt_hash`,
`raw_output`, `latency_ms`, `tokens_in`, `tokens_out`, `cost`,
`model_version`, `template_version` - are likewise now optional
caller-supplied parameters instead of hardcoded constants. Every default
still matches the pre-6C hardcoded value exactly (None for all of them
except `cost`, which stays 0.0), so any call site that predates this
change - and A3-D's call site, always - is byte-for-byte unaffected.
`src/rrx/harness/runner.py` is the only caller that now supplies
non-default values, and only for a policy that exposes them (see
`rrx.agent.planner.A3LLMPolicy`). None of this changes §14's 22-field
schema - every one of these columns already existed; only their wiring
changed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from rrx.agent.gate import AGENT_SEND_HOUR, GateVerdict
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """§14's 22-field per-tick record, in table order."""

    episode_id: str
    tick: int
    tick_type: str
    view_hash: str
    prompt_hash: str | None
    raw_output: str | None
    parsed_action: dict | None
    reason_code: str | None
    rationale: str | None
    gate_verdict: str | None  # "accept" | "reject" | None
    gate_rule_fired: str | None
    fallback_reason: str | None
    executed_action: dict | None
    budget_before: int
    budget_after: int
    send_hour: str | None
    latency_ms: float | None
    tokens_in: int | None
    tokens_out: int | None
    cost: float
    model_version: str | None
    template_version: str | None


def _hash_view(view: EpisodeView) -> str:
    """§14: "hash of the EpisodeView used". EpisodeView is a frozen
    dataclass with a deterministic repr (its only non-primitive field,
    contact_history, is a tuple of frozen ContactRecord dataclasses,
    also deterministically repr'd) - stable across calls for equal
    field values."""
    return hashlib.sha256(repr(view).encode("utf-8")).hexdigest()


def default_ledger_record(
    *,
    episode_id: str,
    tick: int,
    tick_type: str,
    view: EpisodeView,
    proposal: Proposal | None,
    gate_verdict: GateVerdict | None,
    executed_action: dict | None,
    budget_before: int,
    budget_after: int,
    contact_sent: bool,
    fallback_reason: str | None = None,
    prompt_hash: str | None = None,
    raw_output: str | None = None,
    latency_ms: float | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost: float = 0.0,
    model_version: str | None = None,
    template_version: str | None = None,
) -> LedgerRecord:
    """Builds one §14 ledger record for a single day's tick. `proposal`/
    `gate_verdict` are None on non-wakeup ticks (§7: reason_code/
    gate_verdict/gate_rule_fired are wakeup-only). `send_hour` is stamped
    here, by the ledger (§9, §14), as the fixed `AGENT_SEND_HOUR`
    whenever `contact_sent` is True - never computed or chosen by the
    runner. Every keyword argument from `fallback_reason` onward defaults
    to exactly the value this function hardcoded before Day 6 Stage
    6B/6C - passing any of them is opt-in, never required, and A3-D's
    call site never does."""
    gate_verdict_str: str | None = None
    gate_rule_fired: str | None = None
    if gate_verdict is not None:
        gate_verdict_str = "accept" if gate_verdict.accepted else "reject"
        gate_rule_fired = gate_verdict.rule_fired

    return LedgerRecord(
        episode_id=episode_id,
        tick=tick,
        tick_type=tick_type,
        view_hash=_hash_view(view),
        prompt_hash=prompt_hash,
        raw_output=raw_output,
        parsed_action=asdict(proposal) if proposal is not None else None,
        reason_code=proposal.reason_code if proposal is not None else None,
        rationale=proposal.rationale if proposal is not None else None,
        gate_verdict=gate_verdict_str,
        gate_rule_fired=gate_rule_fired,
        fallback_reason=fallback_reason,
        executed_action=executed_action,
        budget_before=budget_before,
        budget_after=budget_after,
        send_hour=AGENT_SEND_HOUR if contact_sent else None,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
        model_version=model_version,
        template_version=template_version,
    )


def to_json_line(record: LedgerRecord) -> str:
    """One §22 results/**/ledger.jsonl line. Not called by the runner in
    this pass - no run_id/results-directory infrastructure exists yet."""
    return json.dumps(asdict(record), sort_keys=True)
