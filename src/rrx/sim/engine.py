"""Day 2 Stage 3: clock, retry engine, action-effect resolver, A0, A2.

Implements SIM.md §2-§5 mechanics plus the three model clarifications
recorded in SIM.md (§4, §5, §2 respectively) during the Stage 3 closing
pass:

MODEL RULING - within-day ordering (SIM.md §4). A message sent on day t and
engaged with on day t changes physical state BEFORE that day's end-of-day
retry reads it. Engagement is continuous-time (SIM.md §3's t_engage); the
retry schedule is day-granular. Implementation: any contact/email scheduled
for day t is resolved and its effects applied first; the day-t retry (if
day t is a retry day) reads state as of after that resolution.

MODEL RULING - post-halt card rescue (SIM.md §5), narrower form. Only
episodes that OPENED with card_chargeable=False are eligible: the instant
`card_chargeable` becomes true while `subscription_state == "halted"`, for
such an episode `subscription_state` is set to "active" immediately - no
additional condition, no delay. Episodes already card_chargeable=True at
opening (insufficient_funds, transaction_limit_exceeded, payment_risk_
check_failed) never become subscription_rescued merely because a post-halt
message occurs - see `_EpisodeState.card_chargeable_at_opening`. Evidence
for the mechanism itself (episodes that WERE card-broken can be rescued):
episode.yaml#/payment_method_change_effect/while_halted names `subscription_
rescued` as an outcome with `manual_charge_required: true` /
`manual_charge_available_domestic_card: false` - the failed invoice itself
can never be recovered post-halt (no in-scope mechanism reads funds_
available_from again once halted - SIM.md §4/§5), but the subscription can
still return to active. The at-opening restriction itself is a model
clarification, not derived from any single existing sentence - see SIM.md
§5's clarification text and the Stage 3 closing report for the reasoning.
Invoice recovery and subscription rescue are tracked as strictly separate
outcomes; a rescued subscription's originally-failed invoice is never
counted as recovered.

MODEL RULING - blocked_until "never" (SIM.md §2). See rrx.sim.latent's
inline comment; this module does not implement that clarification directly,
but its retry gate (_retry_succeeds) depends on it.

Remedy-matching (SIM.md §3): this module never evaluates whether an action
was the "correct" remedy for a decline code. A message's CONTENT (card-
naming and/or dues-naming) either changes physical state or it doesn't,
purely mechanically. A contact that turns out to be a physical no-op still
consumes budget and increments fatigue - it is a wasted attempt (reported
as `no_op_contacts`), not a penalised one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from rrx.features.episode_view import ContactRecord, EpisodeView
from rrx.sim.cohort import CohortEpisode, sample_cohort_episode
from rrx.sim.latent import MASTER_SEED, LatentState, draw_latent_state
from rrx.sim.rng import rng_for_child_stream

# [DESIGN]: highest channel_multiplier; A2 has no channel-selection logic.
AGENT_CHANNEL = "whatsapp"
# Razorpay's automatic failure email is, definitionally, an email.
AUTO_EMAIL_CHANNEL = "email"

_CARD_BROKEN_KEYS = frozenset(
    {"card_expired", "debit_instrument_blocked", "card_not_enabled_group"}
)


@dataclass(frozen=True, slots=True)
class EpisodeResult:
    opening_condition_key: str
    invoice_amount_inr: int
    invoice_recovered: bool
    subscription_rescued: bool
    contacts_sent: int
    wasted_attempts: int
    card_change_sent_for_insufficient_funds: bool


class _EpisodeState:
    """Mutable per-episode simulation state. Not exported - an
    implementation detail of run_episode()."""

    def __init__(self, latent: LatentState, condition_kind: str):
        self.card_chargeable = latent.card_chargeable
        # RULING 2 (narrower, model-clarified): only episodes that OPENED
        # with card_chargeable=False are eligible for post-halt rescue.
        # Recorded once, at T=0, and never updated thereafter.
        self.card_chargeable_at_opening = latent.card_chargeable
        self.funds_available_from = latent.funds_available_from
        self.mandate_alive = latent.mandate_alive
        self.blocked_until = latent.blocked_until
        self.completion_propensity = latent.card_change_completion_propensity

        self.subscription_state = (
            "cancelled" if condition_kind == "subscription_state" else "pending"
        )
        self.invoice_recovered = False

        self.contacts_sent = 0
        self.wasted_attempts = 0
        # fatigue exponent input - agent contacts only.
        self.agent_contact_count = 0
        # channel_response:engagement / card_change_completion:completion child index.
        self.message_index = 0
        # topup_acceleration child index - dues-naming engagements only.
        self.topup_engagement_index = 0
        self.card_change_sent_for_insufficient_funds = False

        # RULING 6 (Stage 4B): observational log only - never read by
        # _retry_succeeds, the card/dues effect resolvers, or either
        # policy. Holds plain rrx.features.episode_view.ContactRecord
        # values only (never latent state, RNG state, or a reference to
        # this _EpisodeState itself).
        self.contact_history: list[ContactRecord] = []


def _retry_succeeds(state: _EpisodeState, day: int) -> bool:
    """SIM.md §4's four-term AND gate, evaluated against CURRENT state."""
    return (
        state.card_chargeable
        and day >= state.funds_available_from
        and state.mandate_alive
        and day >= state.blocked_until
    )


def _engagement_probability(
    channel: str,
    theta_c: float,
    fatigue_base: float,
    channel_multipliers: dict[str, float],
    prior_agent_contacts: int,
    is_agent_contact: bool,
) -> float:
    p = channel_multipliers[channel] * theta_c
    if is_agent_contact:
        p *= fatigue_base**prior_agent_contacts
    return min(max(p, 0.0), 1.0)


def _apply_card_naming_effect(
    state: _EpisodeState, split: str, i: int, msg_idx: int, master_seed: int
) -> bool:
    """SIM.md §3 card-naming mechanism. Idempotent no-op if already true -
    no draw is consumed, since nothing would change either way."""
    if state.card_chargeable:
        return False
    rng = rng_for_child_stream(
        split, i, "card_change_completion", f"completion:{msg_idx}", master_seed
    )
    if rng.random() < state.completion_propensity:
        state.card_chargeable = True
        return True
    return False


def _apply_dues_naming_effect(
    state: _EpisodeState,
    day: int,
    episode_cfg: dict[str, Any],
    split: str,
    i: int,
    master_seed: int,
) -> bool:
    """SIM.md §3 dues-naming mechanism: min(original_delay, t_engage + draw).

    Precondition (episode.yaml#/latent/balance_restore_delay/topup_
    acceleration/precondition): "engagement occurs strictly before next
    auto-retry". Post-halt, no further retry ever reads funds_available_from
    (SIM.md §4/§5), so there is no next auto-retry left to precede; the
    mechanism does not fire at all (no draw consumed) rather than firing
    into a no-op, keeping topup_engagement_index scoped to draws that can
    possibly matter.
    """
    halt_boundary_day = episode_cfg["payment_method_change_effect"]["halt_boundary_day"]
    if day > halt_boundary_day:
        return False

    topup_cfg = episode_cfg["latent"]["balance_restore_delay"]["topup_acceleration"]
    idx = state.topup_engagement_index
    state.topup_engagement_index += 1
    rng = rng_for_child_stream(split, i, "topup_acceleration", str(idx), master_seed)

    if rng.random() < topup_cfg["p_topup_action"]:
        accel_draw = rng.exponential(topup_cfg["accelerated_delay"]["mean_days"])
        candidate = day + accel_draw
        if candidate < state.funds_available_from:
            state.funds_available_from = candidate
            return True
    return False


def _send_message(
    state: _EpisodeState,
    *,
    day: int,
    channel: str,
    names_card: bool,
    names_dues: bool,
    is_agent_contact: bool,
    split: str,
    i: int,
    latent: LatentState,
    episode_cfg: dict[str, Any],
    master_seed: int,
) -> None:
    msg_idx = state.message_index
    state.message_index += 1

    channel_response_cfg = episode_cfg["latent"]["channel_response_propensity"]
    fatigue_cfg = channel_response_cfg["fatigue"]
    channel_multipliers = channel_response_cfg["channel_multipliers"]
    p_eng = _engagement_probability(
        channel, latent.channel_response_trait, fatigue_cfg["base"],
        channel_multipliers, state.agent_contact_count, is_agent_contact,
    )

    eng_rng = rng_for_child_stream(
        split, i, "channel_response", f"engagement:{msg_idx}", master_seed
    )
    engaged = bool(eng_rng.random() < p_eng)

    if is_agent_contact:
        state.contacts_sent += 1
        state.agent_contact_count += 1

    changed = False
    if engaged:
        if names_card:
            changed |= _apply_card_naming_effect(state, split, i, msg_idx, master_seed)
        if names_dues:
            changed |= _apply_dues_naming_effect(state, day, episode_cfg, split, i, master_seed)

    if is_agent_contact and not changed:
        state.wasted_attempts += 1

    # RULING 6 (Stage 4B): observational logging only, using values already
    # computed above - does not feed back into any mechanic. `remedy` names
    # the message's content per SIM.md §3's own action table ("card, not
    # dues" / "dues, not card" / "both" for the automatic email).
    if names_card and names_dues:
        remedy = "both"
    elif names_card:
        remedy = "card_change"
    else:
        remedy = "topup_reminder"
    state.contact_history.append(
        ContactRecord(day=day, channel=channel, remedy=remedy, delivered=True, engaged=engaged)
    )

    # RULING 2 (narrower, model-clarified): immediate post-halt rescue, but
    # ONLY for episodes that opened with card_chargeable=False. An episode
    # already card_chargeable=True at opening (insufficient_funds,
    # transaction_limit_exceeded, payment_risk_check_failed) never becomes
    # subscription_rescued merely because a post-halt message occurs - there
    # is nothing for such a message to have fixed.
    if (
        state.subscription_state == "halted"
        and state.card_chargeable
        and not state.card_chargeable_at_opening
    ):
        state.subscription_state = "active"


# ---------------------------------------------------------------------------
# A0 / A2 policies.
#
# A policy is (opening_condition_key, day, subscription_state) -> action name
# ("card_change" | "topup_reminder") or None. Schedule points are
# UNCONDITIONAL unless a conditional is written into the frozen schedule
# text itself - only insufficient_funds/transaction_limit_exceeded's T+5
# fallback carries an explicit "if still pending/halted" clause.
# ---------------------------------------------------------------------------


def a0_action_for_day(opening_condition_key: str, day: int, subscription_state: str) -> str | None:
    """A0: no merchant contact, ever. Auto-retries and the automatic email
    still occur - that machinery lives in run_episode(), not here."""
    return None


def a2_action_for_day(opening_condition_key: str, day: int, subscription_state: str) -> str | None:
    """The reference policy dictated for Stage 3. Verified against the
    repository (Stage 3 closing pass, 2026-08-26): EVAL.md, SIM.md, and
    configs/ contain NO written A2 policy schedule at all - EVAL.md has no
    §4 (confirmed by grepping every `## `/`### ` heading), SIM.md defines
    world mechanics only (never agent policy), and no policy/reference-
    policy file exists anywhere in the repo (confirmed by search). This
    schedule, including every day-offset below, was dictated directly in
    conversation and is recorded here as its only actual source - it was
    never copied from, and is not verifiable against, any written spec file.

    insufficient_funds gets ONLY the T+1 top-up, never a card-change
    fallback. This was originally dictated WITH a T+5 card-change fallback
    for insufficient_funds; that fallback was dropped by an explicit user
    decision because it would have violated EVAL.md §5.2's actual, written
    gate ("Card-change prompts for insufficient_funds: 0", `test_gate_
    remedy_match.py`) - that gate IS real text in EVAL.md and does apply
    here; nothing about "superseding a §4" is being claimed, because there
    is no §4 for anything to supersede. transaction_limit_exceeded is not
    named in that gate (or in any other written rule) and keeps its T+5
    fallback - also dictated, not written anywhere in EVAL.md/SIM.md.
    """
    if opening_condition_key in _CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 5) else None

    if opening_condition_key == "insufficient_funds":
        return "topup_reminder" if day == 1 else None

    if opening_condition_key == "transaction_limit_exceeded":
        if day == 1:
            return "topup_reminder"
        if day == 5 and subscription_state in ("pending", "halted"):
            return "card_change"
        return None

    if opening_condition_key == "ambiguous_decline":
        return "card_change" if day in (0, 7) else None

    if opening_condition_key == "bank_technical_error":
        return "card_change" if day == 5 else None

    if opening_condition_key in ("subscription_cancelled_by_customer", "payment_risk_check_failed"):
        # cancelled: no contact (terminal, not restartable).
        # payment_risk_check_failed: escalate_to_merchant - not a customer contact.
        return None

    raise KeyError(f"a2_action_for_day: unhandled opening condition {opening_condition_key!r}")


_POLICIES: dict[str, Callable[[str, int, str], str | None]] = {
    "A0": a0_action_for_day,
    "A2": a2_action_for_day,
}


def build_episode_view(
    cohort: CohortEpisode,
    state: _EpisodeState,
    day: int,
    episode_cfg: dict[str, Any],
    split: str,
    i: int,
) -> EpisodeView:
    """RULING 7: the actual agent-facing projection, produced from real
    simulator state. A POSITIVE construction - every field below is copied
    out of `cohort`/`state` as a plain value (str/int/tuple-of-
    ContactRecord); no field is, or references, `state`, `cohort`,
    `LatentState`, an RNG, or any other simulator object. See episode_view.
    py's module docstring for exactly which EVAL.md §3.4 fields this v1
    surface omits and why (RULING 3, 4, 5, 8).

    `decline_code` (RULING 2): the observable, group-level
    `opening_condition_key` itself - "ambiguous_decline" for that bucket,
    never the resolved latent Bernoulli cause, matching population.yaml's
    own note that "A3 and A2 both see only decline_code for this bucket."

    `billing_amount_inr` (RULING 8): aliased to `invoice_amount_inr` - no
    separate recurring-price figure exists anywhere in this repository.

    `days_since_first_failure`/`auto_retries_remaining`/
    `next_auto_retry_day` (RULING 1): all relative-day integers, derived
    from `day` and the frozen retry schedule; no calendar anchor exists or
    is invented.
    """
    retry_days = episode_cfg["razorpay_retry_engine"]["card_schedule_days"]
    halt_boundary_day = episode_cfg["payment_method_change_effect"]["halt_boundary_day"]
    max_contacts = episode_cfg["agent_budget"]["max_contacts_per_episode"]

    retries_exhausted = state.invoice_recovered or day >= halt_boundary_day
    upcoming = [] if retries_exhausted else sorted(rd for rd in retry_days if rd > day)

    return EpisodeView(
        subscription_id=f"{split}-{i}",
        subscription_state=state.subscription_state,
        invoice_amount_inr=cohort.invoice_amount_inr,
        days_since_first_failure=day,
        auto_retries_remaining=len(upcoming),
        next_auto_retry_day=upcoming[0] if upcoming else None,
        decline_code=cohort.opening_condition_key,
        billing_amount_inr=cohort.invoice_amount_inr,
        contact_history=tuple(state.contact_history),
        budget_remaining=max_contacts - state.contacts_sent,
    )


def _finalize(cohort, state: _EpisodeState) -> EpisodeResult:
    return EpisodeResult(
        opening_condition_key=cohort.opening_condition_key,
        invoice_amount_inr=cohort.invoice_amount_inr,
        invoice_recovered=state.invoice_recovered,
        subscription_rescued=(state.subscription_state == "active"),
        contacts_sent=state.contacts_sent,
        wasted_attempts=state.wasted_attempts,
        card_change_sent_for_insufficient_funds=state.card_change_sent_for_insufficient_funds,
    )


def run_episode(
    split: str,
    i: int,
    arm: str,
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    master_seed: int = MASTER_SEED,
    capture_view_at_day: int | None = None,
) -> EpisodeResult | tuple[EpisodeResult, EpisodeView | None]:
    """Simulate one episode under `arm` ("A0" or "A2").

    The cohort draw and the latent-state draw never take `arm` as an input -
    both are computed identically regardless of which policy runs, which is
    what makes A0 and A2 paired-CRN comparable: episode i's world is
    byte-identical across arms, only the policy differs.

    RULING 7 (Stage 4B): `capture_view_at_day`, when given, additionally
    returns the real `EpisodeView` (via `build_episode_view`) as of the end
    of that day's mechanics - `(EpisodeResult, EpisodeView | None)` instead
    of a bare `EpisodeResult`. Purely opt-in and additive: every existing
    caller that omits it gets the exact same `EpisodeResult` as before, byte
    for byte - nothing about outcome resolution, engagement, or policy
    behavior changes based on this parameter. Returns `(result, None)` if
    the requested day is never reached (currently: the terminal-at-open
    `subscription_cancelled_by_customer` path, which returns before the day
    loop exists at all).
    """
    if arm not in _POLICIES:
        raise KeyError(f"unknown arm: {arm!r}")
    policy = _POLICIES[arm]

    cohort = sample_cohort_episode(split, i, population_cfg, master_seed)
    latent = draw_latent_state(
        split, i, cohort.opening_condition_key, episode_cfg, population_cfg, master_seed
    )
    condition = next(
        c for c in population_cfg["opening_conditions"] if c["key"] == cohort.opening_condition_key
    )
    state = _EpisodeState(latent, condition["kind"])

    if condition["kind"] == "subscription_state":
        # subscription_cancelled_by_customer: terminal at open, no charge was
        # ever attempted - no payment-failure event, so no automatic email,
        # no retries, and (EVAL.md §5.2) no agent contact either.
        result = _finalize(cohort, state)
        return (result, None) if capture_view_at_day is not None else result

    retry_days = episode_cfg["razorpay_retry_engine"]["card_schedule_days"]
    halt_boundary_day = episode_cfg["payment_method_change_effect"]["halt_boundary_day"]
    window_days = episode_cfg["episode"]["window_days"]
    max_contacts = episode_cfg["agent_budget"]["max_contacts_per_episode"]

    halted = False
    send_kwargs = dict(
        split=split, i=i, latent=latent, episode_cfg=episode_cfg, master_seed=master_seed
    )

    captured_view: EpisodeView | None = None

    for day in range(0, window_days + 1):
        if day == 0:
            _send_message(
                state, day=day, channel=AUTO_EMAIL_CHANNEL, names_card=True, names_dues=True,
                is_agent_contact=False, **send_kwargs,
            )

        if state.contacts_sent < max_contacts:
            action = policy(cohort.opening_condition_key, day, state.subscription_state)
            if action == "card_change":
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
                    is_agent_contact=True, **send_kwargs,
                )
                if cohort.opening_condition_key == "insufficient_funds":
                    state.card_change_sent_for_insufficient_funds = True
            elif action == "topup_reminder":
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=False, names_dues=True,
                    is_agent_contact=True, **send_kwargs,
                )

        if day in retry_days and not state.invoice_recovered and not halted:
            if _retry_succeeds(state, day):
                state.invoice_recovered = True
                state.subscription_state = "active"

        if day == halt_boundary_day and not state.invoice_recovered and not halted:
            halted = True
            state.subscription_state = "halted"
            _send_message(
                state, day=day, channel=AUTO_EMAIL_CHANNEL, names_card=True, names_dues=True,
                is_agent_contact=False, **send_kwargs,
            )

        if capture_view_at_day is not None and day == capture_view_at_day:
            captured_view = build_episode_view(cohort, state, day, episode_cfg, split, i)

    result = _finalize(cohort, state)
    return (result, captured_view) if capture_view_at_day is not None else result
