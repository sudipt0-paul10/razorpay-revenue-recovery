"""A3-D decision table conformance tests (docs/A3-DESIGN.md §10A).

These tests are the enforcing layer for §10A's pre-registration. They fall into
four groups:

1. PER-RULE REGRESSION - one synthetic EpisodeView engineered to reach each of
   R-01..R-16, asserting the exact (rule_id, action_type, remedy, reason_code)
   tuple §10A.4 specifies. If the table is edited, these fail loudly, which is
   the point: a silent table edit is a new tuning configuration
   (EVAL.md §6A, §10A.9) and must not pass unnoticed.

2. TOTALITY - the full cross product of reachable inputs. Every combination must
   produce a valid Proposal. No exception, no fallthrough, no null reason_code.

3. GATE COMPLIANCE - §8 claims A3-D "is gate-compliant by construction." That
   claim is discharged empirically here: evaluate_gate() must accept every
   proposal A3-D produces over the whole reachable input space. A single
   rejection is a defect, not a result (§10A.6).

4. ADMISSIBILITY - every emitted (reason_code, decline_code) pair satisfies §7's
   table, and every reason_code is a member of the frozen 7. This is the
   enforcing test EVAL.md §5.3's 100% [INVARIANT] currently lacks.

Synthetic views only. No simulator call, no dev episode, no RNG. The policy is a
pure function, so the whole reachable input space is enumerable directly.

STAGE 5E BOUNDARY: this file imports rrx.agent.policy.a3d_policy, which does
not exist yet - that module is Stage 5E, not implemented in this pass
(docs/A3-DESIGN.md §10A.9). Until it exists, this file is expected to fail to
COLLECT (an ImportError at module load), not to fail its assertions.
"""

from __future__ import annotations

import itertools

import pytest

from rrx.agent.gate import evaluate_gate
from rrx.agent.policy import a3d_policy
from rrx.agent.reason_codes import (
    ALL_DECLINE_CODES,
    REASON_CODES,
    is_admissible,
)
from rrx.features.episode_view import ContactRecord, EpisodeView

# ---------------------------------------------------------------------------
# Reachable input space
# ---------------------------------------------------------------------------

CARD_BROKEN = frozenset(
    {"card_expired", "debit_instrument_blocked", "card_not_enabled_group"}
)

# §5's frozen wake-up set, plus every other day reachable via the event-driven
# engagement trigger ("any day where contact_history has gained a new
# engaged=true record since the last wake"). The table must be total over the
# full 0..30 window, not only over the fixed set.
WINDOW_DAYS = 30
FIXED_WAKEUP_DAYS = (0, 1, 2, 3, 5, 7, 14)
ALL_REACHABLE_DAYS = tuple(range(0, WINDOW_DAYS + 1))

# §10A.1: cancelled/expired are runner-suppressed before invocation. "active" is
# runner-suppressed under §10A.2 [D-1] but is retained in the reachable set here
# so R-01's defensive branch is exercised, on the same footing as gate rule R2
# (§8: "Defensive only, in practice unreachable").
REACHABLE_STATES = ("pending", "halted", "active")

# §10A.1: budget_remaining == 0 produces tick_type=budget_exhausted and the
# policy is never invoked.
REACHABLE_BUDGETS = (1, 2, 3)

AGENT_CHANNEL = "whatsapp"
AUTO_EMAIL_CHANNEL = "email"


def _history(*, n_observations: int, any_engaged: bool) -> tuple[ContactRecord, ...]:
    """Build a contact_history with a controlled (observations, any_engaged)
    pair - the only two derived quantities §10A.3's withhold predicate reads.

    The first record is Razorpay's automatic failure email, which EVAL.md §3.4
    requires to appear in contact_history as an observable entry while
    consuming no budget and inducing no fatigue (SIM.md §3).
    """
    records = []
    for k in range(n_observations):
        records.append(
            ContactRecord(
                day=k,
                channel=AUTO_EMAIL_CHANNEL if k == 0 else AGENT_CHANNEL,
                remedy="card_change",
                delivered=True,
                # engagement placed on the last record when requested, so that
                # any_engaged is False for every prefix
                engaged=any_engaged and (k == n_observations - 1),
            )
        )
    return tuple(records)


def _view(
    *,
    decline_code: str,
    day: int,
    subscription_state: str = "pending",
    budget_remaining: int = 3,
    n_observations: int = 0,
    any_engaged: bool = False,
) -> EpisodeView:
    """A synthetic EpisodeView. Fields A3-D does not read are set to fixed,
    plausible constants - the policy is required to be a function of the fields
    §10A names and of nothing else, which test_policy_ignores_unread_fields
    checks directly.
    """
    retries_remaining = max(0, 3 - day) if day <= 3 else 0
    next_retry = day + 1 if day < 3 else None
    return EpisodeView(
        subscription_id=f"dev-{decline_code}-{day}",
        subscription_state=subscription_state,
        invoice_amount_inr=2000,
        days_since_first_failure=day,
        auto_retries_remaining=retries_remaining,
        next_auto_retry_day=next_retry,
        decline_code=decline_code,
        billing_amount_inr=2000,
        contact_history=_history(
            n_observations=n_observations, any_engaged=any_engaged
        ),
        budget_remaining=budget_remaining,
    )


# ---------------------------------------------------------------------------
# 1. PER-RULE REGRESSION
# ---------------------------------------------------------------------------
#
# (view kwargs, expected rule id, action_type, remedy, reason_code)
# Each case is engineered so that every earlier rule in §10A.4's ordering fails
# to match, which is what makes the expected rule id meaningful.

_RULE_CASES = [
    (
        "R-01",
        dict(decline_code="card_expired", day=5, subscription_state="active"),
        "STOP", None, "no_engagement_restraint",
    ),
    (
        "R-02",
        dict(decline_code="payment_risk_check_failed", day=0),
        "STOP", None, "risk_flagged",
    ),
    (
        "R-03",
        dict(decline_code="transaction_limit_exceeded", day=0),
        "STOP", None, "no_engagement_restraint",
    ),
    (
        "R-04",
        dict(decline_code="bank_technical_error", day=0),
        "WAIT", None, "retry_window_open",
    ),
    (
        "R-05",
        dict(decline_code="bank_technical_error", day=5, subscription_state="halted"),
        "STOP", None, "no_engagement_restraint",
    ),
    (
        "R-06",
        dict(decline_code="insufficient_funds", day=3, subscription_state="halted"),
        "STOP", None, "no_engagement_restraint",
    ),
    (
        "R-07",
        dict(decline_code="insufficient_funds", day=7),
        "STOP", None, "no_engagement_restraint",
    ),
    (
        "R-08",
        dict(decline_code="insufficient_funds", day=0, n_observations=1),
        "CONTACT", "topup_reminder", "remedy_match_topup",
    ),
    (
        # day 2, withhold does not apply because engagement was observed
        "R-09-engaged",
        dict(
            decline_code="insufficient_funds", day=2,
            n_observations=2, any_engaged=True, budget_remaining=2,
        ),
        "CONTACT", "topup_reminder", "engagement_observed",
    ),
    (
        # day 2, withhold does not apply because fewer than 2 observations
        "R-09-thin",
        dict(
            decline_code="insufficient_funds", day=2,
            n_observations=1, any_engaged=False, budget_remaining=2,
        ),
        "CONTACT", "topup_reminder", "remedy_match_topup",
    ),
    (
        # day 2, withhold applies: >=2 observations, none engaged
        "R-10-withheld",
        dict(
            decline_code="insufficient_funds", day=2,
            n_observations=2, any_engaged=False, budget_remaining=2,
        ),
        "WAIT", None, "no_engagement_restraint",
    ),
    (
        # day 1: not a contact day for this bucket, retries still open
        "R-10-window",
        dict(
            decline_code="insufficient_funds", day=1,
            n_observations=1, any_engaged=False, budget_remaining=2,
        ),
        "WAIT", None, "retry_window_open",
    ),
    (
        # exempt from the withhold test per [D-7]: no engagement, still contacts
        "R-11-card-broken",
        dict(
            decline_code="card_expired", day=5, subscription_state="halted",
            n_observations=4, any_engaged=False, budget_remaining=1,
        ),
        "CONTACT", "card_change", "post_halt_rescue",
    ),
    (
        "R-11-ambiguous",
        dict(
            decline_code="ambiguous_decline", day=5, subscription_state="halted",
            n_observations=4, any_engaged=False, budget_remaining=1,
        ),
        "CONTACT", "card_change", "post_halt_rescue",
    ),
    (
        "R-12",
        dict(decline_code="card_expired", day=0, n_observations=1),
        "CONTACT", "card_change", "remedy_match_card",
    ),
    (
        "R-13-engaged",
        dict(
            decline_code="debit_instrument_blocked", day=3,
            n_observations=2, any_engaged=True, budget_remaining=2,
        ),
        "CONTACT", "card_change", "engagement_observed",
    ),
    (
        "R-13-thin",
        dict(
            decline_code="card_not_enabled_group", day=3,
            n_observations=1, any_engaged=False, budget_remaining=2,
        ),
        "CONTACT", "card_change", "remedy_match_card",
    ),
    (
        "R-14",
        dict(decline_code="ambiguous_decline", day=0, n_observations=1),
        "CONTACT", "card_change", "remedy_match_card",
    ),
    (
        "R-15",
        dict(
            decline_code="ambiguous_decline", day=2,
            n_observations=1, any_engaged=False, budget_remaining=2,
        ),
        "CONTACT", "topup_reminder", "remedy_match_topup",
    ),
    (
        # card-broken, day 3, withhold applies -> falls past R-13 to the default
        "R-16-withheld",
        dict(
            decline_code="card_expired", day=3,
            n_observations=2, any_engaged=False, budget_remaining=2,
        ),
        "WAIT", None, "no_engagement_restraint",
    ),
    (
        # card-broken, halted, day 7 - R-11 is gated to day 5 exactly
        "R-16-late-halted",
        dict(
            decline_code="card_expired", day=7, subscription_state="halted",
            n_observations=3, any_engaged=True, budget_remaining=1,
        ),
        "WAIT", None, "no_engagement_restraint",
    ),
]


@pytest.mark.parametrize(
    "case_id,kwargs,action_type,remedy,reason_code",
    _RULE_CASES,
    ids=[c[0] for c in _RULE_CASES],
)
def test_rule_produces_registered_decision(
    case_id, kwargs, action_type, remedy, reason_code
):
    """§10A.4, one case per rule. A failure here means the decision table
    changed - which is a new tuning configuration (§10A.9), not a bug fix."""
    proposal = a3d_policy(_view(**kwargs))
    assert proposal.action_type == action_type, case_id
    assert proposal.remedy == remedy, case_id
    assert proposal.reason_code == reason_code, case_id


def test_every_rule_id_is_reachable():
    """No dead rules. Each of R-01..R-16 must be fired by at least one case
    above, identified through Proposal.rationale (§10: the rationale is the
    fired rule's identifier)."""
    fired = set()
    for _case_id, kwargs, *_ in _RULE_CASES:
        fired.add(a3d_policy(_view(**kwargs)).rationale)
    expected = {f"R-{n:02d}" for n in range(1, 17)}
    assert fired == expected, (
        f"unreachable rules: {sorted(expected - fired)}; "
        f"unregistered rationales: {sorted(fired - expected)}"
    )


# ---------------------------------------------------------------------------
# 2. TOTALITY
# ---------------------------------------------------------------------------

def _reachable_space():
    """Full cross product of the reachable input space (§10A.1).

    contact_history is collapsed to its two decision-relevant projections -
    (observations, any_engaged) - because §10A.3's withhold predicate reads
    nothing else from it. test_policy_ignores_unread_fields checks that this
    collapse is legitimate rather than assumed.
    """
    histories = [(0, False), (1, False), (2, False), (2, True), (4, False), (4, True)]
    return itertools.product(
        sorted(ALL_DECLINE_CODES),
        ALL_REACHABLE_DAYS,
        REACHABLE_STATES,
        REACHABLE_BUDGETS,
        histories,
    )


def _all_views():
    for code, day, state, budget, (n_obs, engaged) in _reachable_space():
        yield _view(
            decline_code=code,
            day=day,
            subscription_state=state,
            budget_remaining=budget,
            n_observations=n_obs,
            any_engaged=engaged,
        )


def test_policy_is_total_over_reachable_inputs():
    """§10A.4 must be defined for every reachable EpisodeView. No exception, no
    None return, no unpopulated mandatory field (§6)."""
    for view in _all_views():
        proposal = a3d_policy(view)
        assert proposal is not None
        assert proposal.action_type in {"CONTACT", "WAIT", "STOP"}
        assert proposal.reason_code, f"empty reason_code for {view!r}"
        assert proposal.rationale, f"empty rationale for {view!r}"


def test_policy_is_deterministic():
    """EVAL.md §4.2: 'a pure, deterministic function of EpisodeView'."""
    for view in _all_views():
        first = a3d_policy(view)
        assert a3d_policy(view) == first


def test_remedy_present_iff_contact():
    """§6: remedy required iff CONTACT, null otherwise."""
    for view in _all_views():
        p = a3d_policy(view)
        if p.action_type == "CONTACT":
            assert p.remedy in {"card_change", "topup_reminder"}
        else:
            assert p.remedy is None


def test_policy_ignores_unread_fields():
    """A3-D must be a function of the fields §10A names. Perturbing a field no
    rule reads must not change the decision - this is what licenses the
    collapsed contact_history representation used above, and it also guards
    against a rule silently starting to read invoice_amount_inr (which would be
    an unregistered fourth advantage source under EVAL.md §3.4)."""
    for view in _all_views():
        baseline = a3d_policy(view)
        perturbed = EpisodeView(
            subscription_id="dev-perturbed",
            subscription_state=view.subscription_state,
            invoice_amount_inr=47_500,
            days_since_first_failure=view.days_since_first_failure,
            auto_retries_remaining=view.auto_retries_remaining,
            next_auto_retry_day=view.next_auto_retry_day,
            decline_code=view.decline_code,
            billing_amount_inr=47_500,
            contact_history=view.contact_history,
            budget_remaining=view.budget_remaining,
        )
        after = a3d_policy(perturbed)
        assert after.action_type == baseline.action_type
        assert after.remedy == baseline.remedy
        assert after.reason_code == baseline.reason_code
        assert after.rationale == baseline.rationale


# ---------------------------------------------------------------------------
# 3. GATE COMPLIANCE
# ---------------------------------------------------------------------------

def test_gate_accepts_every_a3d_proposal():
    """§8: A3-D 'is gate-compliant by construction - its own decision logic
    never proposes a violating action.' Discharged empirically over the whole
    reachable space.

    A failure here is a DEFECT, not a result (§10A.6). Do not adjust the
    decision table to make a rejection disappear; report it.
    """
    rejections = []
    for view in _all_views():
        proposal = a3d_policy(view)
        verdict = evaluate_gate(proposal, view)
        if not verdict.accepted:
            rejections.append((verdict.rule_fired, proposal.rationale, view))
    assert not rejections, (
        f"{len(rejections)} gate rejection(s) from A3-D output; "
        f"first: rule={rejections[0][0]} fired_by={rejections[0][1]}"
    )


def test_no_card_change_for_balance_conditions():
    """EVAL.md §5.2's remedy-match invariant, checked at the policy layer rather
    than only at the gate - defence in depth for the row that prices a
    wrong-remedy contact."""
    forbidden = {"insufficient_funds", "transaction_limit_exceeded"}
    for view in _all_views():
        if view.decline_code in forbidden:
            p = a3d_policy(view)
            assert not (p.action_type == "CONTACT" and p.remedy == "card_change")


def test_no_contact_after_risk_flag():
    """EVAL.md §5.2: contacts after payment_risk_check_failed: 0."""
    for view in _all_views():
        if view.decline_code == "payment_risk_check_failed":
            assert a3d_policy(view).action_type != "CONTACT"


# ---------------------------------------------------------------------------
# 4. REASON-CODE VALIDITY AND ADMISSIBILITY
# ---------------------------------------------------------------------------

def test_reason_codes_are_members_of_the_frozen_enum():
    """docs/A3-DESIGN.md §7's 7-value closed taxonomy, and EVAL.md §5.3's
    '% actions carrying a machine-readable reason code: 100% [INVARIANT]'.

    This is the enforcing test that invariant previously lacked: no test
    anywhere in the repository asserted membership, and Proposal.reason_code is
    typed as a bare str.
    """
    for view in _all_views():
        code = a3d_policy(view).reason_code
        assert code in REASON_CODES, f"{code!r} is not one of §7's 7 values"


def test_reason_code_decline_code_pairs_are_admissible():
    """§7's admissible-decline_code-per-reason_code table, via
    reason_codes.is_admissible(). Note this assumes [CONSEQUENTIAL-1]:
    ambiguous_decline added to remedy_match_topup's admissible set, required by
    rule R-15."""
    violations = []
    for view in _all_views():
        p = a3d_policy(view)
        if not is_admissible(p.reason_code, view.decline_code):
            violations.append((p.rationale, p.reason_code, view.decline_code))
    assert not violations, (
        f"{len(violations)} inadmissible pair(s); first: "
        f"rule={violations[0][0]} {violations[0][1]} x {violations[0][2]}"
    )


def test_post_halt_rescue_only_when_halted():
    """§7: post_halt_rescue 'requires subscription_state == halted', and is not
    admissible for bank_technical_error (card_chargeable=True at opening,
    SIM.md §2/§5)."""
    for view in _all_views():
        p = a3d_policy(view)
        if p.reason_code == "post_halt_rescue":
            assert view.subscription_state == "halted"
            assert view.decline_code != "bank_technical_error"


# ---------------------------------------------------------------------------
# 5. BUDGET ACCOUNTING (§10A.8)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "decline_code,max_contact_days",
    [
        ("card_expired", 3),
        ("debit_instrument_blocked", 3),
        ("card_not_enabled_group", 3),
        ("ambiguous_decline", 3),
        ("insufficient_funds", 2),
        ("bank_technical_error", 0),
        ("transaction_limit_exceeded", 0),
        ("payment_risk_check_failed", 0),
    ],
)
def test_contact_day_count_within_budget(decline_code, max_contact_days):
    """§10A.8: no bucket's contact-day set exceeds the 3-contact budget
    (episode.yaml#/agent_budget/max_contacts_per_episode), so gate R5 is never
    reached through A3-D output.

    Counts the distinct days on which the policy would contact under the most
    permissive history (engagement observed, so the withhold predicate never
    fires) and the most permissive state trajectory (pending through day 3,
    halted thereafter).
    """
    contact_days = set()
    for day in ALL_REACHABLE_DAYS:
        state = "pending" if day < 3 else "halted"
        p = a3d_policy(
            _view(
                decline_code=decline_code,
                day=day,
                subscription_state=state,
                budget_remaining=3,
                n_observations=2,
                any_engaged=True,
            )
        )
        if p.action_type == "CONTACT":
            contact_days.add(day)
    assert len(contact_days) == max_contact_days, (
        f"{decline_code}: expected {max_contact_days} contact day(s), "
        f"got {sorted(contact_days)}"
    )
