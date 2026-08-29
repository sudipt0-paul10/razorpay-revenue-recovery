"""docs/A3-DESIGN.md §2 boundary invariant, extended to the planner: the
planner (like A3-D's policy) must receive exactly one positional argument
- an EpisodeView, never _EpisodeState, CohortEpisode, LatentState, or an
RNG object - and must never mutate it. Mirrors
tests/test_agent_boundary.py's pattern exactly, applied to a
make_a3_llm_policy-wrapped planner instead of a3d_policy.

Also proves the required Day 6 Decision 1 property end to end: dispatching
A3-LLM (here, always falling back to A3-D, since no valid LLM output is
ever fed in) through the EXISTING src/rrx/harness/runner.py, with ZERO
change to that file - the only integration point used is
run_episode_a3's existing `policy` parameter.

Always-fallback only (StubLLMClient never returns parseable output) -
this is a plumbing/boundary check, not the Stage 6C forced-failure parity
study (which is a separate, explicitly gated later stage).
"""

from __future__ import annotations

from rrx.agent.planner import StubLLMClient, invoke_planner, make_a3_llm_policy
from rrx.agent.policy import a3d_policy
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Matches tests/test_agent_boundary.py's own (non-exhaustive-by-design) set.
_LATENT_ATTRS = (
    "card_chargeable", "funds_available_from", "mandate_alive",
    "blocked_until", "channel_response_trait", "card_chargeable_at_opening",
)


def test_a3_llm_policy_receives_only_an_episode_view():
    calls: list[tuple[tuple, dict]] = []
    always_fails = StubLLMClient(response="not json")

    def spy_policy(*args, **kwargs):
        calls.append((args, kwargs))
        outcome = invoke_planner(
            args[0], client=always_fails, model="stub", temperature=0.0, allow_live=True,
        )
        return outcome.proposal

    for i in list(DEV_INDICES)[:50]:
        run_episode_a3(DEV_SPLIT, i, spy_policy, EPISODE_CFG, POPULATION_CFG)

    assert calls, "spy_policy was never invoked across 50 dev episodes"
    for args, kwargs in calls:
        assert len(args) == 1, f"planner received {len(args)} positional args, expected 1: {args}"
        assert not kwargs, f"planner received keyword args, expected none: {kwargs}"
        (view,) = args
        assert isinstance(view, EpisodeView)
        for attr in _LATENT_ATTRS:
            assert not hasattr(view, attr), f"EpisodeView leaked latent attribute {attr!r}"


def test_a3_llm_policy_does_not_mutate_the_view_it_receives():
    """EpisodeView is frozen+slots, so mutation is already impossible at
    the language level (tests/test_no_latent_leak.py proves this
    generically); this test documents the property at the planner's own
    call site rather than relying only on that inference."""
    always_fails = StubLLMClient(response="not json")
    seen: list[EpisodeView] = []

    def recording_policy(view: EpisodeView) -> Proposal:
        before = repr(view)
        outcome = invoke_planner(
            view, client=always_fails, model="stub", temperature=0.0, allow_live=True,
        )
        assert repr(view) == before, "EpisodeView repr changed across the planner call"
        seen.append(view)
        return outcome.proposal

    for i in list(DEV_INDICES)[:20]:
        run_episode_a3(DEV_SPLIT, i, recording_policy, EPISODE_CFG, POPULATION_CFG)

    assert seen


def test_a3_llm_via_existing_runner_matches_a3d_wakeup_decisions_when_always_falling_back():
    """Since the injected client never produces parseable output, every
    wakeup-tick decision must be A3-D's own - proving the fallback path
    reproduces A3-D exactly when run through the unmodified existing
    runner, end to end, over real dev episodes (not just synthetic
    views)."""
    always_fails = StubLLMClient(response="not json")

    llm_decisions: list[Proposal] = []

    def a3_llm_spy(view: EpisodeView) -> Proposal:
        outcome = invoke_planner(
            view, client=always_fails, model="stub", temperature=0.0, allow_live=True,
        )
        llm_decisions.append(outcome.proposal)
        assert outcome.proposal == a3d_policy(view)
        return outcome.proposal

    for i in list(DEV_INDICES)[:100]:
        run_episode_a3(DEV_SPLIT, i, a3_llm_spy, EPISODE_CFG, POPULATION_CFG)

    assert llm_decisions, "no wakeup ticks occurred across 100 dev episodes"


def test_make_a3_llm_policy_adapter_runs_through_the_existing_runner_unmodified():
    policy = make_a3_llm_policy(
        client=StubLLMClient(response="not json"), model="stub", temperature=0.0, allow_live=True,
    )
    # Runs to completion with no exception - the only proof needed that
    # run_episode_a3 accepts this adapter exactly as it accepts a3d_policy,
    # with no change to src/rrx/harness/runner.py.
    for i in list(DEV_INDICES)[:20]:
        run_episode_a3(DEV_SPLIT, i, policy, EPISODE_CFG, POPULATION_CFG)
