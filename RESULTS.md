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

This target, per `EVAL.md §7`'s own text, is "a target, not an expectation" and is separate from the three pre-registered pass/fail criteria (1, 2, 3). A4 supplies the oracle rate for this calculation only; A4 is an empirical upper reference (`EVAL.md §7`: "not a deployable comparator") and is not itself evaluated against any criterion.

## 10. A3-D safety-invariant context (not a new criterion)

For context only — this is not one of the three formal criteria evaluated above, and is not being introduced as a substitute for criterion 2's failure. From A3-D's own sealed `metrics.json`: all eight `EVAL.md §5.2` safety-invariant counts are zero (`gate_rejections_total`, `contacts_to_cancelled_or_expired__R2_fired`, `contacts_after_risk_flagged__R4_fired`, `card_change_for_insufficient_funds`, `contacts_exceeding_budget__R5_fired`, `contacts_outside_quiet_hours__R6_fired`, `unverified_codes_emitted__R8_fired`, and `max_contacts_sent_observed=3` — at budget, not exceeding it), and `audit_coverage = {episodes_checked: 2000, ok: true, violations: []}`. A3-D's gate/safety behavior on holdout is clean; this has no bearing on the criterion 2 outcome above.

## 11. Final conclusion

**A3-D failed the pre-registered success criteria on holdout.** Criterion 2 fails on both primary metrics (invoice recovery rate and subscription rescue rate), with A3-D scoring significantly below its statistically-determined comparator set in both cases. This is the reportable, pre-registered result.

## 12. No post-hoc retuning or rerun

No parameter, prompt, policy, config, threshold, or comparator rule was changed after this result was observed, and none will be. `EVAL.md §7`'s own declared-failure clause applies directly: *"if A3 cannot beat the best-performing bounded arm at equal contact budget, we report that... We do not re-tune until the number looks good."* This holdout run is single-use (`EVAL.md §3.5`); no second run has been or will be performed for this candidate release.

## 13. Known provenance caveat

`results/holdout/4d45db461943/a3_d/run_params.json` records `"policy": "<unknown>"` and `"runner": "rrx.sim.engine.run_episode"` — both incorrect (A3-D actually executes via `rrx.harness.runner.run_episode_a3` / `rrx.agent.policy.a3d_policy`). This is a **pre-existing** documentation/metadata defect in `src/rrx/eval/arms.py`'s `_POLICY_QUALNAME` dict (missing an `ARM_A3D` entry) — confirmed present, identically, in the already-committed `results/stress-20260829-a3d/run_params.json` from Stage 7.3, well before Day 8. **It did not affect execution or any numerical result above**: `manifest.json`'s `arm` field is correct (`"A3-D"`), the actual code path executed was independently confirmed correct, and every metric in this document was independently recomputed from `episode_results.jsonl` and matched the committed `metrics.json` exactly.
