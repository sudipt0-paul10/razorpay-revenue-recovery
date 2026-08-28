# Stage 5D — DEV statistical results

Status: DEV analysis, non-confirmatory. Computed per the pre-registered
`diagnostics/stage5d_dev_analysis_plan.md`.

**This document does not determine, and must not be read as determining,
whether A3-D passes or fails `EVAL.md §7`.** That criterion is evaluated on
the holdout split, which has not been accessed.

## 1. Provenance for every input run

| Arm | run_id | original git_sha | config_hash | spec_version |
|---|---|---|---|---|
| A0 | `a0-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` | `eval-spec-v1.6` |
| A1 | `a1-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | same | `eval-spec-v1.6` |
| A2-strengthened | `a2s-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | same | `eval-spec-v1.6` |
| A3-D | `a3d-dev-20260828-01` | `e829161b8b174d2afca317f571048810b426b587` | same | `eval-spec-v1.5` |

**A3-D's original SHA differs from the comparator arms' SHA** (`e829161` vs
`f5c992a`). Confirmed (`diagnostics/stage5d_capture_plan.md §4`) that the
intervening commits touch only `EVAL.md`/`CHANGELOG.md` (the `eval-spec-v1.6`
A1 amendment) and new `rrx.eval`/`rrx.baselines.a1` orchestration code —
`git diff --stat e829161..f5c992a` over `src/rrx/sim/`,
`src/rrx/agent/policy.py`, `src/rrx/agent/reason_codes.py`,
`src/rrx/harness/`, and both config files is empty. A3-D's capture was still
executed against the literal `e829161` tree via a temporary worktree, not
against this inference.

**A1's canonicalization**: A1's content (`card_change` remedy at day 0 and
day 3) was adopted as a new consequential decision under `eval-spec-v1.6`
(`EVAL.md §4.3`), not recovered from an original unambiguous spec. See that
section for the full decision record. This DEV analysis uses that canonical
A1 as-is; it does not revisit the decision.

split = `dev`, indices = `1000`–`2999` inclusive, N = `2000`, master_seed =
`20260825` — identical for all four arms.

## 2. Input validation

All four `results/capture/<run_id>/episodes.jsonl` verified (not assumed)
before any bootstrap ran:

- exactly 2000 rows each
- episode indices exactly `1000..2999`, strictly ordered, identical index
  set across all four arms (world-level CRN pairing — §4 below)
- no duplicate indices
- `invoice_recovered`/`subscription_rescued` fields are JSON booleans in
  every row
- recomputed aggregate rates from the vectors exactly reproduce the
  official `metrics.json` figures:

| Arm | invoice recovery (vector / official) | subscription rescue (vector / official) |
|---|---|---|
| A0 | 0.3525 / 0.3525 | 0.4055 / 0.4055 |
| A1 | 0.4840 / 0.4840 | 0.5095 / 0.5095 |
| A2-strengthened | 0.4830 / 0.4830 | 0.5385 / 0.5385 |
| A3-D | 0.4670 / 0.4670 | 0.5305 / 0.5305 |

All four matched exactly; no vector was modified and no arm was rerun.

## 3. Bootstrap methodology

`rrx.sim.run_stage3.paired_bootstrap_ci`, used unmodified. Statistic:
`mean(b) - mean(a)`, paired at identical resampled episode indices for `a`
and `b` on each of 10,000 draws. Resamples: `10,000`. Confidence level:
`95%`. Seed: `20260826` (the function's own default — not overridden).

## 4. World-level CRN pairing / per-message pairing limitation

All four episode-index sequences are identical (§2), which is what licenses
the paired (not independent-sample) bootstrap used here. Per `EVAL.md §8`
item 7 (already frozen, not introduced by this analysis): per-message
engagement draws use an arm-local message-index counter and are not fully
paired across arms sending different numbers of messages — this is expected
variance in message-level noise, not a bias, and does not affect the
episode-level world pairing the bootstrap relies on.

## 5. Results — six pre-registered bounded-arm comparisons

| # | Comparison | Metric | Point (B−A) | 95% CI low | 95% CI high | N |
|---|---|---|---:|---:|---:|---:|
| 1 | A1 − A0 | invoice recovery | +0.1315 | +0.1170 | +0.1465 | 2000 |
| 2 | A2-strengthened − A0 | invoice recovery | +0.1305 | +0.1160 | +0.1455 | 2000 |
| 3 | A1 − A2-strengthened | invoice recovery | +0.0010 | −0.0060 | +0.0080 | 2000 |
| 4 | A1 − A0 | subscription rescue | +0.1040 | +0.0905 | +0.1175 | 2000 |
| 5 | A2-strengthened − A0 | subscription rescue | +0.1330 | +0.1185 | +0.1480 | 2000 |
| 6 | A1 − A2-strengthened | subscription rescue | −0.0290 | −0.0375 | −0.0205 | 2000 |

## 6. Results — six descriptive A3-D comparisons (DESCRIPTIVE / NON-CRITERION-BEARING)

| # | Comparison | Metric | Point (B−A) | 95% CI low | 95% CI high | N |
|---|---|---|---:|---:|---:|---:|
| 7 | A3-D − A0 | invoice recovery | +0.1145 | +0.1005 | +0.1290 | 2000 |
| 8 | A3-D − A1 | invoice recovery | −0.0170 | −0.0270 | −0.0070 | 2000 |
| 9 | A3-D − A2-strengthened | invoice recovery | −0.0160 | −0.0235 | −0.0090 | 2000 |
| 10 | A3-D − A0 | subscription rescue | +0.1250 | +0.1110 | +0.1395 | 2000 |
| 11 | A3-D − A1 | subscription rescue | +0.0210 | +0.0120 | +0.0300 | 2000 |
| 12 | A3-D − A2-strengthened | subscription rescue | −0.0080 | −0.0155 | −0.0010 | 2000 |

All twelve computed with `n_resamples=10000`, `ci=0.95`, `seed=20260826`,
using the frozen function's defaults directly, no sign-convention change.

## 7. Descriptive interpretation

On this DEV split, both A1 and A2-strengthened show a 95% CI clearly above
zero relative to A0 on both metrics (#1, #2, #4, #5) — both bounded
comparators separate from the no-action baseline here. A1 vs.
A2-strengthened is not distinguishable on invoice recovery (#3, CI spans
zero) but A2-strengthened's CI sits below zero for A1 on subscription rescue
(#6) — i.e., on this split A2-strengthened's rescue rate exceeds A1's.

The six A3-D rows (#7–12) are reported for descriptive context only. A3-D's
CI is above zero relative to A0 on both metrics (#7, #10). Relative to the
two bounded comparators, A3-D's CI sits below zero on invoice recovery (#8,
#9) and is mixed on subscription rescue — above zero vs. A1 (#11), below
zero vs. A2-strengthened (#12, narrowly, CI upper bound −0.0010). None of
this constitutes, implies, or substitutes for an `EVAL.md §7` determination,
which is holdout-only; no comparator is selected or recommended from these
figures, and no interpretation here should be read as confirmatory.

## 8. Reproduction summary

All four original aggregate results were exactly reproduced from the
captured per-episode vectors (§2) — the capture's deterministic-reproduction
guarantee, established in `diagnostics/stage5d_capture_plan.md`, held for
every arm used in this analysis.
