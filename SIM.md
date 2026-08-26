# SIM.md — Simulator World Specification

**Project:** Subscription recovery orchestration agent (Razorpay AI Buildathon, Track 03 — AI Revenue Recovery)

**Status:** Day 2, Stage 0. Freezes at `sim-v1` — see §0.

---

## §0. Purpose and relationship to EVAL.md

`EVAL.md` specifies **what is measured**. This document specifies **the world it is
measured in**: the hidden mechanics that generate episodes, decline codes, and
outcomes from actions. `EVAL.md` governs on conflict. Any conflict discovered
between this document and `EVAL.md` is a defect to be logged and reported, never
resolved by editing `EVAL.md`.

This document freezes at tag `sim-v1`, on the same terms `EVAL.md` froze at
`eval-spec-v1`: once tagged, changes require a new tagged version with a
changelog entry, and reopening it is justified only by a discovered validity
defect — never to improve an agent's expected performance.

**Update, eval-spec-v1.1 (2026-08-26):** the two gaps this document originally
recorded as open — `P(card | ambiguous decline)` and `bank_technical_error`
clearance timing — are now resolved in the frozen configs
(`population.yaml#/opening_conditions` and `episode.yaml#/latent`
respectively; see §6, §9). Separately, Q1 research found no primary
documentation supporting `send_subscription_link` as specified; it is removed
from the v1 action space (§3, §9), and the corresponding `EVAL.md §1.2` row is
footnoted as a defect under `EVAL.md §10`, not rewritten.

---

## §1. Hidden physical state

Four variables tracked per episode. These are the entire physical world; nothing
else changes as a result of an action.

| Variable | Type | Meaning |
|---|---|---|
| `card_chargeable` | bool | The card on file can be charged for recurring auto-debit |
| `funds_available_from` | day (float) | First day the account holds >= `invoice_amount_inr` |
| `mandate_alive` | bool | The mandate/subscription authorization still exists |
| `blocked_until` | day (float) | Day on which a transient issuer/risk block clears |

**These four variables are never projected into `EpisodeView`.** They are
architecturally unreachable from `rrx.agent` and `rrx.features` — enforced by
`tests/test_no_latent_leak.py` — the same boundary `EVAL.md §3.3` requires for
latent state. `rrx.agent` and `rrx.features` must never import `rrx.sim.latent`,
directly or transitively.

---

## §2. Decline code → physical state at T=0

A translation table only. No success probabilities appear in this section —
those live in §3 and §4. Covers all nine opening conditions from `EVAL.md §3.2`
/ `population.yaml#/opening_conditions`.

| Opening condition | Physical state at T=0 |
|---|---|
| `insufficient_funds` | `card_chargeable = true`; `funds_available_from` drawn from the balance-restore mechanism (§6, `episode.yaml#/latent/balance_restore_delay`) |
| `card_declined` / `payment_failed` (ambiguous group) | `card_chargeable ~ Bernoulli(p_card_cause = 0.50)` — `population.yaml#/opening_conditions` (`ambiguous_decline` entry); if card ok, `funds_available_from` drawn as above |
| `card_expired` | `card_chargeable = FALSE`; `funds_available_from` = day 0 |
| `debit_instrument_blocked` | `card_chargeable = FALSE`; `funds_available_from` = day 0 |
| `card_not_enrolled` (+ aliases) | `card_chargeable = FALSE`; `funds_available_from` = day 0 |
| `cancelled` (subscription already cancelled at open) | `mandate_alive = FALSE` |
| `bank_technical_error` | `blocked_until ~ Uniform(0, 2]` days — `episode.yaml#/latent/bank_technical_error_clearance` |
| `transaction_limit_exceeded` | `blocked_until` = never (within the 30-day window) |
| `payment_risk_check_failed` | `blocked_until` = never (within the 30-day window) |

Unless stated otherwise, `mandate_alive = TRUE` and `blocked_until` = never at
T=0 for all rows except `cancelled`.

---

## §3. Actions → physical state, via message CONTENT, never via correctness

Table of what each message names — content, not correctness, is what moves
state:

| Action | Names |
|---|---|
| `send_card_change_prompt` | card, not dues |
| `send_topup_reminder` | dues, not card |
| Razorpay automatic email | both — `[CITE]` |

**Mechanism.** Engagement is a two-step gate: delivered (1.0 in v1), then
engaged with probability `channel_response_propensity[customer][channel]`
(`episode.yaml#/latent/channel_response_propensity`).

Razorpay's automatic failure email does **not** increment the fatigue exponent
in `channel_response_propensity.fatigue`. Consistent with `EVAL.md §9`'s
principle that it is not a contact, and with the cancellation hazard, which
already exempts it (`episode.yaml#/latent/cancellation/hazard_per_contact/applies_to_razorpay_auto_email`).
It appears in `contact_history[]` as an observable entry (`EVAL.md §3.4`)
without consuming budget or inducing fatigue.

**Card-naming mechanism.** An engaged CARD-naming message sets
`card_chargeable = true` with the customer's `card_change_completion_propensity`,
drawn **once per customer** from `episode.yaml#/latent/card_change_completion_propensity`
(`Beta(mean 0.55, concentration 6)`).

**Dues-naming mechanism.** An engaged DUES-naming message triggers a top-up
action with probability `episode.yaml#/latent/balance_restore_delay/topup_acceleration/p_topup_action`
(`0.35`). If triggered:

```
funds_available_from = min(original_delay, t_engage + Exponential(mean 0.5 days))
```

per the frozen rule at `episode.yaml#/latent/balance_restore_delay/topup_acceleration`.
`original_delay` is whatever the customer's balance-restore mixture (§6) already
drew for `funds_available_from`.

The `min` is load-bearing: acceleration only matters if the accelerated draw
lands before an auto-retry that was going to fire anyway (T+1…T+3). After halt,
an accelerated `funds_available_from` changes nothing, because no further retry
reads it (§4). **This `min`-against-the-retry-clock relationship is the entire
timing advantage a top-up reminder can create** — there is no other channel
through which this action affects the episode.

Acceleration is drawn **per engagement**, not per customer: each time a
dues-naming message is engaged with, a fresh `p_topup_action = 0.35` Bernoulli
trial and a fresh `Exponential(mean 0.5)` draw occur. Top-up responsiveness is
therefore **not a persistent customer trait** and is not inferable from contact
history. This is deliberate — a persistent trait here would create a fourth
source of agent advantage beyond the three `EVAL.md §3.4` pre-registers.

**Consequence, stated explicitly:** a card-change prompt sent for an
`insufficient_funds` episode names the card. The card was never broken. Nothing
changes. This is a no-op, not a penalty. **No function in this model evaluates
whether an action was the correct remedy** for a decline code — decline_code
sets physical state (§2), actions change physical state via message content
(this section), and the retry clock (§4) only ever reads physical state.

`hold_service_delivery` is **excluded from the v1 action space**. This is
recorded as a scope limitation of this document, narrowing `EVAL.md §1.2`'s
listed action space for v1 — not an edit to `EVAL.md`.

`send_subscription_link` is **also excluded from the v1 action space.** Q1
research (2026-08-26) found no primary Razorpay documentation describing a
customer-facing link that clears an already-failed subscription invoice for a
domestic card. Three real mechanisms exist and none matches: the card-change
email link restores the subscription but does not re-attempt previous
charges (`https://razorpay.com/docs/payments/subscriptions/payment-retries/`,
retrieved 2026-08-26; `https://razorpay.com/docs/payments/subscriptions/states/`,
retrieved 2026-08-26); manual invoice charge is Dashboard-only and explicitly
unsupported for domestic cards
(`https://razorpay.com/docs/payments/subscriptions/manually-charge-card/`,
retrieved 2026-08-26); Subscription Links are for initial authorisation only.
Modelling an action that names both card and dues would also dominate every
single-purpose remedy at equal contact cost, removing the remedy-matching
decision `EVAL.md §3.4` pre-registers as a source of agent advantage.

---

## §4. The clock

- Auto-retries fire at T+1, T+2, T+3 ONLY (`episode.yaml#/razorpay_retry_engine/card_schedule_days`, `[CITE]`).
- A retry at day `t` succeeds iff:

```
card_chargeable
AND t >= funds_available_from
AND mandate_alive
AND t >= blocked_until
```

- First success ends the episode.
- After T+3 the subscription is halted (`episode.yaml#/razorpay_retry_engine/state_after_exhaustion`)
  and **no further auto-retry fires**. Funds arriving after halt do nothing on
  their own — per `EVAL.md §1.3`, previous charges are not re-attempted after
  the subscription returns to `active`; only future billing cycles are charged.
- Window closes at T+30 (`episode.yaml#/episode/window_days`, `[DESIGN]`).
- Razorpay's automatic failure email fires at T+0 and at the halt transition,
  using the customer's email-channel propensity from
  `episode.yaml#/latent/channel_response_propensity` — no separate multiplier,
  no new parameter.
  - Email **content** (names both card and dues) is `[CITE]`:
    `https://razorpay.com/docs/payments/subscriptions/payment-retries/`,
    retrieved 2026-08-26. That page states the email contains a card-change
    link, and gives a worked example in which a customer with insufficient
    balance receives the failure email and then adds money to their account.
  - Email **schedule** (T+0 and halt) is `[CITE-PENDING]`.

**This email is the sole reason arm A0 recovers more than zero.**

---

## §5. Outcome resolution

- **Invoice recovery** occurs if and only if an auto-retry succeeds at T+1,
  T+2, or T+3. There is no in-scope mechanism by which a halted subscription's
  failed invoice is recovered. Subscription rescue remains available across
  the full 30-day window via card change.
- **Subscription rescue:** subscription state is `active` at T+30.
- **Regime A cancellation hazard** lives in a separate resolver that is never
  invoked under Regime B.

---

## §6. Parameter table

Tier 2 note on provenance: the Day-2 Stage-0 prompt originally proposed
additional Tier-2 magnitudes for four parameter families — a responsiveness
weight `w = 0.50`, a channel base response mean of `0.40` with `sigma_c = 0.80` /
`sigma_k = 0.60`, a flat `remedy_completion_propensity = 0.50`, and a flat
cancellation hazard of `0.03` per contact. All four families were already
frozen, with different values and in one case a different distributional
structure, in `episode.yaml` / `model_params.yaml` at `eval-spec-v1`. Per user
decision on 2026-08-26, those four families are governed entirely by the frozen
configs cited below; the Stage-0 prompt's numbers for them are superseded and do
not appear elsewhere in this document.

### Tier 1 — fixed by the frozen configs

| Parameter | Value | Source |
|---|---|---|
| Invoice amount | `LogNormal(mu=ln(2000), sigma=1.0)`, rejection-sampled to `[100, 50000]`, rounded to nearest rupee | `population.yaml#/invoice_amount_inr` |
| Failure mix (9 conditions) | `insufficient_funds` .32, `card_declined_or_payment_failed` .24, `card_expired` .16, `debit_instrument_blocked` .12, `card_not_enrolled`(+aliases) .06, `subscription_cancelled` .05, `bank_technical_error` .03, `transaction_limit_exceeded` .01, `payment_risk_check_failed` .01 | `population.yaml#/failure_mix/conditions` |
| Remaining subscription lifetime (Regime A only) | `Geometric(mean 9 cycles)` | `episode.yaml#/latent/cancellation/remaining_subscription_lifetime_cycles` |
| Retry schedule | T+1, T+2, T+3; halt after exhaustion | `episode.yaml#/razorpay_retry_engine/card_schedule_days`, `#/state_after_exhaustion` |
| Halt boundary | day 3 | `episode.yaml#/payment_method_change_effect/halt_boundary_day` |
| Episode window | 30 days | `episode.yaml#/episode/window_days` |
| Contact budget | 3 contacts/episode | `episode.yaml#/agent_budget/max_contacts_per_episode` |
| Quiet hours | 09:00–21:00 IST, contacts only | `episode.yaml#/agent_budget/quiet_hours_ist` |
| Balance-restore timing | 45% transient `Exponential(mean 2.0d)` truncated `[0,30]` + 55% salary-cycle (`salary_day_pmf {1:.55, 7:.20, 25:.10, 30:.15}` + `Gamma(shape 2, mean 1.0d)` jitter); top-up acceleration `p_topup_action=0.35`, `Exponential(mean 0.5d)`, rule `min(original, t_engage+draw)` | `episode.yaml#/latent/balance_restore_delay` |
| Channel response propensity | `θ_c ~ Beta(mean 0.28, concentration 7)`; multipliers `whatsapp 1.15 / sms 1.00 / email 0.65`; fatigue `0.80^(prior contacts)`; tenure coupling `logit(θ_c) += 0.35 · z(tenure_days)` | `episode.yaml#/latent/channel_response_propensity` |
| Card-change completion propensity | `Beta(mean 0.55, concentration 6)`, conditional on engagement, drawn once per customer | `episode.yaml#/latent/card_change_completion_propensity` |
| Cancellation hazard (Regime A only) | `h_n = clamp(0.010 * 1.5^(n-1), 0, 1)`; cumulative ≈ 4.6% over 3 contacts; does not apply to the Razorpay auto email | `model_params.yaml#/parameters/cancellation_hazard_and_ltv/definition/hazard_per_contact` |
| `P(card \| ambiguous decline)` | `p_card_cause = 0.50`, max-entropy | `population.yaml#/opening_conditions` (`ambiguous_decline` entry); `model_params.yaml#/parameters/failure_mix_weights/definition/ambiguous_cause_split` |
| `bank_technical_error` clearance | `Uniform(0, 2]` days | `episode.yaml#/latent/bank_technical_error_clearance`; `model_params.yaml#/parameters/balance_restore_timing/definition/transient_block_clearance` |

### Tier 2 — no external source; value and selection rule

Empty as of `eval-spec-v1.1`. Both gap entries previously listed here —
`P(card | ambiguous decline)` and `bank_technical_error` clearance — were
resolved into the frozen configs on 2026-08-26 (Q1 research) and moved to
Tier 1 above.

### Tier 3 — the six [MODEL] families

Exactly six, matching `model_params.yaml`'s registry:

1. **Invoice amount** — `population.yaml#/invoice_amount_inr`, `model_params.yaml#/parameters/invoice_amount`
2. **Failure mix weights** (includes `P(card | ambiguous)` = `p_card_cause`) — `population.yaml#/failure_mix`, `population.yaml#/opening_conditions` (`ambiguous_decline` entry), `model_params.yaml#/parameters/failure_mix_weights`
3. **Transient resolution timing** — funds arrival = balance-restore mixture (Tier 1); block clearance = `bank_technical_error_clearance` — `episode.yaml#/latent/balance_restore_delay`, `episode.yaml#/latent/bank_technical_error_clearance`, `model_params.yaml#/parameters/balance_restore_timing`
4. **Channel response propensity** — `episode.yaml#/latent/channel_response_propensity`, `model_params.yaml#/parameters/channel_response_propensity`
5. **Remedy completion propensity** (card change only, since `send_subscription_link` is excluded — §3, §9) — `episode.yaml#/latent/card_change_completion_propensity`, `model_params.yaml#/parameters/card_change_completion_propensity`
6. **Cancellation hazard + LTV** (Regime A only) — `episode.yaml#/latent/cancellation`, `model_params.yaml#/parameters/cancellation_hazard_and_ltv`

**Independence of funds arrival from billing cycle.** Funds arrival is drawn
independently of `billing_cycle_day`, because `billing_cycle_day` is visible in
`EpisodeView` and a correlation would create a fourth source of agent advantage
that `EVAL.md §3.4` does not pre-register, breaking `EVAL.md §7` criterion 4.

**Interpretation note — channel ranking is not the inferable signal.** Under
the frozen parameterisation, `channel_multipliers` is a fixed table identical
for every customer, so channel *ranking* (WhatsApp > SMS > Email) is a global
constant and requires no inference by any arm. `EVAL.md §3.4`'s third
pre-registered advantage therefore manifests, under this simulator, as
estimating a customer's overall response propensity (`θ_c`) and deciding
*whether and how often* to contact at all — shaped by fatigue `0.80^n` — rather
than as learning which channel to prefer. `EVAL.md §3.4`'s substantive claim
("response propensity varies and is partly inferable") holds; only its row
title overstates the channel-ranking dimension. This is a consequence of the
frozen config, recorded here, not a change to `EVAL.md`.

---

## §7. Tier boundary

Governing rule: **a distribution family is `[DESIGN]`; a magnitude is `[MODEL]`.**

**`[INVARIANT]`**
- Hidden physical state (§1) is architecturally unreachable from `rrx.agent` /
  `rrx.features` (`tests/test_no_latent_leak.py`).
- No function branches on `decline_code` and remedy correctness jointly — the
  outcome model is mechanism-based only (§2–§4).

**`[DESIGN]`**
- Episode window = 30 days (`episode.yaml#/episode/window_provenance`)
- v1 method = domestic cards only (`episode.yaml#/episode/v1_method_provenance`)
- Contact budget = 3, quiet hours 09:00–21:00 IST (`episode.yaml#/agent_budget`, `provenance: DESIGN`)
- `hold_service_delivery` and `send_subscription_link` excluded from v1 action
  space (§3)
- Distribution families: lognormal (invoice amount); Beta (channel trait,
  completion propensity); two-component mixture — truncated exponential +
  salary-day pmf with gamma jitter (balance restore); uniform (bank-technical
  block clearance); Bernoulli (ambiguous-decline card cause); geometric
  (remaining lifetime); `clamp(h0 · gamma^(n-1))` functional form
  (cancellation hazard)

**`[MODEL]`**
- All Tier 1 magnitudes in §6: invoice median/sigma; failure-mix weights;
  balance-restore mixture weights (.45/.55), salary-day pmf, jitter shape/mean,
  `p_topup_action=0.35`, accelerated-delay mean; `bank_technical_error`
  clearance bound (`2` days); ambiguous-decline `p_card_cause=0.50`; channel
  trait mean/concentration, channel multipliers, fatigue base, tenure beta;
  completion propensity mean/concentration; cancellation `h0`/`gamma`;
  remaining-lifetime mean cycles.

**`[CITE]`** (referenced, not part of the three-way boundary above, listed for
completeness): retry schedule T+1/T+2/T+3 and halt-after-exhaustion
(`episode.yaml#/razorpay_retry_engine`); halt boundary / manual-charge
unavailability (`episode.yaml#/payment_method_change_effect`); Razorpay
automatic failure-email existence and content (§3, §4).

---

## §8. Falsification tests this simulator must pass

Listed only — not implemented in this stage.

1. **Ordering** — A4 > A2-ish > A1-ish > A0, and A0 > 0.
2. **Wrong-remedy null** — an always-inverted-remedy policy performs ≈ A0 at 3x
   the contact cost.
3. **Timing null** — top-up reminders delivered after halt have ≈ zero effect
   on invoice recovery.
4. **CRN identity** — same episode index, different arms, identical latent
   draw.
5. **Responsiveness-signal null** — set
   `channel_response_propensity.customer_trait` concentration to a very large
   value (all customers share mean 0.28) and `tenure_coupling.beta = 0`. Any
   responsiveness-inference advantage must collapse to approximately zero.

---

## §9. Known limitations

- `hold_service_delivery` excluded from v1 action space (§3).
- Issuer downtime not modelled (`EVAL.md §3.2`).
- eMandate and UPI subscription retry models out of scope (`EVAL.md §1.4`).
- Razorpay automatic failure-email **schedule** is `[CITE-PENDING]` (§4).
- **RESOLVED (Q1, 2026-08-26, `eval-spec-v1.1`)** — `send_subscription_link`
  is excluded from the v1 action space. No primary Razorpay documentation
  describes a customer-facing link that clears an already-failed subscription
  invoice for a domestic card; see §3. Excluding it also avoids a design
  defect: an action naming both card and dues would dominate every
  single-purpose remedy at equal contact cost, removing the remedy-matching
  decision `EVAL.md §3.4` pre-registers as a source of agent advantage.
- **RESOLVED (2026-08-26, `eval-spec-v1.1`)** — `P(card | ambiguous decline)`
  is `p_card_cause = 0.50`, `population.yaml#/opening_conditions`
  (`ambiguous_decline` entry). Previously an open gap
  (`UNRESOLVED_intra_group_split`); folded into the `failure_mix_weights`
  `[MODEL]` family, not a seventh parameter.
- **RESOLVED (2026-08-26, `eval-spec-v1.1`)** — `bank_technical_error`
  clearance is `Uniform(0, 2]` days, `episode.yaml#/latent/bank_technical_error_clearance`.
  Previously an open gap, absent from all configs; folded into the
  `balance_restore_timing` `[MODEL]` family, not a seventh parameter.
