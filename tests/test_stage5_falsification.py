"""Day 2 Stage 5: the five falsification tests from SIM.md §8.

These are FALSIFICATION tests, not simulator-repair tests. If one fails,
the failure is reported - the simulator (engine.py, latent.py, configs) is
never modified to force a pass.

Two arms this stage needs (A1-ish, the wrong-remedy null policy) are
registered into `rrx.sim.engine._POLICIES` at TEST RUNTIME ONLY, via a
fixture that mutates the dict and reverts it on teardown - engine.py's
SOURCE is never touched, and A0/A2's existing entries are never replaced,
only new keys added. This gets these two arms the exact same `run_episode`
mechanics A0/A2 use, with zero duplication-fidelity risk.

A4 (the oracle) genuinely needs full latent access, which the standard
`(opening_condition_key, day, subscription_state) -> action` policy
interface does not provide. It is implemented as a separate, test-local
episode loop built from the same real, unmodified primitives `run_episode`
itself uses (`_EpisodeState`, `_send_message`, `_retry_succeeds`,
`draw_latent_state`, `sample_cohort_episode`) - not a policy plugged into
`run_episode`.
"""

from __future__ import annotations

import pytest

from rrx.baselines.a1 import a1_action_for_day
from rrx.sim import engine
from rrx.sim.cohort import sample_cohort_episode
from rrx.sim.engine import (
    AGENT_CHANNEL,
    AUTO_EMAIL_CHANNEL,
    EpisodeResult,
    _EpisodeState,
    _retry_succeeds,
    _send_message,
    run_episode,
)
from rrx.sim.latent import MASTER_SEED, draw_latent_state, load_configs
from rrx.sim.run_stage3 import paired_bootstrap_ci

EPISODE_CFG, POPULATION_CFG = load_configs()
SPLIT = "dev"
N = 2000
INDICES = range(1000, 1000 + N)


# ===========================================================================
# Shared arm definitions (Test 1, Test 2)
# ===========================================================================

# HISTORICAL PROVENANCE, preserved: `a1_action_for_day` was originally
# defined locally in this file, self-labelled "A1-ish" throughout this
# module - a naive fixed-contact policy (T+0/T+3, `card_change`
# uniformly, no adaptive reasoning), declared here because, at the time
# this test was written (Day 2 Stage 5, commit `cdd118a`), no frozen
# specification defined A1's remedy content. `eval-spec-v1.6` (`EVAL.md
# §4.3`, `[CONSEQUENTIAL-2]`) later formally adopted this exact
# operationalization as canonical A1. It now lives in
# `src/rrx/baselines/a1.py` and is imported above rather than redefined
# here - behaviorally identical, byte-for-byte, to what this file
# originally declared inline (see `tests/test_a1.py` for the enforcing
# equivalence check). This module's every other reference to "A1-ish" below is left
# as originally written - it documents this test's own history at the
# time it was authored, before canonical adoption existed, and is not
# rewritten to say "A1" merely because the name is now also canonical.


_CARD_CHANGE_IS_CORRECT = frozenset(
    {"card_expired", "debit_instrument_blocked", "card_not_enabled_group", "ambiguous_decline"}
)
_TOPUP_IS_CORRECT = frozenset({"insufficient_funds"})
_NO_CUSTOMER_CONTACT_IS_CORRECT = frozenset(
    {"subscription_cancelled_by_customer", "payment_risk_check_failed"}
)
# transaction_limit_exceeded, bank_technical_error: correct = wait.


def wrong_remedy_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """Test 2's "always-inverted-remedy" policy: for every condition, send
    the content that is NEVER the correct remedy for it, at T+0/T+1/T+3
    (mirroring A2's max scheduling footprint).

    Declared exclusion: `subscription_cancelled_by_customer` and
    `payment_risk_check_failed` are excluded from this arm's action space,
    matching A2's own exclusion - EVAL.md §5.2's gate ("Contacts to
    cancelled or expired Subscriptions: 0") is a hard invariant that binds
    every arm (Stage 3 finding), not a remedy-content choice this test is
    about; "always contact anyway" here would be a gate violation, not a
    wrong-remedy demonstration.
    """
    if opening_condition_key in _NO_CUSTOMER_CONTACT_IS_CORRECT:
        return None
    if day not in (0, 1, 3):
        return None
    if opening_condition_key in _CARD_CHANGE_IS_CORRECT:
        return "topup_reminder"
    if opening_condition_key in _TOPUP_IS_CORRECT:
        return "card_change"
    # transaction_limit_exceeded, bank_technical_error (correct = wait):
    # any active contact is wrong; card_change picked as the fixed content.
    return "card_change"


def post_halt_only_topup_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """Test 3's policy: topup reminders ONLY after the halt boundary
    (days 4-10), never before - isolates the timing-null claim."""
    if opening_condition_key != "insufficient_funds":
        return None
    return "topup_reminder" if 4 <= day <= 10 else None


@pytest.fixture(scope="module", autouse=True)
def _register_test_arms():
    """Adds three new keys to engine._POLICIES at test runtime only -
    engine.py's source file is never modified, and A0/A2's existing
    entries are never touched (verified separately: Test 4 checks A0/A2's
    world draws are unaffected by these arms existing)."""
    engine._POLICIES["A1"] = a1_action_for_day
    engine._POLICIES["WRONG_REMEDY"] = wrong_remedy_action_for_day
    engine._POLICIES["POST_HALT_TOPUP_ONLY"] = post_halt_only_topup_action_for_day
    yield
    del engine._POLICIES["A1"]
    del engine._POLICIES["WRONG_REMEDY"]
    del engine._POLICIES["POST_HALT_TOPUP_ONLY"]


# ===========================================================================
# A4 - the oracle arm (test-local, full latent access, CORRECTED to the
# same 3-contact budget as A1-ish/A2-ish)
# ===========================================================================
#
# CORRECTION (this pass): the original A4 got exactly one contact while
# A1-ish/A2-ish could use up to three - not an apples-to-apples comparison
# under the equal-contact-budget regime. A4 now gets the SAME budget
# (max_contacts_per_episode, episode.yaml#/agent_budget - 3 in the frozen
# config). This is an arm-DEFINITION correction restoring the intended
# comparison, not tuning the policy to force an ordering: the objective and
# the underlying decision LOGIC (which content, which condition needs it)
# are unchanged from the original single-contact version; only how many
# times and on which days that logic is allowed to act has changed, to
# match what A1-ish/A2-ish were always allowed to do.
#
# DECLARED OBJECTIVE (unchanged, before this run): lexicographic - maximize
# invoice recovery rate first; where a choice does not affect invoice
# recovery, maximize subscription rescue rate as the tiebreak.
#
# DECLARED SCOPE OF "full latent access": the four hidden physical-state
# variables (card_chargeable, funds_available_from, mandate_alive,
# blocked_until) at T=0 - never clairvoyance into FUTURE independent RNG
# draws or future engagement outcomes. A4 MAY react to its OWN
# already-resolved state (state.card_chargeable, state.invoice_recovered)
# at each decision point - this is ordinary determinism conditional on the
# RNG stream already consumed by its own prior actions, not a peek forward;
# no future contact's engagement/completion/topup outcome is ever read
# before that contact itself happens.
#
# DECLARED DECISION RULE (deterministic given latent state + own prior
# results; not tuned after seeing this pass's results):
#   - subscription_cancelled_by_customer: no action (mandate dead, nothing
#     helps) - 0 of 3 contacts used.
#   - card_chargeable is False at opening (card-broken bucket, or
#     ambiguous_decline's false draw): send card_change on T+0, T+1, T+2
#     (all three <= the T+3 halt boundary), SKIPPING any of those days on
#     which state.invoice_recovered or state.card_chargeable is ALREADY
#     true (a fact about its own earlier attempts this same episode, not a
#     future peek) - a further attempt would be a guaranteed no-op
#     (_apply_card_naming_effect is idempotent once card_chargeable is
#     true). Placing all three attempts as early as possible is provably
#     equivalent, for the invoice-recovery probability, to any other
#     3-of-{0,1,2,3} placement: since a successful flip persists forever
#     and every one of T+1/T+2/T+3 is a retry day, P(>=1 of 3 independent
#     trials succeeds by T+3) is the same regardless of which 3 days
#     <= T+3 they land on. T+0,T+1,T+2 is chosen because using the
#     earliest days first strictly dominates on the SECONDARY (rescue)
#     objective too (more margin left in the 30-day window for a post-halt
#     attempt in an edge case), never worse on the primary objective.
#   - card_chargeable is True and funds_available_from <= halt_boundary_day
#     AND blocked_until <= halt_boundary_day: no action - invoice recovery
#     is already certain via auto-retry regardless of any contact - 0 of 3
#     contacts used.
#   - card_chargeable is True, the condition is fund-driven
#     (insufficient_funds, or ambiguous_decline's true draw), and
#     funds_available_from > halt_boundary_day: send topup_reminder on
#     T+0, T+1, T+2 (same skip-if-already-recovered logic) - each
#     independent attempt gives a fresh Bernoulli(p_topup_action) trial and,
#     if triggered, a fresh Exponential draw; min(...) across attempts means
#     more tries strictly cannot hurt, and can only lower funds_available_
#     from further.
#   - Otherwise (transaction_limit_exceeded: blocked_until is indefinite,
#     structurally unrecoverable regardless of any action;
#     payment_risk_check_failed: hard_stop/escalate, no customer contact
#     permitted): no action - 0 of 3 contacts used.
#
# Channel: whatsapp (AGENT_CHANNEL) throughout - per SIM.md §6's own
# "channel ranking is not the inferable signal" finding, channel_multipliers
# is a fixed global table, so whatsapp is the objectively best channel for
# every customer regardless of latent access; A4 has nothing to gain from
# "choosing" a channel A2 doesn't already use.

A4_MAX_CONTACTS = 3  # matches episode.yaml#/agent_budget/max_contacts_per_episode


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
    split, i, episode_cfg, population_cfg, master_seed=MASTER_SEED, max_contacts=A4_MAX_CONTACTS
) -> EpisodeResult:
    """A4's episode simulation - reuses the exact same primitives
    run_episode() uses (_EpisodeState, _send_message, _retry_succeeds,
    draw_latent_state, sample_cohort_episode), unmodified. The only new
    logic is the decision rule above; everything else (T+0 auto email, the
    AND-gate, halt + halt-email) is the real mechanism. `max_contacts`
    defaults to the same 3-contact budget A1-ish/A2-ish use."""
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


# ===========================================================================
# TEST 1 - policy ordering: A4 > A2-ish > A1-ish > A0, A0 > 0
# ===========================================================================

def test_1_policy_ordering():
    a0 = [run_episode(SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    a1 = [run_episode(SPLIT, i, "A1", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    a2 = [run_episode(SPLIT, i, "A2", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    a4 = [run_a4_episode(SPLIT, i, EPISODE_CFG, POPULATION_CFG) for i in INDICES]

    # Budget-parity proof: A4's per-episode contact cap must equal the same
    # 3-contact budget A1-ish/A2-ish operate under (episode.yaml#/
    # agent_budget/max_contacts_per_episode) - not merely equal by
    # coincidence of these particular results.
    frozen_budget = EPISODE_CFG["agent_budget"]["max_contacts_per_episode"]
    assert A4_MAX_CONTACTS == frozen_budget, (
        f"A4_MAX_CONTACTS ({A4_MAX_CONTACTS}) != the frozen agent budget ({frozen_budget})"
    )
    max_contacts_observed = {
        "A0": max(r.contacts_sent for r in a0),
        "A1": max(r.contacts_sent for r in a1),
        "A2": max(r.contacts_sent for r in a2),
        "A4": max(r.contacts_sent for r in a4),
    }
    print(f"\nBudget parity - max contacts_sent observed per arm: {max_contacts_observed}")
    assert max_contacts_observed["A4"] <= A4_MAX_CONTACTS
    assert max_contacts_observed["A1"] <= A4_MAX_CONTACTS
    assert max_contacts_observed["A2"] <= A4_MAX_CONTACTS

    def rate(results):
        return sum(r.invoice_recovered for r in results) / len(results)

    def rescue_rate(results):
        return sum(r.subscription_rescued for r in results) / len(results)

    r0, r1, r2, r4 = rate(a0), rate(a1), rate(a2), rate(a4)
    s0, s1, s2, s4 = rescue_rate(a0), rescue_rate(a1), rescue_rate(a2), rescue_rate(a4)

    print(f"Test 1 invoice recovery: A0={r0:.4f} A1={r1:.4f} A2={r2:.4f} A4={r4:.4f}")
    print(f"Test 1 subscription rescue: A0={s0:.4f} A1={s1:.4f} A2={s2:.4f} A4={s4:.4f}")

    assert r0 > 0, f"A0 invoice recovery rate must be > 0, got {r0}"

    a0_inv = [float(r.invoice_recovered) for r in a0]
    a1_inv = [float(r.invoice_recovered) for r in a1]
    a2_inv = [float(r.invoice_recovered) for r in a2]
    a4_inv = [float(r.invoice_recovered) for r in a4]
    a2_res = [float(r.subscription_rescued) for r in a2]
    a4_res = [float(r.subscription_rescued) for r in a4]

    d_10, lo_10, hi_10 = paired_bootstrap_ci(a0_inv, a1_inv, n_resamples=5000)
    d_21, lo_21, hi_21 = paired_bootstrap_ci(a1_inv, a2_inv, n_resamples=5000)
    d_42, lo_42, hi_42 = paired_bootstrap_ci(a2_inv, a4_inv, n_resamples=5000)
    dr_42, lor_42, hir_42 = paired_bootstrap_ci(a2_res, a4_res, n_resamples=5000)

    print(f"A1-A0 diff={d_10:+.4f} CI=[{lo_10:+.4f},{hi_10:+.4f}]")
    print(f"A2-A1 diff={d_21:+.4f} CI=[{lo_21:+.4f},{hi_21:+.4f}]")
    print(
        f"A4-A2 invoice-recovery diff={d_42:+.4f} CI=[{lo_42:+.4f},{hi_42:+.4f}]  "
        f"<- empirical oracle headroom over A2"
    )
    print(
        f"A4-A2 subscription-rescue diff={dr_42:+.4f} CI=[{lor_42:+.4f},{hir_42:+.4f}]"
    )

    failures = []
    if not (d_10 > 0 and lo_10 > 0):
        failures.append(
            f"A1-ish did not significantly beat A0 on invoice recovery: "
            f"diff={d_10:+.4f} CI=[{lo_10:+.4f},{hi_10:+.4f}]"
        )
    if not (d_21 > 0 and lo_21 > 0):
        failures.append(
            f"A2-ish did not significantly beat A1-ish on invoice recovery: "
            f"diff={d_21:+.4f} CI=[{lo_21:+.4f},{hi_21:+.4f}]"
        )
    if not (d_42 > 0 and lo_42 > 0):
        failures.append(
            f"A4 did not significantly beat A2-ish on invoice recovery: "
            f"diff={d_42:+.4f} CI=[{lo_42:+.4f},{hi_42:+.4f}]"
        )

    # Sanity check on the oracle ceiling, not a pass/fail assertion:
    # subscription_cancelled_by_customer (~5%) and payment_risk_check_failed
    # (~1%) can never recover regardless of any action (mandate dead /
    # hard_stop), so r4 should be well below 0.95, not approaching 1.0.
    if r4 > 0.95:
        print(
            f"WARNING: A4 invoice recovery {r4:.4f} approaches an implausible "
            f"ceiling given >=6% of the population is structurally "
            f"unrecoverable - possible oracle-definition or simulator problem."
        )

    if failures:
        pytest.fail("Test 1 (policy ordering) FAILED:\n" + "\n".join(failures))


# ===========================================================================
# TEST 2 - wrong-remedy null
# ===========================================================================

def test_2_wrong_remedy_null():
    a0 = [run_episode(SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    a2 = [run_episode(SPLIT, i, "A2", EPISODE_CFG, POPULATION_CFG) for i in INDICES]
    wr = [run_episode(SPLIT, i, "WRONG_REMEDY", EPISODE_CFG, POPULATION_CFG) for i in INDICES]

    def rate(results):
        return sum(r.invoice_recovered for r in results) / len(results)

    r0, r2, rwr = rate(a0), rate(a2), rate(wr)

    a0_inv = [float(r.invoice_recovered) for r in a0]
    wr_inv = [float(r.invoice_recovered) for r in wr]
    diff, lo, hi = paired_bootstrap_ci(a0_inv, wr_inv, n_resamples=5000)

    a2_contacts = sum(r.contacts_sent for r in a2)
    wr_contacts = sum(r.contacts_sent for r in wr)
    ratio = wr_contacts / a2_contacts

    print(f"\nTest 2: A0={r0:.4f} A2={r2:.4f} WRONG_REMEDY={rwr:.4f}")
    print(f"WRONG_REMEDY - A0 diff={diff:+.4f} CI=[{lo:+.4f},{hi:+.4f}]")
    print(f"contacts: A2={a2_contacts} WRONG_REMEDY={wr_contacts} ratio={ratio:.4f}")

    if abs(ratio - 3.0) > 0.3:
        print(f"NOTE: wrong-remedy/A2 contact ratio is {ratio:.4f}, not close to the "
              f"originally-cited 3x. A2's own average contact count (not just the "
              f"wrong-remedy policy's) determines this ratio, and A2's schedule "
              f"(1-2 contacts for most conditions, occasionally more) was itself "
              f"defined after the '3x' figure was written into SIM.md §8 - the 3x "
              f"figure appears to be a stale estimate from before A2's exact schedule "
              f"was fixed, not a property this test can tune the policy to hit.")

    failures = []
    # "recovery approximately comparable to A0": CI must include zero, or the
    # point difference must be small in absolute terms.
    if not (lo <= 0 <= hi or abs(diff) < 0.02):
        failures.append(
            f"WRONG_REMEDY invoice recovery not comparable to A0: "
            f"diff={diff:+.4f} CI=[{lo:+.4f},{hi:+.4f}]"
        )
    if not (ratio > 1.0):
        failures.append(f"WRONG_REMEDY did not have higher contact cost than A2: ratio={ratio:.4f}")

    if failures:
        pytest.fail("Test 2 (wrong-remedy null) FAILED:\n" + "\n".join(failures))


# ===========================================================================
# TEST 3 - timing null: post-halt top-up has ~zero effect on invoice recovery
# ===========================================================================

def test_3_timing_null():
    a0 = [
        run_episode(SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG) for i in INDICES
    ]
    post_halt = [
        run_episode(SPLIT, i, "POST_HALT_TOPUP_ONLY", EPISODE_CFG, POPULATION_CFG) for i in INDICES
    ]

    # Scope to insufficient_funds only - the only condition this policy acts on.
    pairs = [
        (a.invoice_recovered, p.invoice_recovered)
        for a, p in zip(a0, post_halt)
        if a.opening_condition_key == "insufficient_funds"
    ]
    assert pairs, "no insufficient_funds episodes found in range"

    a0_inv = [float(x) for x, _ in pairs]
    ph_inv = [float(y) for _, y in pairs]
    diff, lo, hi = paired_bootstrap_ci(a0_inv, ph_inv, n_resamples=5000)

    n_matched = sum(1 for x, y in pairs if x == y)
    print(
        f"\nTest 3: n(insufficient_funds)={len(pairs)}, "
        f"exact-match rate={n_matched / len(pairs):.4f}"
    )
    print(f"post-halt-topup - A0 invoice recovery diff={diff:+.4f} CI=[{lo:+.4f},{hi:+.4f}]")

    # Mechanistically this must be EXACTLY zero (not just approximately):
    # _apply_dues_naming_effect returns False, unconsumed, for day >
    # halt_boundary_day - no topup draw ever fires post-halt, so outcomes
    # must be byte-identical to A0 for every paired episode.
    if diff != 0.0 or n_matched != len(pairs):
        pytest.fail(
            f"Test 3 (timing null) FAILED: post-halt topup changed invoice recovery "
            f"(diff={diff:+.4f}, {len(pairs) - n_matched}/{len(pairs)} episodes differ from A0) - "
            f"expected exact equality, since the halt-boundary guard should make every "
            f"post-halt topup attempt a structural no-op."
        )


# ===========================================================================
# TEST 4 - CRN identity
# ===========================================================================

def test_4_crn_identity_across_all_arms():
    """Same episode index -> identical opening condition, invoice amount,
    and full LatentState, across every arm this stage defines (including
    the three new ones) - proves _register_test_arms did not disturb CRN,
    and that A4's separate loop draws the identical world A0/A1/A2/
    WRONG_REMEDY/POST_HALT_TOPUP_ONLY draw."""
    mismatches = []
    for i in list(INDICES)[:300]:
        cohort_ref = sample_cohort_episode(SPLIT, i, POPULATION_CFG)
        latent_ref = draw_latent_state(
            SPLIT, i, cohort_ref.opening_condition_key, EPISODE_CFG, POPULATION_CFG
        )

        results = {
            arm: run_episode(SPLIT, i, arm, EPISODE_CFG, POPULATION_CFG)
            for arm in ("A0", "A1", "A2", "WRONG_REMEDY", "POST_HALT_TOPUP_ONLY")
        }
        results["A4"] = run_a4_episode(SPLIT, i, EPISODE_CFG, POPULATION_CFG)

        for arm, r in results.items():
            if r.opening_condition_key != cohort_ref.opening_condition_key:
                mismatches.append((i, arm, "opening_condition_key"))
            if r.invoice_amount_inr != cohort_ref.invoice_amount_inr:
                mismatches.append((i, arm, "invoice_amount_inr"))

        # Direct re-draw determinism (the actual latent world, not just the
        # cohort-level summary) - proves nothing about these arms' existence
        # perturbed the underlying CRN scheme.
        latent_again = draw_latent_state(
            SPLIT, i, cohort_ref.opening_condition_key, EPISODE_CFG, POPULATION_CFG
        )
        if latent_again != latent_ref:
            mismatches.append((i, "direct_redraw", "LatentState"))

    print(f"\nTest 4: checked {len(list(INDICES)[:300])} episode indices across 6 arms, "
          f"{len(mismatches)} mismatches")

    if mismatches:
        pytest.fail(
            f"Test 4 (CRN identity) FAILED: {len(mismatches)} mismatches, e.g. {mismatches[:5]}"
        )


# ===========================================================================
# TEST 5 - responsiveness-signal null (Stage 4B narrowed formulation)
# ===========================================================================
#
# PRE-DECLARED, BEFORE RUNNING: everything in this block is fixed before any
# Test 5 result is observed.
#
# Mechanism under test: channel_response_trait (theta_c) is drawn ONCE per
# episode and reused for every message sent in that episode (rrx.sim.engine.
# run_episode threads the same `latent` object through every _send_message
# call via send_kwargs). An ADAPTIVE policy that observes contact_history.
# engaged after an early contact and decides whether to send a second one
# can exploit this persistence; a NON-ADAPTIVE control cannot.
#
# Fixed opening condition: "card_expired" for every synthetic episode in
# this test (draw_latent_state called directly with this key, bypassing
# cohort condition sampling) - isolates the responsiveness signal from
# cross-condition population heterogeneity, which is irrelevant to what
# this test measures (engagement only, not recovery outcomes).
_T5_KEY = "card_expired"
_T5_N = 3000
_T5_INDICES = range(5000, 5000 + _T5_N)
_T5_CONCENTRATION_BASELINE = 7  # episode.yaml's frozen value - unchanged.
_T5_CONCENTRATION_HIGH = 1_000_000  # "sufficiently high": see variance check below.
_T5_MEANINGFUL_EFFECT_MIN = 0.02  # normal-concentration effect must exceed this.
_T5_COLLAPSE_TOLERANCE = 0.02  # high-concentration effect must fall within +/- this of zero.


def _episode_cfg_with_concentration(concentration: float) -> dict:
    import copy

    cfg = copy.deepcopy(EPISODE_CFG)
    cfg["latent"]["channel_response_propensity"]["customer_trait"]["concentration"] = concentration
    return cfg


def _theta_c_variance(mean: float, concentration: float) -> float:
    """Closed-form Beta(alpha, beta) variance, alpha=mean*C, beta=(1-mean)*C:
    Var = mean(1-mean) / (concentration + 1)."""
    return mean * (1.0 - mean) / (concentration + 1.0)


def _run_two_contact_episode(split, i, episode_cfg, adaptive: bool, master_seed=MASTER_SEED):
    """ADAPTIVE: send contact 1 at T+0; OBSERVE state.contact_history[-1].
    engaged (a real ContactRecord, produced by the real _send_message); send
    contact 2 at T+3 ONLY if engaged. NON-ADAPTIVE control: always send
    both. Both use the real _EpisodeState/_send_message - not a
    reimplementation of the engagement mechanism."""
    latent = draw_latent_state(split, i, _T5_KEY, episode_cfg, POPULATION_CFG, master_seed)
    state = _EpisodeState(latent, condition_kind="decline_code")
    send_kwargs = dict(
        split=split, i=i, latent=latent, episode_cfg=episode_cfg, master_seed=master_seed
    )

    _send_message(
        state, day=0, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
        is_agent_contact=True, **send_kwargs,
    )
    first_engaged = state.contact_history[-1].engaged  # observing contact_history.engaged

    send_second = first_engaged if adaptive else True
    if send_second:
        _send_message(
            state, day=3, channel=AGENT_CHANNEL, names_card=True, names_dues=False,
            is_agent_contact=True, **send_kwargs,
        )

    contacts_sent = len(state.contact_history)
    engaged_count = sum(1 for r in state.contact_history if r.engaged)
    return contacts_sent, engaged_count


def _yield_for(episode_cfg, adaptive: bool) -> float:
    total_contacts = 0
    total_engaged = 0
    for i in _T5_INDICES:
        c, e = _run_two_contact_episode("dev", i, episode_cfg, adaptive)
        total_contacts += c
        total_engaged += e
    return total_engaged / total_contacts


def test_5_responsiveness_signal_null():
    mean = EPISODE_CFG["latent"]["channel_response_propensity"]["customer_trait"]["mean"]
    var_baseline = _theta_c_variance(mean, _T5_CONCENTRATION_BASELINE)
    var_high = _theta_c_variance(mean, _T5_CONCENTRATION_HIGH)
    print(
        f"\nTest 5: theta_c variance baseline (C={_T5_CONCENTRATION_BASELINE})="
        f"{var_baseline:.6f}, high (C={_T5_CONCENTRATION_HIGH})={var_high:.10f}"
    )
    assert var_high < var_baseline / 1000, "high concentration did not collapse variance"

    cfg_baseline = EPISODE_CFG
    cfg_high = _episode_cfg_with_concentration(_T5_CONCENTRATION_HIGH)

    yield_adaptive_baseline = _yield_for(cfg_baseline, adaptive=True)
    yield_control_baseline = _yield_for(cfg_baseline, adaptive=False)
    yield_adaptive_high = _yield_for(cfg_high, adaptive=True)
    yield_control_high = _yield_for(cfg_high, adaptive=False)

    effect_baseline = yield_adaptive_baseline - yield_control_baseline
    effect_high = yield_adaptive_high - yield_control_high

    print(
        f"yield adaptive/control @ baseline concentration: "
        f"{yield_adaptive_baseline:.4f} / {yield_control_baseline:.4f}"
    )
    print(
        f"yield adaptive/control @ high concentration:     "
        f"{yield_adaptive_high:.4f} / {yield_control_high:.4f}"
    )
    print(
        f"effect @ baseline = {effect_baseline:+.4f} "
        f"(pre-declared must exceed +{_T5_MEANINGFUL_EFFECT_MIN})"
    )
    print(
        f"effect @ high     = {effect_high:+.4f} "
        f"(pre-declared must fall within +/-{_T5_COLLAPSE_TOLERANCE} of zero)"
    )

    failures = []
    if not (effect_baseline > _T5_MEANINGFUL_EFFECT_MIN):
        failures.append(
            f"No meaningful adaptive advantage at baseline concentration: "
            f"effect={effect_baseline:+.4f}, required > {_T5_MEANINGFUL_EFFECT_MIN}"
        )
    if not (abs(effect_high) <= _T5_COLLAPSE_TOLERANCE):
        failures.append(
            f"Adaptive advantage did not collapse under high concentration: "
            f"effect={effect_high:+.4f}, required within +/-{_T5_COLLAPSE_TOLERANCE}"
        )

    if failures:
        pytest.fail("Test 5 (responsiveness-signal null) FAILED:\n" + "\n".join(failures))
