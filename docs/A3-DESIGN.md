# A3 Design — EpisodeView-Aware Runner, Gate, Executor, Ledger

**Status:** Design freeze (eval-spec-v1.4), final pass — all open
questions from the prior pass resolved (§21). Amended at `eval-spec-v1.5`
(§10A added — the A3-D decision-table pre-registration, plus the
[D-1]/[CONSEQUENTIAL-1] corrections it required; see `CHANGELOG.md`).
Specification only — no implementation exists yet. Companion to
`EVAL.md §4.2, §5.2-§5.4, §6A, §8 items 7-8` and `SIM.md`. `src/rrx/sim/`
is unmodified.

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
| `no_engagement_restraint` | Withholding or stopping — either low observed engagement this episode, or a condition under which `SIM.md §2`–§5 make every available action a mechanical no-op `[D-2, eval-spec-v1.5]` | `WAIT` | any except `subscription_cancelled_by_customer` |
| `risk_flagged` | Escalation | `STOP` | `payment_risk_check_failed` only |

`[D-2, eval-spec-v1.5]` **`no_engagement_restraint`'s meaning column widened.**
Originally "Withholding — low observed engagement this episode" only.
Routing the mechanically-dead conditions §10A.4 identifies (R-03, R-05,
R-06, R-07) to `WAIT` instead of `STOP` would place environment-forced
inaction in `wait_rate`'s numerator — the same error `EVAL.md §8` item 8
already forbids for the cancelled-at-open bucket. The admissible
`decline_code` set (any except `subscription_cancelled_by_customer`) and
the 7-value enum are both unchanged; only this row's meaning column reads
differently. See §10A.7.

`[CONSEQUENTIAL-1, eval-spec-v1.5]` **`remedy_match_topup`'s admissible
`decline_code` set widened to include `ambiguous_decline`** (table row
above, and `ADMISSIBLE_DECLINE_CODES[REMEDY_MATCH_TOPUP]` in
`src/rrx/agent/reason_codes.py`). Required by §10A.4 rule R-15. See
§10A.7 for the full rationale.

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
  gate_rejected | stale_state | no_executor_mapping | null` (§11, §19).
  `[CORRECTION, eval-spec-v1.10]` `no_executor_mapping` is the sixth,
  enforcement-layer value added by `EVAL.md §7.1` item E
  (`eval-spec-v1.8`): it fires when the gate accepts a proposal but the
  executor holds no legal mapping for the proposed `(action_type,
  remedy)` pair — distinct from `gate_rejected`. It is not added to
  `rrx.agent.planner.FALLBACK_REASONS`, which remains the pre-
  `eval-spec-v1.8` five-value set — that constant's own scope (per its
  module docstring) is the three fallback reasons the planner itself can
  determine (`timeout`, `unparseable`, `schema_violation`) before a
  `Proposal` reaches the gate; `gate_rejected`/`stale_state` were already
  outside its own determination, and `no_executor_mapping` is the same.

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

## 10A. A3-D decision table — pre-registration `[AMENDMENT, eval-spec-v1.5]`

**Status:** Pre-registered. Written and tagged before `src/rrx/agent/policy.py`
exists and before any A3-D episode has been executed. This section supplies the
concrete decision table §10 deferred ("The concrete decision table is
implementation, not this design freeze"). Once tagged, it is subject to the same
rule as every other frozen section: changes require a new tagged version and a
`CHANGELOG.md` entry, and constitute a new tuning configuration under
`EVAL.md §6A`.

---

### 10A.1 Scope and invocation preconditions

A3-D is a pure, deterministic function `EpisodeView -> Proposal`
(`EVAL.md §4.2`). It is invoked by `src/rrx/harness/runner.py` only on ticks
where `tick_type == "wakeup"` (§3 step 4). Therefore, on entry:

- `subscription_state not in {"cancelled", "expired", "active"}` — runner-suppressed (§5, §10A.2)
- `budget_remaining >= 1` — otherwise `tick_type = "budget_exhausted"` (§7)
- no prior `STOP` decision in this episode — otherwise `terminal_suppressed` (§6)
- `decline_code in ALL_DECLINE_CODES` (8 values, `src/rrx/agent/reason_codes.py`).
  `subscription_cancelled_by_customer` is not a `decline_code` and never reaches
  a tick at all (`engine.py:438-443`; `EVAL.md §8` item 8)

A3-D reads no field outside `EpisodeView` / `ContactRecord`
(§4; `tests/test_no_latent_leak.py`). It performs no I/O, holds no state between
ticks, and draws no randomness.

---

### 10A.2 Runner amendment — `"active"` is terminal `[D-1]`

`src/rrx/harness/runner.py`'s `TERMINAL_SUBSCRIPTION_STATES` is amended from
`{"cancelled", "expired"}` to `{"cancelled", "expired", "active"}`.

**Reason.** `_retry_succeeds` sets `subscription_state = "active"` on invoice
recovery. Without this amendment, a recovered episode remains non-terminal, keeps
its remaining budget, and therefore produces full `wakeup` ticks on every
subsequent day in the frozen wake-up set — each demanding a mandatory
`reason_code` from §7's closed 7-value enum. No member of that enum denotes "this
episode is already resolved." `terminal_state` was removed in `eval-spec-v1.4`
on a rationale addressed solely to `subscription_cancelled_by_customer`
(terminal at T=0, before any tick); the post-recovery `active` case was not
considered and is reachable on a large fraction of the population.

Suppressing these ticks mirrors §6's existing STOP semantics ("subsequent
would-be wake-up days produce `tick_type=terminal_suppressed`") and requires no
change to the frozen enum.

**Consequences, declared before the run:** `tick_type` counts shift
(`terminal_suppressed` up, `wakeup` down) for every arm run through the A3
runner. `wait_rate`'s denominator (wake-up decisions, `EVAL.md §5.3`) therefore
excludes post-recovery ticks, which is the intended reading — a decision that
cannot affect the outcome is not restraint. NULL-POLICY parity was re-verified
at 2,000/2,000 after this change (`tests/test_a3_runner_parity.py`); `null_policy`
mutates no state, so `EpisodeResult` and the day-30 `EpisodeView` are unchanged.

---

### 10A.3 Restraint predicate — the withhold test `[D-3]` `[DESIGN]`

```
observations      = len(view.contact_history)
any_engaged       = any(rec.engaged for rec in view.contact_history)
withhold_applies  = (observations >= 2) and (not any_engaged)
```

`contact_history` includes Razorpay's automatic failure email as an entry
(`EVAL.md §3.4`; `SIM.md §3`), so `observations` counts the auto-email at T+0,
the halt email at T+3, and every agent contact. `withhold_applies` is therefore
evaluable from the day-0 tick onward, because the runner sends the auto-email
(§3 step 1) and rebuilds the view (step 2) before the policy is called (step 4).

**Basis.** `channel_response_trait` (θ_c) is drawn once per episode and reused
for every message in that episode (`SIM.md §3`; `episode.yaml#/latent/
channel_response_propensity`), so observed non-engagement is genuine evidence
about θ_c rather than independent noise. With mean θ_c = 0.28, the email
multiplier 0.65 and WhatsApp 1.15, the auto-email engages with ≈0.18 and a first
agent contact with ≈0.32; two consecutive non-engagements move the posterior on
θ_c down materially. Meanwhile fatigue has already reduced the next contact's
effectiveness to 0.80× and the cancellation hazard has risen to 1.5× its initial
value. The first agent contact is never withheld — a single Bernoulli
observation is too thin to justify silence — so the predicate gates only the
second and third.

**The threshold `observations >= 2` is `[DESIGN]`.** No frozen source implies it.
It is fixed here, before any result exists, and changing it constitutes a new
tuning configuration.

**This predicate is the sole mechanism by which A3-D exercises `EVAL.md §3.4`'s
third pre-registered advantage source** (within-episode adaptive contact, as
narrowed by `SIM.md §10`). No other rule in this table reads engagement history.

---

### 10A.4 The decision table

An **ordered list. First match wins.** This ordering is the tie-breaking rule
required for totality; no rule is reachable by a view that an earlier rule
matches. Every rule emits its own id as `Proposal.rationale` (§10: "always
populated, with the internal rule identifier that fired").

`CARD_BROKEN = {card_expired, debit_instrument_blocked, card_not_enabled_group}`
`day = view.days_since_first_failure`

| # | Condition | `action_type` | `remedy` | `reason_code` |
|---|---|---|---|---|
| **R-01** | `subscription_state == "active"` | STOP | — | `no_engagement_restraint` |
| **R-02** | `decline_code == "payment_risk_check_failed"` | STOP | — | `risk_flagged` |
| **R-03** | `decline_code == "transaction_limit_exceeded"` | STOP | — | `no_engagement_restraint` |
| **R-04** | `decline_code == "bank_technical_error"` and `auto_retries_remaining > 0` | WAIT | — | `retry_window_open` |
| **R-05** | `decline_code == "bank_technical_error"` | STOP | — | `no_engagement_restraint` |
| **R-06** | `decline_code == "insufficient_funds"` and `subscription_state == "halted"` | STOP | — | `no_engagement_restraint` |
| **R-07** | `decline_code == "insufficient_funds"` and `day >= 3` | STOP | — | `no_engagement_restraint` |
| **R-08** | `decline_code == "insufficient_funds"` and `day == 0` | CONTACT | `topup_reminder` | `remedy_match_topup` |
| **R-09** | `decline_code == "insufficient_funds"` and `day == 2` and not `withhold_applies` | CONTACT | `topup_reminder` | `engagement_observed` if `any_engaged` else `remedy_match_topup` |
| **R-10** | `decline_code == "insufficient_funds"` | WAIT | — | `no_engagement_restraint` if `withhold_applies` else `retry_window_open` |
| **R-11** | `decline_code in CARD_BROKEN ∪ {ambiguous_decline}` and `subscription_state == "halted"` and `day == 5` and `budget_remaining >= 1` | CONTACT | `card_change` | `post_halt_rescue` |
| **R-12** | `decline_code in CARD_BROKEN` and `day == 0` | CONTACT | `card_change` | `remedy_match_card` |
| **R-13** | `decline_code in CARD_BROKEN` and `day == 3` and not `withhold_applies` | CONTACT | `card_change` | `engagement_observed` if `any_engaged` else `remedy_match_card` |
| **R-14** | `decline_code == "ambiguous_decline"` and `day == 0` | CONTACT | `card_change` | `remedy_match_card` |
| **R-15** | `decline_code == "ambiguous_decline"` and `day == 2` and not `withhold_applies` | CONTACT | `topup_reminder` | `remedy_match_topup` `[CONSEQUENTIAL-1]` |
| **R-16** | *(default — every remaining view)* | WAIT | — | `no_engagement_restraint` |

---

### 10A.5 Per-rule basis

**R-01 `[D-1]` — defensive, structurally unreachable.** Under §10A.2 the runner
suppresses `active` ticks, so this rule can never fire against a real tick. It is
retained as a defensive guard on the same footing as gate rule R2 (§8:
"Defensive only, in practice unreachable"), and is exercised only by synthetic
views in `tests/test_a3d_policy.py`.

**R-02 `[FORCED]`.** Gate R4 rejects any `CONTACT` when
`decline_code == payment_risk_check_failed`, so contacting is impossible.
`EVAL.md §5.3` amendment 3 defines escalation as `STOP` with
`reason_code=risk_flagged`; §7 admits `risk_flagged` for this code alone.

**R-03 `[FORCED mechanically]` `[D-2]`.** `SIM.md §2` sets `blocked_until` beyond
every auto-retry day for this condition, so `§4`'s retry conjunction can never be
satisfied in-window — invoice recovery is impossible. `SIM.md §5` restricts
post-halt rescue to episodes whose `card_chargeable` was false at opening; this
condition opens `card_chargeable = true`, so rescue is unreachable too. Gate R3
independently forbids `card_change` here. No action of any kind can change this
episode's outcome.

**R-04 `[FORCED]`.** `episode.yaml#/latent/bank_technical_error_clearance` gives
`blocked_until ~ Uniform(0, 2]`, and retries fire at T+1/T+2/T+3, so the block
clears before the day-2 retry with certainty. Waiting is the correct remedy,
exactly as `EVAL.md §3.2` states. `retry_window_open` is admissible for this
code per §7.

**R-05 `[D-2]`.** Reached only if retries are exhausted, which the mechanism above
makes vanishingly rare. `card_chargeable = true` at opening (`SIM.md §2`) blocks
the post-halt rescue path, so nothing further is reachable. This is the same
mechanism behind `EVAL.md §4.1.1` item 2, which found A2-original's unguarded
T+5 contact useless on 51 of 51 dev episodes.

**R-06, R-07 `[FORCED mechanically]` `[D-2]` `[D-4]`.** Two independent grounds.
(1) `EVAL.md §1.3` and `SIM.md §5`: invoice recovery occurs only via an auto-retry
at T+1/T+2/T+3, and this condition opens `card_chargeable = true`, so `SIM.md §5`'s
at-opening restriction rules out post-halt rescue — after halt, nothing is
reachable. (2) The acceleration rule is
`funds_available_from = min(original, t_engage + Exponential(mean 0.5))`
(`SIM.md §3`). The exponential draw is strictly positive, so a dues-naming message
engaged on day *t* yields funds strictly after *t*, and the day-*t* retry's
`t >= funds_available_from` test fails. A topup reminder sent on day 3 therefore
cannot affect the day-3 retry, and no later retry exists. **Days 3 and beyond are
provably dead for this bucket.**

**R-08, R-09 `[D-4]` `[DESIGN]`.** Day 0 is the earliest reachable decision point
and its effect is visible to the retries at T+1, T+2 and T+3. Day 2 is the last
day on which a topup can still affect an auto-retry, per the proof above, and
leaves one intervening day in which engagement can be observed. Each engaged
dues-naming message triggers a fresh `Bernoulli(p_topup_action = 0.35)` and a
fresh `Exponential` draw (`SIM.md §3`, "drawn per engagement, not per customer"),
so a second attempt is not redundant. Two attempts rather than three is a
restraint choice, not a forced one: the third budget slot has no legal use in this
bucket, since gate R3 forbids `card_change` here and days 3+ are dead.

**R-10 `[D-3]`.** Covers day 1, and day 2 when the withhold test fires. The
reason code distinguishes the two grounds for waiting: `retry_window_open` when
retries may still resolve it unaided (admissible for this code per §7), and
`no_engagement_restraint` when the withhold predicate is what suppressed the
contact. This distinction is what makes the ledger's restraint accounting
readable after the fact.

**R-11 `[D-5]` `[D-6]` `[D-7]`.** Post-halt, subscription rescue is the only
reachable value (`EVAL.md §1.3`; `SIM.md §5`), and only for episodes whose
`card_chargeable` was false at opening — which is exactly `CARD_BROKEN` plus
`ambiguous_decline`'s false draw. Day 5 matches
`a2_strengthened_action_for_day`'s third contact, whose measured gain on this
bucket was +5.6 rescue points at zero invoice-recovery cost (`EVAL.md §4.1.2`).
**Exempt from the withhold test per `[D-7]`:** withholding here saves a
cancellation hazard of 0.0225 and forfeits an attempt at one of `EVAL.md §7`'s
two primary metrics. The asymmetry is deliberate and declared. The rule is gated
to `day == 5` exactly; halted wake-ups on other days (7, 14, or engagement-driven)
fall through to R-16, so this bucket never spends more than one post-halt contact.
`budget_remaining >= 1` is guaranteed by the invocation precondition and is
re-checked defensively.

**R-12, R-13 `[D-5]`.** **A3-D deliberately adopts A2-strengthened's contact
schedule (T+0 / T+3 / T+5-if-halted) unchanged.** A3-D is the control arm against
which A3-LLM's incremental contribution is measured (`EVAL.md §4.2`), and it is
also the arm from which any A3-D − A2 reading would be taken. Changing both the
schedule and the decision logic relative to A2 would confound adaptivity with
scheduling, leaving neither effect identifiable. **The single intended difference
between A3-D and A2-strengthened on this bucket is that A3-D's day-3 contact is
conditional on the withhold test and A2's is unconditional.** A mechanically
earlier schedule (T+0/T+1) is available and would likely improve A3-D's invoice
recovery — within-day ordering (`SIM.md §4`) means a day-1 contact is visible to
the retries at T+1, T+2 and T+3 while a day-3 contact reaches only T+3 — and it is
declined here on identifiability grounds, not oversight. Recorded so that the
choice is auditable and so that no later run may adopt the stronger schedule
without registering a new configuration.

**R-14, R-15 `[D-6]`.** `EVAL.md §3.2` names the fail-safe card-change prompt as
the correct remedy for this ambiguous bucket, and `population.yaml#/
opening_conditions` sets `p_card_cause = 0.50`, so half the bucket is
funds-caused. Day 0 sends the fail-safe. Day 2 hedges the funds branch on the last
day a topup can still matter (R-06/R-07's proof applies identically here), and by
then non-recovery after an engaged card-change prompt is weak evidence against the
card branch, since a completed card change would likely have recovered at the T+1
or T+2 retry. Day 5 post-halt returns to card-change via R-11. This is a
remedy-matching decision A2 does not make — `a2_strengthened_action_for_day` sends
`card_change` at T+0 and T+7 for this bucket and never a topup.

**R-16 `[D-8]`.** A named, logged default rather than an implicit fallthrough, so
that every decision carries an attributable rule id (§6: `rationale` mandatory).
Its firing rate is a diagnostic: a rate materially above expectation indicates the
table has a hole, and that finding is to be reported rather than silently patched.

---

### 10A.6 Gate-compliance proof

§8 states A3-D "is gate-compliant by construction — its own decision logic
never proposes a violating action." That claim is discharged as follows, and enforced by
`tests/test_a3d_policy.py`.

| Gate rule | Discharge |
|---|---|
| R1 (schema validity) | Every rule emits `action_type in {CONTACT, WAIT, STOP}` and `remedy in {card_change, topup_reminder}` iff `CONTACT`, null otherwise — enforced at `Proposal` construction (§6) |
| R2 (terminal states) | Unreachable: `cancelled`/`expired` suppressed by the runner before invocation |
| R3 (remedy match) | No rule emits `card_change` for `insufficient_funds` (R-06…R-10) or `transaction_limit_exceeded` (R-03 STOPs first) |
| R4 (risk stop) | R-02 fires first and emits STOP |
| R5 (budget) | `budget_remaining >= 1` by precondition; R-11 re-checks defensively |
| R6 (quiet hours) | Declared vacuous in `sim-v1` (§8); executor stamps `send_hour = "10:00"` |
| R7 (audit coverage) | Structural — one ledger record per tick, runner-guaranteed |
| R8 (verified codes) | `decline_code in ALL_DECLINE_CODES` by cohort construction |

**A gate rejection originating from A3-D output is a defect, not a result.** If one
occurs during the dev run, work stops and the cause is reported; the table is not
adjusted to make the rejection disappear.

---

### 10A.7 Reason-code admissibility

Every `(reason_code, decline_code)` pair this table can emit satisfies §7's
admissibility mapping, with one consequential amendment:

`[CONSEQUENTIAL-1]` **§7's `remedy_match_topup` row is widened to include
`ambiguous_decline`.** R-15 sends a dues-naming remedy for a bucket that is
50% funds-caused by `population.yaml`'s own `p_card_cause = 0.50`, which is a
remedy match in the ordinary sense of the term. §7 already admits
`ambiguous_decline` under `post_halt_rescue`; its absence from
`remedy_match_topup` is an omission rather than a decision, and is corrected here
rather than worked around by emitting a less accurate code.
`ADMISSIBLE_DECLINE_CODES[REMEDY_MATCH_TOPUP]` in
`src/rrx/agent/reason_codes.py` is updated to match. No other row of §7's table
changes; the enum remains at 7 values.

`[D-2]` **§7's `no_engagement_restraint` row's meaning column is widened** from
"Withholding — low observed engagement this episode" to "Withholding or
stopping — either low observed engagement this episode, or a condition under
which `SIM.md §2`–§5 make every available action a mechanical no-op." Its
admissible `decline_code` set (any except `subscription_cancelled_by_customer`)
is unchanged, and the enum remains at 7 values.

**Why `STOP` rather than `WAIT` for the mechanically-dead conditions
(R-03, R-05, R-06, R-07).** Routing them to `WAIT` would place environment-forced
inaction in `wait_rate`'s numerator. `EVAL.md §8` item 8 already forbids
presenting environment-enforced restraint as agent judgement for the
cancelled-at-open bucket; the same principle applies to `transaction_limit_exceeded`
(1%), `bank_technical_error` (3%), and post-halt `insufficient_funds`. `STOP`
keeps `wait_rate` a measure of discretionary restraint. These STOPs are
nonetheless real decisions — the agent recognises an unrecoverable condition and
forgoes its remaining budget — and are recorded as such in the ledger.

---

### 10A.8 Contact-budget accounting

Maximum agent contacts under this table, by bucket:

| Bucket | Days | Max contacts | Budget |
|---|---|---|---|
| `CARD_BROKEN` | 0, 3, 5-if-halted | 3 | 3 |
| `ambiguous_decline` | 0, 2, 5-if-halted | 3 | 3 |
| `insufficient_funds` | 0, 2 | 2 | 3 |
| `bank_technical_error` | — | 0 | 3 |
| `transaction_limit_exceeded` | — | 0 | 3 |
| `payment_risk_check_failed` | — | 0 | 3 |

No bucket can exceed the 3-contact budget (`episode.yaml#/agent_budget/
max_contacts_per_episode`), so gate R5 is never reached through A3-D output —
consistent with §8's enforcement-by-construction framing. The withhold test can
only reduce these counts, never increase them.

---

### 10A.9 Tuning-configuration identity

This section, as tagged, **is A3-D configuration #1 of the N=3 budget**
(`EVAL.md §6A`). Any subsequent change to any rule, ordering, threshold, remedy,
reason-code assignment, or to the withhold predicate constitutes configuration #2,
and must be recorded in `results/tuning_log.md` **before** it is executed. The
`[DESIGN]`-tagged quantities most likely to attract revision are named here so
that a later change cannot be characterised as a clarification: the withhold
threshold `observations >= 2` (§10A.3), the `insufficient_funds` day set `{0, 2}`
(R-08/R-09), and the `ambiguous_decline` day-2 remedy choice (R-15).

**No A3-D result of any kind exists at the time this section is tagged.**
`src/rrx/agent/policy.py` is not implemented in this pass (Stage 5E) — this
section is specification only.

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
| `fallback_reason` | enum (§7, 6 values) \| null `[CORRECTION, eval-spec-v1.10]` | | If fallback occurred | Always null — A3-D is the fallback target |
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

**The 5% cancelled-at-open population bucket is environment-restraint,
not agent-restraint, for every arm.** `subscription_cancelled_by_customer`
episodes terminate at T=0 before any per-day tick exists
(`engine.py:438-443`) — not merely before any contact is sent. No arm,
including A3-D/A3-LLM, is ever invoked for this bucket; the zero-contact
outcome is structural, identical for A0/A1/A2/A3/A4, and holds wherever
such episodes occur — in `dev`, `holdout`, or `stress` alike, at whatever
rate the frozen population distribution produces them. No pitch, README,
or results narrative may cite this bucket's zero-contact rate as evidence
of A3's judgement or restraint — it demonstrates nothing about the
policy, deterministic or LLM. See `EVAL.md §8` item 8 (verbatim
cross-reference). This verification is now complete: the runner is
implemented (this document), and the finding above holds as stated.

`[CORRECTION, eval-spec-v1.9]` The previous version of this paragraph
additionally stated that this bucket's restraint "also applies to the
all-`cancelled` `stress` cohort" — implying `stress` was itself composed
entirely of cancelled-at-open episodes. **`stress` is not, and was never
implemented as, an all-cancelled cohort.** `EVAL.md §3.5` (`eval-spec-v1.9`)
corrects this: `stress` is 300 episodes drawn from the ordinary frozen
population distribution, in which cancelled-at-open episodes occur only
at their normal population rate (§3.2), the same as in `dev`/`holdout`.
The dev-bucket conclusion above is unaffected by this correction — it was
never dependent on `stress`'s composition.

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
