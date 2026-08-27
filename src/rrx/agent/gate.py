"""Day 4 foundation: no-op stub only.

Full R1-R8 rule evaluation (docs/A3-DESIGN.md §8) is explicitly out of
scope for Task 4A. This stub always accepts, so the A3 runner's
proposal -> gate -> executor pipeline (§3 step 5) has a concrete call
site to exercise without pre-empting the real gate's design. Only ever
handles Proposal/EpisodeView - no rrx.sim import, structurally or
otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass

from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


@dataclass(frozen=True, slots=True)
class GateVerdict:
    accepted: bool
    rule_fired: str | None  # "R1"-"R8" | None (§8) - never populated by this stub


def no_op_gate(proposal: Proposal, view: EpisodeView) -> GateVerdict:
    """Always accepts. Real §8 rule evaluation (R1-R8) is future work."""
    return GateVerdict(accepted=True, rule_fired=None)
