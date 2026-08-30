# DAY 9 — A3-D FRONTIER ANALYSIS

**Status:** Day 9, Stage 4 only. Part A is a read-only re-adjudication of
Stage 3's already-published R-16 finding. Part B is a dev-only descriptive
experiment. Neither modifies, nor has the power to modify,
`RESULTS.md`'s already-recorded criterion 2 verdict, `EVAL.md`, the cost
model, or any holdout artifact. Pre-declared in `CHANGELOG.md` ("Day 9
Stage 4 — R-16 adjudication + dev-only frontier, pre-declaration",
committed `2e81eec`) before `scripts/day9_frontier.py` was run.

---

## 1. Scope and contamination boundary

**Part A** classifies every R-16 (default fallthrough) firing observed in
Stage 3 into one of three pre-identified categories and adjudicates each
against the frozen design text (`docs/A3-DESIGN.md §10A.4`/`§10A.5`,
`EVAL.md §3.4`/`§5`). No new script, no new data — a re-inspection of
Stage 3's `results/day9_decomposition/mechanism_attribution.json` plus a
small number of new, read-only decline-code/tick queries against the
already-sealed `results/holdout/4d45db461943/a3_d/ledger.jsonl` (same file
Stage 2/3 already read).

**Part B** runs a dev-only sweep of A3-D's restraint threshold to test
whether the frozen setting is well-positioned on its own recovery/contact
tradeoff curve. **Holdout is never accessed** — `scripts/day9_frontier.py`
imports only `rrx.harness.splits.dev_indices`, never
`holdout_indices`(confirmed: `grep -n "holdout_indices" scripts/day9_frontier.py`
returns nothing). `src/rrx/agent/policy.py` is not imported for its
policy logic and not modified — the swept parameter is implemented as a
new, parameterized function in `scripts/day9_frontier.py`, mechanically
identical to `a3d_policy` except one literal, validated by an exact
parity check before being trusted (§4). No production policy is selected;
no `A3.1` is created.

**Holdout integrity, verified both before and after Part B's execution:**
`sha256sum -c results/holdout/4d45db461943/SHA256SUMS` reports all 21
files `OK` at both checkpoints — Part B did not read, write, or otherwise
touch anything under `results/holdout/`.

---

## 2. R-16 adjudication

R-16 fires on 3,740 / 8,045 (46.5%) of A3-D's holdout wakeup ticks
(`results/day9_decomposition/mechanism_attribution.json`, Stage 3).
**Re-verified this session:** R-16 fires **only** for `card_expired`
(1,162), `debit_instrument_blocked` (900), `card_not_enabled_group`
(347), and `ambiguous_decline` (1,331) — **zero** occurrences for
`insufficient_funds`, `bank_technical_error`, `transaction_limit_exceeded`,
or `payment_risk_check_failed`, which are fully covered by dedicated
rules (`R-02`/`R-03`/`R-04`/`R-05`/`R-06`/`R-07`/`R-08`/`R-09`/`R-10`) on
every day. This is a direct table-coverage fact, confirmed empirically
against the sealed ledger, not assumed from reading the table alone.

| Category | Ticks | Count | Adjudication | Basis |
|---|---|---:|---|---|
| Engagement-triggered off-schedule days | 4, 6 | **132** | **EXPECTED FALLTHROUGH** | No rule in `docs/A3-DESIGN.md §10A.4` is keyed to a non-fixed day; the wake-up mechanism itself is designed to add "more decision points, not more actions" (`CHANGELOG.md`, `eval-spec-v1.4` item F). WAIT is the only sensible default for a day the table was never meant to have a bespoke rule for. |
| Late fixed days after rules exhausted | 7, 14 | **990** | **EXPECTED FALLTHROUGH** | Directly, explicitly stated in `docs/A3-DESIGN.md §10A.5` (R-11 basis): *"gated to `day == 5` exactly; halted wake-ups on other days (7, 14, or engagement-driven) fall through to R-16, so this bucket never spends more than one post-halt contact."* This is not an inference — it is a verbatim citation naming days 7 and 14 as the intended fallthrough. |
| Decline-code/day combos with no dedicated rule at all | `CARD_BROKEN` day 1 (684), `CARD_BROKEN` day 2 (543), `ambiguous_decline` day 1 (453) | **1,680** | **EXPECTED FALLTHROUGH** | `docs/A3-DESIGN.md §10A.5` (R-12/R-13 basis) states A3-D "deliberately adopts A2-strengthened's contact schedule (T+0/T+3/T+5-if-halted) unchanged" — A2-strengthened's own schedule (`EVAL.md §4.1.2`) is identically silent on days 1/2 for this bucket, so the gap is the explicitly adopted, shared schedule, not an omission specific to A3-D. `ambiguous_decline` day 1 follows the same "day 0 / day 2 / day 5" three-point pattern R-14/R-15/R-11's basis describes, by analogy rather than a sentence naming day 1 specifically — weaker citation than `CARD_BROKEN`'s, but consistent with the same design economy applied elsewhere in the table. |
| `ambiguous_decline` day 3 — no rule at all (unlike `CARD_BROKEN`, which has `R-13`, gated) | 3 | **285** | **DESIGN-AMBIGUOUS** | No sentence in `§10A.5` addresses this specific gap. Half of `ambiguous_decline` is funds-caused (`population.yaml p_card_cause=0.50`), for which `R-06`/`R-07`'s mechanical proof (days 3+ structurally dead for a funds remedy) would apply and justify skipping day 3 — but the other, card-caused half has no equivalent mechanical justification: `SIM.md`'s within-day-ordering rule means a day-3 `card_change` contact for this half would be visible to that day's own retry, exactly as it is for `R-13`'s `CARD_BROKEN` case, and no rule offers that option. This is the one case in the table where a plausible design rationale exists but is not confirmed by the frozen text, and where a rule genuinely could have been written and was not — reported as ambiguous, not as a bug, and not resolved either way here. |
| *(Excluded from this table — already characterized in Stage 3 §4, not a "no rule" case)* `CARD_BROKEN` day 3 via `R-13`, gated by `withhold_applies` (417); `ambiguous_decline` day 2 via `R-15`, gated (236) | 2, 3 | 653 | *N/A — a dedicated rule exists and was suppressed by the AC predicate, not absent* | Reported here only so the category totals reconcile exactly: 132 + 990 + 1,680 + 285 + 653 = **3,740**, matching Stage 3's total R-16 count exactly. |

**Instrumentation/representation finding, reported separately from the
above table (per the stage's fourth listed category):** `R-16`'s static
`reason_code` is always `no_engagement_restraint`
(`src/rrx/agent/policy.py:180`) regardless of *why* it fired — the same
label covers "no rule exists for this day at all" (2,223+285=2,508
occurrences above) and "a rule exists but the withhold predicate
suppressed it" (417+236=653 occurrences, Stage 3 §4). **This is a
genuine representation limitation**: no ledger field distinguishes these
two causally different situations without the cross-reference this and
Stage 3 performed (`rationale` + `decline_code` + `tick`, none of which
alone is sufficient). It does not itself imply either situation is
handled wrongly — both were separately adjudicated above and in Stage 3
— but it does mean `reason_code=no_engagement_restraint`'s aggregate
count (`reason_code_distribution_wakeup_ticks` in every published
`metrics.json`) cannot be read as "the AC mechanism fired this many
times" without this disaggregation.

**Overall adjudication: no `DESIGN GAP` is found.** Of the 3,740 total
R-16 firings: 2,802 (74.9%) are `EXPECTED FALLTHROUGH`, directly or
closely traceable to explicit design text; 653 (17.5%) are not "no rule"
cases at all — a dedicated rule exists and was suppressed by the AC
predicate, already fully characterized as the dominant deficit mechanism
in Stage 3 §4/§5; and the remaining 285 (7.6%, `ambiguous_decline` day 3)
are `DESIGN-AMBIGUOUS` — plausible but not textually confirmed either
way. The rule table is not modified by this adjudication, per
contamination rule 1.

---

## 3. Parameter and threshold grid

The swept parameter is the literal `2` in `src/rrx/agent/policy.py:43`:
`withhold_applies = observations >= 2 and not any_engaged`
(`docs/A3-DESIGN.md §10A.3`). It is an inline literal — no config key
exists to sweep without either editing the frozen module (forbidden) or
writing a separate, parameterized copy outside it (done here,
`scripts/day9_frontier.py::make_a3d_policy_variant`, mirroring the
`rrx.baselines.a2_variants` precedent).

**Grid, recorded before execution (`CHANGELOG.md`, committed `2e81eec`):**
`{1, 2, 3, 4, 5, 6, 7}` — 7 points, current setting (`2`) at the center.

**Rationale (stated as a hypothesis before running, not fitted after):**
`withhold_applies` is evaluated only at three gated decision points
(`R-09` day 2 for `insufficient_funds`; `R-13` day 3 for `CARD_BROKEN`;
`R-15` day 2 for `ambiguous_decline`), and at every one of them the
preceding day-0 rule for that same decline code (`R-08`/`R-12`/`R-14`)
contacts unconditionally — so `observations` is deterministically `2`
(the day-0 auto-email plus the day-0 contact) whenever the predicate is
evaluated, absent engagement. The grid was chosen to bracket this value
symmetrically and confirm or refute, empirically, that thresholds `1`–`2`
collapse to the current behavior and `3`–`7` collapse to a single
different regime.

---

## 4. Experimental setup

- **Split:** `dev` only, `rrx.harness.splits.dev_indices()`, seeds
  1000–2999, N=2,000.
- **Master seed:** `20260825` (`rrx.sim.engine.MASTER_SEED`), identical to
  every other dev/holdout run.
- **Gate, executor, ledger:** unmodified production implementations
  (`rrx.agent.gate.evaluate_gate`, default executor path inside
  `run_episode_a3`, `rrx.agent.ledger.default_ledger_record`) — only the
  policy layer is substituted.
- **Command:** `python scripts/day9_frontier.py` (no arguments).
- **Parity check (required before trusting any sweep result):** the
  variant at `withhold_threshold=2` was run over full `dev` and compared
  field-by-field against `results/a3d-dev-20260828-01/metrics.json`
  (`invoice_recovery_rate`, `subscription_rescue_rate`, `total_contacts`,
  `contacts_per_invoice_recovered`, `contacts_per_subscription_rescued`,
  `n`, `n_wakeup_ticks`, `n_ledger_records_total`, `wait_count`,
  `escalation_count`, `gate_rejection_count`). **Result: exact match on
  every field — `PARITY CHECK PASSED`** (script output, this session).
  This confirms the hand-written variant is a faithful transcription of
  the frozen `a3d_policy`, not an independently-behaving approximation.

---

## 5. Frontier results

**MEASURED**, `results/day9_frontier/threshold_{1..7}.json`:

| Threshold | Invoice recovery | Subscription rescue | Total contacts | Contacts/invoice recovered | Contacts/rescue |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.4670 | 0.5305 | 2,825 | 3.0246 | 2.6626 |
| **2 (frozen default)** | **0.4670** | **0.5305** | **2,825** | **3.0246** | **2.6626** |
| 3 | 0.4920 | 0.5445 | 3,710 | 3.7703 | 3.4068 |
| 4 | 0.4920 | 0.5445 | 3,710 | 3.7703 | 3.4068 |
| 5 | 0.4920 | 0.5445 | 3,710 | 3.7703 | 3.4068 |
| 6 | 0.4920 | 0.5445 | 3,710 | 3.7703 | 3.4068 |
| 7 | 0.4920 | 0.5445 | 3,710 | 3.7703 | 3.4068 |

**Every tested point is reported above, including the four (4–7) that tie
threshold 3 and the one (1) that ties the frozen default.** No point was
dropped.

**The grid collapses to exactly two distinct behavioral regimes**,
confirming §3's pre-stated hypothesis empirically rather than assuming
it: `{1, 2}` (current) and `{3, 4, 5, 6, 7}` (unrestrained). This is
itself a finding about the parameterization, not an artifact of a small
grid — §3 already explains why, structurally, no intermediate regime is
reachable given the fixed day-0-contact schedule this policy shares with
A2-strengthened.

**Statistical backing (dev-only, using the frozen, unmodified
`rrx.sim.run_stage3.paired_bootstrap_ci`, 10,000 resamples, seed
`20260826`), threshold 3 vs. threshold 2, paired on the same 2,000 `dev`
episode indices** (`results/day9_frontier/threshold_2_vs_3_paired_ci.json`):

- Invoice recovery: diff = **+0.0250**, 95% CI **[+0.0185, +0.0320]** —
  excludes zero.
- Subscription rescue: diff = **+0.0140**, 95% CI **[+0.0065, +0.0215]**
  — excludes zero.

Both differences are statistically real on `dev`, not noise from a single
point estimate.

---

## 6. Comparator overlay

**MEASURED**, from already-published, already-committed dev artifacts —
not rerun (`results/a1-dev-20260828-01/metrics.json`,
`results/a2s-dev-20260828-01/metrics.json`,
`results/a3d-dev-20260828-01/metrics.json`):

| Arm / setting | Invoice recovery | Subscription rescue | Total contacts |
|---|---:|---:|---:|
| A1 (dev) | 0.4840 | 0.5095 | 3,780 |
| A2-strengthened (dev) | 0.4830 | 0.5385 | 3,651 |
| **A3-D original (threshold=2, dev)** | **0.4670** | **0.5305** | **2,825** |
| **A3-D, threshold≥3 (dev)** | **0.4920** | **0.5445** | **3,710** |

---

## 7. Safety results

**MEASURED**, all 7 threshold points (`results/day9_frontier/threshold_{1..7}.json`,
`safety_invariants` and `audit_coverage`): every one of the eight
`EVAL.md §5.2` safety-invariant counts is **zero** at every threshold —
`gate_rejections_total`, `contacts_to_cancelled_or_expired__R2_fired`,
`contacts_after_risk_flagged__R4_fired`, `card_change_for_insufficient_funds`,
`contacts_exceeding_budget__R5_fired`, `contacts_outside_quiet_hours__R6_fired`,
`unverified_codes_emitted__R8_fired` all `0`; `max_contacts_sent_observed=3`
(at budget, never exceeding it) at every threshold. `audit_coverage.ok = true`
for all 7 runs (2,000/2,000 episodes, zero violations). **The threshold
sweep does not compromise any safety gate at any tested value** — this is
expected, since the swept parameter only ever gates whether a
already-remedy-matched `CONTACT` is sent, never which remedy or whether
it passes the gate.

---

## 8. Frontier interpretation

1. **Does any threshold achieve higher invoice recovery than the best
   bounded comparator at equal or fewer contacts?** **Yes, against A1**:
   threshold≥3 (0.4920 recovery, 3,710 contacts) beats A1 (0.4840
   recovery, 3,780 contacts) on invoice recovery while using *fewer*
   contacts. **No, against A2-strengthened**: threshold≥3 beats
   A2-strengthened's recovery rate (0.4920 > 0.4830) but at *more*
   contacts (3,710 > 3,651) — higher recovery, higher cost, not "equal or
   fewer."
2. **Does any threshold dominate the best bounded comparator on both
   recovery and contact count?** **Yes, against A1** — threshold≥3 is
   strictly better than A1 on invoice recovery, subscription rescue,
   *and* total contacts simultaneously. **No, against A2-strengthened** —
   threshold≥3 beats A2-strengthened on both recovery metrics but not on
   contact count; this is a tradeoff point, not dominance.
3. **Is the original A3-D setting (threshold=2) obviously
   interior/dominated on the dev frontier?** **Yes, relative to
   threshold≥3, on the outcome axes** — threshold=2 has strictly lower
   invoice recovery and subscription rescue than threshold≥3, at the cost
   of substantially fewer contacts (2,825 vs. 3,710). This is not a
   strict Pareto dominance (threshold=2 uses fewer contacts, so it is not
   uniformly worse on every axis) — it is a point *on* the tradeoff curve,
   specifically the low-contact/low-recovery end of a two-point frontier.
   What is notable is that the *other* reachable point (threshold≥3)
   simultaneously beats **both** bounded comparators on **both** primary
   metrics on `dev` (§6), which threshold=2 does not.
4. **Does the frontier support a simple "threshold too conservative"
   explanation?** **Partially, and with an important structural caveat.**
   Moving the threshold in the "less restrictive" direction does recover
   ground against both comparators on `dev` — consistent with "the
   frozen threshold was positioned too conservatively for this tradeoff."
   But §3/§5 already established the parameterization itself is a step
   function in this population (only two reachable regimes, not a smooth
   dial) — so "the threshold was mis-tuned" is not quite the right frame
   either; more precisely, **the specific mechanism (`observations >= 2`,
   evaluated only at a fixed observation count of exactly 2) makes the
   predicate either fully active or fully inert given this schedule, and
   the frozen configuration happened to land on the fully-active
   (more restrained) side.**
5. **Or does it suggest a structural limitation?** Not in the sense of
   "no configuration can do better than the comparators" — threshold≥3
   is direct dev evidence against a purely structural-dominance
   explanation, since it beats A1 outright and improves on
   A2-strengthened's outcomes (at a higher contact cost). The structural
   element that *does* hold is narrower: **this specific predicate
   design, as implemented, cannot express an intermediate restraint
   level** — the only two dev-observed behaviors are "withhold whenever
   unengaged by the fixed day-0-contact schedule's second checkpoint" or
   "never withhold." A finer-grained restraint mechanism (e.g. one keyed
   to a continuously accumulating signal rather than a fixed
   two-observation checkpoint) was not tested and is out of scope for
   this stage.

**Answering the stage's core question directly:** this is evidence of a
**parameter-positioning problem** in the specific sense that the frozen
threshold happens to sit on the worse side of a real (if binary, not
continuous) dev tradeoff, **not** evidence of a structural dominance
problem — A3-D's decision-table architecture, at a different (still
dev-only, still unvalidated) point in its own reachable behavior space,
would have compared favorably to both bounded comparators on `dev`.

---

## 9. Limitations

1. **This is `dev` evidence only and has no bearing on the sealed
   `holdout` result.** `RESULTS.md`'s criterion 2 FAIL verdict is
   unchanged, unchallenged, and not reopened by anything in this
   document. Per `EVAL.md §3.5`, `holdout` is single-use per candidate
   release and has already been consumed for the current candidate — no
   number in this document could be holdout-validated even if a
   production change were later authorized, without a new candidate
   release and a new holdout run.
2. **No claim is made, or may be inferred, that threshold≥3 would beat
   A1/A2-strengthened on `holdout`.** Dev-to-holdout generalization is
   exactly the risk pre-registration and single-use holdout access exist
   to guard against; this document is descriptive `dev` evidence, not a
   holdout projection, and none of its numbers should be read as one.
3. **The comparator overlay (§6) is point-estimate only against
   A1/A2-strengthened.** A paired-bootstrap CI was computed for
   threshold 2 vs. 3 (both from this session's own runs, full per-episode
   data available), but not against A1/A2-strengthened's dev results
   specifically — doing so would require their per-episode dev outcome
   arrays, and was not part of this stage's required deliverable.
4. **The grid only explores one parameter along one axis.** The
   `observations >= N` predicate is the only restraint mechanism this
   stage tested; other possible restraint designs (e.g., a propensity
   threshold, a different observation-counting rule, per-decline-code
   thresholds) are untested and out of scope.
5. **No new production decision follows from this document.** Per the
   stage's explicit contamination boundary, no threshold is selected for
   deployment, `src/rrx/agent/policy.py` is unmodified, and no `A3.1` is
   created.

---

## 10. Conclusion

**NON-DOMINATED SETTING EXISTS ON DEV.**

A dev-only threshold (`withhold_threshold ≥ 3` — behaviorally a single
regime across the tested range 3–7) exists that beats A1 outright
(higher invoice recovery, higher subscription rescue, fewer total
contacts — full dominance) and improves on A2-strengthened on both
primary metrics (at a higher contact cost, not a dominance relationship
against that specific comparator). The frozen A3-D setting (`threshold=2`)
is not the best-positioned point A3-D's own decision-table architecture
can reach on `dev`. This is **not** a claim that the frozen holdout
result would have been different under a different threshold — `holdout`
was never accessed in this stage, cannot be re-accessed for this
candidate, and no number here is holdout-validated. It is a `dev`-only,
statistically-backed (§5) finding that A3-D's underperformance is at
least partly attributable to where its restraint parameter was set, not
solely to a structural ceiling on what its architecture could achieve
against these comparators.
