"""The reason_code taxonomy (docs/A3-DESIGN.md §7) - 7 values, plus the
admissible-decline_code-per-reason_code mapping from the same table.

`terminal_state` was removed in eval-spec-v1.4 (reduced from 8 to 7
values): `subscription_cancelled_by_customer` never reaches a day-loop
tick at all (condition["kind"] == "subscription_state" returns before
the loop starts), so a terminal_state reason_code could never actually
be emitted - dead code, not re-added here (§7's own removal note).

This module only defines data (the enum values and the admissible-code
table) - it does not enforce anything itself. The gate (src/rrx/agent/
gate.py) enforces §8's R1-R8, which operate on action_type/remedy/
subscription_state/decline_code, never on reason_code; reason_code
admissibility is audit-taxonomy bookkeeping, not a gate rule.
"""

from __future__ import annotations

REMEDY_MATCH_CARD = "remedy_match_card"
REMEDY_MATCH_TOPUP = "remedy_match_topup"
RETRY_WINDOW_OPEN = "retry_window_open"
POST_HALT_RESCUE = "post_halt_rescue"
ENGAGEMENT_OBSERVED = "engagement_observed"
NO_ENGAGEMENT_RESTRAINT = "no_engagement_restraint"
RISK_FLAGGED = "risk_flagged"

REASON_CODES: frozenset[str] = frozenset({
    REMEDY_MATCH_CARD,
    REMEDY_MATCH_TOPUP,
    RETRY_WINDOW_OPEN,
    POST_HALT_RESCUE,
    ENGAGEMENT_OBSERVED,
    NO_ENGAGEMENT_RESTRAINT,
    RISK_FLAGGED,
})

# Every decline_code (== EpisodeView.decline_code / configs/population.yaml
# opening_condition key, engine.py:379) sim-v1 can produce for an episode
# that reaches a day-loop tick at all. subscription_cancelled_by_customer
# is deliberately excluded - it is a population.yaml kind: subscription_state
# opening condition, not a decline_code, and never reaches a runner tick
# (§7, §20; configs/population.yaml:140-150).
ALL_DECLINE_CODES: frozenset[str] = frozenset({
    "insufficient_funds",
    "ambiguous_decline",
    "card_expired",
    "debit_instrument_blocked",
    "card_not_enabled_group",
    "bank_technical_error",
    "transaction_limit_exceeded",
    "payment_risk_check_failed",
})

# docs/A3-DESIGN.md §7's table, verbatim ("Admissible decline_code(s)" column).
ADMISSIBLE_DECLINE_CODES: dict[str, frozenset[str]] = {
    REMEDY_MATCH_CARD: frozenset({
        "card_expired", "debit_instrument_blocked", "card_not_enabled_group",
        "ambiguous_decline", "bank_technical_error",
    }),
    REMEDY_MATCH_TOPUP: frozenset({"insufficient_funds", "transaction_limit_exceeded"}),
    RETRY_WINDOW_OPEN: frozenset({
        "insufficient_funds", "bank_technical_error", "transaction_limit_exceeded",
    }),
    # §7: additionally requires subscription_state == "halted" - not
    # encoded here (this table is decline_code-keyed only) - and NOT
    # admissible for bank_technical_error, whose card_chargeable=True at
    # opening (SIM.md §2), unlike the other four codes here.
    POST_HALT_RESCUE: frozenset({
        "card_expired", "debit_instrument_blocked", "card_not_enabled_group",
        "ambiguous_decline",
    }),
    # "any except subscription_cancelled_by_customer" (§7) - ALL_DECLINE_CODES
    # already excludes it by construction (it is not a decline_code).
    ENGAGEMENT_OBSERVED: ALL_DECLINE_CODES,
    NO_ENGAGEMENT_RESTRAINT: ALL_DECLINE_CODES,
    RISK_FLAGGED: frozenset({"payment_risk_check_failed"}),
}

# §7's "Typical action" column - documentation only, not enforced by the
# gate (R1-R8 operate on the Proposal/EpisodeView directly, never via
# this table).
TYPICAL_ACTION: dict[str, str] = {
    REMEDY_MATCH_CARD: "CONTACT(card_change)",
    REMEDY_MATCH_TOPUP: "CONTACT(topup_reminder)",
    RETRY_WINDOW_OPEN: "WAIT",
    POST_HALT_RESCUE: "CONTACT(card_change)",
    ENGAGEMENT_OBSERVED: "CONTACT",
    NO_ENGAGEMENT_RESTRAINT: "WAIT",
    RISK_FLAGGED: "STOP",
}


def is_admissible(reason_code: str, decline_code: str) -> bool:
    """Whether `decline_code` may legitimately co-occur with `reason_code`
    per §7's table. Not called by the gate (see module docstring) - for
    tests and future A3-D/gate extensions."""
    return decline_code in ADMISSIBLE_DECLINE_CODES.get(reason_code, frozenset())
