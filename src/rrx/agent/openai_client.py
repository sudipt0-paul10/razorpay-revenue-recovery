"""OpenAI Chat Completions provider adapter (Day 6 Stage 6I) - gpt-5-mini.

Implements `rrx.agent.planner.LLMClient`'s Protocol
(`complete(prompt, *, model, temperature) -> str`) using the official
`openai` Python SDK. Analogous to `gemini_client.py` wherever OpenAI's
API semantics allow it to be; diverges only where they don't (temperature
handling, error taxonomy, response field names - noted inline below).

FIXED, per `results/tuning_log.md` Entry 2 (the frozen GPT-native
methodology - GPT-C1..C6):
- model = `gpt-5-mini`
- `temperature` is NEVER forwarded to the API - Stage 6G.1 empirically
  confirmed (one live HTTP request, `temperature=0.5` -> HTTP 400
  `invalid_request_error`/`unsupported_value`: "Only the default (1)
  value is supported") that `gpt-5-mini` rejects any non-default
  temperature. The frozen methodology's response is to omit the
  parameter entirely, not to pass `1` explicitly. `complete()` still
  ACCEPTS a `temperature` argument (LLMClient's Protocol requires it,
  and `rrx.agent.planner.invoke_planner`'s cache-key construction still
  needs some value for that field) but never sends it to OpenAI.
- `verbosity="low"` is a FIXED, non-configurable constant used by every
  call this module makes - not a constructor parameter, so there is no
  way to accidentally vary it per cell (results/tuning_log.md Entry 2:
  "verbosity must NOT vary across cells").
- `reasoning_effort` is a CONSTRUCTOR-time `OpenAIClient` setting, one
  fixed value per instance, exactly mirroring how `thinking_level` is a
  constructor-time `GeminiClient` setting (Day 6 Stage 6E) - `LLMClient`'s
  Protocol is unchanged, so this requires zero change to `planner.py`.

Cache isolation: `reasoning_effort`, like Gemini's `thinking_level`, is
NOT part of the frozen `(template_version, model, temperature,
prompt_hash)` cache key (`rrx.agent.llm_cache.CacheKey`). GPT-C1/C3/C5
(minimal/low/medium reasoning, disclosure=low) would collide on that key
tuple if they shared one cache - and GPT-C2/C4/C6 similarly among
themselves. Isolation is achieved the same way it already is for Gemini:
each of the six GPT-C1..C6 cells gets its OWN fresh `OpenAIClient` AND
its own fresh `rrx.agent.llm_cache.LLMCache` instance, never shared or
merged - no change to the frozen `CacheKey` shape. Prompt `disclosure`
(low/high), by contrast, changes the rendered prompt text itself and
therefore the `prompt_hash` - if implemented with two distinct
`template_version` strings (see `rrx.agent.prompt`), that axis is
already correctly distinguished by the existing frozen cache key, with
no extra isolation needed.

Cost accounting - a DELIBERATE, FLAGGED divergence from `gemini_client.py`:
`self.cost_inr` stays `0.0` after every call here too, but NOT for the
same reason as Gemini. Gemini's `cost_inr=0.0` reflects genuine Free
Tier reality - nothing is charged. `gpt-5-mini` is a PAID model - real
money is spent on every call this adapter makes. `cost_inr` is pinned to
`0.0` anyway ONLY because the frozen `LedgerRecord.cost` field's
documented unit is INR (`docs/A3-DESIGN.md §14`: "₹ (EVAL.md §5.1)"),
this project has no authorized USD->INR conversion rate anywhere, and
inventing one to populate this field would be exactly the kind of
fabricated pricing constant this project's discipline forbids. The
correctly-denominated, real quantity - `estimated_paid_equivalent_usd`
below - is real spend for OpenAI (not a paid-tier hypothetical the way
it is for Gemini), computed in USD from officially published rates,
deliberately kept OUT of the `cost`/`cost_inr` ledger field rather than
silently mislabeling a USD figure as INR. This is a genuine, unresolved
methodological gap (flagged, not fixed, by this module) - anyone reading
GPT-C1..C6 ledger data must compute actual USD spend from
`estimated_paid_equivalent_usd(tokens_in, tokens_out)` themselves; the
ledger's own `cost` column will silently read `0.0` for every GPT tick,
which is NOT the same as "this call was free."

Quota/rate-limit: `openai.RateLimitError` (HTTP 429) is re-raised as
`OpenAIQuotaExhaustedError`, deliberately a DIFFERENT exception from
`rrx.agent.planner.PlannerTimeoutError` - `invoke_planner` only catches
`PlannerTimeoutError` around `client.complete(...)`, so a quota exception
propagates all the way out of `run_episode_a3` and stops whatever script
is driving it, exactly mirroring `GeminiQuotaExhaustedError`'s behavior
(Day 6 Stage 6D/6E). Every OTHER `openai.APIError` (timeout, connection
error, 5xx, any transport problem - including `openai.APITimeoutError`,
a subclass of `APIConnectionError`/`APIError`, so it is caught by the
same branch) is re-raised as `PlannerTimeoutError` - the frozen 5-value
fallback taxonomy has no separate "transport error" category and this
module does not invent one.

No retry loop exists anywhere in this module's OWN code - one call, one
result or one raised exception. Day 6 Stage 6R: this claim used to be
true only of this module's code, not of the FULL effective behavior -
the `openai` SDK's own defaults (`max_retries=2`, 600s read timeout,
`openai._constants.DEFAULT_TIMEOUT`/`DEFAULT_MAX_RETRIES`) let a single
`client.complete()` call silently attempt the request up to 3 times
internally, invisible above the SDK boundary. Found via a live GPT-C6 run
that produced individual recorded latencies of 35, 49, and 77 real
minutes before this fix. `OpenAI(timeout=60.0, max_retries=0)` now makes
the "one call, one attempt" claim true end to end: `max_retries=0`
disables the SDK's internal retries entirely, and `timeout=60.0` bounds
worst-case wait time to a value chosen from this experiment's own
observed data (the five GPT cells that completed before this fix had
per-call max latencies of 16.3s/8.6s/27.2s/21.6s/19.7s - none exceeded
30s - so 60s is a real, evidence-based margin, not an arbitrary guess).

The `openai` package is imported LOCALLY, inside `complete()`, not at
module top level - importing this module for its constants
(`PINNED_MODEL`, `RESPONSE_FORMAT`, `estimated_paid_equivalent_usd`,
etc.) never requires the `openai` package to be installed; only actually
calling `.complete()` does.
"""

from __future__ import annotations

from rrx.agent.planner import PlannerTimeoutError
from rrx.agent.reason_codes import REASON_CODES

PINNED_PROVIDER = "openai"
PINNED_MODEL = "gpt-5-mini"
# results/tuning_log.md Entry 2: fixed at "low" across all six GPT-C1..C6
# cells - not an experimental factor. Not a constructor parameter of
# OpenAIClient below, by design (see module docstring).
PINNED_VERBOSITY = "low"

_ACTION_TYPES = ("CONTACT", "WAIT", "STOP")
_REMEDIES = ("card_change", "topup_reminder")

# Mirrors §11's exact 4-key output schema and gemini_client.py's
# RESPONSE_JSON_SCHEMA, adapted to OpenAI's Structured Outputs request
# shape (response_format={"type": "json_schema", "json_schema": {...}}).
# Uses the project's REAL frozen enum values - the Stage 6G.1 empirical
# probe (gpt_probe.py) used placeholder enum values, corrected in
# `results/tuning_log.md` Entry 2; this is the actual schema. NOT
# authoritative on its own (Day 6 Stage 6D/6I): every response, structured
# or not, still passes through rrx.agent.planner.parse_llm_output
# unchanged - this module never bypasses or duplicates that parser.
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "action_type": {"type": "string", "enum": list(_ACTION_TYPES)},
        "remedy": {
            "anyOf": [{"type": "string", "enum": list(_REMEDIES)}, {"type": "null"}]
        },
        "reason_code": {"type": "string", "enum": sorted(REASON_CODES)},
        "rationale": {"type": "string"},
    },
    "required": ["action_type", "remedy", "reason_code", "rationale"],
    "additionalProperties": False,
}

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "a3_llm_proposal",
        "strict": True,
        "schema": _RESPONSE_SCHEMA,
    },
}

# CITE (developers.openai.com/api/docs/models/gpt-5-mini, retrieved
# 2026-08-28): $0.25 / 1M input tokens, $2.00 / 1M output tokens. Used
# ONLY by estimated_paid_equivalent_usd below - never actual spend, never
# written into configs/costs.yaml (unchanged, still a placeholder).
_PAID_TIER_INPUT_USD_PER_1M_TOKENS = 0.25
_PAID_TIER_OUTPUT_USD_PER_1M_TOKENS = 2.00

# results/tuning_log.md Entry 2's frozen matrix uses minimal/low/medium
# only - "high" is included here because it is a real, valid API value
# (Day 6 Stage 6G confirmed this), not because any GPT-C1..C6 cell uses
# it. OpenAIClient validates against this full set, not just the three
# the frozen matrix happens to use, so a construction-time typo is
# caught regardless of which cell is being built.
_VALID_REASONING_EFFORTS = frozenset({"minimal", "low", "medium", "high"})


class OpenAIQuotaExhaustedError(Exception):
    """HTTP 429 (`openai.RateLimitError`). See module docstring -
    deliberately NOT a PlannerTimeoutError, so it is never caught as a
    per-tick fallback; it propagates and stops the run."""


def estimated_paid_equivalent_usd(tokens_in: int | None, tokens_out: int | None) -> float | None:
    """The USD cost of a call with the given token counts, from the
    officially published rates above - NOT actual spend. Returns None if
    either token count is unavailable, rather than fabricating a partial
    estimate."""
    if tokens_in is None or tokens_out is None:
        return None
    return (
        tokens_in / 1_000_000 * _PAID_TIER_INPUT_USD_PER_1M_TOKENS
        + tokens_out / 1_000_000 * _PAID_TIER_OUTPUT_USD_PER_1M_TOKENS
    )


class OpenAIClient:
    """Implements `rrx.agent.planner.LLMClient`. Mutable (unlike the
    frozen `StubLLMClient`) because a real call's `tokens_in`/
    `tokens_out`/`cost_inr` differ every time and must be read by
    `invoke_planner` via `getattr(client, "tokens_in"/"tokens_out"/
    "cost_inr", ...)` immediately after each `complete()` call - the same
    mechanism `GeminiClient` already uses. Not thread-safe / not
    re-entrant, matching sim-v1's single-threaded, one-call-at-a-time day
    loop exactly - no stronger guarantee is needed or provided.

    One instance = one fixed `reasoning_effort` for its whole lifetime -
    matching how each of GPT-C1..C6 is a fixed configuration, not a
    per-call choice."""

    def __init__(self, *, reasoning_effort: str) -> None:
        if reasoning_effort not in _VALID_REASONING_EFFORTS:
            raise ValueError(
                f"reasoning_effort must be one of {sorted(_VALID_REASONING_EFFORTS)}, "
                f"got {reasoning_effort!r}"
            )
        self.reasoning_effort = reasoning_effort
        self.tokens_in: int | None = None
        self.tokens_out: int | None = None
        self.cost_inr: float = 0.0  # actual spend - never estimated cost, see module docstring

    def complete(self, prompt: str, *, model: str, temperature: float) -> str:
        # `temperature` is part of LLMClient's Protocol (and feeds
        # rrx.agent.llm_cache.CacheKey's temperature field, which this
        # module has no say over) but is deliberately NEVER forwarded to
        # the OpenAI API - see module docstring's temperature section.
        del temperature

        from openai import APIError as OpenAIAPIError
        from openai import OpenAI, RateLimitError

        self.tokens_in = None
        self.tokens_out = None
        self.cost_inr = 0.0

        # Day 6 Stage 6R: explicit, bounded transport configuration -
        # found necessary after a live GPT-C6 run observed individual
        # calls taking 35/49/77 real minutes. The `openai` SDK's own
        # UNDOCUMENTED-at-this-module's-level defaults
        # (openai._constants.DEFAULT_TIMEOUT = 600s read timeout,
        # DEFAULT_MAX_RETRIES = 2) let a single client.complete() call
        # silently attempt the request up to 3 times internally, entirely
        # invisible above this line - this module's own "no retry loop"
        # claim was true of ITS code, not of the full effective behavior.
        # max_retries=0 makes that claim true end to end: exactly one
        # transport attempt, ever. timeout=60.0s is chosen from the
        # actual observed data across the five GPT cells that completed
        # normally before this fix (C1-C5 max latencies: 16.3s / 8.6s /
        # 27.2s / 21.6s / 19.7s - none exceeded 30s) - roughly 2x the
        # largest genuine observed max, comfortably bounding worst-case
        # wait time while not truncating any response shape actually seen
        # in this experiment.
        # Reads OPENAI_API_KEY from env; never read here.
        client = OpenAI(timeout=60.0, max_retries=0)
        try:
            # `prompt` is exactly what render_prompt produced - unmodified.
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                reasoning_effort=self.reasoning_effort,
                verbosity=PINNED_VERBOSITY,
                response_format=RESPONSE_FORMAT,
            )
        except RateLimitError as e:
            raise OpenAIQuotaExhaustedError(
                f"OpenAI quota/rate-limit exhausted "
                f"(status_code={getattr(e, 'status_code', None)}): {e}"
            ) from e
        except OpenAIAPIError as e:
            raise PlannerTimeoutError(f"OpenAI API error: {e}") from e

        usage = getattr(response, "usage", None)
        if usage is not None:
            self.tokens_in = getattr(usage, "prompt_tokens", None)
            self.tokens_out = getattr(usage, "completion_tokens", None)

        message = response.choices[0].message
        if message.content is None:
            # Structured Outputs refusal (message.refusal set instead of
            # content) or otherwise empty completion - no valid JSON was
            # produced. Returned as-is, never fabricated into fake valid
            # JSON: rrx.agent.planner.parse_llm_output classifies whatever
            # comes back through json.loads exactly as it does any other
            # malformed response (typically "unparseable") - no new
            # fallback reason invented here.
            return getattr(message, "refusal", None) or ""

        return message.content
