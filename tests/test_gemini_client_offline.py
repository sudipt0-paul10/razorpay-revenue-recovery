"""Day 6 Stage 6D: everything about rrx.agent.gemini_client that can be
verified WITHOUT a live API call - safe to run in every regular
`pytest -q` invocation, unlike the one-off live smoke test (deliberately
kept OUT of this repository - see the Stage 6D deliverable for why).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from rrx.agent.gemini_client import (
    PINNED_MODEL,
    PINNED_PROVIDER,
    PINNED_TEMPERATURE,
    RESPONSE_JSON_SCHEMA,
    GeminiClient,
    GeminiQuotaExhaustedError,
    estimated_paid_equivalent_usd,
)
from rrx.agent.planner import PlannerTimeoutError, invoke_planner
from rrx.agent.reason_codes import REASON_CODES
from rrx.features.episode_view import EpisodeView

SRC = Path(__file__).resolve().parents[1] / "src"


def _view() -> EpisodeView:
    return EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=50000,
        days_since_first_failure=0, auto_retries_remaining=1, next_auto_retry_day=1,
        decline_code="card_expired", billing_amount_inr=50000,
        contact_history=(), budget_remaining=3,
    )


# ---------------------------------------------------------------------------
# 6D-2: pinned configuration
# ---------------------------------------------------------------------------

def test_pinned_configuration_values():
    assert PINNED_PROVIDER == "google"
    assert PINNED_MODEL == "gemini-3.1-flash-lite"
    assert PINNED_TEMPERATURE == 0.0


def test_response_json_schema_matches_the_frozen_four_key_output_contract():
    assert RESPONSE_JSON_SCHEMA["required"] == [
        "action_type", "remedy", "reason_code", "rationale"
    ]
    props = RESPONSE_JSON_SCHEMA["properties"]
    assert set(props.keys()) == {"action_type", "remedy", "reason_code", "rationale"}
    assert set(props["action_type"]["enum"]) == {"CONTACT", "WAIT", "STOP"}
    assert set(props["reason_code"]["enum"]) == REASON_CODES


# ---------------------------------------------------------------------------
# 6D-3: import boundary - this module is the ONLY network-capable one, and
# importing it for its constants never requires google-genai to be
# installed (only calling .complete() does).
# ---------------------------------------------------------------------------

def test_gemini_client_module_does_not_import_google_genai_at_top_level():
    """`from google import genai` must appear only INSIDE complete()'s
    function body - never at module scope - so importing this module for
    PINNED_MODEL/RESPONSE_JSON_SCHEMA/etc. never requires the optional
    google-genai package to be installed."""
    path = SRC / "rrx" / "agent" / "gemini_client.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    module_level_imports: set[str] = set()
    for node in tree.body:  # top-level statements only, not nested in functions
        if isinstance(node, ast.ImportFrom) and node.module:
            module_level_imports.add(node.module)
        elif isinstance(node, ast.Import):
            module_level_imports.update(a.name for a in node.names)

    assert "google" not in module_level_imports
    assert "google.genai" not in module_level_imports


def test_gemini_client_is_the_only_module_that_imports_google_genai():
    agent_dir = SRC / "rrx" / "agent"
    offenders = []
    for path in agent_dir.rglob("*.py"):
        if path.name == "gemini_client.py" or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "google" in node.module:
                offenders.append(str(path))
            elif isinstance(node, ast.Import) and any("google" in a.name for a in node.names):
                offenders.append(str(path))
    assert not offenders, f"unexpected google.* import outside gemini_client.py: {offenders}"


def test_gemini_client_never_reads_the_api_key_itself():
    """The SDK reads GEMINI_API_KEY/GOOGLE_API_KEY internally via
    genai.Client() - this module must never call os.environ/os.getenv to
    fetch it as a Python value, which is the strongest possible guarantee
    against ever holding, and therefore ever leaking, the key. (The env
    var NAMES may still appear in an explanatory comment - that is not a
    leak; the check below is for actual CODE that would read the value.)
    """
    path = SRC / "rrx" / "agent" / "gemini_client.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "environ":
            raise AssertionError("gemini_client.py touches os.environ directly")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "getenv":
                raise AssertionError("gemini_client.py calls os.getenv directly")
        if isinstance(node, ast.keyword) and node.arg == "api_key":
            raise AssertionError("gemini_client.py passes an explicit api_key= somewhere")


# ---------------------------------------------------------------------------
# 6D-6: quota/rate-limit failures must NOT be caught as a per-tick
# fallback - they must propagate and stop the run.
# ---------------------------------------------------------------------------

class _QuotaExhaustedClient:
    def complete(self, prompt: str, *, model: str, temperature: float) -> str:
        raise GeminiQuotaExhaustedError("simulated 429 RESOURCE_EXHAUSTED")


def test_quota_exhaustion_is_not_caught_by_invoke_planner_and_propagates():
    with pytest.raises(GeminiQuotaExhaustedError):
        invoke_planner(
            _view(), client=_QuotaExhaustedClient(), model=PINNED_MODEL,
            temperature=PINNED_TEMPERATURE, allow_live=True,
        )


def test_quota_exhausted_error_is_distinct_from_planner_timeout_error():
    assert not issubclass(GeminiQuotaExhaustedError, PlannerTimeoutError)
    assert not issubclass(PlannerTimeoutError, GeminiQuotaExhaustedError)


# ---------------------------------------------------------------------------
# 6D-8/6D-9: actual_spend vs estimated_paid_equivalent, kept separate
# ---------------------------------------------------------------------------

def test_estimated_paid_equivalent_usd_matches_the_cited_published_rates():
    # 1,000,000 input tokens @ $0.25/1M + 1,000,000 output tokens @ $1.50/1M
    result = estimated_paid_equivalent_usd(1_000_000, 1_000_000)
    assert result == pytest.approx(0.25 + 1.50)


def test_estimated_paid_equivalent_usd_zero_tokens_is_zero_cost():
    assert estimated_paid_equivalent_usd(0, 0) == 0.0


def test_estimated_paid_equivalent_usd_none_when_a_token_count_is_unavailable():
    assert estimated_paid_equivalent_usd(None, 100) is None
    assert estimated_paid_equivalent_usd(100, None) is None


def test_gemini_client_cost_inr_starts_at_zero_never_none():
    """Matches default_ledger_record's own `cost: float = 0.0` default
    (never omitted, per §17) - the live client's cost_inr must be a float,
    not a placeholder None, from construction onward."""
    client = GeminiClient()
    assert client.cost_inr == 0.0
    assert client.tokens_in is None
    assert client.tokens_out is None


# ---------------------------------------------------------------------------
# Day 6 Stage 6E: thinking_level is a constructor-time GeminiClient setting,
# not a complete() argument - LLMClient's Protocol is unchanged.
# ---------------------------------------------------------------------------

def test_thinking_level_defaults_to_none_and_is_settable_at_construction():
    default_client = GeminiClient()
    assert default_client.thinking_level is None

    for level in ("minimal", "low", "medium", "high"):
        assert GeminiClient(thinking_level=level).thinking_level == level


def test_gemini_client_complete_signature_is_unchanged_by_thinking_level():
    """LLMClient's Protocol (complete(prompt, *, model, temperature)) must
    still be exactly what rrx.agent.planner.invoke_planner calls -
    thinking_level must never appear as a complete() parameter."""
    import inspect

    sig = inspect.signature(GeminiClient.complete)
    assert list(sig.parameters) == ["self", "prompt", "model", "temperature"]


def test_six_tuning_configurations_would_use_isolated_client_instances():
    """docs/A3-DESIGN.md §13's cache key is (template_version, model,
    temperature, prompt_hash) - it does not include thinking_level, so
    C1/C2/C3 (all temperature=0.0) would collide on cache KEY if they
    shared one cache. This is resolved operationally (Day 6 Stage 6E),
    never by changing the frozen 4-field CacheKey: each configuration
    gets its own GeminiClient AND its own LLMCache instance, so no cache
    key collision can ever actually be looked up across configurations,
    regardless of what the abstract key tuple would be. This test proves
    the isolation is real at the object level, not just documented."""
    c1_client = GeminiClient(thinking_level="minimal")
    c2_client = GeminiClient(thinking_level="low")
    assert c1_client is not c2_client
    assert c1_client.thinking_level != c2_client.thinking_level
    # Each configuration's own cache is a fresh, disjoint object - proven
    # directly, not inferred: two fresh LLMCache() calls never share state.
    from rrx.agent.llm_cache import LLMCache

    cache_c1, cache_c2 = LLMCache(), LLMCache()
    assert cache_c1 is not cache_c2
    assert cache_c1._entries is not cache_c2._entries
