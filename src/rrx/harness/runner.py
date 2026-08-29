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

Day 6 Stage 6B addition - gate-rejection fallback hook (docs/A3-DESIGN.md
§11: "Gate rejection → fallback: fallback_reason=gate_rejected... its
proposal executes through the same gate/executor"). Inserted between
steps 5 and 6: if `gate(proposal, view)` rejects, `rrx.agent.policy.
a3d_policy` (UNMODIFIED) is re-invoked on the SAME `view`, and ITS
proposal is re-gated through the SAME `gate` call before the executor
runs. The ledger's `proposal`/`gate_verdict`/`gate_rule_fired` fields
still record the ORIGINAL (rejected) proposal - the audit-relevant fact
of what was proposed and why it was refused - while `executed_action`
reflects what the fallback actually did and the new `fallback_reason`
field marks that a fallback occurred. This hook is generic at the runner
level, not arm-conditioned: for a3d_policy itself it is provably dead
code (tests/test_a3d_policy.py's exhaustive gate-compliance proof already
shows a3d_policy's own proposals are accepted over its entire reachable
input space, so `not gate_verdict.accepted` never evaluates True when
`policy is a3d_policy`) - A3-D's behavior is therefore unchanged by this
addition. Only a policy capable of producing a gate-rejected proposal
(A3-LLM) can ever reach this branch. `stale_state` (§11's other
gate-adjacent fallback reason) is NOT implemented here: sim-v1's day loop
is single-threaded and fully synchronous - `view` is built once (step 2)
and consumed by `policy` and `gate` in the same call stack with no
intervening tick - so there is no mechanism by which `state.
subscription_state` could change between view-construction and
gate-evaluation. Genuinely unreachable under this architecture, not
implemented, not simulated.

Day 6 Stage 6B closure - planner-layer fallback auditability. Before this,
a timeout/unparseable/schema_violation fallback (resolved entirely inside
rrx.agent.planner, before this module ever sees a Proposal) was invisible
to the ledger: `policy(view)` returns only a Proposal, so the runner had
no way to learn that Proposal was itself already a fallback. Fixed by
`getattr(policy, "last_fallback_reason", None)` immediately after the
policy call - a3d_policy (a bare function) has no such attribute, so this
is always None for A3-D; rrx.agent.planner.A3LLMPolicy (a callable object)
sets it on every call. No change to PolicyFn's shape - still exactly
`Callable[[EpisodeView], Proposal]` - and no new LedgerRecord field: the
existing `fallback_reason` column is simply populated from one more
source than before.
"""

from __future__ import annotations

from typing import Any, Callable

from rrx.agent.gate import GateVerdict, evaluate_gate
from rrx.agent.ledger import default_ledger_record
from rrx.agent.policy import a3d_policy
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
        fallback_reason: str | None = None
        # Day 6 Stage 6C: declared here (not just inside the wakeup branch)
        # because step 9's ledger_record call below runs on EVERY tick,
        # wakeup or not - these must have a defined, ledger-correct default
        # (matching default_ledger_record's own defaults exactly) on a
        # non-wakeup tick too.
        planner_raw_output: str | None = None
        planner_prompt_hash: str | None = None
        planner_model_version: str | None = None
        planner_template_version: str | None = None
        planner_latency_ms: float | None = None
        planner_tokens_in: int | None = None
        planner_tokens_out: int | None = None
        planner_cost: float = 0.0

        if tick_type == TICK_WAKEUP:
            last_wake_history_len = len(view.contact_history)
            # --- step 4: policy invocation, only on a real wakeup tick ---
            proposal = policy(view)
            # --- step 5: gate (§8's R1-R8, real precedence-ordered check) ---
            gate_verdict = gate(proposal, view)

            # --- Day 6 Stage 6B closure: planner-layer fallback
            # auditability. `policy` is still a plain (EpisodeView) ->
            # Proposal callable (PolicyFn is unchanged) - a3d_policy is a
            # bare function and has no such attribute, so this is None for
            # every A3-D call, always. rrx.agent.planner.A3LLMPolicy (what
            # make_a3_llm_policy now returns) is a callable OBJECT that
            # additionally records its own most recent
            # timeout/unparseable/schema_violation resolution as an
            # attribute, precisely so the runner - which only ever sees
            # the single Proposal a PolicyFn call returns - can recover
            # that provenance for the ledger without changing what a
            # PolicyFn is.
            #
            # Day 6 Stage 6C (6C-1/6C-7): the same getattr mechanism now
            # also recovers every other §14 LLM-only ledger column
            # A3LLMPolicy exposes. Every default below matches
            # default_ledger_record's own default exactly, so a
            # bare-function policy (a3d_policy, null_policy, any test
            # policy) leaves every one of these None/0.0, unchanged from
            # before this addition.
            planner_fallback_reason = getattr(policy, "last_fallback_reason", None)
            planner_raw_output = getattr(policy, "last_raw_output", None)
            planner_prompt_hash = getattr(policy, "last_prompt_hash", None)
            planner_model_version = getattr(policy, "last_model_version", None)
            planner_template_version = getattr(policy, "last_template_version", None)
            planner_latency_ms = getattr(policy, "last_latency_ms", None)
            planner_tokens_in = getattr(policy, "last_tokens_in", None)
            planner_tokens_out = getattr(policy, "last_tokens_out", None)
            planner_cost = getattr(policy, "last_cost_inr", 0.0)

            # --- gate-rejection fallback hook (see module docstring).
            # `exec_proposal`/`exec_gate_verdict` are what the executor
            # below acts on; `proposal`/`gate_verdict` (the ORIGINAL
            # decision) are still what step 9 logs, unchanged. A
            # gate-level rejection is a strictly later, independent
            # failure mode from a planner-layer one (and can only ever
            # apply to a proposal a planner-layer fallback did NOT already
            # produce - a3d_policy's own output is gate-compliant by
            # construction, so if `planner_fallback_reason` is set here,
            # `gate_verdict.accepted` is always True) - "gate_rejected"
            # therefore always takes precedence when both could
            # apply, with no actual case where both do. ---
            if gate_verdict.accepted:
                exec_proposal, exec_gate_verdict = proposal, gate_verdict
                fallback_reason = planner_fallback_reason
            else:
                fallback_reason = "gate_rejected"
                fallback_proposal = a3d_policy(view)
                exec_proposal = fallback_proposal
                exec_gate_verdict = gate(fallback_proposal, view)

            # --- step 6: executor ---
            if exec_gate_verdict.accepted and exec_proposal.action_type == "CONTACT" and (
                exec_proposal.remedy == "card_change"
            ):
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
                    is_agent_contact=True, **send_kwargs,
                )
                if cohort.opening_condition_key == "insufficient_funds":
                    state.card_change_sent_for_insufficient_funds = True
                contact_sent_this_tick = True
                executed_action = {"action_type": "CONTACT", "remedy": "card_change"}
            elif exec_gate_verdict.accepted and exec_proposal.action_type == "CONTACT" and (
                exec_proposal.remedy == "topup_reminder"
            ):
                _send_message(
                    state, day=day, channel=AGENT_CHANNEL, names_card=False, names_dues=True,
                    is_agent_contact=True, **send_kwargs,
                )
                contact_sent_this_tick = True
                executed_action = {"action_type": "CONTACT", "remedy": "topup_reminder"}
            elif exec_gate_verdict.accepted and exec_proposal.action_type == "STOP":
                episode_stopped = True
                executed_action = {"action_type": "STOP"}
            else:
                # WAIT, a rejected/otherwise-unexecutable proposal, or (in
                # principle unreachable, per the module docstring's
                # gate-compliance proof) even the fallback itself being
                # rejected: no state mutation (§3 step 6; §9's executor
                # table).
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
            fallback_reason=fallback_reason,
            prompt_hash=planner_prompt_hash,
            raw_output=planner_raw_output,
            latency_ms=planner_latency_ms,
            tokens_in=planner_tokens_in,
            tokens_out=planner_tokens_out,
            cost=planner_cost,
            model_version=planner_model_version,
            template_version=planner_template_version,
        )

        if capture_view_at_day is not None and day == capture_view_at_day:
            captured_view = build_episode_view(cohort, state, day, episode_cfg, split, i)

    result = _finalize(cohort, state)
    return (result, captured_view) if capture_view_at_day is not None else result
