# DAY5-CONTEXT-DUMP.md

Read-only inspection of `c:\razorpay-revenue-recovery`, produced per the
Day 5 context-dump instructions. No file other than this one was created
or modified. Git state is unchanged. Generated 2026-08-27.

---

## 1. REPOSITORY STATE

### Commands and verbatim output

```
$ git rev-parse --abbrev-ref HEAD
main

$ git rev-parse HEAD
447997a5aca47561b03f42fb9f4db9316a35973d

$ git status --porcelain=v1
?? CLAUDE.md

$ git log --oneline -20
447997a Task 4B: real gate (R1-R8) and ledger implementations
7238c6f Day 4 foundation: A3 runner skeleton + byte-identity parity proof
eb6b979 Propagate A3 -> A3-D/A3-LLM split into test_model_params_registry.py
641dcfa Add docs/A3-DESIGN.md: A3 runner/gate/executor/ledger design freeze
51a0054 Amend EVAL.md to v1.4: A3-D/A3-LLM, decision-audit taxonomy, tuning/sweep (authorized)
d480e5d Recover EVAL.md §3.5, §8, §9 (eval-spec-v1.4)
9c4ec0c Day 3 evaluation cleanup: eval-spec-v1.3
bbfa55d Day 2 Stage 6: sim-v1 simulator freeze (eval-spec-v1.2)
cdd118a Day 2 Stage 5: falsification tests
b048d95 Day 2 Stage 4/4B: honest EpisodeView boundary, eval-spec-v1.2
c5c3853 Complete Day 2 Stage 3 simulator
354b084 sim: Stage 2 sweep materialization and reachability
a9400ab sim: Stage 1 latent state sampling (SIM.md §1, §2)
9371230 Track the Razorpay test-mode guard (EVAL.md §3 [INVARIANT])
9305725 Freeze eval-spec-v1.1: SIM.md, send_subscription_link removal, two gap resolutions
0617f78 Freeze Day 1 evaluation specification
337e006 Complete Day 1 evaluation infrastructure
d04d158 Update evaluation for subscription recovery orchestration
176c6ef Add evaluation spec and payment decline taxonomy
821288e Set up project tooling and CI

$ git tag --list
eval-spec-v1
eval-spec-v1.1
eval-spec-v1.2
eval-spec-v1.3
eval-spec-v1.4
sim-v1

$ git tag --list --format='%(refname:short) %(objectname)'
eval-spec-v1 69945931c7ce75aca5d092a4948b87ad98c2ce9f
eval-spec-v1.1 5e440eeae038a27148187ad217c76f6e2362f7e5
eval-spec-v1.2 6f4a05d04cda9e2276654dd6c8da0897169b2f89
eval-spec-v1.3 8725099dbc167d89e683a5cb66b6ff2c121e64db
eval-spec-v1.4 af19f3b0e5fce77bdf7bd63f0deb427de5ae0a76
sim-v1 022abc9460b85462d254dd361eb92667f26174ac
```

These `objectname` values are the **tag objects'** SHAs (all six are
annotated tags), not the commits they point at. Resolved to commits
(`git rev-parse <tag>^{commit}`):

```
eval-spec-v1   -> 0617f78fa16c0434a5f89d5637c4ca48454c167f
eval-spec-v1.1 -> 9305725cc6927d86f41b8df2779e1929926b5404
eval-spec-v1.2 -> b048d9562c3a0d4c439ac53874e57a8f3f66101d
eval-spec-v1.3 -> 9c4ec0cb77dae69aaa7a366552d4c8f4c451692e
eval-spec-v1.4 -> eb6b9797fad52236cf089e47d9364f75b547b721
sim-v1         -> bbfa55d68a97ca9f41a9b151477b193db5054ffe
```

Note: `eval-spec-v1.4`'s tag commit (`eb6b979`) is **not** HEAD and is not
EVAL.md's own last-modifying commit (`51a0054`, older, see §2 below) — it
is a descendant commit that includes `51a0054`'s EVAL.md changes with no
further EVAL.md edits in between. HEAD (`447997a`) is two commits ahead
of the `eval-spec-v1.4` tag (`7238c6f`, `447997a` — the Day 4 runner/gate
work), i.e. Day 4 work is untagged.

```
$ git status --porcelain -- src/rrx/sim/
(empty)

$ git diff --stat HEAD -- src/rrx/sim/
(empty)
```

**Working tree is clean except one untracked file, `CLAUDE.md`** (the
project-instructions file itself — not part of the evaluation surface).
`src/rrx/sim/` has zero uncommitted changes and zero diff against HEAD.

### `src/rrx/sim/` file inventory

| File | Lines (PowerShell `Get-Content \| Measure-Object -Line`) | SHA256 |
|---|---:|---|
| `__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `cohort.py` | 95 | `bc7456bec3342e92ea24921f9044fb00b6c7e2b2768c0c6b8a9d12a1788edafa` |
| `engine.py` | 419 | `e08a134ab6ae939b28d816d99bd7ef7b6816a279abf36036806d532bdb153c5d` |
| `latent.py` | 267 | `e8a5dcc6e4e9bc78ecbb61c286f5d18db15ce8e64c10580ad8887e9124491eab` |
| `rng.py` | 31 | `f5e034465448b5eca1e6a7d9400fb199dd8d0b2bb6946e527e3c2928a142c837` |
| `run_stage3.py` | 134 | `375ae1449e591f6e07817cab3bc338e95e9e908890b04acb3f48999f782d7687` |

(`__pycache__/*.pyc` excluded — build artefacts, not source.)

**Discrepancy noted, not resolved:** `bash`'s `wc -l src/rrx/sim/engine.py`
reported **496** lines in the same working tree where PowerShell's
`Get-Content | Measure-Object -Line` reported **419**. Not investigated
further per the read-only mandate (no tool exists in this pass to
adjudicate whether this is a CRLF/final-newline counting artifact between
the two counting methods, or something else) — flagged here rather than
silently picking one number. The SHA256 hash above is the authoritative
identity check; both counting tools were pointed at the same file with no
edits in between.

### Frozen-hash manifest / hash-checking test search

Grep for `sha256|hashlib|FROZEN|sim-v1` across the repo (excluding
`.venv`) hit 21 files. Of these, exactly one performs a **live SHA256
file-hash check against `src/rrx/sim/*.py`**:

- `tests/test_a3_runner_parity.py` — `_hash_frozen_files()` hashes every
  `*.py` under `src/rrx/sim/` plus `src/rrx/features/episode_view.py`
  before and after the parity run and asserts equality (see §10 below;
  this is a **before/after-this-test-run** check, not a check against a
  pinned/recorded hash manifest committed anywhere).
- `src/rrx/spec/manifest.py` defines `config_hash()` (sha256 over config
  file bytes) as part of `RunManifest` — general-purpose, not a
  `sim/`-specific frozen-hash check, and not wired into anything yet (see
  §8).
- `tests/test_latent_snapshot.py` pins **sampled numeric values** (RNG
  output), not file hashes — see its full content, read in this pass,
  quoted in §7/§8 context below.

**No committed frozen-hash manifest for `src/rrx/sim/*.py` exists anywhere
in the repository** (no file recording the SHA256 values in the table
above for comparison across runs/sessions). MISSING — searched: repo-wide
grep for `sha256|hashlib|FROZEN|sim-v1`, plus `Glob` for `**/*manifest*`,
`**/*.lock`, `**/*HASHES*`.

**Does `src/rrx/sim/` match the frozen state? Answer: YES, by the only
evidence available this session** — `git status`/`git diff --stat` against
HEAD are both empty, and `tests/test_a3_runner_parity.py`'s own
hash-based before/after guard passed (this pass's one full `pytest -q`
run, §10, did not fail that test). There is no cross-session pinned-hash
artifact to compare against, so "matches `sim-v1`'s tagged state
specifically" is UNKNOWN by file hash — it can only be established via
`git diff sim-v1 -- src/rrx/sim/`, which was not run in this pass (out of
the batch's prescribed command list) but can be inferred safe: the tag
`sim-v1` sits at `bbfa55d`, and no commit between `bbfa55d` and HEAD
(`447997a`) touches `src/rrx/sim/` per every commit's stated scope in
`git log` above and the empty working-tree diff.

---

## 2. SIMULATOR INTEGRITY

Covered above in §1 (combined per the batch's own content — Batch 1 and
Batch 2 of the instructions both concern `src/rrx/sim/` integrity and are
reported together here since the underlying evidence is identical).
---

## 3. EVAL.md (VERBATIM)

**Path:** `EVAL.md` (at repository root, as given — no relocation needed).
**Line count:** 648.
**Declared version string:** none in a single "vX.Y" field; the file's
own `Status:` line says "Freezes at `eval-spec-v1` — see §10", and its
body carries a trail of `[AMENDMENT, eval-spec-v1.4]` / `[RECOVERY,
eval-spec-v1.4]` / `[DEFECT, eval-spec-vN]` tags whose highest value is
`eval-spec-v1.4`. Freeze checklist (§10) shows the `eval-spec-v1` tag
checkbox **unchecked** (`- [ ] Tagged eval-spec-v1`) even though the
git tag `eval-spec-v1` exists — the tag was cut at `0617f78` (Day 1),
before every amendment through v1.4 that the freeze checklist's own
surrounding boxes describe as done; this file's own checklist has not
been updated to reflect that the v1.4 content is not itself tagged.
**Git tag pointing at its last-modifying commit:** none exactly.
`git log -1 -- EVAL.md` = `51a0054cd39668de7ae928900277ede44e6bb8a6`
("Amend EVAL.md to v1.4..."); no tag points at `51a0054` directly. The
nearest tag is `eval-spec-v1.4` at `eb6b979` (2 commits later), which
contains `51a0054`'s EVAL.md content unmodified since.

### Table of contents (heading → line number)

```
1:# EVAL.md — Evaluation Specification
11:## 0. Provenance tiers
26:## 1. What we are measuring
28:### 1.1 The constraint that defines this project `[CITE]`
34:### 1.2 What the agent actually decides
56:### 1.3 Two things are recoverable, and they are not the same
65:### 1.4 Scope
73:## 2. Cost and value model
87:## 3. Population
91:### 3.1 Invoice amount
97:### 3.2 Failure mix — generated from config, not hand-typed
119:### 3.3 Latent state — hidden from the agent
163:### 3.4 Pre-registered sources of A3 advantage, and the signals that expose them
227:### 3.5 Splits
255:## 4. Arms
273:### 4.1 A2 — three published variants `[DESIGN]`
289:#### 4.1.1 A2-corrected-v1 — CORRECTION, not tuning `[DESIGN]`
299:#### 4.1.2 A2-strengthened — STRENGTHENING, a distinct decision `[DESIGN]`
315:### 4.2 A3 — two pre-registered arms `[AMENDMENT, eval-spec-v1.4]`
347:## 5. Metrics
362:### 5.1 Cost model (`configs/costs.yaml`)
377:### 5.2 Safety gates — `[INVARIANT]`
411:### 5.3 Agent reliability
438:### 5.4 A3 decision-audit taxonomy `[AMENDMENT, eval-spec-v1.4]`
459:## 6. Seeds and statistics
469:### 6A. Pre-registered A3 tuning and sweep subsample `[AMENDMENT, eval-spec-v1.4]`
521:## 7. Pre-registered success criteria
552:## 8. Threats to validity
618:## 9. Definitions
635:## 10. Freeze checklist — then stop editing this file
```

### Complete verbatim contents

```markdown
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
**selected** configuration is subsequently run on full `dev`. Every
configuration tried, including losing ones, is recorded in
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
```
---

## 4. SIM.md (VERBATIM)

**Path:** `SIM.md` (repository root).
**Line count:** 498.
**Declared version string:** `Status: Day 2, Stage 0. Freezes at sim-v1 — see §0.` plus an inline "Update, eval-spec-v1.1 (2026-08-26)" note near the top. No standalone "vX.Y" self-label beyond `sim-v1`.
**Git tag pointing at its last-modifying commit:** **YES, exact match.**
`git log -1 -- SIM.md` = `b048d9562c3a0d4c439ac53874e57a8f3f66101d`, which
is exactly the commit the `eval-spec-v1.2` tag resolves to.

### Table of contents (heading → line number)

```
1:# SIM.md — Simulator World Specification
9:## §0. Purpose and relationship to EVAL.md
33:## §1. Hidden physical state
53:## §2. Decline code → physical state at T=0
99:## §3. Actions → physical state, via message CONTENT, never via correctness
180:## §4. The clock
226:## §5. Outcome resolution
265:## §6. Parameter table
278:### Tier 1 — fixed by the frozen configs
297:### Tier 2 — no external source; value and selection rule
304:### Tier 3 — the six [MODEL] families
334:## §7. Tier boundary
374:## §8. Falsification tests this simulator must pass
392:## §9. Known limitations
417:## §10. EpisodeView boundary — v1 narrowing (Day 2 Stage 4B, 2026-08-26)
453:### Channel-selection advantage, narrowed
474:### Tenure coupling — not implemented in v1
```

### Complete verbatim contents

```markdown
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

**Discovered semantic clarification (2026-08-26):** for `transaction_limit_exceeded`
and `payment_risk_check_failed`, "never" means `blocked_until` is set beyond
every auto-retry day (T+1…T+3), so `§4`'s `t >= blocked_until` gate can never
be satisfied for these two conditions within the episode.

**Model ruling (2026-08-26, Day 2 Stage 3 closing): meaning of "never" for
every other row.** For every row covered by the "unless stated otherwise"
default ABOVE, EXCEPT `transaction_limit_exceeded` and
`payment_risk_check_failed`, `blocked_until = never` means **non-blocking**
(`0.0`) - `§4`'s `t >= blocked_until` term is trivially satisfied, because
these rows have no transient issuer/risk block to begin with; `blocked_
until` is simply not their bottleneck. Discovered as a defect during Day 2
Stage 3 implementation: an unconditional `BLOCKED_INDEFINITELY` default in
`rrx.sim.latent.draw_latent_state` silently made `§4`'s AND-gate
unsatisfiable for `insufficient_funds`, `ambiguous_decline`, and every
card-broken row - 91% of the population - regardless of `card_chargeable`/
`funds_available_from`, contradicting this document's own §3 statement that
transient-mode `insufficient_funds` customers recover "with no agent
action." Fixed in `latent.py`; `blocked_until` now defaults to `0.0`, with
`transaction_limit_exceeded`/`payment_risk_check_failed` set to
`BLOCKED_INDEFINITELY` explicitly, matching the clarification directly
above.

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

**Model ruling (2026-08-26, Day 2 Stage 3 closing): within-day ordering.**
This document did not previously state whether a message sent and engaged
with on day t changes physical state in time for day t's OWN retry check,
or only day t+1's. Resolved: an engaged message on day t changes physical
state immediately, and that change is visible to that same day's end-of-day
retry - not only to the next day's. Engagement is continuous-time (§3's
`t_engage`); the retry schedule above is day-granular. Fatigue and
contact-budget accounting are unaffected by this ordering. Implemented in
`rrx.sim.engine._send_message`/`run_episode`: any contact/email scheduled
for day t is resolved and its effects applied before that day's retry check
runs.

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

**Model ruling (2026-08-26, Day 2 Stage 3 closing): post-halt card rescue,
narrower form.** This document did not previously state what mechanism
transitions a `halted` subscription to `active`, or when. Resolved, with a
restriction narrower than this project initially ran with (see the Stage 3
closing report for the discovered implementation mismatch this corrects):
only episodes whose `card_chargeable` was `false` at opening (§2) may be
rescued post-halt when `card_chargeable` becomes `true`. Episodes already
`card_chargeable = true` at opening - `insufficient_funds`,
`transaction_limit_exceeded`, and `payment_risk_check_failed` - do **not**
transition to `active` merely because `card_chargeable` is (still) `true`
after halt; nothing in this simulator rescues their subscription post-halt.
This restriction is a model clarification, not forced by any single
existing sentence in this document or in `episode.yaml`: the only direct
evidence is `episode.yaml#/payment_method_change_effect/while_halted`
naming `subscription_rescued` as a reachable outcome (with
`manual_charge_required: true` / `manual_charge_available_domestic_card:
false` - the failed invoice itself is never recoverable post-halt), which
says nothing about which conditions are eligible or what event triggers it.
The at-opening restriction is added here to give "rescue" a coherent
meaning (a card that was genuinely broken getting fixed) rather than
crediting a message with fixing something that was never broken.
Implemented in `rrx.sim.engine._EpisodeState.card_chargeable_at_opening`
and the corresponding check in `_send_message`.

- **Regime A cancellation hazard** lives in a separate resolver that is never
  invoked under Regime B. **Not implemented as of Day 2 Stage 3** - no
  cancellation-hazard mechanism exists in `rrx.sim.engine` yet; this
  section describes a future resolver, not current runtime behavior.

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

---

## §10. EpisodeView boundary — v1 narrowing (Day 2 Stage 4B, 2026-08-26)

`EVAL.md §3.4` lists 16 fields as the complete agent-facing surface.
`rrx.features.episode_view.EpisodeView` (Day 2 Stage 4B) implements a
**deliberately narrower 10-field v1 boundary**, recorded here per this
document's own §0 rule ("Any conflict discovered between this document and
`EVAL.md` is a defect to be logged and reported, never resolved by editing
`EVAL.md`") rather than by silently editing `EVAL.md §3.4`. Six fields are
removed because no honest producer exists for them in this repository, not
because they are unimportant:

- **`decline_source`** — undefined anywhere in `EVAL.md`, this document, or
  any config (verified by repository-wide search, Day 2 Stage 4 gap
  analysis). Removed rather than fabricated. **v1 makes the remedy-matching
  decision using `decline_code` alone.**
- **`billing_cycle_day`, `completed_billing_cycles`** — no distribution or
  producer exists anywhere in the repository for either (only an ad hoc
  `Generator(999_999)` inside one *test*, never a real simulator producer,
  for `billing_cycle_day`). Inventing a distribution for either was
  explicitly ruled out. Removed/deferred, not fabricated.
- **`customer_tenure_days`, `prior_pending_episodes`,
  `prior_recovery_channel`** — see the channel-selection narrowing below.

Two fields are renamed, not removed, per a **[DESIGN] schema ruling**: this
simulator has no calendar anchor anywhere and none is invented to support
them. `next_auto_retry_date: date | None` → `next_auto_retry_day: int | None`;
`ContactRecord.ts: datetime` → `ContactRecord.day: int`. Both remain
relative-day integers (T+0…T+30), consistent with every other time
quantity in this document.

`billing_amount_inr` is **retained**, aliased to `invoice_amount_inr`: no
separate recurring-price figure exists anywhere in the repository —
`invoice_amount_inr` is the only price this simulator ever defines, and
`model_params.yaml`'s `valued_at: billing_amount_inr` never distinguishes
the two.

### Channel-selection advantage, narrowed

`EVAL.md §3.4`'s third pre-registered advantage (channel selection) is
narrowed for v1, per this section's "Interpretation note" above (channel
*ranking* was already established as not the inferable signal), one step
further: **v1 does not build a cross-episode customer-history model.**
`customer_tenure_days`, `prior_pending_episodes`, and
`prior_recovery_channel` are removed from `EpisodeView` entirely. The v1
channel-selection advantage is narrowed to:

> within-episode adaptive contact: infer persistent episode-level response
> propensity from observable `contact_history.engaged` and decide
> whether/how often to contact.

This remains a genuine, real signal in v1: `channel_response_trait` (θ_c)
is drawn once per episode and reused for every message sent in that
episode (§3), so engagement observed on an earlier contact genuinely
correlates with engagement on a later one within the same episode. What is
explicitly **not** claimed for v1: cross-episode relationship learning, or
tenure-based inference of any kind.

### Tenure coupling — not implemented in v1

`EVAL.md §3.3`'s tenure-coupling formula (`logit(θ_c) += 0.35 ×
z(customer_tenure_days)`) is **not implemented anywhere in `rrx.sim.latent`**
— `_sample_channel_response_trait` draws only the raw `Beta(mean,
concentration)` value. This was true before Stage 4B and remains true after
it: Stage 4B does not add a seventh population/model parameter, does not
modify `latent.py`, does not modify `_sample_channel_response_trait`, and
does not invent a tenure distribution.

**§8 falsification test #5, narrowed definition (recorded, NOT implemented
or run in Stage 4B):** as originally written, test #5 requires both
`concentration` → very large AND `tenure_coupling.beta = 0` to collapse the
responsiveness-inference advantage to zero — but `tenure_coupling` already
never runs regardless of its configured value, so the `beta = 0` half of
that manipulation currently has no discriminating power (see the Day 2
Stage 4 gap analysis). The test is narrowed to match the mechanism that
actually exists in v1:

> force `channel_response_propensity.customer_trait` concentration to a
> very large value, collapsing cross-customer variance in persistent
> episode-level response propensity; verify that the within-episode
> adaptive-contact advantage (above) collapses toward noise.

This narrowed test is not run in Stage 4B and remains a Stage 5 item.
```
---

## 5. A3-DESIGN.md (VERBATIM)

**Path:** `docs/A3-DESIGN.md`.
**Line count:** 590.
**Declared version string:** `Status: Design freeze (eval-spec-v1.4), final pass — all open questions from the prior pass resolved (§21).`
**Git tag pointing at its last-modifying commit:** none. `git log -1 --
docs/A3-DESIGN.md` = `641dcfa645849ec25271931b3388de0904e457dd`, which no
tag resolves to directly. The nearest descendant tag is `eval-spec-v1.4`
at `eb6b979` (one commit later), which contains this file unmodified
since `641dcfa`.

### Table of contents (heading → line number)

```
1:# A3 Design — EpisodeView-Aware Runner, Gate, Executor, Ledger
10:## 1. Purpose and decision problem
43:## 2. Integration boundary
96:## 3. A3 runner day-loop contract
121:## 4. EpisodeView / feature allowlist
148:## 5. Wake-up events — FROZEN
187:## 6. Action / proposal contract
216:## 7. Decision-audit taxonomy (four fields)
264:## 8. Safety gate
291:## 9. Executor
313:## 10. A3-D deterministic ablation
335:## 11. A3-LLM planner
355:## 12. Prompt / latent-leak invariant
375:## 13. LLM cache / reproducibility
398:## 14. Audit ledger
429:## 15. Determinism / CRN contract
440:## 16. Byte-identity / mechanics-parity requirements
452:## 17. Evaluation requirements (carried forward)
465:## 18. Pre-registered tuning and sweep
498:## 19. Failure injection
511:## 20. Advantage sources / limitations
551:## 21. Open questions / deferred decisions
571:## 22. Artifact policy
```

### Complete verbatim contents

```markdown
# A3 Design — EpisodeView-Aware Runner, Gate, Executor, Ledger

**Status:** Design freeze (eval-spec-v1.4), final pass — all open
questions from the prior pass resolved (§21). Specification only — no
implementation exists yet. Companion to `EVAL.md §4.2, §5.2-§5.4, §6A, §8
items 7-8` and `SIM.md`. `src/rrx/sim/` is unmodified.

---

## 1. Purpose and decision problem

**State (simulator-owned, hidden):** `card_chargeable`, `funds_available_from`,
`mandate_alive`, `blocked_until` (`SIM.md §1`) — never observed by A3.

**Observation (agent-owned):** `EpisodeView` as of the current day, before
the current day's decision — §4.

**Action set (v1):** `CONTACT` (remedy: `card_change` or `topup_reminder`),
`WAIT`, `STOP`. `escalate_to_merchant` is **not** a distinct action type
— represented as `STOP` with `reason_code=risk_flagged` (§6, §7).
`hold_service_delivery` and `send_subscription_link` remain excluded from
v1 entirely (`SIM.md §3/§9`); A3 must never propose them.

**Horizon:** 30-day episode window (`EVAL.md §1.4`), day-granular.

**Contact budget:** 3 contacts/episode, 09:00–21:00 IST — the same
budget every arm gets (`EVAL.md §2`). See §8 (R6) for how quiet hours is
handled given the simulator's day granularity.

**Objective:** maximize Regime-B outcomes under the shared budget
(`EVAL.md §7`); Regime A reported alongside, not optimized for.

**What the agent controls:** whether to contact (only at runner-determined
wake-ups, §5), which remedy, and when to stop spending its budget.
Channel is **not** agent-controlled in v1 (§6, §20).

**What remains simulator-owned:** the Razorpay auto-retry clock, halt-
after-exhaustion, the automatic email, all outcome resolution
(`SIM.md §2-§5`).

---

## 2. Integration boundary

```
existing arms (A0, A1, A2-original, A2-corrected, A2-strengthened, A4):
    run_episode() / _POLICIES        [src/rrx/sim/engine.py — UNCHANGED]

A3 (A3-D, A3-LLM):
    a separate, EpisodeView-aware runner, entirely under
    src/rrx/agent/:
        src/rrx/agent/runner.py    — the day-loop driver (§3)
        src/rrx/agent/policy.py    — A3-D (§10)
        src/rrx/agent/planner.py   — A3-LLM (§11)
        src/rrx/agent/prompt.py    — prompt builder (§12)
        src/rrx/agent/gate.py      — the safety gate (§8)
        src/rrx/agent/ledger.py    — the audit ledger (§14)
```

**Module placement — gate and ledger inside the guarded package.** All
six modules above, including the gate and ledger, live under
`src/rrx/agent/`. This is a placement decision, not a test change:
`test_no_latent_leak.py`'s `GUARDED_PACKAGES = ("rrx/agent", "rrx/features")`
already covers everything under `rrx/agent` — Layers 1 (AST import scan)
and 2 (runtime transitive-import check) apply to the gate and ledger the
moment they exist here, with **zero modification to `test_no_latent_leak.py`**,
which remains a locked file this design does not touch.
`test_no_latent_leak.py:146-152`'s `test_agent_package_guard_status`
currently *skips* ("`rrx/agent` not built yet") precisely so this
coverage activates the moment the directory is populated. The gate and
ledger have no structural need to import `rrx.sim.latent` — placement
inside the guard is a belt-and-suspenders closure of the coverage gap the
prior design pass identified, achieved by *where the files live*, not by
amending an already-locked enforcing test. (Resolves the prior pass's
§21 item 1; no open question remains on this point.)

**Why `capture_view_at_day` cannot serve as a live observation channel**
(Task 3A.1/3A.2, unchanged): fires after the policy call, once per run.

**Why a separate runner is necessary** (unchanged): `_EpisodeState`/
`CohortEpisode` are private to `run_episode()`'s stack frame.

**A4 precedent**, documented without overclaiming identity (unchanged):
A4's test-local loop (`test_stage5_falsification.py:14-20, 27-38`)
establishes the pattern; A3 follows it but, unlike A4, must never read
full `LatentState`.

**Guarantees**, unchanged: `src/rrx/sim/` byte-identical; existing arms
untouched; A3 reuses `_EpisodeState`, `_send_message`, `_retry_succeeds`,
`build_episode_view`, `AGENT_CHANNEL`, `sample_cohort_episode`,
`draw_latent_state` unmodified; A3 must reproduce day-loop mechanics
faithfully (§16 proves it does).

---

## 3. A3 runner day-loop contract

Per day `D`:

1. **Automatic events preceding the decision.** `D==0`: Razorpay's auto
   email fires — identical to `engine.py:458-462`.
2. **EpisodeView construction.** `view = build_episode_view(cohort, state,
   D, episode_cfg, split, i)` — unmodified, called after step 1, before
   step 4 (verified correct, Task 3A.2 Q7-Q8).
3. **Wake-up determination** (§5). Not a wake-up day, or
   `subscription_state` terminal, or `budget_remaining == 0`: record the
   appropriate `tick_type` (§7/§14) and skip to step 8. No planner call.
4. **Policy invocation** — only on a real wakeup tick. A3-D or A3-LLM
   receives `view`, returns a **Proposal** (§6).
5. **Gate** (§8). Accept, or reject + rule fired.
6. **Executor** (§9). Accepted: mapped to `_send_message()`, channel
   always `AGENT_CHANNEL` (§6), `send_hour=10:00` stamped for R6 (§8).
   Rejected / WAIT / STOP: no state mutation.
7. **Retry check** — identical to `engine.py:479-482`, runs after step 6
   (`SIM.md §4` within-day ordering).
8. **Halt check + halt auto-email** — identical to `engine.py:484-490`.
9. **Ledger record** (§14) — exactly one per day.

---

## 4. EpisodeView / feature allowlist

`EpisodeView` (`episode_view.py:67-86`):

| Field | Source | Type | Populated in sim-v1? | Allowed in prompt? | Future info? |
|---|---|---|---|---|---|
| `subscription_id` | `f"{split}-{i}"` | `str` | Yes | Yes | No |
| `subscription_state` | `state.subscription_state` | `str` | Yes | Yes | No |
| `invoice_amount_inr` | `cohort.invoice_amount_inr` | `int` | Yes | Yes | No |
| `days_since_first_failure` | `day` | `int` | Yes | Yes | No |
| `auto_retries_remaining` | count of scheduled future retry days | `int` | Yes | Yes | No (schedule, not outcome) |
| `next_auto_retry_day` | next scheduled retry day | `int \| None` | Yes | Yes | No |
| `decline_code` | `cohort.opening_condition_key` | `str` | Yes | Yes | No |
| `billing_amount_inr` | aliased to `invoice_amount_inr` | `int` | Yes | Yes | No |
| `contact_history` | `tuple(state.contact_history)` | `tuple[ContactRecord, ...]` | Yes | Yes | No |
| `budget_remaining` | `max_contacts - contacts_sent` | `int` | Yes | Yes | No |

`ContactRecord` (`episode_view.py:51-64`): `day`, `channel`, `remedy`,
`delivered`, `engaged` — all populated, all allowed, none future.

**Explicitly excluded:** latent state (`LATENT_FIELD_NAMES`,
`test_no_latent_leak.py:80-88`), RNG seeds, other episodes, future retry
*outcomes*, `customer_tenure_days` (verified inert, Task 3A.1 Q5),
cross-episode customer history.

---

## 5. Wake-up events — FROZEN

**Fixed set:** days `{0, 1, 2, 3, 5, 7, 14}`.

**Plus an event-driven wake-up:** any day where `contact_history` has
gained a new `engaged=true` record since the last wake.

**Suppressed** (no planner invocation) when `subscription_state` is
terminal, or `budget_remaining == 0`.

**Identical for A3-D and A3-LLM.** The planner never selects its own
wake-ups — this is entirely runner-owned.

**Rationale for T+5/T+7 (not just T+0-T+3):** subscription rescue is only
reachable *post-halt* (halt occurs at T+3,
`episode.yaml#/payment_method_change_effect/halt_boundary_day`), and
`a2_strengthened_action_for_day` — the adopted §4.1.2 comparator —
contacts on exactly these later days (card-broken bucket: T+0/T+3/T+5;
`ambiguous_decline`: T+0/T+7). A wake-up set ending at T+3 would make
subscription rescue **structurally unreachable** for A3 in the card-
broken/ambiguous buckets — one of `EVAL.md §7`'s two headline metrics
would be capped by runner design, before A3-D or A3-LLM ever ran a
single decision.

**A3 does not get more actions than A2 — it gets the same 3-contact
budget with more decision points at which to decide whether to spend
it.** T+5/T+7/T+14 are opportunities to *reconsider*, not additional
contacts beyond the shared cap; the gate (§8, R5) enforces the same
3-contact ceiling on A3 that every other arm operates under. T+14 gives
A3 one further mid-window point at which to decide whether the same
budget is better spent now or held — a decision A2's fixed schedule does
not make at all, since A2 never decides, it only executes.

On a **non-wake-up day**, `tick_type=no_wakeup`, no ledger `reason_code`
is populated (reason_code is wakeup-only, §7). This is an audit decision,
not a simulator contact — no budget consumed, no message sent.

---

## 6. Action / proposal contract

**Proposal:**

| Field | Type | Notes |
|---|---|---|
| `action_type` | `CONTACT \| WAIT \| STOP` | 3 values |
| `remedy` | `card_change \| topup_reminder \| null` | required iff `CONTACT` |
| `rationale` | free text | **populated for both arms** — A3-D: a fixed rule-id string (§10, §13); A3-LLM: model-generated |
| `reason_code` | one of 7 (§7) | mandatory on every Proposal |

**`channel` is not part of the Proposal schema.** Pinned to `whatsapp`
at the executor (§9), not chosen by the policy — see §20 for the
fairness rationale.

**No timing field.** A proposal is for *today's* decision only; wake-up
scheduling is runner-owned (§5).

**Pipeline:** `proposal → gate verdict → executed action` (possibly
A3-D's own result, if this was an A3-LLM fallback).

**STOP semantics:** the agent voluntarily forgoes remaining budget. It
does **not** end the simulator's day loop, which always runs days 0-30
regardless (`SIM.md §4`). After a STOP decision, subsequent would-be
wake-up days produce `tick_type=terminal_suppressed` instead of invoking
the planner again (§7).

---

## 7. Decision-audit taxonomy (four fields)

- **`tick_type`**: `wakeup | no_wakeup | budget_exhausted | terminal_suppressed`
  - `no_wakeup`: day not in the frozen set (§5) and no engagement trigger.
  - `budget_exhausted`: `budget_remaining == 0` (enforcement-by-construction,
    mirrors `engine.py:464` — never a fabricated gate rejection, §8).
  - `terminal_suppressed`: `subscription_state` is terminal, **or** the
    episode has previously received a `STOP` decision.
  - `wakeup`: the planner was actually invoked.

- **`reason_code`** (7 values, populated **only** on `wakeup` ticks):

| `reason_code` | Meaning | Typical action | Admissible `decline_code`s |
|---|---|---|---|
| `remedy_match_card` | Card-broken/ambiguous condition | `CONTACT(card_change)` | `card_expired`, `debit_instrument_blocked`, `card_not_enabled_group`, `ambiguous_decline`, `bank_technical_error` |
| `remedy_match_topup` | Balance condition | `CONTACT(topup_reminder)` | `insufficient_funds`, `transaction_limit_exceeded` |
| `retry_window_open` | Waiting — an auto-retry may still resolve it | `WAIT` | `insufficient_funds`, `bank_technical_error`, `transaction_limit_exceeded` |
| `post_halt_rescue` | Post-halt contact aimed at subscription rescue | `CONTACT(card_change)` | `card_expired`, `debit_instrument_blocked`, `card_not_enabled_group`, `ambiguous_decline` — **requires** `subscription_state == halted` (`SIM.md §5`'s at-opening `card_chargeable=False` restriction; not admissible for `bank_technical_error`, whose `card_chargeable=True` at opening per `SIM.md §2`) |
| `engagement_observed` | Re-contacting — prior engagement seen this episode | `CONTACT` | any except `subscription_cancelled_by_customer` |
| `no_engagement_restraint` | Withholding — low observed engagement this episode | `WAIT` | any except `subscription_cancelled_by_customer` |
| `risk_flagged` | Escalation | `STOP` | `payment_risk_check_failed` only |

**`terminal_state` removed from this enum (reduced from 8 to 7 values).**
`subscription_cancelled_by_customer` is the only `decline_code` for which
a terminal-state reason would apply, but `engine.py:438-443` shows this
opening condition (`condition["kind"] == "subscription_state"`) causes
`run_episode()`-equivalent logic to return **immediately at T=0, before
any day-loop iteration runs at all** — no day-0 tick, no wakeup, no
non-wakeup tick, nothing. The A3 runner mirrors this exactly (§3), so a
`terminal_state` reason_code could never actually be emitted — it was
dead code in the enum. Removed rather than kept as a defensive
placeholder. See §20 and `EVAL.md §8` item 8 for the full consequence of
this finding (the cancelled bucket's zero-contact behaviour is
environment-enforced, not agent-demonstrated, for **every** arm).

- **`gate_rule_fired`**: `R1–R8 | null` (§8). **R2** (contacts to
  cancelled/expired subscriptions) is retained in the gate for defense-
  in-depth, but — following directly from the reachability finding above
  — is never triggered by a real A3 runner tick in `sim-v1`: it is
  exercised **only** by the synthetic adversarial proposals §8's gate
  tests construct.
- **`fallback_reason`**: `timeout | unparseable | schema_violation |
  gate_rejected | stale_state | null` (§11, §19).

Not part of, and does not modify, `data/decline_codes.yaml`.

---

## 8. Safety gate

| # | `EVAL.md §5.2` row | Gate rule | Enforcement mode |
|---|---|---|---|
| 1 | Agent-initiated retries: 0 | R1: reject any retry-implying action | Defensive — no such value exists in the schema |
| 2 | Contacts to cancelled/expired: 0 | R2: reject `CONTACT` when `subscription_state ∈ {cancelled, expired}` | **Defensive only, in practice unreachable** — `subscription_cancelled_by_customer` episodes never generate a runner tick at all (§7), so R2 is exercised solely by synthetic adversarial test proposals, never by real A3-D/A3-LLM output |
| 3 | Card-change for insufficient_funds/transaction_limit_exceeded: 0 | R3: reject `remedy=card_change` for those `decline_code`s | Active |
| 4 | Contacts after payment_risk_check_failed: 0 | R4: reject `CONTACT` when `decline_code == payment_risk_check_failed` | Active |
| 5 | Budget cap: 0 | R5 | **Enforcement-by-construction** — planner never invoked once `budget_remaining==0` (§3 step 3); `tick_type=budget_exhausted`, never a fabricated gate rejection |
| 6 | Quiet hours: 0 | R6 | **Declared vacuous in sim-v1.** No intraday model exists. Executor stamps a fixed `send_hour=10:00 IST` on every sent message (§9); R6 validates that constant; the test asserts zero violations trivially. Not presented as a live gate |
| 7 | No audit record: 0 | Runner invariant — one ledger record per tick, structurally guaranteed | Structural |
| 8 | Unverified/attended-only codes: 0 | R8: defensive reject | Defensive — already guaranteed by cohort generation |

**Precedence:** R2, R4 → R3 → R1, R8 → R5, R6.

**Gate test driver:** the eight gate tests are driven by **synthetic
adversarial proposals constructed in the test**, never by A3-D or A3-LLM
output. A3-D is gate-compliant by construction — its own decision logic
never proposes a violating action — so a gate tested only against A3-D's
output would never exercise a single rejection path (and, per R2 above,
could never exercise that path through real output even in principle).
For each of R1–R8: one test proposal engineered to trigger it (assert
reject), one engineered not to (assert accept). Not implemented in this
pass.

---

## 9. Executor

| Proposal | Executor action | Primitive |
|---|---|---|
| `remedy=card_change` | `_send_message(names_card=True, names_dues=False, is_agent_contact=True, channel=AGENT_CHANNEL)` | unmodified |
| `remedy=topup_reminder` | `_send_message(names_card=False, names_dues=True, is_agent_contact=True, channel=AGENT_CHANNEL)` | unmodified |
| `WAIT` | No-op | ledger-only |
| `STOP` | No `_send_message` call; runner marks episode agent-terminated for contact purposes; subsequent wake-ups become `tick_type=terminal_suppressed` | runner-level flag only |

`channel` is **always** `AGENT_CHANNEL` ("whatsapp") — never chosen by
the proposal (§6, §20).

`send_hour=10:00` is stamped as a **ledger-only annotation** for every
sent message (`src/rrx/agent/ledger.py`, §14). It is **not** added to
`ContactRecord`/`EpisodeView`, which remain at their current, locked
field sets (`CONTACT_RECORD_ALLOWED`, `test_no_latent_leak.py:71`).

No new simulator mechanics. `escalate`/`stop_episode` fold entirely into
`STOP`, which needs no state-mutating primitive — a runner-level flag.

---

## 10. A3-D deterministic ablation

Same `EpisodeView`, runner, gate, executor, ledger, wake-up schedule as
A3-LLM; differs only in the policy function (`src/rrx/agent/policy.py`)
— pure, deterministic, no network, no RNG beyond shared CRN substreams.

**Status:** ablation **and control** arm. Must clear every §5.2 gate.
**Not** required to clear §7's 40%-of-gap criterion. **Pre-registered
now:** if A3-D outperforms A3-LLM on either primary metric, that result
is published as the finding; A3-LLM is not re-tuned in response
(`EVAL.md §4.2`).

**Rationale field:** always populated, with the internal rule identifier
that fired (e.g. `"R_topup_insufficient_funds"`) — not left null.

**Comparison:** A3-LLM − A3-D, paired bootstrap, same episode indices
(§15's world-level-pairing caveat applies).

The concrete decision table is implementation, not this design freeze.

---

## 11. A3-LLM planner

- **Input:** `EpisodeView` + `template_version` — nothing else.
- **Prompt construction:** deterministic template render (§12).
- **Output schema:** `action_type` (`CONTACT|WAIT|STOP`), `remedy`,
  `reason_code`, `rationale` — no `channel` field (§6).
- **Parsing:** strict schema validation.
- **Timeout → fallback:** `fallback_reason=timeout`.
- **Malformed/unparseable → fallback:** `fallback_reason=unparseable` or
  `schema_violation`.
- **Gate rejection → fallback:** `fallback_reason=gate_rejected`.
- **Stale state at gate-check time → fallback:** `fallback_reason=stale_state`
  (§19).
- **Fallback mechanics:** re-invoke A3-D's pure function for the same
  `EpisodeView`/tick; its proposal executes through the same gate/executor.
- **Attribution:** episode remains attributed to arm `A3-LLM`; per-tick
  `fallback_reason` marks exactly which ticks were actually A3-D's logic.

---

## 12. Prompt / latent-leak invariant

Prompt construction consumes only `EpisodeView`/`ContactRecord` fields
(§4); no `rrx.sim.latent` import; no `_EpisodeState` stringification; no
RNG/seed exposure; no future-tick information beyond §4's schedule
fields; no cross-episode information; no `channel` selection surface to
leak through (removed, §6).

**New test required** (Task 3A.1 Q E, unresolved by any existing
coverage): a prompt-content test rendering a synthetic `EpisodeView` and
asserting the rendered string contains none of `LATENT_FIELD_NAMES`
(`test_no_latent_leak.py:80-88`) and no RNG-seed-shaped token. Because
`src/rrx/agent/prompt.py` lives under the guarded package (§2), it also
inherits `test_no_latent_leak.py`'s existing import-graph checks
automatically — but those check imports, not rendered string content, so
this new test remains necessary on top of, not instead of, that coverage.
Not implemented in this pass.

---

## 13. LLM cache / reproducibility

- **Cache key:** `(template_version, model, temperature, prompt_hash)`.
- **Canonical run artifact:** `results/<run_id>/llm_cache.jsonl`.
- **Replay:** any reproduction of a past `run_id` must satisfy every LLM
  call from that run's cache. **Cache-miss during exact replay = hard
  failure**, never a silent live re-call.
- **`--allow-live`:** required for any live call (initial canonical run,
  cache extension, **or** one of the three repeat-nondeterminism runs).
- **Repeat-run exception:** the three nondeterminism repeat-runs
  (`EVAL.md §8` item 4, `§6A`) over seeds 1000–1299 are each an
  **independent live run**, not a replay of a prior `run_id` — each
  writes its own cache file (`llm_cache_rep1.jsonl`, `rep2.jsonl`,
  `rep3.jsonl`) precisely so they are not constrained to reproduce each
  other. The hard-failure-on-miss rule applies when replaying *one
  specific* `run_id`; it does not apply between these three independent
  runs.
- **`reproduced` manifest field:** `false` whenever any call in a run was
  live; `true` otherwise. Extends `RunManifest` (`rrx/spec/manifest.py:29-44`)
  with one new field — not implemented in this pass.

---

## 14. Audit ledger

Per-tick JSONL record, written by `src/rrx/agent/ledger.py`:

| Field | Type | Meaning | Mandatory? | A3-D applicability |
|---|---|---|---|---|
| `episode_id` | str | `subscription_id` | Yes | Yes |
| `tick` | int | day `D` | Yes | Yes |
| `tick_type` | enum (§7) | wakeup / no_wakeup / budget_exhausted / terminal_suppressed | Yes | Yes |
| `view_hash` | str | hash of the `EpisodeView` used | Yes | Yes |
| `prompt_hash` | str \| null | §13 cache key component | Only A3-LLM | Null |
| `raw_output` | str \| null | unparsed model response | Only A3-LLM | Null |
| `parsed_action` | object \| null | the Proposal (§6) | On `wakeup` ticks | Yes |
| `reason_code` | enum (§7, 7 values) \| null | wakeup-only | On `wakeup` ticks | Yes |
| `rationale` | str \| null | populated for both arms — A3-D: fixed rule-id string; A3-LLM: model text | On `wakeup` ticks | Yes — fired rule id |
| `gate_verdict` | enum: accept/reject \| null | §8 outcome | On `wakeup` ticks | Yes |
| `gate_rule_fired` | `R1-R8` \| null | §8 | If rejected | Yes |
| `fallback_reason` | enum (§7, 5 values) \| null | | If fallback occurred | Always null — A3-D is the fallback target |
| `executed_action` | object \| null | what actually ran | Yes | Yes |
| `budget_before` | int | pre-decision | Yes | Yes |
| `budget_after` | int | post-decision | Yes | Yes |
| `send_hour` | str | fixed `"10:00"` stamp for R6 (§8, §9) | If a contact was sent | Yes |
| `latency_ms` | float \| null | planner call latency | Only A3-LLM | Null |
| `tokens_in` | int \| null | prompt tokens | Only A3-LLM | Null |
| `tokens_out` | int \| null | completion tokens | Only A3-LLM | Null |
| `cost` | float \| null | ₹ (`EVAL.md §5.1`) | Only A3-LLM | `0.0` |
| `model_version` | str \| null | pinned model id | Only A3-LLM | Null |
| `template_version` | str \| null | §13 cache key component | Only A3-LLM | Null |

---

## 15. Determinism / CRN contract

World-level CRN identical across all arms (`engine.py:429-431`);
planner/LLM randomness never touches simulator RNG; LLM output made
replayable through the cache (§13); per-message engagement draws not
perfectly paired across arms (arm-local message-index counter,
`engine.py:206-207`) — treated as variance, not bias; paired bootstrap
remains valid at the world/episode level.

---

## 16. Byte-identity / mechanics-parity requirements

File-hash identity of `src/rrx/sim/*` and `episode_view.py`; exact
`EpisodeResult` equality for A0/A1/A2-original/A2-corrected/
A2-strengthened over `dev` seeds 1000–2999 (2,000 episodes); exact
`contact_history` equality via `capture_view_at_day=30`; exact aggregate-
metric equality; A4 test-loop parity; full `pytest`/`ruff` status parity
(preserving the intentional 4-of-5 Stage 5 result). Not created in this
pass.

---

## 17. Evaluation requirements (carried forward)

Primary/secondary metrics, cost model, gate invariants, statistical
methodology, and target definition unchanged from `EVAL.md §5-§7`.
`wait_rate` for A3 = WAIT decisions / wake-up decisions, `tick_type !=
wakeup` excluded (§5's rationale, `EVAL.md §5.3` amendment). "Unknown-
condition escalation rate" = STOP decisions with `reason_code=risk_flagged`
(`EVAL.md §5.3` amendment). LLM cost charged to A3-LLM alone; A3-D's
`cost` field is always `0.0`, never omitted. No episode dropped on any
planner failure (§19).

---

## 18. Pre-registered tuning and sweep

- **Tuning budget:** A3-LLM N=6, A3-D N=3 dev configurations, in
  `results/tuning_log.md`. **The 6 A3-LLM tuning configurations are
  evaluated on the 500-episode subsample (seeds 1000–1499), not full
  `dev`** — only the **selected** configuration is subsequently run on
  full `dev`.
- **Sweep subsample:** 500 `dev` episodes (seeds 1000–1499) for A3-LLM,
  all six `[MODEL]` parameters retained. A2 additionally run on the same
  500 indices, specifically for pairing against A3-LLM — separate from,
  and not a substitute for, A2's own full-dev (N=2,000) canonical sweep.
- **A3-D swept at full `dev`** (N=2,000, all 22 cells) — deterministic,
  free.
- **A2's canonical full-dev sweep is scheduled as independent
  deterministic work, not blocked on A3.** `results/sensitivity.md` is
  currently 100% `PENDING`; this pass schedules A2's run to populate it.
- **Pre-registered sweep-cost contingency**, declared now, before any
  results exist — never to be applied silently: if A3-LLM's full 22-cell
  sweep proves cost-prohibitive, the fallback is A3-D swept across all 22
  cells (unaffected) and A3-LLM swept across the nominal cell plus the
  four cells for `channel_response_propensity` (low, high) and
  `card_change_completion_propensity` (low, high) only. Any invocation of
  this fallback must be declared explicitly in `results/sensitivity.md`,
  naming which cells were skipped and why.
- **Repeat-run subsample:** seeds 1000–1299, nested inside the 500-episode
  sweep subsample. Three live runs, three separate cache files (§13).
- Relationship to "no per-cell retuning" (`model_params.yaml`, locked
  decision 14): tuning happens once, pre-freeze; the frozen result then
  runs unmodified across every sweep cell. Both rules apply, at different
  points in the timeline.

---

## 19. Failure injection

| Mode | Ledger representation | Episode outcome |
|---|---|---|
| API timeout | `fallback_reason=timeout` | Continues — A3-D executes |
| Malformed/hallucinated LLM action | `fallback_reason=unparseable`, `schema_violation`, or `gate_rejected` | Continues |
| Mid-episode subscription state change | Gate re-checks **current** `state.subscription_state` at proposal-evaluation time, not just prompt-build time; a mismatch → `fallback_reason=stale_state` | Continues |

All three: run continues, failure fully visible in the ledger, no episode
dropped — `EVAL.md §7` criterion 5.

---

## 20. Advantage sources / limitations

`EVAL.md §3.4`'s three sources, verbatim (Task 3A.1 Q4): retry-window
timing, remedy matching, channel selection narrowed to within-episode
adaptive contact.

**Channel is pinned to `whatsapp` for both A3 arms. Lead reason: this
removes an advantage A3 would otherwise hold over every other arm.**
Every existing arm (A0, A1, A2-original, A2-corrected, A2-strengthened)
sends through `engine.py`'s hardcoded `AGENT_CHANNEL` constant — none of
them ever choose a channel. Giving A3 a free choice would hand it a
capability no baseline was ever allowed, making any A3-vs-A2 uplift
partially attributable to a call-site asymmetry rather than to agent
judgement. Pinning `AGENT_CHANNEL` closes that off entirely: A3, like
every other arm, sends on `whatsapp`. As supporting evidence, not the
argument, this costs A3 nothing in expectation — `whatsapp`'s multiplier
(1.15) is already the highest of the three channels (`sms` 1.00, `email`
0.65, `episode.yaml:164-167`), so pinning to it is not a handicap either.
**Advantage source 3 is therefore exclusively within-episode adaptive
contact** — no channel-selection mechanism remains in A3's design at
all.

**The 5% cancelled-at-open bucket is environment-restraint, not
agent-restraint, for every arm.** `subscription_cancelled_by_customer`
episodes terminate at T=0 before any per-day tick exists
(`engine.py:438-443`) — not merely before any contact is sent. No arm,
including A3-D/A3-LLM, is ever invoked for this bucket; the zero-contact
outcome is structural, identical for A0/A1/A2/A3/A4. This also applies to
the all-`cancelled` `stress` cohort (`EVAL.md §3.5`). No pitch, README,
or results narrative may cite this bucket's zero-contact rate as evidence
of A3's judgement or restraint — it demonstrates nothing about the
policy, deterministic or LLM. See `EVAL.md §8` item 8 (verbatim
cross-reference) — flagged for definitive verification once the runner
is implemented.

`customer_tenure_days` inert (Task 3A.1 Q5); cross-episode history out of
scope; unpaired per-message engagement draw documented as variance (§15).

---

## 21. Open questions / deferred decisions

None remain from the prior design pass. Both items previously listed
here are resolved:

- The `GUARDED_PACKAGES` coverage gap is closed by module placement (§2)
  — gate and ledger live under `src/rrx/agent/`, not by amending
  `test_no_latent_leak.py`.
- `reason_code=terminal_state`'s reachability question is resolved by
  removing it from the enum (§7) — it was unreachable by construction,
  and the underlying finding (the cancelled bucket's restraint is
  environment-, not agent-, enforced) is now recorded as a limitation in
  §20 and `EVAL.md §8` item 8, flagged for definitive verification during
  implementation rather than left as an open design question.

No new open question was introduced by this pass's four amendments or
two wording fixes.

---

## 22. Artifact policy

- **`results/**/ledger.jsonl` and `results/**/llm_cache*.jsonl` are
  gitignored.** Per-episode audit ledgers and LLM response caches are run
  outputs, not source — they are large, run-specific, and (for the
  cache) may contain full LLM prompts/completions not intended for
  version control.
- **`results/audit_sample/` is committed.** A curated set of
  approximately 20 episodes, selected to cover every `tick_type`, every
  gate rejection path (R1–R8), and every `fallback_reason` value at least
  once. This is the public audit-trail deliverable — a reviewer can
  inspect real, representative ledger records without needing a full run.
- **Manifests and aggregate results are always committed** —
  `results/<run_id>/manifest.json` (`rrx.spec.manifest`),
  `results/sensitivity.md`, `results/tuning_log.md`, and similar
  aggregate/summary artifacts are source-controlled, not gitignored.

Not implemented in this pass — no `results/` directory or `.gitignore`
entry exists yet; this section documents the policy for when
implementation creates them.
```
---

## 6. EVALUATION DESIGN FACTS

All items below are quoted from `EVAL.md` only, with exact line numbers
against the verbatim dump in Section 3 above.

**Full list of evaluation arms and their definitions** — `EVAL.md:261-269`
(the arms table) plus `EVAL.md:273-313` (A2's three variants) and
`EVAL.md:315-343` (§4.2, A3's two named arms):
> `A0 — Razorpay default`, `A1 — Naive dunning`, `A1-U — Unbounded`,
> `A2 — Competent rules` (three variants: A2-original, A2-corrected-v1,
> A2-strengthened — the last "adopted as 'the' A2"), `A3 — Agent` (split
> into `A3-D` and `A3-LLM`, `EVAL.md:315-343`), `A4 — Oracle`.

**The pre-registered comparator arm for A3** — `EVAL.md:524` (§7 criterion
2) defines the comparator as **dynamic, not a single fixed arm**: "A3's
rate exceeds the best-performing bounded non-agent arm's rate on that
same metric... Bounded non-agent arms = {A0, A1, A2 (as finally adopted,
§4.1)}." There is no single named "the comparator" in EVAL.md for A3
overall. A **fixed** comparator does exist, but only for the narrower
A3-LLM-vs-A3-D comparison: `EVAL.md:334-337` (§4.2) — "A3-LLM's
contribution is reported as A3-LLM − A3-D, paired bootstrap (§6)... over
the same episode indices." (`configs/model_params.yaml`'s
`sweep.win_criterion.comparator: A2` is a *sweep-grid* win criterion, a
different file, not part of this EVAL.md-only answer.)

**Dev seed range / indices** — `EVAL.md:231`: "`dev` | 2,000 |
1,000–2,999 | All development and tuning".

**Held-out / test seed range / indices** — `EVAL.md:232`: "`holdout` |
2,000 | 9,000–10,999 | **Once** per candidate release".

**Any additional split** — `EVAL.md:233`: "`stress` | 300 | 5,000–5,299 |
Adversarial", with the stress cohort composition at `EVAL.md:237`:
"all-`cancelled` cohort... all-`halted`-at-open; high-value only
(≥₹10,000...); unreachable customer." No calibration/sensitivity-subset
split beyond these three is named anywhere in EVAL.md (the 500-episode
and 300-episode **subsamples** at `EVAL.md:469-518` §6A are subsets of
`dev`, not separate named splits).

**Population definition** — `EVAL.md §3`, lines 87-161: generated by
`src/rrx/sim/` from `configs/population.yaml`, synthetic only
(`EVAL.md:89`); invoice amount `LogNormal(mu=ln(2000), sigma=1.0)`
rejection-sampled to `[₹100, ₹50,000]` (`EVAL.md:93`); 9-condition failure
mix with weights summing to 1.0 (`EVAL.md:101-113`); four latent
parameters (`EVAL.md:119-161`). Episode **count** per split is given only
in §3.5's table (`EVAL.md:231-233`), not restated in §3 itself.

**Pre-registered metrics, with exact definitions** — `EVAL.md:347-360`
(§5): primary (Regime B) = invoice recovery rate, subscription rescue
rate, contacts per invoice recovered, contacts per subscription rescued,
total contacts across the cohort, median/p90 time-to-rescue; secondary
(Regime A) = net value formula and cancellations attributable to contact
volume; broken out separately: `card_declined`/`payment_failed` bucket
and the `cancelled`-at-open bucket.

**Success thresholds / GO criteria, exact numbers** — `EVAL.md:521-538`
(§7): five numbered criteria; criterion 2's revised target
(`EVAL.md:533`): "A3 captures ≥40% of the A4 minus best-bounded-arm gap on
both primary metrics on `holdout`", with illustrative (not fixed) `dev`
figures at `EVAL.md:535`: "invoice recovery ≥ 0.5090... subscription
rescue ≥ 0.5499." The **original**, superseded target is preserved at
`EVAL.md:531`: "≥15% relative uplift... A target, not an expectation."

**Tuning rules: budget, what counts as one configuration, per-cell
retuning policy, tuning-log requirements** — `EVAL.md:469-518` (§6A):
budget "A3-LLM N = 6 dev configurations; A3-D N = 3 dev configurations"
(`EVAL.md:471-472`); every configuration tried "including losing ones, is
recorded in `results/tuning_log.md`" (`EVAL.md:475-477`); "distinct from,
and does not relax, `configs/model_params.yaml`'s existing
`frozen_policies` / 'no per-cell retuning' rule (locked decision 14)"
(`EVAL.md:477-480`). EVAL.md does not itself define "what counts as one
configuration" beyond the N=6/N=3 counts — that definition is not present
in EVAL.md's text (NOT SPECIFIED IN EVAL.md, beyond the count).

**Provenance/tagging requirements** — `EVAL.md:11-23` (§0's four-tier
table) and `EVAL.md:635-648` (§10's freeze checklist and its closing
rule: "After the tag, the only reason to reopen this file is a discovered
validity defect — never to improve expected A3 performance.").

**The §8 threat list, in full, with threat numbering as written** —
`EVAL.md:552-614`, quoted verbatim in Section 3 above (items 1-6
"[RECOVERY, eval-spec-v1.4] Restored verbatim", items 7-8
"[ADDED, eval-spec-v1.4]").

**Any statement about paired comparison / CRN methodology** —
`EVAL.md:461` (§6): "common random numbers, so episode *i*'s latent world
is identical across arms; paired bootstrap, 10,000 resamples, 95% CI on
the difference between arms." Also `EVAL.md:583-591` (§8 item 7, added
v1.4): world-level CRN pairing holds; per-message engagement draws are
**not** perfectly paired across arms — "arm-local message-index counter
(`engine.py:206-207`...)... Treated as increased variance in the
paired-bootstrap estimate, not as bias."

**Any statement about confidence intervals (method, level, n_boot)** —
same line, `EVAL.md:461`: method = paired bootstrap, `n_boot` = 10,000
resamples, level = 95% CI, computed on the **difference between arms**
(not on each arm's rate independently). `EVAL.md:463`: "A point estimate
with no interval is not a result."

### Which of the above appear ONLY in docs/A3-DESIGN.md, not in EVAL.md

- The exact **wake-up day set** `{0, 1, 2, 3, 5, 7, 14}` and the
  event-driven engagement trigger — `A3-DESIGN.md §5` only; EVAL.md never
  states a concrete wake-up schedule.
- The **gate rule IDs R1-R8**, their precedence order, and their
  enforcement-mode annotations (defensive/active/structural/
  by-construction) — `A3-DESIGN.md §8` only; EVAL.md's §5.2 table names
  the eight *invariants* and their eventual test-file names, but never
  assigns R1-R8 identifiers or a precedence order.
- The **22-field ledger schema** (exact field names/types/mandatory
  columns) — `A3-DESIGN.md §14` only.
- The **Proposal/action schema** (`action_type`, `remedy`, `rationale`,
  `reason_code`, no `channel` field) — `A3-DESIGN.md §6` only.
- The **executor mapping table** (Proposal → `_send_message()` call
  shape) — `A3-DESIGN.md §9` only.
- The **LLM cache key formula and replay/hard-failure-on-miss contract**
  — `A3-DESIGN.md §13` only.
- The **module file layout** (`runner.py`, `policy.py`, `planner.py`,
  `prompt.py`, `gate.py`, `ledger.py`) — `A3-DESIGN.md §2` only.
- The **reason_code → admissible decline_code table** (7×N mapping) —
  `A3-DESIGN.md §7` only (EVAL.md §5.4 names the 7 reason_codes but not
  their admissible-decline_code mapping).
- The **artifact/gitignore policy** for `results/**/ledger.jsonl`,
  `llm_cache*.jsonl`, `audit_sample/` — `A3-DESIGN.md §22` only.
---

## 7. AGENT CONTRACTS

`src/rrx/agent/` currently contains 5 non-`__init__` modules:
`proposal.py`, `gate.py`, `reason_codes.py`, `ledger.py`, `null_policy.py`.
`policy.py` (A3-D) and `planner.py`/`prompt.py` (A3-LLM), named in
`docs/A3-DESIGN.md §2`'s module list, do **not** exist yet —
MISSING: `src/rrx/agent/policy.py`, `src/rrx/agent/planner.py`,
`src/rrx/agent/prompt.py` — searched: `Glob src/rrx/agent/**/*.py`.

### `src/rrx/agent/proposal.py` (verbatim)

```python
"""The Proposal contract (docs/A3-DESIGN.md §6).

The only object an A3 policy (A3-D or A3-LLM, neither implemented in
this pass) returns to the runner. Plain data only - never holds a
reference to any rrx.sim object, so this module has no structural need
to import rrx.sim and never does.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Proposal:
    """docs/A3-DESIGN.md §6. `channel` is deliberately absent - pinned to
    AGENT_CHANNEL at the executor, never chosen by the policy (§6, §20).
    `reason_code`'s 7-value frozen enum (§7) and the gate's R1-R8
    enforcement of this contract are future work (§8) - not implemented
    in this pass.
    """

    action_type: str  # "CONTACT" | "WAIT" | "STOP"
    remedy: str | None  # "card_change" | "topup_reminder" | None
    rationale: str
    reason_code: str
```

### `src/rrx/agent/gate.py` (verbatim)

```python
"""The safety gate (docs/A3-DESIGN.md §8) - R1-R8, in the frozen
precedence order R2, R4 -> R3 -> R1, R8 -> R5, R6.

Pure function: `evaluate_gate(proposal, view)` reads only its two
arguments (plus the R6-only `send_hour` override, a testability knob -
see below) and a small set of module-level constants; no I/O, no rrx.sim
import, no mutation of `proposal`/`view` (both are frozen dataclasses
anyway).

R5 (budget) and R6 (quiet hours) are enforcement-by-construction per §8:
the real runner (src/rrx/harness/runner.py) never invokes the policy, and
therefore never calls this gate, once `budget_remaining == 0`
(tick_type=budget_exhausted instead - §3 step 3), and always executes
messages at the fixed `AGENT_SEND_HOUR` this module defines (§9). Both
rules below are still implemented and checked, so a synthetic adversarial
Proposal/EpisodeView (or, for R6, an explicit `send_hour` override) can
exercise the rejection path in tests/test_gate_rules.py - but neither
should ever actually fire against a real runner tick. Do not fabricate a
gate rejection for a budget-exhausted tick anywhere else in this
codebase; that case is tick_type=budget_exhausted at the runner level,
never a gate call at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from rrx.agent.proposal import Proposal
from rrx.agent.reason_codes import ALL_DECLINE_CODES
from rrx.features.episode_view import EpisodeView

# §9: the executor's fixed send-hour stamp. R6 validates this constant.
AGENT_SEND_HOUR = "10:00"

# data/decline_codes.yaml#/defaults/global_caps/quiet_hours_ist - not a
# new config key, just this project's already-frozen 09:00-21:00 IST
# window, restated here as the literal bound R6 checks against.
_QUIET_HOURS_START = "09:00"
_QUIET_HOURS_END = "21:00"

# §6: the only 3 legal Proposal.action_type values. Anything else is, by
# construction, an action outside the schema - R1's target ("no such
# value exists in the schema").
_VALID_ACTION_TYPES = frozenset({"CONTACT", "WAIT", "STOP"})

# R2: subscription_state values a CONTACT must never be sent against.
# "expired" never occurs in sim-v1 (checked anyway, matching R2's own
# defensive/unreachable framing, §8).
_R2_TERMINAL_SUBSCRIPTION_STATES = frozenset({"cancelled", "expired"})

# R3: decline_codes for which card_change is never the correct remedy.
_R3_FORBIDDEN_CARD_CHANGE_DECLINE_CODES = frozenset(
    {"insufficient_funds", "transaction_limit_exceeded"}
)

# R4: the single hard-stop decline_code.
_R4_RISK_DECLINE_CODE = "payment_risk_check_failed"


@dataclass(frozen=True, slots=True)
class GateVerdict:
    accepted: bool
    rule_fired: str | None  # "R1"-"R8" | None (§8)


def _within_quiet_hours(send_hour: str) -> bool:
    """Zero-padded "HH:MM" strings compare correctly under plain string
    ordering within a single day."""
    return _QUIET_HOURS_START <= send_hour <= _QUIET_HOURS_END


def evaluate_gate(
    proposal: Proposal, view: EpisodeView, *, send_hour: str = AGENT_SEND_HOUR
) -> GateVerdict:
    """§8's R1-R8, checked in the frozen precedence order
    R2, R4 -> R3 -> R1, R8 -> R5, R6. Returns the FIRST rule that fires;
    a proposal violating several rules is reported under only the
    highest-precedence one (tests/test_gate_precedence.py)."""

    # --- R2, R4 (tied precedence; checked R2 then R4) ---
    if proposal.action_type == "CONTACT" and view.subscription_state in (
        _R2_TERMINAL_SUBSCRIPTION_STATES
    ):
        return GateVerdict(accepted=False, rule_fired="R2")
    if proposal.action_type == "CONTACT" and view.decline_code == _R4_RISK_DECLINE_CODE:
        return GateVerdict(accepted=False, rule_fired="R4")

    # --- R3 ---
    if (
        proposal.action_type == "CONTACT"
        and proposal.remedy == "card_change"
        and view.decline_code in _R3_FORBIDDEN_CARD_CHANGE_DECLINE_CODES
    ):
        return GateVerdict(accepted=False, rule_fired="R3")

    # --- R1, R8 (tied precedence; checked R1 then R8) ---
    if proposal.action_type not in _VALID_ACTION_TYPES:
        return GateVerdict(accepted=False, rule_fired="R1")
    if proposal.action_type == "CONTACT" and view.decline_code not in ALL_DECLINE_CODES:
        return GateVerdict(accepted=False, rule_fired="R8")

    # --- R5, R6 (tied precedence; checked R5 then R6) ---
    if proposal.action_type == "CONTACT" and view.budget_remaining <= 0:
        return GateVerdict(accepted=False, rule_fired="R5")
    if not _within_quiet_hours(send_hour):
        return GateVerdict(accepted=False, rule_fired="R6")

    return GateVerdict(accepted=True, rule_fired=None)
```

### `src/rrx/agent/reason_codes.py` (verbatim)

```python
"""The reason_code taxonomy (docs/A3-DESIGN.md §7) - 7 values, plus the
admissible-decline_code-per-reason_code mapping from the same table.

`terminal_state` was removed in eval-spec-v1.4 (reduced from 8 to 7
values): `subscription_cancelled_by_customer` never reaches a day-loop
tick at all (condition["kind"] == "subscription_state" returns before
the loop starts), so a terminal_state reason_code could never actually
be emitted - dead code, not re-added here (§7's own removal note).

This module only defines data (the enum values and the admissible-code
table) - it does not enforce anything itself. The gate (src/rrx/agent/
gate.py) enforces §8's R1-R8, which operate on action_type/remedy/
subscription_state/decline_code, never on reason_code; reason_code
admissibility is audit-taxonomy bookkeeping, not a gate rule.
"""

from __future__ import annotations

REMEDY_MATCH_CARD = "remedy_match_card"
REMEDY_MATCH_TOPUP = "remedy_match_topup"
RETRY_WINDOW_OPEN = "retry_window_open"
POST_HALT_RESCUE = "post_halt_rescue"
ENGAGEMENT_OBSERVED = "engagement_observed"
NO_ENGAGEMENT_RESTRAINT = "no_engagement_restraint"
RISK_FLAGGED = "risk_flagged"

REASON_CODES: frozenset[str] = frozenset({
    REMEDY_MATCH_CARD,
    REMEDY_MATCH_TOPUP,
    RETRY_WINDOW_OPEN,
    POST_HALT_RESCUE,
    ENGAGEMENT_OBSERVED,
    NO_ENGAGEMENT_RESTRAINT,
    RISK_FLAGGED,
})

# Every decline_code (== EpisodeView.decline_code / configs/population.yaml
# opening_condition key, engine.py:379) sim-v1 can produce for an episode
# that reaches a day-loop tick at all. subscription_cancelled_by_customer
# is deliberately excluded - it is a population.yaml kind: subscription_state
# opening condition, not a decline_code, and never reaches a runner tick
# (§7, §20; configs/population.yaml:140-150).
ALL_DECLINE_CODES: frozenset[str] = frozenset({
    "insufficient_funds",
    "ambiguous_decline",
    "card_expired",
    "debit_instrument_blocked",
    "card_not_enabled_group",
    "bank_technical_error",
    "transaction_limit_exceeded",
    "payment_risk_check_failed",
})

# docs/A3-DESIGN.md §7's table, verbatim ("Admissible decline_code(s)" column).
ADMISSIBLE_DECLINE_CODES: dict[str, frozenset[str]] = {
    REMEDY_MATCH_CARD: frozenset({
        "card_expired", "debit_instrument_blocked", "card_not_enabled_group",
        "ambiguous_decline", "bank_technical_error",
    }),
    REMEDY_MATCH_TOPUP: frozenset({"insufficient_funds", "transaction_limit_exceeded"}),
    RETRY_WINDOW_OPEN: frozenset({
        "insufficient_funds", "bank_technical_error", "transaction_limit_exceeded",
    }),
    # §7: additionally requires subscription_state == "halted" - not
    # encoded here (this table is decline_code-keyed only) - and NOT
    # admissible for bank_technical_error, whose card_chargeable=True at
    # opening (SIM.md §2), unlike the other four codes here.
    POST_HALT_RESCUE: frozenset({
        "card_expired", "debit_instrument_blocked", "card_not_enabled_group",
        "ambiguous_decline",
    }),
    # "any except subscription_cancelled_by_customer" (§7) - ALL_DECLINE_CODES
    # already excludes it by construction (it is not a decline_code).
    ENGAGEMENT_OBSERVED: ALL_DECLINE_CODES,
    NO_ENGAGEMENT_RESTRAINT: ALL_DECLINE_CODES,
    RISK_FLAGGED: frozenset({"payment_risk_check_failed"}),
}

# §7's "Typical action" column - documentation only, not enforced by the
# gate (R1-R8 operate on the Proposal/EpisodeView directly, never via
# this table).
TYPICAL_ACTION: dict[str, str] = {
    REMEDY_MATCH_CARD: "CONTACT(card_change)",
    REMEDY_MATCH_TOPUP: "CONTACT(topup_reminder)",
    RETRY_WINDOW_OPEN: "WAIT",
    POST_HALT_RESCUE: "CONTACT(card_change)",
    ENGAGEMENT_OBSERVED: "CONTACT",
    NO_ENGAGEMENT_RESTRAINT: "WAIT",
    RISK_FLAGGED: "STOP",
}


def is_admissible(reason_code: str, decline_code: str) -> bool:
    """Whether `decline_code` may legitimately co-occur with `reason_code`
    per §7's table. Not called by the gate (see module docstring) - for
    tests and future A3-D/gate extensions."""
    return decline_code in ADMISSIBLE_DECLINE_CODES.get(reason_code, frozenset())
```

### `src/rrx/agent/ledger.py` (verbatim)

```python
"""The audit ledger (docs/A3-DESIGN.md §14) - one JSONL-serializable
record per tick.

`default_ledger_record` is a pure function: given the runner's per-tick
bookkeeping (episode_id, tick, tick_type, the EpisodeView used, the
Proposal if any, the gate's verdict if any, what actually executed, and
the pre/post budget), it constructs and returns a LedgerRecord with
every one of §14's fields populated per that table's Mandatory?/A3-D
columns. No I/O - persisting a run's records to results/<run_id>/
ledger.jsonl (§22) is run-orchestration infrastructure that does not
exist yet and is out of scope here; `to_json_line` is provided for when
it does.

No A3-LLM exists in this pass, so every LLM-only field
(prompt_hash, raw_output, latency_ms, tokens_in, tokens_out,
model_version, template_version) is always null, `fallback_reason` is
always null (no fallback mechanism exists yet), and `cost` is always
0.0 - "never omitted" per §17, matching A3-D's own applicability column.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from rrx.agent.gate import AGENT_SEND_HOUR, GateVerdict
from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """§14's 22-field per-tick record, in table order."""

    episode_id: str
    tick: int
    tick_type: str
    view_hash: str
    prompt_hash: str | None
    raw_output: str | None
    parsed_action: dict | None
    reason_code: str | None
    rationale: str | None
    gate_verdict: str | None  # "accept" | "reject" | None
    gate_rule_fired: str | None
    fallback_reason: str | None
    executed_action: dict | None
    budget_before: int
    budget_after: int
    send_hour: str | None
    latency_ms: float | None
    tokens_in: int | None
    tokens_out: int | None
    cost: float
    model_version: str | None
    template_version: str | None


def _hash_view(view: EpisodeView) -> str:
    """§14: "hash of the EpisodeView used". EpisodeView is a frozen
    dataclass with a deterministic repr (its only non-primitive field,
    contact_history, is a tuple of frozen ContactRecord dataclasses,
    also deterministically repr'd) - stable across calls for equal
    field values."""
    return hashlib.sha256(repr(view).encode("utf-8")).hexdigest()


def default_ledger_record(
    *,
    episode_id: str,
    tick: int,
    tick_type: str,
    view: EpisodeView,
    proposal: Proposal | None,
    gate_verdict: GateVerdict | None,
    executed_action: dict | None,
    budget_before: int,
    budget_after: int,
    contact_sent: bool,
) -> LedgerRecord:
    """Builds one §14 ledger record for a single day's tick. `proposal`/
    `gate_verdict` are None on non-wakeup ticks (§7: reason_code/
    gate_verdict/gate_rule_fired are wakeup-only). `send_hour` is stamped
    here, by the ledger (§9, §14), as the fixed `AGENT_SEND_HOUR`
    whenever `contact_sent` is True - never computed or chosen by the
    runner."""
    gate_verdict_str: str | None = None
    gate_rule_fired: str | None = None
    if gate_verdict is not None:
        gate_verdict_str = "accept" if gate_verdict.accepted else "reject"
        gate_rule_fired = gate_verdict.rule_fired

    return LedgerRecord(
        episode_id=episode_id,
        tick=tick,
        tick_type=tick_type,
        view_hash=_hash_view(view),
        prompt_hash=None,
        raw_output=None,
        parsed_action=asdict(proposal) if proposal is not None else None,
        reason_code=proposal.reason_code if proposal is not None else None,
        rationale=proposal.rationale if proposal is not None else None,
        gate_verdict=gate_verdict_str,
        gate_rule_fired=gate_rule_fired,
        fallback_reason=None,
        executed_action=executed_action,
        budget_before=budget_before,
        budget_after=budget_after,
        send_hour=AGENT_SEND_HOUR if contact_sent else None,
        latency_ms=None,
        tokens_in=None,
        tokens_out=None,
        cost=0.0,
        model_version=None,
        template_version=None,
    )


def to_json_line(record: LedgerRecord) -> str:
    """One §22 results/**/ledger.jsonl line. Not called by the runner in
    this pass - no run_id/results-directory infrastructure exists yet."""
    return json.dumps(asdict(record), sort_keys=True)
```

### `src/rrx/agent/null_policy.py` (verbatim)

```python
"""Day 4 foundation: a policy with zero intelligence.

Used only to exercise the A3 runner's execution path
(docs/A3-DESIGN.md Task 4A §3, §16's byte-identity proof). Always
proposes WAIT - no rule logic, no randomness, no LLM calls, no reading of
`view`. This is NOT A3-D (src/rrx/agent/policy.py, not implemented in
this pass) - deliberately kept in a separate module so it is never
mistaken for, or later expanded into, the real deterministic ablation.
"""

from __future__ import annotations

from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView

# Not one of docs/A3-DESIGN.md §7's 7 frozen reason_code values - this
# policy has no decision logic to justify any of those, and assigning one
# would fabricate a reason this policy does not have. The gate/ledger are
# no-op stubs in this pass (src/rrx/agent/gate.py, ledger.py), so nothing
# validates this value against the §7 enum yet; that validation is future
# gate work, out of scope for Task 4A.
NULL_POLICY_REASON_CODE = "null_policy_no_reasoning"


def null_policy(view: EpisodeView) -> Proposal:
    """Always WAIT. `view` is accepted (matching the real policy
    signature) but never inspected - this policy carries no logic to
    inspect it with."""
    return Proposal(
        action_type="WAIT",
        remedy=None,
        rationale="null_policy: always WAIT, no decision logic",
        reason_code=NULL_POLICY_REASON_CODE,
    )
```

### EpisodeView definition

**File:** `src/rrx/features/episode_view.py:67-86`.

```python
@dataclass(frozen=True, slots=True)
class EpisodeView:
    subscription_id: str
    subscription_state: str
    invoice_amount_inr: int

    days_since_first_failure: int
    auto_retries_remaining: int
    next_auto_retry_day: int | None

    decline_code: str

    billing_amount_inr: int

    contact_history: tuple[ContactRecord, ...]
    budget_remaining: int
```

**Field count: 10** (matches `SIM.md §10`'s stated "10 fields, not
EVAL.md §3.4's original 16").

**Where the allowlist is enforced:** `tests/test_no_latent_leak.py`,
three independent layers (full text read and reproduced in Section 1's
integrity check above, and again here since it directly answers this
question):
1. **Static** — AST import scan of every `.py` file under
   `GUARDED_PACKAGES = ("rrx/agent", "rrx/features")` for any import
   reaching `rrx.sim.latent` or `rrx.sim` (`test_no_forbidden_import_statement`).
2. **Runtime transitive** — imports `rrx.agent`/`rrx.features` in a clean
   subprocess and asserts `rrx.sim.latent` never lands in `sys.modules`
   (`test_no_transitive_latent_import`).
3. **Surface** — `EPISODE_VIEW_ALLOWED` (a 10-name set, byte-identical to
   the dataclass field list above) is asserted **set-equal** (not just
   "no extras") to `EpisodeView`'s actual `dataclasses.fields()`
   (`test_episode_view_field_set_equals_the_allowlist_exactly`), plus a
   separate "no latent field name" check against `LATENT_FIELD_NAMES`,
   plus field-type-token and frozen/slots structural checks
   (`test_episode_view_field_types_are_all_plain_observable_values`,
   `test_episode_view_and_contact_record_are_frozen`,
   `test_episode_view_and_contact_record_reject_arbitrary_new_attributes`).

### ContactRecord definition

**File:** `src/rrx/features/episode_view.py:52-64`.

```python
@dataclass(frozen=True, slots=True)
class ContactRecord:
    day: int
    channel: str
    remedy: str
    delivered: bool
    engaged: bool
```

**Field count: 5**, allowlisted separately as `CONTACT_RECORD_ALLOWED =
{"day", "channel", "remedy", "delivered", "engaged"}` in
`test_no_latent_leak.py` (checked because `ContactRecord` nests inside
`EpisodeView.contact_history`, invisible to a scan of `EpisodeView`'s own
field names).

### The ledger schema

`src/rrx/agent/ledger.py`'s `LedgerRecord` dataclass, **field count: 22**
(counted directly from the dataclass body, in declaration order — matches
the module's own docstring claim "§14's 22-field per-tick record"):

| # | Field | Type | Required? | Validation rule |
|---:|---|---|---|---|
| 1 | `episode_id` | `str` | always | none beyond type |
| 2 | `tick` | `int` | always | none beyond type |
| 3 | `tick_type` | `str` | always | none beyond type (not enum-checked in code — see gap note below) |
| 4 | `view_hash` | `str` | always | sha256 hex of `repr(view)` |
| 5 | `prompt_hash` | `str \| None` | optional | null unless A3-LLM |
| 6 | `raw_output` | `str \| None` | optional | null unless A3-LLM |
| 7 | `parsed_action` | `dict \| None` | wakeup-only | `asdict(proposal)` or `None` |
| 8 | `reason_code` | `str \| None` | wakeup-only | taken from `proposal.reason_code`, not independently validated against the 7-value enum here |
| 9 | `rationale` | `str \| None` | wakeup-only | taken from `proposal.rationale` |
| 10 | `gate_verdict` | `str \| None` | wakeup-only | `"accept"` \| `"reject"` \| `None` |
| 11 | `gate_rule_fired` | `str \| None` | if rejected | taken from `GateVerdict.rule_fired` |
| 12 | `fallback_reason` | `str \| None` | if fallback | always `None` in this pass (no fallback mechanism built) |
| 13 | `executed_action` | `dict \| None` | always | caller-supplied dict, no schema check in this module |
| 14 | `budget_before` | `int` | always | none beyond type |
| 15 | `budget_after` | `int` | always | none beyond type |
| 16 | `send_hour` | `str \| None` | if contact sent | fixed to `AGENT_SEND_HOUR` ("10:00") when `contact_sent=True`, else `None` |
| 17 | `latency_ms` | `float \| None` | optional | null unless A3-LLM |
| 18 | `tokens_in` | `int \| None` | optional | null unless A3-LLM |
| 19 | `tokens_out` | `int \| None` | optional | null unless A3-LLM |
| 20 | `cost` | `float` | always | `0.0` for A3-D, "never omitted" |
| 21 | `model_version` | `str \| None` | optional | null unless A3-LLM |
| 22 | `template_version` | `str \| None` | optional | null unless A3-LLM |

**Field count is 22, exactly as this file's own docstring claims — no
discrepancy found.**

### The proposal / action space

`Proposal.action_type ∈ {"CONTACT", "WAIT", "STOP"}` (3 legal values,
`src/rrx/agent/gate.py`'s `_VALID_ACTION_TYPES`); `remedy ∈
{"card_change", "topup_reminder", None}` (required iff `action_type ==
"CONTACT"`, per the design doc — **not** enforced as a hard constraint by
the `Proposal` dataclass itself, which types `remedy: str | None` with no
validation). `escalate_to_merchant` is not a fourth action type — folded
into `STOP` + `reason_code=risk_flagged` per `A3-DESIGN.md §1/§6/§7`.
`hold_service_delivery` and `send_subscription_link` are excluded from
the v1 action space entirely (`SIM.md §3/§9`) and have no representation
anywhere in `Proposal`.

### The gate: every rule ID and what each rejects

(From `src/rrx/agent/gate.py`, verbatim above, cross-checked against
`docs/A3-DESIGN.md §8`'s table and `tests/test_gate_rules.py`, which was
opened and confirmed to have one reject-test and one accept-test per rule
for R1–R6 and R8; R7 has no dedicated `test_gate_rules.py` case — it is
described in both EVAL.md and A3-DESIGN.md as a **structural** guarantee
of the runner producing exactly one ledger record per tick, not a
predicate the gate function evaluates.)

| Rule | Rejects |
|---|---|
| R1 | `action_type` not in `{"CONTACT","WAIT","STOP"}` |
| R2 | `CONTACT` when `subscription_state ∈ {"cancelled","expired"}` |
| R3 | `CONTACT` with `remedy=="card_change"` when `decline_code ∈ {"insufficient_funds","transaction_limit_exceeded"}` |
| R4 | `CONTACT` when `decline_code == "payment_risk_check_failed"` |
| R5 | `CONTACT` when `view.budget_remaining <= 0` |
| R6 | any action when `send_hour` falls outside `"09:00"–"21:00"` (string-compared) |
| R7 | (not gate-evaluated — runner-structural: one ledger record per tick) |
| R8 | `CONTACT` when `decline_code` not in `ALL_DECLINE_CODES` (the 8-code frozenset in `reason_codes.py`) |

Precedence, exactly as implemented (matches `A3-DESIGN.md §8`'s stated
"R2, R4 → R3 → R1, R8 → R5, R6"): checked in the order **R2, R4, R3, R1,
R8, R5, R6** — first match wins.

### Is every legal proposal guaranteed to have a legal executor mapping?

**UNENFORCED.** Read `src/rrx/harness/runner.py`'s step-6 executor block
(full text in Section 8 below) directly: it branches on
`gate_verdict.accepted and proposal.action_type == "CONTACT" and
proposal.remedy == "card_change"`, then the `topup_reminder` equivalent,
then `action_type == "STOP"`, and an `else` branch that treats
**everything else** — including a **gate-accepted** `CONTACT` proposal
whose `remedy` is `None` or any value other than the two known
strings — as if it were `WAIT` (`executed_action = {"action_type":
"WAIT"}`). Nothing in `evaluate_gate()` (§8's R1–R8 above) rejects a
`CONTACT` proposal with `remedy=None` or an unrecognized `remedy` string
— R1 only checks `action_type`, R3/R4/R2/R5/R6/R8 never inspect
`remedy`'s value except R3's specific `== "card_change"` check. So a
`Proposal(action_type="CONTACT", remedy=None, ...)` (or
`remedy="something_else"`) passes the gate as **accepted**, is recorded
in the ledger with `gate_verdict="accept"`, and is then **silently
executed as WAIT** by the runner — a real mismatch between what the gate
certified and what actually happened, with no test found in this pass
(`tests/test_gate_rules.py`, `tests/test_a3_runner_parity.py`) that
exercises this specific case. Flagged here as an implementation gap, not
fixed (out of scope for a read-only inspection).
---

## 8. RUNNER / EVALUATION INFRASTRUCTURE

The batch's requested path `src/rrx/harness/runner.py` and
`src/rrx/harness/splits.py` both exist (unlike the literal path the
instructions gave — no case mismatch, no relocation needed).

### `src/rrx/harness/runner.py` (verbatim)

```python
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
TERMINAL_SUBSCRIPTION_STATES = frozenset({"cancelled", "expired"})

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
```

### `src/rrx/harness/splits.py` (verbatim)

```python
"""dev / holdout / stress split definitions (EVAL.md §3.5, restored
verbatim in eval-spec-v1.4).

Not a guarded package - this is harness bookkeeping, not agent logic, and
holds no rrx.sim import regardless. Cross-checked against
rrx.sim.run_stage3.EPISODE_INDICES (range(1000, 3000)) and
tests/test_stage5_falsification.py's INDICES, per EVAL.md §3.5's own
cross-check note.

Holdout must never run accidentally: EVAL.md §3.5 - "Once per candidate
release", every run (successful or not) logged in
results/holdout_runs.md. `holdout_indices()` requires an explicit
`authorized=True` to return anything, rather than exposing the range as
a plain module-level constant that any caller could iterate without
thinking.
"""

from __future__ import annotations

DEV_SPLIT = "dev"
DEV_SEED_START = 1000
DEV_N = 2000
DEV_INDICES = range(DEV_SEED_START, DEV_SEED_START + DEV_N)  # 1000-2999

HOLDOUT_SPLIT = "holdout"
HOLDOUT_SEED_START = 9000
HOLDOUT_N = 2000
_HOLDOUT_INDICES = range(HOLDOUT_SEED_START, HOLDOUT_SEED_START + HOLDOUT_N)  # 9000-10999

STRESS_SPLIT = "stress"
STRESS_SEED_START = 5000
STRESS_N = 300
STRESS_INDICES = range(STRESS_SEED_START, STRESS_SEED_START + STRESS_N)  # 5000-5299


class HoldoutNotAuthorizedError(RuntimeError):
    """Raised when holdout indices are requested without explicit
    authorization. Do not catch-and-retry this with authorized=True
    unless the user has actually authorized a holdout run."""


def dev_indices() -> range:
    return DEV_INDICES


def stress_indices() -> range:
    return STRESS_INDICES


def holdout_indices(*, authorized: bool = False) -> range:
    """EVAL.md §3.5: holdout runs 'once per candidate release', and every
    run - successful or not - must be logged in results/holdout_runs.md.
    This is the only way this module exposes the holdout index range;
    callers must pass authorized=True deliberately, never as a default."""
    if not authorized:
        raise HoldoutNotAuthorizedError(
            "Holdout split access requires authorized=True. EVAL.md §3.5: holdout "
            "runs once per candidate release, and every run (successful or not) "
            "must be logged in results/holdout_runs.md. Do not set authorized=True "
            "without the user's explicit go-ahead for a real holdout run."
        )
    return _HOLDOUT_INDICES
```

### Located components, or MISSING

- **`run_episode()` entry point and `_POLICIES` registry (existing arms,
  not A3):** `src/rrx/sim/engine.py:330-333`:
  ```python
  _POLICIES: dict[str, Callable[[str, int, str], str | None]] = {
      "A0": a0_action_for_day,
      "A2": a2_action_for_day,
  }
  ```
  **Only `A0` and `A2` (A2-original) are registered.** `a2_action_for_day`
  is defined at `engine.py:275-327`; `a0_action_for_day` is defined at
  `engine.py:275`'s neighboring block (line 275 itself is
  `a0_action_for_day`'s signature per the grep hit). **No `A1`, `A1-U`, or
  `A4` policy function exists anywhere in `src/rrx/sim/engine.py`** —
  grepping the whole file for `a1_action_for_day`/`a4_action_for_day`
  returns nothing. `A1`/`A4` are instead constructed **ad hoc, test-local**
  in `tests/test_stage5_falsification.py` (per that file's own module
  docstring reference and `src/rrx/baselines/a2_variants.py`'s docstring,
  which says new arm keys "can be registered into
  `rrx.sim.engine._POLICIES` at runtime... the same way
  `tests/test_stage5_falsification.py` already registers 'A1'"). A2's two
  Day-3 variants (`A2-corrected-v1`, `A2-strengthened`) live in
  `src/rrx/baselines/a2_variants.py` (dumped below) and are likewise
  **not** registered into `_POLICIES` by any non-test code — only tests
  register them at runtime.
- **`RunManifest`:** `src/rrx/spec/manifest.py` — path exists, full
  11-field schema (`git_sha, spec_version, config_hash, seed, arm,
  regime, sweep_cell, model_version, timestamp, wall_clock_seconds,
  llm_cost_inr`) matching `EVAL.md §6`'s eleven-field list exactly. Its
  own docstring states plainly: "no A3/evaluation harness exists yet to
  wire this into" — **confirmed**: no other file in the repository
  imports or calls `write_manifest`/`RunManifest`/`current_git_sha`
  outside its own module. **RUNMANIFEST: DEFINED BUT NEVER INVOKED —
  no run in this repository produces a `manifest.json`.**
- **Metrics computation module(s):** MISSING as a standalone,
  reusable module — searched `Glob **/metrics*.py`, `Grep
  "invoice_recovery_rate\s*="`. The only place recovery/rescue rates and
  contact counts are actually computed is ad hoc, inline code inside
  `tests/test_stage5_falsification.py` and the two `diagnostics/*.py`
  scripts (`day3_diagnostic.py`, `day3_baseline_headroom.py`) — none of
  these are importable, documented public APIs.
- **Statistics — paired comparison / bootstrap / CI:** `paired_bootstrap_ci`
  lives in `src/rrx/sim/run_stage3.py:46-73` (module docstring: "Day 2
  Stage 3: the first reproducible A0-vs-A2 result... No manifest, no
  results directory, no formatting infrastructure - prints a plain
  report to stdout. Run with: `python -m rrx.sim.run_stage3`"). Its
  defaults (`N_BOOTSTRAP_RESAMPLES = 10_000`, `CI_LEVEL = 0.95`) match
  `EVAL.md §6`'s "10,000 resamples... 95% CI" exactly. **This is a
  one-off Day-2 diagnostic script, not a supported/reusable harness
  statistics API** — `tests/test_stage5_falsification.py` imports this
  same function directly from `rrx.sim.run_stage3` and, in that specific
  test, overrides `n_resamples=5000` for its own falsification-check
  speed (confirmed in this pass's `pytest -q` output, e.g. `d_10, lo_10,
  hi_10 = paired_bootstrap_ci(a0_inv, a1_inv, n_resamples=5000)`) — the
  canonical 10,000-resample default is unaffected by this, but no
  dedicated `rrx.harness`-namespaced statistics module exists.
- **Sweep infrastructure:** `src/rrx/spec/registry.py` (dumped in full
  below) implements `enumerate_cells()` — the one-at-a-time grid builder
  consuming `configs/model_params.yaml` — and is exercised by
  `tests/test_model_params_swept.py`/`test_failure_mix_simplex.py`. It
  produces `Cell` objects (22 of them per `results/sensitivity.md`'s own
  count) but **nothing in the repository actually runs an arm against
  each cell and writes results** — `results/sensitivity.md` (dumped
  below, §6) is 100% `PENDING` for all 22 cells.
- **CLI entry points:** **MISSING entirely.** Searched
  `pyproject.toml` (`[project]` block has no `[project.scripts]`/
  `console_scripts` table), grepped the whole repo (excluding `.venv`)
  for `ArgumentParser|add_argument` — zero hits outside third-party
  packages in `.venv`. `Makefile`'s `eval`/`sweep` targets invoke
  `python -m rrx.eval.runner` / `python -m rrx.eval.runner --sweep` —
  **`rrx.eval` does not exist anywhere in `src/rrx/`** (confirmed via
  `python -c "import rrx.eval.runner"` → `ModuleNotFoundError: No module
  named 'rrx.eval'`, run with `src` on `sys.path`). **No `--allow-live`
  flag exists anywhere** (mentioned only in prose, `docs/A3-DESIGN.md
  §13` and `EVAL.md §6A`) — no CLI parses it. **No split-selection flag**
  exists either; `src/rrx/harness/splits.py`'s functions are the only
  split-selection surface, and they are plain Python functions, not
  CLI-exposed.

### `src/rrx/baselines/a2_variants.py` (verbatim, 111 lines)

```python
"""A2 baseline variants — Day 3 approved corrections/strengthening.

DELIBERATELY OUTSIDE `src/rrx/sim/`: sim-v1 (commit
bbfa55d68a97ca9f41a9b151477b193db5054ffe) freezes `src/rrx/sim/` including
`engine.py`'s `a2_action_for_day` (the "A2-original" policy). This module
does not import, monkeypatch, or otherwise mutate anything in `rrx.sim` -
it defines two NEW policy callables with `rrx.sim.engine`'s own
`(opening_condition_key, day, subscription_state) -> action | None`
interface, delegating to `engine.a2_action_for_day` for every branch that
is unchanged. They can be registered into `rrx.sim.engine._POLICIES` at
runtime under new arm keys (e.g. "A2_CORRECTED_V1", "A2_STRENGTHENED") the
same way `tests/test_stage5_falsification.py` already registers "A1" -
`engine.py`'s source is never touched, and the existing "A0"/"A2" keys
(A2-original) are never overwritten, so A2-original stays reproducible
under its own name.

Four independently-justified changes vs `engine.a2_action_for_day`, kept
distinct per the Day 3 review's explicit instruction not to blur
correction and strengthening rationales:

1. Card-broken bucket (`card_expired`, `debit_instrument_blocked`,
   `card_not_enabled_group`): second card_change contact moves T+5 -> T+3
   ["CORRECTION" — `a2_corrected_v1_action_for_day` and
   `a2_strengthened_action_for_day` both apply this]. Justified purely by
   EVAL.md §1.1/§1.3 ("auto-retries T+1...T+3" / "invoice recovery... only
   possible while auto-retries remain") plus `episode.yaml`'s own
   `halt_boundary_day: 3` - a T+5 contact for this bucket's invoice-
   relevant remedy is scheduled at a day the frozen simulator's own
   boundary makes structurally invoice-irrelevant, independent of any
   comparison to A1/A4.

2. Card-broken bucket: T+5 restored as a THIRD contact (T+0/T+3/T+5)
   ["STRENGTHENING", `a2_strengthened_action_for_day` only]. Not a
   correction of (1) - a deliberate use of the 3rd budget slot
   (`episode.yaml#/agent_budget/max_contacts_per_episode: 3`) for a
   post-halt rescue attempt. `episode.yaml#/payment_method_change_effect/
   while_halted` already names `subscription_rescued` as a reachable
   outcome, and `engine.py`'s existing (unmodified) post-halt-rescue block
   fires for exactly this bucket, since `card_chargeable_at_opening=False`
   for all three card-broken keys. Day 3 diagnostic measured a real
   rescue-rate gain from this addition with zero invoice-recovery cost.

3. `bank_technical_error`: the T+5 card_change contact is now guarded by
   `subscription_state in ("pending", "halted")` ["CORRECTION" - both
   variants]. This restores, verbatim, a conditional clause
   ("card-change prompt at T+5 if still failing") that was present in the
   EVAL.md §4 text committed before commit 337e0060e9f5af013e4b8362623a0
   4e57a8f3f66101d deleted §4 - `engine.a2_action_for_day`'s existing
   implementation dropped this guard, and since `blocked_until` for this
   condition is always <= 2 (episode.yaml's `bank_technical_error_
   clearance` support is `[0, 2]`, retry_days include day 2), recovery is
   *always* already resolved before day 5, so the unguarded version sends
   a guaranteed-useless contact 100% of the time (confirmed empirically
   on the dev cohort: 51/51 bank_technical_error episodes). This is a
   restoration of previously-written intent, not new design.

4. `transaction_limit_exceeded`: the T+5 card_change fallback is removed
   entirely, leaving only the T+1 topup_reminder ["CORRECTION" - both
   variants]. `latent.py`'s `_MECHANISM_ISOLATED_KEYS` branch draws
   `card_chargeable=True` at opening for this condition, identically to
   `insufficient_funds` - `_apply_card_naming_effect` is therefore an
   equally guaranteed no-op here, which is exactly the situation EVAL.md
   §5.2's remedy-match gate ("Card-change prompts for insufficient_funds:
   0") already exists to prevent. The gate's literal text names only
   `insufficient_funds`; this widens the same underlying principle to the
   mechanically identical condition, rather than leaving an inconsistent
   carve-out. `blocked_until=BLOCKED_INDEFINITELY` means the invoice can
   never recover in-window regardless of this fallback either way, so the
   change affects only wasted-contact accounting, never the invoice/
   rescue metrics (confirmed empirically: 0% for this condition under
   every arm tested).

All other opening conditions (`insufficient_funds`, `ambiguous_decline`,
`subscription_cancelled_by_customer`, `payment_risk_check_failed`) are
untouched and delegate to `engine.a2_action_for_day` unchanged.
"""

from __future__ import annotations

from rrx.sim import engine


def a2_corrected_v1_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """A2-original with changes (1), (3), (4) above. Same contact COUNT as
    A2-original for the card-broken bucket (2 contacts, just retimed)."""
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3) else None

    if opening_condition_key == "bank_technical_error":
        if day == 5 and subscription_state in ("pending", "halted"):
            return "card_change"
        return None

    if opening_condition_key == "transaction_limit_exceeded":
        return "topup_reminder" if day == 1 else None

    return engine.a2_action_for_day(opening_condition_key, day, subscription_state)


def a2_strengthened_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """a2_corrected_v1_action_for_day PLUS change (2): the card-broken
    bucket's third, post-halt rescue-only contact at T+5. Uses the full
    3-contact budget for that bucket; every other condition is identical
    to a2_corrected_v1_action_for_day."""
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3, 5) else None
    return a2_corrected_v1_action_for_day(opening_condition_key, day, subscription_state)
```

### `configs/model_params.yaml` (verbatim)

```yaml
# configs/model_params.yaml
# Canonical registry of [MODEL] parameters for EVAL.md.
#
# This file is the SINGLE SOURCE OF TRUTH for:
#   - how many [MODEL] parameters exist
#   - what scalar handle each one is swept on
#   - what the baseline and sensitivity cells are
#
# It does NOT hold the distributions themselves. Those live in
# population.yaml / episode.yaml and are referenced by owner_path.
# tests/test_model_params_registry.py enforces that every pointer resolves.
#
# EVAL.md sections are generated FROM this file by `make docs`.
# Do not hand-edit the §8.2 table.

spec_version: eval-spec-v1-draft
eval_section: "8.2"

sweep:
  method: one_at_a_time          # locked decision 2
  split: dev                     # locked decision 1 - HOLDOUT is never swept
  default_magnitude: 0.30        # locked decisions 3, 6, 9, 10
  directions: [low, high]
  probability_clamp: [0.0, 1.0]  # locked decision 10
  record_clamping: true          # locked decision 10
  win_criterion:
    # locked decision 4
    metrics: [invoice_recovery_rate, subscription_rescue_rate]
    require: all                 # BOTH metrics, not either
    test: paired_bootstrap_95ci_excludes_zero
    comparator: A2
  majority_threshold: 0.80       # locked decision 5
  rounding: ceil                 # ceil(0.80 * 22) = 18
  frozen_policies: [A2, A3-D, A3-LLM]  # locked decision 14 - no per-cell
    # retuning. AMENDED eval-spec-v1.4: "A3" split into its two
    # pre-registered named arms (EVAL.md §4.2). win_criterion.comparator
    # above is UNCHANGED (A2).
  common_random_numbers:
    enabled: true                # locked decision 14
    # DEFECT 6 FIX: naive shared streams mean perturbing one parameter
    # reshuffles every downstream draw, which destroys the OAT comparison.
    # Each latent variable draws from its own named substream so that
    # changing parameter X only changes X's realisations.
    substream_isolation: per_variable
    substreams:
      - invoice_amount
      - failure_condition
      - balance_restore
      - topup_acceleration
      - channel_response
      - card_change_completion
      - cancellation_hazard
      - remaining_lifetime

  # DEFECT 1: p_topup_action is an invented [MODEL] number introduced by
  # locked decision 12 but not given a sweep row. Leaving it unswept
  # violates EVAL.md §0. Your locked cell count is 22, so this defaults
  # to false and the parameter is declared un-swept and low-confidence.
  # Flip to true for 24 cells / threshold 20. REQUIRES HUMAN DECISION.
  include_topup_acceleration_cells: false

# ---------------------------------------------------------------------------
# The six parameters. Exactly six. IDs are canonical and match EVAL.md §8.2
# verbatim; tests/test_model_params_registry.py asserts the set equality.
# ---------------------------------------------------------------------------

parameters:

  invoice_amount:
    eval_section: "3.1"
    status: specified
    provenance: invented_synthetic     # NOT observed Razorpay statistics
    kind: distribution
    owner_path: "population.yaml#/invoice_amount_inr"
    regime: [B, A]
    handle:
      name: median_inr
      transform: multiplicative
      baseline: 2000                   # locked decision 6
      held_fixed:
        sigma: 1.0
        support: [100, 50000]
    sweep:
      swept: true
      magnitude: 0.30
      cells:
        low:  1400
        high: 2600

  failure_mix_weights:
    eval_section: "3.2"
    status: specified
    provenance: invented_synthetic
    kind: vector_simplex
    owner_path: "population.yaml#/failure_mix"
    regime: [B, A]
    definition:
      # Q1 gap resolution (2026-08-26, eval-spec-v1.1). Not a new bucket and
      # not a seventh [MODEL] family - folds into the existing "ambiguous"
      # bucket below (bucket_mass perturbation), but is INDEPENDENTLY swept
      # in its own right: it is a [MODEL] magnitude in its own right, not a
      # fixed within-bucket ratio, and EVAL.md §0 requires every [MODEL]
      # magnitude to reach the sweep grid.
      # DEFECT (2026-08-26): this entry was originally marked
      # sweep_required: true with no sweep.cells, so it silently contributed
      # zero cells to enumerate_cells(). test_model_params_swept did not
      # catch it because it only checked top-level handles, never anything
      # nested inside definition:. Fixed here; see
      # tests/test_model_params_swept.py::test_all_sweep_required_entries_produce_cells.
      ambiguous_cause_split:
        p_card_cause: 0.50
        basis: project_inference
        rationale: >
          Maximum entropy over two causes. The code is ambiguous by
          construction and no signal distinguishes them. Near arm-neutral:
          A3 and A2 both see only decline_code for this bucket.
        owner_path: "population.yaml#/opening_conditions (ambiguous_decline entry)"
        sweep_required: true
        sweep:
          magnitude: 0.30
          handle: p_card_cause
          cells:
            low: 0.35
            high: 0.65
    handle:
      name: bucket_mass
      transform: multiplicative
      projection: renormalise_across_buckets   # locked decision 3
      preserve_within_bucket_ratios: true      # locked decision 3
      buckets:
        card_change:
          baseline: 0.34
          members: [card_expired, debit_instrument_blocked, card_not_enrolled]
          low_information: false
        balance:
          baseline: 0.32
          members: [insufficient_funds]
          low_information: false
        ambiguous:
          baseline: 0.24
          members: [card_declined_or_payment_failed]
          low_information: false
        wait:
          baseline: 0.04
          members: [bank_technical_error, transaction_limit_exceeded]
          low_information: true    # locked decision 13 - swept, kept in denominator
        no_contact:
          baseline: 0.05
          members: [subscription_cancelled]
          low_information: false
        escalate:
          baseline: 0.01
          members: [payment_risk_check_failed]
          low_information: true    # locked decision 13
    sweep:
      swept: true
      magnitude: 0.30
      cells_per_bucket: 2
      invariants: [sums_to_one, non_negative, within_bucket_ratios_preserved]

  balance_restore_timing:
    eval_section: "3.3"
    status: specified
    provenance: invented_synthetic     # locked decision 11 - label explicitly
    kind: mixture_distribution
    owner_path: "episode.yaml#/latent/balance_restore_delay"
    regime: [B, A]
    definition:
      # locked decision 11
      components:
        transient:
          weight: 0.45
          dist: truncated_exponential
          mean_days: 2.0
          support_days: [0, 30]
        salary_cycle:
          weight: 0.55
          dist: days_until_next_salary_day
          salary_day_pmf: {1: 0.55, 7: 0.20, 25: 0.10, 30: 0.15}
          jitter:
            dist: gamma
            shape: 2
            mean_days: 1.0
      # locked decision 12 - invented synthetic causal mechanism.
      # NOT a Razorpay fact. See DEFECT 1 above re: sweep coverage.
      topup_acceleration:
        p_topup_action: 0.35
        accelerated_delay:
          dist: exponential
          mean_days: 0.5
          rule: "min(original_delay, t_engage + draw)"
        precondition: "engagement occurs strictly before next auto-retry"
        provenance: invented_synthetic
        swept: false                   # <-- DEFECT 1: see toggle above
        confidence: low
      # Q1 gap resolution (2026-08-26, eval-spec-v1.1). Not a seventh
      # [MODEL] family - folds into transient resolution timing alongside
      # the components mixture above, but is INDEPENDENTLY swept: it is a
      # [MODEL] magnitude in its own right, not a fixed component of the
      # balance_restore_delay mixture above.
      # DEFECT (2026-08-26): this entry was originally marked
      # sweep_required: true with no sweep.cells, so it silently contributed
      # zero cells to enumerate_cells(). Fixed here; see
      # tests/test_model_params_swept.py::test_all_sweep_required_entries_produce_cells.
      transient_block_clearance:
        provenance: invented_synthetic
        dist: uniform
        support_days: [0, 2]
        applies_to: bank_technical_error
        rationale: >
          EVAL 3.2 states the correct remedy is "wait - auto-retry likely
          resolves it". Requires clearance inside the retry window.
          P(clear before T+1) = 0.5, P(clear before T+2) = 1.0.
        owner_path: "episode.yaml#/latent/bank_technical_error_clearance"
        sweep_required: true
        sweep:
          magnitude: 0.30
          handle: support_days_upper_bound
          cells:
            low: [0, 1.4]
            high: [0, 2.6]
    handle:
      name: salary_mode_mass
      transform: multiplicative
      baseline: 0.55
      held_fixed: [transient_mean_days, salary_day_pmf, jitter]
      projection: renormalise_two_component_mixture
    sweep:
      swept: true
      magnitude: 0.30
      cells:
        low:  0.385
        high: 0.715

  channel_response_propensity:
    eval_section: "3.3"
    status: specified
    provenance: invented_synthetic
    kind: latent_field
    owner_path: "episode.yaml#/latent/channel_response_propensity"
    regime: [B, A]
    definition:
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
        form: "0.80 ** prior_contacts_in_episode"
        base: 0.80
      tenure_coupling:
        form: "logit(theta_c) += beta * z(customer_tenure_days)"
        beta: 0.35
      # DEFECT 4 FIX: the tenure logit shift means the REALISED population
      # mean is not exactly the Beta mean parameter. The handle addresses
      # the Beta parameter; the realised mean is recorded per run.
      handle_addresses: beta_mean_parameter
      record_realised_mean: true
      clamp: [0.0, 1.0]
    handle:
      name: trait_mean
      transform: multiplicative
      baseline: 0.28
      held_fixed: [concentration, channel_multipliers, fatigue_base, tenure_beta]
    sweep:
      swept: true
      magnitude: 0.30
      cells:
        low:  0.196
        high: 0.364

  card_change_completion_propensity:
    eval_section: "3.3"
    status: specified
    provenance: invented_synthetic
    kind: latent_field
    owner_path: "episode.yaml#/latent/card_change_completion_propensity"
    regime: [B, A]
    definition:
      dist: beta
      parameterisation: mean_concentration
      mean: 0.55
      concentration: 6
      conditional_on: engagement_with_card_change_prompt
      # Deliberately uncorrelated with every EpisodeView signal, so that
      # no fourth source of A3 advantage exists beyond the three
      # pre-registered in EVAL.md §3.4.
      independent_of_visible_signals: true
      clamp: [0.0, 1.0]
    handle:
      name: completion_mean
      transform: multiplicative
      baseline: 0.55
      held_fixed: [concentration]
    sweep:
      swept: true
      magnitude: 0.30
      cells:
        low:  0.385
        high: 0.715

  cancellation_hazard_and_ltv:
    eval_section: "3.3"
    status: specified
    provenance: invented_synthetic
    kind: composite
    owner_path: "episode.yaml#/latent/cancellation"
    # locked decision 8: hazard is a WORLD MECHANIC and can change
    # subscription_state, therefore it affects Regime-B rescue outcomes.
    # LTV remains Regime-A-only pricing.
    regime: [B, A]
    regime_split:
      hazard: world_mechanic          # affects Regime B
      ltv: regime_a_pricing_only
    definition:
      hazard_per_contact:
        form: "clamp(h0 * gamma ** (n - 1), 0, 1)"
        h0: 0.010
        gamma: 1.5
        n: contact_index_within_episode
        cumulative_over_3_contacts: 0.0460
        # DEFECT 5 FIX: EVAL.md §1.2 says Razorpay's automatic failure
        # email is part of the world, not a contact. It therefore carries
        # NO hazard, and arm A0 has exactly zero cancellation hazard.
        applies_to_razorpay_auto_email: false
      remaining_lifetime_cycles:
        # locked decision 7 - a COMPONENT, not a seventh parameter
        dist: geometric
        mean_cycles: 9
        valued_at: billing_amount_inr
        regime: [A]
    handle:
      name: joint_multiplier         # locked decision 9
      transform: multiplicative
      baseline: 1.0
      applies_to: [hazard_h0, remaining_lifetime_mean_cycles]
      # Scaling both together moves cancellation PROBABILITY and COST
      # per cancellation in the same direction, so the Regime-A term
      # moves ~quadratically while Regime-B rescue moves ~linearly.
      # This is a pessimistic/optimistic axis, not a clean +-30% on one
      # quantity. Stated here so it is not read as such.
      axis_semantics: joint_pessimistic_optimistic
    sweep:
      swept: true
      magnitude: 0.30
      cells:
        low:
          hazard_h0: 0.007
          remaining_lifetime_mean_cycles: 6.3
        high:
          hazard_h0: 0.013
          remaining_lifetime_mean_cycles: 11.7
```

**The six `[MODEL]` parameters and their `sweep_required`/`swept` flags**
(the file's top-level per-parameter `sweep.swept` flag — the deprecated
`sweep_required` key EVAL.md §0 mentions survives only as a nested,
per-sub-magnitude flag inside two parameters' `definition:` blocks, per
the file's own DEFECT comments):

| Parameter | top-level `sweep.swept` | nested `sweep_required: true` sub-magnitudes |
|---|---|---|
| `invoice_amount` | `true` | none |
| `failure_mix_weights` | `true` | `ambiguous_cause_split` (`p_card_cause`) |
| `balance_restore_timing` | `true` | `transient_block_clearance`; **`topup_acceleration` is `swept: false`, `confidence: low`** (excluded unless `sweep.include_topup_acceleration_cells` is flipped to `true`, currently `false`) |
| `channel_response_propensity` | `true` | none |
| `card_change_completion_propensity` | `true` | none |
| `cancellation_hazard_and_ltv` | `true` | none |

### How episodes are selected and seeds passed

`split` + `i` (integer episode index) are the only two inputs; both
`rrx.sim.engine.run_episode()` and `rrx.harness.runner.run_episode_a3()`
derive everything else (cohort draw, latent draw) from
`sample_cohort_episode(split, i, population_cfg, master_seed)` and
`draw_latent_state(split, i, opening_condition_key, episode_cfg,
population_cfg, master_seed)` — both keyed by `(split, i)` against the
fixed `MASTER_SEED` (re-exported from `rrx.sim.latent` through
`rrx.sim.engine`), giving CRN identity across arms per `EVAL.md §6`.
`i` ranges are supplied externally by `src/rrx/harness/splits.py`'s
`dev_indices()`/`stress_indices()`/`holdout_indices(authorized=...)`.

### How an arm is selected

For the existing (non-A3) arms: a string key (`"A0"`, `"A2"`, ...) looked
up in `rrx.sim.engine._POLICIES` (only `A0`/`A2` registered by default,
per above) and passed as the `policy` argument to `run_episode()`. For
A3: the caller passes a Python **callable** (`policy: PolicyFn =
Callable[[EpisodeView], Proposal]`) directly into `run_episode_a3()` —
there is no string-keyed A3 arm registry; `null_policy` (the only
callable that currently exists) is imported and passed explicitly by
`tests/test_a3_runner_parity.py`.

### Where in the loop the gate is invoked

`run_episode_a3()`, step 5, inside the `if tick_type == TICK_WAKEUP:`
block, immediately after the policy call and before the executor
(`gate_verdict = gate(proposal, view)`) — never called on
`no_wakeup`/`budget_exhausted`/`terminal_suppressed` ticks (no proposal
exists to gate on those ticks).

### What currently happens to an unmappable/rejected proposal

A **gate-rejected** proposal (`gate_verdict.accepted == False`, any
`action_type`) falls into the runner's final `else` branch and is
executed as `{"action_type": "WAIT"}` — no state mutation, no contact
sent, no budget consumed. An **accepted** proposal whose `action_type`/
`remedy` combination the runner's `elif` chain does not recognize
(see §7's UNENFORCED finding above) falls into the **same** `else`
branch and is likewise silently treated as WAIT, despite having been
gate-accepted — this is the one identified gap in the pipeline's
"proposal → gate verdict → executed action" contract.

### Where results are written today

**Nowhere, structurally.** No file in the repository writes to a
`results/<run_id>/` directory as part of normal execution.
`rrx.spec.manifest.write_manifest()` can write `manifest.json` if a
caller supplies `results_dir` explicitly (never defaulted to the real
`results/` tree, by the module's own design — see its docstring), but no
caller does. `rrx.agent.ledger.to_json_line()` similarly exists but is
never called by the runner. `rrx.sim.run_stage3` prints a plain report to
stdout only ("No manifest, no results directory, no formatting
infrastructure"). The only file that physically exists under `results/`
is the hand/`make docs`-generated `results/sensitivity.md`, checked into
git (dumped in Section 9 below).
---

## 9. DEV / HELDOUT SPLIT & OUTPUT POLICY

### How dev vs held-out is represented in code

`src/rrx/harness/splits.py` (full text dumped in Section 8 above). Quoted
constants:

```python
DEV_SPLIT = "dev"
DEV_SEED_START = 1000
DEV_N = 2000
DEV_INDICES = range(DEV_SEED_START, DEV_SEED_START + DEV_N)  # 1000-2999

HOLDOUT_SPLIT = "holdout"
HOLDOUT_SEED_START = 9000
HOLDOUT_N = 2000
_HOLDOUT_INDICES = range(HOLDOUT_SEED_START, HOLDOUT_SEED_START + HOLDOUT_N)  # 9000-10999
```

Note `_HOLDOUT_INDICES` is name-mangled with a leading underscore — not
importable/iterable directly from outside the module; only reachable
through the guarded `holdout_indices(authorized=...)` function below.

### Guard against accidental holdout execution

**YES — quoted directly:**

```python
class HoldoutNotAuthorizedError(RuntimeError):
    """Raised when holdout indices are requested without explicit
    authorization. Do not catch-and-retry this with authorized=True
    unless the user has actually authorized a holdout run."""


def holdout_indices(*, authorized: bool = False) -> range:
    """EVAL.md §3.5: holdout runs 'once per candidate release', and every
    run - successful or not - must be logged in results/holdout_runs.md.
    This is the only way this module exposes the holdout index range;
    callers must pass authorized=True deliberately, never as a default."""
    if not authorized:
        raise HoldoutNotAuthorizedError(
            "Holdout split access requires authorized=True. EVAL.md §3.5: holdout "
            "runs once per candidate release, and every run (successful or not) "
            "must be logged in results/holdout_runs.md. Do not set authorized=True "
            "without the user's explicit go-ahead for a real holdout run."
        )
    return _HOLDOUT_INDICES
```

`authorized` defaults to `False`, forcing an explicit, deliberate
`authorized=True` at every call site — there is no plain module-level
constant a caller could iterate over without thinking (the guard's own
docstring states this design intent directly). This guard is
**code-level only** — it does not itself write to
`results/holdout_runs.md` (that file does not exist, see below); it only
prevents *silent* accidental access to the index range.

### `.gitignore` (verbatim)

```
# Virtual environment
.venv/

# Python cache
__pycache__/
*.py[cod]

# Build artefacts (pip install -e . writes src/*.egg-info)
*.egg-info/
build/
dist/

# Pytest
.pytest_cache/

# Ruff
.ruff_cache/

# IDE
.vscode/

# Environment / secrets
.env
.env.*

# OS files
.DS_Store
Thumbs.db
```

No `results/**` patterns exist yet — consistent with
`docs/A3-DESIGN.md §22`'s own statement that its artifact policy
("`results/**/ledger.jsonl` and `results/**/llm_cache*.jsonl` are
gitignored... `results/audit_sample/` is committed... manifests and
aggregate results are always committed") is **"Not implemented in this
pass — no `results/` directory or `.gitignore` entry exists yet."**

### Current contents of `results/` (paths only, depth 2)

```
results/
results/sensitivity.md
```

That is the **entire** contents — no subdirectories, no `<run_id>/`
folders, no `tuning_log.md`, no `holdout_runs.md`, no `audit_sample/`.
MISSING: `results/tuning_log.md` — searched: `Glob results/tuning_log.md`.
MISSING: `results/holdout_runs.md` — searched: `Glob
results/holdout_runs.md`. MISSING: `results/audit_sample/` — searched:
`Glob results/audit_sample/**`.

### Which artifact classes are currently committed vs ignored

| Artifact class | Status |
|---|---|
| `results/sensitivity.md` | **Committed** (exists, tracked, all cells `PENDING`) |
| `results/tuning_log.md` | Does not exist — neither committed nor ignored, simply absent |
| `results/holdout_runs.md` | Does not exist — simply absent |
| `results/audit_sample/` | Does not exist — simply absent |
| `results/<run_id>/manifest.json` | No run has ever produced one; no `.gitignore` rule for it either way |
| `results/**/ledger.jsonl`, `llm_cache*.jsonl` | Policy documented (`A3-DESIGN.md §22`) but not yet encoded in `.gitignore`; no such files exist to be ignored yet |

**`results/sensitivity.md` (verbatim, for reference — dumped in full
since it is the one artifact that exists):**

```markdown
# results/sensitivity.md

Generated by `make docs`. Do not hand-edit. Losing cells are published, never dropped.

- Split: `dev` (locked decision 1)
- Method: one_at_a_time, magnitude 30%
- Win: both Regime-B primary metrics beat A2, paired 95% CI excludes zero
- Pass mark: 18 / 22 cells (ceil of 80%)

| cell_id | parameter | handle | dir | clamped | invoice CI | rescue CI | win | low-info |
|---|---|---|---|---|---|---|---|---|
| `invoice_amount.low` | invoice_amount | median_inr | low | PENDING | PENDING | PENDING | PENDING |  |
| `invoice_amount.high` | invoice_amount | median_inr | high | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.card_change.low` | failure_mix_weights | bucket_mass:card_change | low | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.card_change.high` | failure_mix_weights | bucket_mass:card_change | high | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.balance.low` | failure_mix_weights | bucket_mass:balance | low | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.balance.high` | failure_mix_weights | bucket_mass:balance | high | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.ambiguous.low` | failure_mix_weights | bucket_mass:ambiguous | low | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.ambiguous.high` | failure_mix_weights | bucket_mass:ambiguous | high | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.wait.low` | failure_mix_weights | bucket_mass:wait | low | PENDING | PENDING | PENDING | PENDING | yes |
| `failure_mix_weights.wait.high` | failure_mix_weights | bucket_mass:wait | high | PENDING | PENDING | PENDING | PENDING | yes |
| `failure_mix_weights.no_contact.low` | failure_mix_weights | bucket_mass:no_contact | low | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.no_contact.high` | failure_mix_weights | bucket_mass:no_contact | high | PENDING | PENDING | PENDING | PENDING |  |
| `failure_mix_weights.escalate.low` | failure_mix_weights | bucket_mass:escalate | low | PENDING | PENDING | PENDING | PENDING | yes |
| `failure_mix_weights.escalate.high` | failure_mix_weights | bucket_mass:escalate | high | PENDING | PENDING | PENDING | PENDING | yes |
| `balance_restore_timing.low` | balance_restore_timing | salary_mode_mass | low | PENDING | PENDING | PENDING | PENDING |  |
| `balance_restore_timing.high` | balance_restore_timing | salary_mode_mass | high | PENDING | PENDING | PENDING | PENDING |  |
| `channel_response_propensity.low` | channel_response_propensity | trait_mean | low | PENDING | PENDING | PENDING | PENDING |  |
| `channel_response_propensity.high` | channel_response_propensity | trait_mean | high | PENDING | PENDING | PENDING | PENDING |  |
| `card_change_completion_propensity.low` | card_change_completion_propensity | completion_mean | low | PENDING | PENDING | PENDING | PENDING |  |
| `card_change_completion_propensity.high` | card_change_completion_propensity | completion_mean | high | PENDING | PENDING | PENDING | PENDING |  |
| `cancellation_hazard_and_ltv.low` | cancellation_hazard_and_ltv | joint_multiplier | low | PENDING | PENDING | PENDING | PENDING |  |
| `cancellation_hazard_and_ltv.high` | cancellation_hazard_and_ltv | joint_multiplier | high | PENDING | PENDING | PENDING | PENDING |  |

**Cells won: PENDING / 22. Pass mark 18.**

Low-information cells (wait/escalate buckets, <=5% mass) are counted in the
denominator per locked decision 13 and flagged, not removed.
```

---

## 10. DAY 4 VERIFICATION

### `pytest -q` — exact summary line

```
1 failed, 622 passed in 59.53s
```

### Every failing test, by full node id

```
tests/test_stage5_falsification.py::test_1_policy_ordering
```

Exact failure output:

```
Budget parity - max contacts_sent observed per arm: {'A0': 0, 'A1': 2, 'A2': 2, 'A4': 3}
Test 1 invoice recovery: A0=0.3525 A1=0.4840 A2=0.4485 A4=0.5465
Test 1 subscription rescue: A0=0.4055 A1=0.5095 A2=0.5180 A4=0.5670
A1-A0 diff=+0.1315 CI=[+0.1170,+0.1465]
A2-A1 diff=-0.0355 CI=[-0.0465,-0.0250]
A4-A2 invoice-recovery diff=+0.0980 CI=[+0.0855,+0.1115]  <- empirical oracle headroom over A2
A4-A2 subscription-rescue diff=+0.0490 CI=[+0.0390,+0.0595]

FAILED tests/test_stage5_falsification.py::test_1_policy_ordering - Failed:
Test 1 (policy ordering) FAILED:
A2-ish did not significantly beat A1-ish on invoice recovery: diff=-0.0355 CI=[-0.0465,-0.0250]
```

### Is this the only failure, and does it match the documented Stage 5 falsification?

**YES.** `1 failed, 622 passed` — exactly one failing node, and it is
`test_1_policy_ordering` inside `test_stage5_falsification.py`, the file
whose own module docstring and `EVAL.md`/`CHANGELOG.md` (§4.1's A2-vs-A1
discussion, dumped in Section 3 above) already document A2-original
underperforming A1 on invoice recovery as a **known, named defect** (the
same defect that motivated A2-corrected-v1/A2-strengthened in
`src/rrx/baselines/a2_variants.py`). This matches
`docs/A3-DESIGN.md §16`'s explicit expectation: "full `pytest`/`ruff`
status parity (**preserving the intentional 4-of-5 Stage 5 result**)."
**No other failures exist.**

### `ruff check .` — output

```
All checks passed!
```

### The NULL-POLICY parity test

**File:** `tests/test_a3_runner_parity.py`, function
`test_a3_runner_null_policy_exact_parity_with_a0_over_dev` (full text
dumped in Section 7's agent-contracts material is not this file — quoted
here in full since it directly answers this question):

```python
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
    # ... (failure-reporting branch, omitted here — quoted in full above
    # in the agent/runner sections; not reached on a passing run)
```

**Assertion being made:** for every `i` in `DEV_INDICES` (no early exit
on success — only breaks early on the first *mismatch*), `run_episode`
(A0, the frozen `sim-v1` arm) and `run_episode_a3` (the new A3 runner
driven by `null_policy`, which always proposes WAIT) must produce
**byte-identical** `EpisodeResult` **and** `EpisodeView`-at-day-30. If
`first_mismatch is None` after the full loop, the test passes silently
(`return`); it also independently asserts the SHA256 hashes of every
`src/rrx/sim/*.py` file plus `episode_view.py`, taken before and after
the loop, are unchanged (guards against the test itself accidentally
mutating frozen files).

**Episode count actually covered:** `DEV_INDICES = range(DEV_SEED_START,
DEV_SEED_START + DEV_N)` = `range(1000, 3000)` = **exactly 2,000**
episodes, iterated in full with no sampling/truncation.

**Confirmed or refuted: the claimed 2000/2000?** **CONFIRMED.** This
test is not among the failing node ids reported above (the pytest run's
only failure is `test_stage5_falsification.py::test_1_policy_ordering`),
so `test_a3_runner_null_policy_exact_parity_with_a0_over_dev` passed —
meaning all 2,000 dev episodes produced byte-identical results between
A0 and the null-policy A3 runner, with no mismatch triggering the early
break.

### Commit SHAs git history attributes to Day 4

From `git log --oneline -20` (Section 1): the two commits whose own
messages explicitly say "Day 4" / "Task 4B":

```
447997a Task 4B: real gate (R1-R8) and ledger implementations
7238c6f Day 4 foundation: A3 runner skeleton + byte-identity parity proof
```

`447997a` is current `HEAD`. The three commits immediately before these
(`eb6b979`, `641dcfa`, `51a0054`) are the A3-DESIGN.md freeze and its
EVAL.md v1.4 amendment — preparatory/design work that precedes "Day 4"
by its own commit messages ("Amend EVAL.md to v1.4", "Add
docs/A3-DESIGN.md", "Propagate A3 -> A3-D/A3-LLM split") rather than
implementation, so they are not counted as "Day 4" commits here, but are
its immediate prerequisite.

### TODO / FIXME / NotImplementedError in `src/rrx/agent/` and `src/rrx/harness/`

**None found.** `grep -rn "TODO\|FIXME\|NotImplementedError" src/rrx/agent
src/rrx/harness` returned no output/matches.
---

## 11. SPECIFICATION GAPS AND CONFLICTS

### GAPS — things Day 5 would need that no frozen spec defines

1. **No CLI entry point exists**, yet `Makefile`'s `eval`/`sweep` targets
   reference `python -m rrx.eval.runner`, a module that does not exist
   anywhere in `src/rrx/` (confirmed by direct import attempt, Section
   8). What owns this: a new `src/rrx/eval/` package (or a corrected
   `Makefile` target pointing at wherever the real entry point ends up).
   Blocks: `make eval`, `make sweep`, and `EVAL.md §6`'s "Reproducible via
   `make eval RUN=<run_id>`" claim — currently false, nothing is
   reproducible via `make eval` because the target fails immediately.
2. **`RunManifest`/`write_manifest` (`src/rrx/spec/manifest.py`) is
   defined but never invoked anywhere.** What owns wiring it in: whatever
   becomes the canonical run harness. Blocks: `EVAL.md §6`'s eleven-field
   manifest requirement for every run.
3. **No metrics-computation module exists** (invoice recovery rate,
   subscription rescue rate, contacts-per-recovery/rescue, etc., as
   reusable, tested functions) — only ad hoc inline code in
   `tests/test_stage5_falsification.py` and `diagnostics/*.py` scripts.
   What owns it: unclear — no file/module name is pre-registered anywhere
   in `EVAL.md` or `docs/A3-DESIGN.md`. Blocks: any canonical run
   producing `EVAL.md §5`'s metrics in a reusable, auditable way.
4. **No dedicated statistics/bootstrap module** — `paired_bootstrap_ci`
   lives in `src/rrx/sim/run_stage3.py`, a file whose own docstring
   frames it as a one-off "Day 2 Stage 3" diagnostic script ("No
   manifest, no results directory, no formatting infrastructure"), not a
   supported harness API. Blocks: a canonical, documented statistics
   entry point for A3-D/A3-LLM-vs-baseline comparisons.
5. **A3-D and A3-LLM themselves do not exist.** `src/rrx/agent/policy.py`
   (A3-D), `src/rrx/agent/planner.py`, and `src/rrx/agent/prompt.py`
   (A3-LLM) are all named as required modules in `docs/A3-DESIGN.md §2`
   but none exist yet (`Glob src/rrx/agent/**/*.py` returns only
   `proposal.py`, `gate.py`, `reason_codes.py`, `ledger.py`,
   `null_policy.py`). Blocks: everything downstream of "the agent makes a
   real decision" — the runner/gate/ledger pipeline currently has nothing
   to drive except the always-WAIT `null_policy`.
6. **No LLM model is pinned.** `EVAL.md §5.1`: "LLM inference | measured
   per run | `PLACEHOLDER` until the model is pinned." No config anywhere
   names a model/provider/version. Blocks: any A3-LLM cost accounting,
   the `model_version` ledger/manifest field, and `docs/A3-DESIGN.md
   §13`'s cache-key formula (`(template_version, model, temperature,
   prompt_hash)`), which has no `model` value to key on yet.
7. **No `--allow-live` flag, or any CLI flag, exists anywhere** — see gap
   1. `docs/A3-DESIGN.md §13`/`EVAL.md §6A` both require it for any live
   LLM call, cache extension, or one of the three repeat-nondeterminism
   runs, but no argument parser in the repository defines it.
8. **`results/tuning_log.md`, `results/holdout_runs.md`, and
   `results/audit_sample/` do not exist.** All three are named as
   required outputs (`EVAL.md §6A`, `§3.5`; `docs/A3-DESIGN.md §22`) but
   nothing in the repository creates them. Blocks: the tuning-budget
   record-keeping requirement, the holdout-run logging requirement, and
   the public audit-trail deliverable.
9. **The sweep grid has never been run for any arm.**
   `results/sensitivity.md` is 100% `PENDING` across all 22 cells, for
   every arm, including A2 (whose full-dev sweep `EVAL.md §6A` explicitly
   says "is scheduled as independent, deterministic work, not blocked on
   A3" — i.e. it could be run today, independent of A3 existing at all).
   Not technically undefined by spec (the sweep grid and win criterion
   are fully specified in `configs/model_params.yaml`), but flagged here
   because it is real, unstarted work with no code gap standing in the
   way except the missing runner-to-results wiring (gaps 1-4 above).
10. **No `run_id` generation scheme is specified anywhere.**
    `rrx.spec.manifest.write_manifest(manifest, run_id, results_dir)`
    requires the caller to supply `run_id`, but no config, doc, or code
    defines its format (timestamp? hash? sequential?). Blocks: any
    concrete call to `write_manifest`.

### CONFLICTS — EVAL.md vs. docs/A3-DESIGN.md

**None found in this pass.** Both documents were read in full (Sections
3 and 5 above) and cross-checked against each other on every point where
`A3-DESIGN.md` explicitly claims to carry forward or restate an
`EVAL.md` provision (wake-up rationale, `wait_rate` definition,
"unknown-condition escalation rate" definition, CRN/pairing methodology,
gate-row-to-rule mapping, tuning/sweep numbers, cost-attribution rule,
five-value fallback-reason enum, seven-value reason_code enum). Every
cross-reference checked resolves consistently — `A3-DESIGN.md` is
explicitly written as `EVAL.md`'s "Companion", and its own text
repeatedly states when it is "carried forward... unchanged" (§17) versus
introducing something `EVAL.md` never specifies (§5's wake-up days, §14's
ledger schema — see Section 6's "ONLY in A3-DESIGN.md" list above, which
are additions, not contradictions). This is not an exhaustive
line-by-line diff of every sentence in both 1,238 combined lines — it is
what this pass's read-through surfaced — so absence of a found conflict
here is evidence, not proof, that none exists.

One near-conflict considered and **ruled not a conflict**: `EVAL.md §6`
specifies "paired bootstrap, 10,000 resamples" as the canonical
methodology; the one existing bootstrap implementation
(`src/rrx/sim/run_stage3.py`) defaults to `N_BOOTSTRAP_RESAMPLES =
10_000`, matching exactly, but `tests/test_stage5_falsification.py`
calls the same function with an explicit `n_resamples=5000` override for
its own falsification-check speed. This is a **test-code choice**, not a
disagreement between `EVAL.md` and `A3-DESIGN.md` (the two documents this
section is scoped to), so it is not listed as a CONFLICT — recorded here
only so it isn't silently lost.

### MISSING AUTHORITATIVE CONTEXT — anything not locatable in this pass

- `data/decline_codes.md` §10.5 — `EVAL.md §1.4` cites this path/section
  for the eMandate/UPI retry-model documentation gap; not opened in this
  pass (out of the batch's prescribed file list) — its existence/content
  is unverified here.
- The full text of `CHANGELOG.md` — referenced repeatedly by both
  `EVAL.md` and `SIM.md` as the authoritative provenance record for
  several amendments (e.g. the `eval-spec-v1.3`/`v1.4` entries, the A2
  baseline-resolution derivation), but not in this batch's required dump
  list; only its section headings were sampled (Section 1 area) to
  locate Day 4 attribution, not read in full.
- `data/decline_codes.yaml` — referenced constantly (`global_caps`,
  `verified`/`in_v1_cohort` flags, `ALL_DECLINE_CODES` provenance) but
  not opened in this pass.
- `configs/population.yaml`, `configs/episode.yaml`, `configs/costs.yaml`
  — referenced extensively by `owner_path` pointers throughout
  `model_params.yaml`/`EVAL.md`/`SIM.md`, but not opened in this pass
  (only referenced, never dumped) — their content is taken on the
  authority of the citing documents' quotations, not independently
  verified against the raw YAML in this pass.
- `tests/test_gate_precedence.py` — named in `gate.py`'s own docstring
  ("a proposal violating several rules is reported under only the
  highest-precedence one (tests/test_gate_precedence.py)") but not
  confirmed to exist as a file in this pass — not independently searched.

---

## 12. COMPLETENESS CHECKLIST

**Batch 1 — Repo state & integrity**
- [DUMPED] `git rev-parse --abbrev-ref HEAD`, `HEAD` SHA, `git status
  --porcelain=v1`, `git log --oneline -20`, `git tag --list` (plain and
  with SHAs), `git status`/`git diff --stat` for `src/rrx/sim/`
- [DUMPED] File listing + line counts + SHA256 hashes for every
  `src/rrx/sim/*.py` file
- [DUMPED] Frozen-hash manifest search (result: none exists; one
  before/after hash check exists in `test_a3_runner_parity.py`)
- [DUMPED] Plain statement: does `src/rrx/sim/` match frozen state — YES
  (by git diff/status; no cross-session hash artifact exists to check
  further, noted as UNKNOWN by that narrower standard)

**Batch 2 — Frozen specifications**
- [DUMPED] `EVAL.md` — path, 648 lines, TOC, full verbatim text, version
  string, tag-pointer analysis
- [DUMPED] `SIM.md` — path, 498 lines, TOC, full verbatim text, version
  string, tag-pointer analysis (exact tag match: `eval-spec-v1.2`)
- [DUMPED] `docs/A3-DESIGN.md` — path, 590 lines, TOC, full verbatim
  text, version string, tag-pointer analysis

**Batch 3 — Evaluation design facts**
- [DUMPED] Every requested item, quoted with exact `EVAL.md` line numbers
- [DUMPED] Explicit list of what appears ONLY in `A3-DESIGN.md`

**Batch 4 — Agent contracts**
- [DUMPED] `proposal.py`, `gate.py`, `reason_codes.py`, `ledger.py` — full
  verbatim
- [PARTIAL] `null_policy.py` dumped in full, but this is **not** the file
  the batch instruction named (`src/rrx/agent/reason_codes.py` was
  requested and dumped; the batch also implicitly expected A3-D's real
  policy, which does not exist — see GAPS item 5). All five files that
  *do* exist under `src/rrx/agent/` were dumped in full; two named-future
  files (`policy.py` is not literally named in the batch list but is the
  file the reason_codes/gate machinery exists to serve) do not exist.
- [DUMPED] `EpisodeView` definition, field count (10), allowlist
  enforcement location (3-layer `test_no_latent_leak.py`)
- [DUMPED] `ContactRecord` definition, field count (5)
- [DUMPED] Ledger schema, field-by-field table, field count confirmed as
  22 (matches the file's own docstring claim — no discrepancy)
- [DUMPED] Proposal/action space enumeration
- [DUMPED] Gate rule table (R1–R8) with precedence
- [DUMPED] Direct answer: legal-proposal→legal-executor-mapping —
  **UNENFORCED**, with the specific code path quoted

**Batch 5 — Runner & evaluation infrastructure**
- [DUMPED] `src/rrx/harness/runner.py` — full verbatim
- [DUMPED] `src/rrx/harness/splits.py` — full verbatim
- [DUMPED] `run_episode()`/`_POLICIES` registry — located, dumped, only
  A0/A2 registered (flagged loudly)
- [PARTIAL] "Every existing arm policy implementation (A0, A1, A2
  variants, A4)" — A0/A2-original located in `engine.py` (not dumped in
  full — that file is outside this batch's named dump list and outside
  the locked-file boundary this session must not reproduce beyond what's
  needed to answer the specific sub-questions asked); A2-corrected-v1/
  A2-strengthened dumped in full (`a2_variants.py`); **A1 and A4 have no
  standalone implementation anywhere** — both are constructed ad hoc
  inside `tests/test_stage5_falsification.py`, which was not opened in
  full in this pass (only grepped) — MISSING as a dumped file, PARTIAL as
  an answer.
- [DUMPED] `RunManifest` — path, full 11-field schema, "wired into
  nothing" confirmed
- [MISSING] Metrics computation module(s) — does not exist
- [PARTIAL] Statistics (paired comparison/bootstrap/CI) — located
  (`run_stage3.py`) and quoted, but flagged as a one-off script, not a
  supported module — see GAPS item 4
- [DUMPED] Sweep infrastructure — `registry.py` described (not dumped in
  full — not in this batch's named dump list) plus `model_params.yaml`
  dumped in full and `results/sensitivity.md` dumped in full
- [MISSING] CLI entry points — none exist anywhere; `Makefile`'s targets
  reference a nonexistent module (`rrx.eval.runner`), confirmed by direct
  import attempt
- [DUMPED] Episode selection/seed passing, arm selection, gate-invocation
  point, unmappable/rejected-proposal handling, results-writing location
  — all answered directly

**Batch 6 — Split protection & output policy**
- [DUMPED] dev/holdout representation in code, quoted
- [DUMPED] Holdout guard — quoted (`HoldoutNotAuthorizedError`,
  `authorized=True` requirement)
- [DUMPED] `.gitignore` — full verbatim
- [DUMPED] `results/` contents (depth 2) — only `sensitivity.md` exists
- [DUMPED] Artifact-class committed-vs-ignored table

**Batch 7 — Day 4 verification**
- [DUMPED] `pytest -q` exact summary line: `1 failed, 622 passed in
  59.53s`
- [DUMPED] Full failing node id: `test_stage5_falsification.py::
  test_1_policy_ordering`, with its exact failure text
- [DUMPED] Confirmed: this is the only failure and it matches the
  documented Stage 5 falsification (A2-original underperforming A1 on
  invoice recovery, a pre-existing named defect)
- [DUMPED] `ruff check .` output: `All checks passed!`
- [DUMPED] NULL-POLICY parity test — located, quoted, episode count
  confirmed as exactly 2,000 (`DEV_INDICES = range(1000, 3000)`),
  2000/2000 claim CONFIRMED (test is not among the pytest failures)
- [DUMPED] Day 4 commit SHAs: `447997a`, `7238c6f`
- [DUMPED] TODO/FIXME/NotImplementedError search in
  `src/rrx/agent`/`src/rrx/harness` — none found

**Batch 8 — File structure & gap report**
- [DUMPED] This document, under the exact 12 headings requested
- [DUMPED] Section 11 GAPS (10 items), CONFLICTS (none found, one
  near-conflict explicitly ruled out with reasoning), MISSING
  AUTHORITATIVE CONTEXT (5 items)
- [DUMPED] This checklist (Section 12) — every batch-1-through-7 item
  marked DUMPED / MISSING / PARTIAL with a stated reason for every
  PARTIAL
