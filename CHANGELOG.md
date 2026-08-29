# Changelog

## eval-spec-v1.10 — fallback-reason taxonomy corrected for executor enforcement — 2026-08-29

Correction-only stage. No simulator, agent, config, test, or result
artifact changed. No holdout index accessed. `eval-spec-v1.9` remains
unchanged at `fbe09c6`; this entry does not rewrite any earlier version.

### What changed

| Item | Class | Summary |
|---|---|---|
| `EVAL.md §5.4` | `CORRECTION` | Extended the `fallback_reason` taxonomy from five to six named values by adding `no_executor_mapping` |
| `docs/A3-DESIGN.md` §7 taxonomy | `CORRECTION` | Updated the corresponding enum list to the six-value taxonomy |
| `docs/A3-DESIGN.md` §14 | `CORRECTION` | Updated the ledger-table reference from five to six values |

### Why this is a correction

`eval-spec-v1.8` introduced an enforcement-layer invariant (`§7.1` item
E) requiring a distinguishing `fallback_reason` when a gate-accepted
proposal has no legal executor mapping. The implementation uses the
value `no_executor_mapping`, and Stage 7.2's regression tests
(`tests/test_executor_mapping_enforcement.py`) already verify it.

The frozen `§5.4` taxonomy was not updated at that time and therefore
incorrectly continued to describe the field as closed at five values.
This amendment reconciles the documentation with the already-frozen
behavior; it does not introduce new behavior.

### Layering

`no_executor_mapping` is an executor/enforcement-layer value, determined
only after gate evaluation. It is not added to
`rrx.agent.planner.FALLBACK_REASONS`, which remains the pre-
`eval-spec-v1.8` five-value set, unmodified. That constant's own module
docstring already scopes its authority to the three fallback reasons the
planner itself can determine (`timeout`, `unparseable`,
`schema_violation`) before a `Proposal` reaches the gate — `gate_rejected`
and `stale_state` were already outside its own determination, and
`no_executor_mapping` is the same. `EVAL.md §5.4`, not that constant, is
the authority on the full six-value taxonomy.

### What did not change

- `LedgerRecord` schema.
- Simulator.
- Agent behavior.
- Gate rules R1–R8.
- §5.2 invariants.
- Criterion 1.
- v1.7 comparator/tie-set rule.
- Stress definition.
- Sensitivity cell membership or threshold.
- Holdout behavior.
- Any result artifact.

### Verification required before commit

- Only `EVAL.md`, `CHANGELOG.md`, and `docs/A3-DESIGN.md` changed.
- The six-value taxonomy is consistent in both documents.
- `no_executor_mapping` is explicitly distinguished from `gate_rejected`.
- `rrx.agent.planner.FALLBACK_REASONS` remains unchanged.
- `eval-spec-v1.9` remains at `fbe09c6`.
- No results artifacts changed.
- No holdout access.
- No API calls.

## eval-spec-v1.9 — stress-split definition corrected to the implemented one — 2026-08-29

Correction-only stage. No simulator, agent, config, or test change. No
`holdout` index accessed. `eval-spec-v1.8` remains unchanged at
`7ffb527`; this entry does not rewrite it or any earlier version.

### What changed

| Item | Class | Summary |
|---|---|---|
| §3.5 stress row | `CORRECTION` | Stress is now formally defined as an independent invariant check: N=300, seeds 5,000–5,299 |
| §3.5 stress prose | `CORRECTION` | Unimplemented adversarial-cohort prose removed; stress uses the ordinary frozen population distribution |
| §3.5 recovery note | `CORRECTION` | Records that stress has now been exercised while holdout remains unexercised |
| §8 item 8 | `CORRECTION` | Stale all-cancelled-stress reference corrected |
| A3-DESIGN §20 | `CORRECTION` | Stale all-cancelled-stress verification reference corrected |

### Why this is a correction, not a new experiment

`src/rrx/harness/splits.py::stress_indices()` has always returned
`range(5000, 5300)`, and the frozen population generator uses the ordinary
`configs/population.yaml` distribution for that split. No implementation
of the previously described adversarial cohort construction exists in the
repository or its git history.

The prior prose was therefore never an operationally reproducible
definition. Building an adversarial cohort now, after development results
are known, would introduce a new post-hoc experimental design. This
correction instead makes the specification match the implementation that
was actually built and run.

### Evidentiary consequence

This correction is an explicit downgrade in the strength of the stress
claim. The stress result establishes §5.2 invariant-holding on a third
independent sample from the frozen population. It does not establish
robustness to adversarial, shifted, or worst-case populations.

No artifact may describe the Stage 7.3 stress result as adversarial or as
worst-case robustness evidence.

### What did not change

- N=300.
- Seeds 5,000–5,299.
- `configs/population.yaml`.
- Simulator mechanics.
- §5.2 invariants.
- Criterion 1.
- Holdout arm set or single-use status.
- Any A3 comparison rule.
- `eval-spec-v1.8` at `7ffb527`.

### Provenance

The Stage 7.3 stress run was executed against seeds 5,000–5,299 using the
ordinary population generator. Its artifacts are retained unchanged.
`eval-spec-v1.9` formally corrects the specification before holdout so
that the run's actual construction and the normative definition agree.

`docs/A3-DESIGN.md §20` is corrected in this commit because it carried the
same stale all-cancelled-stress premise and had explicitly marked it as
pending verification. The verification is now complete.

### Verification required before commit

- `git diff --stat` contains only `EVAL.md`, `CHANGELOG.md`, and
  `docs/A3-DESIGN.md`.
- No changes under `src/`, `configs/`, `tests/`, `data/`, `SIM.md`, or
  results artifacts.
- `eval-spec-v1.8` remains at `7ffb527`.
- No new `authorized=True` holdout call site.
- No holdout artifact exists.
- No API calls made.
- The v1.7 comparator/tie-set rule is byte-unchanged.
- All stale stress-specific references identified in the review are either
  corrected or explicitly historical/flagged.

### Not done

No holdout run. No sensitivity run. No stress rerun. No simulator or
agent implementation change. No result numbers changed.

## eval-spec-v1.8 — pre-holdout scope, undeclared omissions, and one added invariant — 2026-08-29

Pre-registration-only stage. No simulator, agent, config, or test change.
No `holdout` index accessed. Committed before the single authorized
`holdout` run, so every rule under which that run is scored predates its
results.

### What changed in the specification

| Item | Class | Summary |
|---|---|---|
| A | `AMENDMENT` | `holdout` = {A0, A1, A2-strengthened, A3-D, A4}. A3-LLM excluded for budget, not performance. Inference of an A3-LLM `holdout` figure prohibited |
| B.1 | `AMENDMENT` | §6A's N=2,000 confirmation of GPT-C2 not executed; all A3-LLM figures are N=500 |
| B.2 | `AMENDMENT` | §8 item 4's three repeat runs not executed; **no nondeterminism evidence exists** |
| C | `CORRECTION` | Sweep is 26 cells, not 22; 80% threshold unchanged, pass mark 21/26; membership untouched |
| D | `AMENDMENT` | Criterion 5's two LLM-named failure modes are injected against a stubbed planner |
| E | `INVARIANT` | Gate-accepted proposals must have a legal executor mapping; added to §5.2, scored under criterion 1 |

### On B.2 — the omission with the widest reach

The three repeat runs were prescribed precisely because cache replay
cannot measure variance and `temperature` could not be pinned to 0. All
three legs of §8 item 4's determinism argument are now absent:
`temperature=1` is forced by the endpoint, the repeat runs were never
built, and cache replay is byte-identical by construction. The honest
position is that A3-LLM's single N=500 figure is one observation from a
process of unmeasured variance. That is what this entry declares, and no
artifact may imply otherwise. This omission was silent until this entry;
declaring it is the point of the entry.

### On E — why an invariant, not a limitation

The catch-all branch in `src/rrx/harness/runner.py` collapses two
distinct events — a gate rejection, and a gate acceptance the executor
cannot honour — into one indistinguishable ledger outcome. Verification
against `26ba176` indicates the second is unreachable via the implemented
A3-D and A3-LLM callers, but that rests on caller discipline rather than
on the enforcement layer, and no regression test proves it. Documenting
it as an accepted limitation was considered and rejected: the
gate/executor boundary is the specific thing this project asks a reader
to trust. It is fixed and tested before freeze.

### What was deliberately NOT changed

- **Criteria 2 and 3, including the comparator tie-set rule, are frozen at
  `eval-spec-v1.7` (`7fde138`) and are not touched.**
- **Criterion 1 is not weakened.** Stress remains required and will be
  wired/run before `code-freeze-holdout`.
- **Failure injection is not redesigned.** It is already substantially
  implemented and tested.
- **`temperature` is not made an evaluation rule.** Existing environment
  evidence is retained in `results/tuning_log.md` and `LIMITATIONS.md`.

### Verification required before commit

- `git diff --stat` shows `EVAL.md` and `CHANGELOG.md` only.
- Nothing modified under `src/`, `configs/`, `tests/`, `data/`, `SIM.md`,
  `docs/A3-DESIGN.md`.
- `git grep -n "authorized=True"` returns no new call site.
- `pytest -q` and `ruff check .` unchanged from `26ba176`.
- No holdout artifact exists.

### Not done in this entry

No `holdout` run. No `stress` run. No sweep. No code — including the
item-E enforcement fix. No `results/sensitivity.md` regeneration.

## eval-spec-v1.7 — Holdout comparator tie-set rule (evaluability-defect amendment) — 2026-08-28

`[CONSEQUENTIAL-3]` A NEW CONSEQUENTIAL METHODOLOGICAL DECISION /
VALIDITY-DEFECT AMENDMENT, not a recovered historical rule and not a
clarification.

**The defect.** `EVAL.md §7` criterion 2 requires A3 to exceed "the
best-performing bounded non-agent arm's rate" and separately states that
a tie among bounded arms "is reported explicitly, not silently resolved
by point estimate alone" — but never specifies what A3 must clear when
the best-performing arms are themselves tied. Criterion 3 compounds
this: it ties the contact-budget check to "the SAME bounded arm that won
the rate comparison for that metric," which presumes a single winner
exists. Neither a single-arm point-estimate tie-break nor a multi-arm
tie-set requirement is authorized anywhere in the frozen text. This is a
genuine evaluability gap in the original criteria — they cannot be
mechanically applied when the best-performing bounded arms are
statistically indistinguishable — not an ambiguity resolvable by reading
them more carefully.

**Why now.** The DEV paired-bootstrap analysis
(`diagnostics/stage5d_dev_statistical_results.md`, committed `06b43a8`)
found A1 and A2-strengthened statistically indistinguishable on invoice
recovery (A1 − A2-strengthened: +0.0010, 95% CI [−0.0060, +0.0080]) while
both clearly separate from A0. This DEV result did not create the
defect — it was already latent in the frozen §7 text — but it is what
surfaced it, ahead of holdout access. Consistent with this project's
standing discipline against letting evaluation definitions bend to a
specific result, this gap is closed prospectively, before any holdout
run, rather than left to be resolved ad hoc once a holdout tie is or
isn't observed.

**The new rule (`EVAL.md §7`, new paragraph appended after the existing
criteria):**

1. Per primary metric, the comparator determination uses HOLDOUT data
   only — never DEV.
2. Identify the bounded arm with the highest holdout point estimate on
   that metric.
3. The comparator set = that arm, plus every other bounded arm whose
   pairwise 95% CI against it (on holdout) includes zero.
4. A3 satisfies criterion 2 on that metric only if it beats EVERY member
   of that set, each difference's 95% CI excluding zero.
5. A multi-arm comparator set is reported explicitly (unchanged
   tie-reporting language).
6. Criterion 3's contact-budget check inherits the same comparator set —
   A3 must satisfy both contact constraints against every member, not
   just one arm.
7. A single-arm comparator set reduces exactly to the pre-existing §7
   criteria — no behavior change in the non-tied case.

**This rule is conservative, not permissive:** widening the comparator
set to every arm statistically tied with the top performer can only add
arms A3 must beat and contact constraints A3 must satisfy — never shrink
the set or relax a constraint. It does not lower the bar to make any
future A3 result more likely to pass.

**Frozen before holdout access.** As of this entry, holdout has not been
run. This rule is adopted before any holdout arm outcome exists, so it
cannot have been shaped by a holdout result.

**No DEV result was used to choose the eventual holdout comparator.**
The DEV tie is cited above only as the evidence that motivated closing
this gap now; it plays no role in which arms end up in any future
holdout comparator set — that set is determined solely by holdout data,
per the rule above, once holdout is run.

**A1 unaltered.** `EVAL.md §4.3`'s canonical A1 adoption
(`eval-spec-v1.6`) is unaffected; this entry does not touch A1's
content, schedule, or status.

No file under `src/` or `tests/` changed. No simulator, gate, or A3-D
change. No A0/A1/A2/A3-D cohort run, DEV or holdout. No comparator
selected.

## eval-spec-v1.6 — Canonical A1 content/remedy adoption — 2026-08-28

`[CONSEQUENTIAL-2]` A NEW CONSEQUENTIAL DECISION, not a recovered
historical specification and not a clarification. `EVAL.md §4`'s A1 row
("Same two contacts to everyone at T+0 and T+3, regardless of state or
reason") has specified A1's schedule since this section's original
authorship (`d04d158:EVAL.md`) and was never rewritten. It never
specified the contact's remedy/content, and no commit before this one
filled that gap.

A repository-wide provenance investigation (2026-08-28, read-only, no
file changed) established: the only executable A1 implementation
anywhere, `tests/test_stage5_falsification.py::a1_action_for_day`
(introduced `cdd118a`, Day 2 Stage 5), chose `card_change` uniformly,
with its own docstring admitting the choice was "declared here, since
the task does not specify one." That file and `SIM.md §8` label the
construction "A1-ish" throughout, never plain "A1."
`diagnostics/day3_baseline_headroom.py`, which later reused it to
compute headroom figures, states in its own header: "NON-CANONICAL
DIAGNOSTIC OUTPUT... not part of the frozen A0-A4 arm registry." Unlike
A2-corrected-v1/A2-strengthened, A1's content was never moved into
`src/` or written into `EVAL.md` prose the way A2's was
(`§4.1.1`/`§4.1.2`).

`EVAL.md §4.3` (new) now formally adopts `card_change` at both T+0 and
T+3 as canonical A1. Full rationale in that section; summary:

- Two uniform operationalizations were possible (`card_change` or
  `topup_reminder` at both contacts) — "regardless of state or reason"
  rules out anything decline-code-dependent. Neither was historically
  specified.
- `card_change` is value-bearing for ≈46% of the population
  (`card_expired`+`debit_instrument_blocked`+`card_not_enrolled`-aliases
  = 34%, plus the `card_chargeable=false` half of `ambiguous_decline` at
  `population.yaml`'s `p_card_cause=0.50`) vs. `topup_reminder`'s ≈44%
  (`insufficient_funds` + the fund-driven half of `ambiguous_decline`).
- Mechanically decisive, independent of the population math: `SIM.md
  §3`'s dues-naming acceleration rule (`funds_available_from =
  min(original, t_engage + Exponential(mean 0.5))`, strictly positive)
  means a topup sent on day 3 — A1's second contact — could never affect
  day 3's own retry, and no later retry exists, so `topup_reminder`
  would make A1's SECOND contact a structural no-op for its entire
  matching bucket. `SIM.md §4`'s within-day-ordering ruling gives
  `card_change` no such lag: a day-3 engagement is visible to day 3's
  own retry check. Adopting `card_change` keeps both of A1's contacts
  mechanically live; `topup_reminder` would not have.
- Recorded to show the choice does not lower A1's bar to make A3-D look
  better — not to claim A1 will win anything. No A1 result of any kind
  exists at the time of this entry.

**Temporal ordering, disclosed explicitly.** The `card_change`
operationalization predates A3-D entirely (Day 2 Stage 5, before
`docs/A3-DESIGN.md §10A` existed). This entry's formal *adoption* of it,
however, comes strictly after A3-D's first raw dev result: run ID
`a3d-dev-20260828-01`, git SHA
`e829161b8b174d2afca317f571048810b426b587`, executed and recorded
2026-08-28 (A3-D configuration #1 under the already-tagged
`eval-spec-v1.5` `§10A`). No A3-D-vs-anything comparison has been
performed at any point up to and including this entry; the content
choice was not selected by observing that result. `results/
a3d-dev-20260828-01/` is untouched by this entry and remains valid as an
A3-D configuration #1 observation; formal A3-D-vs-A1 comparison is
deferred until a canonical A1 dev run exists.

**§5.2 scope, resolved for A1.** `EVAL.md §4.3` also records, as a new
interpretive decision (not a rewrite of the invariant, the gate, or
A3-D): §5.2's safety invariants are titled "Safety gates," enforced by
gate tests, and cross-referenced (`[AMENDMENT, eval-spec-v1.4]`) to
`docs/A3-DESIGN.md §8`'s R1-R8 mechanism, which only
`rrx.harness.runner.run_episode_a3` (A3-D/A3-LLM) invokes.
`rrx.sim.engine.run_episode` (A0/A1/A2) has no gate, `Proposal`, or
`reason_code` mechanism at all. §5.2 is therefore read as scoped to the
agent execution/gate pathway; A1's naive, condition-blind schedule
reaching e.g. `payment_risk_check_failed` (which A2's own policy
explicitly excludes) is adopted as A1's deliberate strawman role
(`EVAL.md §4`: "Strawman"), not a violation of §5.2.

**The existing §7 illustrative figure ("best-bounded A1 at 0.4840")** is
relabelled, not recalculated or deleted, as historical/diagnostic
provenance from the pre-canonicalization `A1-ish` construction — see
`EVAL.md §4.3`'s closing paragraph. Whether a canonical A1 dev run
reproduces it is an open question; no canonical A1 run has been
executed.

**`results/tuning_log.md` does not exist.** Not created by this entry;
its creation is not required by any existing frozen instruction consulted
here. If a later stage logs A3-D configuration #1 or a future A1
configuration, that entry must state honestly that it was written after
execution, not backdated.

No file under `src/` or `tests/` changed. No simulator, gate, or A3-D
change. No A0/A1/A2/A3-D cohort run. No comparator selected.

## eval-spec-v1.5 — A3-D decision-table pre-registration — 2026-08-27

Tagged before `src/rrx/agent/policy.py` exists and before any A3-D episode has
been executed. Every number and rule in this entry was fixed with no A3-D result
of any kind in existence.

`docs/A3-DESIGN.md §10` (frozen at `eval-spec-v1.4`) ends with: *"The concrete
decision table is implementation, not this design freeze."* `EVAL.md §4.2`
specifies A3-D only as *"a pure, deterministic function of `EpisodeView`."*
Neither document contained a single decision rule. This entry closes that gap
ahead of implementation, adding `docs/A3-DESIGN.md §10A` — a 16-rule ordered
list, first-match-wins, total over every reachable `EpisodeView`. Each rule is
tagged `[FORCED]` (derivable from `SIM.md` mechanics or gate constraints),
`[FORCED mechanically]` (the mechanism makes every action a provable no-op), or
`[DESIGN]` (a genuine choice with no frozen basis). Full text in §10A.

Two mechanical results underpin the table and are recorded here because they are
falsifiable claims, not preferences:

1. **A dues-naming message cannot affect an auto-retry on the day it is sent
   or later than day 2.** `SIM.md §3`'s acceleration rule is
   `funds_available_from = min(original, t_engage + Exponential(mean 0.5))`. The
   exponential draw is strictly positive, so funds arrive strictly after
   `t_engage`, and `SIM.md §4`'s retry test `t >= funds_available_from` fails on
   day *t* itself. With the last retry at T+3, a topup reminder sent on day 3 or
   later can never affect invoice recovery. Combined with `SIM.md §5`'s
   at-opening restriction (which excludes `insufficient_funds` from post-halt
   rescue, since it opens `card_chargeable = true`), days 3+ are dead for that
   bucket entirely. Rules R-06/R-07 STOP accordingly.
2. **Three opening conditions admit no value-bearing action at all.**
   `transaction_limit_exceeded` (`blocked_until` beyond every retry day,
   `card_chargeable = true` at opening), `bank_technical_error` after retry
   exhaustion (same at-opening property), and post-halt `insufficient_funds`.
   Rules R-03, R-05, R-06 STOP.

### A. `[D-1]` `TERMINAL_SUBSCRIPTION_STATES` amended to include `"active"`

`src/rrx/harness/runner.py`'s terminal set was `{"cancelled", "expired"}`.
`_retry_succeeds` sets `subscription_state = "active"` on invoice recovery, so a
recovered episode remained non-terminal, kept its budget, and produced full
`wakeup` ticks on every subsequent wake-up day — each requiring a mandatory
`reason_code` from a closed enum containing no value that means "already
resolved."

`reason_code=terminal_state` was removed from the enum at `eval-spec-v1.4` on a
rationale addressed solely to `subscription_cancelled_by_customer`, which
terminates at T=0 before any tick (`engine.py:438-443`). That rationale is
correct and is not reopened. The post-recovery `active` case was simply not
considered in that pass. It is closed here by runner suppression rather than by
re-expanding the enum, mirroring §6's existing STOP semantics.

Declared consequences: `tick_type` distribution shifts for every arm run through
the A3 runner; `wait_rate`'s denominator (`EVAL.md §5.3`) correspondingly
excludes post-recovery ticks, which is the intended reading. **NULL-POLICY
parity re-verified at 2,000/2,000 after the change** — see Verification below.

### B. `[D-2]` §7 `no_engagement_restraint` meaning column widened

From *"Withholding — low observed engagement this episode"* to *"Withholding or
stopping — either low observed engagement this episode, or a condition under
which `SIM.md §2`–§5 make every available action a mechanical no-op."*

The enum stays at 7 values and the row's admissible `decline_code` set is
unchanged. The alternative — routing the mechanically-dead conditions to `WAIT`
— was rejected because it would place environment-forced inaction in
`wait_rate`'s numerator, which is the precise error `EVAL.md §8` item 8 already
prohibits for the cancelled-at-open bucket. This is a wording clarification
required for §10A's own rules (R-03, R-05, R-06, R-07) to be consistent with §7
as written — it changes no admissibility set and no test asserts exact wording.

### C. `[CONSEQUENTIAL-1]` §7 `remedy_match_topup` row widened

`ambiguous_decline` added to the admissible `decline_code` set for
`remedy_match_topup`, and correspondingly to
`ADMISSIBLE_DECLINE_CODES[REMEDY_MATCH_TOPUP]` in
`src/rrx/agent/reason_codes.py`.

Rule R-15 sends a topup reminder to the ambiguous bucket on day 2, hedging the
funds branch. `population.yaml#/opening_conditions` sets `p_card_cause = 0.50`,
so half that bucket is funds-caused and the remedy genuinely matches. §7 already
admits `ambiguous_decline` under `post_halt_rescue`; its absence from
`remedy_match_topup` was an omission. Corrected rather than worked around by
emitting a less accurate reason code.

### D. `[D-5]` A3-D adopts A2-strengthened's contact schedule unchanged

On the card-broken bucket, A3-D contacts at T+0, T+3, and T+5-if-halted —
identical to `rrx.baselines.a2_variants.a2_strengthened_action_for_day`
(`EVAL.md §4.1.2`). The single intended difference is that A3-D's T+3 contact is
conditional on the withhold predicate (§10A.3) while A2's is unconditional.

A mechanically stronger schedule was available and was declined. `SIM.md §4`'s
within-day ordering means a contact on day *t* is visible to that same day's
retry, so a T+1 contact reaches the retries at T+1, T+2 and T+3 while a T+3
contact reaches only T+3; front-loading would very likely raise A3-D's invoice
recovery. It is not adopted because A3-D is the control arm for A3-LLM
(`EVAL.md §4.2`) and the reference point for any A3-D − A2 reading. Changing both
the schedule and the decision logic would confound adaptivity with scheduling and
leave neither effect identifiable.

Recorded explicitly so that adopting the stronger schedule later is visible as a
new tuning configuration and not as a clarification.

### E. `[D-7]` Post-halt rescue exempt from the withhold predicate

R-11 contacts whenever the subscription is halted at day 5 with budget
remaining, regardless of engagement history. Post-halt the only reachable value
is subscription rescue (`EVAL.md §1.3`, `SIM.md §5`); withholding would save a
cancellation hazard of 0.0225 and forfeit an attempt at one of `EVAL.md §7`'s two
primary metrics. Declared as a deliberate asymmetry rather than left implicit.

### Verification

- `python -m pytest -q --ignore=tests/test_a3d_policy.py`: **622 passed, 1
  failed** — the failure is the pre-existing, documented
  `test_stage5_falsification.py::test_1_policy_ordering` (A2 not
  significantly beating A1 on invoice recovery on this CRN draw); unchanged
  by this entry and not newly introduced by it.
- `python -m ruff check .`: all checks passed.
- `git diff --stat -- src/rrx/sim/`: empty — the simulator is untouched.
- `tests/test_a3_runner_parity.py`: **2/2 passed** — exact `EpisodeResult`
  and day-30 `EpisodeView` parity between A0 and the NULL-POLICY-driven A3
  runner over all 2,000 `dev` episodes, re-verified after item A.
- `tests/test_a3d_policy.py`: added this pass — totality, determinism, gate
  compliance, reason-code admissibility, and per-rule reachability. Fails to
  **collect** (`ModuleNotFoundError: rrx.agent.policy`), not to assert — the
  expected state ahead of Stage 5E (§10A.9).

### Not done in this entry

- `src/rrx/agent/policy.py` is not written. This entry is specification only.
  Implementation follows in a separate pass and is a transcription of §10A; if
  any decision has to be taken during that transcription, the table is
  incomplete and work returns here.
- No A3-D episode has been executed. No A3-D result of any kind exists.
- A3-LLM is untouched.

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

## Day 2 Stage 5 — falsification tests, closed — 2026-08-26

Five falsification tests (`tests/test_stage5_falsification.py`, SIM.md §8).
No simulator, A0, A1-ish, A2, A4, or config change was made at any point in
this stage to obtain a result - every number below is as-observed.

### Results

|  | invoice recovery | subscription rescue |
|---|---:|---:|
| A0 | 0.3525 | 0.4055 |
| A1-ish | 0.4840 | 0.5095 |
| A2 | 0.4485 | 0.5180 |
| A4 (equal 3-contact budget) | 0.5465 | 0.5670 |

A4 − A2: invoice recovery +0.0980 (CI [+0.0855, +0.1115]); subscription
rescue +0.0490 (CI [+0.0390, +0.0595]).

### Test-design defect (corrected, not a simulator finding)

The original A4 arm used exactly one contact while A1-ish/A2 could use up
to three - not an equal-budget comparison, so the original A4-vs-A2 result
(A4 invoice recovery 0.4545) **is not, and must not be described as, a
simulator falsification or a falsification of the A4 oracle.** It was an
arm-definition defect. Corrected by giving A4 the identical 3-contact
budget (`episode.yaml#/agent_budget/max_contacts_per_episode`), applying
its existing latent-informed decision logic (unchanged: which content, for
which condition, chosen from full T=0 latent access, never from future RNG
outcomes) across up to three attempts instead of one. Under the corrected
budget A4 clearly beats A2 on both metrics (table above) - an
arm-definition correction restoring the intended comparison, not tuning
toward a desired result.

### Genuine falsification finding: the ordering hypothesis is rejected

`SIM.md §8` test 1's hypothesis (A4 > A2 > A1-ish > A0) is **rejected**,
specifically and only because **A1-ish beats A2 on invoice recovery**
(0.4840 vs 0.4485; paired-bootstrap diff -0.0355, CI [-0.0465, -0.0250],
clearly excludes zero). Mechanism verified, not merely asserted: A2's own
frozen schedule places its second contact for the card-broken bucket and
`ambiguous_decline` at T+5/T+7 - always after the T+3 invoice-retry
boundary, so those contacts can only ever affect post-halt rescue, never
invoice recovery. A1-ish's naive fixed T+3 contact lands exactly on the
last retry day, and under the within-day-ordering ruling, that same-day
engagement is visible to that day's own retry check - a real chance A2's
schedule structurally forfeits on the card-broken + `ambiguous_decline`
buckets (58% of the population). No simulator or policy change was made to
alter this finding; it stands as reported. **This is not a claim that "the
simulator failed"** - every other mechanism it depends on (the retry gate,
CRN, the halt boundary, the responsiveness signal) passed its own
falsification test this stage. It is a specific, actionable finding about
A2's frozen schedule.

### Test 2 (wrong-remedy null) — PASSED, with a flagged stale figure

Recovery comparable to A0 (WRONG_REMEDY 0.3595 vs A0 0.3525). Actual
contact ratio: **1.8378× A2**, not 3×. `SIM.md §8`'s "3x" figure predates
A2's exact schedule being fixed and is flagged as stale/unsupported by the
current A2 schedule - not tuned toward, recorded as observed.

### Tests 3–5 — PASSED

- **Test 3 (timing null):** post-halt topup effect exactly zero (636/636
  `insufficient_funds` episodes byte-identical to A0).
- **Test 4 (CRN identity):** 0 mismatches across all arms, including the
  corrected A4, over 300 episode indices.
- **Test 5 (responsiveness-signal null, Stage 4B narrowed formulation):**
  adaptive-vs-control effect +0.0383 at baseline concentration (pre-declared
  threshold: must exceed +0.02 - met), +0.0173 at high concentration
  (pre-declared tolerance: within ±0.02 - met). θ_c variance collapsed
  >1000×.

### Empirical A4 reference - not a target

The A4 headroom over A2 (+9.8 points invoice recovery, +4.9 points
subscription rescue) is an **empirical oracle/reference gap under this
simulator's defined information and 3-contact budget** - not a
mathematical theoretical maximum, and not a guaranteed target for a future
A3.

A4 provides an empirical oracle/reference of 0.5670 subscription rescue
and 0.5465 invoice recovery under the frozen simulator's equal 3-contact
budget; A4 − A2 headroom is +0.0490 rescue and +0.0980 invoice recovery;
`EVAL.md §3.3`'s cited "15% relative target" (the `§7` it names is
referenced but not written as a section anywhere in `EVAL.md` - the figure
itself is real text at `§3.3`, not a fabricated number) would require A3
to reach approximately 0.5957 rescue from the A2 baseline of 0.5180
(0.5180 × 1.15); this exceeds the observed A4 empirical oracle/reference
of 0.5670, so the pre-registered target appears unreachable under the
frozen simulator, equal 3-contact budget, and A4's information set - this
is an empirical finding about the target's reachability, **not** a change
to the target or to `EVAL.md`.

### Test reporting (kept separate, per this closure's instruction)

- **Ordinary regression suite** (everything except the intentional Stage 5
  falsification assertions): all PASS.
- **Stage 5 falsification suite:** 4 of 5 hypotheses PASS (timing null, CRN
  identity, responsiveness-signal null, wrong-remedy null); **1 of 5 FAILS/
  REJECTED** (the policy-ordering hypothesis, for the A1-vs-A2 reason
  above - not weakened or altered to obtain a pass).

`python -m ruff check .`: all checks passed. Not committed. `EVAL.md` and
`SIM.md` untouched throughout Stage 5.

## eval-spec-v1.2 — 2026-08-26

Closes the specification/test inconsistency the Day 2 Stage 4B review
identified: `EVAL.md §3.4` still specified its original 16-field
`EpisodeView` surface while the implementation (and `tests/
test_no_latent_leak.py`'s enforcing allowlist) had already moved to the
narrower 10-field v1 surface documented in `SIM.md §10`. `SIM.md §0`
authorizes *logging and reporting* such a conflict without editing
`EVAL.md`, but not permanently redefining the enforced surface as if that
resolved it - so `EVAL.md` needed an actual amendment, following the exact
precedent `eval-spec-v1.1` already established for
`send_subscription_link` (a `[DEFECT, eval-spec-vX]` footnote, the frozen
text recorded rather than rewritten).

### EVAL.md — one footnote added, frozen text unchanged

`git diff -- EVAL.md`: exactly one added block, directly below §3.4's
16-field list (verified - no other line in the file changed). The footnote
(`[DEFECT, eval-spec-v1.2]`):

- records that 6 of the 16 fields have no honest producer anywhere in the
  built simulator (`decline_source`, `billing_cycle_day`,
  `completed_billing_cycles`, `customer_tenure_days`,
  `prior_pending_episodes`, `prior_recovery_channel`) and were not
  fabricated - producing them would mean inventing a new `[MODEL]`
  parameter or mechanism outside the frozen six;
- records the two time-representation renames: `next_auto_retry_date` →
  `next_auto_retry_day`, `contact_history[].ts` → `.day` - no calendar
  anchor exists anywhere in this simulator, and none is invented;
- enumerates, for the first time in this file, the three pre-registered
  sources of A3 advantage §3.4's own title names but never previously
  listed explicitly (assembled from this file's field grouping and
  `SIM.md`'s cross-references), and states each one's v1 status:
  retry-window timing (fully preserved), remedy matching (preserved via
  `decline_code` alone), channel selection (narrowed to within-episode
  adaptive contact - persistent episode-level response propensity inferred
  from observable `contact_history.engaged`, with cross-episode
  customer-history learning and tenure-based inference explicitly out of
  v1).

The frozen 16-field list itself is untouched - it remains the target
surface for a future version, not a claim about what v1 delivers now.

### Complete schema delta (EVAL.md §3.4 original -> v1 EpisodeView)

**Removed (6, no producer anywhere in the repository, not fabricated):**
`decline_source`, `billing_cycle_day`, `completed_billing_cycles`,
`customer_tenure_days`, `prior_pending_episodes`, `prior_recovery_channel`.

**Renamed + type-changed (2, RULING 1 - relative time, no calendar anchor):**
`next_auto_retry_date: date | None` -> `next_auto_retry_day: int | None`;
`ContactRecord.ts: datetime` -> `ContactRecord.day: int`.

**Retained fields with narrowed/clarified semantics (2):**
- `billing_amount_inr` - name and type unchanged, but now explicitly
  aliased to `invoice_amount_inr` (no independent recurring-price figure
  exists anywhere in the repository) rather than left as an independently
  undefined quantity.
- `decline_code` - name and type unchanged (`str`), but now explicitly
  defined as the observable, group-level `opening_condition_key` (e.g.
  `"ambiguous_decline"` for that bucket) rather than an unspecified
  granularity.

**Retained, unchanged (6):** `subscription_id`, `subscription_state`,
`invoice_amount_inr`, `days_since_first_failure`, `auto_retries_remaining`,
`budget_remaining` - and `contact_history` itself (its entry shape changed
per the rename above, but the field's presence/role did not).

### tests/test_no_latent_leak.py - enforcing test now genuinely agrees with EVAL.md

Updated the module docstring and the `EPISODE_VIEW_ALLOWED` comment to
state plainly that this allowlist enforces the CURRENT (eval-spec-v1.2
amended) `EVAL.md §3.4`, not a stand-in that merely happens to be narrower
than it. No change to the allowlist's actual contents (already correct
from Stage 4B) or to any test's pass/fail behavior.

### Verification

- `python -m pytest -q`: see the closure report for the exact count.
- `python -m ruff check .`: all checks passed.
- `latent.py`, all of `configs/`, retry/outcome mechanics, and A0/A2 policy
  behavior confirmed unmodified.
- Tagged `eval-spec-v1.2` after tests were confirmed green (see the
  closure report for the exact commit SHA).

## Day 2 Stage 4B — 2026-08-26

Completes the minimum honest EpisodeView boundary identified by the Day 2
Stage 4 gap analysis: EpisodeView is now actually constructed from real
simulator state, with a deliberately narrowed field set rather than
fabricated values for the fields with no honest producer. No Stage 5, no
A3, no gates - out of scope per this pass's brief.

### RULING 1 — relative time, [DESIGN] schema ruling

No calendar anchor exists anywhere in this simulator, and none is invented.
`EpisodeView.next_auto_retry_date: date | None` → `next_auto_retry_day: int
| None`; `ContactRecord.ts: datetime` → `ContactRecord.day: int`. Recorded
in `SIM.md §10`.

### RULING 2 — decline_code, group-level

`EpisodeView.decline_code` is the observable `opening_condition_key` itself
- `"ambiguous_decline"` for that bucket, never the resolved latent
Bernoulli cause. Matches population.yaml's own note ("A3 and A2 both see
only decline_code for this bucket"). Additive observation only -
`rrx.sim.engine.build_episode_view` reads `cohort.opening_condition_key`;
nothing about outcome resolution changes.

### RULING 3 — decline_source removed

Not modeled in v1: the term is undefined anywhere in `EVAL.md`, `SIM.md`,
or any config (verified by repository-wide search). Removed from
`EpisodeView` rather than fabricated. **v1 makes the remedy-matching
decision using `decline_code` alone.** Recorded in `SIM.md §10`.

### RULING 4 — channel-selection narrowed; no cross-episode history model

`customer_tenure_days`, `prior_pending_episodes`, `prior_recovery_channel`
removed from `EpisodeView`. The v1 channel-selection advantage is narrowed
to within-episode adaptive contact: inferring persistent episode-level
response propensity from observable `contact_history.engaged` alone. This
is a genuine narrowing of `EVAL.md §3.4`'s third pre-registered advantage,
not a silent drop - full reasoning and what remains/is removed recorded in
`SIM.md §10`.

### RULING 5 — tenure coupling not implemented

Confirmed (again) that `rrx.sim.latent._sample_channel_response_trait`
implements only the raw `Beta(mean, concentration)` draw - no
`tenure_coupling` logit shift, no seventh model parameter, `latent.py`
untouched this pass. `SIM.md §8`'s falsification test #5 is given a
narrowed definition in `SIM.md §10` (concentration-only manipulation,
matching the mechanism that actually exists) - **recorded, not implemented
or run.** Stage 5 work.

### RULING 6 — contact_history, real runtime logging

`_EpisodeState.contact_history: list[ContactRecord]` (engine.py); every
`_send_message` call now appends a record built from values it already
computes (`day`, `channel`, a `remedy` derived from `names_card`/
`names_dues` - `"card_change"` / `"topup_reminder"` / `"both"` for the
dual-content automatic email, matching `SIM.md §3`'s own action table -
`delivered=True` per `SIM.md §3`'s `"delivered (1.0 in v1)"`, and the
already-resolved `engaged` bool). Purely observational: nothing reads
`contact_history` back into engagement probability, card/dues effects, the
retry gate, contact budget, or either policy. Confirmed by the full test
suite passing unchanged (537 passed, same A0/A2 outcome behavior as before
this pass).

### RULING 7 — EpisodeView actually constructed

`rrx.sim.engine.build_episode_view(cohort, state, day, episode_cfg, split,
i) -> EpisodeView` - a positive construction (every field copied out as a
plain value; never a reference to `state`, `cohort`, `LatentState`, or an
RNG). Wired into `run_episode` via a new, fully backward-compatible opt-in
parameter: `run_episode(..., capture_view_at_day=None)` returns the exact
same bare `EpisodeResult` as before when omitted (verified: every existing
Stage 3 test, including the byte-identical replay-determinism test, passes
unchanged); passing an integer day additionally returns
`(EpisodeResult, EpisodeView | None)`, the `EpisodeView` captured as of the
end of that day's mechanics (`None` if that day is never reached - the
`subscription_cancelled_by_customer` early-return path). No agent or
planner created; nothing consumes the view for policy decisions.

### RULING 8 — final field set, billing-fields investigation

Investigated per the ruling before implementing:
- `billing_amount_inr` — **retained**, aliased to `invoice_amount_inr`. No
  separate recurring-price figure exists anywhere in the repository;
  `model_params.yaml`'s `valued_at: billing_amount_inr` never distinguishes
  the two. Defensible equivalence, not invention.
- `billing_cycle_day`, `completed_billing_cycles` — **removed/deferred**.
  No distribution or producer exists anywhere in the repository for
  either. Not invented.
- `subscription_id` — `f"{split}-{i}"`, the deterministic existing episode
  identity, as directed.

**Final v1 EpisodeView field set (10 fields, down from EVAL.md §3.4's 16):**
`subscription_id`, `subscription_state`, `invoice_amount_inr`,
`days_since_first_failure`, `auto_retries_remaining`,
`next_auto_retry_day`, `decline_code`, `billing_amount_inr`,
`contact_history`, `budget_remaining`.

### RULING 9 — EVAL.md untouched; conflict recorded in SIM.md instead

`EVAL.md` was not modified. The narrowing conflict with `EVAL.md §3.4`'s
16-field list is recorded explicitly in `SIM.md §10` (new section, per
`SIM.md §0`'s own rule: conflicts with `EVAL.md` are "a defect to be logged
and reported, never resolved by editing `EVAL.md`"), and in this entry.
The v1 observable surface is narrower than `EVAL.md §3.4`'s original list;
this is stated plainly, not minimized.

### RULING 10 — tests

New `tests/test_episode_view_construction.py` (16 tests): real runtime
construction, backward-compatible default return, `None` on an unreached
day, capture determinism, `contact_history` population and remedy mapping,
no-simulator-object check on real constructed instances, relative-day
retry-window fields (before/during/after halt), `decline_code` group-level
mapping (including `ambiguous_decline` specifically), `billing_amount_inr`
aliasing, and removed-fields-absent. `tests/test_no_latent_leak.py` updated
for the narrowed allowlists (`EPISODE_VIEW_ALLOWED`, `CONTACT_RECORD_
ALLOWED`, `_ALLOWED_FIELD_TYPES` - `date`/`datetime` dropped, no longer
used by any field) - all 18 of its tests (12 pre-existing Stage 4 + this
pass's field-set updates) still pass.

### Verification

- Targeted: `tests/test_no_latent_leak.py` (18 passed),
  `tests/test_episode_view_construction.py` (16 passed).
- `python -m pytest -q`: 537 passed.
- `python -m ruff check .`: all checks passed.
- `latent.py`, all of `configs/`, `EVAL.md`, retry/outcome mechanics, and
  A0/A2 policy behavior confirmed unmodified.
- Not committed.

## Day 2 Stage 3 — 2026-08-26

Thin end-to-end simulator: cohort generator, clock/retry engine,
action-effect resolver, A0, A2, and the first reproducible A0-vs-A2 result.
No A3, no manifest, no holdout, no Razorpay integration - out of scope per
this stage's brief.

### Discovered defect, fixed (authorized): `blocked_until` default

`src/rrx/sim/latent.py::draw_latent_state` defaulted `blocked_until` to
`BLOCKED_INDEFINITELY` (`math.inf`) unconditionally, overriding it only for
`bank_technical_error`. Since SIM.md §4's retry AND-gate requires
`t >= blocked_until` for every condition, this silently made auto-retry
success impossible for `insufficient_funds`, `ambiguous_decline`,
`card_expired`, `debit_instrument_blocked`, and `card_not_enabled_group` -
91% of the population - regardless of `card_chargeable`/
`funds_available_from`. This contradicted SIM.md §3's explicit claim that
transient-mode `insufficient_funds` customers recover "with no agent
action," and SIM.md's own "Discovered semantic clarification" scopes the
indefinite-block reading of "never" to `transaction_limit_exceeded` /
`payment_risk_check_failed` only. Confirmed empirically before the fix: a
2000-episode A0 dev run recovered invoices only via `bank_technical_error`
(51/51), zero via `insufficient_funds`.

Fix (authorized by user decision, 2026-08-26): default changed to `0.0`
(non-blocking); `transaction_limit_exceeded`/`payment_risk_check_failed`
now set `BLOCKED_INDEFINITELY` explicitly. Updated the three locked-behavior
assertions in `tests/test_latent_sampling.py` and re-pinned the four
affected cases in `tests/test_latent_snapshot.py` (the snapshot correctly
failed on this change - exactly what it exists to catch; only `blocked_until`
moved, every other pinned field is unchanged).

### Three model clarifications - applied to SIM.md (Day 2 Stage 3 final closing pass, 2026-08-26)

Recorded directly in `SIM.md` (§2, §4, §5) in this pass, labeled "Model
ruling" with the date, per CLAUDE.md's locked-file rule (edits authorized by
explicit user instruction). Earlier revisions of this changelog entry and of
`engine.py`'s docstrings described these as "approved 2026-08-26" while
still unrecorded in SIM.md; that was inaccurate and was corrected before
this pass ever labeled anything "approved" prematurely again.

- **Within-day ordering (SIM.md §4).** A message sent and engaged with on
  day t changes physical state before that day's end-of-day retry reads it.
  Implemented in `rrx.sim.engine._send_message` / `run_episode`'s day loop:
  contacts/emails scheduled for day t are resolved before day t's retry
  check.
- **`blocked_until` "never" (SIM.md §2).** Non-blocking (`0.0`) for every
  row except `transaction_limit_exceeded`/`payment_risk_check_failed`,
  which receive the indefinite-block value explicitly. See the "Discovered
  defect" entry below - this is the specification-level record of that
  fix.
- **Post-halt card rescue, narrower form (SIM.md §5).** Only episodes whose
  `card_chargeable` was `false` AT OPENING may be rescued post-halt when
  `card_chargeable` becomes `true`. Episodes already `card_chargeable =
  true` at opening (`insufficient_funds`, `transaction_limit_exceeded`,
  `payment_risk_check_failed`) never transition to `active` merely because
  a post-halt message occurs.

  **Why this rule exists - discovered implementation bug it fixes:** the
  ORIGINAL (broader) rule as first implemented tested the CURRENT value of
  `card_chargeable` at the end of every post-halt message, not whether that
  message caused a false→true TRANSITION. Since `insufficient_funds`/
  `transaction_limit_exceeded`/`payment_risk_check_failed` all have
  `card_chargeable = true` from T=0 (SIM.md §2), this meant the halt-
  transition automatic email alone flipped `subscription_state` to
  `"active"` unconditionally the instant it was sent, with no engagement
  required. Confirmed empirically before the fix: of 2000 dev episodes,
  every single non-recovered `insufficient_funds` (195/195), `transaction_
  limit_exceeded` (23/23), and `payment_risk_check_failed` (21/21) episode
  was reported as rescued (100%). Card-broken/ambiguous-decline buckets
  were unaffected in practice, because for those, `card_chargeable`
  becoming true pre-halt would already have recovered the invoice on the
  next retry day, so halting with `card_chargeable` already true could only
  happen via the very message being evaluated.

  **Fixed:** `_EpisodeState` now records `card_chargeable_at_opening` once,
  at construction, and `_send_message`'s rescue check requires it to be
  `False`. Re-ran the 2000-episode dev smoke after the fix: of the same
  195/23/21 non-recovered episodes, 0/0/0 are now reported as rescued -
  confirming the fix is genuinely connected to the runtime path, not merely
  documented. A0/A2 subscription rescue rate dropped from 0.5850/0.6850 to
  0.4055/0.5180; invoice recovery rate (0.3525/0.4485) is unchanged, as
  expected - this fix only ever touches `subscription_rescued`.

### A2 policy verified against the repository, not memory (Day 2 Stage 3 final closing pass, 2026-08-26)

Searched `EVAL.md`, `SIM.md`, `configs/`, and the whole repository for any
written A2 reference-policy schedule. Finding: **none exists.** `EVAL.md`
has no `## 4.` heading (confirmed again by listing every `##`/`###`
heading - the file jumps `## 3. Population` -> `## 5. Metrics`). `SIM.md`
defines world mechanics only and never prescribes agent policy. No
policy/reference-policy file exists anywhere in `configs/` or the repo
(confirmed by search - the only files matching "reference policy"/"a2
policy" are this changelog and `engine.py` itself). `EVAL.md §3.2`'s table
states `insufficient_funds`'s remedy as "Top-up reminder **before** retries
exhaust" with no mention of any card-change fallback, at T+5 or otherwise.
No occurrence of the string "T+5" exists in `EVAL.md` or `SIM.md` at all.

**Conclusion: the entire A2 day-offset schedule in `rrx.sim.engine.
a2_action_for_day` - including every T+0/T+1/T+5/T+7 in it - was dictated
directly in conversation and has no other source.** It was never copied
from EVAL.md; describing it as "EVAL.md §4's reference policy" (as an
earlier turn did) does not resolve to real text in the file. This is not a
new finding this pass invented - it restates and confirms what the Stage 3
audit already established about `§4` not existing - but this pass
additionally confirms there is no T+5-for-`insufficient_funds` rule
anywhere in the written spec to have a discrepancy against: the current
code (no fallback for `insufficient_funds`, ever) matches the *absence* of
any such written rule, and separately matches `EVAL.md §5.2`'s actual,
real, written gate ("Card-change prompts for `insufficient_funds`: 0",
`test_gate_remedy_match.py`, which does not exist yet as a file). The
previously-written "`EVAL.md §5.2` supersedes `§4`" framing is dropped -
there is no `§4` for anything to supersede. `engine.py`'s
`a2_action_for_day` docstring has been corrected accordingly.

### New simulator modules

- `src/rrx/sim/rng.py`: `rng_for_child_stream` - extends the frozen
  per-variable substream isolation to per-message/per-engagement draws via
  `seed_for_substream`'s existing hash (`"<root>:<child>"`), without a ninth
  top-level substream and without modifying `latent.py`'s frozen
  `SUBSTREAM_NAMES`/`rng_for_substream`.
- `src/rrx/sim/cohort.py`: opening-condition selection (from the
  authoritative `population.yaml#/failure_mix/conditions`, via a
  `failure_condition:opening_condition_select` child stream kept independent
  of the existing ambiguous-cause Bernoulli) and invoice-amount sampling
  (first real use of the `invoice_amount` substream; authority resolved by
  the same `owner_path` convention that resolved failure-mix -
  `tests/test_invoice_amount_representations_agree.py` confirms
  `population.yaml`/`episode.yaml`'s two invoice representations agree at
  baseline).
- `src/rrx/sim/engine.py`: the clock, retry AND-gate, action-effect
  resolver (card-naming, dues-naming/top-up), A0 (no contact, ever) and A2
  (EVAL.md §5.2-compliant reference policy - `insufficient_funds` gets only
  a T+1 top-up, never a card-change fallback, so the "0 card-change prompts
  for insufficient_funds" gate holds by construction).
- `src/rrx/sim/run_stage3.py`: batch A0/A2 run (dev, 2000 episodes, seeds
  1000-2999) plus paired bootstrap 95% CI (reusing
  `model_params.yaml#/sweep/win_criterion`'s existing convention, not a new
  statistical framework). Prints to stdout only - no manifest, no results
  directory.

### Tests

`tests/test_cohort.py`, `test_engine_mechanics.py`, `test_engine_policies.py`,
`test_topup_crn.py`, `test_stage3_run.py`,
`test_invoice_amount_representations_agree.py` (new);
`test_failure_mix_representations_agree.py` now imports its key-mapping from
`rrx.sim.cohort` instead of a duplicated local copy.

### Regime A cancellation - not implemented (scope exclusion, not a gap to silently fill)

No cancellation-hazard mechanism exists anywhere in `rrx.sim.engine` -
nothing reads `episode_cfg["latent"]["cancellation"]`, no hazard draw, no
LTV computation. This was an explicit, stated Stage 3 scope exclusion (the
10-item SIMULATOR SCOPE list has no cancellation/Regime A item), not
something dropped silently. Consequence: there is no runtime "Regime A
cancellation cannot occur in Regime B" gate to test, because there is no
Regime A mechanism for such a gate to guard. Any claim that Stage 3
validates Regime A/Regime B cancellation-gating behavior would be false -
Stage 3 validates nothing about cancellation, in either direction, and no
test in this stage's suite asserts otherwise. This must be built as real
work in a later stage, not invented to make a test pass.

### Stage 3 closing pass — 2026-08-26

- Added `test_no_retry_evaluated_after_halt_even_if_and_gate_would_pass`
  (`tests/test_engine_mechanics.py`): monkeypatches `draw_latent_state`/
  `sample_cohort_episode` to force a state that provably satisfies the full
  retry AND-gate on a post-halt day, and confirms `invoice_recovered`
  stays `False` - closing the coverage gap flagged in the Stage 3 audit
  (previously only a statistical, black-box observation existed).
- Added `test_run_episode_full_replay_is_byte_identical`
  (`tests/test_engine_mechanics.py`): calls `run_episode()` twice with
  identical inputs across both arms and 120 episode indices, asserting full
  `EpisodeResult` equality - exercises the engine's own engagement/
  completion/topup RNG consumption, not just cohort/latent determinism -
  closing the other coverage gap flagged in the audit.
- Added a `payment_risk_check_failed` case to
  `tests/test_latent_snapshot.py`, pinning `blocked_until ==
  BLOCKED_INDEFINITELY` for it. The blocked_until defect fix's `elif key in
  ("transaction_limit_exceeded", "payment_risk_check_failed")` branch
  previously had only `transaction_limit_exceeded` pinned by a snapshot
  case; a future edit dropping `payment_risk_check_failed` from that tuple
  would have passed every existing snapshot test.
- Corrected "approved 2026-08-26" language in `engine.py`'s module
  docstring and `a2_action_for_day`'s docstring, and "frozen rulings" in
  `test_engine_mechanics.py`'s docstring, to accurately describe both
  rulings as proposed/pending - neither has been approved or written into
  SIM.md.
- `src/rrx/sim/run_stage3.py`: renamed the printed/reported metric labels
  "wasted attempts" → `no_op_contacts` and "hard-decline retry rate" →
  `remedy_mismatch_rate`, since there are no agent-controlled payment-retry
  attempts in this model (Razorpay's auto-retry is the only retry mechanism,
  and the agent has no retry action at all - EVAL.md §1.1/§1.2) and
  describing a mismatched contact as a "retry attempt" or "hard decline
  retry" mischaracterizes what it actually is (a contact whose content
  didn't change physical state). Underlying calculations unchanged; only
  the local variable names and printed labels moved.

### Final closing pass — narrower rescue implemented, SIM.md updated (2026-08-26)

- Implemented the narrower post-halt rescue rule in `rrx.sim.engine`
  (`_EpisodeState.card_chargeable_at_opening`, gated check in
  `_send_message`) - see above.
- Added `test_a_card_broken_at_open_episode_can_be_post_halt_rescued`,
  `test_b_already_chargeable_at_open_episode_cannot_be_post_halt_rescued`,
  and `test_insufficient_funds_and_kin_structurally_cannot_be_post_halt_
  rescued` to `tests/test_engine_mechanics.py`.
- Applied all three model clarifications to `SIM.md` (§2, §4, §5), labeled
  "Model ruling (2026-08-26, Day 2 Stage 3 closing)" - see above.
- Verified the A2 policy against the actual repository contents (see above)
  and corrected `engine.py`'s docstrings accordingly.
- Re-ran the 2000-episode dev smoke; numbers reported in the Stage 3 final
  closing report (not reproduced here to avoid a second source of truth for
  a non-formal smoke run).

### Verification

- `python -m pytest -q`: 515 passed.
- `python -m ruff check .`: all checks passed.
- No frozen spec file modified except the three authorized `SIM.md`
  clarifications recorded above; `EVAL.md`, all of `configs/`, and
  `data/decline_codes.yaml` remain untouched.

## Day 2 Stage 2 — 2026-08-26

Sweep-cell materialization and a reproducibility control. No agent, clock,
cohort generator, or manifest — those remain out of scope per this stage's
brief.

### Cell -> resolved-config resolver

- `src/rrx/spec/resolver.py`: new pure `resolve_config(episode_cfg,
  population_cfg, cell)`, dispatched by each cell's declared `handle` (not
  by pattern-matching `cell_id`). Returns fresh deep copies; never mutates
  its inputs. Resolves all 26 `enumerate_cells()` cells except
  `invoice_amount`, which raises `NotImplementedError` naming the
  unresolved invoice-authority question (`population.yaml#/invoice_amount_inr`
  vs `episode.yaml#/invoice_amount_inr#mu_expression` - two independent
  representations, no consumer for either today, so no basis to pick one).
- `failure_mix_weights` bucket-mass cells update only
  `population.yaml#/failure_mix/conditions` - the representation
  `model_params.yaml`'s `owner_path` names and the one
  `rrx.spec.registry.expand_to_conditions` actually consumes.
  `population.yaml#/opening_conditions[*]/weight` is a separate
  representation (consumed only by
  `tests/test_population_matches_decline_codes.py` and, apparently,
  `EVAL.md §3.2`'s hand-maintained table - the `make docs` generator that
  comment references does not exist in this repository) with no test or
  code proving the two agree. Left deliberately unsynchronized rather than
  silently patched to match, per the discovered-duplication rule for this
  stage - see `tests/test_sweep_materialization.py`'s module docstring and
  `test_failure_mix_bucket_cell_changes_only_failure_mix_conditions`.

### Sweep reachability

`tests/test_sweep_materialization.py` classifies all 26 cells:
**10/26 simulator-reachable** (`balance_restore_timing` x2 handles x2,
`channel_response_propensity`, `card_change_completion_propensity`,
`failure_mix_weights.ambiguous_cause_split` - each has a live consumer in
`rrx.sim.latent`) and **16/26 materializer-only** (`invoice_amount`, the six
`failure_mix_weights` bucket-mass cells, `cancellation_hazard_and_ltv` - no
opening-condition selector, invoice sampler, or cancellation/LTV sampler
exists yet). Reachable cells get a smoke test proving the resolved config
moves the relevant sampled statistic in the declared direction relative to
baseline; materializer-only cells are resolved but no consumer is invented
to inflate the count.

### Reproducibility control

Not performance-motivated. `pyproject.toml`: `numpy>=2.0` -> `numpy==2.5.2`
(the installed version) - an unpinned lower bound lets a future numpy/RNG
implementation change silently shift every sampled value while the frozen
CRN seeding (`seed_for_substream`) and calling code stay identical.
`tests/test_latent_snapshot.py` pins six known `(split, episode_index,
opening_condition)` -> `LatentState` cases (one per SIM.md §2 mechanism
family, across both `dev` and `holdout`) recorded against numpy 2.5.2, so a
future deliberate dependency bump that changes sampled outputs fails loudly
here instead of silently.

### Verification

- `python -m pytest -q`: see run output in the Stage 2 report.
- `python -m ruff check .`: see run output in the Stage 2 report.
- No frozen spec file (`EVAL.md`, `SIM.md`, `configs/episode.yaml`,
  `configs/population.yaml`, `configs/model_params.yaml`) modified.
- Does not move or delete `eval-spec-v1` or `eval-spec-v1.1`. Does not tag
  `sim-v1` (deferred; manifest work is Stage 4).

## eval-spec-v1.1 — 2026-08-26

Not performance-motivated. No agent (A2, A3, or otherwise) exists yet in this
repository — Day 2 is still simulator-construction stage. These changes
close gaps and a documentation defect discovered while writing `SIM.md`,
under `EVAL.md §10`'s discovered-validity-defect clause.

### `send_subscription_link` excluded from the v1 action space

Q1 research (2026-08-26) found no primary Razorpay documentation supporting
a customer-facing link that clears an already-failed subscription invoice
for a domestic card — the claim `EVAL.md §1.2`'s action-space table makes for
that row. Three real Razorpay mechanisms exist and none matches: the
card-change email link restores the subscription but does not re-attempt
previous charges; manual invoice charge is Dashboard-only and explicitly
unsupported for domestic cards; Subscription Links are for initial
authorisation only, not existing-invoice recovery.

- `EVAL.md`: added a `[DEFECT, eval-spec-v1.1]` footnote immediately below
  the `§1.2` action-space table, recording the finding. The frozen table
  itself is unchanged, per `§10`.
- `SIM.md`: `send_subscription_link` removed from the action-space and
  message-content tables (`§3`); `link_clears_failed_invoice` removed from
  outcome resolution (`§5`) — invoice recovery is now auto-retry-only;
  `§6` Tier 3 family 5 (remedy completion propensity) now reads "card change
  only"; `§9` records the resolution.

### Two config gaps resolved — and genuinely swept

Both were flagged as open in `SIM.md` at Day 2 Stage 0 and are folded into
their existing `[MODEL]` families — no seventh family created.

- **`P(card | ambiguous decline)`** — `configs/population.yaml`'s
  `ambiguous_decline` entry gets `p_card_cause: 0.50` (`basis:
  project_inference`, max-entropy rationale) and
  `UNRESOLVED_intra_group_split` flips to `false`. Folded into
  `failure_mix_weights` via `configs/model_params.yaml`'s new
  `definition.ambiguous_cause_split`, `sweep_required: true`, cells
  `0.35` / `0.65` (±30%).
- **`bank_technical_error` clearance** — `configs/episode.yaml`'s `latent`
  section gets `bank_technical_error_clearance` (`Uniform(0, 2]` days).
  Folded into `balance_restore_timing` via `configs/model_params.yaml`'s new
  `definition.transient_block_clearance`, `sweep_required: true`, cells
  `[0, 1.4]` / `[0, 2.6]` (±30% on the upper bound).

**Correction (same day, before commit):** these two were initially marked
`sweep_required: true` with no `sweep.cells`, so they silently contributed
**zero** cells to `enumerate_cells()` — `sweep_required` was documentation
only, not enforced. `test_model_params_swept.py` did not catch this because
none of its checks looked inside a parameter's `definition:` block; only
top-level `handle`/`sweep.cells` were read. This is a gap in the `EVAL.md
§0` enforcement mechanism, not just these two entries, and is fixed here:

- `src/rrx/spec/registry.py`: `enumerate_cells()` now recurses into every
  canonical parameter's `definition:` block and generates cells for any node
  marked `sweep_required: true` with a `sweep.cells` low/high pair. Added
  `find_sweep_required_nodes()`, `unswept_required_entries()` (returns every
  `sweep_required` node with no matching cell), and `scalar_valued_handles()`
  (distinguishes a declared-scalar magnitude from a corrupted bucket-vector
  cell, for `test_failure_mix_simplex.py`'s companion check below).
- `tests/test_model_params_swept.py`: cell-count arithmetic updated
  **22 → 26** (28 with the topup toggle) — an **increase** in sweep
  coverage, not a relaxation: the old count of 22 simply omitted two
  `[MODEL]` parameters that should always have been in the grid.
  `test_failure_mix_contributes_twelve_cells` → **fourteen** (the six
  buckets' 12, plus `ambiguous_cause_split`'s own 2).
  `test_required_wins_is_ceil_of_eighty_percent` updated to `ceil(0.8×26)=21`
  / `ceil(0.8×28)=23`. `test_scalar_handles_have_two_directional_cells`
  rewritten to check per-`handle` rather than per-`parameter`, since
  `balance_restore_timing` now legitimately has two independent handles.
  Added `test_all_sweep_required_entries_produce_cells` (real config: no
  `sweep_required` node may contribute zero cells) and
  `test_sweep_required_with_zero_cells_is_detected` (regression, on a
  synthetic registry, reproducing today's exact bug shape to prove the
  detection mechanism itself works).
- `tests/test_failure_mix_simplex.py`: `test_all_generated_failure_mix_cells_are_valid_simplexes`
  now skips non-`dict`-valued cells (the new `ambiguous_cause_split` cells
  are scalars, not bucket vectors, and were never meant to be simplex-checked).
  Added `test_scalar_cells_are_declared_scalar_not_corrupted_vectors` as a
  companion so that guard cannot silently swallow a genuine defect: any
  non-dict `failure_mix_weights` cell must correspond to a handle explicitly
  declared scalar in `model_params.yaml`, or the test fails.

**Second correction (same day, before commit):** the first correction fixed
whether a `sweep_required` node contributes cells at all, but two sibling
checks in `tests/test_model_params_swept.py` —
`test_scalar_cells_are_thirty_percent_from_baseline` and
`test_probability_cells_within_clamp` — read only a parameter's top-level
`handle`/`sweep.cells` and so were still blind to anything nested inside
`definition:`. `ambiguous_cause_split`'s `0.35`/`0.65` was therefore enforced
as neither ±30% from its own `0.50` baseline nor within the `[0, 1]`
probability clamp — the same blindness `find_sweep_required_nodes()` exists
to fix, left in place in these two sibling tests. Fixed here, both extended
to reuse `find_sweep_required_nodes()`:

- `test_scalar_cells_are_thirty_percent_from_baseline` now also checks every
  definition-nested `sweep_required` node's cells against its own declared
  baseline at ±30%. `transient_block_clearance`'s cells are `[lower, upper]`
  day-bound lists, not a bare scalar — **chose option (2a)**: the check
  applies to the upper bound only (the `support_days_upper_bound` handle)
  against the baseline's own upper bound (`2` days), since the lower bound
  is fixed at `0` by design and is not what the magnitude sweeps. Rejected
  (2b) (a silent/stated exemption) because the upper bound genuinely is a
  ±30%-swept `[MODEL]` magnitude and a real check was available at no extra
  cost.
- `test_probability_cells_within_clamp` now also checks every
  definition-nested `sweep_required` node whose cells are scalar (a
  probability) against `probability_clamp`. `transient_block_clearance`'s
  list-valued day-bound cells are explicitly excluded here, stated in the
  test body: a day count of `2.6` failing a `[0, 1]` clamp would be a false
  positive, not a real defect — it is checked instead, correctly, by the
  ±30% test above.
- Added `test_thirty_percent_check_catches_a_bad_definition_nested_cell`
  (regression, same shape as `test_sweep_required_with_zero_cells_is_
  detected`): corrupts `ambiguous_cause_split`'s `high` cell to `0.99` on a
  synthetic registry and asserts the new check catches it, proving the
  extension actually works rather than merely happening to pass on today's
  already-correct values.

### Verification

- `python -m pytest -q`: 188 passed (all locked tests green, including both
  corrections to `test_model_params_swept.py` and `test_failure_mix_simplex.py`).
- Sweep cell count: 22 → 26, unchanged by the second correction (it added
  enforcement, not cells; 24 → 28 with the topup toggle on — that toggle's
  own on/off semantics are unchanged).
- `git diff -- EVAL.md`: exactly one added paragraph (the `§1.2` footnote);
  no other line changed.

Does not move or delete the `eval-spec-v1` tag.
