# EVAL.md — Evaluation Specification

**Project:** Subscription recovery orchestration agent (Razorpay AI Buildathon, Track 03 — AI Revenue Recovery)

**Status:** Pre-registered. Written before any agent code. Freezes at `eval-spec-v1` — see §10.

**Rule:** Any change after the tag is a new tagged version with a changelog entry. Results always report the spec version they ran under.

---

## 0. Provenance tiers

| Tag | Meaning | Obligation |
|---|---|---|
| `[CITE]` | External fact | URL + retrieval date |
| `[INVARIANT]` | A constraint we impose, not a belief about the world | Enforcing test |
| `[DESIGN]` | Experimental choice with no bearing on validity | None |
| `[MODEL]` | World assumption that could change the conclusion | Registered in `configs/model_params.yaml` and included in the six canonical sensitivity handles where applicable |

The six canonical `[MODEL]` **sweep parameters** are defined in `configs/model_params.yaml`. That file is the single source of truth for sweep membership. `sweep_required` flags in `population.yaml` and `episode.yaml` are deprecated and removed.

Composite parameters may contain fixed synthetic sub-assumptions. A fixed sub-assumption is not treated as a separate sweep parameter unless it has its own canonical sensitivity handle.

---

## 1. What we are measuring

### 1.1 The constraint that defines this project `[CITE]`

Razorpay retries failed subscription auto-charges **automatically and on a fixed schedule** — for cards, T+1, T+2, T+3, once daily, without merchant interference — after which the Subscription moves to `halted`. **Manual charging of a domestic card is not supported.**

**The merchant does not control retry timing and cannot trigger a retry.** An agent that schedules or sequences payment retries on Razorpay Subscriptions is designing against an API surface that does not exist. This spec therefore does not evaluate retry policy.

### 1.2 What the agent actually decides

An episode opens when a Subscription enters `pending` after a failed auto-charge. Razorpay's retry clock is already running and will run regardless. The agent decides:

**whether to contact the customer, when, on which channel, with which of a small set of remedies — and when to stop.**

Its verified action space `[CITE]`:

| Action | Notes |
|---|---|
| `send_card_change_prompt` | The actual recovery mechanism for card-validity failures |
| `send_topup_reminder` | For balance failures, only useful **before** auto-retries are exhausted |
| `send_subscription_link` | Clear dues on `pending` / `halted` |
| `hold_service_delivery` / `resume` | Merchant-side lever |
| `escalate_to_merchant` | Unknown or risk-flagged cases |
| `wait` | **An explicit, logged action.** Restraint must be a decision, not an absence of one. |
| `stop_episode` | Terminal |

[DEFECT, eval-spec-v1.1] The `send_subscription_link` row's `[CITE]` is not supported for domestic cards. Q1 research (2026-08-26) found no primary documentation for a customer-facing link that clears an already-failed subscription invoice on a domestic card. The action is excluded from the v1 action space; see `SIM.md §3` and `§9`. Recorded rather than rewritten, to preserve the frozen text.

Razorpay independently sends the customer a payment-failure email containing a card-change link `[CITE]`. That email is part of the world, not an arm's choice, and every arm — including A0 — operates on top of it. The agent's contacts are **additional** to it, which is why they carry annoyance cost.

### 1.3 Two things are recoverable, and they are not the same

Once a Subscription returns to `active` from `halted`, **previous charges are not re-attempted — only future billing cycles are charged** `[CITE]`. So:

- **Invoice recovery** — the specific failed invoice gets paid. Only possible while auto-retries remain (T+1…T+3), or via manual charge on an older invoice, which is unavailable for domestic cards.
- **Subscription rescue** — the Subscription returns to `active` via card re-authentication. Future revenue preserved; the failed invoice may still be lost.

Both are reported. Conflating them would overstate results.

### 1.4 Scope

**v1 cohort is domestic cards only** `[DESIGN]`. Razorpay's eMandate and UPI subscription retry models are documented in page sections we could not read (`data/decline_codes.md` §10.5); we will not model a retry engine we have not verified. Also out of scope: partial payments, chargebacks, multi-currency, human handoff, international cards.

**Episode window:** 30 days from the failed charge (T=0) `[DESIGN]`.

---

## 2. Cost and value model

The agent's only action is contact. Contacts cost ~₹0.02–₹0.18 `[CITE]` — negligible against the invoice. But contact is no longer the only thing at stake: **over-contacting risks the customer cancelling**, which forfeits not just the invoice but the Subscription's remaining lifetime value.

**Regime B — Equal contact budget (headline).** Every arm gets **3 contacts** per episode `[DESIGN]`, within 09:00–21:00 IST, not counting Razorpay's automatic email. Outcomes are **counted, not priced**: invoice recovery rate and subscription rescue rate. The claim is *"same contact budget, more invoices recovered and more subscriptions rescued"* — no invented monetary weighting anywhere in it.

Cancellation is a state change in the simulated world, so over-contacting can reduce the **Regime-B rescue rate directly**. Only the monetary valuation of cancellation and remaining LTV belongs to Regime A.

**Regime A — Monetised (secondary, `[MODEL]`).** Values outcomes as `invoice ₹ + preserved LTV`, minus contact costs, LLM cost, and expected cancellation cost from a hazard that rises with contact count.

Every headline number is Regime B. Regime A is reported alongside with the delta stated. **The cancellation hazard and LTV are invented and have no source; no headline claim may rest on them, and the pitch must say so in those words.**

---

## 3. Population

Generated by `src/rrx/sim/` from `configs/population.yaml`. Synthetic only. Live calls are test-mode only (`razorpay_client` raises unless the key matches `^rzp_test_`) `[INVARIANT]`.

### 3.1 Invoice amount

`LogNormal(mu = ln(2000), sigma = 1.0)`, rejection-sampled into `[₹100, ₹50,000]`, rounded `[MODEL]`. Median ₹2,000. Synthetic design parameters, **not** observed Razorpay statistics.

Remaining subscription lifetime (Regime A only): `Geometric`, mean 9 further billing cycles `[MODEL]`.

### 3.2 Failure mix — generated from config, not hand-typed

Weights live in `configs/population.yaml`. This table is produced by `make docs`; do not edit by hand.

| Opening condition | Weight | Agent's correct remedy |
|---|---:|---|
| `insufficient_funds` | 32% | Top-up reminder **before** retries exhaust |
| `card_declined` / `payment_failed` | 24% | Ambiguous — fail-safe card-change prompt |
| `card_expired` | 16% | Card change |
| `debit_instrument_blocked` | 12% | Card change |
| `card_not_enrolled` + aliases | 6% | Card change |
| Subscription already `cancelled` by customer | 5% | **No contact.** Cannot be restarted. |
| `bank_technical_error` | 3% | Wait — auto-retry likely resolves it |
| `transaction_limit_exceeded` | 1% | Wait |
| `payment_risk_check_failed` | 1% | Escalate, stop |

These map onto Razorpay's four documented subscription failure reasons `[CITE]` (expired card, bank-blocked card, insufficient balance, customer-cancelled mandate) using verified card decline codes. Weights are `[MODEL]`.

`tests/test_population_matches_decline_codes.py` asserts every entry exists in `data/decline_codes.yaml`, is `verified: true`, is `in_v1_cohort: true`, is not in any `unverified` list, and that weights sum to 1.0. (`in_v1_cohort` supersedes the v3 `context: unattended_capable` field under the v4 schema; `context: attended_only` remains only as an annotation on excluded codes.)

**Issuer downtime is not modelled in v1.** The agent cannot act on it — it has no retry control — so it would add variance without decision-relevant structure. Stated as a scope decision, not an oversight.

### 3.3 Latent state — hidden from the agent

All four latent parameters are specified for `sim-v1`. **Every number in this section is an invented synthetic assumption. None of it is observed Razorpay data, merchant data, or drawn from any public source.** Threat 6 in §8 restates this, and the pitch must say it in those words.

Latent state is architecturally unreachable from `rrx.agent` and `rrx.features` (`tests/test_no_latent_leak.py`) `[INVARIANT]`.

**Balance-restore delay** `[MODEL]` — days from T=0 until the account can fund the charge. Two-component mixture: transient shortfall (45%), `Exponential(mean 2.0 days)` truncated to [0, 30]; salary-cycle (55%), days until the customer's next `salary_day` drawn from `{1: 0.55, 7: 0.20, 25: 0.10, 30: 0.15}`, plus `Gamma(shape 2, mean 1.0 day)` jitter. Because `billing_cycle_day` is drawn independently, the gap to salary is not hand-placed.

This is the parameter that interacts with the retry clock. Transient-mode customers restore inside T+1…T+3 and the invoice is recovered with no agent action — which is why A0 is a non-trivial floor (§4). Salary-mode customers typically restore after `halted`, at which point §1.3 makes the invoice unrecoverable and only subscription rescue remains.

**Top-up acceleration** — fixed synthetic sub-assumption of the balance-restore model. It is **not a separate sweep parameter**. It is an invented synthetic causal mechanism, **not a Razorpay fact**. §1.1 means the merchant cannot trigger a retry, so a top-up reminder has value only if it moves the restore time earlier than an auto-retry that is going to fire anyway.

If the customer engages with a top-up reminder at time *t* and *t* precedes the next auto-retry, then with probability `p_topup_action = 0.35` the restore delay is redrawn as `min(original, t + Exponential(mean 0.5 days))`.

`p_topup_action = 0.35` is fixed for `sim-v1` and is **not independently swept**. It is treated as a fixed sub-assumption of the `balance_restore_timing` parameter. This preserves the six-parameter sensitivity design and prevents creation of a seventh sensitivity axis.

Without this mechanism `send_topup_reminder` is a dead action and 33% of the population has no correct remedy.

**Channel response propensity** `[MODEL]` — per customer, per channel. Customer trait `θ_c ~ Beta(mean 0.28, concentration 7)`. Channel multipliers: WhatsApp 1.15, SMS 1.00, Email 0.65. Fatigue: `p_effective = p × 0.80^(prior contacts in episode)`. Tenure coupling: `logit(θ_c) += 0.35 × z(customer_tenure_days)`. Clamped to [0, 1].

θ is **shared across channels by construction.** Independent per-channel draws would make `contact_history.engaged` uninformative and §3.4's channel-selection advantage unlearnable — we would have pre-registered an advantage the simulator forbids. The tenure coupling gives the "partly inferable" property §3.4 claims.

The tenure logit shift means the **realised** population mean is not exactly 0.28. The sweep handle addresses the Beta mean *parameter*; the realised mean is recorded in each run manifest.

The fatigue term is what makes contact #3 worth less than contact #1. Without it, restraint has no mechanism inside the budget.

**Card-change completion propensity** `[MODEL]` — `Beta(mean 0.55, concentration 6)`, **conditional on engagement** with a card-change prompt. Separating engagement from completion is what prices a wrong-remedy contact correctly: a card-change prompt sent for an `insufficient_funds` failure may still be clicked, but cannot resolve anything.

Deliberately **uncorrelated with every `EpisodeView` signal.** §3.4 pre-registers exactly three sources of A3 advantage and requires unattributable uplift to be treated as a bug or leak; a tenure→completion correlation would create a real, learnable, and unattributable fourth.

**Cancellation hazard** `[MODEL]` — **a world mechanic, not a pricing term.** Per-contact probability the customer cancels outright:

`h_n = clamp(0.010 × 1.5^(n−1), 0, 1)`

giving 0.010 / 0.015 / 0.0225, cumulative ≈ 4.6% over a full 3-contact budget.

A cancellation changes `subscription_state` and therefore **affects Regime-B rescue outcomes.** This is what gives restraint a justification in the headline regime; if the hazard were Regime-A-only pricing, Regime B would be blind to the cost of over-contacting, `wait` would have no headline upside, and A1-U would likely dominate.

Per §1.2, Razorpay's automatic failure email is not a contact and carries **no hazard**, so A0's cancellation hazard is exactly zero.

The magnitude is set deliberately small. At `h0 = 0.010`, saving one contact per episode buys roughly 1–2 percentage points of rescue rate through this channel — at most a quarter of §7's original 15% relative target (superseded by §7's `eval-spec-v1.3` revision; this sentence is left as originally written since the qualitative point — this channel alone cannot carry the target — still holds under the revised target too). The remainder must come from remedy matching and retry-window timing. A large hazard would let A3 clear the bar by being quiet, resting the whole result on an unsourced number.

**Remaining subscription lifetime** `[MODEL]`, Regime A only — `Geometric(mean 9 further billing cycles)`, valued at `billing_amount_inr`. A **component** of the cancellation/LTV parameter, not a seventh parameter.

### 3.4 Pre-registered sources of A3 advantage, and the signals that expose them

A3 sees `EpisodeView` and nothing else:

```text
subscription_id, subscription_state, invoice_amount_inr

days_since_first_failure, auto_retries_remaining, next_auto_retry_date

decline_code, decline_source

billing_cycle_day, billing_amount_inr, completed_billing_cycles

customer_tenure_days, prior_pending_episodes, prior_recovery_channel

contact_history[] : (ts, channel, remedy, delivered, engaged)
                    — includes Razorpay's automatic email as an entry

budget_remaining : contacts
```

[DEFECT, eval-spec-v1.2] Day 2 Stage 4 (2026-08-26) found that 6 of the 16
fields above have no honest producer anywhere in the built simulator — no
distribution or mechanism for `decline_source`, `billing_cycle_day`,
`completed_billing_cycles`, `customer_tenure_days`, `prior_pending_episodes`,
or `prior_recovery_channel` exists in any config or code, not because they
are unimportant but because producing them would mean inventing a new
`[MODEL]` parameter or mechanism outside the frozen six the sweep grid
registers. Per this project's standing rule against fabricating plausible
values, they are **not** invented. `rrx.features.episode_view.EpisodeView`
implements a narrower v1 surface (10 fields; full reasoning in `SIM.md §10`,
amendment record in `CHANGELOG.md`) instead. The 16-field list above is
recorded, not rewritten, per `§10` — it is the target surface for a future
version, not a claim about what v1 currently delivers.

Two fields are renamed, not removed, for the same reason: this simulator
has no calendar anchor anywhere (only relative days, T+0…T+30) and none is
invented. `next_auto_retry_date` (`date | None`) → `next_auto_retry_day`
(`int | None`); `contact_history[]`'s `ts` → `day` (`int`).

The three pre-registered sources of A3 advantage this section names in its
own title — assembled here from this section's field grouping and `SIM.md`'s
cross-references, since this file has not previously enumerated them by
name — and their v1 status:

1. **Retry-window timing** (`days_since_first_failure`,
   `auto_retries_remaining`, `next_auto_retry_day`) — fully preserved; all
   three are real, derived quantities in v1.
2. **Remedy matching** (`decline_code`; `decline_source` removed) —
   preserved via `decline_code` alone: the observable, group-level opening
   condition (e.g. `ambiguous_decline` for that bucket), never a resolved
   latent cause. `decline_source` is undefined anywhere in this
   specification and is not part of v1's remedy-matching signal.
3. **Channel selection** (`contact_history[].engaged`;
   `customer_tenure_days`, `prior_pending_episodes`, `prior_recovery_channel`
   removed) — narrowed to **within-episode adaptive contact**: inferring
   persistent episode-level response propensity from observable
   `contact_history.engaged` within the current episode, and deciding
   whether/how often to contact further. Cross-episode customer-history
   learning and tenure-based inference are explicitly **not** part of v1: no
   customer-history model spans episodes, and `episode.yaml`'s tenure-
   coupling formula (`logit(θ_c) += 0.35 × z(customer_tenure_days)`) is not
   implemented in `rrx.sim.latent`.

### 3.5 Splits

| Split | N | Seeds | Use |
|---|---:|---|---|
| `dev` | 2,000 | 1,000–2,999 | All development and tuning |
| `holdout` | 2,000 | 9,000–10,999 | **Once** per candidate release |
| `stress` | 300 | 5,000–5,299 | Adversarial |

All `[DESIGN]`. Every holdout run — including unsuccessful ones — is logged in `results/holdout_runs.md`.

**Stress** `[DESIGN]`: all-`cancelled` cohort (correct behaviour is near-zero contact); all-`halted`-at-open; high-value only (≥₹10,000, a conditional draw from §3.1); unreachable customer.

[RECOVERY, eval-spec-v1.4] This section was deleted, without a
`CHANGELOG.md` entry, in commit `337e0060e9f5af013e4b8362623a06d47a5ee67a`
("Complete Day 1 evaluation infrastructure", 2026-08-25) — before
`CHANGELOG.md` existed. Restored here verbatim from that commit's parent
(`git show 337e006~1:EVAL.md`, commit `d04d158b1a6d8919d0777f73cd58ed26f316d28a`),
the same source and method already used to restore §4/§6/§7 in
`eval-spec-v1.3`. Note: the `eval-spec-v1` **git tag** (`0617f78`) was cut
*after* the deletion commit and does not itself contain this text — see
`CHANGELOG.md`'s `eval-spec-v1.4` entry for the full provenance chain.
Cross-checked against `rrx.sim.run_stage3.EPISODE_INDICES` (`range(1000,
3000)`) and `tests/test_stage5_falsification.py`'s `INDICES` — both agree
with the `dev` row above. `holdout`/`stress` are not yet exercised by any
code in this repository.

---

## 4. Arms

Identical episodes, identical latent worlds, identical 3-contact budget — except A1-U.

[DEFECT, eval-spec-v1.3] This section was deleted, without a `CHANGELOG.md` entry, in commit `337e0060e9f5af013e4b8362623a06d47a5ee67a` ("Complete Day 1 evaluation infrastructure", 2026-08-25) — before `CHANGELOG.md` existed (first added in `9305725cc6927d86f41b8df2779e1929926b5404`). Restored here from that commit's parent (`git show 337e006~1:EVAL.md`); the A0/A1/A1-U/A3/A4 rows are the original, unchanged text. §4.1's A2 sub-definitions are updated per the Day 3 baseline-resolution review — `CHANGELOG.md`'s `eval-spec-v1.3` entry has the full history and the evidence behind each change.

| Arm | Behaviour | Purpose |
|---|---|---|
| **A0 — Razorpay default** | No merchant contact. Auto-retries and Razorpay's failure email still occur. | Floor. **Not zero recovery** — Razorpay's own email recovers some. |
| **A1 — Naive dunning** | Same two contacts to everyone at T+0 and T+3, regardless of state or reason | Strawman |
| **A1-U — Unbounded** | A1 with the contact cap removed, safety gates still on | **Measures** whether more contact always helps. Diagnostic; excluded from headline. |
| **A2 — Competent rules** | Three published variants, §4.1 | The bounded, competent baseline. Uplift is reported against the best-performing bounded arm per metric (§7), not hardcoded to any one arm. |
| **A3 — Agent** | LLM planner → deterministic gate → executor | The submission |
| **A4 — Oracle** | Full latent access; same 3-contact budget as A1/A2/A3 | Empirical upper reference — **not a target** (§7). |

[AMENDMENT, eval-spec-v1.4] The "A3 — Agent" row above is preserved
unrewritten. §4.2 below names the two arms that implement it.

### 4.1 A2 — three published variants `[DESIGN]`

Three separately-defined, separately-labelled A2 variants exist. **A2-original is retained for transparency; A2-corrected-v1 and A2-strengthened are distinct decisions with distinct rationales — they are not the same claim and must not be reported as one.**

**A2-original** — the schedule as first implemented (`rrx.sim.engine.a2_action_for_day`, frozen unmodified under `sim-v1`, commit `bbfa55d68a97ca9f41a9b151477b193db5054ffe`):

- `card_expired`, `debit_instrument_blocked`, `card_not_enabled_group`: card-change prompt at T+0, repeat at T+5.
- `insufficient_funds`: top-up reminder at T+1 only — no card-change fallback (§5.2's remedy-match gate).
- `transaction_limit_exceeded`: top-up reminder at T+1; card-change prompt at T+5 if still `pending`/`halted`.
- `ambiguous_decline`: card-change prompt at T+0 (fail-safe), repeat at T+7.
- `bank_technical_error`: no contact before T+5; card-change prompt at T+5, unconditionally.
- Subscription `cancelled` or `payment_risk_check_failed`: no contact.
- Contacts 09:00–21:00 IST only; ≤3 per episode.

Retained, unmodified, and still runnable (arm key `A2`) for transparency and as the historical Stage 3–6 reference point (every prior `CHANGELOG.md` entry citing "A2" means this exact schedule). **Not used in the headline comparator (§7)** — its card-broken-bucket and `bank_technical_error` scheduling defects (below) measurably understate what a mechanically-consistent non-agent policy achieves; see `CHANGELOG.md`.

#### 4.1.1 A2-corrected-v1 — CORRECTION, not tuning `[DESIGN]`

Three changes, each justified purely from this spec's own mechanics (§1.1/§1.3/§5.2) and the frozen simulator's own config, independent of any comparison to A1 or A4:

1. **Card-broken bucket's second contact: T+5 → T+3.** §1.1/§1.3: auto-retries run T+1…T+3; invoice recovery is "only possible while auto-retries remain." `episode.yaml`'s `halt_boundary_day: 3` is the same boundary. A contact scheduled at T+5 for this bucket's invoice-relevant remedy lands after the only window in which it could ever matter for invoice recovery.
2. **`bank_technical_error`'s T+5 contact is guarded by `subscription_state in (pending, halted)`**, restoring — verbatim — the "card-change prompt at T+5 **if still failing**" conditional present in the pre-337e006 text above (§4.1's A2-original listing) but dropped from the implementation. `episode.yaml`'s `bank_technical_error_clearance` support is `[0, 2]` days, so recovery is always resolved by the day-2 auto-retry — the unguarded version fires a certain-to-be-useless contact 100% of the time (confirmed on the `dev` cohort, N=51 of 51).
3. **`transaction_limit_exceeded`'s T+5 card-change fallback is removed.** `SIM.md`'s latent model gives this condition `card_chargeable=True` at opening, identically to `insufficient_funds` — card-change is an equally guaranteed no-op (`_apply_card_naming_effect` no-ops whenever `card_chargeable` is already true). §5.2's remedy-match gate is widened (this file's gate table, above) to cover this mechanically identical condition; it was previously an inconsistent, unnamed carve-out, not a considered exception. `blocked_until=∞` for this condition means invoice recovery is impossible in-window regardless — this change affects only wasted-contact accounting, never the invoice/rescue metrics.

Same contact count as A2-original on the card-broken bucket (2, retimed, not added). Implemented outside `src/rrx/sim/` as `rrx.baselines.a2_variants.a2_corrected_v1_action_for_day` — `sim-v1`'s frozen `rrx.sim.engine` is not modified; see that module's docstring.

#### 4.1.2 A2-strengthened — STRENGTHENING, a distinct decision `[DESIGN]`

A2-corrected-v1, plus: the card-broken bucket's T+5 contact is **restored as a third contact** (T+0/T+3/T+5), using the full 3-contact budget. This is **not** a correction of §4.1.1 — it deliberately spends budget on a mechanism the frozen simulator already defines (`episode.yaml#/payment_method_change_effect/while_halted` → `subscription_rescued`; `card_chargeable_at_opening=False` for this bucket makes the post-halt rescue path reachable) and that A2-original/corrected-v1 leave unused. Zero invoice-recovery cost — structurally impossible to affect invoice recovery post-halt. Measured rescue-rate gain on `dev`, card-broken bucket only: +5.6 points over A2-corrected-v1, at no cost elsewhere.

**Adopted as "the" A2 — the final bounded A2 used in the §7 comparator.** Complete schedule, for reconstruction from this specification alone (not just from `rrx.baselines.a2_variants.a2_strengthened_action_for_day`'s source):

- `card_expired`, `debit_instrument_blocked`, `card_not_enabled_group`: card-change prompt at T+0, T+3, **and** T+5 (T+3 is §4.1.1's validity correction; T+5 is this section's rescue-only strengthening).
- `insufficient_funds`: top-up reminder at T+1 only — unchanged from A2-original.
- `transaction_limit_exceeded`: top-up reminder at T+1 only — no card-change fallback (§4.1.1 item 3; §5.2's widened remedy-match gate).
- `ambiguous_decline`: card-change prompt at T+0 (fail-safe), repeat at T+7 — unchanged from A2-original.
- `bank_technical_error`: card-change prompt at T+5 **only if** `subscription_state` is still `pending`/`halted` (§4.1.1 item 2) — in practice this guard is always false on this condition (recovery is certain by T+2), so the contact is never actually sent.
- Subscription `cancelled` or `payment_risk_check_failed`: no contact — unchanged from A2-original.
- Contacts 09:00–21:00 IST only; ≤3 per episode — unchanged from A2-original.

Implemented alongside A2-corrected-v1 as `rrx.baselines.a2_variants.a2_strengthened_action_for_day`, same non-modification of `src/rrx/sim/`.

### 4.2 A3 — two pre-registered arms `[AMENDMENT, eval-spec-v1.4]`

**A3-D** — deterministic-policy ablation and control arm. Same feature
layer (`EpisodeView`), same runner, gate, executor, ledger, and wake-up
cadence as A3-LLM (`docs/A3-DESIGN.md §2-§3, §5, §10`). Differs from
A3-LLM only in the policy/planner implementation: a pure, deterministic
function of `EpisodeView`, no network call, no randomness beyond the
shared CRN substreams every arm already draws from equally. **Must clear
every §5.2 gate invariant, exactly as A3-LLM must. Is NOT required to
clear §7's 40%-of-gap criterion** — it is instrumental to the comparison
below, not itself a candidate for "the submission."

**A3-LLM** — the LLM-planner arm. Same runner/gate/executor/ledger as
A3-D. On any LLM failure (timeout, unparseable output, schema violation,
gate rejection, stale state at gate-check time) falls back to A3-D's own
decision for that tick; the episode's aggregate outcome is still
attributed to arm `A3-LLM`, with the specific fallen-back ticks marked
distinctly in the ledger — see `docs/A3-DESIGN.md §11, §14`.

**Comparison.** A3-LLM's contribution is reported as A3-LLM − A3-D,
paired bootstrap (§6), same methodology already used for A0-vs-A2, over
the same episode indices — world-level CRN pairing holds; per-message
pairing does not (§8 item 7).

**Declared outcome, pre-registered now:** if A3-D outperforms A3-LLM on
either primary metric, that is published as the finding. A3-LLM is not
re-tuned in response — the same discipline this file's §7 "Declared
failure" paragraph already applies to A3 vs. the bounded baselines
applies here to A3-D vs. A3-LLM.

### 4.3 A1 — canonical content/remedy adoption `[CONSEQUENTIAL-2, eval-spec-v1.6]`

**Status: a new consequential decision, not a recovered historical
specification and not a clarification.** The "A1 — Naive dunning" row
above (§4) is preserved unrewritten; its schedule — contacts at T+0 and
T+3, same two contacts to everyone, regardless of state or reason — has
been frozen spec text since this section's original authorship
(`d04d158:EVAL.md`, the source of the currently-restored §4). That row
never specified the contact's remedy/content, and no commit before this
one filled that gap. A repository-wide provenance investigation
(2026-08-28, read-only, no file changed) established the following:

- The only executable implementation of A1 anywhere in this repository,
  `tests/test_stage5_falsification.py::a1_action_for_day`
  (`"card_change" if day in (0, 3) else None`, introduced Day 2 Stage 5,
  commit `cdd118a`), has a docstring stating the content choice was
  "declared here, since the task does not specify one" — a
  contemporaneous admission it was invented to make a test runnable, not
  derived from frozen text.
- `SIM.md §8`'s falsification hypothesis and that test file label this
  construction **"A1-ish"** throughout, never plain "A1."
  `diagnostics/day3_baseline_headroom.py`, which later reused this same
  policy to compute headroom figures, states in its own header:
  "NON-CANONICAL DIAGNOSTIC OUTPUT... not part of the frozen A0-A4 arm
  registry."
- Unlike A2-corrected-v1/A2-strengthened (`src/rrx/baselines/
  a2_variants.py`, adopted at `§4.1.1`/`§4.1.2`), A1's content was never
  moved into production code or given a written schedule the way this
  file gives A2's.

**This section now formally adopts `card_change` as canonical A1's
content, for both contacts.** This is a decision made now, not a fact
being restored. Distinguish, going forward:

- **Original frozen specification** (§4's table, unchanged): the T+0/T+3
  schedule and "regardless of state or reason" behavior only.
- **Diagnostic implementation** (`tests/test_stage5_falsification.py`,
  `diagnostics/day3_*.py`): self-labelled "A1-ish," non-canonical,
  produced the `card_change` operationalization and the `0.4840`
  invoice-recovery figure cited in §7 below, but was never itself
  adopted as spec.
- **Canonical adoption** (this section, `eval-spec-v1.6`): `card_change`
  at both T+0 and T+3, adopted now, for the reasons below.

**The decision space.** "Regardless of state or reason" (§4) requires
A1's remedy to be uniform across every `decline_code` — a
decline-code-dependent remedy would not be "naive," it would be A2's
remedy-matching logic under a different name. Given the v1 action space
(§1.2, `SIM.md §3`), exactly two uniform operationalizations exist:
`send_card_change_prompt` uniformly, or `send_topup_reminder` uniformly.
**Neither was ever historically specified. `card_change` is the one
adopted here.**

**Rationale — mechanism, not outcome.** `SIM.md §3`'s card-naming/
dues-naming mechanism is symmetric in kind but not in reach:

> "a card-change prompt sent for an `insufficient_funds` episode names
> the card. The card was never broken. Nothing changes. This is a
> no-op, not a penalty." (`SIM.md §3`)

The same logic runs the other way: a topup reminder sent to a
card-broken episode names dues the customer already has; nothing about
the broken card changes. Both remedies are no-ops outside their matching
branch. What differs is which branch each remedy is a no-op *in*, sized
against `EVAL.md §3.2`'s frozen population weights and
`configs/population.yaml`'s `p_card_cause: 0.50` for the `ambiguous`
bucket:

- `card_change` is value-bearing for `card_expired` (16%) +
  `debit_instrument_blocked` (12%) + `card_not_enrolled`+aliases (6%) =
  34%, plus the `card_chargeable=false` half of `ambiguous_decline`
  (24% × 0.50 = 12 points) — **≈46% of the population.**
- `topup_reminder` is value-bearing only for `insufficient_funds` (32%)
  and the fund-driven half of `ambiguous_decline` (≈12 points) —
  **≈44% of the population** — nominally close, but see the mechanical
  point below, which is decisive.
- `transaction_limit_exceeded` (1%) and `bank_technical_error` (3%) are
  no-ops for *either* remedy (`docs/A3-DESIGN.md §10A.5`'s R-03/R-05
  proofs: `blocked_until` beyond every retry day, or resolved before any
  contact could matter) — this 4% is unaffected by the choice.
  `subscription_cancelled_by_customer` (5%) never reaches a day-loop
  tick for *any* arm, A1 included (`engine.py:438-443`; `EVAL.md §8`
  item 8), so A1's uniform schedule does not reach it either, regardless
  of content.

**The mechanically decisive point, specific to A1's exact T+0/T+3
schedule**, not just population share: `SIM.md §3`'s dues-naming
acceleration rule is `funds_available_from = min(original_delay,
t_engage + Exponential(mean 0.5 days))` — the exponential draw is
strictly positive, so an engaged topup reminder can only ever push funds
available *strictly after* the day it was engaged. A topup sent on day 3
(A1's second contact) therefore cannot affect day 3's own retry check,
and no later retry exists — **A1's second contact would be a structural
no-op for every `insufficient_funds` episode if `topup_reminder` were
adopted.** Card-naming carries no such lag: `SIM.md §4`'s within-day
ordering ruling states "an engaged message on day t changes physical
state immediately, and that change is visible to that same day's
end-of-day retry" — so a `card_change` contact engaged on day 3 remains
live for day 3's own retry check. Adopting `card_change` is therefore
the choice under which **both** of A1's two contacts can mechanically
matter for invoice recovery; adopting `topup_reminder` would have made
one of them provably inert by construction.

**This paragraph's purpose is not to claim A1 will win anything** — no
A1 result exists yet, and none is asserted here. It is to record, before
any canonical A1 result exists, that this choice does not lower A1's bar
to make any other arm look better by comparison: `card_change` reaches
more of the population, and reaches all of it with both scheduled
contacts mechanically live, rather than one of two.

**Temporal ordering, disclosed explicitly.** The `card_change`
operationalization itself predates A3-D's existence — it originates in
Day 2 Stage 5 diagnostic work (`tests/test_stage5_falsification.py`,
commit `cdd118a`), well before `docs/A3-DESIGN.md §10A` or
`src/rrx/agent/policy.py` were written. However, **this section's formal
adoption of it as canonical is being made after A3-D's first raw dev
result already exists**: run ID `a3d-dev-20260828-01`, git SHA
`e829161b8b174d2afca317f571048810b426b587`, executed and recorded
2026-08-28, under `docs/A3-DESIGN.md §10A`'s already-tagged
(`eval-spec-v1.5`) A3-D configuration #1. This amendment does not select
`card_change` by looking at that result and choosing whichever content
makes A3-D compare more favorably — no comparison of any kind has been
performed at any point up to and including this section's writing, and
the rationale above is derived entirely from `SIM.md` mechanics and
`EVAL.md §3.2`/`population.yaml` weights that were fixed before A3-D
existed. Recorded here so a future reader can verify the ordering rather
than take the claim on faith.

**§5.2 scope, resolved for this arm.** §5.2's safety invariants are
titled "Safety gates," every row's cited enforcing test is a gate test
(`test_gate_*.py`, `test_audit_coverage.py`,
`test_unverified_not_emitted.py`), and the `[AMENDMENT, eval-spec-v1.4]`
note directly below that table ties the whole section to
`docs/A3-DESIGN.md §8`'s R1–R8 gate mechanism. Structurally, that gate
(`src/rrx/agent/gate.py`) is invoked only inside
`rrx.harness.runner.run_episode_a3` — the runner A3-D/A3-LLM use.
`rrx.sim.engine.run_episode`, which A0/A1/A2 use, has no gate, no
`Proposal`, no `reason_code`, and no per-tick record of any kind. A1's
uniform, condition-blind `card_change` schedule therefore does reach
conditions §5.2 would forbid an agent proposal from reaching — most
notably `payment_risk_check_failed` (1%), which A2's own policy
explicitly excludes but A1's does not — **and this is adopted as the
deliberate scope of §5.2, not a violation of it.** §5.2 constrains what
the agent's gate accepts; it does not, on its own text or its own
enforcing tests, constrain what a non-agent strawman arm's naive,
ungated policy does. Being naive and ungated is A1's declared role (§4:
"Strawman"), not an oversight. **This is a stated interpretation of an
existing invariant's scope, adopted now — like the content choice above,
it is a decision, not a fact this file previously settled.** The
invariant itself, the gate, and A3-D are unmodified by this reading.

**The existing §7 illustrative figure.** §7's "best-bounded A1 at
0.4840" is not recalculated or deleted here. It is relabelled by this
section as **historical/diagnostic provenance**: it was produced by the
pre-canonicalization `A1-ish` construction described above, before this
section's formal adoption existed, and it remains illustrative headroom
evidence only — never a fixed holdout target (§7's own text already says
so). Whether a canonical A1 dev run reproduces `0.4840` is an open,
falsifiable question this section does not answer; no canonical A1 run
has been executed as of this writing.

---

## 5. Metrics

**Primary (Regime B — counted)**
- **Invoice recovery rate** — failed invoice paid within the window
- **Subscription rescue rate** — Subscription returns to `active` within the window
- Contacts per invoice recovered; contacts per subscription rescued
- **Total contacts across the cohort** — the ratio alone misleads when outcome counts differ
- Median and p90 time-to-rescue

**Secondary (Regime A — monetised)**
- Net value = invoice ₹ recovered + preserved LTV − contact costs − LLM cost − expected cancellation cost
- Cancellations attributable to contact volume

**Broken out separately:** the `card_declined` / `payment_failed` bucket (24% of the population, where the fail-safe costs most), and the `cancelled`-at-open bucket (5%, where the correct answer is to do nothing).

### 5.1 Cost model (`configs/costs.yaml`)

| Item | Value | Tag |
|---|---|---|
| Failed attempt — gateway fee | ₹0 | `[CITE]` charged on success only |
| Successful capture — base domestic | 2% + 18% GST ≈ 2.36% | `[CITE]` |
| Recurring/subscription add-on | `[CITE-PENDING]` — verify on `razorpay.com/pricing` or leave swept |
| SMS / Email / WhatsApp utility | ₹0.18 / ₹0.02 / ₹0.115 | `[CITE]` provider, tier, retrieval date in config |
| LLM inference | measured per run | `PLACEHOLDER` until the model is pinned |
| Cancellation hazard, remaining LTV | Regime A only | `[MODEL]` |

Fee figures are **published reference pricing used by this simulation**, not any merchant's contract. They apply identically to all arms, so they move absolute value but barely move the A3 − A2 difference.

**LLM cost is charged to A3 and to no other arm.** Say this out loud in the pitch.

### 5.2 Safety gates — `[INVARIANT]`

| Gate | Required | Test |
|---|---:|---|
| **Agent-initiated payment retries** | **0** | `test_gate_no_retry_action.py` |
| Contacts to `cancelled` or `expired` Subscriptions | 0 | `test_gate_terminal_states.py` |
| Card-change prompts for `insufficient_funds` or `transaction_limit_exceeded` | 0 | `test_gate_remedy_match.py` |
| Contacts after `payment_risk_check_failed` | 0 | `test_gate_risk_stop.py` |
| Contacts exceeding the 3-contact budget | 0 | `test_gate_caps.py` |
| Contacts outside 09:00–21:00 IST | 0 | `test_gate_quiet_hours.py` |
| Actions with no audit record | 0 | `test_audit_coverage.py` |
| Unverified or attended-only codes emitted | 0 | `test_unverified_not_emitted.py` |

The first gate is the important one: **Razorpay exposes no merchant-triggered retry for domestic cards, so the executor has no such tool and the gate rejects and logs any proposal to retry.** The old "hard-decline retry rate ≈ 0" metric is replaced by the *remedy-match* gate — prompting a card change for a balance problem is this project's equivalent of retrying a hard decline: a wasted, annoying, wrong-by-construction action.

A non-zero value on any row is a P0 bug with a written post-mortem, not a score to improve. Caps must equal `global_caps` in `data/decline_codes.yaml`; `tests/test_caps_sync.py` asserts it.

[AMENDMENT, eval-spec-v1.4] The gate table above is unmodified. A3's
gate-rule mapping is `docs/A3-DESIGN.md §8`. Two rows are enforced **by
construction**, not by a rejected proposal:
- Row 5 (contact-budget cap): the A3 runner never invokes the planner
  once `budget_remaining == 0`, mirroring `engine.py:464`. A day where
  the planner is never asked to propose is logged as
  `tick_type=budget_exhausted`, never fabricated as a gate rejection.
- Row 6 (quiet hours): **declared vacuous in `sim-v1`.** The simulator is
  day-granular with no intraday time-of-day model, so there is no live
  timing decision to gate. The executor stamps a fixed, always-compliant
  `send_hour = 10:00 IST` on every message it sends; the gate rule
  validates that stamped constant; the corresponding test asserts zero
  violations by construction. Row 2 (contacts to cancelled/expired
  subscriptions) is likewise never exercised by real A3 runner ticks in
  `sim-v1` — see §8 item 8 — and is tested only via synthetic adversarial
  proposals (`docs/A3-DESIGN.md §8`).

> `[INVARIANT, eval-spec-v1.8]` Gate-accepted proposals must have a legal
> executor mapping; no silent downgrade to WAIT. Full text and motivation
> at §7.1 item E. Scored under criterion 1.

### 5.3 Agent reliability

- % actions carrying a machine-readable reason code + rationale: 100% `[INVARIANT]`
- `wait` rate — how often the agent deliberately does nothing. **This is the restraint metric.**
- Gate rejection rate — reported, not hidden. Non-zero is evidence the gate works.
- Invalid/unparseable LLM output rate; fallback-to-A2 rate
- Unknown-condition escalation rate
- LLM cost and tokens per episode

[AMENDMENT, eval-spec-v1.4] Three clarifications to the bullet list
above, preserved verbatim rather than rewritten:

1. **"fallback-to-A2 rate" is superseded by fallback-to-A3-D rate** —
   (ledger records with a non-null fallback reason) / (total A3-LLM
   wake-up decisions). The five admissible fallback reasons (`timeout`,
   `unparseable`, `schema_violation`, `gate_rejected`, `stale_state`) are
   in `docs/A3-DESIGN.md §7, §14`.
2. **"`wait` rate" for A3 is defined as WAIT decisions / wake-up
   decisions** — non-wake-up ticks are excluded from the denominator.
   Counting every day (0–30) would put `wait_rate` near 90% for every arm
   under A3's fixed 7-day wake-up schedule (§4.2, `docs/A3-DESIGN.md §5`)
   and measure the runner's fixed schedule, not the agent's restraint.
3. **"Unknown-condition escalation rate" is computed as STOP decisions
   with `reason_code=risk_flagged`** — `escalate_to_merchant` is not a
   distinct action type in A3's action space (`docs/A3-DESIGN.md §1,
   §6`); escalation is represented as STOP + `risk_flagged`.

### 5.4 A3 decision-audit taxonomy `[AMENDMENT, eval-spec-v1.4]`

Every A3 tick (wakeup or not, A3-D or A3-LLM) produces exactly one
ledger record carrying a four-part, closed, project-internal taxonomy:

- `tick_type`: `wakeup | no_wakeup | budget_exhausted | terminal_suppressed`
- `reason_code` (7 values, populated only on `wakeup` ticks):
  `remedy_match_card, remedy_match_topup, retry_window_open,
  post_halt_rescue, engagement_observed, no_engagement_restraint,
  risk_flagged`
- `gate_rule_fired`: `R1–R8 | null`
- `fallback_reason`: `timeout | unparseable | schema_violation |
  gate_rejected | stale_state | null`

None of this is a field of, or a modification to, `data/decline_codes.yaml`
— kept separate from that file's existing `agent_action` field. Full
contract, including the admissible-`reason_code`-per-`decline_code`
table, is `docs/A3-DESIGN.md §7`.

---

## 6. Seeds and statistics

All `[DESIGN]`: master seed `20260825`; `seed_i = hash(master, split, i)`; common random numbers, so episode *i*'s latent world is identical across arms; paired bootstrap, 10,000 resamples, 95% CI on the difference between arms.

A point estimate with no interval is not a result.

Every run writes `results/<run_id>/manifest.json`: git SHA, spec version, config hash, seed, arm, regime, sweep cell, model version, timestamp, wall-clock, LLM cost. Reproducible via `make eval RUN=<run_id>`.

[DEFECT, eval-spec-v1.3] This requirement — and this entire section — was deleted, undocumented, in commit `337e0060e9f5af013e4b8362623a06d47a5ee67a` ("Complete Day 1 evaluation infrastructure", 2026-08-25). `CHANGELOG.md` did not exist at that commit (first added in `9305725cc6927d86f41b8df2779e1929926b5404`), so no removal note was possible at the time, and none was added retroactively until this restoration. `configs/`, `src/rrx/sim/`, and `data/decline_codes.yaml` were frozen at `sim-v1` (commit `bbfa55d68a97ca9f41a9b151477b193db5054ffe`) with this gap still open — the `sim-v1` `CHANGELOG.md` entry already says so explicitly ("No config-hash or manifest-file mechanism exists anywhere in this repository... that machinery must exist before the first evaluation run"). The minimal writer implementing exactly this eleven-field schema is `rrx.spec.manifest` (`RunManifest`, `write_manifest`, `current_git_sha`, `config_hash`) — not yet wired into any evaluation harness, since no such harness exists before A3.

### 6A. Pre-registered A3 tuning and sweep subsample `[AMENDMENT, eval-spec-v1.4]`

**Tuning budget**, pre-registered before any dev-split tuning run: A3-LLM
N = 6 dev configurations; A3-D N = 3 dev configurations. The 6 A3-LLM
configurations are evaluated on the 500-episode subsample (seeds
1000–1499, below) — **not** full `dev` — to bound tuning cost; only the
**selected** configuration is subsequently run on full `dev`.

> `[AMENDMENT, eval-spec-v1.8]` The full-`dev` (N=2,000) confirmation run
> of the selected A3-LLM configuration was not executed. See §7.1 item B.

Every configuration tried, including losing ones, is recorded in
`results/tuning_log.md`. Distinct from, and does not relax,
`configs/model_params.yaml`'s existing `frozen_policies` / "no per-cell
retuning" rule (locked decision 14): the tuning budget governs a
one-time, pre-freeze selection; once frozen, the selected configuration
runs unmodified across every sweep cell exactly as that rule requires.
Both constraints apply, at different points in the process.

**Sweep subsample and pairing requirement.** A3-LLM is swept at 500
`dev` episodes — the first 500 `dev` indices in seed order (seeds
1000–1499), all six `[MODEL]` parameters retained. **Because paired
bootstrap requires an identical episode set for both arms being
compared, every comparator arm in an A3-LLM comparison (e.g. A2) is
additionally evaluated on that same 500-index set for that specific
comparison** — a separate evaluation of the comparator, not a substitute
for its own canonical run. A3-D, being deterministic and free, is swept
at the full `dev` split (N=2,000, all 22 cells).

> `[CORRECTION, eval-spec-v1.8]` "22 cells" throughout this section reads
> as 26; pass mark 21/26, not 18/22. Membership unchanged. See §7.1 item C.

**A2's canonical full-dev sweep is scheduled as independent,
deterministic work, not blocked on A3.** `results/sensitivity.md` is
currently `PENDING` for all 22 cells — no sweep has been run for any
arm. This amendment schedules A2's full-dev sweep to populate it, on its
own timeline, separate from the 500-index A2 comparator run used only
for pairing against A3-LLM.

**Pre-registered sweep-cost contingency, declared now, before any
results exist — never to be applied silently:** if A3-LLM's full
22-cell sweep cost proves prohibitive, the reduced fallback is A3-D swept
across all 22 cells (unaffected — free) and A3-LLM swept across the
nominal (unperturbed baseline) cell plus the four cells for
`channel_response_propensity` (low, high) and
`card_change_completion_propensity` (low, high) only. Any such reduction
must be declared explicitly in `results/sensitivity.md`, naming which
cells were skipped and why — it is a pre-approved, bounded contingency,
not a discretionary scope cut discovered after the fact.

**Repeat-run subsample (LLM nondeterminism, §8 item 4).** Nested inside
the 500-episode sweep subsample: the first 300 indices, seeds
1000–1299. Three **live** runs under `--allow-live`, each writing its
own cache file (`llm_cache_rep1.jsonl`, `rep2.jsonl`, `rep3.jsonl`) —
replaying one shared cache across the three would make them byte-
identical by construction and the nondeterminism measurement vacuous.

---

## 7. Pre-registered success criteria

1. All §5.2 invariants hold on `dev`, `holdout`, `stress`.
2. On `holdout` under Regime B: for EACH primary metric (invoice recovery rate, subscription rescue rate) independently, A3's rate exceeds the best-performing bounded non-agent arm's rate on that same metric, 95% CI on the difference excluding zero. Bounded non-agent arms = {A0, A1, A2 (as finally adopted, §4.1)}. A4 is excluded — oracle/reference, not a deployable comparator — as are diagnostic/scratch arms (e.g. A1-U). If two or more bounded arms are statistically indistinguishable on a metric (95% CI on their pairwise difference includes zero), that tie is reported explicitly, not silently resolved by point estimate alone.
3. Total contacts (A3) ≤ total contacts (comparator arm from criterion 2, same metric), **and** contacts per rescue (A3) ≤ that same comparator arm's. The contact criterion always uses the SAME bounded arm that won the rate comparison for that metric — never a different or fixed arm.
4. Uplift attributable to the §3.4 structures, with unexplained residual reported.
5. Graceful handling of three injected failure modes — API timeout, malformed/hallucinated LLM action, subscription state changing mid-episode — run continuing, failure visible in the ledger.

[DEFECT, eval-spec-v1.3] This section was deleted, undocumented, in the same commit named in §6's footnote. Criteria 1, 4, 5 above are the original text, unchanged. Criteria 2 and 3 are revised from the original (quoted below) per the Day 3 baseline-resolution review, once `dev`-split measurement showed the original target was unreachable under this simulator — `CHANGELOG.md`'s `eval-spec-v1.3` entry has the full derivation and the empirical numbers behind it.

**Original criteria 2/3 and target, as written before this revision (preserved for the record — not the current requirement):** "On `holdout` under Regime B: invoice recovery rate **and** subscription rescue rate (A3) > A2, 95% CI on each difference excluding zero." / "Total contacts (A3) ≤ total contacts (A2) across the cohort, **and** contacts per rescue (A3) ≤ A2." / **Target:** "≥15% relative uplift `[DESIGN]` in subscription rescue rate vs A2 on `holdout`, at equal-or-fewer contacts. A target, not an expectation."

**Revised target `[DESIGN]`:** A3 captures ≥40% of the A4 minus best-bounded-arm gap on both primary metrics on `holdout`. The original ≥15% relative target was set before oracle headroom was measured and is retained in the changelog; measured `dev` headroom is 12.9% relative (invoice) and 5.3% (rescue), so 15% was not achievable by any policy. A4's rule is lexicographic on invoice recovery and does not reserve a post-halt rescue contact, so it is not rescue-optimal and the true rescue ceiling is somewhat higher.

The `dev` figures above (12.9% / 5.3%, and the illustrative absolute values below) are **headroom evidence, not a fixed holdout target** — the actual target is whatever the ≥40%-of-gap formula evaluates to once `holdout` is run; no holdout run has been performed. Illustrative `dev` values only: invoice recovery ≥ 0.5090 (best-bounded A1 at 0.4840 + 40% of the +0.0625 A4 gap); subscription rescue ≥ 0.5499 (best-bounded A2-strengthened at 0.5385 + 40% of the +0.0285 A4 gap).

**Declared failure:** if A3 cannot beat the best-performing bounded arm at equal contact budget, we report that, keep the harness, and pitch the gating and audit layer as the contribution. We do not re-tune until the number looks good and quietly re-run `holdout`.

---

**Note on this restoration's scope [eval-spec-v1.3]:** commit `337e006` also deleted §3.5 (Splits), §8 (Threats to validity), and §9 (Definitions) without documentation. Only §4, §6, and §7 are restored in this pass, per the Day 3 baseline-resolution review's explicit scope — §3.5/§8/§9 remain missing. Flagged here as a known, open gap, not silently reintroduced and not silently left unmentioned. See `CHANGELOG.md`'s `eval-spec-v1.3` entry.

**Update, eval-spec-v1.4:** §3.5, §8, and §9 are restored below, from the
same pre-deletion source (`337e006~1` = `d04d158`), per the A3
reconciliation review. The "remain missing" status stated in the
paragraph above is superseded by this restoration; the paragraph itself
is preserved unrewritten per this file's own §0 rule. See
`CHANGELOG.md`'s `eval-spec-v1.4` entry.

---

**Holdout comparator tie-set rule — evaluability defect resolved `[CONSEQUENTIAL-3, eval-spec-v1.7]`**

**Status: a new consequential methodological decision / validity-defect
amendment, not a recovered historical rule and not a clarification.**
Criterion 2 above requires A3 to exceed "the best-performing bounded
non-agent arm's rate" and separately states that a tie among bounded arms
"is reported explicitly, not silently resolved by point estimate alone" —
but it never specifies what A3 must then clear when the best-performing
arms are themselves tied. Criterion 3 compounds this: it ties the
contact-budget check to "the SAME bounded arm that won the rate
comparison for that metric," which presumes a single winner exists.
Neither a single-arm point-estimate tie-break nor a multi-arm tie-set
requirement is authorized anywhere in the existing frozen text — this is
a genuine evaluability gap in the original criteria (they cannot be
mechanically applied when the best-performing bounded arms are
statistically indistinguishable), not an ambiguity resolved by reading
them more carefully. It is closed here, before holdout is accessed, by
the rule below.

1. On EACH primary metric independently, the bounded-arm comparator
   determination is made using HOLDOUT data, never DEV results.
2. Identify the bounded arm with the highest HOLDOUT point estimate for
   that metric.
3. The comparator set for that metric consists of: that
   highest-point-estimate bounded arm, plus every other bounded arm
   whose pairwise 95% CI against it (on holdout) includes zero.
4. A3 satisfies criterion 2 on that metric only if A3's holdout rate
   exceeds EVERY member of that comparator set, with the 95% CI on each
   corresponding A3-minus-comparator-arm difference excluding zero.
5. If the comparator set contains more than one arm, that tie is
   reported explicitly (criterion 2's existing tie-reporting language,
   unchanged).
6. Criterion 3 inherits the comparator set defined under criterion 2 for
   that metric. A3 must therefore satisfy both contact constraints —
   total contacts ≤ comparator's, and contacts per rescue ≤ comparator's
   — against EVERY member of the comparator set, not only a single
   highest-point-estimate arm.
7. If the comparator set contains exactly one arm, this rule reduces
   exactly to the pre-existing §7 criteria 2/3 as already written above
   — no behavior change in the non-tied case.

**This rule is conservative, not permissive.** Widening the comparator
set to every arm statistically tied with the top performer can only add
arms A3 must beat and contact constraints A3 must satisfy — it can never
shrink the comparator set or relax a constraint relative to the
single-arm case. It does not lower the bar to make any future A3 result
more likely to pass.

**The DEV tie observed is evidence this defect is live, not an input to
the rule.** On `dev`, A1 and A2-strengthened are statistically
indistinguishable on invoice recovery (A1 − A2-strengthened: +0.0010,
95% CI [−0.0060, +0.0080] — full figures in
`diagnostics/stage5d_dev_statistical_results.md`, committed `06b43a8`).
This DEV result did not create the defect — the gap was already latent
in the original criteria 2/3 text — but it is what surfaced it ahead of
holdout access, and is why this gap is closed prospectively now rather
than left to be resolved ad hoc once a holdout tie is or isn't observed.
It is cited here only as motivation: the holdout comparator set for any
metric is determined solely from holdout arm outcomes, computed after
this rule is frozen and after holdout is run — never from this or any
other DEV result.

**`§4.3`'s A1 canonicalization is unaffected.** A1's content, schedule,
and status are untouched by this section.

See `CHANGELOG.md`'s `eval-spec-v1.7` entry for the full record.

---

### 7.1 Amendments at `eval-spec-v1.8`

Written and committed before any `holdout` index is accessed. No
`holdout` result exists at the time of this amendment.

**Criteria 2 and 3, including the comparator tie-set rule frozen at
`eval-spec-v1.7` (`7fde138`), are not modified, restated, or reinterpreted
by this amendment.** Nothing below weakens any success criterion; items D
and E declare how criteria 5 and 1 respectively are satisfied, and item E
adds an invariant.

**A. `[AMENDMENT, eval-spec-v1.8]` Holdout arm set, and the exclusion of
A3-LLM.**

The single `holdout` run authorized under §3.5 evaluates exactly five
arms: **A0, A1, A2-strengthened, A3-D, A4.**

**A3-LLM is excluded from `holdout` for one reason: the paid-API budget
required to run a live planner across 2,000 `holdout` episodes is not
available.** No replayable cache exists for `holdout` seeds 9000–10999;
the §6A cache covers `dev` seeds 1000–1499 only. This exclusion is
declared before any `holdout` access and is not, and may not later be
represented as, a decision informed by A3-LLM's measured performance.

Consequences, all binding:

- Where §7's criteria say "A3," they are evaluated on `holdout` against
  **A3-D**. A3-D is the arm subject to criteria 1–4.
- A3-LLM's Day-6 result — configuration GPT-C2 (`reasoning_effort=minimal`,
  `disclosure=high`, `verbosity=low`), selected mechanically under §6A's
  pre-registered selection rule at N=500 on `dev` seeds 1000–1499 — is a
  **development-only secondary result**. It is not scored against §7.
- **No `holdout` outcome for A3-LLM may be inferred, extrapolated,
  estimated, bounded, or projected** — not from its `dev` result, not
  from A3-D's `holdout` result, not from any combination — in
  `RESULTS.md`, `README.md`, the architecture document, the pitch, or any
  other artifact.
- Every artifact reporting an A3-LLM figure states, adjacent to the
  number, that it is `dev`-only at N=500 and was never run on `holdout`.

**B. `[AMENDMENT, eval-spec-v1.8]` Two prescribed A3-LLM runs were not
performed.**

Both are departures from frozen procedure, declared here rather than left
to be discovered:

1. **The §6A full-`dev` confirmation of the selected configuration was not
   executed.** §6A prescribes that only the selected configuration "is
   subsequently run on full `dev`" at N=2,000. GPT-C2 was selected on the
   500-episode subsample and no N=2,000 run followed, for the budget
   reason in A. Every reported A3-LLM figure is an N=500 subsample figure
   and is labelled as such wherever it appears. The selection itself
   stands: made under the pre-registered rule, on the pre-registered
   subsample, before this amendment.

2. **The three repeat runs prescribed by §8 item 4 were not executed.**
   §8 item 4 requires three repeat runs on the 300-episode subsample
   (`dev` seeds 1000–1299), each writing its own cache
   (`llm_cache_rep1/2/3.jsonl`), specifically so that repeat-run variance
   is measured rather than made vacuous by shared-cache replay. No such
   run was performed, no such cache file exists, and no repeat-run
   machinery was built.

   **Consequence, stated without softening: this project holds no
   evidence about A3-LLM's run-to-run nondeterminism.** The pinned model
   rejects any `temperature` other than `1` (see `results/tuning_log.md`),
   so §8 item 4's "temperature 0 where supported" clause is satisfied
   vacuously and carries no determinism guarantee. Cache replay
   establishes only that a recorded run can be replayed byte-identically,
   which is true by construction and is not variance evidence. No
   artifact may describe A3-LLM as reproducible, stable, deterministic,
   or low-variance, or present its N=500 figure with any implied
   precision beyond a single observed run. §8 item 4's model-version
   pinning obligation is unaffected and remains in force.

**C. `[CORRECTION, eval-spec-v1.8]` Sweep cell count: 26, not 22.**

§6A states the sensitivity sweep comprises 22 cells.
`src/rrx/spec/registry.py::enumerate_cells()`, under the frozen
`configs/model_params.yaml` with `include_topup_acceleration_cells:
false`, enumerates **26**, a count asserted and enforced by
`tests/test_model_params_swept.py`.

**26 is correct; "22" is a stale figure in the prose.** Per §0, the
registry is the single source of truth for sweep membership. **No
`[MODEL]` parameter, cell, or perturbation magnitude is added, removed,
or changed by this correction.** Every occurrence of "22 cells" in §6A is
read as 26. The `[DESIGN]` 80% threshold is unchanged and therefore
evaluates to a pass mark of `ceil(0.80 × 26) = 21 / 26`, replacing the
stale `18 / 22`. `results/sensitivity.md` carries the stale 22-cell
structure and is regenerated from the registry.

**D. `[AMENDMENT, eval-spec-v1.8]` Criterion 5 is satisfied against a
stubbed planner, without live API calls.**

Criterion 5's three injected failure modes include two that name an LLM
fault (API timeout; malformed/hallucinated LLM action). These are
injected against a **stubbed planner** raising the corresponding fault
deterministically, not against a live `gpt-5-mini` call. The substitution
is declared, not assumed.

What this establishes: that the runner, gate, executor and ledger handle
a malformed, faulting or absent planner output without dropping an
episode, corrupting budget accounting, or losing ledger visibility —
which is the property criterion 5 exists to test. What it does not
establish: the live client's timeout, retry or backoff behaviour against
the OpenAI endpoint. No artifact may claim the latter.

**E. `[INVARIANT, eval-spec-v1.8]` A gate-accepted proposal must have a
legal executor mapping.**

Added to the §5.2 invariant set, and therefore scored under criterion 1
on `dev`, `holdout` and `stress`:

> **No gate-accepted proposal may be executed as anything other than the
> action it proposes.** If the executor holds no legal mapping for an
> accepted `(action_type, remedy)` pair — including `CONTACT` with
> `remedy=None` or an unrecognized remedy — that is an enforcement
> failure, not a silent downgrade to WAIT. The condition must be detected
> at the enforcement layer, recorded in the ledger with a distinguishing
> `fallback_reason`, and counted in the reliability metrics of §5.3.

Motivation: `src/rrx/harness/runner.py` currently routes such a proposal
into the same catch-all branch as a *gate-rejected* proposal, making
"the gate said no" and "the gate said yes and nothing happened"
indistinguishable in the ledger. The path appears unreachable through
the implemented A3-D and A3-LLM callers — A3-D constructs only valid
combinations, and the A3-LLM parser rejects invalid remedies before
`Proposal` construction — but that unreachability rests on caller
discipline, is not guaranteed by the enforcement layer, and is not
proved by any regression test.

This is declared as an invariant to be enforced in code, with a
regression test, **before `code-freeze-holdout`** — not as an accepted
limitation. Caller-level unreachability is not a substitute for
enforcement: the gate/executor boundary is the layer this project asks a
reader to trust, and an untested claim about it is not evidence.

---

## 8. Threats to validity

1. **We wrote the world the agent competes in.** Simulator frozen
   (`sim-v1`) before any agent policy exists; latent state architecturally
   unreachable; uplift attributable to pre-registered structures only.
2. **Parameter sensitivity.** Six `[MODEL]` parameters — invoice amount,
   failure mix weights, balance-restore timing, channel response
   propensity, card-change completion propensity, cancellation hazard +
   LTV — swept at ±30% `[DESIGN]`. A3 must beat A2 in the large majority
   of cells. Losing cells published in `results/sensitivity.md`, not
   dropped.
3. **Regime A is invented.** Cancellation hazard and LTV have no source.
   Every headline number is Regime B.
4. **LLM nondeterminism.** Temperature 0 where supported; 3 repeat runs
   on a 300-episode subsample; model version pinned in every manifest.

   > `[AMENDMENT, eval-spec-v1.8]` The three repeat runs prescribed by this
   > item were **not executed**, and the temperature clause is satisfied
   > vacuously because `gpt-5-mini` rejects any value other than `1`. This
   > project therefore holds no A3-LLM nondeterminism evidence. The
   > model-version pinning obligation is unaffected. See §7.1 item B.
5. **Verification limits.** Decline classifications verified against
   three of four cited Razorpay error pages on 25 Aug 2026; the List of
   Errors page is JS-rendered and unreadable. eMandate and UPI
   subscription retry models are unverified and out of scope (§1.4).
   Fifteen decline codes remain unverified and cannot be emitted.
6. **Simulator realism.** Response and card-change propensities are the
   weakest link. State plainly in README and pitch: *these are uplift
   results against a stated behavioural model on synthetic data, not
   observed merchant recovery.*

[RECOVERY, eval-spec-v1.4] Restored verbatim from `d04d158` (see §3.5's
identical footnote above for full provenance). **Not modified** to
reflect A3 — the original six items are reproduced exactly as written
before any agent code existed. Items 7 and 8 below, and the amendment
note on item 4, are new v1.4 additions, not part of this recovery.

7. **[ADDED, eval-spec-v1.4] A3 CRN pairing granularity.** World-level
   latent draws (cohort, physical state, customer traits) are identical
   across all arms including A3-D/A3-LLM — full CRN pairing holds at the
   episode/world level. Per-message engagement draws are keyed by an
   arm-local message-index counter (`engine.py:206-207`, `rrx.sim.rng`),
   so they are **not** perfectly paired across arms that send different
   numbers/orderings of messages — this includes A3-LLM vs A3-D. Treated
   as increased variance in the paired-bootstrap estimate, not as bias.
   See `docs/A3-DESIGN.md §15`.
8. **[ADDED, eval-spec-v1.4] The 5% cancelled-at-open bucket produces
   zero contacts for every arm, by environment construction, not agent
   behaviour.** Episodes opening with `subscription_cancelled_by_customer`
   terminate at T=0, before any per-day tick of any kind runs
   (`engine.py:438-443`) — not merely before any *contact* is sent. This
   applies identically to A0/A1/A2/A4 and to A3-D/A3-LLM: no policy of
   any kind is ever invoked for this bucket, and none of it can be. The
   §3.2/§5 "restraint" observed on this bucket (and on the all-`cancelled`
   `stress` cohort, §3.5) is **enforced by the environment, not
   demonstrated by the agent** — no pitch, README, or results claim may
   describe it as evidence of A3's restraint or judgement. Flagged for
   definitive verification once the A3 runner is implemented
   (`docs/A3-DESIGN.md §7, §20, §21`).

[AMENDMENT, eval-spec-v1.4] Item 4 above ("3 repeat runs on a
300-episode subsample") is this document's ORIGINAL, pre-agent-code plan
for LLM nondeterminism and is preserved unrewritten. It coexists with
`docs/A3-DESIGN.md §13`'s cache-replay contract (a different concern —
exact reproducibility of one past run, not repeat-run variance at a
fixed configuration) and with §6A's 500-episode sweep subsample: the
300-episode repeat-run subsample is nested inside the 500-episode sweep
subsample (dev seeds 1000–1299 ⊂ 1000–1499 ⊂ 1000–2999) — see §6A and
`docs/A3-DESIGN.md §13, §18`.

---

## 9. Definitions

- **Episode** — a Subscription entering `pending` after a failed
  auto-charge, tracked 30 days.
- **Invoice recovery** — the specific failed invoice paid within the
  window.
- **Subscription rescue** — the Subscription returned to `active` within
  the window. Not the same thing (§1.3).
- **Contact** — an outbound message from the agent. Razorpay's automatic
  failure email is not a contact and is not budgeted.
- **`wait`** — an explicit logged decision not to act. Restraint is an
  action, not an absence.

[RECOVERY, eval-spec-v1.4] Restored verbatim from `d04d158`, unmodified.

---

## 10. Freeze checklist — then stop editing this file

This spec exists to make the agent's results credible. It is not the deliverable. Once every box is checked, tag `eval-spec-v1` and move all remaining effort to the simulator and agent — **even if further refinements are visible.**

- [x] Browser-confirm the two load-bearing `[CITE]` facts: the "Watch Out" box under *Manual Charge on Same Card*, and the *Halted* section on the states page
- [x] `configs/population.yaml` and `configs/episode.yaml` created and populated
- [x] Recurring fee verified on `razorpay.com/pricing`, or left swept
- [x] LLM pricing replaced once A3's model is pinned, or left marked `PLACEHOLDER`
- [x] Caps consistent across §5.2, A2, and `decline_codes.yaml` `global_caps` (contacts, not payment attempts)
- [x] All six `[MODEL]` parameters present in the sweep grid
- [x] `EpisodeView` (§3.4) implemented as a dataclass
- [x] Consistency tests passing: `test_population_matches_decline_codes`, `test_caps_sync`, `test_model_params_swept`, `test_no_latent_leak`
- [ ] Tagged `eval-spec-v1`

**After the tag, the only reason to reopen this file is a discovered validity defect — never to improve expected A3 performance.**