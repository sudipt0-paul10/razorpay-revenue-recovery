# Stage 5D — DEV statistical analysis plan

Status: PRE-REGISTERED. No confidence interval has been computed as of this
commit.

Depends on: `diagnostics/stage5d_capture_plan.md` (capture pre-registration,
committed `1f5a3a0`) and its execution (committed `13285f5`) — both already
verified to reproduce the official aggregate metrics exactly.

## 1. Scope

This is **DEV analysis only**.

## 2. DEV cannot pass or fail EVAL.md §7

The bounded-vs-agent criterion in `EVAL.md §7` is defined over the holdout
split. No result computed here can satisfy or fail that criterion. Nothing
in this analysis is a §7 determination.

## 3. No holdout data will be accessed

Only the `dev` split, indices 1000–2999 (`master_seed=20260825`), is used.

## 4. No policy tuning or reruns will occur based on DEV results

Whatever the twelve comparisons below show, no policy code changes and no
arm is rerun as a consequence of this analysis.

## 5. Bounded non-agent arms

`{A0, A1, A2-strengthened}` — the pre-registered comparator set (`EVAL.md
§4.3`'s post-eval-spec-v1.6 A1 content, and the strengthened-A2 baseline).

## 6. Agent arm

`A3-D` — the deterministic-ablation agent arm.

## 7. World-level CRN pairing is present

All four arms' `results/capture/<run_id>/episodes.jsonl` carry the identical
ordered index set `1000..2999` (verified in Part 2 of this stage, not
assumed) — the world draw (cohort assignment, latent state) for episode `i`
is shared bit-for-bit across all four arms, which is what licenses a paired
(not independent-samples) bootstrap.

## 8. Per-message engagement pairing limitation

Per `EVAL.md §8` item 7 (already frozen, restated here for visibility, not
introduced by this analysis): per-message engagement draws use an arm-local
message-index counter and are **not** fully paired across arms that send
different numbers of messages. World-level CRN pairing (§7 above) is intact
regardless; this limitation affects only within-episode message-level noise,
not the episode-level outcome pairing the bootstrap below relies on.

## 9. Bootstrap implementation

`rrx.sim.run_stage3.paired_bootstrap_ci`, used exactly as implemented — no
modification, no substitute interval (no BCa, no studentized, no normal
approximation, no t-test).

## 10. Bootstrap parameters

- resamples: `10,000` (the function's own `N_BOOTSTRAP_RESAMPLES` default)
- confidence level: `95%` (the function's own `CI_LEVEL` default)
- seed: `20260826` (the function's own `BOOTSTRAP_SEED` default)
- statistic: `mean(b) - mean(a)`, with `a`/`b` resampled at identical
  episode indices each draw (paired, per the function's own docstring)

## 11. No multiplicity correction

No multiple-comparison correction (Bonferroni, Holm, FDR, etc.) is applied
to the twelve intervals below — none is already specified by the frozen
repository methodology (`EVAL.md §6` does not require one), so none is
introduced here.

## 12. No holdout comparator selected from DEV

This analysis does not choose, recommend, or rank a holdout comparator.

## 13. Six required bounded-arm pairwise comparisons

Invoice recovery: `A1 − A0`, `A2-strengthened − A0`, `A1 − A2-strengthened`
Subscription rescue: `A1 − A0`, `A2-strengthened − A0`, `A1 − A2-strengthened`

## 14. Six descriptive A3-D comparisons — DESCRIPTIVE / NON-CRITERION-BEARING

Invoice recovery: `A3-D − A0`, `A3-D − A1`, `A3-D − A2-strengthened`
Subscription rescue: `A3-D − A0`, `A3-D − A1`, `A3-D − A2-strengthened`

These six are explicitly descriptive: they report DEV-split effect sizes and
uncertainty for context only. They carry no pass/fail meaning under `EVAL.md
§7`, which is holdout-only.

## 15. Comparator-selection tie handling is untouched

Whatever eventual rule `EVAL.md §7` uses to break a tie among bounded
comparators for holdout comparator selection is **not** being decided,
altered, or pre-empted by this DEV analysis. This document computes
descriptive statistics only; it does not constitute or substitute for that
selection step.

## Provenance (restated from the capture plan, for this document's own
completeness)

| Arm | run_id | original git_sha | config_hash |
|---|---|---|---|
| A0 | `a0-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` |
| A1 | `a1-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | same |
| A2-strengthened | `a2s-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | same |
| A3-D | `a3d-dev-20260828-01` | `e829161b8b174d2afca317f571048810b426b587` | same |

split=`dev`, indices=`1000`–`2999` inclusive (N=2000), master_seed=`20260825`
for all four.
