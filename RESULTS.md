# RESULTS.md — Day 8 Holdout Results

**Status:** Final, from the sealed holdout run. Written from sealed artifacts only — no number below was retyped from memory, recomputed with different parameters, or adjusted after being observed.

---

## 1. Executive summary

On the frozen `holdout` split, the pre-registered candidate arm **A3-D failed the pre-registered success criteria** (`EVAL.md §7` criterion 2, as refined by the eval-spec-v1.7 comparator/tie-set rule). On both primary metrics — invoice recovery rate and subscription rescue rate — A3-D did not merely fail to exceed its comparator arms; it scored **significantly lower** than every member of the statistically-tied comparator set, with the 95% confidence interval on each difference excluding zero in A3-D's unfavorable direction. A3-D also fell short of the illustrative 40%-of-gap target on both metrics. A3-D's contact discipline (criterion 3) was satisfied on both metrics — it used fewer total contacts and a better contacts-per-outcome ratio than its comparators — but this is moot given criterion 2's outcome. This is reported as a declared, pre-registered failure, per `EVAL.md §7`'s own instruction: no retuning or rerun was performed in response.

## 2. Holdout provenance

| Field | Value |
|---|---|
| Executing implementation (commit) | `29e8cd394402f9fef1b32a7ed1ffaf69f474a572` |
| Evaluation contract | `eval-spec-v1.10` (tag → `125eae8841562f6d5eccab58e055400340e71af6`) |
| Frozen implementation anchor | `code-freeze-holdout` → `4d45db461943978637673a5611a429e0fe826065` |
| Split | `holdout` |
| Episodes per arm | 2,000 |
| Episode indices | 9,000–10,999 inclusive, exact, verified — no duplicates, no gaps, no extras, for all five arms |
| Master seed | `20260825` |
| Config hash (all five arms, identical) | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` |
| Arms (exactly five, `EVAL.md §7.1` item A) | A0, A1, A2-strengthened, A3-D, A4 |
| Authorization | `holdout-authorized-latest` tag, resolved dynamically by `scripts/run_holdout.py`, equal to the executing commit at run time |

## 3. Artifact integrity / sealing

- **Seal tag:** `holdout-run-4d45db461943-sealed` → commit `2d451088ef5105b5075b5f4990803da5230e00bb`.
- **Checksum manifest:** `results/holdout/4d45db461943/SHA256SUMS` — SHA-256 over all 21 artifacts in the run directory, including the gitignored `a3_d/ledger.jsonl` (58,559 records, 0 malformed lines).
- **Independent verification performed twice** (once at seal time, once immediately before writing this document) via `rrx.eval.holdout_analysis.load_arm_data()`: for every arm, `episode_results.jsonl` contains exactly 2,000 records with the exact declared index set, and every metric independently recomputed from those raw records matches the committed `metrics.json` byte-for-byte. Both passes completed with zero `ArtifactError`s.

## 3A. Criterion-by-criterion verdict (all five, `EVAL.md §7`)

| # | Criterion (`EVAL.md` definition) | Verdict | Basis |
|---|---|---|---|
| 1 | All §5.2 invariants hold on `dev`, `holdout`, `stress` (`EVAL.md:773`, extended `EVAL.md:989-1001`) | **PASS** | Zero safety-invariant violations and zero audit-coverage violations on all three splits for A3-D (`results/a3d-dev-20260828-01/metrics.json`, `results/stress_summary.json`, `results/holdout/4d45db461943/a3_d/metrics.json` — see §10 below). Item E (legal executor mapping) is structurally unreachable for A3-D by construction and covered by `tests/test_executor_mapping_enforcement.py`. |
| 2 | Per primary metric, A3(-D) exceeds every member of the holdout comparator set, 95% CI excluding zero (`EVAL.md:774`, tie-set rule `EVAL.md:821-841`) | **FAIL** | Both metrics; see §7 below. A3-D scored significantly *below* its comparator set on both. |
| 3 | Total contacts and contacts/rescue ≤ same comparator arm(s) as criterion 2 (`EVAL.md:775`) | **PASS** | Both metrics; see §8 below. Moot given criterion 2's failure. |
| 4 | Uplift attributable to §3.4 structures, unexplained residual reported (`EVAL.md:776`; sole defined procedure at `EVAL.md:387-390` is A3-LLM − A3-D) | **N/A (holdout)** | A3-LLM was excluded from holdout for budget reasons (`EVAL.md:888-893`), and no A3-LLM holdout outcome may be inferred, estimated, or projected under any circumstance (`EVAL.md:903-907`). Criterion 4's only defined input is therefore unavailable by design, not by omission. A dev-only, N=500 A3-LLM − A3-D comparison exists (`results/tuning_log.md`) but is explicitly a "development-only secondary result... not scored against §7" (`EVAL.md:900-902`) and cannot substitute. |
| 5 | Graceful handling of three injected failure modes, failure visible in the ledger (`EVAL.md:777`, satisfied via stubbed planner per `EVAL.md:973-980`) | **N/A (holdout)** | Two of the three modes are LLM-planner faults; A3-D has no planner call at all (`EVAL.md:373-374`), so neither is a possible event on the arm that actually ran on holdout. `EVAL.md:897-898` lists A3-D as "the arm subject to criteria 1–4" — criterion 5 is not among them. All three modes are instead demonstrated at dev level against a stubbed planner (`LIMITATIONS.md §2.1`–§2.3, full test citations there); the mid-episode state-change mode is separately architecturally unreachable in `sim-v1` regardless of split. |

**On criteria 4 and 5 reading "N/A" rather than "FAIL":** neither failure is a result of A3-D underperforming or the harness misbehaving — both are consequences of the pre-declared, budget-driven decision (`EVAL.md §7.1` item A) to exclude A3-LLM from holdout, made before any holdout access and independent of any measured result. Marking them FAIL would misrepresent a scope exclusion as a missed criterion; marking them PASS would claim evidence that does not exist and that `EVAL.md` explicitly forbids fabricating. N/A is the accurate reading of the frozen text.

## 4. Per-arm primary metrics

| Arm | Invoice recovery rate | Subscription rescue rate | Total contacts | Contacts / invoice recovered | Contacts / subscription rescued |
|---|---:|---:|---:|---:|---:|
| A0 | 0.3585 | 0.3920 | 0 | n/a (no contacts) | n/a (no contacts) |
| A1 | 0.4640 | 0.4890 | 3,778 | 4.0711 | 3.8630 |
| A2-strengthened | 0.4685 | 0.5190 | 3,626 | 3.8698 | 3.4933 |
| **A3-D** | **0.4425** | **0.5085** | **2,871** | **3.2441** | **2.8230** |
| A4 (oracle — **not** a deployable comparator, reference only) | 0.5245 | 0.5445 | 3,076 | 2.9323 | 2.8246 |

## 5. Comparator selection and tie-set

Per the eval-spec-v1.7 tie-set rule (`EVAL.md:821-841`), computed from HOLDOUT data only, over the bounded set {A0, A1, A2-strengthened}:

- **Invoice recovery rate:** leader = A2-strengthened (0.4685). A0 vs. leader: diff +0.1100, 95% CI [0.0965, 0.1235] — excludes zero, not tied. A1 vs. leader: diff +0.0045, 95% CI **[-0.0015, 0.0105] — includes zero, tied.** **Comparator set = {A2-strengthened, A1}.**
- **Subscription rescue rate:** leader = A2-strengthened (0.5190). A0 vs. leader: diff +0.1270, CI [0.1130, 0.1420] — not tied. A1 vs. leader: diff +0.0300, CI [0.0220, 0.0385] — not tied. **Comparator set = {A2-strengthened} alone.**

## 6. Bootstrap method

Paired bootstrap on the difference of means, resampling paired episode indices (CRN-preserving), via `rrx.sim.run_stage3.paired_bootstrap_ci` — unmodified, frozen procedure:

- **Resamples:** 10,000
- **Seed:** 20260826
- **CI level:** 95%

## 7. Criterion 2 — A3-D vs. every comparator-set member, exact CIs

**Invoice recovery rate — FAIL.**
- A3-D vs. A1: diff = **-0.0215**, 95% CI **[-0.0315, -0.0115]** — excludes zero, in A3-D's unfavorable direction.
- A3-D vs. A2-strengthened: diff = **-0.0260**, 95% CI **[-0.0340, -0.0185]** — excludes zero, unfavorable.

**Subscription rescue rate — FAIL.**
- A3-D vs. A2-strengthened: diff = **-0.0105**, 95% CI **[-0.0180, -0.0030]** — excludes zero, unfavorable.

Criterion 2 requires A3-D's holdout rate to exceed **every** comparator-set member with the CI on the difference excluding zero. On both metrics, the CIs exclude zero but in the direction opposite to what the criterion requires — A3-D is significantly worse, not statistically tied and not better.

## 8. Criterion 3 — contact discipline

**Both metrics: PASS.** A3-D's total contacts (2,871) and both contacts-per-outcome ratios are lower than every comparator-set member's on both metrics (e.g., vs. A2-strengthened: 2,871 < 3,626 total contacts; 3.2441 < 3.8698 contacts/recovery; 2.8230 < 3.4933 contacts/rescue). This criterion is satisfied on both metrics, but is moot given criterion 2's failure — the comparator relationship criterion 3 depends on doesn't hold in A3-D's favor.

## 9. 40%-of-gap target analysis (illustrative, `[DESIGN]` — **not** a formal pass/fail criterion)

| Metric | Best-bounded (leader) | Oracle (A4) | Gap | Threshold (40% of gap) | A3-D actual | Target met? |
|---|---:|---:|---:|---:|---:|---|
| Invoice recovery rate | 0.4685 | 0.5245 | 0.0560 | 0.4909 | 0.4425 | **No** (0.0484 below) |
| Subscription rescue rate | 0.5190 | 0.5445 | 0.0255 | 0.5292 | 0.5085 | **No** (0.0207 below) |

This target, per `EVAL.md §7`'s own text, is "a target, not an expectation" and is separate from the criteria evaluated against comparators on holdout (criteria 1–3; see §3A above for the full five-criterion verdict, including why criteria 4 and 5 are N/A on holdout). A4 supplies the oracle rate for this calculation only; A4 is an empirical upper reference (`EVAL.md §7`: "not a deployable comparator") and is not itself evaluated against any criterion.

## 10. A3-D safety-invariant context (not a new criterion)

For context only — this is not one of the three formal criteria evaluated above, and is not being introduced as a substitute for criterion 2's failure. From A3-D's own sealed `metrics.json`: all eight `EVAL.md §5.2` safety-invariant counts are zero (`gate_rejections_total`, `contacts_to_cancelled_or_expired__R2_fired`, `contacts_after_risk_flagged__R4_fired`, `card_change_for_insufficient_funds`, `contacts_exceeding_budget__R5_fired`, `contacts_outside_quiet_hours__R6_fired`, `unverified_codes_emitted__R8_fired`, and `max_contacts_sent_observed=3` — at budget, not exceeding it), and `audit_coverage = {episodes_checked: 2000, ok: true, violations: []}`. A3-D's gate/safety behavior on holdout is clean; this has no bearing on the criterion 2 outcome above.

## 11. Final conclusion

**A3-D failed the pre-registered success criteria on holdout.** Criterion 2 fails on both primary metrics (invoice recovery rate and subscription rescue rate), with A3-D scoring significantly below its statistically-determined comparator set in both cases. This is the reportable, pre-registered result.

## 12. No post-hoc retuning or rerun

No parameter, prompt, policy, config, threshold, or comparator rule was changed after this result was observed, and none will be. `EVAL.md §7`'s own declared-failure clause applies directly: *"if A3 cannot beat the best-performing bounded arm at equal contact budget, we report that... We do not re-tune until the number looks good."* This holdout run is single-use (`EVAL.md §3.5`); no second run has been or will be performed for this candidate release.

## 13. Known provenance caveat

`results/holdout/4d45db461943/a3_d/run_params.json` records `"policy": "<unknown>"` and `"runner": "rrx.sim.engine.run_episode"` — both incorrect (A3-D actually executes via `rrx.harness.runner.run_episode_a3` / `rrx.agent.policy.a3d_policy`). This is a **pre-existing** documentation/metadata defect in `src/rrx/eval/arms.py`'s `_POLICY_QUALNAME` dict (missing an `ARM_A3D` entry) — confirmed present, identically, in the already-committed `results/stress-20260829-a3d/run_params.json` from Stage 7.3, well before Day 8. **It did not affect execution or any numerical result above**: `manifest.json`'s `arm` field is correct (`"A3-D"`), the actual code path executed was independently confirmed correct, and every metric in this document was independently recomputed from `episode_results.jsonl` and matched the committed `metrics.json` exactly.

---

## 14. Day 9 Diagnostic Analysis

**Status: post-hoc descriptive diagnostic analysis, performed after this document's §1–§13 were sealed.** Nothing below is a pre-registered `EVAL.md §7` criterion, changes any number in §1–§13 above, or has any power to revise the criterion 2 FAIL verdict. Each subsection summarizes one Day 9 stage's full write-up; the linked document is authoritative for method, evidence standard, and complete numbers — this section is a summary, not a replacement.

### 14.1 Economic analysis (Day 9 Stage 1, reconciled with Day 10)

Full documents: [`docs/analysis/DAY9-NET-VALUE.md`](docs/analysis/DAY9-NET-VALUE.md) (Stage 1, bracketed) and [`docs/analysis/DAY10-VALUE.md`](docs/analysis/DAY10-VALUE.md) (Day 10, measured — supersedes the Stage 1 bracket for current economic interpretation; authorization recorded in `CHANGELOG.md`, Day 10 entry).

**A post-hoc descriptive economic re-expression** of the §1–§13 holdout result, using the already-registered cost model (`configs/costs.yaml`) unchanged:

- A3-D saves **907 contacts vs. A1** (2,871 vs. 3,778) and **755 contacts vs. A2-strengthened** (2,871 vs. 3,626).
- Registered effective contact cost: **₹1.115/contact** — the sum of two separately labeled components in `configs/costs.yaml`: a **CITE**-labeled WhatsApp utility-message price of **₹0.115**, which is the only cash outflow, and an **ASSUMPTION**-labeled synthetic annoyance penalty of **₹1.00**. ₹1.115 is therefore an effective decision cost, **not** a pure cash price, and is not treated as one below.
- Break-even effective contact cost — the price at which A3-D's contact savings would exactly offset its lost invoice-recovery value — has two recorded values, in this order:
  - **Day 9 Stage 1, earlier bracketed estimate (retained as historical context):** **₹92.58–₹152.64 vs. A1** and **₹134.50–₹221.75 vs. A2-strengthened**. Stage 1 bracketed rather than measured because its authorization did not permit deriving new statistics from the sealed per-episode `episode_results.jsonl` artifacts, so it substituted two labeled population-level invoice-value references (registered population median vs. the lognormal population mean implied by the same registered distribution parameters) — neither a measured per-arm recovered value.
  - **Day 10, measured — supersedes the bracket for current post-hoc economic interpretation:** **₹154.81 vs. A1** and **₹236.25 vs. A2-strengthened** (`docs/analysis/DAY10-VALUE.md §4.1`), computed from the arm-conditional value of the recoveries A3-D actually forfeited, net of the registered 2.36% capture fee. Both land modestly **above** Day 9's upper bounds — Day 9's population-level reference slightly understated the deficit. The Day 9 bracket was low, not wrong in direction.
- The measured monetary deficit behind those figures (Day 10, descriptive): A3-D recovered **₹28,67,109** of the **₹64,66,221** of invoice value at risk, against A1's **₹30,10,915** and A2-strengthened's **₹30,49,789** — a gross shortfall of **−₹1,43,806 vs. A1** and **−₹1,82,680 vs. A2-strengthened**, for a contact-cost saving of **₹104.31 (cash-only) to ₹1,011.30 (effective)** vs. A1. These are point estimates carrying **no confidence interval**; the underlying *rate* differences carry the pre-registered CIs already published in §7.
- Both the bracketed and the measured figures are roughly two orders of magnitude above the actual registered ₹1.115 effective cost (139× and 212× respectively, on the measured values): under the registered cost model, A3-D's contact savings recover under ~1.3% of the value its recovery deficit forfeits.
- **No monetary break-even exists for subscription rescue.** No LTV or cancellation-hazard value is registered anywhere in this project's cost model (`configs/costs.yaml` has no such field; `EVAL.md §3.3`'s cancellation-hazard mechanic is unimplemented in the simulator), so no ₹ value can be attached to a rescue, and none is claimed.

### 14.2 Recovery-deficit decomposition (Day 9 Stage 2)

Full document: [`docs/analysis/DAY9-DECOMPOSITION.md`](docs/analysis/DAY9-DECOMPOSITION.md).

Episode-level, paired decomposition of the holdout invoice-recovery deficit, using episode-index pairing (the same CRN key the frozen paired bootstrap already uses):

**Against A2-strengthened:** 59 episodes where the comparator recovered and A3-D did not (comparator-only), 7 where A3-D recovered and the comparator did not (A3-D-only). **59/59 (100%) of the deficit episodes trace to fewer-contact, WAIT/withhold-driven behavior** (Bucket A); **0 are STOP-attributable**.

**Against A1:** 73 comparator-only, 30 A3-D-only. **47/73 are explained by the same fewer-contact/withhold mechanism; 26 remain unexplained** (Bucket E — 21 with equal contact counts, 5 where A3-D used *more* contacts than A1 yet still lost).

**Same-contact-count timing divergence (Bucket C) is explicitly NOT IDENTIFIABLE** — neither A1 nor A2-strengthened produces a ledger or any per-day contact record (only a per-episode total `contacts_sent`), so no artifact can establish which day their contacts were sent.

### 14.3 Mechanism attribution (Day 9 Stage 3)

Full document: [`docs/analysis/DAY9-DECOMPOSITION.md`](docs/analysis/DAY9-DECOMPOSITION.md) (Stage 3 section).

Attribution of A3-D's holdout behavior to `EVAL.md §3.4`'s three pre-registered advantage sources, using the ledger's structured `rationale` (decision-table rule id) field, cross-referenced against `docs/A3-DESIGN.md §10A.5`'s already-frozen per-rule basis text:

- **Retry-window timing:** empirically visible (2,193 wakeup ticks reason about it), but **zero measurable contribution to the deficit** — neither deficit population contains an episode from the decline buckets these rules govern.
- **Remedy matching:** **100% match rate among A3-D's actual holdout contacts** (0 mismatches / 2,871 contacts) — **zero deficit contribution**. The deficit is about contacts not sent, never a wrong remedy on one that was sent.
- **Within-episode adaptive contact: the dominant mechanism.** Rule `R-13`'s day-3 `withhold_applies` gate directly explains **59/59 of the A2-strengthened deficit episodes** and **41/47 of the A1 fewer-contact-attributable deficit episodes** (identified by decline-code composition, not the full 73 — see §14.2).
- **STOP divergence: zero.** None of A3-D's 311 holdout STOP actions overlap with either comparator's deficit population — the mechanism is withheld contacts (WAIT), never active disengagement.
- **Cancelled-at-open contamination: definitively ruled out.** Verified against both source (`src/rrx/harness/runner.py`) and the sealed ledger: all 111 `subscription_cancelled_by_customer` holdout episodes produce zero contacts and zero ledger records, identically across every arm — this bucket cannot contaminate any restraint statistic, structurally, not by argument.

**This is attribution, not causal proof.** It identifies which decision-table rule is empirically associated with each outcome and cross-checks that association against the design record; it does not run a counterfactual holdout to establish that a different rule would have changed the sealed result.

### 14.4 Dev-only frontier (Day 9 Stage 4)

Full document: [`docs/analysis/DAY9-FRONTIER.md`](docs/analysis/DAY9-FRONTIER.md).

**DEV-ONLY. Not holdout data, not a holdout claim, and not a new official agent.** A3-D's frozen withhold threshold (`2`, the value actually evaluated on holdout and reported in §1–§13 above) was swept on `dev` only, via a parameterized copy of the decision table kept entirely outside `src/rrx/agent/` — `src/rrx/agent/policy.py` was never modified.

- The grid `{1,...,7}` collapsed to two dev-observed regimes: `{1,2}` (identical to the frozen setting) and `{3,...,7}` (a single "unrestrained" regime).
- At threshold ≥3 on `dev`: invoice recovery **0.4920**, subscription rescue **0.5445**, total contacts **3,710** — vs. the frozen threshold=2 dev result (0.4670 / 0.5305 / 2,825) and the dev comparators A1 (0.4840 / 0.5095 / 3,780) and A2-strengthened (0.4830 / 0.5385 / 3,651).
- This dev-only setting **dominated A1 on the measured dev axes** (higher recovery, higher rescue, fewer contacts) and improved on A2-strengthened on both primary metrics (at higher contact cost). Paired dev bootstrap (frozen procedure, threshold 3 vs. 2): invoice +0.0250 CI [+0.0185, +0.0320], rescue +0.0140 CI [+0.0065, +0.0215] — both exclude zero. Full figures: `DAY9-FRONTIER.md §5`.
- **This is DEV-ONLY evidence and was NOT holdout validated.** `holdout` was not re-accessed to test it, cannot be re-accessed for this candidate (`EVAL.md §3.5`, single-use), and no claim is made that it would replicate. It is not, and is not described anywhere as, a new official agent, a selected configuration, or "A3.1" — none was created.

### 14.5 R-16 adjudication (Day 9 Stage 4, Part A)

Full document: [`docs/analysis/DAY9-FRONTIER.md`](docs/analysis/DAY9-FRONTIER.md) (§2).

Classification of every holdout `R-16` (decision-table default fallthrough) firing against the frozen design text:

- **No `DESIGN GAP` found.** Most `R-16` firings (74.9%) are `EXPECTED FALLTHROUGH`, directly or closely traceable to `docs/A3-DESIGN.md §10A.5`'s existing text (e.g. R-11's basis explicitly names days 7/14 as intended fallthrough days). A further 17.5% are not "no rule" cases at all — they are the `R-13` withhold-gated mechanism already covered in §14.3.
- **`ambiguous_decline` on day 3 (7.6% of `R-16` firings) remains `DESIGN-AMBIGUOUS`.** A plausible partial justification exists (the funds-caused half of this bucket is mechanically dead past day 2, by the same proof that governs `insufficient_funds`), but it does not fully cover the card-caused half, and no sentence in the frozen design text confirms this gap was deliberate. **This ambiguity is not resolved here** — it is reported exactly as `docs/analysis/DAY9-FRONTIER.md` leaves it.
