"""The Proposal contract (docs/A3-DESIGN.md §6).

The only object an A3 policy (A3-D or A3-LLM, neither implemented in
this pass) returns to the runner. Plain data only - never holds a
reference to any rrx.sim object, so this module has no structural need
to import rrx.sim and never does.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Proposal:
    """docs/A3-DESIGN.md §6. `channel` is deliberately absent - pinned to
    AGENT_CHANNEL at the executor, never chosen by the policy (§6, §20).
    `reason_code`'s 7-value frozen enum (§7) and the gate's R1-R8
    enforcement of this contract are future work (§8) - not implemented
    in this pass.
    """

    action_type: str  # "CONTACT" | "WAIT" | "STOP"
    remedy: str | None  # "card_change" | "topup_reminder" | None
    rationale: str
    reason_code: str
