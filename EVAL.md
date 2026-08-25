# EVAL.md — Evaluation Specification

**Project:** Subscription recovery orchestration agent (Razorpay AI Buildathon, Track 03 — AI Revenue Recovery)
**Status:** Pre-registered. Written before any agent code. Freezes at `eval-spec-v1` — see §11.
**Rule:** Any change after the tag is a new tagged version with a changelog entry. Results always report the spec version they ran under.

---

## 0. Provenance tiers

| Tag | Meaning | Obligation |
|---|---|---|
| `[CITE]` | External fact | URL + retrieval date |
| `[INVARIANT]` | A constraint we impose, not a belief about the world | Enforcing test |
| `[DESIGN]` | Experimental choice with no bearing on validity | None |
| `[MODEL]` | World assumption that could change the conclusion | **Row in `results/sensitivity.md`** |

`tests/test_model_params_swept.py` fails the build if a `[MODEL]` parameter is missing from the sweep grid. **Six `[MODEL]` parameters** (§8.2).

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
| `send_topup_reminder` | For balance failures, only useful *before* auto-retries are exhausted |
| `send_subscription_link` | Clear dues on `pending` / `halted` |
| `hold_service_delivery` / `resume` | Merchant-side lever |
| `escalate_to_merchant` | Unknown or risk-flagged cases |
| `wait` | **An explicit, logged action.** Restraint must be a decision, not an absence of one. |
| `stop_episode` | Terminal |

Razorpay independently sends the customer a payment-failure email containing a card-change link `[CITE]`. That email is part of the world, not an arm's choice, and every arm — including A0 — operates on top of it. The agent's contacts are *additional* to it, which is why they carry annoyance cost.

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

The agent's only action is contact. Contacts cost ~₹0.02–₹0.18 `[CITE]` — negligible against the invoice. But contact is no longer the only thing at stake: **over-contacting risks the customer cancelling**, which forfeits not just the invoice but the Subscription's remaining lifetime value. That is a real mechanism, not an invented penalty, and it is why restraint matters here in a way it did not under a retry framing.

**Regime B — Equal contact budget (headline).** Every arm gets **3 contacts** per episode `[DESIGN]`, within 09:00–21:00 IST, not counting Razorpay's automatic email. Outcomes are **counted, not priced**: invoice recovery rate and subscription rescue rate. The claim is *"same contact budget, more invoices recovered and more subscriptions rescued"* — no invented monetary weighting anywhere in it.

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

`tests/test_population_matches_decline_codes.py` asserts every entry exists in `data/decline_codes.yaml`, is `verified: true`, is `context: unattended_capable`, is not in any `unverified` list, and that weights sum to 1.0.

**Issuer downtime is not modelled in v1.** The agent cannot act on it — it has no retry control — so it would add variance without decision-relevant structure. Stated as a scope decision, not an oversight.

### 3.3 Latent state — hidden from the agent

| Factor | Tag |
|---|---|
| Balance-restore delay (bimodal, salary-cycle cluster) | `[MODEL]` |
| Channel response propensity, per customer per channel | `[MODEL]` |
| Card-change completion propensity | `[MODEL]` |
| Cancellation hazard per contact (Regime A) | `[MODEL]` |

### 3.4 Pre-registered sources of A3 advantage, and the signals that expose them

A3 sees `EpisodeView` and nothing else:

```
subscription_id, subscription_state, invoice_amount_inr
days_since_first_failure, auto_retries_remaining, next_auto_retry_date
decline_code, decline_source
billing_cycle_day, billing_amount_inr, completed_billing_cycles
customer_tenure_days, prior_pending_episodes, prior_recovery_channel
contact_history[] : (ts, channel, remedy, delivered, engaged)
                    — includes Razorpay's automatic email as an entry
budget_remaining  : contacts
```

| Advantage | Signals | Latent field it must NOT see |
|---|---|---|
| **Retry-window timing** — a top-up reminder is worth far more before auto-retries exhaust than after; after `halted`, only a card change can work | `auto_retries_remaining`, `subscription_state`, `days_since_first_failure` | `balance_restore_delay` |
| **Remedy matching** — a card-change prompt for an `insufficient_funds` failure is a wasted contact, and vice versa | `decline_code`, `decline_source` | `card_change_completion_propensity` |
| **Channel selection** — response propensity varies and is partly inferable | `contact_history.engaged`, `prior_recovery_channel`, `customer_tenure_days` | `channel_response_propensity` |

`tests/test_no_latent_leak.py` enforces that `rrx.agent` and `rrx.features` cannot import `rrx.sim.latent` `[INVARIANT]`.

**If measured uplift cannot be attributed to one of these three, treat it as a bug or a leak, not a result.** `results/attribution.md` decomposes uplift and reports the unexplained residual.

### 3.5 Splits

| Split | N | Seeds | Use |
|---|---:|---|---|
| `dev` | 2,000 | 1,000–2,999 | All development and tuning |
| `holdout` | 2,000 | 9,000–10,999 | **Once** per candidate release |
| `stress` | 300 | 5,000–5,299 | Adversarial |

All `[DESIGN]`. Every holdout run — including unsuccessful ones — is logged in `results/holdout_runs.md`.

**Stress** `[DESIGN]`: all-`cancelled` cohort (correct behaviour is near-zero contact); all-`halted`-at-open; high-value only (≥₹10,000, a conditional draw from §3.1); unreachable customer.

---

## 4. Arms

Identical episodes, identical latent worlds, identical 3-contact budget — except A1-U.

| Arm | Behaviour | Purpose |
|---|---|---|
| **A0 — Razorpay default** | No merchant contact. Auto-retries and Razorpay's failure email still occur. | Floor. **Not zero recovery** — Razorpay's own email recovers some. |
| **A1 — Naive dunning** | Same two contacts to everyone at T+0 and T+3, regardless of state or reason | Strawman |
| **A1-U — Unbounded** | A1 with the contact cap removed, safety gates still on | **Measures** whether more contact always helps. Diagnostic; excluded from headline. |
| **A2 — Competent rules** | Below | **The real baseline. Uplift is reported against A2.** |
| **A3 — Agent** | LLM planner → deterministic gate → executor | The submission |
| **A4 — Oracle** | Full latent access; optimal single contact | Upper bound |

**A2 reference policy** `[DESIGN]`, frozen before A3 is tuned:

- `card_expired`, `debit_instrument_blocked`, `card_not_enrolled`: card-change prompt at T+0, repeat at T+5.
- `insufficient_funds`, `transaction_limit_exceeded`: top-up reminder at T+1; card-change prompt at T+5 if still `pending`/`halted`.
- `card_declined` / `payment_failed`: card-change prompt at T+0 (fail-safe), repeat at T+7.
- `bank_technical_error`: no contact before T+3; card-change prompt at T+5 if still failing.
- Subscription `cancelled` or `expired`: **no contact.**
- `payment_risk_check_failed`: escalate, no customer contact.
- Contacts 09:00–21:00 IST only; ≤3 per episode.

A0 is a genuinely non-trivial floor here, and A2 is a genuinely competent baseline. Beating A2 means something.

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

## 6. Seeds and statistics

All `[DESIGN]`: master seed `20260825`; `seed_i = hash(master, split, i)`; common random numbers, so episode *i*'s latent world is identical across arms; paired bootstrap, 10,000 resamples, 95% CI on the difference A3 − A2.

A point estimate with no interval is not a result.

Every run writes `results/<run_id>/manifest.json`: git SHA, spec version, config hash, seed, arm, regime, sweep cell, model version, timestamp, wall-clock, LLM cost. Reproducible via `make eval RUN=<run_id>`.

---

## 7. Pre-registered success criteria

1. All §5.2 invariants hold on `dev`, `holdout`, `stress`.
2. On `holdout` under Regime B: invoice recovery rate **and** subscription rescue rate (A3) > A2, 95% CI on each difference excluding zero.
3. Total contacts (A3) ≤ total contacts (A2) across the cohort, **and** contacts per rescue (A3) ≤ A2.
4. Uplift attributable to the §3.4 structures, with unexplained residual reported.
5. Graceful handling of three injected failure modes — API timeout, malformed/hallucinated LLM action, subscription state changing mid-episode — run continuing, failure visible in the ledger.

**Target:** ≥15% relative uplift `[DESIGN]` in subscription rescue rate vs A2 on `holdout`, at equal-or-fewer contacts. A target, not an expectation.

**Declared failure:** if A3 cannot beat A2 at equal contact budget, we report that, keep the harness, and pitch the gating and audit layer as the contribution. We do not re-tune until the number looks good and quietly re-run `holdout`.

---

## 8. Threats to validity

1. **We wrote the world the agent competes in.** Simulator frozen (`sim-v1`) before any agent policy exists; latent state architecturally unreachable; uplift attributable to pre-registered structures only.
2. **Parameter sensitivity.** Six `[MODEL]` parameters — invoice amount, failure mix weights, balance-restore timing, channel response propensity, card-change completion propensity, cancellation hazard + LTV — swept at ±30% `[DESIGN]`. A3 must beat A2 in the large majority of cells. Losing cells published in `results/sensitivity.md`, not dropped.
3. **Regime A is invented.** Cancellation hazard and LTV have no source. Every headline number is Regime B.
4. **LLM nondeterminism.** Temperature 0 where supported; 3 repeat runs on a 300-episode subsample; model version pinned in every manifest.
5. **Verification limits.** Decline classifications verified against three of four cited Razorpay error pages on 25 Aug 2026; the List of Errors page is JS-rendered and unreadable. eMandate and UPI subscription retry models are unverified and out of scope (§1.4). Fifteen decline codes remain unverified and cannot be emitted.
6. **Simulator realism.** Response and card-change propensities are the weakest link. State plainly in README and pitch: *these are uplift results against a stated behavioural model on synthetic data, not observed merchant recovery.*

---

## 9. Definitions

- **Episode** — a Subscription entering `pending` after a failed auto-charge, tracked 30 days.
- **Invoice recovery** — the specific failed invoice paid within the window.
- **Subscription rescue** — the Subscription returned to `active` within the window. Not the same thing (§1.3).
- **Contact** — an outbound message from the agent. Razorpay's automatic failure email is not a contact and is not budgeted.
- **`wait`** — an explicit logged decision not to act. Restraint is an action, not an absence.

---

## 10. Freeze checklist — then stop editing this file

This spec exists to make the agent's results credible. It is not the deliverable. Once every box is checked, tag `eval-spec-v1` and move all remaining effort to the simulator and agent — **even if further refinements are visible.**

- [ ] Browser-confirm the two load-bearing `[CITE]` facts: the "Watch Out" box under *Manual Charge on Same Card*, and the *Halted* section on the states page
- [ ] `configs/population.yaml` and `configs/episode.yaml` created and populated
- [ ] Recurring fee verified on `razorpay.com/pricing`, or left swept
- [ ] LLM pricing replaced once A3's model is pinned, or left marked `PLACEHOLDER`
- [ ] Caps consistent across §5.2, A2, and `decline_codes.yaml` `global_caps` (contacts, not payment attempts)
- [ ] All six `[MODEL]` parameters present in the sweep grid
- [ ] `EpisodeView` (§3.4) implemented as a dataclass
- [ ] Consistency tests passing: `test_population_matches_decline_codes`, `test_caps_sync`, `test_model_params_swept`, `test_no_latent_leak`
- [ ] Tagged `eval-spec-v1`

**After the tag, the only reason to reopen this file is a discovered validity defect — never to improve expected A3 performance.**
