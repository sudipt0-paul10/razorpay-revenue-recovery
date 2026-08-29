"""Google Gemini Developer API live provider adapter (Day 6 Stage 6D).

Implements `rrx.agent.planner.LLMClient`'s Protocol
(`complete(prompt, *, model, temperature) -> str`) using `google-genai`,
the only currently-supported SDK (the older `google-generativeai` package
reached end-of-life 2025-11-30). This is the ONLY module in the
repository that imports `google.genai`, and the ONLY module anywhere in
`src/rrx` that performs network I/O - every other module stays
offline-safe by construction (see `tests/test_gemini_client_offline.py`'s
import-boundary check).

`google.genai` is imported LOCALLY, inside `complete()`, not at module
top level - importing THIS module (to read `PINNED_MODEL`,
`RESPONSE_JSON_SCHEMA`, `estimated_paid_equivalent_usd`, etc., all of
which offline tests need) never requires the `google-genai` package to be
installed; only actually calling `.complete()` does.

FREE TIER ONLY, by design, not just by account configuration:
- `PINNED_MODEL`/`PINNED_TEMPERATURE` below are this stage's ONLY
  configuration - one provider, one model, no tuning, no per-call drift.
- A quota/rate-limit response (HTTP 429 / `RESOURCE_EXHAUSTED`) raises
  `GeminiQuotaExhaustedError`, which is DELIBERATELY a distinct exception
  from `rrx.agent.planner.PlannerTimeoutError` - `invoke_planner` only
  catches `PlannerTimeoutError` around `client.complete(...)`, so a quota
  exception propagates all the way out of `run_episode_a3` and stops the
  calling script entirely. This is intentional: a quota condition means
  the whole session should halt, not silently keep burning fallback
  cycles against a rate-limited API on every remaining tick.
- No retry loop exists anywhere in this module. One call, one result or
  one raised exception - never retry-until-success, which could quietly
  turn a free-tier account into a paid one by hammering the API.
- Every OTHER API failure (timeout, connection error, 5xx, any transport
  problem) is re-raised as `PlannerTimeoutError` - `EVAL.md`/
  `docs/A3-DESIGN.md` §19's fallback taxonomy has no separate "transport
  error" category, and this module does not invent one (Day 6 Stage 6D,
  6D-6: "Do not invent new fallback reasons").

Cost accounting: the frozen `LedgerRecord.cost` field already means
"actually incurred spend" (A3-D's is always 0.0 because A3-D never calls
an LLM at all). For a free-tier Gemini call, `cost_inr` stays exactly
0.0, for the identical reason - nothing was actually charged. That is NOT
the same quantity as what the same call would have cost on the PAID tier;
`estimated_paid_equivalent_usd` below computes that second quantity
separately, from officially published per-token rates, and is never
written into `LedgerRecord.cost` - doing so would conflate two different
numbers inside one frozen field. No ledger schema change was needed or
made to keep these separate; the existing `tokens_in`/`tokens_out`
columns already carry everything the estimate needs, so it is computed
from ledger data after the fact, not stored per-tick.
"""

from __future__ import annotations

from rrx.agent.planner import PlannerTimeoutError
from rrx.agent.reason_codes import REASON_CODES

# --- Day 6 Stage 6D-2: the pinned configuration. Exactly one provider,
# one model, one temperature - no alternates, no sweep, no tuning. ---
PINNED_PROVIDER = "google"
PINNED_MODEL = "gemini-3.1-flash-lite"
# CITE (2026-08-28, ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite):
# confirmed stable/GA, not preview, not deprecated; supports
# response_mime_type="application/json" + response_json_schema.
PINNED_TEMPERATURE = 0.0  # the most-deterministic setting the API exposes

_ACTION_TYPES = ("CONTACT", "WAIT", "STOP")
_REMEDIES = ("card_change", "topup_reminder")

# Mirrors §11's exact 4-key output schema (rrx.agent.planner._REQUIRED_KEYS).
# Requested from the model as a courtesy to reduce wasted free-tier calls -
# NOT authoritative (Day 6 Stage 6D, 6D-4): every response, structured or
# not, still passes through rrx.agent.planner.parse_llm_output unchanged.
RESPONSE_JSON_SCHEMA = {
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
}

# CITE (2026-08-28, ai.google.dev/gemini-api/docs/pricing, gemini-3.1-flash-lite
# standard paid tier): $0.25 / 1M input tokens (text), $1.50 / 1M output
# tokens. Used ONLY by estimated_paid_equivalent_usd below - never written
# into configs/costs.yaml (still an untouched placeholder) and never
# treated as actual spend.
_PAID_TIER_INPUT_USD_PER_1M_TOKENS = 0.25
_PAID_TIER_OUTPUT_USD_PER_1M_TOKENS = 1.50


class GeminiQuotaExhaustedError(Exception):
    """HTTP 429 / RESOURCE_EXHAUSTED. See module docstring - deliberately
    NOT a PlannerTimeoutError, so it is never caught as a per-tick
    fallback; it propagates and stops the run."""


def estimated_paid_equivalent_usd(tokens_in: int | None, tokens_out: int | None) -> float | None:
    """The paid-tier-equivalent USD cost of a call with the given token
    counts, from the officially published rates above - NOT actual spend
    (this account is Free Tier; actual spend is 0.0). Returns None if
    either token count is unavailable, rather than fabricating a partial
    estimate."""
    if tokens_in is None or tokens_out is None:
        return None
    return (
        tokens_in / 1_000_000 * _PAID_TIER_INPUT_USD_PER_1M_TOKENS
        + tokens_out / 1_000_000 * _PAID_TIER_OUTPUT_USD_PER_1M_TOKENS
    )


class GeminiClient:
    """Implements `rrx.agent.planner.LLMClient`. Mutable (unlike the
    frozen `StubLLMClient`) because a real call's `tokens_in`/
    `tokens_out`/`cost_inr` differ every time and must be read by
    `invoke_planner` via `getattr(client, "tokens_in"/"tokens_out"/
    "cost_inr", ...)` immediately after each `complete()` call - the same
    mechanism `StubLLMClient` uses with fixed values, here updated
    per-call. Not thread-safe / not re-entrant, matching sim-v1's
    single-threaded, one-call-at-a-time day loop exactly - no stronger
    guarantee is needed or provided."""

    def __init__(self, *, thinking_level: str | None = None) -> None:
        """`thinking_level` (Day 6 Stage 6E: `minimal`/`low`/`medium`/`high`)
        is a CONSTRUCTOR-time setting, not a `complete()` argument -
        `rrx.agent.planner.LLMClient`'s Protocol
        (`complete(prompt, *, model, temperature) -> str`) is unchanged,
        so this addition requires no change to `invoke_planner`,
        `A3LLMPolicy`, or anything else in `planner.py`. One `GeminiClient`
        instance = one fixed `thinking_level` for its whole lifetime -
        exactly matching how each of C1-C6 (`results/tuning_log.md`) is a
        fixed configuration, not a per-call choice. `None` omits the
        parameter entirely (API default applies)."""
        self.thinking_level = thinking_level
        self.tokens_in: int | None = None
        self.tokens_out: int | None = None
        self.cost_inr: float = 0.0  # Free Tier: always 0.0, always - see module docstring

    def complete(self, prompt: str, *, model: str, temperature: float) -> str:
        from google import genai
        from google.genai import errors, types

        self.tokens_in = None
        self.tokens_out = None
        self.cost_inr = 0.0

        config_kwargs: dict = {
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_json_schema": RESPONSE_JSON_SCHEMA,
        }
        if self.thinking_level is not None:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self.thinking_level
            )

        client = genai.Client()  # reads GEMINI_API_KEY / GOOGLE_API_KEY from env; never read here
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,  # exactly what render_prompt produced - unmodified
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except errors.APIError as e:
            code = getattr(e, "code", None)
            message = str(getattr(e, "message", e) or e)
            if code == 429 or "RESOURCE_EXHAUSTED" in message.upper():
                raise GeminiQuotaExhaustedError(
                    f"Gemini quota/rate-limit exhausted (code={code}): {message}"
                ) from e
            raise PlannerTimeoutError(f"Gemini API error (code={code}): {message}") from e

        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            # Field names vary across SDK/doc revisions (input_tokens vs
            # prompt_token_count) - try the known variants, record
            # unavailable rather than guessing (Day 6 Stage 6D, 6D-9).
            self.tokens_in = getattr(usage, "input_tokens", None) or getattr(
                usage, "prompt_token_count", None
            )
            self.tokens_out = getattr(usage, "output_tokens", None) or getattr(
                usage, "candidates_token_count", None
            )

        return response.text
