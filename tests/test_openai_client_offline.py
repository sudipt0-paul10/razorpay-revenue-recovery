"""Day 6 Stage 6I: everything about rrx.agent.openai_client that can be
verified WITHOUT a live API call. Mirrors tests/test_gemini_client_offline.py's
structure and rigor - construction/configuration, structured-output schema
correctness, mocked API invocation, error-propagation behavior, and
response extraction.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest

from rrx.agent.llm_cache import LLMCache
from rrx.agent.openai_client import (
    PINNED_MODEL,
    PINNED_PROVIDER,
    PINNED_VERBOSITY,
    RESPONSE_FORMAT,
    OpenAIClient,
    OpenAIQuotaExhaustedError,
    estimated_paid_equivalent_usd,
)
from rrx.agent.planner import PlannerTimeoutError

SRC = Path(__file__).resolve().parents[1] / "src"


def _fake_response(content: str | None, *, refusal: str | None = None,
                    prompt_tokens: int = 10, completion_tokens: int = 5):
    message = MagicMock()
    message.content = content
    message.refusal = refusal
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return response


def _http_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


# ---------------------------------------------------------------------------
# Construction / configuration
# ---------------------------------------------------------------------------

def test_pinned_configuration_values():
    assert PINNED_PROVIDER == "openai"
    assert PINNED_MODEL == "gpt-5-mini"
    assert PINNED_VERBOSITY == "low"


def test_reasoning_effort_is_set_at_construction_and_stored():
    for level in ("minimal", "low", "medium", "high"):
        assert OpenAIClient(reasoning_effort=level).reasoning_effort == level


def test_reasoning_effort_rejects_an_unknown_value():
    with pytest.raises(ValueError):
        OpenAIClient(reasoning_effort="not-a-real-level")


def test_verbosity_is_not_a_constructor_parameter():
    """Fixed at "low" for every cell (results/tuning_log.md Entry 2) -
    structurally non-configurable, not merely defaulted, so there is no
    way to accidentally vary it per GPT-C1..C6 cell."""
    sig = inspect.signature(OpenAIClient.__init__)
    assert "verbosity" not in sig.parameters


def test_complete_signature_matches_llm_client_protocol():
    sig = inspect.signature(OpenAIClient.complete)
    assert list(sig.parameters) == ["self", "prompt", "model", "temperature"]


def test_client_starts_with_no_token_or_cost_data():
    client = OpenAIClient(reasoning_effort="minimal")
    assert client.tokens_in is None
    assert client.tokens_out is None
    assert client.cost_inr == 0.0


def test_six_gpt_cells_would_use_isolated_client_and_cache_instances():
    """reasoning_effort is not part of the frozen (template_version,
    model, temperature, prompt_hash) cache key - isolation must come from
    separate client/cache OBJECTS per cell, mirroring the strategy already
    established for Gemini's thinking_level."""
    c_minimal = OpenAIClient(reasoning_effort="minimal")
    c_low = OpenAIClient(reasoning_effort="low")
    assert c_minimal is not c_low
    assert c_minimal.reasoning_effort != c_low.reasoning_effort

    cache_a, cache_b = LLMCache(), LLMCache()
    assert cache_a is not cache_b
    assert cache_a._entries is not cache_b._entries


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

def test_response_format_requests_strict_json_schema():
    assert RESPONSE_FORMAT["type"] == "json_schema"
    assert RESPONSE_FORMAT["json_schema"]["strict"] is True


def test_response_format_schema_uses_the_projects_real_enum_values():
    """Stage 6H's correction: the Stage 6G.1 probe (gpt_probe.py) used
    placeholder enum values (retry/hold/stop, etc.) - this is the actual,
    real, frozen schema, matching rrx.agent.reason_codes exactly."""
    from rrx.agent.reason_codes import REASON_CODES

    schema = RESPONSE_FORMAT["json_schema"]["schema"]
    props = schema["properties"]

    assert set(props["action_type"]["enum"]) == {"CONTACT", "WAIT", "STOP"}

    remedy_options = props["remedy"]["anyOf"]
    remedy_enum = next(o["enum"] for o in remedy_options if "enum" in o)
    assert set(remedy_enum) == {"card_change", "topup_reminder"}
    assert any(o.get("type") == "null" for o in remedy_options)

    assert set(props["reason_code"]["enum"]) == REASON_CODES
    assert schema["required"] == ["action_type", "remedy", "reason_code", "rationale"]
    assert schema["additionalProperties"] is False


# ---------------------------------------------------------------------------
# API invocation (mocked - no network)
# ---------------------------------------------------------------------------

_VALID_WAIT_JSON = (
    '{"action_type": "WAIT", "remedy": null, '
    '"reason_code": "retry_window_open", "rationale": "x"}'
)


def test_complete_sends_the_correct_request_shape():
    client = OpenAIClient(reasoning_effort="medium")
    raw = _VALID_WAIT_JSON
    fake = _fake_response(raw)

    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake
        result = client.complete("PROMPT TEXT", model=PINNED_MODEL, temperature=1.0)

    create = mock_cls.return_value.chat.completions.create
    create.assert_called_once()
    _, kwargs = create.call_args
    assert kwargs["model"] == PINNED_MODEL
    assert kwargs["reasoning_effort"] == "medium"
    assert kwargs["verbosity"] == "low"
    assert "temperature" not in kwargs
    assert kwargs["response_format"] == RESPONSE_FORMAT
    assert kwargs["messages"] == [{"role": "user", "content": "PROMPT TEXT"}]
    assert result == raw


def test_client_constructed_with_explicit_bounded_timeout_and_zero_retries():
    """Day 6 Stage 6R: found necessary after a live GPT-C6 run observed
    individual calls taking 35/49/77 real minutes, traced to the openai
    SDK's own default max_retries=2 / 600s read timeout stacking up
    invisibly beneath a single client.complete() call. OpenAI() must now
    be constructed with an explicit, bounded timeout and max_retries=0 -
    every time, regardless of which cell/reasoning_effort is in use."""
    client = OpenAIClient(reasoning_effort="minimal")
    fake = _fake_response(_VALID_WAIT_JSON)

    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake
        client.complete("p", model=PINNED_MODEL, temperature=1.0)

    _, ctor_kwargs = mock_cls.call_args
    assert ctor_kwargs["max_retries"] == 0
    assert ctor_kwargs["timeout"] == 60.0
    assert ctor_kwargs["timeout"] < 600, "must be far below the SDK's own 600s default"


def test_complete_never_forwards_temperature_regardless_of_value_passed_in():
    """LLMClient's Protocol requires accepting temperature (invoke_planner
    always passes one for the cache key) - it must never reach the API,
    for any value, per the Stage 6G.1 empirical 400 finding."""
    client = OpenAIClient(reasoning_effort="low")
    fake = _fake_response(_VALID_WAIT_JSON)
    for temp in (0.0, 0.5, 1.0, 2.0):
        with patch("openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = fake
            client.complete("p", model=PINNED_MODEL, temperature=temp)
        _, kwargs = mock_cls.return_value.chat.completions.create.call_args
        assert "temperature" not in kwargs


def test_complete_extracts_token_usage_onto_the_client():
    client = OpenAIClient(reasoning_effort="low")
    fake = _fake_response("{}", prompt_tokens=42, completion_tokens=17)
    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake
        client.complete("p", model=PINNED_MODEL, temperature=1.0)
    assert client.tokens_in == 42
    assert client.tokens_out == 17
    assert client.cost_inr == 0.0  # see module docstring - deliberately never real INR spend


def test_complete_resets_stale_token_data_on_a_fresh_call():
    """A second call must not silently keep the first call's token
    counts if the second call's usage is unavailable."""
    client = OpenAIClient(reasoning_effort="low")
    fake1 = _fake_response("{}", prompt_tokens=42, completion_tokens=17)
    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake1
        client.complete("p", model=PINNED_MODEL, temperature=1.0)
    assert client.tokens_in == 42

    fake2 = _fake_response("{}")
    fake2.usage = None
    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake2
        client.complete("p", model=PINNED_MODEL, temperature=1.0)
    assert client.tokens_in is None
    assert client.tokens_out is None


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------

def test_complete_returns_the_raw_message_content_unmodified():
    client = OpenAIClient(reasoning_effort="minimal")
    raw = '{"action_type": "STOP", "remedy": null, "reason_code": "risk_flagged", "rationale": "y"}'
    fake = _fake_response(raw)
    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake
        result = client.complete("p", model=PINNED_MODEL, temperature=1.0)
    assert result == raw


def test_complete_handles_a_refusal_without_fabricating_valid_json():
    """content=None (Structured Outputs refusal) must not be turned into
    fake valid JSON - it is returned as-is (the refusal text, or empty
    string), and rrx.agent.planner.parse_llm_output classifies it exactly
    like any other malformed response."""
    client = OpenAIClient(reasoning_effort="minimal")
    fake = _fake_response(None, refusal="I cannot help with that.")
    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = fake
        result = client.complete("p", model=PINNED_MODEL, temperature=1.0)
    assert result == "I cannot help with that."

    from rrx.agent.planner import ParseFailure, parse_llm_output
    from rrx.features.episode_view import EpisodeView

    view = EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=1,
        days_since_first_failure=0, auto_retries_remaining=1, next_auto_retry_day=1,
        decline_code="card_expired", billing_amount_inr=1, contact_history=(), budget_remaining=3,
    )
    outcome = parse_llm_output(result, view)
    assert isinstance(outcome, ParseFailure)
    assert outcome.fallback_reason == "unparseable"


# ---------------------------------------------------------------------------
# Error behavior - quota/rate-limit must NOT become a silent fallback
# ---------------------------------------------------------------------------

def test_rate_limit_error_raises_openai_quota_exhausted_not_planner_timeout():
    client = OpenAIClient(reasoning_effort="minimal")
    request = _http_request()
    response = httpx.Response(429, request=request, json={"error": {"message": "quota exceeded"}})
    rate_limit_error = openai.RateLimitError("quota exceeded", response=response, body=None)

    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.side_effect = rate_limit_error
        with pytest.raises(OpenAIQuotaExhaustedError):
            client.complete("p", model=PINNED_MODEL, temperature=1.0)


def test_quota_exhausted_error_is_not_caught_by_invoke_planner():
    """The whole point of raising a DIFFERENT exception type than
    PlannerTimeoutError: invoke_planner only catches PlannerTimeoutError
    around client.complete(...), so this must propagate all the way out,
    exactly like GeminiQuotaExhaustedError."""
    from rrx.agent.planner import invoke_planner
    from rrx.features.episode_view import EpisodeView

    class _QuotaExhaustedStub:
        def complete(self, prompt, *, model, temperature):
            raise OpenAIQuotaExhaustedError("simulated 429")

    view = EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=1,
        days_since_first_failure=0, auto_retries_remaining=1, next_auto_retry_day=1,
        decline_code="card_expired", billing_amount_inr=1, contact_history=(), budget_remaining=3,
    )
    with pytest.raises(OpenAIQuotaExhaustedError):
        invoke_planner(
            view, client=_QuotaExhaustedStub(), model=PINNED_MODEL, temperature=1.0,
            allow_live=True,
        )


def test_quota_exhausted_error_is_distinct_from_planner_timeout_error():
    assert not issubclass(OpenAIQuotaExhaustedError, PlannerTimeoutError)
    assert not issubclass(PlannerTimeoutError, OpenAIQuotaExhaustedError)


def test_generic_api_error_maps_to_planner_timeout_error():
    """Every OTHER openai.APIError (transport failure, timeout, 5xx) -
    the frozen fallback taxonomy has no separate "transport error"
    category, so this maps to the existing "timeout" fallback_reason via
    PlannerTimeoutError, exactly mirroring gemini_client.py."""
    client = OpenAIClient(reasoning_effort="minimal")
    request = _http_request()
    connection_error = openai.APIConnectionError(message="connection failed", request=request)

    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.side_effect = connection_error
        with pytest.raises(PlannerTimeoutError):
            client.complete("p", model=PINNED_MODEL, temperature=1.0)


def test_api_timeout_error_specifically_maps_to_planner_timeout_error():
    """Day 6 Stage 6R: with max_retries=0 and an explicit bounded
    timeout, `openai.APITimeoutError` (a subclass of
    APIConnectionError/APIError) is exactly what the SDK now raises when
    a call exceeds the configured timeout - confirm this specific,
    now-more-likely-to-occur exception type still maps correctly, not
    just the generic connection-error case."""
    client = OpenAIClient(reasoning_effort="minimal")
    request = _http_request()
    timeout_error = openai.APITimeoutError(request=request)

    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.side_effect = timeout_error
        with pytest.raises(PlannerTimeoutError):
            client.complete("p", model=PINNED_MODEL, temperature=1.0)


def test_no_retry_loop_exists_in_complete():
    """A single API error must result in exactly one call attempt - no
    retry-until-success loop that could quietly turn into repeated paid
    calls."""
    client = OpenAIClient(reasoning_effort="minimal")
    request = _http_request()
    connection_error = openai.APIConnectionError(message="connection failed", request=request)

    with patch("openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.side_effect = connection_error
        with pytest.raises(PlannerTimeoutError):
            client.complete("p", model=PINNED_MODEL, temperature=1.0)
        assert mock_cls.return_value.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# Cost accounting
# ---------------------------------------------------------------------------

def test_estimated_paid_equivalent_usd_matches_the_cited_published_rates():
    # 1,000,000 input @ $0.25/1M + 1,000,000 output @ $2.00/1M
    assert estimated_paid_equivalent_usd(1_000_000, 1_000_000) == pytest.approx(0.25 + 2.00)


def test_estimated_paid_equivalent_usd_none_when_a_token_count_is_unavailable():
    assert estimated_paid_equivalent_usd(None, 100) is None
    assert estimated_paid_equivalent_usd(100, None) is None


# ---------------------------------------------------------------------------
# No live network call in this module's own import/dependency surface
# ---------------------------------------------------------------------------

def test_openai_client_module_does_not_import_openai_at_top_level():
    """`from openai import ...` must appear only INSIDE complete()'s
    function body - never at module scope - so importing this module for
    PINNED_MODEL/RESPONSE_FORMAT/etc. never requires the optional `openai`
    package to be installed."""
    path = SRC / "rrx" / "agent" / "openai_client.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    module_level_imports: set[str] = set()
    for node in tree.body:  # top-level statements only, not nested in functions
        if isinstance(node, ast.ImportFrom) and node.module:
            module_level_imports.add(node.module)
        elif isinstance(node, ast.Import):
            module_level_imports.update(a.name for a in node.names)

    assert "openai" not in module_level_imports


def test_openai_client_never_reads_the_api_key_itself():
    """The SDK reads OPENAI_API_KEY internally via OpenAI() - this module
    must never call os.environ/os.getenv for it, or pass an explicit
    api_key= - the strongest guarantee against ever holding, and
    therefore ever leaking, the key value."""
    path = SRC / "rrx" / "agent" / "openai_client.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "environ":
            raise AssertionError("openai_client.py touches os.environ directly")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "getenv":
                raise AssertionError("openai_client.py calls os.getenv directly")
        if isinstance(node, ast.keyword) and node.arg == "api_key":
            raise AssertionError("openai_client.py passes an explicit api_key= somewhere")
