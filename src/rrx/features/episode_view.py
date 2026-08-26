"""EpisodeView - the complete information surface exposed to the agent.

EVAL.md §3.4 [INVARIANT]: A3 sees this and nothing else. Adding a field
here widens what the agent can condition on and is a spec change, not an
implementation detail. tests/test_no_latent_leak.py enforces the field set
against the allowlist in both directions.

Frozen so no downstream code can attach latent state at runtime.

Day 2 Stage 4B NARROWING (model/design rulings, recorded in full in
CHANGELOG.md and SIM.md; summarized here since this is the file the
narrowing changes): the v1 observable surface is DELIBERATELY NARROWER than
EVAL.md §3.4's original 16-field list. Six fields are removed rather than
populated with fabricated values:

  - decline_source        - RULING 3: undefined anywhere in EVAL.md/SIM.md/
                             configs (verified by search); v1 makes the
                             remedy-matching decision using decline_code
                             alone.
  - billing_cycle_day      - RULING 8: no distribution/producer exists
  - completed_billing_cycles  anywhere in the repository; inventing one was
                             explicitly forbidden, so these are deferred
                             rather than fabricated.
  - customer_tenure_days   - RULING 4/5: v1 does not build a cross-episode
  - prior_pending_episodes   customer-history model or implement tenure
  - prior_recovery_channel   coupling. The channel-selection advantage is
                             narrowed to within-episode adaptive contact:
                             inferring persistent EPISODE-LEVEL response
                             propensity from observable contact_history.engaged
                             alone, not cross-episode history.

Two representational changes (RULING 1, relative time - no calendar anchor
exists or is invented anywhere in this simulator):

  - `next_auto_retry_date: date | None` -> `next_auto_retry_day: int | None`
  - `ContactRecord.ts: datetime` -> `ContactRecord.day: int`

`billing_amount_inr` is retained: RULING 8 found it defensibly equivalent to
`invoice_amount_inr` (no separate recurring-price model exists anywhere in
the repository; `invoice_amount_inr` is the only price figure this
simulator ever defines, and model_params.yaml's `valued_at: billing_amount_inr`
never distinguishes it from the invoice amount) - the projection aliases it
rather than inventing a second value.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContactRecord:
    """One prior outbound touch. Per §1.2 this INCLUDES Razorpay's
    automatic payment-failure email, which is part of the world rather
    than an arm's choice and is not budgeted.

    `day` is relative (T+0..T+30), per RULING 1 - the simulator has no
    calendar anchor anywhere and none is invented here.
    """
    day: int
    channel: str
    remedy: str
    delivered: bool
    engaged: bool


@dataclass(frozen=True, slots=True)
class EpisodeView:
    """Day 2 Stage 4B v1 narrowed surface - 10 fields, not EVAL.md §3.4's
    original 16. See the module docstring above for exactly which six
    fields were removed and why, and the two fields renamed for relative
    (not calendar) time."""
    subscription_id: str
    subscription_state: str
    invoice_amount_inr: int

    days_since_first_failure: int
    auto_retries_remaining: int
    next_auto_retry_day: int | None

    decline_code: str

    billing_amount_inr: int

    contact_history: tuple[ContactRecord, ...]
    budget_remaining: int
