# DAY 9 — RECOVERY-DEFICIT DECOMPOSITION

**Status:** Day 9, Stage 2 only. A diagnostic decomposition of the
already-sealed, already-scored holdout invoice-recovery deficit. Does not
modify, and has no power to modify, `RESULTS.md`'s already-recorded
criterion 2 FAIL verdict. Pre-declared in `CHANGELOG.md` ("Day 9 Stage 2 —
paired recovery-deficit decomposition, pre-declaration", committed
`8ff9a15`) before `scripts/day9_decompose.py` was executed.

---

## 1. Scope and contamination boundary

This document answers: **at the episode level, where does A3-D's holdout
invoice-recovery deficit against its `EVAL.md §7` comparator set (A1,
A2-strengthened) come from?**

What this document is:
- A read-only join of already-sealed, already-checksummed per-episode
  artifacts (`results/holdout/4d45db461943/{a3_d,a1,a2_strengthened}/episode_results.jsonl`,
  `results/holdout/4d45db461943/a3_d/ledger.jsonl`), paired on
  `episode_index` — the same CRN world-level key the frozen paired
  bootstrap already uses.
- Arithmetic and simple field lookups on top of that join. No new
  statistical test, confidence interval, or p-value is computed.

What this document is **not**:
- It does not rerun, replay, or access `holdout_indices(authorized=True)`.
  It does not modify any file under `results/holdout/` — verified below
  (§14) by checksum comparison against the sealed manifest.
- It does not select or redefine buckets after seeing counts. The bucket
  taxonomy was fixed in `CHANGELOG.md` (commit `8ff9a15`) before
  `scripts/day9_decompose.py` was run.
- It does not tune A3-D, change the agent, or propose a fix. It explains
  a result that is already final.

## 2. Pre-declared decomposition

Restated verbatim from `CHANGELOG.md` (committed before execution):

- **Bucket A — Fewer contacts, lost recovery.** A3-D's `contacts_sent` <
  comparator's, comparator recovered, A3-D did not.
  - **A.D1 — STOP-attributable.** A3-D's ledger shows an explicit
    `executed_action.action_type == "STOP"` tick for that episode.
  - **A.D2 — Other fewer-contact loss.** Bucket A minus A.D1.
- **Bucket B — Fewer contacts, recovery preserved.** A3-D's contacts <
  comparator's, both recovered. Context only; contributes 0 to the rate
  difference.
- **Bucket C — Same contact count, timing difference.** Pre-declared
  **NOT IDENTIFIABLE** — neither A1 nor A2-strengthened produces a ledger
  or any per-day contact record (`docs/DAY8-AUDIT-SAMPLE-RULING.md §2`
  item 1), so no artifact establishes *when* their contacts were sent.
  Episodes that would otherwise qualify (equal contact count, differing
  outcome) are counted in Bucket E instead, tagged `same_contacts` for
  transparency.
- **Bucket D — STOP divergence.** Not a parallel top-level bucket (per
  this stage's own no-double-counting instruction) — implemented as
  sub-bucket **A.D1**.
- **Bucket E — Other / unexplained.** Residual of the "comparator
  recovered, A3-D did not" population not captured by A: equal contact
  counts (`same_contacts`) and A3-D using **more** contacts than the
  comparator yet still losing (`more_contacts`).

## 3. Data sources and fields

| File | Role | Key fields used |
|---|---|---|
| `results/holdout/4d45db461943/a3_d/episode_results.jsonl` | A3-D outcome per episode | `episode_index`, `invoice_recovered`, `contacts_sent`, `opening_condition_key`, `invoice_amount_inr` |
| `results/holdout/4d45db461943/a1/episode_results.jsonl` | A1 outcome per episode | same fields |
| `results/holdout/4d45db461943/a2_strengthened/episode_results.jsonl` | A2-strengthened outcome per episode | same fields |
| `results/holdout/4d45db461943/a3_d/ledger.jsonl` | A3-D per-tick decision trail (A3-D only — no ledger exists for A1/A2-strengthened) | `episode_id`, `tick`, `tick_type`, `executed_action.action_type`, `reason_code` |

Script: `scripts/day9_decompose.py` (committed `8ff9a15`, before execution).
Raw output: `results/day9_decomposition/decomposition_a1.json`,
`decomposition_a2_strengthened.json`, `decomposition_all.json`. Every
number in §4–§10 below is read directly from those files — reproducible
by re-running `python scripts/day9_decompose.py`.

Join integrity, asserted by the script and confirmed by its successful
run: all three arms' `episode_results.jsonl` contain exactly the same
2,000 `episode_index` values (`{9000, …, 10999}`); the script raises on
any mismatch and did not raise.

## 4. A3-D vs A1 paired outcomes

**MEASURED** (`results/day9_decomposition/decomposition_a1.json`,
`confusion_matrix`):

| | Count | % of 2,000 |
|---|---:|---:|
| Both recovered | 855 | 42.75% |
| Neither recovered | 1,042 | 52.10% |
| A1 recovered, A3-D did not | **73** | 3.65% |
| A3-D recovered, A1 did not | 30 | 1.50% |

**ARITHMETIC RE-EXPRESSION:** (73 − 30) / 2000 = **0.0215**, matching
`RESULTS.md` §7's published A3-D-vs-A1 invoice-recovery diff exactly (43
of the 2,000-episode-count difference reported in Stage 1 is the
*net* of these two opposing populations: 73 − 30 = 43, not a single
one-directional population — a materially more precise picture than the
net figure alone).

## 5. A3-D vs A2-strengthened paired outcomes

**MEASURED** (`decomposition_a2_strengthened.json`, `confusion_matrix`):

| | Count | % of 2,000 |
|---|---:|---:|
| Both recovered | 878 | 43.90% |
| Neither recovered | 1,056 | 52.80% |
| A2-strengthened recovered, A3-D did not | **59** | 2.95% |
| A3-D recovered, A2-strengthened did not | 7 | 0.35% |

**ARITHMETIC RE-EXPRESSION:** (59 − 7) / 2000 = **0.0260**, matching
`RESULTS.md` §7's published diff exactly.

## 6. Primary decomposition

**MEASURED**, from the two `comp_only` populations above (73 for A1, 59
for A2-strengthened):

| Bucket | vs. A1 (n=73) | vs. A2-strengthened (n=59) |
|---|---:|---:|
| **A — fewer contacts, lost** | **47** (64.4%) | **59** (100.0%) |
| — A.D1 STOP-attributable | 0 | 0 |
| — A.D2 other fewer-contact loss | 47 | 59 |
| **C — same contacts, timing** | NOT IDENTIFIABLE | NOT IDENTIFIABLE |
| **E — other/unexplained** | **26** (35.6%) | **0** (0.0%) |
| — E.same_contacts | 21 | 0 |
| — E.more_contacts | 5 | 0 |
| **Total (= comp_only)** | 73 | 59 |

Bucket B (context only, no rate-diff contribution): **724** episodes vs.
A1, **317** vs. A2-strengthened — A3-D used fewer contacts than the
comparator and both still recovered the invoice.

**Headline finding: against A2-strengthened, 100% of A3-D's invoice-recovery
losses are Bucket A (fewer contacts, lost) — none are unexplained.**
Against A1, 64% are Bucket A and the remaining 36% are Bucket E (mostly
same-contact-count divergences whose mechanism this data cannot establish
— see §12).

**A.D1 (STOP-attributable) is zero for both comparators** — see §9.

## 7. Decline-code stratification

**MEASURED**, `decline_code_strat` on Bucket A (`opening_condition_key`,
the actual simulator decline-code/decline-code-group field — no new
taxonomy invented):

**vs. A1 (Bucket A, n=47):**

| `opening_condition_key` | Count |
|---|---:|
| `card_expired` | 21 |
| `debit_instrument_blocked` | 17 |
| `ambiguous_decline` | 6 |
| `card_not_enabled_group` | 3 |

**vs. A2-strengthened (Bucket A, n=59):**

| `opening_condition_key` | Count |
|---|---:|
| `card_expired` | 27 |
| `debit_instrument_blocked` | 27 |
| `card_not_enabled_group` | 5 |

**Diagnostic interpretation:** against A2-strengthened, Bucket A is
**exclusively** the three "card-broken" buckets (`card_expired`,
`debit_instrument_blocked`, `card_not_enabled_group`) — precisely the
bucket `CHANGELOG.md`'s `eval-spec-v1.5` entry, item D, already flagged
before any A3-D result existed: *"A3-D's T+3 contact is conditional on the
withhold predicate (§10A.3) while A2's is unconditional... A mechanically
stronger schedule was available and was declined... because A3-D is the
control arm for A3-LLM."* This decomposition is empirical confirmation,
on holdout, of a mechanism the design record predicted in advance — not a
new hypothesis discovered by looking at holdout data. Against A1, the same
three buckets account for 41/47 (87%) of Bucket A, plus 6 `ambiguous_decline`
episodes not present in the A2-strengthened breakdown (A1's unconditional
`card_change`-content contacts, per `EVAL.md §4.3`, reach a somewhat wider
set of buckets than A2-strengthened's condition-aware schedule).

## 8. Days-since-first-failure stratification

**MEASURED**, `day_strat_last_a3d_wakeup_tick` on Bucket A — the `tick`
(day) of A3-D's **last** wakeup decision in each lost-recovery episode.
**This is an A3-D-only measurement**: neither A1 nor A2-strengthened
produces any per-day record, so this cannot be directly compared to the
comparator's own contact day(s) — it only shows when A3-D's own
engagement ended.

**vs. A1 (n=47):** day 3 — **all 47 (100%)**.

**vs. A2-strengthened (n=59):** day 3 — 41 (69.5%); day 5 — 3 (5.1%); day
14 — 15 (25.4%).

**Diagnostic interpretation:** the day-3 concentration lines up with both
comparators' own T+3 second contact (`EVAL.md §4.3` for A1;
`EVAL.md §4.1.2` for A2-strengthened) and with A3-D's Bucket-A example
records (`decomposition_a1.json`, `D2_other_fewer_contact_loss.examples`),
which consistently show `a3d_last_wakeup_reason_code: "no_engagement_restraint"`
at tick 3 — i.e., A3-D's withhold predicate declines the T+3 contact for
lack of observed engagement, in exactly the episodes where the comparator
sends its (unconditional, for A1; condition-aware, for A2-strengthened)
T+3 contact anyway and that contact recovers the invoice. The 15
day-14-divergence episodes against A2-strengthened do not fit this
pattern as cleanly and are not further explained by this data — flagged,
not forced into the T+3 narrative.

## 9. STOP divergence analysis

**MEASURED**, independently verified two ways:

1. `scripts/day9_decompose.py`'s per-episode STOP detection (`stop_flag`
   from `ledger.jsonl`) found **A.D1 = 0** episodes for both comparators.
2. Direct verification against the raw ledger (ad hoc check, this session):
   A3-D issues an explicit `STOP` action in **311 distinct episodes**
   across the full holdout run (out of 8,045 wakeup ticks: 4,863 WAIT,
   2,871 CONTACT, 311 STOP — sums exactly to `n_wakeup_ticks=8045` and
   `total_contacts=2871` in `results/holdout/4d45db461943/a3_d/metrics.json`).
   Of those 311 STOP episodes, **zero** overlap with either comparator's
   `comp_only` population (A1: 0/73; A2-strengthened: 0/59), checked
   without restricting to the fewer-contacts condition — i.e., not one of
   A3-D's 311 STOP episodes is an episode where the comparator went on to
   recover an invoice A3-D missed.

**Diagnostic interpretation:** A3-D's explicit STOP mechanism (including
the 24 `risk_flagged` escalations reported in
`results/holdout/4d45db461943/a3_d/metrics.json`) plays **no role** in the
observed invoice-recovery deficit against either comparator. The entire
deficit is Bucket A.D2 — WAIT-driven restraint (the withhold predicate
choosing not to contact) rather than an active STOP decision.

## 10. Reason-code / mechanism analysis

**MEASURED**, `reason_code_mechanism_all_comp_only` and
`tick_type_mechanism_all_comp_only` — computed over the full `comp_only`
population (73 / 59), using A3-D's ledger `reason_code` (last wakeup
tick) and `tick_type` fields directly, not inferred from free-text
`rationale`:

**vs. A1 (n=73 episodes, all A3-D wakeup ticks within them):**
- `reason_code` at last wakeup: `no_engagement_restraint` 65, `post_halt_rescue` 8.
- `tick_type` totals across all ticks in these episodes: `terminal_suppressed` 1,371, `no_wakeup` 415, `wakeup` 352, `budget_exhausted` 125.

**vs. A2-strengthened (n=59 episodes):**
- `reason_code` at last wakeup: `no_engagement_restraint` 56, `post_halt_rescue` 3.
- `tick_type` totals: `terminal_suppressed` 1,182, `no_wakeup` 362, `wakeup` 285. (`budget_exhausted` did not occur in this subset.)

**Diagnostic interpretation:** `no_engagement_restraint` dominates both
populations (89% of A1's comp_only episodes, 95% of A2-strengthened's),
consistent with §8/§9: the mechanism is A3-D's withhold-on-no-engagement
rule declining a contact the comparator sends anyway, not budget
exhaustion (`budget_exhausted` is a minority even where present) and not
an active STOP.

## 11. Reconciliation to observed recovery deficit

**ARITHMETIC RE-EXPRESSION**, signed contributions (positive =
comparator-only recoveries, i.e. A3-D loses; negative = A3-D-only
recoveries, i.e. A3-D gains), all as a fraction of 2,000:

**vs. A1:**

| Component | Count | Signed contribution |
|---|---:|---:|
| Bucket A | 47 | +0.0235 |
| Bucket E (same_contacts) | 21 | +0.0105 |
| Bucket E (more_contacts) | 5 | +0.0025 |
| Bucket B | 724 | 0.0000 |
| Both / neither recovered | 1,897 | 0.0000 |
| A3-D-only recovered | 30 | −0.0150 |
| **Sum** | | **+0.0215** |

Published diff (`RESULTS.md` §7): **0.0215**. **Reconciles exactly.**

**vs. A2-strengthened:**

| Component | Count | Signed contribution |
|---|---:|---:|
| Bucket A | 59 | +0.0295 |
| Bucket E | 0 | 0.0000 |
| Bucket B | 317 | 0.0000 |
| Both / neither recovered | 1,934 | 0.0000 |
| A3-D-only recovered | 7 | −0.0035 |
| **Sum** | | **+0.0260** |

Published diff (`RESULTS.md` §7): **0.0260**. **Reconciles exactly.**

Both reconciliations are also asserted programmatically:
`reconciliation.matches_pairwise_rate_diff = true` in both output JSON
files.

## 12. Residual / unexplained component

Bucket E is the only unexplained component:

- **vs. A1: 26 episodes (35.6% of the 73-episode deficit population,
  1.30 points of the 2.15-point rate gap).** 21 have equal contact
  counts (Bucket C's would-be population, undecomposable — no per-day
  data exists for A1); 5 have A3-D using **more** contacts than A1 yet
  still losing the invoice, which is not explained by any contact-count
  or engagement-restraint story this data can test. Bucket E's
  `more_contacts` examples are concentrated in `ambiguous_decline`
  (`decomposition_a1.json`: 5/5).
- **vs. A2-strengthened: 0 episodes.** The entire 59-episode deficit
  population is explained by Bucket A (fewer contacts, no STOP involved).

No episode was forced into A, B, C, or D to avoid reporting Bucket E.

## 13. Limitations

1. **Bucket C is NOT IDENTIFIABLE for both comparators**, as pre-declared
   before computation — A1 and A2-strengthened produce no ledger and no
   per-day contact record, only a per-episode total `contacts_sent`
   (`docs/DAY8-AUDIT-SAMPLE-RULING.md §2` item 1). The 21 same-contact-count
   divergent episodes against A1 may or may not be timing-driven; this
   data cannot say.
2. **The "days since first failure" stratification (§8) is one-sided.**
   It measures only A3-D's last wakeup tick, not the comparator's actual
   contact day(s), because no comparator ledger exists. The T+3 alignment
   in §8/§9 is a plausible, source-consistent mechanism (matching the
   documented A1/A2-strengthened T+3 schedules and A3-D's own withhold
   predicate), not a directly observed A3-D-vs-comparator timing
   comparison.
3. **Bucket E's 5 "more contacts, still lost" episodes (vs. A1) are
   genuinely unexplained** by any field this analysis used. A more granular
   investigation (e.g., which specific remedy A3-D sent vs. which A1 sent)
   would require inspecting A3-D's `parsed_action.remedy` per tick, which
   this pre-declared decomposition did not include as a stratification
   axis — noted as a gap, not filled retroactively.
4. **This is a per-episode outcome join, not a new confidence interval.**
   The confusion-matrix cell counts (§4, §5) are exact, sealed-artifact
   counts, not estimates — but no new CI is placed on any bucket
   proportion. The only CI-bearing claim used anywhere in this document is
   the already-published, already-pre-registered holdout CI on the
   aggregate rate difference itself (`RESULTS.md` §7).
5. **A4 (oracle) and A0 are not part of this decomposition.** Per this
   stage's own instruction, only the two official invoice-recovery
   comparators (A1, A2-strengthened) are used — A4 is excluded from
   `EVAL.md §7` criterion 2 by design, and including it here was not
   authorized.
6. **Subscription rescue is not decomposed in this document.** Stage 2's
   authorization scoped the primary comparison to invoice recovery
   specifically; the subscription-rescue comparator set (A2-strengthened
   alone) and its deficit are not analyzed here.

## 14. Interpretation

**Directly measured from sealed artifacts:** the exact confusion matrices
(§4, §5), the exact bucket counts (§6), the exact decline-code and
last-wakeup-tick distributions (§7, §8), the exact zero STOP-overlap
finding (§9), and the exact reason-code/tick-type distributions (§10).

**Arithmetic decompositions:** the percentage breakdowns, the signed
reconciliation (§11), and the "% of comp_only" framing throughout.

**Diagnostic interpretation (labeled explicitly wherever used, §7–§9):**
that the T+3 withhold predicate — A3-D declining a second contact for
`no_engagement_restraint` in episodes where the comparator's own T+3
contact goes on to recover the invoice — is the dominant, identifiable
mechanism behind the deficit, responsible for 100% of the A2-strengthened
deficit and 64% of the A1 deficit (with the T+3 timing evidence itself
being A3-D-side only, per Limitation 2). This is consistent with, and
adds episode-level evidence under, the mechanism `CHANGELOG.md`'s
`eval-spec-v1.5` entry (item D) already flagged as a known, declined
design tradeoff before any A3-D holdout result existed: A3-D was
deliberately not given a stronger, unconditional schedule "because A3-D
is the control arm for A3-LLM... changing both the schedule and the
decision logic would confound adaptivity with scheduling."

**No STOP-based explanation holds for any part of the deficit** (§9) —
the mechanism is uniformly under-contacting via WAIT/withhold, not
active disengagement.

**35.6% of the A1 deficit (Bucket E) remains genuinely unexplained** by
this analysis and is reported as such, not folded into the T+3 narrative
that fits the other 64.4%.

**Holdout integrity, verified after producing this document:**
`sha256sum -c results/holdout/4d45db461943/SHA256SUMS`, run from within
that directory, reports **all 21 files `OK`** — every sealed holdout
artifact (including `a3_d/ledger.jsonl`) is byte-identical to its sealed
checksum. This diagnostic analysis read those files but did not modify,
regenerate, or touch `results/holdout/` in any way.

---

## Stage 3 — Mechanism Attribution

**Status:** Day 9, Stage 3 only. Attributes A3-D's holdout behavior — and
specifically the Stage 2 deficit population — to `EVAL.md §3.4`'s three
pre-registered advantage sources. Pre-declared in `CHANGELOG.md` ("Day 9
Stage 3 — mechanism attribution, pre-declaration", committed `cc86ba6`)
before `scripts/day9_mechanism_attribution.py` was run. Diagnostic only;
does not change any Stage 0–2 finding or `RESULTS.md`'s criterion 2
verdict.

### 1. Scope and contamination boundary

This section answers: **which of `EVAL.md §3.4`'s three declared
mechanisms are empirically visible in A3-D's holdout ledger, and how do
they relate to the Stage 2 deficit?**

Method: every A3-D wakeup ledger record carries `rationale` — the exact
decision-table rule id (`R-01`…`R-16`) that fired
(`docs/A3-DESIGN.md §10A.4`). Each rule's mechanism association is read
verbatim from `docs/A3-DESIGN.md §10A.5`, a document frozen under tag
`eval-spec-v1.5` before any A3-D episode was ever executed. This is a
structured-field lookup, not an inference from free-text `rationale`
narrative (there is none — A3-D never calls an LLM, so `raw_output` is
always `null`; `rationale` here is the rule id string itself, a
closed-vocabulary structured field).

Script: `scripts/day9_mechanism_attribution.py` (committed `cc86ba6`,
before execution). Output:
`results/day9_decomposition/mechanism_attribution.json`. Read-only
against `results/holdout/`; re-verified `OK` against `SHA256SUMS` after
running (§ Stage 2 holdout-integrity note above covers the same check,
re-run after this script also).

**Integrity cross-check, required by the pre-declaration and satisfied:**
re-deriving Stage 2's Bucket A membership from the identical rule (fewer
contacts, comparator recovered, A3-D did not) reproduces **47** (vs. A1)
and **59** (vs. A2-strengthened) exactly —
`mechanism_attribution.json`, `stage2_bucket_a_mechanism_crosscheck.*.bucket_a_count_rederived`
— matching `docs/analysis/DAY9-DECOMPOSITION.md` §6 above byte-for-byte.

### 2. Retry-window timing

**MEASURED**, `mechanism_attribution.json`:

- **Contact timing relative to the retry/halt boundary (day 3,
  `configs/episode.yaml:61`, `halt_boundary_day: 3`):** of 2,871 total
  contacts, **2,158 (75.2%)** occur at or before day 3 (within the
  invoice-recovery-relevant window); **713 (24.8%)** occur after day 3.
  **All 713** post-boundary contacts are rule `R-11` (post-halt rescue,
  day 5 only) — `rule_firing_distribution_all_wakeups.R-11 = 713` matches
  `contacts_after_retry_boundary_day3 = 713` exactly. No other rule ever
  sends a contact after day 3.
- **Withhold at T+3:** **972** wakeup ticks at `tick == 3` produce a
  WAIT/STOP with `reason_code = no_engagement_restraint`, split by rule:
  **702 via `R-16`** (the default fallthrough) and **270 via `R-07`**
  (`insufficient_funds`, day ≥ 3 — `[FORCED mechanically]` per §10A.5,
  tagged retry-window timing, not adaptive contact).
- **Withhold inside vs. outside the declared retry window:** **3,605**
  withhold ticks (`reason_code=no_engagement_restraint`, WAIT/STOP) occur
  at `tick` 1–3 (inside the auto-retry window); **1,122** occur at
  `tick > 3` (after the window closes); **17** occur at `tick == 0`.
- **The 17 `tick == 0` withholds are entirely rule `R-03`**
  (`transaction_limit_exceeded`, unconditional, day-independent, `[FORCED
  mechanically]`) — verified directly against the ledger. This does
  **not** contradict `docs/A3-DESIGN.md §10A.3`'s claim that "the first
  agent contact is never withheld [by the AC predicate]" — `R-03` is a
  different, unconditional rule untouched by `withhold_applies`; the
  AC-gated rules (R-09, R-10, R-13, R-15) never fire at `tick == 0` in
  this data, consistent with the design claim.

**For the Stage 2 loss episodes:** §8 above already established the
timing pattern (A1: 47/47 at tick 3; A2-strengthened: 41 at tick 3, 3 at
tick 5, 15 at tick 14). Mechanism-2/3 sections below connect this to the
specific rules involved.

**Comparator limitation, restated:** A1 and A2-strengthened have no
per-day contact record (`docs/DAY8-AUDIT-SAMPLE-RULING.md §2` item 1), so
none of the above can be compared against the *comparator's* actual
timing — only against the documented, fixed T+0/T+3 (A1) or
condition-aware T+0/T+3/T+5 (A2-strengthened) schedules named in
`EVAL.md §4.3`/`§4.1.2`. This is a design-document reference, not a
per-episode artifact comparison. **No causal claim is made from the
tick=3 correlation alone** — §4 below traces the specific rule mechanics
that make the correlation causally interpretable in this case.

### 3. Remedy matching

**MEASURED**, `mechanism_attribution.json`:

- **Remedy-match rate: 2,871 / 2,871 (100%).** Every `CONTACT` action's
  `reason_code` is admissible for that episode's `opening_condition_key`
  (decline code) per `src/rrx/agent/reason_codes.ADMISSIBLE_DECLINE_CODES`
  — `remedy_mismatch_count = 0`. This is an empirical confirmation, on
  real holdout ledger data, of gate-compliance-by-construction
  (`docs/A3-DESIGN.md §10A.6`; also unit-tested at the policy level by
  `tests/test_a3d_policy.py`'s 40/40 totality tests) — not a new proof,
  a cross-check that the deployed holdout run matches the proven
  property.
- **Remedy selection across decline buckets (rule-level):** `R-08`
  (topup, day 0, `insufficient_funds`) 651 firings; `R-12` (card_change,
  day 0, `CARD_BROKEN`) 684; `R-14` (card_change, day 0,
  `ambiguous_decline`) 453; `R-09`/`R-13`/`R-15` (day-2/3 follow-up
  remedies, all withhold-gated) 132/126/112; `R-11` (post-halt
  card_change) 713.
- **Among the recovery-loss episodes: remedy mismatch is not a measurable
  contributor.** Since remedy-match is 100% across all 2,871 holdout
  contacts (including every contact inside both Stage 2 deficit
  populations), no lost recovery in Bucket A can be attributed to A3-D
  proposing the wrong remedy — the contacts A3-D *did* send in those
  episodes (e.g. the day-0 `R-12`/`R-08` contact) always match the
  declared correct remedy for that decline bucket. The deficit is driven
  entirely by contacts A3-D **did not send**, not by a wrong remedy on a
  contact it did send.
- **Is remedy matching separable from contact-withholding? NOT
  SEPARABLE for four of the seven `CONTACT` rules.** `R-09`, `R-13`, and
  `R-15` combine a remedy decision and the `AC` withhold gate in a single
  ordered condition (`"day == N and not withhold_applies"`); `R-08`
  combines remedy matching with retry-window timing (earliest in-window
  day). Only `R-12`, `R-14` (day-0, unconditional) and `R-11`
  (post-halt, explicitly withhold-exempt) select a remedy independent of
  any other mechanism. This fusion is a property of the frozen decision
  table (`docs/A3-DESIGN.md §10A.4`), not an artifact of this analysis —
  see §5 below.

**Comparator limitation:** A1's and A2-strengthened's remedy choices per
episode are not recorded in any artifact beyond the aggregate
`card_change_for_insufficient_funds` gate-check field
(`results/holdout/4d45db461943/a1/metrics.json`); their remedy logic is
fully described in `EVAL.md §4.3`/`§4.1.2` as fixed, condition-keyed
rules, not per-episode adaptive decisions, so no per-episode
remedy-match rate is computable or meaningful for them the way it is for
A3-D.

### 4. Within-episode adaptive contact

**MEASURED**, `mechanism_attribution.json`:

- **The predicate's only implementation is `withhold_applies` (`observations
  >= 2 and not any_engaged`), `docs/A3-DESIGN.md §10A.3`.** It gates
  exactly four rules: `R-09`, `R-10`, `R-13`, `R-15` — **1,341** total
  wakeup ticks (`AC` tag total), 16.7% of all 8,045 wakeup ticks.
- **How restraint compounds with prior contacts:** `R-16`'s tick-3
  firings (702 total) split by decline code — **417 (59.4%) are
  `CARD_BROKEN`** (`card_expired` 199, `debit_instrument_blocked` 159,
  `card_not_enabled_group` 59), for which `R-13` (the AC-gated day-3
  remedy rule) would have matched and sent a contact **had
  `withhold_applies` been false** — this 417 is the directly
  AC-attributable component. The remaining **285 (40.6%) are
  `ambiguous_decline`**, which has no day-3 rule at all (`R-14`/`R-15`
  cover only day 0/2) — these fall to `R-16` regardless of engagement
  history and are **not** AC-attributable, disambiguated here rather
  than left folded into a single "no_engagement_restraint" total.
- **`no_engagement_restraint` is a heavily overloaded label — not a
  reliable proxy for the AC mechanism on its own.** It is the static
  `reason_code` for five mechanically-forced STOP rules (`R-01`, `R-03`,
  `R-05`, `R-06`, `R-07` — none use `withhold_applies`) in addition to
  the genuinely adaptive `R-09`/`R-10`/`R-13`/`R-15` and the default
  `R-16`. Counting every `no_engagement_restraint` occurrence as "the
  agent adapted to non-engagement" would overstate the AC mechanism's
  footprint; this document does not do that (§2 above already separated
  the 270 `R-07` instances at tick 3 from the 702 `R-16` instances on
  exactly this basis).
- **`R-16`'s overall firing rate (3,740 / 8,045 = 46.5% of all wakeup
  ticks) is high enough that `docs/A3-DESIGN.md §10A.5`'s own stated
  diagnostic criterion applies** ("a rate materially above expectation
  indicates the table has a hole... to be reported rather than silently
  patched"). By tick: 1,137 (day 1), 779 (day 2), 702 (day 3), 73 (day
  4), 59 (day 6), 495 (day 7), 495 (day 14). Days 4 and 6 are not in the
  fixed wake-up set `{0,1,2,3,5,7,14}` (`docs/A3-DESIGN.md §5`), so these
  are engagement-triggered extra wake-ups for which the table has no
  bespoke rule at all — an expected use of the default, not evidence of
  a hole. Days 7 and 14 (990 combined) are late fixed wake-ups after
  every bucket's dedicated rules (through `R-15`) or rescue attempt
  (`R-11`, day 5 only) have already fired or been forgone — also an
  expected default. Days 1–3 (2,618 combined, 70% of all `R-16` firings)
  are the ambiguous case: for several decline-code/day combinations
  (e.g. `ambiguous_decline` at day 1 or day 3, `CARD_BROKEN` at day 1 or
  2) no dedicated rule was ever written for that specific day, so `R-16`
  fires regardless of engagement. **This document does not resolve
  whether that specific gap is a missed design opportunity or an
  intentional economy of rules** — that judgment is out of scope for a
  diagnostic stage that must not propose or evaluate a design change
  (contamination rule 5/6). It is reported as a measured fact and an
  open question, not resolved either way.
- **Is the T+3 restraint behavior dependent on episode history? Yes,
  for the `CARD_BROKEN` bucket specifically, and this is directly
  traceable, not inferred:** `withhold_applies` requires `observations >=
  2` — by day 3, an episode with no engagement has accumulated the day-0
  auto-email plus the day-0 agent contact (`R-12`), satisfying the
  `>= 2` threshold; if neither engaged, `R-13`'s day-3 contact is
  withheld and control falls to `R-16`. This is exactly the mechanism
  `docs/A3-DESIGN.md §10A.5` describes for `R-13`, confirmed empirically
  in ledger records rather than assumed from the design text alone (see
  the three-episode trace under §5 below).
- **Connecting Stage 2 loss episodes directly:** `stage2_bucket_a_mechanism_crosscheck`
  (re-derived, matching Stage 2 exactly):
  - vs. A1 (n=47): **47/47** last-wakeup rule is `R-16`.
  - vs. A2-strengthened (n=59): **56/59** last-wakeup rule is `R-16`;
    **3/59** last-wakeup rule is `R-11`.

  The 3 `R-11`-last-wakeup episodes (9159, 9921, 10098 —
  `results/holdout/4d45db461943/a3_d/ledger.jsonl`, verified by direct
  trace) all show the identical pattern: `R-12` (day 0 contact) →
  `R-16`/WAIT (days 1, 2, **and 3** — the AC-attributable withhold) →
  `R-11`/CONTACT (day 5, post-halt rescue). Their day-3 divergence from
  A2-strengthened is the same AC mechanism as the other 56; the later
  `R-11` firing is a subsequent, invoice-recovery-irrelevant rescue
  attempt (post-halt structurally cannot affect invoice recovery,
  `docs/A3-DESIGN.md §10A.5` R-11 basis / `RESULTS.md` §9), not a
  different cause. **All 59 of the A2-strengthened deficit episodes are
  therefore traceable to the same single mechanism: the day-3
  `withhold_applies` gate on rule `R-13` for the `CARD_BROKEN` bucket.**
  For A1, all 47 Bucket-A episodes' last wakeup is `R-16` at tick 3
  (§8 above); decline-code composition (§7 above: 41/47 `CARD_BROKEN`,
  6/47 `ambiguous_decline`) means **41 of the 47 are AC-attributable by
  the same `R-13` mechanism, and 6 are not** (`ambiguous_decline` has no
  day-3 rule, so those 6 episodes' `R-16` firing at tick 3 is structural,
  not AC-caused — consistent with §7's finding that `ambiguous_decline`
  also dominates Bucket E's `more_contacts` subgroup).

### 5. §3.4 attribution summary

| Mechanism | Empirically visible? | Quantifiable contribution | Relationship to Stage 2 deficit | Separable? |
|---|---|---|---|---|
| **Retry-window timing** | Yes — 2,193 wakeup ticks (`R-03,04,05(0),06(0),07,08,09,10`) reason explicitly about the retry/halt boundary; 100% of post-day-3 contacts are the single `R-11` post-halt rule. | Directly countable (§2). | Present in the deficit population only as background (e.g. `R-07`'s 270 tick-3 STOPs are RWT, not AC, and do not appear in either Stage 2 Bucket A population — `insufficient_funds` is absent from both Bucket A decline-code breakdowns, §7). **No measurable direct contribution to the invoice-recovery deficit** — the deficit populations (§7) contain zero `insufficient_funds`/`bank_technical_error`/`transaction_limit_exceeded` episodes, the buckets RWT rules govern. | Separable from AC in most rules (R-03,04,05,06,07); fused with RM+AC in R-08/R-09. |
| **Remedy matching** | Yes — 100% match rate, 2,871/2,871 contacts (§3). | Directly countable; contributes **zero** identifiable loss (no mismatch exists to attribute). | **Not a contributor to the deficit.** Every contact A3-D sent in a Bucket A episode was correctly remedy-matched; the loss is entirely about contacts not sent. | **NOT SEPARABLE** from AC in `R-09`, `R-13`, `R-15` — the same ordered condition gates both which remedy to send and whether to send it at all. |
| **Within-episode adaptive contact** | Yes — 1,341 AC-gated wakeup ticks; the `withhold_applies` predicate is directly traceable via `rationale`/`reason_code` (§4). | **Quantified for the deficit population specifically:** 59/59 (100%) of the A2-strengthened deficit and 41/47 (87.2%) of the A1 deficit are directly attributable to `R-13`'s withhold gate at day 3. | **This is the dominant identified mechanism behind the recovery deficit.** Restated with the appropriate sign, per this stage's instruction: `EVAL.md §3.4`'s third pre-registered advantage source is empirically the primary driver of A3-D's holdout *underperformance* on invoice recovery, not of an uplift. | Fused with RM in the same four rules; not separable from remedy matching in those cases, but cleanly separable from retry-window timing (disjoint rule sets except R-09/R-10). |

**Overall reading, stated with the sign this stage requires:** the
declared advantage-source structure that is most visible in A3-D's
actual holdout behavior — within-episode adaptive contact via
`withhold_applies` — is not associated with an uplift here. It is
associated with the deficit. This was a foreseeable, declared tradeoff,
not a newly discovered defect: `docs/A3-DESIGN.md §10A.5` (R-12/R-13
basis) states plainly, before any holdout run, that "a mechanically
earlier schedule... would likely improve A3-D's invoice recovery... it
is declined here on identifiability grounds, not oversight," made "because
A3-D is the control arm for A3-LLM." Stage 3 supplies the holdout-level
quantification of exactly how much that declared, deliberate tradeoff
cost: the majority of the measured invoice-recovery deficit against both
comparators.

**Retry-window timing and remedy matching are not associated with the
deficit** in any measurable way this data can show — the deficit
populations contain zero episodes from the decline buckets RWT rules
govern, and zero remedy mismatches exist anywhere in the holdout ledger.

### 6. EVAL §8 item 8 verification

**Verified against implementation and actual sealed holdout ledger
evidence, not by re-quoting `docs/A3-DESIGN.md §20`'s existing claim.**

1. **Located the logic.** `src/rrx/sim/engine.py` (lines ~432–447,
   `run_episode`) and `src/rrx/harness/runner.py` (lines 185–196,
   `run_episode_a3`) both contain an explicit early-return for
   `condition["kind"] == "subscription_state"` — the
   `subscription_cancelled_by_customer` opening condition — that returns
   `_finalize(cohort, state)` **before the day loop / tick loop begins**,
   in both the non-agent engine and the A3-runner used by A3-D/A3-LLM.
   Read directly from source this session, not from documentation.
2. **Inspected actual A3-D holdout ledger/episode behavior.** Of A3-D's
   2,000 holdout episodes, **111 (5.55%)** have
   `opening_condition_key == "subscription_cancelled_by_customer"`
   (`results/holdout/4d45db461943/a3_d/episode_results.jsonl`). For
   **all 111**: `contacts_sent == 0`, and a direct scan of
   `results/holdout/4d45db461943/a3_d/ledger.jsonl` finds **zero** ledger
   records of any kind for any of the 111 episode ids — no `wakeup`, no
   `no_wakeup`, no `budget_exhausted`, no `terminal_suppressed` tick, and
   therefore no policy invocation and no `reason_code` of any kind.
3. **A3-D's contact restraint is never triggered by this bucket, because
   A3-D's policy function is never invoked for it at all** — not
   "invoked and it chose WAIT," but structurally never called. This is
   confirmed at both the code level (item 1) and the sealed-data level
   (item 2), independently.
4. **Contamination check: none of the 111 episodes appear in either Stage
   2 deficit population** or, by construction, in any WAIT/`no_engagement_restraint`
   count anywhere in §2–§4 above, because zero ledger records exist for
   them — they cannot appear in any ledger-derived statistic. Cross-arm
   check: A0, A1, A2-strengthened, and A4 also show `contacts_sent == 0`
   for all 111 of the same episode indices (`episode_index` is the CRN
   world-level pairing key, so the same 111 episodes are
   `subscription_cancelled_by_customer` under every arm) — the
   zero-contact outcome is identical across every arm, confirming it is
   environmental, not policy-driven, exactly as `docs/A3-DESIGN.md §20`
   claims. All 111 also show `invoice_recovered == False` and
   `subscription_rescued == False` for every arm (recovery is
   structurally impossible when no auto-charge was ever attempted).

**Conclusion: the limitation is resolved, definitively, by direct
verification against both source code and sealed holdout artifacts (not
merely restated from existing documentation).** This bucket contributes
**zero contamination** to any A3-D restraint statistic reported in this
document or in `RESULTS.md` — it cannot, because it produces no ledger
record, no wakeup tick, and no policy decision on any arm. The bucket's
influence on aggregate rate comparisons (§4 Stage 1, `RESULTS.md`) is
identical across all five arms (0 contacts, 0 recovery, 0 rescue, for
all 111 episodes, all arms) and therefore cancels out of every A3-D-vs-
comparator *difference* by construction, not merely by argument.

### 7. Residual / non-separable mechanisms

- **NOT SEPARABLE:** remedy matching and within-episode adaptive contact,
  wherever both tags apply to the same rule (`R-09`, `R-13`, `R-15` —
  132+126+112 = 370 wakeup ticks, 4.6% of all wakeups). The frozen
  decision table gates the remedy decision and the withhold decision in
  one ordered condition; no ledger field disentangles "the remedy would
  have been X" from "the contact would have been withheld" as
  independent counterfactuals for these rules.
- **NOT SEPARABLE:** retry-window timing and remedy matching in `R-08`
  (651 ticks) — the topup remedy and the earliest-in-window-day choice
  are the same decision.
- **NOT IDENTIFIABLE:** whether A2-strengthened's or A1's *own* per-episode
  contact timing would have shown a different divergence pattern than
  the one inferred from A3-D's side alone — no per-day comparator record
  exists (§2, §3 comparator-limitation notes; `docs/DAY8-AUDIT-SAMPLE-RULING.md §2`).
- **NOT IDENTIFIABLE:** whether the 12.8% (6/47 for A1; note A2-strengthened
  has none) of the deficit population not attributable to the `R-13`
  day-3 AC mechanism (i.e. the `ambiguous_decline` episodes, and Stage
  2's Bucket E entirely) reflects a different mechanism this
  rule-id-based analysis cannot see, or genuine noise. `ambiguous_decline`
  has no day-3 rule of any kind, so nothing in the decision table offers
  a mechanism-level explanation for those episodes' specific losses.

### 8. Interpretation

**Directly measured from sealed artifacts:** every rule-firing count,
every mechanism-tag total, the 100% remedy-match rate, the 0/311 STOP
overlap (Stage 2 §9, re-confirmed structurally consistent here since
STOP-tagged rules R-01/R-02/R-03/R-05/R-06/R-07 are all RWT or untagged,
never AC), the cancelled-at-open verification (§6), and the exact
rule-at-last-wakeup distribution for both Stage 2 deficit populations.

**Arithmetic decompositions:** the RM/RWT/AC mechanism totals (sums over
rule-firing counts), the R-16-at-tick-3 CARD_BROKEN/ambiguous_decline
split, and the 41/47 and 59/59 AC-attributable fractions of the two
deficit populations.

**Diagnostic interpretation:** that within-episode adaptive contact
(specifically `R-13`'s day-3 withhold gate) is the dominant, empirically
traceable mechanism behind the observed deficit; that this was a
declared, foreseeable tradeoff rather than an undiscovered defect
(`docs/A3-DESIGN.md §10A.5`); and that retry-window timing and remedy
matching are both empirically clean (100% match rate; zero presence in
either deficit population's decline-code composition) and therefore not
implicated in the underperformance. **Do not read "within-episode
adaptive contact caused the deficit" as "the mechanism is broken"** — it
functioned exactly as designed (§10A.3's predicate fired precisely when
its own stated conditions held); the finding is that the deliberate
design choice to keep this predicate active and use A2-strengthened's
schedule unchanged (rather than adopt a mechanically stronger,
front-loaded schedule that `docs/A3-DESIGN.md §10A.5` explicitly
identified and declined, for identifiability reasons, before any result
existed) is what cost A3-D the majority of its measured invoice-recovery
deficit.
