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

The magnitude is set deliberately small. At `h0 = 0.010`, saving one contact per episode buys roughly 1–2 percentage points of rescue rate through this channel — at most a quarter of §7's 15% relative target. The remainder must come from remedy matching and retry-window timing. A large hazard would let A3 clear the bar by being quiet, resting the whole result on an unsourced number.

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
| Card-change prompts for `insufficient_funds` | 0 | `test_gate_remedy_match.py` |
| Contacts after `payment_risk_check_failed` | 0 | `test_gate_risk_stop.py` |
| Contacts exceeding the 3-contact budget | 0 | `test_gate_caps.py` |
| Contacts outside 09:00–21:00 IST | 0 | `test_gate_quiet_hours.py` |
| Actions with no audit record | 0 | `test_audit_coverage.py` |
| Unverified or attended-only codes emitted | 0 | `test_unverified_not_emitted.py` |

The first gate is the important one: **Razorpay exposes no merchant-triggered retry for domestic cards, so the executor has no such tool and the gate rejects and logs any proposal to retry.** The old "hard-decline retry rate ≈ 0" metric is replaced by the *remedy-match* gate — prompting a card change for a balance problem is this project's equivalent of retrying a hard decline: a wasted, annoying, wrong-by-construction action.

A non-zero value on any row is a P0 bug with a written post-mortem, not a score to improve. Caps must equal `global_caps` in `data/decline_codes.yaml`; `tests/test_caps_sync.py` asserts it.

### 5.3 Agent reliability

- % actions carrying a machine-readable reason code + rationale: 100% `[INVARIANT]`
- `wait` rate — how often the agent deliberately does nothing. **This is the restraint metric.**
- Gate rejection rate — reported, not hidden. Non-zero is evidence the gate works.
- Invalid/unparseable LLM output rate; fallback-to-A2 rate
- Unknown-condition escalation rate
- LLM cost and tokens per episode

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