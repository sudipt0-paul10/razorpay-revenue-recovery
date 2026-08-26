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
