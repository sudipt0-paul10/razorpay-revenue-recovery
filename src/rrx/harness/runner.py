"""A3 day-loop driver (docs/A3-DESIGN.md §3).

Lives OUTSIDE the guarded rrx.agent / rrx.features packages
(tests/test_no_latent_leak.py's GUARDED_PACKAGES) because it is harness
code whose job is driving real simulator primitives -
_EpisodeState, _send_message, _retry_succeeds, build_episode_view,
sample_cohort_episode, draw_latent_state - none of which an agent policy
may ever see directly. GUARDED_PACKAGES stays exactly as it is;
rrx/agent remains fully guarded, unmodified, and the locked
test_no_latent_leak.py is not touched.

The only object this module ever passes to the injected `policy`
callable is an EpisodeView (via build_episode_view, unmodified) - never
_EpisodeState, CohortEpisode, LatentState, or an RNG object. See
tests/test_agent_boundary.py.

This module obtains draw_latent_state/MASTER_SEED through
rrx.sim.engine's own re-export rather than importing rrx.sim.latent
directly (see tests/test_harness_no_latent_import.py) - the harness
legitimately needs full simulator access, but its own import statements
never name the latent module, mirroring how the existing A4 test-local
loop (tests/test_stage5_falsification.py) reuses the same primitives.

Reuses, UNMODIFIED: _EpisodeState, _send_message, _retry_succeeds,
build_episode_view, _finalize, AGENT_CHANNEL, AUTO_EMAIL_CHANNEL,
EpisodeResult (rrx.sim.engine); sample_cohort_episode (rrx.sim.cohort).
src/rrx/sim/ is never modified.

Day-loop contract, per day D (docs/A3-DESIGN.md §3):
  1. Automatic events preceding the decision (D==0 auto email).
  2. EpisodeView construction - build_episode_view, after step 1, before
     step 4.
  3. Wake-up determination (§5) - tick_type classification.
  4. Policy invocation - only on a real wakeup tick.
  5. Gate (§8) - real R1-R8 evaluation (src/rrx/agent/gate.py).
  6. Executor (§9) - CONTACT maps to _send_message; WAIT/STOP/rejected:
     no state mutation beyond STOP's own runner-level flag.
  7. Retry check - identical to engine.py's own retry-day handling.
  8. Halt check + halt auto-email - identical to engine.py's own.
  9. Ledger record (§14) - real 22-field record
     (src/rrx/agent/ledger.py). Both gate and ledger are pure functions
     (no mutation of `state`/`view`/`proposal`) - wiring them in changes
     nothing about the mutating steps 1/6/7/8, which is what
     tests/test_a3_runner_parity.py depends on.
"""

from __future__ import annotations

from typing import Any, Callable

from rrx.agent.gate import GateVerdict, evaluate_gate
from rrx.agent.ledger import default_ledger_record
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView
from rrx.sim.cohort import sample_cohort_episode
from rrx.sim.engine import (
    AGENT_CHANNEL,
    AUTO_EMAIL_CHANNEL,
    MASTER_SEED,  # re-exported from rrx.sim.latent via rrx.sim.engine's own import
    EpisodeResult,
    _EpisodeState,
    _finalize,
    _retry_succeeds,
    _send_message,
    build_episode_view,
    draw_latent_state,  # re-exported from rrx.sim.latent via rrx.sim.engine's own import
)

# docs/A3-DESIGN.md §5 - FROZEN wake-up set. Identical for A3-D and A3-LLM;
# the planner never selects its own wake-ups.
WAKEUP_DAYS = frozenset({0, 1, 2, 3, 5, 7, 14})

# §7 tick_type enum's terminal-subscription-state test. "cancelled" never
# reaches this day loop at all (condition["kind"] == "subscription_state"
# returns before the loop starts, mirroring engine.py:438-443); "expired"
# never occurs in sim-v1. Both are checked anyway, matching R2's own
# defensive-only set (§8) and §7's literal wording.
#
# "active" added under docs/A3-DESIGN.md §10A.2 [D-1] (eval-spec-v1.5):
# _retry_succeeds sets subscription_state="active" on invoice recovery.
# Without suppressing it here, a recovered episode stayed non-terminal,
# kept its remaining budget, and produced a full wakeup tick on every
# later wake-up day - each demanding a reason_code from §7's closed
# 7-value enum, none of which means "already resolved". Suppressing these
# ticks mirrors §6's existing post-STOP terminal_suppressed semantics and
# requires no change to that enum. wait_rate's denominator (wake-up
# decisions, EVAL.md §5.3) correspondingly excludes post-recovery ticks -
# the intended reading, since a decision that cannot affect the outcome
# is not restraint.
TERMINAL_SUBSCRIPTION_STATES = frozenset({"cancelled", "expired", "active"})

TICK_WAKEUP = "wakeup"
TICK_NO_WAKEUP = "no_wakeup"
TICK_BUDGET_EXHAUSTED = "budget_exhausted"
TICK_TERMINAL_SUPPRESSED = "terminal_suppressed"

PolicyFn = Callable[[EpisodeView], Proposal]
GateFn = Callable[..., GateVerdict]
LedgerFn = Callable[..., Any]


def run_episode_a3(
    split: str,
    i: int,
    policy: PolicyFn,
    episode_cfg: dict[str, Any],
    population_cfg: dict[str, Any],
    master_seed: int = MASTER_SEED,
    capture_view_at_day: int | None = None,
    gate: GateFn = evaluate_gate,
    ledger_record: LedgerFn = default_ledger_record,
) -> EpisodeResult | tuple[EpisodeResult, EpisodeView | None]:
    """Simulate one episode under the A3 runner, driven by an injected
    `policy` callable (docs/A3-DESIGN.md §3).

    Mirrors rrx.sim.engine.run_episode()'s parameter shape (split, i,
    <policy selector>, episode_cfg, population_cfg, master_seed,
    capture_view_at_day) with `policy` an injected callable in place of
    an arm-name string lookup. `gate`/`ledger_record` default to the real
    §8/§14 implementations (src/rrx/agent/gate.py, ledger.py).

    The cohort draw and the latent-state draw take no input from
    `policy`/`gate`/`ledger_record` - identical CRN to run_episode(),
    which is what docs/A3-DESIGN.md §16's byte-identity proof depends on.
    """
    cohort = sample_cohort_episode(split, i, population_cfg, master_seed)
    latent = draw_latent_state(
        split, i, cohort.opening_condition_key, episode_cfg, population_cfg, master_seed
    )
    condition = next(
        c for c in population_cfg["opening_conditions"] if c["key"] == cohort.opening_condition_key
    )
    state = _EpisodeState(latent, condition["kind"])

    if condition["kind"] == "subscription_state":
        # subscription_cancelled_by_customer: terminal at open, before any
        # day-loop iteration - identical early return to run_episode().
        # No runner tick, no wakeup, no policy invocation, no ledger
        # record at all (§7, §20).
        result = _finalize(cohort, state)
        return (result, None) if capture_view_at_day is not None else result

    retry_days = episode_cfg["razorpay_retry_engine"]["card_schedule_days"]
    halt_boundary_day = episode_cfg["payment_method_change_effect"]["halt_boundary_day"]
    window_days = episode_cfg["episode"]["window_days"]
    max_contacts = episode_cfg["agent_budget"]["max_contacts_per_episode"]

    halted = False
    episode_stopped = False  # §6 STOP semantics: forgoes remaining budget only
    last_wake_history_len = 0  # §5's event-driven wake-up bookkeeping
    send_kwargs = dict(
        split=split, i=i, latent=latent, episode_cfg=episode_cfg, master_seed=master_seed
    )

    captured_view: EpisodeView | None = None

    for day in range(0, window_days + 1):
        # --- step 1: automatic events preceding the decision ---
        if day == 0:
            _send_message(
                state, day=day, channel=AUTO_EMAIL_CHANNEL, names_card=True, names_dues=True,
                is_agent_contact=False, **send_kwargs,
            )

        # --- step 2: EpisodeView construction, before the decision ---
        view = build_episode_view(cohort, state, day, episode_cfg, split, i)
        budget_before = view.budget_remaining

        # --- step 3: wake-up determination ---
        new_engagement_since_last_wake = any(
            rec.engaged for rec in view.contact_history[last_wake_history_len:]
        )
        is_terminal = state.subscription_state in TERMINAL_SUBSCRIPTION_STATES or episode_stopped

        if is_terminal:
            tick_type = TICK_TERMINAL_SUPPRESSED
        elif view.budget_remaining == 0:
            tick_type = TICK_BUDGET_EXHAUSTED
        elif day in WAKEUP_DAYS or new_engagement_since_last_wake:
            tick_type = TICK_WAKEUP
        else:
            tick_type = TICK_NO_WAKEUP

        proposal: Proposal | None = None
        gate_verdict: GateVerdict | None = None
        executed_action: dict[str, str] | None = None
        contact_sent_this_tick = False

        if tick_type == TICK_WAKEUP:
            last_wake_history_len = len(view.contact_history)
            # --- step 4: policy invocation, only on a real wakeup tick ---
            proposal = policy(view)
            # --- step 5: gate (§8's R1-R8, real precedence-ordered check) ---
            gate_verdict = gate(proposal, view)

            # --- step 6: executor ---
            if gate_verdict.accepted and proposal.action_type == "CONTACT" and (
                proposal.remedy == "card_change"
            ):
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
                    is_agent_contact=True, **send_kwargs,
                )
                if cohort.opening_condition_key == "insufficient_funds":
                    state.card_change_sent_for_insufficient_funds = True
                contact_sent_this_tick = True
                executed_action = {"action_type": "CONTACT", "remedy": "card_change"}
            elif gate_verdict.accepted and proposal.action_type == "CONTACT" and (
                proposal.remedy == "topup_reminder"
            ):
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=False, names_dues=True,
                    is_agent_contact=True, **send_kwargs,
                )
                contact_sent_this_tick = True
                executed_action = {"action_type": "CONTACT", "remedy": "topup_reminder"}
            elif gate_verdict.accepted and proposal.action_type == "STOP":
                episode_stopped = True
                executed_action = {"action_type": "STOP"}
            else:
                # WAIT, or a rejected/otherwise-unexecutable proposal: no
                # state mutation (§3 step 6; §9's executor table).
                executed_action = {"action_type": "WAIT"}

        # --- step 7: retry check - identical to engine.py:479-482 ---
        if day in retry_days and not state.invoice_recovered and not halted:
            if _retry_succeeds(state, day):
                state.invoice_recovered = True
                state.subscription_state = "active"

        # --- step 8: halt check + halt auto-email - identical to engine.py:484-490 ---
        if day == halt_boundary_day and not state.invoice_recovered and not halted:
            halted = True
            state.subscription_state = "halted"
            _send_message(
                state, day=day, channel=AUTO_EMAIL_CHANNEL, names_card=True, names_dues=True,
                is_agent_contact=False, **send_kwargs,
            )

        # --- step 9: ledger record (§14) - one per tick, structurally guaranteed ---
        budget_after = max_contacts - state.contacts_sent
        ledger_record(
            episode_id=view.subscription_id,
            tick=day,
            tick_type=tick_type,
            view=view,
            proposal=proposal,
            gate_verdict=gate_verdict,
            executed_action=executed_action,
            budget_before=budget_before,
            budget_after=budget_after,
            contact_sent=contact_sent_this_tick,
        )

        if capture_view_at_day is not None and day == capture_view_at_day:
            captured_view = build_episode_view(cohort, state, day, episode_cfg, split, i)

    result = _finalize(cohort, state)
    return (result, captured_view) if capture_view_at_day is not None else result
