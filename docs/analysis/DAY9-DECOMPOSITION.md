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
