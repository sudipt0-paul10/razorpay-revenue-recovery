"""The safety gate (docs/A3-DESIGN.md §8) - R1-R8, in the frozen
precedence order R2, R4 -> R3 -> R1, R8 -> R5, R6.

Pure function: `evaluate_gate(proposal, view)` reads only its two
arguments (plus the R6-only `send_hour` override, a testability knob -
see below) and a small set of module-level constants; no I/O, no rrx.sim
import, no mutation of `proposal`/`view` (both are frozen dataclasses
anyway).

R5 (budget) and R6 (quiet hours) are enforcement-by-construction per §8:
the real runner (src/rrx/harness/runner.py) never invokes the policy, and
therefore never calls this gate, once `budget_remaining == 0`
(tick_type=budget_exhausted instead - §3 step 3), and always executes
messages at the fixed `AGENT_SEND_HOUR` this module defines (§9). Both
rules below are still implemented and checked, so a synthetic adversarial
Proposal/EpisodeView (or, for R6, an explicit `send_hour` override) can
exercise the rejection path in tests/test_gate_rules.py - but neither
should ever actually fire against a real runner tick. Do not fabricate a
gate rejection for a budget-exhausted tick anywhere else in this
codebase; that case is tick_type=budget_exhausted at the runner level,
never a gate call at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from rrx.agent.proposal import Proposal
from rrx.agent.reason_codes import ALL_DECLINE_CODES
from rrx.features.episode_view import EpisodeView

# §9: the executor's fixed send-hour stamp. R6 validates this constant.
AGENT_SEND_HOUR = "10:00"

# data/decline_codes.yaml#/defaults/global_caps/quiet_hours_ist - not a
# new config key, just this project's already-frozen 09:00-21:00 IST
# window, restated here as the literal bound R6 checks against.
_QUIET_HOURS_START = "09:00"
_QUIET_HOURS_END = "21:00"

# §6: the only 3 legal Proposal.action_type values. Anything else is, by
# construction, an action outside the schema - R1's target ("no such
# value exists in the schema").
_VALID_ACTION_TYPES = frozenset({"CONTACT", "WAIT", "STOP"})

# R2: subscription_state values a CONTACT must never be sent against.
# "expired" never occurs in sim-v1 (checked anyway, matching R2's own
# defensive/unreachable framing, §8).
_R2_TERMINAL_SUBSCRIPTION_STATES = frozenset({"cancelled", "expired"})

# R3: decline_codes for which card_change is never the correct remedy.
_R3_FORBIDDEN_CARD_CHANGE_DECLINE_CODES = frozenset(
    {"insufficient_funds", "transaction_limit_exceeded"}
)

# R4: the single hard-stop decline_code.
_R4_RISK_DECLINE_CODE = "payment_risk_check_failed"


@dataclass(frozen=True, slots=True)
class GateVerdict:
    accepted: bool
    rule_fired: str | None  # "R1"-"R8" | None (§8)


def _within_quiet_hours(send_hour: str) -> bool:
    """Zero-padded "HH:MM" strings compare correctly under plain string
    ordering within a single day."""
    return _QUIET_HOURS_START <= send_hour <= _QUIET_HOURS_END


def evaluate_gate(
    proposal: Proposal, view: EpisodeView, *, send_hour: str = AGENT_SEND_HOUR
) -> GateVerdict:
    """§8's R1-R8, checked in the frozen precedence order
    R2, R4 -> R3 -> R1, R8 -> R5, R6. Returns the FIRST rule that fires;
    a proposal violating several rules is reported under only the
    highest-precedence one (tests/test_gate_precedence.py)."""

    # --- R2, R4 (tied precedence; checked R2 then R4) ---
    if proposal.action_type == "CONTACT" and view.subscription_state in (
        _R2_TERMINAL_SUBSCRIPTION_STATES
    ):
        return GateVerdict(accepted=False, rule_fired="R2")
    if proposal.action_type == "CONTACT" and view.decline_code == _R4_RISK_DECLINE_CODE:
        return GateVerdict(accepted=False, rule_fired="R4")

    # --- R3 ---
    if (
        proposal.action_type == "CONTACT"
        and proposal.remedy == "card_change"
        and view.decline_code in _R3_FORBIDDEN_CARD_CHANGE_DECLINE_CODES
    ):
        return GateVerdict(accepted=False, rule_fired="R3")

    # --- R1, R8 (tied precedence; checked R1 then R8) ---
    if proposal.action_type not in _VALID_ACTION_TYPES:
        return GateVerdict(accepted=False, rule_fired="R1")
    if proposal.action_type == "CONTACT" and view.decline_code not in ALL_DECLINE_CODES:
        return GateVerdict(accepted=False, rule_fired="R8")

    # --- R5, R6 (tied precedence; checked R5 then R6) ---
    if proposal.action_type == "CONTACT" and view.budget_remaining <= 0:
        return GateVerdict(accepted=False, rule_fired="R5")
    if not _within_quiet_hours(send_hour):
        return GateVerdict(accepted=False, rule_fired="R6")

    return GateVerdict(accepted=True, rule_fired=None)
