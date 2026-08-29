# DAY5-CONTEXT-DUMP-2.md

Read-only inspection, pass 2 — targeted follow-up on gaps flagged in
`docs/handoff/DAY5-CONTEXT-DUMP.md` (pass 1). Same absolute rules: no
file other than this one created or modified; no git state change; no
evaluation/sweep/agent/holdout run; pytest not re-run in this pass (pass
1 already ran it once this session, satisfying the "at most once"
allowance — its result is reused here where cited, not re-executed).
Pass 1 is not modified. Generated 2026-08-27.

---

## 1. A1 / A4 / A2-VARIANT CONSTRUCTION

**Path:** `tests/test_stage5_falsification.py`. **Line count:** 670.

### Complete verbatim contents

```python
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

def a1_action_for_day(opening_condition_key: str, day: int, subscription_state: str) -> str | None:
    """A1-ish (declared, per the task): naive fixed-contact policy - two
    contacts at T+0 and T+3, regardless of opening condition or
    subscription state, no adaptive reasoning. Content choice (declared
    here, since the task does not specify one): `card_change` uniformly -
    a generic default, matching what Razorpay's own automatic email
    emphasizes as primary content (SIM.md §3's action table)."""
    return "card_change" if day in (0, 3) else None


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
```

### Direct answers

**How is A1 constructed?** A **module-level function**,
`a1_action_for_day(opening_condition_key, day, subscription_state) ->
str | None` (lines 51-58 above), matching `rrx.sim.engine`'s
`(opening_condition_key, day, subscription_state) -> action | None`
policy-callable interface exactly — not a closure, not a lambda, not an
inline schedule dict. Body: `return "card_change" if day in (0, 3) else
None`.

**Registration:** Yes — `_register_test_arms`, a `pytest.fixture(scope=
"module", autouse=True)` (lines 109-121), runs once per test module
collection: `engine._POLICIES["A1"] = a1_action_for_day` (plus
`"WRONG_REMEDY"` and `"POST_HALT_TOPUP_ONLY"`). **It IS unregistered**:
the fixture's teardown (`yield` then `del engine._POLICIES["A1"]` etc.)
removes all three keys after the module's tests finish — `engine.
_POLICIES` reverts to just `{"A0": ..., "A2": ...}` once this test file
is done running.

**A1's contact schedule vs EVAL §4's "T+0 and T+3":** **YES, matches
exactly.** `a1_action_for_day`'s body: `"card_change" if day in (0, 3)
else None` — contacts on day 0 and day 3, `card_change` content every
time, matching `EVAL.md:264`'s "**A1 — Naive dunning**: Same two contacts
to everyone at T+0 and T+3, regardless of state or reason." One
divergence: `EVAL.md §1.2`'s row table lists `send_card_change_prompt`
as one of several named remedies without specifying A1's *content*
choice; this test module's own docstring for `a1_action_for_day`
explicitly "declares" the `card_change` content choice itself, since
EVAL.md's arms table does not specify one.

**A4:** Also a **module-level function pair** — `_a4_content_for_condition`
(the per-condition decision rule, lines 200-217) plus
`run_a4_episode(split, i, episode_cfg, population_cfg, master_seed,
max_contacts)` (lines 220-296), a **full, separate episode-loop
function** — not a policy plugged into `run_episode()`/`_POLICIES` at
all (A4 needs full `LatentState` access, which the
`(opening_condition_key, day, subscription_state)` policy signature
cannot provide). **Never registered into `_POLICIES`** — it is invoked
directly as `run_a4_episode(...)`, a parallel code path, not an
arm-string lookup.

**What latent state does A4 read, and through which import?** The full
`LatentState` object returned by `draw_latent_state(split, i,
cohort.opening_condition_key, episode_cfg, population_cfg, master_seed)`
— imported at the top of the file as `from rrx.sim.latent import
MASTER_SEED, draw_latent_state, load_configs` — a **direct import from
`rrx.sim.latent`**, not routed through `rrx.sim.engine`'s re-export (the
way `src/rrx/harness/runner.py` does it, per Section 8 of pass 1). This
is legitimate here specifically because `tests/` is not a
`GUARDED_PACKAGES` member (`test_no_latent_leak.py`'s guard only covers
`rrx/agent` and `rrx/features`) — A4 is explicitly the oracle arm and is
supposed to see everything.

**A2-corrected-v1 / A2-strengthened — registered here?** **NO.** They do
not appear anywhere in this file. They are registered in a **different**
file, `tests/test_a2_variants.py` (confirmed by direct grep):

```
tests/test_a2_variants.py:33:    engine._POLICIES["A2_CORRECTED_V1"] = a2_corrected_v1_action_for_day
tests/test_a2_variants.py:34:    engine._POLICIES["A2_STRENGTHENED"] = a2_strengthened_action_for_day
tests/test_a2_variants.py:36:    del engine._POLICIES["A2_CORRECTED_V1"]
tests/test_a2_variants.py:37:    del engine._POLICIES["A2_STRENGTHENED"]
```

Exact arm-key strings: **`"A2_CORRECTED_V1"`** and **`"A2_STRENGTHENED"`**
— both registered and torn down by an analogous module-scoped autouse
fixture in `test_a2_variants.py`, following the identical pattern to
`test_stage5_falsification.py`'s `_register_test_arms`.

**Is A1-U (unbounded) constructed anywhere?** **MISSING.** Repo-wide
grep for `A1-U`, `A1_U`, `a1_u` (case-insensitive variants, all
`.py` files, `.venv` excluded) returns zero hits. `EVAL.md:264`'s A1-U
row ("A1 with the contact cap removed, safety gates still on") has no
corresponding implementation anywhere in this repository — not even as a
test-local scratch arm.

**What would be required to run A1 and A2-strengthened over
`DEV_INDICES` from non-test code, given current registration?**
(Described, not implemented.) Both policies are plain, already-importable
functions (`tests.test_stage5_falsification.a1_action_for_day` and
`rrx.baselines.a2_variants.a2_strengthened_action_for_day`) with
`rrx.sim.engine`'s standard `(opening_condition_key, day,
subscription_state) -> str | None` signature. A non-test caller would
need to: (1) import `a1_action_for_day` — currently only defined inside a
`tests/` module, which is not a normal import target for production code
without adding it to `sys.path` or relocating the function into a
non-test module (`a2_strengthened_action_for_day` has no such problem —
it already lives in `src/rrx/baselines/a2_variants.py`); (2) register
both under keys in `rrx.sim.engine._POLICIES` (temporarily, or
permanently, mirroring the fixture pattern but outside `pytest`); (3)
call `rrx.sim.engine.run_episode(DEV_SPLIT, i, "<key>", EPISODE_CFG,
POPULATION_CFG)` for `i in DEV_INDICES` (`src/rrx/harness/splits.py`);
(4) aggregate `EpisodeResult`s into rate/contact metrics using the same
inline pattern both test files already use (no shared metrics module
exists — pass 1 Section 8 gap 3 / this pass's Section 2 confirm this
again). No CLI or script currently does any of this outside a `pytest`
run.

**Inline metric computation quoted (this file):**

```python
def rate(results):
    return sum(r.invoice_recovered for r in results) / len(results)

def rescue_rate(results):
    return sum(r.subscription_rescued for r in results) / len(results)
```
(Test 1, lines 328-332; Test 2 redefines an equivalent local `rate`
inline at lines 405-406.) Contact counting: `sum(r.contacts_sent for r
in a2)` / `sum(r.contacts_sent for r in wr)` (Test 2, lines 414-415).

**`paired_bootstrap_ci` call sites and their `n_resamples` arguments**
(every single call in this file uses **5000**, never the module-level
10,000 default):

```
line 349: d_10,  lo_10,  hi_10  = paired_bootstrap_ci(a0_inv, a1_inv, n_resamples=5000)
line 350: d_21,  lo_21,  hi_21  = paired_bootstrap_ci(a1_inv, a2_inv, n_resamples=5000)
line 351: d_42,  lo_42,  hi_42  = paired_bootstrap_ci(a2_inv, a4_inv, n_resamples=5000)
line 352: dr_42, lor_42, hir_42 = paired_bootstrap_ci(a2_res, a4_res, n_resamples=5000)
line 412: diff, lo, hi          = paired_bootstrap_ci(a0_inv, wr_inv, n_resamples=5000)
line 468: diff, lo, hi          = paired_bootstrap_ci(a0_inv, ph_inv, n_resamples=5000)
```
---

## 2. SWEEP REGISTRY AND MANIFEST

**Path:** `src/rrx/spec/registry.py`. **Line count:** 304.

### Complete verbatim contents

```python
"""Loader for configs/model_params.yaml.

Spec machinery only. Contains no simulation, no agent, no policy.
Its whole job is to make EVAL.md §8.2 machine-checkable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# The canonical six. This list is the assertion target for
# tests/test_model_params_registry.py and must match EVAL.md §8.2 verbatim.
# Adding a seventh is a spec change requiring a new eval-spec version tag.
CANONICAL_MODEL_PARAMS: tuple[str, ...] = (
    "invoice_amount",
    "failure_mix_weights",
    "balance_restore_timing",
    "channel_response_propensity",
    "card_change_completion_propensity",
    "cancellation_hazard_and_ltv",
)

REQUIRED_FIELDS = ("eval_section", "status", "provenance", "kind",
                   "owner_path", "regime", "handle", "sweep")

VALID_STATUS = {"specified", "unspecified"}


def config_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "configs"


@dataclass(frozen=True)
class Registry:
    raw: dict[str, Any]

    @property
    def parameters(self) -> dict[str, Any]:
        return self.raw["parameters"]

    @property
    def sweep(self) -> dict[str, Any]:
        return self.raw["sweep"]

    def specified(self) -> dict[str, Any]:
        return {k: v for k, v in self.parameters.items()
                if v.get("status") == "specified"}

    def unspecified(self) -> dict[str, Any]:
        return {k: v for k, v in self.parameters.items()
                if v.get("status") == "unspecified"}


def load_registry(path: Path | None = None) -> Registry:
    path = path or (config_dir() / "model_params.yaml")
    with open(path) as fh:
        return Registry(yaml.safe_load(fh))


def resolve_owner_path(owner_path: str, cfg_dir: Path | None = None) -> Any:
    """Resolve 'population.yaml#/a/b' to the value at that key path.

    Raises KeyError/FileNotFoundError if the pointer is stale. This is the
    test that keeps the registry from drifting away from the configs.
    """
    cfg_dir = cfg_dir or config_dir()
    if "#" not in owner_path:
        raise ValueError(f"owner_path missing '#' fragment: {owner_path}")
    filename, fragment = owner_path.split("#", 1)
    with open(cfg_dir / filename) as fh:
        doc = yaml.safe_load(fh)
    node = doc
    for part in [p for p in fragment.strip("/").split("/") if p]:
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"{owner_path}: no key {part!r}")
        node = node[part]
    return node


# --------------------------------------------------------------------------
# Failure-mix bucket perturbation (locked decision 3)
# --------------------------------------------------------------------------

def perturb_bucket(buckets: dict[str, float], target: str,
                   direction: str, magnitude: float = 0.30) -> dict[str, float]:
    """Scale one bucket's mass by (1 +/- magnitude), renormalise the rest.

    The non-target buckets are rescaled proportionally so their relative
    ratios are untouched and the whole vector still sums to 1.0.
    """
    if target not in buckets:
        raise KeyError(target)
    if direction not in ("low", "high"):
        raise ValueError(direction)

    factor = (1.0 - magnitude) if direction == "low" else (1.0 + magnitude)
    new_target = buckets[target] * factor
    if not 0.0 <= new_target <= 1.0:
        raise ValueError(f"{target} {direction} leaves [0,1]: {new_target}")

    others_mass = sum(v for k, v in buckets.items() if k != target)
    if others_mass <= 0:
        raise ValueError("no residual mass to renormalise")
    scale = (1.0 - new_target) / others_mass

    out = {k: (new_target if k == target else v * scale)
           for k, v in buckets.items()}
    return out


def expand_to_conditions(bucket_weights: dict[str, float],
                         members: dict[str, list[str]],
                         baseline_conditions: dict[str, float]
                         ) -> dict[str, float]:
    """Split each bucket's mass across its member conditions using the
    BASELINE within-bucket ratios (locked decision 3)."""
    out: dict[str, float] = {}
    for bucket, mass in bucket_weights.items():
        names = members[bucket]
        base = {n: baseline_conditions[n] for n in names}
        total = sum(base.values())
        for n in names:
            out[n] = mass * (base[n] / total)
    return out


# --------------------------------------------------------------------------
# Cell enumeration
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    cell_id: str
    parameter: str
    handle: str
    direction: str
    value: Any
    low_information: bool = False


def enumerate_cells(reg: Registry) -> list[Cell]:
    """One-at-a-time grid. Baseline is not a cell; it is the reference run."""
    cells: list[Cell] = []
    include_topup = reg.sweep.get("include_topup_acceleration_cells", False)

    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        if p["status"] != "specified" or not p["sweep"].get("swept", False):
            continue

        if p["kind"] == "vector_simplex":
            for bucket, spec in p["handle"]["buckets"].items():
                for direction in reg.sweep["directions"]:
                    cells.append(Cell(
                        cell_id=f"{name}.{bucket}.{direction}",
                        parameter=name,
                        handle=f"bucket_mass:{bucket}",
                        direction=direction,
                        value=perturb_bucket(
                            {b: s["baseline"]
                             for b, s in p["handle"]["buckets"].items()},
                            bucket, direction, p["sweep"]["magnitude"]),
                        low_information=spec.get("low_information", False),
                    ))
        else:
            for direction in reg.sweep["directions"]:
                cells.append(Cell(
                    cell_id=f"{name}.{direction}",
                    parameter=name,
                    handle=p["handle"]["name"],
                    direction=direction,
                    value=p["sweep"]["cells"][direction],
                ))

    if include_topup:
        base = (reg.parameters["balance_restore_timing"]["definition"]
                ["topup_acceleration"]["p_topup_action"])
        mag = reg.sweep["default_magnitude"]
        for direction, f in (("low", 1 - mag), ("high", 1 + mag)):
            cells.append(Cell(
                cell_id=f"balance_restore_timing.topup_acceleration.{direction}",
                parameter="balance_restore_timing",
                handle="p_topup_action",
                direction=direction,
                value=round(base * f, 6),
            ))

    # Any [MODEL] magnitude nested inside a parameter's definition: block and
    # marked sweep_required: true must reach the grid too - EVAL.md §0 does
    # not exempt nested magnitudes. Distinct from the include_topup special
    # case above: p_topup_action uses swept: false (an open, un-swept toggle
    # per DEFECT 1), not sweep_required, so it is untouched by this loop.
    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        definition = p.get("definition")
        if not definition:
            continue
        for path, node in _sweep_required_nodes(definition):
            sweep = node.get("sweep") or {}
            node_cells = sweep.get("cells")
            if not node_cells:
                # Deliberately lenient: a sweep_required node with no cells
                # contributes none here. tests/test_model_params_swept.py's
                # test_all_sweep_required_entries_produce_cells is what turns
                # this into a failure, so the gap is caught at test time with
                # a clear message rather than as a silent skip.
                continue
            for direction in reg.sweep["directions"]:
                if direction not in node_cells:
                    continue
                cells.append(Cell(
                    cell_id=f"{name}.{path}.{direction}",
                    parameter=name,
                    handle=sweep.get("handle", path),
                    direction=direction,
                    value=node_cells[direction],
                ))

    return cells


def _sweep_required_nodes(node: Any, path: str = "") -> list[tuple[str, dict]]:
    """Recursively find every dict node with sweep_required: true.

    Does not descend into a node once found - a sweep_required node is a
    leaf for this purpose, not a container of further sweep_required nodes.
    """
    found: list[tuple[str, dict]] = []
    if isinstance(node, dict):
        if node.get("sweep_required") is True:
            found.append((path, node))
            return found
        for key, value in node.items():
            sub_path = f"{path}.{key}" if path else key
            found.extend(_sweep_required_nodes(value, sub_path))
    return found


def find_sweep_required_nodes(reg: Registry) -> list[tuple[str, str]]:
    """(parameter, path) for every sweep_required: true node anywhere in
    any of the six canonical parameters' definition: blocks."""
    out: list[tuple[str, str]] = []
    for name in CANONICAL_MODEL_PARAMS:
        definition = reg.parameters[name].get("definition")
        if not definition:
            continue
        out.extend((name, path) for path, _ in _sweep_required_nodes(definition))
    return out


def scalar_valued_handles(reg: Registry, parameter: str) -> set[str]:
    """Handles, among `parameter`'s definition-nested sweep_required nodes,
    whose declared sweep.cells values are scalars rather than vectors/dicts.

    Lets a caller distinguish a legitimate scalar [MODEL] magnitude (e.g.
    failure_mix_weights.ambiguous_cause_split's p_card_cause) from a
    bucket-vector cell that has been corrupted into a scalar - see
    tests/test_failure_mix_simplex.py's companion assertion to the
    isinstance(c.value, dict) guard.
    """
    definition = reg.parameters[parameter].get("definition")
    if not definition:
        return set()
    out: set[str] = set()
    for path, node in _sweep_required_nodes(definition):
        sweep = node.get("sweep") or {}
        node_cells = sweep.get("cells") or {}
        if node_cells and all(isinstance(v, (int, float))
                              for v in node_cells.values()):
            out.add(sweep.get("handle", path))
    return out


def unswept_required_entries(reg: Registry,
                              cells: list[Cell] | None = None) -> list[str]:
    """'{parameter}.{path}' for every sweep_required: true node that has no
    corresponding cell in enumerate_cells(reg).

    This is the check that today's bug needed: ambiguous_cause_split and
    transient_block_clearance were both marked sweep_required: true but had
    no sweep.cells, so enumerate_cells() silently produced zero cells for
    them and no existing test noticed, because none of them looked inside
    definition: blocks.
    """
    cells = cells if cells is not None else enumerate_cells(reg)
    missing: list[str] = []
    for name, path in find_sweep_required_nodes(reg):
        prefix = f"{name}.{path}."
        if not any(c.parameter == name and c.cell_id.startswith(prefix)
                   for c in cells):
            missing.append(f"{name}.{path}")
    return missing


def required_wins(n_cells: int, reg: Registry) -> int:
    thr = reg.sweep["majority_threshold"]
    if reg.sweep.get("rounding", "ceil") == "ceil":
        return math.ceil(thr * n_cells)
    return round(thr * n_cells)
```

**`enumerate_cells()` signature, return type, `Cell` structure:**
`enumerate_cells(reg: Registry) -> list[Cell]`. `Cell` is a frozen
dataclass: `cell_id: str, parameter: str, handle: str, direction: str,
value: Any, low_information: bool = False`.

**Exact cell count — CONFIRMED 26, NOT 22.** `tests/test_model_params_
swept.py::test_cell_count_matches_locked_design` (dumped below) asserts
`len(cells) == 26` (with `include_topup_acceleration_cells: false`, the
current setting) and this test **passed** in pass 1's `pytest -q` run
(it is not in the one-failure list). The file's own module docstring
states this explicitly: "eval-spec-v1.1 (2026-08-26): the cell count
moved from 22 to 26. This is an INCREASE in sweep coverage, not a
relaxation." **This directly contradicts pass 1's uncritical repetition
of "22 cells" from `EVAL.md §6A` and `results/sensitivity.md` — see
Section 8 (Corrections to Pass 1) and Section 7 (New Conflicts) below.**

**How nested `sweep_required` entries are handled:**
`enumerate_cells()`'s second loop (the `for name in CANONICAL_MODEL_
PARAMS: ... for path, node in _sweep_required_nodes(definition):` block)
walks each parameter's `definition:` block recursively via
`_sweep_required_nodes()`, finds every dict node carrying
`sweep_required: true`, and — **only if that node also declares its own
`sweep.cells`** — appends one `Cell` per direction (`low`/`high`) found
in `node_cells`. `ambiguous_cause_split` (under `failure_mix_weights`)
and `transient_block_clearance` (under `balance_restore_timing`) both
now have `sweep.cells` populated in `configs/model_params.yaml` (per
pass 1's full dump), so both now contribute 2 cells each (4 total) — this
is exactly the +4 that took the count from 22 to 26.

**Is `include_topup_acceleration_cells: false` respected?** **YES** —
`enumerate_cells()`'s `include_topup = reg.sweep.get(
"include_topup_acceleration_cells", False)` gate wraps the topup-specific
cell-generation block in `if include_topup:`, and `configs/model_
params.yaml`'s current value is `false` (per pass 1's dump), so those 2
cells are NOT produced — matching `test_cell_count_matches_locked_
design`'s `26 if ... else 28` branching, confirmed by the passing test.

**Does any code APPLY a `Cell` to a config to produce a perturbed run,
or does `enumerate_cells` only ENUMERATE?** **`enumerate_cells()` (and
this entire module) only ENUMERATES.** `Cell.value` carries the
perturbed target value (e.g. a full renormalised bucket-mass dict for
`vector_simplex` parameters, or a bare scalar/list for others), but
**nothing in `src/rrx/spec/registry.py`, or anywhere else searched in
either pass, takes a `Cell` and writes it back into a copy of
`population.yaml`/`episode.yaml`/`model_params.yaml`, or otherwise
constructs a perturbed `episode_cfg`/`population_cfg` dict ready to feed
into `run_episode()`/`run_episode_a3()`.** This is a real, load-bearing
gap: the sweep grid is fully enumerable (26 `Cell` objects, tested and
passing) but there is no "apply a cell" function anywhere — confirmed by
grep for `apply_cell`, `resolve_config` usage sites (`resolve_config` DOES
exist — `src/rrx/spec/resolver.py`, referenced by `tests/test_latent_
snapshot.py` in pass 1's dump — but only one cell, `channel_response_
propensity.high`, is exercised through it in that one test; no code path
applies all 26 enumerated cells systematically for a sweep run).

**Path:** `src/rrx/spec/manifest.py`. **Line count:** 82. (Full content
already dumped verbatim in pass 1, Section 1's Batch-1 integrity search —
reproduced here since this pass's B2 explicitly requests it again.)

### Complete verbatim contents

```python
"""Per-run manifest writer — restores EVAL.md §6 (eval-spec-v1.3).

The requirement ("Every run writes `results/<run_id>/manifest.json`: git
SHA, spec version, config hash, seed, arm, regime, sweep cell, model
version, timestamp, wall-clock, LLM cost.") was present in EVAL.md from
its first committed version and was deleted, undocumented, in commit
337e0060e9f5af013e4b8362623a06d47a5ee67a. This module reproduces exactly
that eleven-field schema — no field is added, renamed in meaning, or
dropped; field names below are only a snake_case spelling of the same
eleven concepts for JSON/Python use.

Minimal on purpose: this builds and writes the manifest dict only. It does
not decide when a run is "canonical", does not import anything from
`rrx.sim` or `rrx.agent`, and never writes into the repository's real
`results/` directory unless the caller passes that path explicitly — no
A3/evaluation harness exists yet to wire this into.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Exactly the eleven fields EVAL.md §6 names. Adding a twelfth requires
    an EVAL.md §6 amendment first, not a silent extension here."""

    git_sha: str
    spec_version: str
    config_hash: str
    seed: int
    arm: str
    regime: str
    sweep_cell: str
    model_version: str | None
    timestamp: str
    wall_clock_seconds: float
    llm_cost_inr: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def current_git_sha(repo_root: Path | None = None) -> str:
    """git SHA of HEAD. Raises if git is unavailable or this isn't a repo —
    a manifest with a fabricated placeholder SHA would be worse than no
    manifest at all."""
    cwd = repo_root or Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def config_hash(*config_paths: Path) -> str:
    """sha256 over the concatenated bytes of the given config file(s), in
    the order given. Which configs are in scope for a run (episode.yaml,
    population.yaml, model_params.yaml, costs.yaml, ...) is the caller's
    decision, not this function's."""
    digest = hashlib.sha256()
    for p in config_paths:
        digest.update(Path(p).read_bytes())
    return digest.hexdigest()


def write_manifest(manifest: RunManifest, run_id: str, results_dir: Path) -> Path:
    """Writes <results_dir>/<run_id>/manifest.json. `results_dir` is always
    supplied by the caller — never defaulted to the repository's real
    `results/` — so exercising or testing this function cannot produce a
    canonical-looking artifact."""
    run_dir = Path(results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "manifest.json"
    out_path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return out_path
```

**Path:** `tests/test_model_params_swept.py`. **Line count:** 274.

### Complete verbatim contents

```python
"""Sweep-grid readiness.

The second half of the old test_model_params_swept.py. Asserts that every
specified parameter actually reaches the grid, that cell ids are unique,
and that the majority threshold is fixed arithmetically rather than
chosen after the run.

eval-spec-v1.1 (2026-08-26): the cell count moved from 22 to 26. This is an
INCREASE in sweep coverage, not a relaxation - the previous count of 22
omitted two [MODEL] parameters (ambiguous_cause_split, transient_block_
clearance) that were marked sweep_required: true but nested inside a
definition: block that enumerate_cells() did not read, so they silently
contributed zero cells. Nothing here was loosened to make a run go green;
the grid got bigger because two magnitudes that should always have been in
it now are.
"""

import copy

import pytest

from rrx.spec.registry import (
    CANONICAL_MODEL_PARAMS,
    Registry,
    enumerate_cells,
    find_sweep_required_nodes,
    load_registry,
    required_wins,
    unswept_required_entries,
)

reg = load_registry()
cells = enumerate_cells(reg)


def _resolve_definition_node(reg, parameter, path):
    """Walk a dotted path (from find_sweep_required_nodes) down a
    parameter's definition: block to the actual node dict."""
    node = reg.parameters[parameter]["definition"]
    for key in path.split("."):
        node = node[key]
    return node


def _mismatched_sweep_required_cells(reg):
    """'{parameter}.{path}' for every definition-nested sweep_required node
    whose cells are not +/-30% from its own declared baseline.

    Companion to test_scalar_cells_are_thirty_percent_from_baseline's
    top-level loop, which reads only p["handle"]["baseline"] / p["sweep"] -
    invisible to anything nested inside definition:, which is exactly the
    blindness find_sweep_required_nodes() was written to fix. A list-valued
    cell (transient_block_clearance's [lower, upper] day bounds) is checked
    on its upper bound only - see the docstring on the caller for why.
    """
    mismatched = []
    for name, path in find_sweep_required_nodes(reg):
        node = _resolve_definition_node(reg, name, path)
        sweep = node.get("sweep") or {}
        node_cells = sweep.get("cells")
        if not node_cells:
            continue  # the zero-cells case is unswept_required_entries's job
        mag = sweep["magnitude"]
        handle = sweep.get("handle", path)
        low, high = node_cells.get("low"), node_cells.get("high")
        if isinstance(low, list):
            base = node["support_days"][1]
            got_low, got_high = low[1], high[1]
        else:
            base = node[handle]
            got_low, got_high = low, high
        want_low, want_high = base * (1 - mag), base * (1 + mag)
        if (got_low != pytest.approx(want_low, rel=1e-6)
                or got_high != pytest.approx(want_high, rel=1e-6)):
            mismatched.append(f"{name}.{path}")
    return mismatched


def test_every_specified_parameter_reaches_the_grid():
    covered = {c.parameter for c in cells}
    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        if p["status"] == "specified" and p["sweep"].get("swept"):
            assert name in covered, f"{name} declared swept but has no cells"


def test_no_parameter_is_unspecified_before_freeze():
    """Locked decision 11 specified all four remaining latents. If any
    reverts to unspecified, sim-v1 cannot freeze and EVAL.md §8.1's
    ordering (simulator frozen before any agent policy) breaks."""
    assert reg.unspecified() == {}, (
        f"still unspecified: {sorted(reg.unspecified())}"
    )


def test_cell_ids_unique():
    ids = [c.cell_id for c in cells]
    assert len(ids) == len(set(ids))


def test_cell_count_matches_locked_design():
    """26 with the topup toggle off; 28 with it on (DEFECT 1).

    eval-spec-v1.1: was 22/24. The +4 is ambiguous_cause_split (low, high)
    and transient_block_clearance (low, high) - two Q1 gap-resolution
    [MODEL] magnitudes that were marked sweep_required: true from the start
    but, until this fix, contributed no cells. See module docstring."""
    expected = 28 if reg.sweep["include_topup_acceleration_cells"] else 26
    assert len(cells) == expected, (
        f"{len(cells)} cells, expected {expected}. "
        "Changing the count changes the pass mark - update EVAL.md §8.2."
    )


def test_failure_mix_contributes_fourteen_cells():
    """Six buckets x two directions (locked decision 3), plus
    ambiguous_cause_split's own two directional cells (eval-spec-v1.1)."""
    n = len([c for c in cells if c.parameter == "failure_mix_weights"])
    assert n == 14


def test_required_wins_is_ceil_of_eighty_percent():
    """Locked decision 5. Pinned here so the pass mark cannot be chosen
    after seeing which cells failed."""
    assert required_wins(26, reg) == 21
    assert required_wins(28, reg) == 23
    assert required_wins(len(cells), reg) == (
        23 if len(cells) == 28 else 21
    )


def test_low_information_cells_stay_in_denominator():
    """Locked decision 13: the wait and escalate buckets are swept and
    kept in the denominator, flagged rather than dropped."""
    low = {c.cell_id for c in cells if c.low_information}
    assert len(low) == 4, low
    assert all(("wait" in c or "escalate" in c) for c in low)


@pytest.mark.parametrize("name", [
    n for n in CANONICAL_MODEL_PARAMS if n != "failure_mix_weights"
])
def test_scalar_handles_have_two_directional_cells(name):
    """Every distinct handle under a parameter contributes exactly one low
    and one high cell - checked per handle, not per parameter, because
    eval-spec-v1.1 gives balance_restore_timing a second independent handle
    (transient_block_clearance) alongside its top-level salary_mode_mass."""
    handles = {c.handle for c in cells if c.parameter == name}
    for handle in handles:
        got = sorted(c.direction for c in cells
                     if c.parameter == name and c.handle == handle)
        assert got == ["high", "low"], f"{name}.{handle}: {got}"


def test_scalar_cells_are_thirty_percent_from_baseline():
    """Guards against a baseline being edited without its cells."""
    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        if p["kind"] in ("vector_simplex", "composite"):
            continue
        base = p["handle"]["baseline"]
        mag = p["sweep"]["magnitude"]
        assert p["sweep"]["cells"]["low"] == pytest.approx(base * (1 - mag), rel=1e-6)
        assert p["sweep"]["cells"]["high"] == pytest.approx(base * (1 + mag), rel=1e-6)

    # eval-spec-v1.1: the loop above reads only a parameter's top-level
    # handle/sweep, so a scalar magnitude nested inside definition: (e.g.
    # ambiguous_cause_split.p_card_cause) was invisible to this check - the
    # same blindness find_sweep_required_nodes() exists to fix, left in
    # place here until now. transient_block_clearance's cells are [lower,
    # upper] day-bound lists rather than a bare scalar (option 2a, chosen
    # over a silent exemption): the +/-30% check applies to the upper bound
    # against the baseline's own upper bound, since the lower bound is fixed
    # at 0 by design and is not what the magnitude sweeps.
    mismatched = _mismatched_sweep_required_cells(reg)
    assert mismatched == [], (
        f"definition-nested sweep_required cells not +/-30% from baseline: "
        f"{mismatched}"
    )


def test_composite_hazard_cells_scale_both_components():
    """Locked decision 9: one joint multiplier on hazard and lifetime."""
    p = reg.parameters["cancellation_hazard_and_ltv"]
    d = p["definition"]
    mag = p["sweep"]["magnitude"]
    h0 = d["hazard_per_contact"]["h0"]
    cyc = d["remaining_lifetime_cycles"]["mean_cycles"]
    for direction, f in (("low", 1 - mag), ("high", 1 + mag)):
        cell = p["sweep"]["cells"][direction]
        assert cell["hazard_h0"] == pytest.approx(h0 * f, rel=1e-6)
        assert cell["remaining_lifetime_mean_cycles"] == pytest.approx(cyc * f, rel=1e-6)


def test_probability_cells_within_clamp():
    lo, hi = reg.sweep["probability_clamp"]
    for name in ("channel_response_propensity",
                 "card_change_completion_propensity",
                 "balance_restore_timing"):
        for v in reg.parameters[name]["sweep"]["cells"].values():
            assert lo <= v <= hi, f"{name}: {v} outside clamp"

    # eval-spec-v1.1: same blindness as test_scalar_cells_are_thirty_percent_
    # from_baseline - the loop above reads only top-level sweep.cells, so a
    # probability-valued nested magnitude (ambiguous_cause_split.p_card_cause)
    # was invisible here too. transient_block_clearance's cells are
    # day-count bounds, not probabilities (its low/high are [0, 1.4] /
    # [0, 2.6] lists) - a day count of 2.6 failing a [0, 1] clamp would be a
    # false positive, not a real defect, so list-valued cells are explicitly
    # skipped rather than checked against a clamp that does not apply to them.
    for name, path in find_sweep_required_nodes(reg):
        node = _resolve_definition_node(reg, name, path)
        node_cells = (node.get("sweep") or {}).get("cells") or {}
        if not node_cells or isinstance(node_cells.get("low"), list):
            continue
        for v in node_cells.values():
            assert lo <= v <= hi, f"{name}.{path}: {v} outside clamp"


def test_all_sweep_required_entries_produce_cells():
    """EVAL.md §0: every [MODEL] magnitude must reach the sweep grid,
    including one nested inside a definition: block. This is the check
    today's bug needed: ambiguous_cause_split and transient_block_clearance
    were both marked sweep_required: true in configs/model_params.yaml but
    enumerate_cells() did not read anything inside definition:, so they
    silently contributed zero cells and no prior test noticed."""
    missing = unswept_required_entries(reg, cells)
    assert missing == [], (
        f"sweep_required: true but zero cells in enumerate_cells(): {missing}"
    )


def test_sweep_required_with_zero_cells_is_detected():
    """Regression test for today's bug, reproduced on a synthetic registry
    rather than the real config - proves the detection mechanism itself
    works, not just that today's two entries happen to be fixed now.

    Grafts a sweep_required: true node with no sweep.cells onto a real,
    valid parameter (invoice_amount) and asserts unswept_required_entries
    reports exactly that node. Before this fix, enumerate_cells() had no
    code path that read anything under definition: at all (other than the
    special-cased, opt-in topup_acceleration block), so a node in this
    exact shape would have passed silently."""
    broken_params = copy.deepcopy(dict(reg.raw["parameters"]))
    broken_params["invoice_amount"]["definition"] = {
        "orphaned_gap_param": {
            "value": 1.0,
            "sweep_required": True,
            # deliberately no "sweep" key - this is today's exact bug shape
        },
    }
    broken_reg = Registry({"sweep": reg.raw["sweep"], "parameters": broken_params})
    broken_cells = enumerate_cells(broken_reg)

    missing = unswept_required_entries(broken_reg, broken_cells)
    assert missing == ["invoice_amount.orphaned_gap_param"], missing


def test_thirty_percent_check_catches_a_bad_definition_nested_cell():
    """Regression, same shape as test_sweep_required_with_zero_cells_is_
    detected above: proves _mismatched_sweep_required_cells actually catches
    a definition-nested scalar cell that has drifted off its +/-30%
    baseline, not just that today's two real entries currently happen to be
    correct. Before this turn's fix, neither
    test_scalar_cells_are_thirty_percent_from_baseline nor
    test_probability_cells_within_clamp looked inside definition: at all, so
    a corrupted cell in this exact shape would have passed both silently."""
    broken_params = copy.deepcopy(dict(reg.raw["parameters"]))
    broken_params["failure_mix_weights"]["definition"]["ambiguous_cause_split"][
        "sweep"]["cells"]["high"] = 0.99  # should be 0.65 (0.50 * 1.30)
    broken_reg = Registry({"sweep": reg.raw["sweep"], "parameters": broken_params})

    mismatched = _mismatched_sweep_required_cells(broken_reg)
    assert mismatched == ["failure_mix_weights.ambiguous_cause_split"], mismatched
```

**Path:** `tests/test_model_params_registry.py`. **Line count:** 121.

### Complete verbatim contents

```python
"""Registry completeness.

This is the test EVAL.md §0 actually describes: it fails the build if a
[MODEL] parameter is MISSING. A flag-scanner cannot do this, because
scanning finds only what is present. Absence is detectable only against a
declared canonical list.

Split out from the old test_model_params_swept.py, which conflated two
different lifecycle questions (does the parameter exist? is it ready to
run holdout?). Nothing was weakened: both halves are now strictly
enforced, at the right time.
"""

import pytest

from rrx.spec.registry import (
    CANONICAL_MODEL_PARAMS,
    REQUIRED_FIELDS,
    VALID_STATUS,
    load_registry,
    resolve_owner_path,
)

reg = load_registry()


def test_exactly_six_parameters():
    assert len(reg.parameters) == 6, (
        f"EVAL.md §8.2 declares six [MODEL] parameters; registry has "
        f"{len(reg.parameters)}: {sorted(reg.parameters)}"
    )


def test_ids_match_eval_section_8_2_verbatim():
    assert set(reg.parameters) == set(CANONICAL_MODEL_PARAMS)


@pytest.mark.parametrize("name", CANONICAL_MODEL_PARAMS)
def test_required_fields_present(name):
    p = reg.parameters[name]
    missing = [f for f in REQUIRED_FIELDS if f not in p]
    assert not missing, f"{name} missing {missing}"
    assert p["status"] in VALID_STATUS


@pytest.mark.parametrize("name", CANONICAL_MODEL_PARAMS)
def test_owner_path_resolves(name):
    """Stops the registry silently drifting from the configs."""
    resolve_owner_path(reg.parameters[name]["owner_path"])


@pytest.mark.parametrize("name", CANONICAL_MODEL_PARAMS)
def test_provenance_declared_invented(name):
    """Every [MODEL] parameter is a synthetic design choice, never an
    observed Razorpay statistic. EVAL.md §8 threat 6 depends on this."""
    assert reg.parameters[name]["provenance"] == "invented_synthetic"


def test_lifetime_cycles_is_not_a_seventh_parameter():
    """Locked decision 7."""
    assert "remaining_subscription_lifetime_cycles" not in reg.parameters
    comp = reg.parameters["cancellation_hazard_and_ltv"]["handle"]["applies_to"]
    assert "remaining_lifetime_mean_cycles" in comp


def test_hazard_is_a_world_mechanic():
    """Locked decision 8. If hazard were Regime-A-only pricing, Regime B
    would be blind to the cost of over-contacting and the restraint
    thesis would have no headline-regime justification."""
    p = reg.parameters["cancellation_hazard_and_ltv"]
    assert p["regime_split"]["hazard"] == "world_mechanic"
    assert "B" in p["regime"]
    assert p["regime_split"]["ltv"] == "regime_a_pricing_only"


def test_razorpay_auto_email_carries_no_hazard():
    """EVAL.md §1.2: the automatic email is part of the world, not a
    contact. So A0's cancellation hazard is exactly zero and A0 stays a
    clean floor."""
    d = reg.parameters["cancellation_hazard_and_ltv"]["definition"]
    assert d["hazard_per_contact"]["applies_to_razorpay_auto_email"] is False


def test_card_change_completion_has_no_visible_correlate():
    """EVAL.md §3.4 pre-registers exactly three sources of A3 advantage.
    Coupling completion to a visible signal would create an unattributable
    fourth."""
    d = reg.parameters["card_change_completion_propensity"]["definition"]
    assert d["independent_of_visible_signals"] is True


def test_sweep_runs_on_dev_only():
    """Locked decision 1. EVAL.md §3.5 allows ONE holdout use per
    candidate release; a 22-cell sweep on holdout would be 22 uses."""
    assert reg.sweep["split"] == "dev"


def test_policies_frozen_across_cells():
    """Locked decision 14. Per-cell retuning of A3 would invalidate the
    entire sensitivity analysis."""
    # eval-spec-v1.4: "A3" split into its two pre-registered named arms
    # (EVAL.md §4.2) -- propagated, not relaxed: pins three names now.
    assert set(reg.sweep["frozen_policies"]) == {"A2", "A3-D", "A3-LLM"}


def test_crn_uses_per_variable_substreams():
    """Locked decision 14 + defect fix: shared streams would let a change
    to one parameter reshuffle unrelated draws, so the cell would no
    longer be a one-at-a-time comparison."""
    crn = reg.sweep["common_random_numbers"]
    assert crn["enabled"] is True
    assert crn["substream_isolation"] == "per_variable"


def test_win_criterion_requires_both_metrics():
    """Locked decision 4."""
    w = reg.sweep["win_criterion"]
    assert w["require"] == "all"
    assert set(w["metrics"]) == {"invoice_recovery_rate",
                                 "subscription_rescue_rate"}
    assert w["comparator"] == "A2"
```

Note this file's own docstring/test comment (`test_sweep_runs_on_dev_
only`) **still says "22-cell sweep"** in its comment text even though
the sibling file `test_model_params_swept.py` (same commit era) already
documents the count as 26 — a small internal inconsistency between two
test files' comments, not a functional bug (this comment is not asserted
on, just prose).
---

## 3. FROZEN CONFIGS

**Path:** `configs/episode.yaml`. **Line count:** 234.

### Complete verbatim contents

```yaml
# configs/episode.yaml
#
# Episode definition for the v1 recovery-orchestration experiment.
#
# Provenance tags follow EVAL.md 0:
#   [CITE] external fact | [INVARIANT] imposed constraint
#   [DESIGN] experimental choice | [MODEL] world assumption that is
#            explicitly declared as synthetic and swept where required.

meta:
  eval_spec_sections: ["EVAL.md 1", "EVAL.md 3.1", "EVAL.md 3.5", "EVAL.md 5.2"]
  taxonomy_source: data/decline_codes.yaml
  taxonomy_version: 4
  framing: recovery_orchestration

# ---------------------------------------------------------------------------
# Episode boundaries
# ---------------------------------------------------------------------------
episode:
  opens_when: subscription_enters_pending
  opening_state: pending
  window_days: 30
  window_provenance: DESIGN
  v1_method: card
  v1_method_provenance: DESIGN
  v1_method_rationale: >
    eMandate and UPI subscription retry models are verified in decline_codes.yaml
    but are out of v1 scope. Cards only.

# ---------------------------------------------------------------------------
# Razorpay's retry engine. NOT ours. [CITE]
# decline_codes.yaml: subscriptions.retry_control
# ---------------------------------------------------------------------------
razorpay_retry_engine:
  provenance: CITE
  owner: razorpay
  merchant_can_schedule_retries: false
  merchant_can_trigger_retry: false
  manual_charge_domestic_card_supported: false
  card_schedule_days: [1, 2, 3]
  state_after_exhaustion: halted
  note: >
    The agent has NO payment-attempt budget, because payment attempts are not an
    agent action. Any proposal to retry is rejected by the gate and logged.
    Enforced by tests/test_gate_no_retry_action.py.

# ---------------------------------------------------------------------------
# The decisive mechanic. decline_codes.yaml: subscriptions.card_change_effect
# [CITE]
# ---------------------------------------------------------------------------
payment_method_change_effect:
  provenance: CITE
  while_pending:
    last_invoice_auto_charged: true
    outcomes: [invoice_recovered, subscription_rescued]
  while_halted:
    last_invoice_auto_charged: false
    manual_charge_required: true
    manual_charge_available_domestic_card: false
    outcomes: [subscription_rescued]
  halt_boundary_day: 3
  note: "T+3 is a hard cutoff. After it, the invoice is stranded for domestic cards."

# ---------------------------------------------------------------------------
# Agent action budget. NOT payment attempts. [DESIGN]
# Must equal decline_codes.yaml: defaults.global_caps
# ---------------------------------------------------------------------------
agent_budget:
  max_contacts_per_episode: 3
  provenance: DESIGN
  quiet_hours_ist:
    contact_window_start: "09:00"
    contact_window_end: "21:00"
    provenance: DESIGN
    applies_to: contacts_only
  razorpay_failure_email_counts_against_budget: false
  razorpay_failure_email_note: >
    Razorpay independently emails the customer a payment-failure notice containing
    a payment-method-change link [CITE]. It is part of the world for every arm,
    including A0. It is visible to the agent in contact_history but is not budgeted.

# ---------------------------------------------------------------------------
# Invoice amount — EVAL.md 3.1
#
# Sweep membership is declared centrally in configs/model_params.yaml.
# ---------------------------------------------------------------------------
invoice_amount_inr:
  provenance: MODEL
  distribution: lognormal
  mu_expression: "ln(2000)"
  sigma: 1.0
  sampling: rejection
  lower_bound: 100
  upper_bound: 50000
  rounding: rupee
  note: >
    Synthetic design parameters. NOT observed Razorpay merchant statistics.
    Median 2000, mean ~3297. Rejection rate ~0.2%.

# ---------------------------------------------------------------------------
# Regime A only — cancellation hazard + LTV
#
# remaining_subscription_lifetime_cycles is a COMPONENT of the
# cancellation_hazard_and_ltv MODEL parameter, not a standalone swept
# parameter.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Latent parameters
#
# ALL FOUR LATENT PARAMETERS ARE INVENTED SYNTHETIC ASSUMPTIONS.
# They are NOT observed Razorpay statistics, NOT derived from merchant data,
# and NOT sourced from any public document.
#
# These values are hidden from the agent and are used only by the simulator.
# ---------------------------------------------------------------------------
latent:
  provenance: invented_synthetic
  visible_to_agent: false

  balance_restore_delay:
    provenance: invented_synthetic

    mixture:
      transient:
        weight: 0.45
        dist: truncated_exponential
        mean_days: 2.0
        support_days: [0, 30]

      salary_cycle:
        weight: 0.55
        dist: days_until_next_salary_day
        salary_day_pmf:
          1: 0.55
          7: 0.20
          25: 0.10
          30: 0.15
        jitter:
          dist: gamma
          shape: 2
          mean_days: 1.0

    topup_acceleration:
      provenance: invented_synthetic
      p_topup_action: 0.35
      accelerated_delay:
        dist: exponential
        mean_days: 0.5
      rule: "min(original_delay, t_engage + draw)"
      precondition: "engagement strictly before next auto-retry"
      swept: false
      confidence: low

  channel_response_propensity:
    provenance: invented_synthetic

    customer_trait:
      dist: beta
      parameterisation: mean_concentration
      mean: 0.28
      concentration: 7

    channel_multipliers:
      whatsapp: 1.15
      sms: 1.00
      email: 0.65

    fatigue:
      base: 0.80
      exponent: prior_contacts_in_episode

    tenure_coupling:
      beta: 0.35
      form: "logit(theta) += beta * z(tenure_days)"

    handle_addresses: beta_mean_parameter
    record_realised_mean: true
    clamp: [0.0, 1.0]

  card_change_completion_propensity:
    provenance: invented_synthetic
    dist: beta
    parameterisation: mean_concentration
    mean: 0.55
    concentration: 6
    conditional_on: engagement_with_card_change_prompt
    independent_of_visible_signals: true
    clamp: [0.0, 1.0]

  bank_technical_error_clearance:
    provenance: invented_synthetic
    dist: uniform
    support_days: [0, 2]
    rationale: >
      EVAL 3.2 states the correct remedy is "wait - auto-retry likely
      resolves it". Requires clearance inside the retry window.
      P(clear before T+1) = 0.5, P(clear before T+2) = 1.0.
    sweep_required: true
    component_of: balance_restore_timing
    note: >
      Q1 gap resolution (2026-08-26, eval-spec-v1.1). Not a new [MODEL]
      family - folds into balance_restore_timing (transient resolution
      timing) in configs/model_params.yaml, alongside the existing
      balance_restore_delay mixture above.

  cancellation:
    provenance: invented_synthetic

    hazard_per_contact:
      h0: 0.010
      gamma: 1.5
      form: "clamp(h0 * gamma ** (n-1), 0, 1)"
      regime: world_mechanic
      applies_to_razorpay_auto_email: false

    remaining_subscription_lifetime_cycles:
      dist: geometric
      mean_cycles: 9
      regime: [A]
      component_of: cancellation_hazard_and_ltv
      note: >
        This is a component of the cancellation_hazard_and_ltv MODEL parameter,
        NOT a seventh standalone swept parameter.

# ---------------------------------------------------------------------------
# Deliberately NOT in this file
# ---------------------------------------------------------------------------
out_of_scope_here:
  payment_attempt_caps: "Not an agent action. See razorpay_retry_engine."
  issuer_downtime_model: "EVAL.md 3.2 excludes it from v1 — the agent cannot act on it."
  seeds_and_splits: >
    Specified in EVAL.md 3.5 and 6 (master seed, dev/holdout/stress, bootstrap).
    Not duplicated here to avoid two sources of truth. They still need a home —
    configs/eval.yaml — before the harness can run.
```

**Reported fields:**
- `agent_budget.max_contacts_per_episode`: **3**
- `agent_budget.quiet_hours_ist`: `contact_window_start: "09:00"`,
  `contact_window_end: "21:00"`, `provenance: DESIGN`,
  `applies_to: contacts_only`
- `razorpay_retry_engine.card_schedule_days`: **`[1, 2, 3]`**
- `razorpay_retry_engine.state_after_exhaustion`: **`halted`**
- `payment_method_change_effect.halt_boundary_day`: **3**
- `payment_method_change_effect.while_halted`: `last_invoice_auto_
  charged: false`, `manual_charge_required: true`, `manual_charge_
  available_domestic_card: false`, `outcomes: [subscription_rescued]`
- `episode.window_days`: **30**

`configs/episode.yaml`'s own closing `out_of_scope_here.seeds_and_
splits` note is itself a recorded, self-flagged gap: **"They still need
a home — `configs/eval.yaml` — before the harness can run."** No
`configs/eval.yaml` exists anywhere in the repository (confirmed via
`Glob configs/*`, only `costs.yaml`, `episode.yaml`, `model_params.yaml`,
`population.yaml` exist) — this is the config file's own author
flagging, in 2026-08-25/26, the exact same "no canonical harness
entry point" gap pass 1 independently rediscovered from the code side
(pass 1 §11 GAPS items 1/7/10).

**Path:** `configs/costs.yaml`. **Line count:** 55.

### Complete verbatim contents

```yaml
# Cost model for synthetic recovery evaluation.
# Every numeric value is labelled CITE or ASSUMPTION.
# Cited communication prices are provider reference prices; the simulator does not claim
# the merchant actually uses that provider.

currency: INR

gateway:
  failed_attempt_cost_inr: 0.00 # CITE: Razorpay standard pricing says platform fees are charged only on successful transactions.
  successful_capture_fee_rate: 0.0236 # CITE: Razorpay standard domestic rate 2% + 18% GST on the platform fee = 2.36% effective.
  recurring_subscription_addon_inr: null # EVAL.md §5.1: [CITE-PENDING] on razorpay.com/pricing. Left swept, not verified or invented — excluded from net_recovered_formula until a value is sourced or a sweep cell is defined.
  note: "The 0.00 failed-attempt fee is a pricing-model input, not a claim that no bank/network/operational cost exists."

messaging:
  sms:
    cost_inr: 0.18 # CITE: MSG91 India-to-India SMS pricing page, 30,000-message tier; rate shown before GST.
    provider: "MSG91"
    pricing_tier: "30,000 SMS"
    gst_included: false # CITE: MSG91 pricing page states listed rate excludes GST.
  email:
    cost_inr: 0.02 # CITE: MSG91 India email pricing page, Starter plan extra-email rate.
    provider: "MSG91"
    pricing_tier: "Starter extra-email rate"
    gst_included: false # CITE: MSG91 pricing page states listed prices exclude GST.
  whatsapp:
    cost_inr: 0.115 # CITE: MSG91 WhatsApp India utility/authentication rate.
    provider: "MSG91"
    category: "utility"
    gst_included: false # CITE: MSG91 pricing page states listed prices exclude GST.
  voice_per_minute:
    cost_inr: 1.00 # ASSUMPTION: round-number simulation cost; provider rates vary by destination/network and plan.
    provider: "generic reference"
    gst_included: false # ASSUMPTION: GST is excluded from the synthetic cost model unless explicitly added below.

annoyance:
  per_contact_inr: 1.00 # ASSUMPTION: synthetic customer-annoyance penalty; must be included in sensitivity analysis.
  applies_to:
    - sms
    - email
    - whatsapp
    - voice

llm:
  input_cost_inr_per_1k_tokens: 0.50 # ASSUMPTION: provisional placeholder until the exact model/version is pinned.
  output_cost_inr_per_1k_tokens: 1.50 # ASSUMPTION: provisional placeholder until the exact model/version is pinned.
  note: "These two LLM prices must be replaced with the actual pinned model's current pricing before the final eval-spec-v1 tag if the chosen provider exposes a public price."

tax:
  communication_gst_rate: 0.18 # CITE: MSG91 pricing pages state prices are exclusive of 18% GST.
  apply_to_cited_provider_costs: true # ASSUMPTION: modelling choice for the synthetic cost ledger.
  apply_to_llm_costs: false # ASSUMPTION: until the selected model/provider's tax treatment is known.

accounting:
  net_recovered_formula: "gross_recovered - successful_capture_processing_fee - failed_attempt_cost - contact_cost - annoyance_cost - llm_cost"
  rounding_precision_inr: 0.01 # ASSUMPTION: ledger/reporting precision.
```

Notable: `messaging.voice_per_minute` and `annoyance.applies_to`
include `voice` — but no `voice` channel exists anywhere in
`episode.yaml#/latent/channel_response_propensity/channel_multipliers`
(only `whatsapp`/`sms`/`email`), in `EVAL.md`, or in `SIM.md` — a cost
line for a channel the simulator never uses. Not previously flagged in
pass 1 (which never opened this file). `recurring_subscription_addon_
inr: null` confirms `EVAL.md §5.1`'s `[CITE-PENDING]` row is still
genuinely unresolved in the actual config, not just in prose.

**Path:** `configs/population.yaml`. **Line count:** 186 (under the
400-line dump threshold — full file dumped, not just the two named
blocks).

### Complete verbatim contents

```yaml
# configs/population.yaml
#
# SOURCE OF TRUTH for the v1 episode-opening condition mix.
# Weights are copied verbatim from EVAL.md 3.2. This file is the machine-readable
# original; EVAL.md 3.2's table is GENERATED from this file by `make docs`.
# Do not edit weights here without a new EVAL tag + changelog entry.
#
# Provenance tags follow EVAL.md 0:
#   [CITE] external fact | [INVARIANT] imposed constraint
#   [DESIGN] experimental choice with no bearing on validity
#   [MODEL] world assumption that could change the conclusion

meta:
  eval_spec_section: "EVAL.md 3.2"
  taxonomy_source: data/decline_codes.yaml
  taxonomy_version: 4
  provenance: MODEL
  v1_method: card
  spec_version: eval-spec-v1-draft
  provenance_type: invented_synthetic
  note: >
    Synthetic design parameters. NOT observed Razorpay statistics.

validation:
  # Enforced by tests/test_population_matches_decline_codes.py
  weights_must_sum_to: 1.0
  tolerance: 0.0001
  every_code_must:
    exist_in: data/decline_codes.yaml
    have_verified: true
    have_in_v1_cohort: true
    not_appear_in: [unverified.codes, upi_codes_out_of_v1_scope.codes]
    not_have_context: attended_only

# ---------------------------------------------------------------------------
# Invoice amount
# ---------------------------------------------------------------------------

invoice_amount_inr:
  dist: lognormal
  mu_expr: "ln(median_inr)"
  median_inr: 2000
  sigma: 1.0
  support: [100, 50000]
  rounding: nearest_rupee
  provenance: invented_synthetic

# ---------------------------------------------------------------------------
# Failure mix
#
# Condition-level weights.
# Bucket grouping and sensitivity perturbation are defined in
# configs/model_params.yaml.
# ---------------------------------------------------------------------------

failure_mix:
  conditions:
    insufficient_funds: 0.32
    card_declined_or_payment_failed: 0.24
    card_expired: 0.16
    debit_instrument_blocked: 0.12
    card_not_enrolled: 0.06
    subscription_cancelled: 0.05
    bank_technical_error: 0.03
    transaction_limit_exceeded: 0.01
    payment_risk_check_failed: 0.01

# ---------------------------------------------------------------------------
# Episode-opening conditions.
#
# Two kinds of opening condition exist and they are NOT interchangeable:
#   decline_code       - the auto-charge failed with this code; Subscription -> pending
#   subscription_state - the Subscription was already in a terminal state at open
# ---------------------------------------------------------------------------

opening_conditions:

  - key: insufficient_funds
    kind: decline_code
    code: insufficient_funds
    weight: 0.32
    correct_remedy: send_topup_reminder
    urgency: before_halt

  - key: ambiguous_decline
    kind: decline_code_group
    weight: 0.24
    codes: [card_declined, payment_failed]
    correct_remedy: send_payment_method_change_prompt
    urgency: immediate
    report_separately: true
    UNRESOLVED_intra_group_split: false
    p_card_cause: 0.50
    basis: project_inference
    rationale: >
      Maximum entropy over two causes. The code is ambiguous by construction
      and no signal distinguishes them. Near arm-neutral: A3 and A2 both see
      only decline_code for this bucket.
    note: >
      EVAL.md 3.2 assigns 24% to "card_declined / payment_failed" as a single row
      and does not specify how to divide it between the two codes. decline_codes.yaml
      treats them as distinct codes with equivalent documented descriptions.
      Originally NOT split here, because inventing a split would have been a
      silent assumption. Resolved 2026-08-26 (Q1 gap resolution, eval-spec-v1.1):
      p_card_cause=0.50 above is now a recorded config value with a stated
      selection rule, not a silent assumption. Folded into the
      failure_mix_weights [MODEL] family in configs/model_params.yaml; not a
      seventh parameter.

  - key: card_expired
    kind: decline_code
    code: card_expired
    weight: 0.16
    correct_remedy: send_payment_method_change_prompt
    urgency: immediate

  - key: debit_instrument_blocked
    kind: decline_code
    code: debit_instrument_blocked
    weight: 0.12
    correct_remedy: send_payment_method_change_prompt
    urgency: immediate

  - key: card_not_enabled_group
    kind: decline_code_group
    weight: 0.06
    codes:
      - card_not_enrolled
      - card_disabled_for_online_payments
      - debit_instrument_inactive
    correct_remedy: send_payment_method_change_prompt
    urgency: immediate
    UNRESOLVED_intra_group_split: true
    note: >
      EVAL.md 3.2 lists "card_not_enrolled + aliases" as one 6% row. decline_codes.yaml
      records three DISTINCT codes with equivalent documented descriptions and
      explicitly states they must not be collapsed, so the simulator must emit all
      three. The split across them is unspecified in EVAL. Not invented here.

  - key: subscription_cancelled_by_customer
    kind: subscription_state
    state: cancelled
    weight: 0.05
    correct_remedy: no_contact
    urgency: none
    note: >
      NOT a decline code. Maps to subscriptions.states.cancelled in decline_codes.yaml:
      terminal, not restartable. Corresponds to Razorpay's documented failure reason
      "the customer has cancelled the mandate from their end" [CITE].
      Correct agent behaviour is zero contact; gated by test_gate_terminal_states.py.

  - key: bank_technical_error
    kind: decline_code
    code: bank_technical_error
    weight: 0.03
    correct_remedy: wait
    urgency: none

  - key: transaction_limit_exceeded
    kind: decline_code
    code: transaction_limit_exceeded
    weight: 0.01
    correct_remedy: wait
    urgency: none

  - key: payment_risk_check_failed
    kind: decline_code
    code: payment_risk_check_failed
    weight: 0.01
    correct_remedy: escalate_to_merchant
    urgency: immediate
    hard_stop: true

# Sum of failure_mix.conditions:
# 0.32 + 0.24 + 0.16 + 0.12 + 0.06 + 0.05 + 0.03 + 0.01 + 0.01 = 1.00

# ---------------------------------------------------------------------------
# Excluded but present in taxonomy
# ---------------------------------------------------------------------------

excluded_but_in_taxonomy:
  gateway_technical_error:
    reason: >
      Marked in_v1_cohort: true in decline_codes.yaml but carries NO weight in
      EVAL.md 3.2. Left at zero rather than assigned an invented weight.
      Either add it to EVAL 3.2 with a weight, or set in_v1_cohort: false.
      Flagged, not silently resolved.
```

Note: this file's `excluded_but_in_taxonomy.gateway_technical_error`
block is a **self-flagged, still-open gap** in the frozen population
config itself — `gateway_technical_error` is `in_v1_cohort: true` in
`data/decline_codes.yaml` (not opened in this pass either — still
MISSING AUTHORITATIVE CONTEXT, see Section 7) but carries zero weight
and never appears in `opening_conditions`, so it can never actually be
sampled. The file's own author explicitly says this is unresolved
("Either add it to EVAL 3.2 with a weight, or set `in_v1_cohort:
false`... Flagged, not silently resolved") — new GAP for Section 7.

---

## 4. CHANGELOG

**Path:** `CHANGELOG.md`. **Line count:** 1,211 (over the 600-line
threshold — per this pass's instructions, dumping the `eval-spec-v1.3`,
`eval-spec-v1.4`, and `sim-v1` entries in full, plus the full heading
list).

### Heading list (`## ` headings, in file order)

```
3:    ## eval-spec-v1.4 — A3 design freeze — 2026-08-27
103:  ## eval-spec-v1.3 — Day 3 evaluation cleanup — 2026-08-27
427:  ## sim-v1 — simulator freeze — 2026-08-26
470:  ## Day 2 Stage 5 — falsification tests, closed — 2026-08-26
575:  ## eval-spec-v1.2 — 2026-08-26
660:  ## Day 2 Stage 4B — 2026-08-26
792:  ## Day 2 Stage 3 — 2026-08-26
1017: ## Day 2 Stage 2 — 2026-08-26
1082: ## eval-spec-v1.1 — 2026-08-26
```

**No entry newer than `eval-spec-v1.4` (2026-08-27) exists** — the file
has no heading, of any kind, dated after `eval-spec-v1.4`'s. Day 4's two
commits (`7238c6f` "Day 4 foundation...", `447997a` "Task 4B...") have
**no corresponding `CHANGELOG.md` entry at all.**

### `eval-spec-v1.4 — A3 design freeze — 2026-08-27` (complete, verbatim)

```markdown
## eval-spec-v1.4 — A3 design freeze — 2026-08-27

Documentation-only amendment. `sim-v1`
(`bbfa55d68a97ca9f41a9b151477b193db5054ffe`) and `src/rrx/sim/` are
untouched by this pass. Companion document: `docs/A3-DESIGN.md`.

### Provenance correction (recorded, not silently fixed)

The §3.5/§8/§9 recovery (previous commit) was originally framed as
"recover from the `eval-spec-v1` tagged source." That tag
(`0617f78fa16c0434a5f89d5637c4ca48454c167f`) was cut *after* the
undocumented deletion in `337e0060e9f5af013e4b8362623a06d47a5ee67a`, so it
does not itself contain the missing sections. The actual source used —
matching the method `eval-spec-v1.3` already established for §4/§6/§7 —
is `337e006~1` = `d04d158b1a6d8919d0777f73cd58ed26f316d28a`.

### Verification-driven correction

`run_stage3.py` and both `diagnostics/day3_*.py` scripts write nothing to
`results/` (only `open()` call in `run_stage3.py` is a config *read* of
`costs.yaml`). `results/sensitivity.md` is 100% `PENDING` for all 22
cells — no sweep has ever been executed, for A2 or anyone. An earlier
draft of this amendment assumed "A2's existing full-dev sweep numbers"
could be "preserved and republished unchanged" — corrected in `EVAL.md
§6A`: A2's full-dev sweep is scheduled to run for the first time under
this amendment, independent of and unaffected by A3.

### A. A3-D formally distinct (`EVAL.md §4.2`)

Ablation + control arm, shares runner/gate/executor/ledger/wake-up
cadence with A3-LLM. Must clear all §5.2 gates; not required to clear
§7's 40%-gap criterion. A3-D≥A3-LLM outcome pre-registered as a
publishable finding, not a re-tuning trigger.

### B. "fallback-to-A2 rate" superseded (`EVAL.md §5.3`)

Frozen phrase preserved verbatim; amendment states the fallback target is
A3-D, with five admissible fallback reasons.

### C. Four-field decision-audit taxonomy (`EVAL.md §5.4`)

`tick_type` (4 values), `reason_code` (**7** values — `terminal_state`
removed this pass, see F below), `gate_rule_fired` (R1–R8),
`fallback_reason` (5 values). Admissible `reason_code` per `decline_code`:
`docs/A3-DESIGN.md §7`. Kept fully separate from `data/decline_codes.yaml`.

### D. Tuning budget, sweep subsample, pairing, repeat-run nesting, cost
control (`EVAL.md §6A`)

A3-LLM N=6 (tuned on the 500-episode subsample, only the selected
configuration re-run on full `dev`) / A3-D N=3, `results/tuning_log.md`.
500-episode sweep subsample (seeds 1000-1499) for A3-LLM; A2 additionally
evaluated on the same 500 indices for paired comparison, separate from
its own full-dev canonical sweep. A3-D swept at full dev. Pre-registered
sweep-cost contingency (A3-D full 22 cells / A3-LLM nominal + the 4
`channel_response_propensity`/`card_change_completion_propensity` cells)
declared now, to be invoked only with an explicit `results/sensitivity.md`
note if needed — never silently. 300-episode repeat-run subsample nested
inside the 500, three live runs, three separate cache files.

### E. `configs/model_params.yaml` — `frozen_policies` amended

`[A2, A3]` → `[A2, A3-D, A3-LLM]`. `win_criterion.comparator` **unchanged**
(`A2`). Locked file — applied this pass with explicit authorization.

### F. Design decisions closing prior open questions, plus one narrowing

Wake-up set frozen: `{0,1,2,3,5,7,14}` + engagement-triggered, suppressed
on terminal state or exhausted budget (`docs/A3-DESIGN.md §5`) — same
contact budget as every other arm (3), more decision points, not more
actions. Channel pinned to `whatsapp` for both A3 arms — this **removes**
an advantage A3 would otherwise hold over every arm hardcoding
`AGENT_CHANNEL`; `whatsapp`'s multiplier (1.15 vs `sms` 1.00 vs `email`
0.65, `episode.yaml:164-167`) is supporting evidence, not the argument.
Action space narrowed to CONTACT/WAIT/STOP. `reason_code` narrowed from
8 to **7** values: `terminal_state` removed — `subscription_cancelled_by_customer`
episodes terminate at T=0 before any runner tick exists at all
(`engine.py:438-443`), so the code was unreachable by construction; `R2`
(contacts to cancelled/expired subscriptions) remains in the gate,
exercised only by synthetic adversarial test proposals. New `EVAL.md §8`
item 8: the 5% cancelled-at-open bucket's zero-contact behaviour is
enforced by the environment for every arm, not demonstrated by A3 —
flagged against overclaiming in any pitch/README. Module locations:
runner, policy, planner, prompt builder, gate, **and ledger** all under
`src/rrx/agent/` (gate and ledger moved inside the guarded package this
pass, closing the `GUARDED_PACKAGES` coverage gap by placement —
`test_no_latent_leak.py` is NOT modified). Gate tests driven by synthetic
adversarial proposals, not A3-D/A3-LLM output. New `docs/A3-DESIGN.md
§22` artifact policy: per-episode ledgers and LLM caches gitignored; a
~20-episode curated `results/audit_sample/` committed as the public
audit-trail deliverable; manifests and aggregate results always
committed. Both open questions from the prior design pass are resolved —
`docs/A3-DESIGN.md §21` is empty this pass.

### Verification

- `python -m pytest -q`: run after this commit — see report.
- `python -m ruff check .`: run after this commit — see report.
- `git diff --stat -- src/rrx/sim/`: confirmed empty.
```

**Note the direct textual claim, quoted above (section F):** *"Module
locations: runner, policy, planner, prompt builder, gate, and ledger all
under `src/rrx/agent/`"* — **this is the exact claim that the actual Day
4 implementation deviates from.** See Section 7 (New Conflicts) below.

### `eval-spec-v1.3 — Day 3 evaluation cleanup — 2026-08-27` (complete, verbatim)

```markdown
## eval-spec-v1.3 — Day 3 evaluation cleanup — 2026-08-27

**NOT YET COMMITTED.** Prepared and verified in the working tree; this
entry documents the proposed change set for final review before
commit/tag. `sim-v1` (commit
`bbfa55d68a97ca9f41a9b151477b193db5054ffe`) is untouched: everything below
either lives outside `src/rrx/sim/` (`rrx.baselines.a2_variants`,
`rrx.spec.manifest`, new/updated tests) or is a documentation-only change
to `EVAL.md`/`CHANGELOG.md`. No holdout split used anywhere in this
entry — all measurements are `dev`, `range(1000, 3000)`,
`MASTER_SEED=20260825`, reproducible via
`diagnostics/day3_baseline_headroom.py` (non-canonical; writes nothing to
`results/`).

### A. A2 T+5→T+3 validity correction (`EVAL.md §4.1.1`)

**Original A2-original schedule** for the card-broken bucket
(`card_expired`, `debit_instrument_blocked`, `card_not_enabled_group`):
card-change prompt at T+0, repeat at T+5 — unchanged, still exactly what
`rrx.sim.engine.a2_action_for_day` (arm key `A2`) does.

**The §1.1/§1.3 contradiction:** `EVAL.md §1.1` — "Razorpay retries
failed subscription auto-charges automatically... for cards, T+1, T+2,
T+3... after which the Subscription moves to `halted`." `EVAL.md §1.3` —
"Invoice recovery... Only possible while auto-retries remain (T+1…T+3)."
`episode.yaml`'s `halt_boundary_day: 3` encodes the same boundary in the
frozen simulator. A2-original's own second card-broken contact is
scheduled at T+5 — after every one of these boundaries — so it is
structurally incapable of ever affecting invoice recovery, contradicting
the spec's own stated invoice-recovery window.

**Discovery:** this contradiction was surfaced by the Day 3 pre-agent
diagnostic (`diagnostics/day3_diagnostic.py`, then confirmed
quantitatively by `diagnostics/day3_baseline_headroom.py`), not invented
after the fact to justify a result already seen — the reasoning above
(§1.1/§1.3 + `halt_boundary_day`) stands on its own without reference to
any A1/A4 comparison.

Three changes to A2's schedule, each derivable purely from this project's
own frozen mechanics (`EVAL.md §1.1/§1.3`, `episode.yaml`) — none of them
requires comparing to A1 or A4 to justify:

1. Card-broken bucket's second card-change contact: T+5 → T+3, because
   invoice recovery is only possible while auto-retries remain
   (T+1…T+3; `episode.yaml`'s `halt_boundary_day: 3`) — a T+5 contact for
   this bucket's invoice-relevant remedy cannot, structurally, affect
   invoice recovery.
2. `bank_technical_error`'s T+5 contact restores the `subscription_state
   in (pending, halted)` guard — this exact conditional ("card-change
   prompt at T+5 **if still failing**") was present in `EVAL.md §4` before
   it was deleted (see "EVAL.md §4/§6/§7 restoration" below) and was
   dropped by the implementation. `episode.yaml`'s
   `bank_technical_error_clearance` support is `[0, 2]` days, so recovery
   is always resolved by the day-2 auto-retry: on the `dev` cohort,
   **51/51** `bank_technical_error` episodes recover under A0 alone (zero
   contact), so A2-original's unguarded T+5 contact is a certain no-op
   100% of the time.
3. `transaction_limit_exceeded`'s T+5 card-change fallback is removed —
   `card_chargeable=True` at opening for this condition (`rrx.sim.latent`
   `_MECHANISM_ISOLATED_KEYS` branch), identical to `insufficient_funds`,
   so card-change is an equally guaranteed no-op. `EVAL.md §5.2`'s
   remedy-match gate row is widened to name both conditions.

Same contact count as A2-original on the card-broken bucket (2, retimed).
Measured effect (`dev`, N=2000), both primary metrics: card-broken
subgroup invoice recovery 0.2923 → 0.3947 (matches A1's 0.3947 on this
subgroup exactly, using fewer/equal contacts), rescue 0.4481 → 0.4525;
whole-cohort invoice recovery 0.4485 → 0.4830, rescue 0.5180 → 0.5195.

**A2-original is retained and runnable, unmodified**, under arm key `A2`
(`rrx.sim.engine.a2_action_for_day`) — this correction lives entirely in
the new `rrx.baselines.a2_variants` module (§ "Implementation location"
below), so it changes nothing about what `A2` already means in every
prior `CHANGELOG.md` entry or test.

### B. A2-strengthening — separate baseline decision (`EVAL.md §4.1.2`)

**This is a baseline STRENGTHENING, explicitly not the same rationale as
the correction above** — reported as a distinct decision per the
instruction not to blur the two. Where §A corrects a schedule point that
contradicted the spec's own invoice-recovery boundary, §B adds a NEW,
additional contact that was never present in A2-original at all, and
does so for a reason that has nothing to do with invoice recovery.

A2-corrected-v1 plus: the card-broken bucket's T+5 contact is restored as
a **third** contact (T+0/T+3/T+5), spending the full 3-contact budget on
a rescue mechanism the frozen simulator already defines
(`episode.yaml#/payment_method_change_effect/while_halted` →
`subscription_rescued`) and that A2-corrected-v1 leaves unused for this
bucket. Zero invoice-recovery cost (post-halt structurally cannot help
invoice recovery); measured rescue-rate gain on `dev`, card-broken
subgroup: 0.4525 → 0.5089 (+5.6 points) over A2-corrected-v1, at no cost
elsewhere. Whole-cohort: invoice recovery unchanged at 0.4830 (as
expected — this bucket's invoice outcome cannot move post-halt);
subscription rescue 0.5195 → 0.5385.

**Adopted as "the" A2 — the final bounded A2 for the `EVAL.md §7`
comparator, before any A3 code exists.** It weakly dominates
A2-corrected-v1 on both primary metrics on `dev` (equal invoice recovery,
higher rescue). `EVAL.md §4.1.2` now states the adopted schedule
explicitly (not just as a diff against A2-original), so the baseline is
reconstructable from the specification alone.

### C. `bank_technical_error` guard and `transaction_limit_exceeded` gate correction

Documented together because both are §A's items 2/3, restated here as
their own entry per the review's request for a separately-visible record:

- **`bank_technical_error`**: the adopted schedule's T+5 card-change
  contact now requires `subscription_state in (pending, halted)` — the
  "if still pending/halted" condition A2-original's implementation was
  missing (A2-original sends this contact unconditionally). Diagnostic
  evidence: 51/51 `dev`-cohort `bank_technical_error` episodes already
  recover under A0 (zero contact), so the unguarded T+5 contact was a
  certain no-op every time; the guard means it is now *never actually
  sent* for this condition, since it can never still be pending/halted
  by T+5.
- **`transaction_limit_exceeded`**: `EVAL.md §5.2`'s remedy-match gate
  row is widened from naming only `insufficient_funds` to naming both
  conditions — `card_chargeable=True` at opening makes card-change an
  equally guaranteed no-op for `transaction_limit_exceeded`, so the same
  gate principle now applies to both.

**Tests** (`tests/test_engine_policies.py`): the three tests that pinned
A2-original's old schedule for these conditions —
`test_a2_card_broken_bucket_schedule`,
`test_a2_bank_technical_error_schedule_no_contact_before_t3`,
`test_a2_transaction_limit_exceeded_schedule_fallback_removed` (renamed
2026-08-27 from `test_a2_transaction_limit_exceeded_schedule_keeps_
fallback`, once that name started describing the opposite of what the
test asserts; assertions unchanged by the rename) — are updated to assert
the adopted (A2-strengthened) schedule instead, importing
`a2_strengthened_action_for_day` from `rrx.baselines.a2_variants` for
that purpose; `rrx.sim.engine.a2_action_for_day` itself is not imported
differently and not modified. `test_a2_never_sends_card_change_for_
insufficient_funds` is untouched, per the review's explicit instruction.
A2-original's own exact schedule for all three conditions is
independently preserved by a new test, `tests/test_a2_variants.py::
test_a2_original_schedule_preserved_for_transparency`, which pins
`engine.a2_action_for_day` directly — nothing about A2-original's
coverage was weakened, only relocated to a test whose name says what it
actually tests.

### Implementation location

Both variants (`a2_corrected_v1_action_for_day`,
`a2_strengthened_action_for_day`) live in the new module
`src/rrx/baselines/a2_variants.py` — **outside** `src/rrx/sim/`, which
`sim-v1` freezes. They delegate to `rrx.sim.engine.a2_action_for_day` for
every unchanged branch and are registered into
`rrx.sim.engine._POLICIES` at runtime only (the same pattern
`tests/test_stage5_falsification.py` already uses for its own scratch
arms), never by editing `engine.py`. `engine.a2_action_for_day` itself is
byte-for-byte unmodified — `tests/test_a2_variants.py::
test_a2_original_unmodified_by_this_module` asserts this directly (same
function object, before and after import), which is the direct evidence
that A2-original stays reproducible under arm key `A2`.

Tests: `tests/test_a2_variants.py` — pins both variants' exact schedules
(including the three changes above), confirms both delegate to
`engine.a2_action_for_day` unchanged for every other condition, extends
the remedy-match-gate check (never sends card-change for
`insufficient_funds` or `transaction_limit_exceeded`) over a real batch
run for both variants, pins A2-original's own unmodified schedule
separately (§C above), and asserts `engine.a2_action_for_day` is the same
function object before and after import (guards against accidental
monkeypatching).

### Comparator rule (`EVAL.md §7`, criteria 2–3)

Previously (pre-337e006 text): uplift measured against A2 alone, on both
metrics jointly. Revised: for each primary metric independently, A3 is
compared against **the best-performing bounded non-agent arm on that same
metric** — bounded arms = {A0, A1, A2 (final adopted, i.e.
A2-strengthened)}. A4 excluded (oracle/reference); diagnostic/scratch
arms excluded. Ties (95% CI on the pairwise difference includes zero)
are reported explicitly rather than resolved by point estimate alone —
on `dev`, A1 (0.4840) and A2-corrected-v1 (0.4830) are such a tie on
invoice recovery (diff -0.0010, CI [-0.0080, +0.0060]).

The contact criterion (`§7` criterion 3) is revised to always use the
same bounded arm that won the rate comparison for that metric, rather
than a fixed reference arm — so a different arm can be the invoice-rate
comparator and the rescue-rate comparator, and the contact criterion
tracks whichever one applies to the metric in question.

### D. §7 target revision (`EVAL.md §7`)

**Original target**, preserved verbatim in `EVAL.md §7` for the record:
**"≥15% relative uplift `[DESIGN]` in subscription rescue rate vs A2 on
`holdout`, at equal-or-fewer contacts."**

**Measured oracle headroom** (`dev`, `diagnostics/day3_baseline_
headroom.py`): A4 vs the best-performing bounded arm per metric — invoice
recovery +0.0625 absolute (A4 0.5465 vs A1 0.4840, **12.9% relative**);
subscription rescue +0.0285 absolute (A4 0.5670 vs A2-strengthened
0.5385, **5.3% relative**).

**Why the original target was unreachable:** the original ≥15% relative
target was written before any oracle headroom had been measured — no `dev`
or `holdout` run existed yet to check it against. Once measured, 15%
relative on rescue is roughly 3× the actual, empirically observed A4
headroom of 5.3% — i.e. it asks A3 to close more than the entire
oracle-to-best-bounded gap, which is impossible by construction (A4 is
the upper reference). Against A2-original specifically (rescue 0.5180)
the target requires reaching 0.5957, which exceeds even the `dev` A4
figure of 0.5670 — unreachable regardless of which A2 baseline is used.
Additionally: A4's decision rule is lexicographic on invoice recovery and
does not reserve a contact for post-halt rescue, so A4 is not
rescue-optimal and the true rescue ceiling is somewhat higher than 0.5670
— which makes the original target's unreachability, if anything,
understated here, not overstated.

**New target:** A3 captures ≥40% of the A4 minus best-bounded-arm gap on
both primary metrics on `holdout` `[DESIGN]` — a target, not an
expectation, exactly like the original. The `dev` figures above (12.9% /
5.3%, and the illustrative absolute values below) are **headroom
evidence, not a fixed holdout target** — no holdout run has been
performed, and the actual target is whatever this formula evaluates to
once `holdout` is run:

| Metric | A4 (dev) | Best bounded (dev) | Gap | 40% of gap | Illustrative target |
|---|---:|---:|---:|---:|---:|
| Invoice recovery | 0.5465 | A1: 0.4840 | +0.0625 | +0.0250 | ≥0.5090 |
| Subscription rescue | 0.5670 | A2-strengthened: 0.5385 | +0.0285 | +0.0114 | ≥0.5499 |

Why 40%: no closed-form derivation exists for this number — it is a
`[DESIGN]` choice reflecting that A4 has full latent access A3 will never
have (the gap is not fully closeable in principle), while still requiring
A3 to close a majority-fraction of the empirically demonstrated headroom
rather than an arbitrary absolute percentage the `dev` measurement
already shows is unreachable.

### E. Manifest requirement (`EVAL.md §6`) and the undocumented prior removal

`EVAL.md §6`'s manifest requirement — "Every run writes
`results/<run_id>/manifest.json`: git SHA, spec version, config hash,
seed, arm, regime, sweep cell, model version, timestamp, wall-clock, LLM
cost" — was present in `EVAL.md` from its first committed version
(`176c6efb75943143268efdf33b61d59499c5aef5`, "Add evaluation spec and
payment decline taxonomy") and was **deleted, along with all of §4, §6,
§7, §8, and §9, in commit
`337e0060e9f5af013e4b8362623a06d47a5ee67a`** ("Complete Day 1 evaluation
infrastructure", 2026-08-25 15:51:57 +0530) — a 212-net-line rewrite of
`EVAL.md`. **`CHANGELOG.md` did not exist at that time** (first added in
commit `9305725cc6927d86f41b8df2779e1929926b5404`, "Freeze eval-spec-v1.1"
— which post-dates `337e006`), so no contemporaneous removal note was
possible. No removal note was added retroactively either, until this
entry — the `sim-v1` entry below (added `2026-08-26`, well after the
removal) is the first place this repository documents that the manifest
mechanism does not exist, and it documents the absence without tracing
it to a specific deleting commit. This entry closes that gap.

Restored `EVAL.md §6` verbatim (same eleven fields, same wording) plus a
`[DEFECT, eval-spec-v1.3]` note carrying the above history. Minimal
implementation, reproducing the historical schema exactly — no field
added, renamed in meaning, or dropped:

- `src/rrx/spec/manifest.py` — `RunManifest` (a frozen dataclass with
  exactly the eleven fields, snake_cased for Python/JSON:
  `git_sha, spec_version, config_hash, seed, arm, regime, sweep_cell,
  model_version, timestamp, wall_clock_seconds, llm_cost_inr`),
  `current_git_sha()`, `config_hash(*paths)`, `write_manifest(manifest,
  run_id, results_dir)`. `results_dir` is always caller-supplied — never
  defaulted to the repository's real `results/` — so this module cannot
  itself produce a canonical-looking artifact. Not wired into any
  evaluation harness; none exists yet (no A3).
- `tests/test_manifest.py` — schema-completeness check (exactly the eleven
  fields, no more/fewer), write/read round-trip into `tmp_path`, a check
  that writing a manifest never touches the repository's actual
  `results/` directory, and sanity checks on `current_git_sha`/
  `config_hash`.

### EVAL.md §4/§6/§7 restoration — git-history evidence

`337e0060e9f5af013e4b8362623a06d47a5ee67a` deleted five sections from
`EVAL.md` in one pass: §4 (Arms, including A2's original written
schedule), §6 (Seeds and statistics, including the manifest requirement),
§7 (Pre-registered success criteria, including the 15% target), §8
(Threats to validity), §9 (Definitions) — verified via `git show
337e0060e9f5af013e4b8362623a06d47a5ee67a -- EVAL.md`. This entry restores
**only §4, §6, and §7**, per the Day 3 review's explicit scope — §3.5
(Splits), §8, and §9 were also deleted in the same commit and remain
missing, flagged explicitly in `EVAL.md` (a note directly below §7) as an
open, undecided gap rather than silently reintroduced or silently
omitted.

The restored §4's original A2 schedule (`git show 337e006~1:EVAL.md`)
confirms, independently of `rrx.sim.engine.a2_action_for_day`'s own
docstring, that a T+5 card-change fallback for `insufficient_funds` was
originally written into the spec (grouped with `transaction_limit_
exceeded`) and was already absent from the implementation before this
entry — i.e. the implementation's insufficient_funds/§5.2-gate compliance
predates and is independent of this restoration. It also confirms
`bank_technical_error`'s original text carried the "if still failing"
conditional that A2-corrected-v1 restores (above) — that fix is a
reversion to previously-written intent, not new design.

### Verification

- `python -m pytest -q`: 564 passed, 1 failed. The one failure is
  `tests/test_stage5_falsification.py::test_1_policy_ordering`, the
  same, previously-documented, expected rejection (`A2-ish did not
  significantly beat A1-ish on invoice recovery: diff=-0.0355
  CI=[-0.0465,-0.0250]`) already recorded in this file's `Day 2 Stage 5`
  and `sim-v1` entries — unaffected by anything in this entry, since that
  test exercises `A2` (A2-original) unchanged. Not treated as a
  regression to fix.
- `python -m ruff check .`: all checks passed.
- `git diff --stat -- EVAL.md configs/ data/decline_codes.yaml tests/test_model_params_registry.py tests/test_sweep_grid.py tests/test_failure_mix_simplex.py src/rrx/sim/ SIM.md`
  shows zero changes under `src/rrx/sim/` or `SIM.md`; the only locked
  file touched is `EVAL.md` itself, per this entry's explicit approval.
- `git rev-parse sim-v1` still resolves to
  `bbfa55d68a97ca9f41a9b151477b193db5054ffe` — the tag was not moved.

### Not done in this entry

No commit, tag, or push. No holdout run. No `sim-v2`. No A3/agent code.
`EVAL.md §3.5`, `§8`, `§9` not restored (flagged, not silently handled
either way). `rrx.spec.manifest`'s writer was built and reviewed in a
prior pass, before this entry's "restore the specification only" scope
was set — it was not extended, wired into a harness, or otherwise
expanded in this entry.
```

**Note the 564-passed count above** — this is the total *at that point
in the repo's history* (before Day 4's ~58 net new tests). It is not in
tension with pass 1's `622 passed` figure; both are correct for their
respective points in time.

### `sim-v1 — simulator freeze — 2026-08-26` (complete, verbatim)

```markdown
## sim-v1 — simulator freeze — 2026-08-26

Freeze-only stage. No simulator, config, or test change. Freezes the
`SIM.md` §0/§1 simulator surface — `src/rrx/sim/`, `configs/episode.yaml`,
`configs/population.yaml`, `configs/model_params.yaml`,
`configs/costs.yaml`, `SIM.md` — at the Day 2 Stage 5 commit
`cdd118ad9ef0f8cb145a1aab846fe2e3a2d4ba3a`, under `eval-spec-v1.2`.

### Verification at freeze time

- Frozen surface (`src/rrx/sim/`, `configs/`, `EVAL.md`, `SIM.md`)
  verified diff-empty against `cdd118ad9ef0f8cb145a1aab846fe2e3a2d4ba3a`.
- Ordinary regression suite: 537 passed, 0 failed.
- Stage 5 falsification suite (`tests/test_stage5_falsification.py`,
  run standalone): 4 of 5 passed; Test 1 (policy ordering) rejected,
  reproducing the Stage 5 record above (`A1=0.4840, A2=0.4485,
  diff=-0.0355, CI=[-0.0465,-0.0250]`) byte-for-byte — no drift, the
  Stage 5 finding is not re-evaluated or reinterpreted here.
- Test 1's A1/A2 figures are computed on the `dev` split, episode indices
  `range(1000, 3000)` (2000 episodes), `MASTER_SEED=20260825`
  (`tests/test_stage5_falsification.py:42-44,303-307,334`); no holdout
  split is used.
- `python -m ruff check .`: all checks passed.

### Integrity mechanism

`sim-v1` is an annotated git tag pointing at this commit, following the
same convention already used for `eval-spec-v1` / `v1.1` / `v1.2`: the
tag annotation plus this changelog entry constitute the freeze record.
No config-hash or manifest-file mechanism exists anywhere in this
repository, and none is introduced by this entry.

### Deferred work, explicitly preserved

A per-run manifest and config-hash mechanism — referenced only in
passing at `EVAL.md` §3.3 ("the realised mean is recorded in each run
manifest") with no schema specified there — remains unbuilt. It was
flagged as deferred at Stage 2 (`sim-v1 (deferred; manifest work is
Stage 4)`, this file's Stage 2 entry) and was not delivered in Stages
3, 4, 4B, or 5. `sim-v1` freezes the simulator's code/config surface
only via the git commit/tag; it does not supply per-run provenance
capture. That machinery must exist before the first evaluation run.
```

### Direct answers

**The v1.3 baseline-resolution derivation and empirical numbers behind
the revised §7 target:** fully quoted above (§ "D. §7 target revision").
Summary: original ≥15% relative rescue-rate target vs A2, set before any
`dev` measurement existed; measured `dev` A4-vs-best-bounded headroom is
+0.0625 absolute / 12.9% relative (invoice recovery, A4 0.5465 vs A1
0.4840) and +0.0285 absolute / 5.3% relative (rescue, A4 0.5670 vs
A2-strengthened 0.5385) — both well under the original 15% target,
making it unreachable by any policy; revised to "A3 captures ≥40% of the
A4-minus-best-bounded-arm gap on both primary metrics on `holdout`",
illustrative `dev`-based targets ≥0.5090 (invoice) / ≥0.5499 (rescue).

**Is the runner-placement deviation (`A3-DESIGN.md §2` says
`src/rrx/agent/runner.py`; code has `src/rrx/harness/runner.py`)
recorded anywhere in `CHANGELOG.md`?** **NOT RECORDED IN CHANGELOG.**
Searched the full heading list (9 entries, newest `eval-spec-v1.4`,
2026-08-27) and the full text of the two entries most likely to mention
it (`v1.3`, `v1.4`, both quoted above) — neither says anything about
`src/rrx/harness/`. The `v1.4` entry's own section F **explicitly and
specifically states the opposite**: *"Module locations: runner, policy,
planner, prompt builder, gate, and ledger all under `src/rrx/agent/`"*.
Day 4's two commits (`7238c6f`, `447997a`), which actually created
`src/rrx/harness/runner.py`, have **no `CHANGELOG.md` entry of any
kind** — the file's most recent heading (`eval-spec-v1.4`) predates
both Day 4 commits. The deviation **is** recorded, but only inside the
code itself — `src/rrx/harness/runner.py`'s own module docstring
("Lives OUTSIDE the guarded rrx.agent / rrx.features packages...") and,
more explicitly, `tests/test_agent_boundary.py`'s docstring: *"the
day-loop driver lives under src/rrx/harness (not src/rrx/agent)
precisely because it needs full rrx.sim access that a policy must never
have"* — this test file even calls it, in its own words, "the Task 4A
file-plan correction." So: a reasoned, deliberate correction exists and
is documented **in code**, but was never propagated back into
`CHANGELOG.md` or `docs/A3-DESIGN.md`, both of which remain frozen with
the superseded `src/rrx/agent/runner.py` location. See Section 7 below.

---

## 5. A3 PIPELINE TESTS

**Path:** `tests/test_a3_runner_parity.py`. **Line count:** 148.
(Full content already dumped verbatim in pass 1, Section 10 / Batch 7 —
reproduced here in full since this pass's B5 explicitly requests it
again.)

### Complete verbatim contents

```python
"""Task 4A primary deliverable (docs/A3-DESIGN.md §16): byte-identity /
mechanics-parity proof between the frozen sim-v1 A0 arm (run_episode)
and the new A3 runner (rrx.harness.runner.run_episode_a3) driven by a
NULL POLICY that always returns WAIT.

This is NOT a proof that the null policy's "logic" matches A0's - it is
a proof that the new runner reproduces sim-v1's day-loop mechanics
EXACTLY: day ordering, within-day ordering, retry mechanics, halt
mechanics, contact budget, channel handling, RNG/CRN behavior,
latent-state handling, episode termination, contact history,
subscription-state transitions. A0 is the correct comparator because A0
also never contacts (its policy always returns None), so both arms
should be mechanically indistinguishable at the level of executed
actions, whatever the runner's internal wakeup/tick_type bookkeeping
looks like.

Comparison is EXACT EpisodeResult equality plus exact contact_history
equality (via capture_view_at_day=30), for every dev episode (seeds
1000-2999, N=2000) - no tolerances, no aggregate-only comparison, no
excluded episodes. If this fails, the acceptance gate is failed and
nothing past this point (gate, ledger, A3-D, A3-LLM) may proceed - see
this file's module-level STOP condition below.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from rrx.agent.null_policy import null_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.engine import run_episode
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

REPO_ROOT = Path(__file__).resolve().parents[1]
SIM_DIR = REPO_ROOT / "src" / "rrx" / "sim"
EPISODE_VIEW_FILE = REPO_ROOT / "src" / "rrx" / "features" / "episode_view.py"


def _hash_frozen_files() -> dict[str, str]:
    paths = sorted(SIM_DIR.glob("*.py")) + [EPISODE_VIEW_FILE]
    return {
        str(p.relative_to(REPO_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }


def _format_view(view) -> str:
    if view is None:
        return "None"
    return (
        f"EpisodeView(subscription_id={view.subscription_id!r}, "
        f"subscription_state={view.subscription_state!r}, "
        f"invoice_amount_inr={view.invoice_amount_inr}, "
        f"days_since_first_failure={view.days_since_first_failure}, "
        f"auto_retries_remaining={view.auto_retries_remaining}, "
        f"next_auto_retry_day={view.next_auto_retry_day}, "
        f"decline_code={view.decline_code!r}, "
        f"billing_amount_inr={view.billing_amount_inr}, "
        f"contact_history={view.contact_history}, "
        f"budget_remaining={view.budget_remaining})"
    )


def _first_divergent_day(i: int) -> tuple[int | None, str, str]:
    """Best-effort diagnostic, invoked ONLY after a mismatch has already
    been found for episode i: re-runs both arms with capture_view_at_day
    for each day 0..window_days, returning the first day at which the two
    EpisodeViews differ (day, expected-repr, actual-repr)."""
    window_days = EPISODE_CFG["episode"]["window_days"]
    for day in range(0, window_days + 1):
        a0 = run_episode(DEV_SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG, capture_view_at_day=day)
        a3 = run_episode_a3(
            DEV_SPLIT, i, null_policy, EPISODE_CFG, POPULATION_CFG, capture_view_at_day=day
        )
        a0_view = a0[1]
        a3_view = a3[1]
        if a0_view != a3_view:
            return day, _format_view(a0_view), _format_view(a3_view)
    return None, "", ""


def test_a3_runner_null_policy_exact_parity_with_a0_over_dev():
    """The acceptance gate for Task 4A. See module docstring."""
    hashes_before = _hash_frozen_files()

    first_mismatch = None
    for i in DEV_INDICES:
        a0_result, a0_view = run_episode(
            DEV_SPLIT, i, "A0", EPISODE_CFG, POPULATION_CFG, capture_view_at_day=30
        )
        a3_result, a3_view = run_episode_a3(
            DEV_SPLIT, i, null_policy, EPISODE_CFG, POPULATION_CFG, capture_view_at_day=30
        )
        if a0_result != a3_result or a0_view != a3_view:
            first_mismatch = (i, a0_result, a3_result, a0_view, a3_view)
            break  # report the FIRST failing episode only

    hashes_after = _hash_frozen_files()
    assert hashes_before == hashes_after, (
        "src/rrx/sim/*.py or episode_view.py changed during the parity run - "
        "these are frozen; this test suite must never modify them."
    )

    if first_mismatch is None:
        return

    i, a0_result, a3_result, a0_view, a3_view = first_mismatch
    day, a0_view_at_day, a3_view_at_day = _first_divergent_day(i)

    report = [
        "PARITY FAILURE - A3 runner (NULL POLICY) diverges from A0 (run_episode).",
        "Per docs/A3-DESIGN.md Task 4A: do NOT weaken this assertion, add "
        "tolerances, exclude this episode, change seeds, or modify the "
        "simulator. Report this and stop.",
        f"first failing episode index / seed: {i}",
        f"first divergent day (day-by-day capture_view_at_day scan): {day}",
        f"expected (A0) EpisodeResult: {a0_result}",
        f"actual   (A3-null) EpisodeResult: {a3_result}",
        f"expected (A0) EpisodeView @ day 30: {_format_view(a0_view)}",
        f"actual   (A3-null) EpisodeView @ day 30: {_format_view(a3_view)}",
    ]
    if day is not None:
        report.append(f"expected (A0) EpisodeView @ day {day}: {a0_view_at_day}")
        report.append(f"actual   (A3-null) EpisodeView @ day {day}: {a3_view_at_day}")

    pytest.fail("\n".join(report))


def test_sim_directory_has_no_uncommitted_diff():
    """docs/A3-DESIGN.md §16 / Task 4A section 6: `git diff --stat --
    src/rrx/sim/` must be empty - the simulator is untouched by this
    task."""
    result = subprocess.run(
        ["git", "diff", "--stat", "--", "src/rrx/sim/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"git diff failed: {result.stderr}"
    assert result.stdout.strip() == "", (
        f"src/rrx/sim/ has uncommitted changes, which must not exist for this task:\n"
        f"{result.stdout}"
    )
```

**Path:** `tests/test_gate_rules.py`. **Line count:** 184.

### Complete verbatim contents

```python
"""docs/A3-DESIGN.md §8: for EACH of R1-R8, one synthetic adversarial
Proposal engineered to trigger it (assert reject, assert the correct
rule_fired), and one engineered not to (assert accept).

Proposals are constructed IN THIS TEST - never driven by a policy.
A3-D is gate-compliant by construction (it never proposes a violation),
so a gate tested only against a real policy's output would never
exercise a single rejection path (§8's own "Gate test driver" note).
"""

from __future__ import annotations

from rrx.agent.gate import evaluate_gate
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


def _view(
    *,
    subscription_state: str = "pending",
    decline_code: str = "card_expired",
    budget_remaining: int = 3,
) -> EpisodeView:
    return EpisodeView(
        subscription_id="dev-1000",
        subscription_state=subscription_state,
        invoice_amount_inr=50000,
        days_since_first_failure=0,
        auto_retries_remaining=3,
        next_auto_retry_day=1,
        decline_code=decline_code,
        billing_amount_inr=50000,
        contact_history=(),
        budget_remaining=budget_remaining,
    )


def _proposal(action_type: str, remedy: str | None = None) -> Proposal:
    return Proposal(
        action_type=action_type, remedy=remedy, rationale="test", reason_code="test"
    )


# --------------------------------------------------------------------------
# R1 - agent-initiated retries: reject any action_type outside the
# 3-value schema (CONTACT|WAIT|STOP) - "no such value exists in the
# schema", so an out-of-schema value is the only way to construct one.
# --------------------------------------------------------------------------

def test_r1_rejects_out_of_schema_action_type():
    verdict = evaluate_gate(_proposal("RETRY"), _view())
    assert not verdict.accepted
    assert verdict.rule_fired == "R1"


def test_r1_accepts_in_schema_action_type():
    verdict = evaluate_gate(_proposal("WAIT"), _view())
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R2 - contacts to cancelled/expired subscriptions: 0.
# --------------------------------------------------------------------------

def test_r2_rejects_contact_to_cancelled_subscription():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(subscription_state="cancelled")
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R2"


def test_r2_accepts_contact_to_non_terminal_subscription():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(subscription_state="pending")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R3 - card_change for insufficient_funds/transaction_limit_exceeded: 0.
# --------------------------------------------------------------------------

def test_r3_rejects_card_change_for_insufficient_funds():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(decline_code="insufficient_funds")
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R3"


def test_r3_accepts_card_change_for_card_expired():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(decline_code="card_expired")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R4 - contacts after payment_risk_check_failed: 0.
# --------------------------------------------------------------------------

def test_r4_rejects_contact_for_payment_risk_check_failed():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"),
        _view(decline_code="payment_risk_check_failed"),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R4"


def test_r4_accepts_contact_for_a_non_risk_decline_code():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"), _view(decline_code="insufficient_funds")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R5 - budget cap: 0. Enforcement-by-construction at the runner level
# (the real runner never calls the gate once budget_remaining == 0 -
# tick_type=budget_exhausted instead); still checked defensively here.
# --------------------------------------------------------------------------

def test_r5_rejects_contact_when_budget_exhausted():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(budget_remaining=0)
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R5"


def test_r5_accepts_contact_when_budget_remains():
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"), _view(budget_remaining=1)
    )
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R6 - quiet hours: 0. Declared vacuous in sim-v1 (no intraday model) -
# the executor always stamps the fixed AGENT_SEND_HOUR ("10:00"), which
# is always within the window, so the real runner never triggers this.
# `send_hour` is a testability-only override to exercise the branch.
# --------------------------------------------------------------------------

def test_r6_rejects_an_out_of_window_send_hour():
    verdict = evaluate_gate(_proposal("WAIT"), _view(), send_hour="23:00")
    assert not verdict.accepted
    assert verdict.rule_fired == "R6"


def test_r6_accepts_the_fixed_in_window_send_hour():
    verdict = evaluate_gate(_proposal("WAIT"), _view())  # default send_hour="10:00"
    assert verdict.accepted
    assert verdict.rule_fired is None


# --------------------------------------------------------------------------
# R8 - unverified/attended-only codes: 0. Defensive only - cohort
# generation already guarantees view.decline_code is always a known-good
# value; this exercises the gate's own defensive check directly.
# --------------------------------------------------------------------------

def test_r8_rejects_contact_for_an_unverified_decline_code():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"),
        _view(decline_code="incorrect_otp"),  # data/decline_codes.yaml unverified.codes
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R8"


def test_r8_accepts_contact_for_a_known_good_decline_code():
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"), _view(decline_code="insufficient_funds")
    )
    assert verdict.accepted
    assert verdict.rule_fired is None
```

**Path:** `tests/test_agent_boundary.py`. **Line count:** 58.

### Complete verbatim contents

```python
"""docs/A3-DESIGN.md §2 boundary invariant, restated per the Task 4A
file-plan correction: the day-loop driver lives under src/rrx/harness
(not src/rrx/agent) precisely because it needs full rrx.sim access that
a policy must never have.

This test proves the actual boundary crossing is clean: the injected
policy callable receives exactly one positional argument, and that
argument is an EpisodeView - never _EpisodeState, CohortEpisode,
LatentState, or an RNG object.
"""

from __future__ import annotations

from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

# Not exhaustive latent field names - just the most direct ones, matching
# tests/test_no_latent_leak.py's own approach, to catch an EpisodeView
# that somehow grew a latent attribute at runtime.
_LATENT_ATTRS = (
    "card_chargeable", "funds_available_from", "mandate_alive",
    "blocked_until", "channel_response_trait", "card_chargeable_at_opening",
)


def test_policy_receives_only_an_episode_view():
    calls: list[tuple[tuple, dict]] = []

    def spy_policy(*args, **kwargs):
        calls.append((args, kwargs))
        return Proposal(
            action_type="WAIT", remedy=None, rationale="spy", reason_code="spy"
        )

    # Run several dev episodes (not just one) so this isn't accidentally
    # vacuous if a single chosen index happened to be cancelled-at-open
    # (no wakeup tick at all for that bucket, per §7/§20).
    for i in list(DEV_INDICES)[:50]:
        run_episode_a3(DEV_SPLIT, i, spy_policy, EPISODE_CFG, POPULATION_CFG)

    assert calls, (
        "spy_policy was never invoked across 50 dev episodes - "
        "no wakeup tick occurred for any of them"
    )
    for args, kwargs in calls:
        assert len(args) == 1, f"policy received {len(args)} positional args, expected 1: {args}"
        assert not kwargs, f"policy received keyword args, expected none: {kwargs}"
        (view,) = args
        assert isinstance(view, EpisodeView), (
            f"policy received {type(view)!r}, expected EpisodeView"
        )
        for attr in _LATENT_ATTRS:
            assert not hasattr(view, attr), f"EpisodeView leaked latent attribute {attr!r}"
```

**`tests/test_gate_precedence.py` — confirmed to EXIST** (named in
`gate.py`'s docstring; verified present via directory listing, then
opened and read). **Path:** `tests/test_gate_precedence.py`. **Line
count:** 106.

### Complete verbatim contents

```python
"""docs/A3-DESIGN.md §8: "Precedence: R2, R4 -> R3 -> R1, R8 -> R5, R6."
A proposal that violates multiple rules must fire only the
highest-precedence one.

Note there is no "R7" gate rule (EVAL.md §5.2 row 7, "no audit record: 0",
is a structural runner invariant - one ledger record per tick - not a
rejectable gate rule; see tests/test_ledger_completeness.py). The
precedence chain therefore covers exactly R1-R6 and R8 (7 rules), which
is what src/rrx/agent/gate.py implements and what this file checks.
"""

from __future__ import annotations

from rrx.agent.gate import evaluate_gate
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


def _view(**overrides) -> EpisodeView:
    base = dict(
        subscription_id="dev-1000",
        subscription_state="pending",
        invoice_amount_inr=50000,
        days_since_first_failure=0,
        auto_retries_remaining=3,
        next_auto_retry_day=1,
        decline_code="card_expired",
        billing_amount_inr=50000,
        contact_history=(),
        budget_remaining=3,
    )
    base.update(overrides)
    return EpisodeView(**base)


def _proposal(action_type: str, remedy: str | None = None) -> Proposal:
    return Proposal(
        action_type=action_type, remedy=remedy, rationale="test", reason_code="test"
    )


def test_r3_beats_r5_when_both_violated():
    """CONTACT(card_change) for insufficient_funds (violates R3) with
    budget_remaining=0 (would also violate R5). R3 > R5 in precedence -
    only R3 should fire."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"),
        _view(decline_code="insufficient_funds", budget_remaining=0),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R3"


def test_r4_beats_r3_when_both_violated():
    """CONTACT(card_change) for payment_risk_check_failed - R3's forbidden
    set is {insufficient_funds, transaction_limit_exceeded}, so R3 does
    NOT fire here on decline_code alone; R4 fires on decline_code ==
    payment_risk_check_failed regardless of remedy. This proves R4 (tier
    1) preempts what would otherwise reach R3 (tier 2) for ANY remedy,
    including one that would look R3-like if the decline_code differed."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"),
        _view(decline_code="payment_risk_check_failed"),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R4"


def test_r2_beats_r4_precedence_tie_broken_deterministically():
    """subscription_state=cancelled (R2) AND decline_code=
    payment_risk_check_failed (R4) simultaneously - both tier-1 rules.
    The implementation's fixed sub-order (R2 checked before R4) must fire
    R2, deterministically, every call."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "topup_reminder"),
        _view(subscription_state="cancelled", decline_code="payment_risk_check_failed"),
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R2"


def test_r1_beats_r8_precedence_tie_broken_deterministically():
    """An out-of-schema action_type (R1) is, by construction, never
    action_type == "CONTACT", so R8 (which requires CONTACT) can never
    actually co-fire with R1 in practice. This proves R1 alone still
    fires cleanly (not silently swallowed by the R8 check that follows it
    in the same precedence tier)."""
    verdict = evaluate_gate(
        _proposal("RETRY"), _view(decline_code="incorrect_otp")
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R1"


def test_r5_beats_r6_when_both_violated():
    """CONTACT with budget_remaining=0 (R5) plus an out-of-window
    send_hour override (R6, testability-only). R5 > R6 in precedence -
    only R5 should fire."""
    verdict = evaluate_gate(
        _proposal("CONTACT", "card_change"),
        _view(budget_remaining=0),
        send_hour="23:00",
    )
    assert not verdict.accepted
    assert verdict.rule_fired == "R5"
```

This file's own docstring references `tests/test_ledger_completeness.py`
as the enforcer of R7's structural (one-record-per-tick) invariant — a
file **not opened in this pass**, existence unconfirmed either way;
flagged in Section 7's MISSING AUTHORITATIVE CONTEXT-equivalent note.

### Direct answers

**Is there ANY test asserting `reason_code` ∈ the frozen 7-value set?**
**NONE EXISTS.** Searched all of `tests/` (`grep -rln
"REASON_CODES\|reason_code.*in.*{"`) — the only hit,
`tests/test_reason_codes_reference_valid_declines.py` (opened and read
in full this pass), asserts that every `decline_code` *referenced inside*
`ADMISSIBLE_DECLINE_CODES`'s value sets is a member of `ALL_DECLINE_
CODES` and resolves to a verified taxonomy code — it never constructs a
`Proposal` and never checks that a `Proposal.reason_code` value is a
member of `REASON_CODES` (the 7-value frozenset in `reason_codes.py`).
`Proposal.reason_code` is typed as a bare `str` with **zero runtime
validation** anywhere in `src/rrx/agent/gate.py` or `src/rrx/agent/
ledger.py` (confirmed by re-reading both files' full text, pass 1
Section 7) — every gate-rules test file constructs proposals with
`reason_code="test"` (see `_proposal()` helpers, `tests/test_gate_
rules.py:38-41`, `tests/test_gate_precedence.py:36-39`), a value that is
**not one of the 7 frozen values**, and the gate accepts it without
complaint, because the gate never inspects `reason_code` at all (`R1-R8`
operate only on `action_type`/`remedy`/`subscription_state`/
`decline_code`).

**Is there ANY test asserting a gate-accepted proposal has a legal
executor mapping?** **NONE EXISTS.** Searched all of `tests/` (`grep -rln
executed_action`) — zero files reference `executed_action` at all. This
directly confirms pass 1's UNENFORCED finding (Section 7 there): the
`CONTACT` proposal with `remedy=None`/an unrecognized `remedy` string,
silently executed as WAIT despite `gate_verdict.accepted=True`, has no
test coverage anywhere, in either pass.

**Is there ANY test that computes or asserts `wait_rate`?** **NONE
EXISTS.** Searched all of `tests/` and `src/` (`grep -rln "wait_rate"`)
— zero hits anywhere in the entire repository, including the two files
`EVAL.md §5.3`/`docs/A3-DESIGN.md §17` cite this metric's exact
definition ("WAIT decisions / wake-up decisions") in prose only. No code
computes it.

---

## 6. STRESS SPLIT USAGE

**Every caller of `stress_indices()`, `STRESS_INDICES`, or the
`"stress"` split string, repo-wide** (`.venv` excluded):

```
src/rrx/harness/splits.py:30:  STRESS_SPLIT = "stress"
src/rrx/harness/splits.py:33:  STRESS_INDICES = range(STRESS_SEED_START, STRESS_SEED_START + STRESS_N)  # 5000-5299
src/rrx/harness/splits.py:46:  def stress_indices() -> range:
src/rrx/harness/splits.py:47:      return STRESS_INDICES
```

**That is the complete list.** `stress_indices()`/`STRESS_INDICES`/
`STRESS_SPLIT` are defined in exactly one file and **called or
referenced nowhere else in the entire repository** — no test, no
diagnostic script, no other module. (Note: `tests/test_stage5_
falsification.py`'s Test 5 uses a *different* range, `range(5000, 5000 +
3000)` — `_T5_INDICES` — which numerically overlaps the start of the
`stress` range `range(5000, 5300)` but is an **independent, unrelated**
constant in that file, not a call to `stress_indices()`; flagged here
only to avoid a false-positive grep match, not because it uses the
stress split.)

**Does any frozen doc state when stress may be run, or whether stress
runs are single-use?** **NOT SPECIFIED.** `EVAL.md §3.5`'s splits table
gives `holdout` an explicit single-use annotation ("**Once** per
candidate release") and a corresponding sentence ("Every holdout run —
including unsuccessful ones — is logged in `results/holdout_runs.md`");
the `stress` row (`EVAL.md:233`, `| stress | 300 | 5,000–5,299 |
Adversarial |`) carries **no such annotation** — no stated cadence, no
"once per X" rule, no logging requirement analogous to `holdout_
runs.md`. `SIM.md`, `docs/A3-DESIGN.md`, and `CHANGELOG.md` mention
`stress` only in passing (the all-`cancelled` stress cohort's
environment-restraint caveat, `EVAL.md §8` item 8 / `A3-DESIGN.md §20`)
and never state a run-frequency policy either. Consistent with this:
`src/rrx/harness/splits.py`'s own code treats `stress_indices()` as a
plain, unguarded function — no `authorized=True` parameter, no exception
class, unlike `holdout_indices()`'s explicit `HoldoutNotAuthorizedError`
guard. The asymmetry is real and appears deliberate (stress is
"Adversarial" test data, not a scored/pre-registered comparison the way
`holdout` is) but is nowhere stated as a deliberate design choice in any
frozen document.
---

## 7. NEW GAPS AND CONFLICTS FOUND IN PASS 2

### CONFLICTS

**C1 — Sweep cell count: frozen spec text says 22, the actual (tested,
passing) code produces 26.** `EVAL.md §6A` (three separate places,
`EVAL.md:484-499, 501-510`) and `docs/A3-DESIGN.md §18` both say "all 22
cells" / "full 22-cell sweep" / "the full 22 cells." `results/
sensitivity.md` — checked into git, header states "Generated by `make
docs`. Do not hand-edit" — lists exactly 22 `PENDING` rows and a "Pass
mark 18 / 22" footer. **But** `src/rrx/spec/registry.py`'s
`enumerate_cells()`, exercised by `tests/test_model_params_swept.py`
(dumped in full, Section 2 above), produces **26** cells with the
current `configs/model_params.yaml` settings
(`include_topup_acceleration_cells: false`) — asserted directly by
`test_cell_count_matches_locked_design` (`assert len(cells) ==
expected` where `expected = 26`), and this test **passed** in pass 1's
one `pytest -q` run (not in the single reported failure). The module
docstring of `test_model_params_swept.py` states plainly: *"eval-spec-
v1.1 (2026-08-26): the cell count moved from 22 to 26... two [MODEL]
parameters (`ambiguous_cause_split`, `transient_block_clearance`) ...
were marked `sweep_required: true` but nested inside a `definition:`
block that `enumerate_cells()` did not read, so they silently
contributed zero cells."* That fix predates (2026-08-26) `EVAL.md
§6A`/`docs/A3-DESIGN.md`'s "22 cells" language (`eval-spec-v1.4`,
2026-08-27) — meaning **the currently-frozen spec text was written a day
after the code it describes stopped matching that number**, and nothing
in `eval-spec-v1.4`'s changelog entry (quoted in full, Section 4 above)
mentions the 22→26 change at all — the amendment's own "Verification-
driven correction" section instead only corrects an unrelated claim
about A2's sweep having already been run. `configs/model_params.yaml`
itself still carries a stale comment (`sweep.rounding: ceil # ceil(0.80
* 22) = 18`) consistent with the old count, even though its own DEFECT
comments elsewhere in the same file describe the fix that produced 26.
**Practical consequence:** the required pass mark is `ceil(0.80 × 26) =
21` per the actual code (`test_required_wins_is_ceil_of_eighty_percent`,
confirmed passing), not the "18 / 22" `results/sensitivity.md` currently
displays — that artifact is stale and was not regenerated (`make docs`)
after the 2026-08-26 fix, despite its own "Generated by `make docs`"
header implying it should track the registry automatically.

**C2 — Runner module placement: `A3-DESIGN.md`/`CHANGELOG.md` both say
`src/rrx/agent/runner.py`; the actual, tested code is
`src/rrx/harness/runner.py`, and this is not recorded in either frozen
document.** Fully detailed in Section 4 above. `docs/A3-DESIGN.md §2`'s
module-layout block explicitly lists `src/rrx/agent/runner.py — the
day-loop driver (§3)`. `CHANGELOG.md`'s `eval-spec-v1.4` entry, section
F, restates this as settled fact: *"Module locations: runner, policy,
planner, prompt builder, gate, and ledger all under
`src/rrx/agent/`"* — written 2026-08-27, the same day as the design
freeze. The actual Day 4 implementation (commits `7238c6f`, `447997a`,
also 2026-08-27 per the tag/commit ordering) instead created
`src/rrx/harness/runner.py`, entirely outside the guarded package — a
placement its own docstring and `tests/test_agent_boundary.py`'s
docstring both justify with real, sound reasoning (the runner needs
`_EpisodeState`/`_send_message`/full `rrx.sim` access no policy may
ever have), calling it "the Task 4A file-plan correction." **This is a
genuine, reasoned design change that was never propagated back into
either frozen document** — `A3-DESIGN.md` and `CHANGELOG.md` both still
describe the superseded plan, and nothing marks either of them as
stale on this specific point. Functionally this does not break the
`GUARDED_PACKAGES`/`test_no_latent_leak.py` invariant (the module simply
isn't inside the guard either way it's placed, and the guard's own
`GUARDED_PACKAGES` tuple never named `runner.py` specifically) — so this
is a documentation/design-freeze integrity gap, not a safety-invariant
violation.

**C3 — `EVAL.md §5.2`'s literal 8-gate table implies gate names distinct
from `EVAL.md`'s later `[AMENDMENT, eval-spec-v1.4]` note and
`A3-DESIGN.md §8`'s table — not a functional conflict, but worth naming
precisely.** Not elevated to a numbered conflict here because, on
inspection, `EVAL.md`'s own amendment paragraph directly beneath the
table (`EVAL.md:394-409`) already reconciles the two by pointing at
`docs/A3-DESIGN.md §8` for the actual rule IDs — this is the frozen
text explicitly deferring to the companion doc, not an unacknowledged
disagreement. Recorded here only as a "considered, not a conflict"
note, matching the standard set for C1/C2 above.

### GAPS (new, not already listed in pass 1 §11)

**G1 — No code applies an enumerated `Cell` to a config to produce a
perturbed run.** `enumerate_cells()` only enumerates (Section 2 above,
confirmed by exhaustive re-read of `registry.py` and grep for
`apply_cell`/similar names). `resolve_config()` (`src/rrx/spec/
resolver.py`, referenced only via `tests/test_latent_snapshot.py` in
pass 1) exists and is exercised for exactly one cell in one test — no
code path applies all 26 cells systematically. This sits directly
upstream of pass 1's already-noted gap that the sweep has never been
run for any arm (pass 1 §11 GAP 9) — this pass identifies the specific
missing function, not just the missing run.

**G2 — `gateway_technical_error` is a self-flagged, still-open gap
inside the frozen `configs/population.yaml` itself.** Quoted in full,
Section 3 above: `in_v1_cohort: true` in `data/decline_codes.yaml` (not
independently verified — still not opened in either pass) but carries
zero weight in `population.yaml#/failure_mix` and never appears as an
`opening_conditions` entry, so it can never be sampled. The config
file's own author writes: *"Either add it to EVAL 3.2 with a weight, or
set `in_v1_cohort: false`... Flagged, not silently resolved."* Neither
resolution has happened as of this pass.

**G3 — `configs/costs.yaml` prices a `voice` channel
(`messaging.voice_per_minute`, `annoyance.applies_to` includes
`voice`) that does not exist anywhere in the actual channel model.**
`episode.yaml#/latent/channel_response_propensity/channel_multipliers`
only defines `whatsapp`/`sms`/`email` (confirmed, Section 3 above and
pass 1's dump); `AGENT_CHANNEL`/`AUTO_EMAIL_CHANNEL` in `engine.py`
likewise never reference voice. Not harmful (an unused cost row), but an
unreconciled leftover between the cost config and the actual simulated
channel set.

**G4 — `configs/episode.yaml` self-documents its own missing-harness gap
one day before the code side rediscovered it.** Its `out_of_scope_here.
seeds_and_splits` note (quoted, Section 3) states seeds/splits "still
need a home — `configs/eval.yaml` — before the harness can run," and no
such file exists. This corroborates, from the config-authoring side,
exactly the same "no canonical run entry point" finding pass 1 reached
independently from the code side (its GAPS 1/7/10) — worth recording as
independent, config-side corroboration, not a new category of problem.

**G5 — `tests/test_ledger_completeness.py`, cited by
`tests/test_gate_precedence.py`'s own docstring as the enforcer of R7's
structural invariant, was not opened in this pass — its existence is
unconfirmed either way.** Distinct from `test_gate_precedence.py`
itself (confirmed to exist and dumped in full above). Flagged as an
open thread for a future pass, not resolved here.

---

## 8. CORRECTIONS TO PASS 1

Stated plainly, per instructions, not softened.

**CORRECTION 1 (major).** Pass 1's Section 8/"COMPLETENESS CHECKLIST"
and Section 11/"GAPS" repeated `EVAL.md §6A`'s and `results/
sensitivity.md`'s "22 cells" / "18 / 22" figures without independently
verifying them against the actual `enumerate_cells()` code or reading
`tests/test_model_params_swept.py`. **This was wrong; the real,
currently-passing cell count is 26, not 22**, and the required pass mark
is 21 of 26, not 18 of 22. This pass's C1 (Section 7 above) documents
the full discrepancy. Pass 1 did not fabricate this — it accurately
transcribed what the frozen spec text and the one existing results
artifact say — but it presented "22 cells" as settled fact rather than
flagging that the underlying registry code (which pass 1 also dumped in
full, in its own Section 8) actually produces a different, larger
number. A careful reading of pass 1's own dumped `model_params.yaml`
content (which pass 1 quoted in full, including the DEFECT comments
about `ambiguous_cause_split` and `transient_block_clearance` previously
contributing zero cells) contains the seeds of this discrepancy, but
pass 1 never connected them to the "22 cells" claims made three
paragraphs earlier in the same document.

**CORRECTION 2 (major).** Pass 1's Section 8 stated the runner
placement (`src/rrx/harness/runner.py`) as a fact about the current
codebase, correctly, but did **not** flag that this placement
contradicts `docs/A3-DESIGN.md §2`'s explicit module-layout table
(`src/rrx/agent/runner.py`) — pass 1's own Section 5/Batch-2 dump of
`A3-DESIGN.md §2` contains that exact contradicting text, verbatim, but
pass 1's Section 11 "CONFLICTS" section concluded **"None found in this
pass"** for EVAL.md-vs-A3-DESIGN.md conflicts and did not separately
check A3-DESIGN.md against the actual filesystem layout at all. This
pass's C2 (Section 7 above) shows the deviation is real, deliberate, and
justified in code/test docstrings — but was never reconciled back into
either `A3-DESIGN.md` or `CHANGELOG.md`, a genuine documentation-freeze
integrity issue pass 1 had all the raw material to find (it had already
read and quoted both the relevant `A3-DESIGN.md §2` text and the
`runner.py` docstring in adjacent sections of its own document) but did
not cross-reference.

**CORRECTION 3 (minor, scope clarification, not an error).** Pass 1's
Batch-4/Section 7 "COMPLETENESS CHECKLIST" marked the A1/A4/A2-variant
question `[PARTIAL]` and said "A1 and A4 have no standalone
implementation anywhere... MISSING as a dumped file" — accurate as
stated, but this pass's full dump (Section 1 above) shows the
construction is more structured than "ad hoc" suggests: A1/A4 (plus two
other scratch arms) are built via a disciplined, documented,
auto-teardown `pytest` fixture pattern (`_register_test_arms`),
independently reused by a second file (`test_a2_variants.py`) for the
A2 variants — not a one-off improvisation. Not a factual error in pass
1, but its characterization undersold how deliberate and consistent the
pattern is across both test files. Also newly established this pass:
A1-U (`EVAL.md`'s "A1 — Unbounded" diagnostic arm) is confirmed **fully
MISSING** — pass 1 never checked for it at all, since it was outside
that pass's batch scope.

**CORRECTION 4 (minor, no error, additional precision).** Pass 1's
Section 8 stated `paired_bootstrap_ci` "lives in `src/rrx/sim/
run_stage3.py`... a one-off Day-2 diagnostic script" and separately
noted `test_stage5_falsification.py` overrides `n_resamples=5000` "in
that specific test" (singular). This pass's full dump (Section 1)
confirms it is **every** call site in that file (6 of 6 calls across
Tests 1, 2, and 3) that uses `n_resamples=5000`, never the module
default of 10,000 — a small precision gap in pass 1's phrasing ("that
specific test" implied one call, not the file's uniform practice), not
a substantive error.

**No other statement in pass 1 was found to be factually wrong in this
pass's targeted re-verification.** In particular: the 2000/2000 null-
policy parity claim, the `1 failed, 622 passed` summary, the ledger's
22-field count, the `EpisodeView`/`ContactRecord` field counts and
allowlist-enforcement mechanism, the `_POLICIES` registry containing
only `A0`/`A2` by default, the gate's R1–R8 rule table and precedence
order, and the UNENFORCED gate-accepted/no-legal-executor-mapping
finding were all independently re-confirmed by this pass's fresh reads
of the underlying files and are unchanged.

---

## 9. COMPLETENESS CHECKLIST

**B1 — A1/A4/A2-variant construction**
- [DUMPED] `tests/test_stage5_falsification.py` — full verbatim, 670 lines
- [DUMPED] A1 construction (module-level function), registration
  (`_register_test_arms` fixture, module-scoped autouse, WITH teardown)
- [DUMPED] A4 construction (separate episode-loop function pair, never
  registered into `_POLICIES`), latent-state access (direct `rrx.sim.
  latent` import, legitimate since `tests/` is unguarded)
- [DUMPED] A2-corrected-v1/A2-strengthened registration — confirmed in a
  **different** file (`tests/test_a2_variants.py`), exact keys
  `"A2_CORRECTED_V1"` / `"A2_STRENGTHENED"`
- [DUMPED] A1's T+0/T+3 schedule confirmed matching `EVAL.md §4`
- [MISSING] A1-U — confirmed absent, repo-wide grep, zero hits
- [DUMPED] What non-test code would need to run A1/A2-strengthened over
  `DEV_INDICES` — described, not implemented
- [DUMPED] Inline metric computation + all 6 `paired_bootstrap_ci` call
  sites, all using `n_resamples=5000`

**B2 — Sweep registry**
- [DUMPED] `src/rrx/spec/registry.py` — full verbatim, 304 lines
- [DUMPED] `enumerate_cells()` signature/return type/`Cell` structure
- [DUMPED] Exact cell count — **26, confirmed via passing test, NOT 22**
  (see Correction 1 / Conflict C1)
- [DUMPED] Nested `sweep_required` handling explained with code reference
- [DUMPED] `include_topup_acceleration_cells: false` respected — confirmed
- [DUMPED] Enumerate-only vs apply-to-config distinction — stated
  plainly: **enumerate-only**, no apply function exists (new GAP G1)
- [DUMPED] `src/rrx/spec/manifest.py` — full verbatim, 82 lines
  (re-dump of pass-1 content, as requested)
- [DUMPED] `tests/test_model_params_swept.py` — full verbatim, 274 lines
- [DUMPED] `tests/test_model_params_registry.py` — full verbatim, 121 lines

**B3 — Frozen configs**
- [DUMPED] `configs/episode.yaml` — full verbatim, 234 lines, all four
  requested fields (`agent_budget`, `razorpay_retry_engine`,
  `payment_method_change_effect`, `episode.window_days`) reported
- [DUMPED] `configs/costs.yaml` — full verbatim, 55 lines
- [DUMPED] `configs/population.yaml` — full verbatim, 186 lines (under
  the 400-line threshold, dumped whole per instructions rather than only
  the two named blocks)

**B4 — CHANGELOG**
- [PARTIAL, per instructions] `CHANGELOG.md` is 1,211 lines (over the
  600-line threshold) — dumped the `eval-spec-v1.3`, `eval-spec-v1.4`,
  and `sim-v1` entries in full, plus the complete `## ` heading list, per
  the batch's own fallback instruction for long files
- [DUMPED] v1.3 baseline-resolution derivation and empirical numbers
- [DUMPED] Runner-placement deviation search — **NOT RECORDED IN
  CHANGELOG** (quoted the v1.4 entry's contradicting claim directly)

**B5 — A3 pipeline tests**
- [DUMPED] `tests/test_a3_runner_parity.py` — full verbatim, 148 lines
- [DUMPED] `tests/test_gate_rules.py` — full verbatim, 184 lines
- [DUMPED] `tests/test_agent_boundary.py` — full verbatim, 58 lines
- [DUMPED] `tests/test_gate_precedence.py` — **confirmed to EXIST**
  (contrary to pass 1's uncertainty about it), full verbatim, 106 lines
- [DUMPED] reason_code-enum test search — **NONE EXISTS**
- [DUMPED] gate-accepted/legal-executor-mapping test search — **NONE
  EXISTS**
- [DUMPED] `wait_rate` test search — **NONE EXISTS**

**B6 — Stress split usage**
- [DUMPED] Every caller of `stress_indices()`/`STRESS_INDICES`/
  `"stress"` — exactly the 4 lines in `splits.py` itself, zero external
  callers
- [DUMPED] Frozen-doc statement on stress run cadence — **NOT
  SPECIFIED**, with the `holdout`-vs-`stress` asymmetry noted explicitly

**B7 — Gap report**
- [DUMPED] Section 7: 2 new CONFLICTS (C1 cell-count, C2 runner-
  placement), 1 considered-and-not-elevated note (C3), 5 new GAPS
  (G1–G5)
- [DUMPED] Section 8: 4 corrections to pass 1 (2 major, 2 minor), plus an
  explicit statement of what was re-checked and found unchanged
- [DUMPED] This checklist (Section 9)
