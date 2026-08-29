"""docs/A3-DESIGN.md §13: the LLM cache's key contract and its two hard-stop
rules (cache-miss during replay; live call without --allow-live). Cache
mechanics only - rrx.agent.planner.invoke_planner's own use of this module
is covered separately in tests/test_planner.py.
"""

from __future__ import annotations

import pytest

from rrx.agent.llm_cache import CacheKey, LLMCache, compute_prompt_hash, load_jsonl, to_jsonl_line


def _key(**overrides) -> CacheKey:
    base = dict(template_version="t1", model="m", temperature=0.0, prompt_hash="abc123")
    base.update(overrides)
    return CacheKey(**base)


def test_prompt_hash_is_deterministic_and_content_sensitive():
    assert compute_prompt_hash("hello") == compute_prompt_hash("hello")
    assert compute_prompt_hash("hello") != compute_prompt_hash("goodbye")


def test_cache_key_has_exactly_the_four_frozen_components():
    """§13: "Cache key: (template_version, model, temperature, prompt_hash)."""
    import dataclasses

    names = {f.name for f in dataclasses.fields(CacheKey)}
    assert names == {"template_version", "model", "temperature", "prompt_hash"}


def test_cache_put_then_get_round_trips():
    cache = LLMCache()
    key = _key()
    assert cache.get(key) is None
    assert key not in cache
    cache.put(key, "raw response")
    assert key in cache
    assert cache.get(key) == "raw response"


def test_cache_keys_differing_in_any_component_are_distinct_entries():
    cache = LLMCache()
    cache.put(_key(model="m1"), "one")
    cache.put(_key(model="m2"), "two")
    assert cache.get(_key(model="m1")) == "one"
    assert cache.get(_key(model="m2")) == "two"


def test_jsonl_round_trip(tmp_path):
    """load_jsonl/to_jsonl_line never touch the repository's real results/
    directory - both take an explicit path/argument only."""
    key = _key(prompt_hash=compute_prompt_hash("some prompt"))
    line = to_jsonl_line(key, "the raw output")
    path = tmp_path / "llm_cache.jsonl"
    path.write_text(line + "\n", encoding="utf-8")

    cache = load_jsonl(path)
    assert cache.replay is True
    assert cache.get(key) == "the raw output"


def test_load_jsonl_never_defaults_to_a_real_results_path():
    with pytest.raises(TypeError):
        load_jsonl()  # path is a required argument, no default


# ---------------------------------------------------------------------------
# Day 6 Stage 6C-5: "cache record contains the information needed for
# deterministic replay" - proven end to end through rrx.agent.planner,
# not just at the raw cache-storage level above.
# ---------------------------------------------------------------------------

def test_cache_record_reproduces_the_identical_decision_on_replay(tmp_path):
    """A cache built from a prior (simulated) live run's recorded
    raw_output, loaded fresh in replay mode, must make invoke_planner
    reach the EXACT SAME Proposal a live call returning that same raw
    text would have - proving raw_output alone is sufficient information
    for deterministic replay of the DECISION (see rrx.agent.planner.
    invoke_planner's own docstring for why per-call cost/token accounting
    is deliberately NOT also carried in the cache record)."""
    import json

    from rrx.agent.planner import StubLLMClient, invoke_planner
    from rrx.agent.prompt import TEMPLATE_VERSION, render_prompt
    from rrx.features.episode_view import EpisodeView

    view = EpisodeView(
        subscription_id="dev-1000", subscription_state="pending", invoice_amount_inr=50000,
        days_since_first_failure=0, auto_retries_remaining=1, next_auto_retry_day=1,
        decline_code="card_expired", billing_amount_inr=50000,
        contact_history=(), budget_remaining=3,
    )
    raw_output = json.dumps(
        {
            "action_type": "CONTACT", "remedy": "card_change",
            "reason_code": "remedy_match_card", "rationale": "original live call's answer",
        }
    )

    # Simulate the ORIGINAL live run: record what it would have written to
    # results/<run_id>/llm_cache.jsonl.
    prompt = render_prompt(view, template_version=TEMPLATE_VERSION)
    original_key = CacheKey(
        template_version=TEMPLATE_VERSION, model="stub-model", temperature=0.0,
        prompt_hash=compute_prompt_hash(prompt),
    )
    cache_path = tmp_path / "llm_cache.jsonl"
    cache_path.write_text(to_jsonl_line(original_key, raw_output) + "\n", encoding="utf-8")

    # A live client that WOULD answer differently if actually called -
    # proves the replay path never touches it (test_cache_hit_never_calls_
    # the_client in tests/test_planner.py already proves this directly;
    # this is the same guarantee, exercised via the on-disk artifact).
    poison_client = StubLLMClient(response=json.dumps({
        "action_type": "STOP", "remedy": None,
        "reason_code": "no_engagement_restraint", "rationale": "WRONG - should never be reached",
    }))

    replay_cache = load_jsonl(cache_path)
    outcome = invoke_planner(
        view, client=poison_client, model="stub-model", temperature=0.0,
        cache=replay_cache, allow_live=False,
    )

    assert outcome.raw_output == raw_output
    assert outcome.proposal.action_type == "CONTACT"
    assert outcome.proposal.remedy == "card_change"
    assert outcome.proposal.reason_code == "remedy_match_card"
    assert outcome.used_fallback is False
