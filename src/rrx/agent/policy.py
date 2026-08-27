"""A3-D: the deterministic ablation policy (docs/A3-DESIGN.md §10A).

`a3d_policy` is a literal transcription of §10A.4's 16-rule, first-match-wins
decision table - Stage 5E. Pure function `EpisodeView -> Proposal`
(`EVAL.md §4.2`): no I/O, no randomness, no state held between calls, no
import of `rrx.sim` (this module has no structural need to import it and
never does). Reads only the fields §10A names; `test_policy_ignores_unread_fields`
(tests/test_a3d_policy.py) is the enforcing check that no other field -
`invoice_amount_inr` in particular - silently becomes a decision input.

If any test in tests/test_a3d_policy.py disagrees with the mapping coded
here, §10A is authoritative: fix this file, never that table.
"""

from __future__ import annotations

from rrx.agent.proposal import Proposal
from rrx.agent.reason_codes import (
    ENGAGEMENT_OBSERVED,
    NO_ENGAGEMENT_RESTRAINT,
    POST_HALT_RESCUE,
    REMEDY_MATCH_CARD,
    REMEDY_MATCH_TOPUP,
    RETRY_WINDOW_OPEN,
    RISK_FLAGGED,
)
from rrx.features.episode_view import EpisodeView

# §10A.4: CARD_BROKEN = {card_expired, debit_instrument_blocked, card_not_enabled_group}
CARD_BROKEN = frozenset(
    {"card_expired", "debit_instrument_blocked", "card_not_enabled_group"}
)


def a3d_policy(view: EpisodeView) -> Proposal:
    """docs/A3-DESIGN.md §10A.4, in order, first match wins."""
    day = view.days_since_first_failure

    # §10A.3: the withhold predicate. contact_history includes the automatic
    # failure email as an observation (EVAL.md §3.4; SIM.md §3).
    observations = len(view.contact_history)
    any_engaged = any(rec.engaged for rec in view.contact_history)
    withhold_applies = observations >= 2 and not any_engaged

    # R-01 [D-1] - defensive; the runner suppresses "active" ticks (§10A.2),
    # so this is unreachable against a real tick.
    if view.subscription_state == "active":
        return Proposal(
            action_type="STOP", remedy=None,
            rationale="R-01", reason_code=NO_ENGAGEMENT_RESTRAINT,
        )

    # R-02 [FORCED] - gate R4 rejects any CONTACT for this decline_code.
    if view.decline_code == "payment_risk_check_failed":
        return Proposal(
            action_type="STOP", remedy=None,
            rationale="R-02", reason_code=RISK_FLAGGED,
        )

    # R-03 [FORCED mechanically] [D-2] - blocked_until beyond every retry
    # day; card_chargeable=True at opening rules out post-halt rescue too.
    if view.decline_code == "transaction_limit_exceeded":
        return Proposal(
            action_type="STOP", remedy=None,
            rationale="R-03", reason_code=NO_ENGAGEMENT_RESTRAINT,
        )

    # R-04 [FORCED] - the block clears before the day-2 retry with certainty.
    if view.decline_code == "bank_technical_error" and view.auto_retries_remaining > 0:
        return Proposal(
            action_type="WAIT", remedy=None,
            rationale="R-04", reason_code=RETRY_WINDOW_OPEN,
        )

    # R-05 [D-2] - retries exhausted; card_chargeable=True at opening rules
    # out post-halt rescue.
    if view.decline_code == "bank_technical_error":
        return Proposal(
            action_type="STOP", remedy=None,
            rationale="R-05", reason_code=NO_ENGAGEMENT_RESTRAINT,
        )

    # R-06 [FORCED mechanically] [D-2] [D-4] - post-halt, nothing reachable
    # for this bucket (card_chargeable=True at opening).
    if view.decline_code == "insufficient_funds" and view.subscription_state == "halted":
        return Proposal(
            action_type="STOP", remedy=None,
            rationale="R-06", reason_code=NO_ENGAGEMENT_RESTRAINT,
        )

    # R-07 [FORCED mechanically] [D-2] [D-4] - a topup sent on day 3+ cannot
    # affect any remaining retry (SIM.md §3 acceleration rule).
    if view.decline_code == "insufficient_funds" and day >= 3:
        return Proposal(
            action_type="STOP", remedy=None,
            rationale="R-07", reason_code=NO_ENGAGEMENT_RESTRAINT,
        )

    # R-08 [D-4] [DESIGN] - earliest reachable decision point.
    if view.decline_code == "insufficient_funds" and day == 0:
        return Proposal(
            action_type="CONTACT", remedy="topup_reminder",
            rationale="R-08", reason_code=REMEDY_MATCH_TOPUP,
        )

    # R-09 [D-4] [DESIGN] - last day a topup can still affect a retry.
    if (
        view.decline_code == "insufficient_funds"
        and day == 2
        and not withhold_applies
    ):
        return Proposal(
            action_type="CONTACT", remedy="topup_reminder",
            rationale="R-09",
            reason_code=ENGAGEMENT_OBSERVED if any_engaged else REMEDY_MATCH_TOPUP,
        )

    # R-10 [D-3] - day 1, or day 2 when the withhold test fires.
    if view.decline_code == "insufficient_funds":
        return Proposal(
            action_type="WAIT", remedy=None,
            rationale="R-10",
            reason_code=NO_ENGAGEMENT_RESTRAINT if withhold_applies else RETRY_WINDOW_OPEN,
        )

    # R-11 [D-5] [D-6] [D-7] - post-halt rescue, exempt from the withhold
    # test; gated to day 5 exactly.
    if (
        (view.decline_code in CARD_BROKEN or view.decline_code == "ambiguous_decline")
        and view.subscription_state == "halted"
        and day == 5
        and view.budget_remaining >= 1
    ):
        return Proposal(
            action_type="CONTACT", remedy="card_change",
            rationale="R-11", reason_code=POST_HALT_RESCUE,
        )

    # R-12 [D-5] - day 0, A2-strengthened's schedule adopted unchanged.
    if view.decline_code in CARD_BROKEN and day == 0:
        return Proposal(
            action_type="CONTACT", remedy="card_change",
            rationale="R-12", reason_code=REMEDY_MATCH_CARD,
        )

    # R-13 [D-5] - day 3, conditional on the withhold test (A3-D's one
    # intended difference from A2-strengthened's unconditional T+3 contact).
    if (
        view.decline_code in CARD_BROKEN
        and day == 3
        and not withhold_applies
    ):
        return Proposal(
            action_type="CONTACT", remedy="card_change",
            rationale="R-13",
            reason_code=ENGAGEMENT_OBSERVED if any_engaged else REMEDY_MATCH_CARD,
        )

    # R-14 [D-6] - day 0, fail-safe card-change prompt for the ambiguous bucket.
    if view.decline_code == "ambiguous_decline" and day == 0:
        return Proposal(
            action_type="CONTACT", remedy="card_change",
            rationale="R-14", reason_code=REMEDY_MATCH_CARD,
        )

    # R-15 [D-6] [CONSEQUENTIAL-1] - day 2, hedges the funds branch.
    if (
        view.decline_code == "ambiguous_decline"
        and day == 2
        and not withhold_applies
    ):
        return Proposal(
            action_type="CONTACT", remedy="topup_reminder",
            rationale="R-15", reason_code=REMEDY_MATCH_TOPUP,
        )

    # R-16 [D-8] - named default; every remaining reachable view.
    return Proposal(
        action_type="WAIT", remedy=None,
        rationale="R-16", reason_code=NO_ENGAGEMENT_RESTRAINT,
    )
