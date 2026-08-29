"""A4 — the oracle arm (`EVAL.md §4`: "Full latent access; same 3-contact
budget as A1/A2/A3." Empirical upper reference — **not a target** (§7)).

Ported for production reuse, byte-for-byte, from `tests/test_stage5_
falsification.py`'s test-local `run_a4_episode`/`_a4_content_for_condition`
(Day 2 Stage 5, later corrected there to the shared 3-contact budget — see
that module's own extensive decision-rule docstring for the full objective/
scope/decision-rule record, reproduced here only where needed for this
port to stand on its own). **That test module's own copy is NOT modified,
replaced, or deleted by this file** — it remains the authoritative Stage-5
falsification artifact, byte-identical to what is defined here.
`tests/test_a4.py` is the enforcing behavioral-equivalence check between
the two, mirroring the precedent `src/rrx/baselines/a1.py` already
established for A1's own promotion (`tests/test_a1.py`).

A4 cannot be expressed as a `(opening_condition_key, day,
subscription_state) -> action | None` policy callable — `rrx.sim.engine`'s
standard `_POLICIES` interface — because it genuinely needs full latent
access (`card_chargeable`, `funds_available_from`, `blocked_until`) that
interface does not expose. It is therefore its own episode-loop function,
built from the same real, unmodified simulator primitives
`rrx.sim.engine.run_episode` itself uses — not a `_POLICIES` registration.
`rrx.sim.engine`'s own re-exports of `draw_latent_state`/`MASTER_SEED` are
used here (mirroring `src/rrx/harness/runner.py`'s existing practice) so
this module has no direct import naming `rrx.sim.latent`.
"""

from __future__ import annotations

from typing import Any

from rrx.sim.cohort import sample_cohort_episode
from rrx.sim.engine import (
    AGENT_CHANNEL,
    AUTO_EMAIL_CHANNEL,
    MASTER_SEED,
    EpisodeResult,
    _EpisodeState,
    _retry_succeeds,
    _send_message,
    draw_latent_state,
)

# matches episode.yaml#/agent_budget/max_contacts_per_episode
A4_MAX_CONTACTS = 3


def _a4_content_for_condition(opening_condition_key, latent, halt_boundary_day):
    """The lever, if any, for this condition given full latent access.
    Returns None if no contact can ever help (structurally unrecoverable,
    or already certain, or terminal)."""
    if not latent.card_chargeable:
        return "card_change"
    already_certain = (
        latent.funds_available_from <= halt_boundary_day
        and latent.blocked_until <= halt_boundary_day
    )
    if already_certain:
        return None
    is_fund_driven = opening_condition_key == "insufficient_funds" or (
        opening_condition_key == "ambiguous_decline" and latent.card_chargeable
    )
    if is_fund_driven and latent.funds_available_from > halt_boundary_day:
        return "topup_reminder"
    return None


def run_a4_episode(
    split: str,
    i: int,
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    master_seed: int = MASTER_SEED,
    max_contacts: int = A4_MAX_CONTACTS,
) -> EpisodeResult:
    """A4's episode simulation — reuses the exact same primitives
    run_episode() uses (_EpisodeState, _send_message, _retry_succeeds,
    draw_latent_state, sample_cohort_episode), unmodified. The only new
    logic is the decision rule above; everything else (T+0 auto email, the
    AND-gate, halt + halt-email) is the real mechanism. `max_contacts`
    defaults to the same 3-contact budget A1/A2-strengthened/A3-D use."""
    cohort = sample_cohort_episode(split, i, population_cfg, master_seed)
    latent = draw_latent_state(
        split, i, cohort.opening_condition_key, episode_cfg, population_cfg, master_seed
    )
    condition = next(
        c for c in population_cfg["opening_conditions"] if c["key"] == cohort.opening_condition_key
    )
    state = _EpisodeState(latent, condition["kind"])

    if condition["kind"] == "subscription_state":
        return EpisodeResult(
            opening_condition_key=cohort.opening_condition_key,
            invoice_amount_inr=cohort.invoice_amount_inr,
            invoice_recovered=False,
            subscription_rescued=False,
            contacts_sent=0,
            wasted_attempts=0,
            card_change_sent_for_insufficient_funds=False,
        )

    retry_days = episode_cfg["razorpay_retry_engine"]["card_schedule_days"]
    halt_boundary_day = episode_cfg["payment_method_change_effect"]["halt_boundary_day"]
    window_days = episode_cfg["episode"]["window_days"]

    content = _a4_content_for_condition(cohort.opening_condition_key, latent, halt_boundary_day)
    send_kwargs = dict(
        split=split, i=i, latent=latent, episode_cfg=episode_cfg, master_seed=master_seed
    )
    halted = False

    for day in range(0, window_days + 1):
        if day == 0:
            _send_message(
                state, day=day, channel=AUTO_EMAIL_CHANNEL, names_card=True, names_dues=True,
                is_agent_contact=False, **send_kwargs,
            )

        if content is not None and day in (0, 1, 2) and state.contacts_sent < max_contacts:
            names_card = content == "card_change"
            already_resolved = state.invoice_recovered or (names_card and state.card_chargeable)
            if not already_resolved:
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=names_card,
                    names_dues=not names_card, is_agent_contact=True, **send_kwargs,
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

    return EpisodeResult(
        opening_condition_key=cohort.opening_condition_key,
        invoice_amount_inr=cohort.invoice_amount_inr,
        invoice_recovered=state.invoice_recovered,
        subscription_rescued=(state.subscription_state == "active"),
        contacts_sent=state.contacts_sent,
        wasted_attempts=state.wasted_attempts,
        card_change_sent_for_insufficient_funds=False,
    )
