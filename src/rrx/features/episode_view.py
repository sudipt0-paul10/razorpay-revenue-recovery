"""EpisodeView - the complete information surface exposed to the agent.

EVAL.md §3.4 [INVARIANT]: A3 sees this and nothing else. Adding a field
here widens what the agent can condition on and is a spec change, not an
implementation detail. tests/test_no_latent_leak.py enforces the field set
against the §3.4 allowlist in both directions.

Frozen so no downstream code can attach latent state at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class ContactRecord:
    """One prior outbound touch. Per §1.2 this INCLUDES Razorpay's
    automatic payment-failure email, which is part of the world rather
    than an arm's choice and is not budgeted."""
    ts: datetime
    channel: str
    remedy: str
    delivered: bool
    engaged: bool


@dataclass(frozen=True, slots=True)
class EpisodeView:
    subscription_id: str
    subscription_state: str
    invoice_amount_inr: int

    days_since_first_failure: int
    auto_retries_remaining: int
    next_auto_retry_date: date | None

    decline_code: str
    decline_source: str

    billing_cycle_day: int
    billing_amount_inr: int
    completed_billing_cycles: int

    customer_tenure_days: int
    prior_pending_episodes: int
    prior_recovery_channel: str | None

    contact_history: tuple[ContactRecord, ...]
    budget_remaining: int
