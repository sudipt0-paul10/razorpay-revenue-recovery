"""docs/A3-DESIGN.md §2 boundary invariant, restated per the Task 4A
file-plan correction: the day-loop driver lives under src/rrx/harness
(not src/rrx/agent) precisely because it needs full rrx.sim access that
a policy must never have.

This test proves the actual boundary crossing is clean: the injected
policy callable receives exactly one positional argument, and that
argument is an EpisodeView - never _EpisodeState, CohortEpisode,
LatentState, or an RNG object.
"""

from __future__ import annotations

from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Not exhaustive latent field names - just the most direct ones, matching
# tests/test_no_latent_leak.py's own approach, to catch an EpisodeView
# that somehow grew a latent attribute at runtime.
_LATENT_ATTRS = (
    "card_chargeable", "funds_available_from", "mandate_alive",
    "blocked_until", "channel_response_trait", "card_chargeable_at_opening",
)


def test_policy_receives_only_an_episode_view():
    calls: list[tuple[tuple, dict]] = []

    def spy_policy(*args, **kwargs):
        calls.append((args, kwargs))
        return Proposal(
            action_type="WAIT", remedy=None, rationale="spy", reason_code="spy"
        )

    # Run several dev episodes (not just one) so this isn't accidentally
    # vacuous if a single chosen index happened to be cancelled-at-open
    # (no wakeup tick at all for that bucket, per §7/§20).
    for i in list(DEV_INDICES)[:50]:
        run_episode_a3(DEV_SPLIT, i, spy_policy, EPISODE_CFG, POPULATION_CFG)

    assert calls, (
        "spy_policy was never invoked across 50 dev episodes - "
        "no wakeup tick occurred for any of them"
    )
    for args, kwargs in calls:
        assert len(args) == 1, f"policy received {len(args)} positional args, expected 1: {args}"
        assert not kwargs, f"policy received keyword args, expected none: {kwargs}"
        (view,) = args
        assert isinstance(view, EpisodeView), (
            f"policy received {type(view)!r}, expected EpisodeView"
        )
        for attr in _LATENT_ATTRS:
            assert not hasattr(view, attr), f"EpisodeView leaked latent attribute {attr!r}"
