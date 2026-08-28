# Stage 5D — Pre-registered DEV episode-outcome capture plan

Status: PRE-REGISTERED. No capture has been executed as of this commit.

## 1. Nature of this change

This is a **defect correction for missing persisted episode-level data**, not
a policy change, tuning change, simulator change, or new experiment. The
official DEV runs (Stage 5D Part B) computed per-episode `EpisodeResult`
objects (which already carry `invoice_recovered: bool` and
`subscription_rescued: bool`) for every episode, in memory, and used them to
compute the aggregate `metrics.json` files already committed under
`results/`. The per-episode list itself was never serialized to disk for any
arm. `EVAL.md §6`'s paired bootstrap requires per-episode paired vectors,
which do not currently exist as artifacts. This plan captures them via a
deterministic re-execution of the same computation, at the same code state,
over the same inputs — an additive, output-layer-only change.

## 2. Original aggregate results are immutable

`results/a0-dev-20260828-01/`, `results/a1-dev-20260828-01/`,
`results/a2s-dev-20260828-01/`, and `results/a3d-dev-20260828-01/` will not
be modified, added to, or deleted from by this capture. Capture output goes
exclusively to a new, separate location (§14 below).

## 3. Scope: all four arms, one pass

A0, A1, A2-strengthened, and A3-D are all captured together, under this one
pre-registered plan. No selective capture.

## 4. Original run IDs and original SHAs (from each arm's `manifest.json`)

| Arm | Original run_id | git_sha | config_hash | spec_version |
|---|---|---|---|---|
| A0 | `a0-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` | `eval-spec-v1.6` |
| A1 | `a1-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` | `eval-spec-v1.6` |
| A2-strengthened | `a2s-dev-20260828-01` | `f5c992ae6fc98ff1230e8e0e91cf1f361a589f43` | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` | `eval-spec-v1.6` |
| A3-D | `a3d-dev-20260828-01` | `e829161b8b174d2afca317f571048810b426b587` | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` | `eval-spec-v1.5` |

**A3-D's original SHA (`e829161b`) differs from A0/A1/A2-strengthened's
(`f5c992a`)** — confirmed by reading each `manifest.json` directly, not
assumed. This plan does not treat that difference as immaterial by fiat:
`git diff --stat e829161..HEAD -- src/rrx/sim/ src/rrx/agent/policy.py
src/rrx/agent/reason_codes.py src/rrx/harness/ configs/episode.yaml
configs/population.yaml` is empty (byte-identical across both commits, and
`config_hash` independently confirms the two config files are identical),
but the A3-D capture will still execute against the literal `e829161`
tree via a temporary `git worktree`, not against current HEAD, so the
capture is pinned to the recorded SHA rather than to an inference that the
SHA doesn't matter here.

## 5. Expected integer outcome counts (from the user-supplied official figures)

| Arm | invoice_recovered (of 2000) | subscription_rescued (of 2000) |
|---|---:|---:|
| A0 | 705 | 811 |
| A1 | 968 | 1019 |
| A2-strengthened | 966 | 1077 |
| A3-D | 934 | 1061 |

## 6. Reproduction controls (identical for all four arms)

- split: `dev`
- indices: `1000`–`2999` inclusive (N=2000)
- master_seed: `20260825`
- config_hash: `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` (identical for all four, confirmed above)
- git_sha: per-arm, exactly as recorded in that arm's own `manifest.json` (§4)

## 7. Capture is output-layer only

The capture reuses the existing, already-tested computation entry points
(`rrx.eval.arms.run_arm_cohort` for A0/A1/A2-strengthened at HEAD;
`rrx.eval.runner.run_a3d_dev_cohort` for A3-D, imported from the `e829161`
worktree) exactly as-is. No change to policy logic, simulator logic, RNG
behavior, episode iteration order, or the official metrics computation. The
only new code persists the per-episode booleans already present on the
`EpisodeResult` objects those functions already return.

## 8. No simulator/policy behavior changes

Confirmed clean: `git status --short -- src/rrx/sim/ src/rrx/agent/
src/rrx/harness/` is empty at the time of this plan. Frozen-file hashes are
recorded in the Stage 5D Step 2/Step 8 report and will be re-verified
identical after capture.

## 9. No holdout access

Only the `dev` split, indices 1000–2999, is touched.

## 10. No confidence intervals have been computed

No call to `rrx.sim.run_stage3.paired_bootstrap_ci` occurs in this stage.

## 11. All four arms captured in one pass

Executed as a single sequential script run covering A0, A1, A2-strengthened,
A3-D before any comparison or analysis step.

## 12. Critical branch: exact-match requirement

If **any** arm's reproduced integer `invoice_recovered` count OR
`subscription_rescued` count differs from the expected count in §5, the
capture stage STOPS immediately. No debugging, no code changes to force a
match, no rerun of that arm. The mismatch is reported exactly (arm, expected
vs. actual, for both counts) and no further stage proceeds.

## 13. Acceptance condition

Only if all four arms match §5 exactly (integer equality, no tolerance) may
the captured per-episode vectors be accepted as deterministic reproductions
of the original runs and used as input to the (separately authorized) DEV
statistical analysis stage.

## 14. Capture artifact location

```
results/capture/a0-dev-20260828-01/
results/capture/a1-dev-20260828-01/
results/capture/a2s-dev-20260828-01/
results/capture/a3d-dev-20260828-01/
```

Never under a new official run ID; never inside the original
`results/<arm>-dev-20260828-01/` directories.

## 15. Capture artifact contents (minimum)

Each `results/capture/<original_run_id>/episodes.jsonl` holds exactly 2000
lines, one per episode, each an object with at minimum:

```json
{"episode_index": 1000, "invoice_recovered": true, "subscription_rescued": false}
```

## 16. `capture_manifest.json`

Each capture directory also gets a `capture_manifest.json` linking back to
the original run and recording the provenance/control fields used for that
arm's capture: `original_run_id`, `original_git_sha` (the SHA actually used
to execute this capture — matching §4), `capture_git_sha` (HEAD at the time
the capture script itself ran, recorded for transparency; for A3-D this will
differ from `original_git_sha` since a worktree at `original_git_sha` is
used for the simulation itself), `split`, `index_start`, `index_end`, `n`,
`master_seed`, `config_hash`, `spec_version`, `capture_timestamp`.

## 17. No CI generated in this stage

## 18. No comparator selection in this stage

---

Reproduction controls, expected counts, and artifact paths above are frozen
as of this plan's commit. Execution (Steps 5–9 of the Stage 5D capture
prompt) follows only after this plan is committed and reviewed.
