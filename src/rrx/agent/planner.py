"""A3-LLM planner (docs/A3-DESIGN.md §11).

Implements, at this layer, exactly what Day 6 Stage 6B Decision 2
assigns here rather than to the frozen gate:

    raw LLM output -> strict parsing -> schema validation ->
    reason_code / admissibility validation -> Proposal -> existing frozen
    gate (src/rrx/agent/gate.py, UNMODIFIED - no reason_code check added
    to it, no new R1-R8 rule, no precedence change).

Also implements §11's fallback mechanic: "re-invoke A3-D's pure function
for the same EpisodeView/tick; its proposal executes through the same
gate/executor." `rrx.agent.policy.a3d_policy` is imported and called
UNMODIFIED - this module never edits it (Day 6 Decision 4).

SCOPE, EXPLICIT: this module determines 3 of the 5 frozen
`fallback_reason` values - `timeout`, `unparseable`, `schema_violation`
(§19's first two injected failure modes) - because those are knowable
before any Proposal reaches the gate. `invoke_planner` below never
fabricates a `gate_rejected` or `stale_state` outcome itself.

The remaining two are only knowable AFTER a Proposal has been
gate-evaluated, which this module structurally cannot do (it has no gate
call of its own - Day 6 Decision 2: reason_code/schema validation lives
here, gate semantics do not move). `gate_rejected` is handled one layer
up, generically, by `src/rrx/harness/runner.py::run_episode_a3` (Day 6
Stage 6B addition - see that module's docstring): if the gate rejects
WHATEVER proposal a policy returns (this module's included), the runner
itself re-invokes `rrx.agent.policy.a3d_policy` for the same view and
re-gates that. `stale_state` remains unimplemented everywhere - sim-v1's
single-threaded, synchronous day loop gives no mechanism for
`subscription_state` to change between a view being built and that same
view being gate-evaluated (see the runner module's docstring for the
full argument). Not simulated artificially.

Pure except for the one side effect an LLM policy structurally requires:
`client.complete(...)`. No `rrx.sim` import - this module reads only
EpisodeView/ContactRecord fields, exactly as §11 specifies. No live
network call exists anywhere in this module or its dependencies - only a
`Protocol` and a non-network `StubLLMClient` test double.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

from rrx.agent.llm_cache import (
    CacheKey,
    CacheMissDuringReplayError,
    LiveCallNotAllowedError,
    LLMCache,
    compute_prompt_hash,
)
from rrx.agent.policy import a3d_policy
from rrx.agent.prompt import TEMPLATE_VERSION, render_prompt
from rrx.agent.proposal import Proposal
from rrx.agent.reason_codes import POST_HALT_RESCUE, REASON_CODES, is_admissible
from rrx.features.episode_view import EpisodeView

# §14's 5-value fallback_reason enum, verbatim.
FALLBACK_REASONS = frozenset(
    {"timeout", "unparseable", "schema_violation", "gate_rejected", "stale_state"}
)

_ACTION_TYPES = frozenset({"CONTACT", "WAIT", "STOP"})
_REMEDIES = frozenset({"card_change", "topup_reminder"})
# §11's output schema: exactly these four keys - no `channel` (§6, §20).
_REQUIRED_KEYS = frozenset({"action_type", "remedy", "reason_code", "rationale"})


class LLMClient(Protocol):
    """The only capability a planner needs from an LLM integration. No
    implementation calling a real network endpoint exists in this pass
    (Day 6 Decision: "Do not select a model merely to unblock Stage
    6B") - only this Protocol and `StubLLMClient` below."""

    def complete(self, prompt: str, *, model: str, temperature: float) -> str: ...


class PlannerTimeoutError(Exception):
    """Raised by an `LLMClient` to signal §19's "API timeout" failure
    mode. `StubLLMClient` can be configured to raise this for test
    coverage; a live client (not implemented in this pass) would raise it
    on an actual network timeout."""


@dataclass(frozen=True, slots=True)
class StubLLMClient:
    """Deterministic, no-network test double. Never used for a real run.
    `response` is returned verbatim for every call unless `raises` is set,
    in which case that exception is raised instead - lets a test exercise
    the timeout fallback path with no real timing behavior.

    `tokens_in`/`tokens_out`/`cost_inr` (Day 6 Stage 6C, 6C-7) are
    EXPLICITLY STUB VALUES the caller sets deterministically for a test -
    never a real tokenizer count or a real provider price. `invoke_planner`
    reads them via `getattr(client, ...)` after a successful call, exactly
    the way it reads `raises`/`response` - a real (not-implemented-in-this-
    pass) client would expose the same three attributes with genuine
    values from its provider's response."""

    response: str = ""
    raises: BaseException | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_inr: float = 0.0

    def complete(self, prompt: str, *, model: str, temperature: float) -> str:
        if self.raises is not None:
            raise self.raises
        return self.response


@dataclass(frozen=True, slots=True)
class ParseFailure:
    """Names which of the 3 planner-layer `fallback_reason` values
    applies, and why (diagnostic only - `detail` is never assumed
    machine-parsed)."""

    fallback_reason: str
    detail: str


@dataclass(frozen=True, slots=True)
class PlannerOutcome:
    """Day 6 Stage 6C (6C-1/6C-7) adds the six fields from `prompt_hash`
    onward - every one of them a §14 ledger column that was previously
    computed inside `invoke_planner` and then discarded. `latency_ms` is a
    genuine (not fabricated) elapsed-wall-clock measurement of the
    `client.complete(...)` call in THIS process - meaningful even for an
    offline stub, just small. `tokens_in`/`tokens_out`/`cost_inr` are
    whatever the `LLMClient` reports (see `StubLLMClient`); on a cache
    hit, no live call was made in this execution, so all three are None/
    0.0 here regardless of what a prior live call might have cost (see
    this module's `invoke_planner` docstring for why the cache does not
    also store this accounting metadata for replay)."""

    proposal: Proposal
    fallback_reason: str | None
    raw_output: str | None
    used_fallback: bool
    prompt_hash: str
    model: str
    template_version: str
    latency_ms: float | None
    tokens_in: int | None
    tokens_out: int | None
    cost_inr: float


def parse_llm_output(raw: str, view: EpisodeView) -> Proposal | ParseFailure:
    """§11's strict schema validation, plus Decision 2's reason_code /
    admissibility check at this layer (not the gate). Returns a Proposal
    on success, a ParseFailure otherwise. Never raises for malformed
    `raw` - classifying malformed input is this function's job, not
    something it propagates as an exception.

    unparseable  - raw text is not a JSON object at all (can't even
                   extract structured fields).
    schema_violation - JSON parsed, but the shape or field values are
                   invalid: wrong/extra/missing keys, an out-of-enum
                   value, a `remedy` inconsistent with `action_type`, a
                   `reason_code` inadmissible for this view's
                   `decline_code` (docs/A3-DESIGN.md §7), or an empty
                   rationale.

    This is a Stage 6B interpretation filling a genuine gap in the frozen
    text (§19 lists both reasons for "malformed/hallucinated" without
    drawing this exact line) - flagged as such in the Stage 6B deliverable,
    not asserted as if v1.7 spelled it out verbatim.
    """
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ParseFailure("unparseable", "raw output is not valid JSON")

    if not isinstance(obj, dict):
        return ParseFailure(
            "unparseable", f"top-level JSON value is {type(obj).__name__}, not an object"
        )

    keys = set(obj.keys())
    if keys != _REQUIRED_KEYS:
        return ParseFailure(
            "schema_violation", f"keys {sorted(keys)} != required {sorted(_REQUIRED_KEYS)}"
        )

    action_type = obj["action_type"]
    remedy = obj["remedy"]
    reason_code = obj["reason_code"]
    rationale = obj["rationale"]

    if not isinstance(action_type, str) or action_type not in _ACTION_TYPES:
        return ParseFailure(
            "schema_violation", f"action_type {action_type!r} not in {sorted(_ACTION_TYPES)}"
        )

    if action_type == "CONTACT":
        if not isinstance(remedy, str) or remedy not in _REMEDIES:
            return ParseFailure("schema_violation", f"remedy {remedy!r} invalid for CONTACT")
    elif remedy is not None:
        return ParseFailure(
            "schema_violation",
            f"remedy must be null for action_type={action_type!r}, got {remedy!r}",
        )

    if not isinstance(reason_code, str) or reason_code not in REASON_CODES:
        return ParseFailure(
            "schema_violation", f"reason_code {reason_code!r} not in the frozen 7-value enum"
        )

    if not is_admissible(reason_code, view.decline_code):
        return ParseFailure(
            "schema_violation",
            f"reason_code {reason_code!r} not admissible for decline_code "
            f"{view.decline_code!r} (docs/A3-DESIGN.md §7)",
        )

    # §7's admissibility table is decline_code-keyed only; its own comment
    # notes post_halt_rescue "additionally requires subscription_state ==
    # halted", not encoded in rrx.agent.reason_codes.ADMISSIBLE_DECLINE_CODES.
    # Checked here explicitly rather than silently accepted, since it is
    # part of §7's frozen text even though the existing helper doesn't
    # cover it.
    if reason_code == POST_HALT_RESCUE and view.subscription_state != "halted":
        return ParseFailure(
            "schema_violation",
            "post_halt_rescue requires subscription_state == 'halted' (§7)",
        )

    if not isinstance(rationale, str) or not rationale.strip():
        return ParseFailure("schema_violation", "rationale must be a non-empty string")

    return Proposal(
        action_type=action_type, remedy=remedy, rationale=rationale, reason_code=reason_code
    )


def invoke_planner(
    view: EpisodeView,
    *,
    client: LLMClient,
    model: str,
    temperature: float,
    template_version: str = TEMPLATE_VERSION,
    cache: LLMCache | None = None,
    allow_live: bool = False,
) -> PlannerOutcome:
    """§11's planner entry point: EpisodeView -> PlannerOutcome. Always
    returns a valid Proposal - either the LLM's (parsed, validated) one,
    or A3-D's fallback proposal for the same view - never raises for a
    malformed LLM response.

    DOES raise, deliberately, per §13: `CacheMissDuringReplayError` on a
    cache miss while replaying a past run (`cache.replay=True`), or
    `LiveCallNotAllowedError` on a cache miss with `allow_live=False`.
    Both are hard stops, not fallback triggers - §13 draws that line
    explicitly ("Cache-miss during exact replay = hard failure, never a
    silent live re-call").

    Day 6 Stage 6C accounting note: on a cache HIT, `latency_ms`,
    `tokens_in`, `tokens_out` are `None` and `cost_inr` is `0.0` in the
    returned outcome - no live call happened in THIS execution, so
    nothing was measured or spent by it. `rrx.agent.llm_cache.LLMCache`
    stores only `raw_output` (§13's own cache-key/value contract), not
    token/cost metadata: replaying a run reproduces its DECISIONS
    deterministically (raw_output alone determines the parsed Proposal),
    but does not re-incur, and therefore should not re-report, the
    original live call's cost - whether a replayed run's ledger should
    instead carry forward the ORIGINAL call's historical accounting
    figures is a real methodology question the frozen text does not
    settle, flagged here rather than decided unilaterally.
    """
    prompt = render_prompt(view, template_version=template_version)
    p_hash = compute_prompt_hash(prompt)
    key = CacheKey(
        template_version=template_version,
        model=model,
        temperature=temperature,
        prompt_hash=p_hash,
    )

    raw = cache.get(key) if cache is not None else None
    latency_ms: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_inr = 0.0

    if raw is None:
        if cache is not None and cache.replay:
            raise CacheMissDuringReplayError(
                f"cache miss during replay for {key!r} - exact replay of a past "
                "run_id must be satisfied entirely from its cache (docs/A3-DESIGN.md §13)."
            )
        if not allow_live:
            raise LiveCallNotAllowedError(
                f"no cached response for {key!r} and allow_live=False - a live "
                "LLM call requires allow_live=True (docs/A3-DESIGN.md §13)."
            )
        start = time.monotonic()
        try:
            raw = client.complete(prompt, model=model, temperature=temperature)
        except PlannerTimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            fallback = a3d_policy(view)
            return PlannerOutcome(
                proposal=fallback,
                fallback_reason="timeout",
                raw_output=None,
                used_fallback=True,
                prompt_hash=p_hash,
                model=model,
                template_version=template_version,
                latency_ms=elapsed_ms,
                tokens_in=None,
                tokens_out=None,
                cost_inr=0.0,
            )
        latency_ms = (time.monotonic() - start) * 1000.0
        tokens_in = getattr(client, "tokens_in", None)
        tokens_out = getattr(client, "tokens_out", None)
        cost_inr = getattr(client, "cost_inr", 0.0)
        if cache is not None:
            cache.put(key, raw)

    common = dict(
        raw_output=raw,
        prompt_hash=p_hash,
        model=model,
        template_version=template_version,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_inr=cost_inr,
    )

    parsed = parse_llm_output(raw, view)
    if isinstance(parsed, ParseFailure):
        fallback = a3d_policy(view)
        return PlannerOutcome(
            proposal=fallback,
            fallback_reason=parsed.fallback_reason,
            used_fallback=True,
            **common,
        )

    return PlannerOutcome(
        proposal=parsed, fallback_reason=None, used_fallback=False, **common
    )


class A3LLMPolicy:
    """A callable `(EpisodeView) -> Proposal` object - satisfies the exact
    same `PolicyFn` shape a bare function (like `rrx.agent.policy.
    a3d_policy`) does, so `src/rrx/harness/runner.py::run_episode_a3`
    needs no change to accept it (Day 6 Decision 1).

    Day 6 Stage 6B closure: unlike a bare function, this object also
    records its own most recent call's `fallback_reason`/`used_fallback`
    as plain attributes - `last_fallback_reason`, `last_used_fallback`.
    The runner reads `last_fallback_reason` via
    `getattr(policy, "last_fallback_reason", None)` immediately after
    calling `policy(view)`, which is why this is a stateful object and
    not a plain closure: a bare function has no attribute to read, so
    `getattr(..., None)` correctly returns `None` for `a3d_policy` and any
    other plain-function policy, every time - the mechanism is additive
    and invisible to any policy that doesn't opt in by exposing it.

    Day 6 Stage 6C (6C-1/6C-7): the same mechanism now also carries every
    other `PlannerOutcome` field a §14 ledger column needs -
    `last_raw_output`, `last_prompt_hash`, `last_model_version`,
    `last_template_version`, `last_latency_ms`, `last_tokens_in`,
    `last_tokens_out`, `last_cost_inr`. `last_cost_inr` defaults to `0.0`
    (not `None`), matching `default_ledger_record`'s own `cost: float =
    0.0` default and §17's "never omitted" rule - every other `last_*`
    attribute defaults to `None`, matching that function's other LLM-only
    defaults exactly.

    Not thread-safe / not re-entrant - matches sim-v1's single-threaded,
    one-call-at-a-time day loop exactly; no stronger guarantee is needed
    or provided.
    """

    def __init__(
        self,
        *,
        client: LLMClient,
        model: str,
        temperature: float,
        template_version: str = TEMPLATE_VERSION,
        cache: LLMCache | None = None,
        allow_live: bool = False,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._template_version = template_version
        self._cache = cache
        self._allow_live = allow_live
        self.last_fallback_reason: str | None = None
        self.last_used_fallback: bool = False
        self.last_raw_output: str | None = None
        self.last_prompt_hash: str | None = None
        self.last_model_version: str | None = None
        self.last_template_version: str | None = None
        self.last_latency_ms: float | None = None
        self.last_tokens_in: int | None = None
        self.last_tokens_out: int | None = None
        self.last_cost_inr: float = 0.0

    def __call__(self, view: EpisodeView) -> Proposal:
        outcome = invoke_planner(
            view,
            client=self._client,
            model=self._model,
            temperature=self._temperature,
            template_version=self._template_version,
            cache=self._cache,
            allow_live=self._allow_live,
        )
        self.last_fallback_reason = outcome.fallback_reason
        self.last_used_fallback = outcome.used_fallback
        self.last_raw_output = outcome.raw_output
        self.last_prompt_hash = outcome.prompt_hash
        self.last_model_version = outcome.model
        self.last_template_version = outcome.template_version
        self.last_latency_ms = outcome.latency_ms
        self.last_tokens_in = outcome.tokens_in
        self.last_tokens_out = outcome.tokens_out
        self.last_cost_inr = outcome.cost_inr
        return outcome.proposal


def make_a3_llm_policy(
    *,
    client: LLMClient,
    model: str,
    temperature: float,
    template_version: str = TEMPLATE_VERSION,
    cache: LLMCache | None = None,
    allow_live: bool = False,
) -> A3LLMPolicy:
    """Returns an `A3LLMPolicy` instance - a `(EpisodeView) -> Proposal`
    callable, exactly the `PolicyFn` shape
    `src/rrx/harness/runner.py::run_episode_a3` already accepts for its
    `policy` parameter (Day 6 Decision 1: no runner change to dispatch
    A3-LLM). See `A3LLMPolicy`'s own docstring for how
    `last_fallback_reason` reaches the ledger without widening `PolicyFn`
    itself."""
    return A3LLMPolicy(
        client=client,
        model=model,
        temperature=temperature,
        template_version=template_version,
        cache=cache,
        allow_live=allow_live,
    )
