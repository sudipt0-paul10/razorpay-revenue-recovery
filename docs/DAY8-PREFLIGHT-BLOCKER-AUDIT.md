# DAY 8 — PRE-HOLDOUT PROVENANCE BLOCKER AUDIT

**Scope:** audit only, at `HEAD` = `code-freeze-holdout` = `4d45db461943978637673a5611a429e0fe826065`. No file modified, no fix implemented, no commit/push, no test run, no preflight step run, no holdout accessed or authorized. All findings below are read-only inspection (`Read`/`Grep`/`git show`).

**Prior finding carried forward, not re-litigated:** the two `[CORRECTION, eval-spec-v1.11]` passages (`EVAL.md:963-971`, `docs/A3-DESIGN.md:850-858`) are documentation-only and do not affect any of the three issues below.

---

## Issue 1 — Per-episode persistence

### STATUS: **BLOCKER**

### What "the standard runner" actually is

Two distinct dispatch layers exist, and both matter here:

- `src/rrx/harness/runner.py` — the low-level, single-episode day-loop driver for the A3 arms only (`run_episode_a3`). Not itself an evaluation entry point.
- `src/rrx/eval/runner.py` (Stage A) + `src/rrx/eval/arms.py` (Stage B) — **the actual evaluation orchestration layer that produces `results/<run_id>/` artifacts for every arm**, including the generalized `run_official_arm()` (`src/rrx/eval/arms.py:244-260`) that Stage B built specifically so "eventual A1/A2 runs produce run_id/manifest/run_params/metrics 'using the same basic structure'" (`arms.py:252-254`). This is the code path a holdout run would use.

### Exact code path and artifacts written, per arm

`src/rrx/eval/arms.py:166-220` (`run_arm_cohort`, the single dispatch point) routes each arm to one of:

| Arm | Dispatch (`arms.py:192-215`) | Underlying runner | Ledger? |
|---|---|---|---|
| A0 | `run_policies_cohort` (permanent policy) | `rrx.sim.engine.run_episode` | `None` |
| A1 | `run_policies_cohort` (temporarily registered) | `rrx.sim.engine.run_episode` | `None` |
| A2-strengthened | `run_policies_cohort` (temporarily registered) | `rrx.sim.engine.run_episode` | `None` |
| A3-D | `run_a3d_dev_cohort` (`src/rrx/eval/runner.py:87-...`) | `rrx.harness.runner.run_episode_a3` | list of `LedgerRecord` |
| A4 | direct loop over `run_a4_episode` | `rrx.baselines.a4.run_a4_episode` | `None` |

`arms.py:173-177`'s own docstring: *"Returns (results, ledger) - ledger is None (not []) for arms with no ledger mechanism at all."* Confirmed by directory contents at `4d45db4`:
```
results/a0-dev-20260828-01/   → manifest.json, metrics.json, run_params.json         (no ledger.jsonl)
results/a3d-dev-20260828-01/  → manifest.json, metrics.json, run_params.json, ledger.jsonl
```

Whichever writer runs (`arms.py:244-379` for A0/A1/A2-strengthened/A4, or `runner.py:453-522`'s `main()` for A3-D), the on-disk output is exactly:
- `manifest.json` — the frozen 11-field `RunManifest` (`arms.py:344-362`, `runner.py:498-511`).
- `metrics.json` — **aggregates only**: `compute_metrics_results_only(results)` for policies-arms with no ledger (`runner.py:340-...`), or `compute_metrics(results, ledger_records)` plus `audit_coverage` for A3-D (`arms.py:325-331`). Both write a single `dict` of counts/rates via `json.dumps(metrics, ...)` (`arms.py:341-342`) — never a per-episode array.
- `run_params.json` — `split`, `index_start`, `index_end`, `n`, `master_seed`, `arm`, `policy`, `runner` (`runner.py:404-446`) — a reproducibility sidecar (which cohort/config was used), not per-episode outcomes.
- `ledger.jsonl` — **A3-D/A3-LLM only** (`arms.py:335-339`, `runner.py:490-493`), one record per *tick*, not one record per *episode outcome*.

### Is a complete per-episode outcome vector persisted?

**No, not by this path, for any of the five arms.**

`run_arm_cohort` returns `list[EpisodeResult]` in memory (`arms.py:166,173`; `EpisodeResult` is `src/rrx/sim/engine.py:68-75`: `opening_condition_key, invoice_amount_inr, invoice_recovered, subscription_rescued, contacts_sent, wasted_attempts, card_change_sent_for_insufficient_funds` — seven fields). That list (`results`) is consumed only by `compute_metrics`/`compute_metrics_results_only` to produce aggregate counts (`arms.py:324-327`, `runner.py:484`) and is then **discarded** — no code in `arms.py` or `runner.py` serializes `results` itself to disk in any form, for any arm. Paired bootstrap (`EVAL.md §6`, `rrx.sim.run_stage3.paired_bootstrap_ci`) requires exactly this per-episode vector, keyed by episode index, to recompute after the fact; it is not available from any artifact this path writes.

This is not a hypothesis — the repository already documents the consequence it caused once: `results/tuning_log.md:492-494` ("Day 6 Stage 6T found paired bootstrap analysis impossible from the stored artifacts — no per-episode outcome data was persisted for any GPT cell, only aggregate rates").

### Does `results/capture/` satisfy the holdout requirement?

**No — confirmed unrelated/manual, not usable as-is.** `diagnostics/stage5d_capture.py` (full file read):

- **Invocation:** `python diagnostics/stage5d_capture.py <a0|a1|a2s|a3d>` (`stage5d_capture.py:19-22,200-207`) — a standalone script run by hand, not called by `arms.py`/`runner.py`, not wired into `run_official_arm()` or `main()`.
- **Scope:** hardcoded `DEV_INDEX_START = 1000`, `DEV_INDEX_END = 2999` (`stage5d_capture.py:35-36`) — dev-only; no split parameter exists to point it at `holdout`.
- **Arm coverage:** `a0`, `a1`, `a2s`, `a3d` only (`stage5d_capture.py:39-44,117-121`). **No `a4` entry exists anywhere in the script** — A4, one of the five required holdout arms, has no capture path at all.
- **Provenance pinning:** the module docstring (`stage5d_capture.py:11-16`) requires the caller to manually point `PYTHONPATH` at specific historical git worktrees (`f5c992a` for a0/a1/a2s, `e829161` for a3d) to reproduce one *specific already-executed* dev run — it is a retroactive reproduction tool for a fixed, historical result, not a general per-run persistence feature. `capture_a3d()` (`stage5d_capture.py:177-182`) even asserts the worktree's `current_git_sha()` equals that pinned historical SHA and raises if not.
- **Field coverage:** `_write_capture` (`stage5d_capture.py:63-82`) writes only `episode_index`, `invoice_recovered`, `subscription_rescued` — **2 of `EpisodeResult`'s 7 fields.** `contacts_sent`, `wasted_attempts`, `opening_condition_key`, `invoice_amount_inr`, and `card_change_sent_for_insufficient_funds` are not captured, so metrics like contacts-per-rescue, per-condition breakdowns, or time-to-rescue could not be reconstructed from this file even where it exists.

**Verdict:** `results/capture/` is a one-off, manual, dev-only, four-of-five-arm, two-of-seven-field diagnostic reproduction mechanism (Stage 5D). It cannot satisfy `EVAL.md §6`'s reproducibility requirement or the paired-bootstrap need for a `holdout` run without being reinvoked by hand, retargeted to `holdout` indices, and extended to cover A4 and the missing fields — none of which is automatic.

### Minimal implementation change that would be required (not made)

Confined to `src/rrx/eval/arms.py`'s writer path (`run_official_arm`, `arms.py:244-379`) and `src/rrx/eval/runner.py`'s `main()` (`runner.py:453-522`), since both already have `results: list[EpisodeResult]` in scope at the point they currently discard it:

1. Add one write step, alongside the existing `metrics_path`/`ledger_path` writes, that serializes `results` to `results/<run_id>/episode_results.jsonl` (or equivalent), one JSON object per episode keyed by its index (the indices are already available as `resolved_indices` in both functions), containing all seven `EpisodeResult` fields.
2. No change is needed to `EpisodeResult`, `run_arm_cohort`, `compute_metrics`, or any simulator/policy/gate code — `results` already exists in memory with full fidelity at the exact point the new write would occur.
3. `results/capture/`'s field list (`invoice_recovered`, `subscription_rescued` only) is insufficient by the plan's own reproducibility bar; the new writer should persist the full seven-field record, not just the two `stage5d_capture.py` chose for its narrower purpose.

**Not implemented in this pass**, per instruction.

---

## Issue 2 — Spec version provenance

### STATUS: **BLOCKER**

### Every definition/use of `SPEC_VERSION` / `spec_version`

```
$ grep -rn "SPEC_VERSION\|spec_version" --include="*.py" --include="*.yaml" .   (excluding .venv)
src/rrx/spec/manifest.py:35        spec_version: str                              (schema field only)
src/rrx/eval/runner.py:58          SPEC_VERSION = "eval-spec-v1.8"                (THE definition)
src/rrx/eval/runner.py:500         spec_version=SPEC_VERSION,                     (consumer #1: main())
src/rrx/eval/arms.py:346           spec_version=eval_runner.SPEC_VERSION,         (consumer #2: run_official_arm())
configs/model_params.yaml:16       spec_version: eval-spec-v1-draft               (unrelated, unread by any code)
configs/population.yaml:19         spec_version: eval-spec-v1-draft               (unrelated, unread by any code)
diagnostics/stage5d_capture.py:45  _ORIGINAL_SPEC_VERSION = {...}                 (historical record for a one-off script, not live)
tests/test_manifest.py:31          spec_version="eval-spec-v1.3"                  (test fixture literal, not production)
```

**There is exactly one live production definition**, `src/rrx/eval/runner.py:58`, and **exactly two consumers**, both of which read that same constant (`runner.py:500` directly; `arms.py:346` via `eval_runner.SPEC_VERSION`). `configs/model_params.yaml:16` and `configs/population.yaml:19`'s `spec_version: eval-spec-v1-draft` fields are separate, independently-stale YAML data never read by any Python code (confirmed by the grep above — no `load` of those keys exists anywhere) and are locked files this audit does not touch.

### What value would a new run currently write to `manifest.json`?

**`"eval-spec-v1.8"`**, unconditionally — both call sites pass the same module-level constant with no override parameter. A holdout run executed today, unmodified, would produce a `manifest.json` for every arm reading `"spec_version": "eval-spec-v1.8"`, not `"eval-spec-v1.10"` (the tag) and not `"code-freeze-holdout"`/`4d45db4` (the commit actually in effect) — confirming the CONFLICT already flagged during Step 0.

### Why it is currently v1.8 — repository's own explanation

`src/rrx/eval/runner.py:42-57` (comment directly above the constant, quoted in full because it is the exact, first-hand evidence of intent):

> "The currently-governing eval-spec version at the time a NEW run executes via this module (main(), or rrx.eval.arms.run_official_arm(), which reads this same constant). Distinct from, and more precise than, configs/model_params.yaml's stale spec_version: eval-spec-v1-draft field, which is not updated here — not this module's file to edit.
>
> Bumped eval-spec-v1.6 -> eval-spec-v1.8 (Stage 7.3, stress wiring): eval-spec-v1.8 (EVAL.md §7.1, tag eval-spec-v1.8, commit 7ffb527) is HEAD's tagged state as of any run launched now, including the new §7.1 item E executor-mapping invariant this same HEAD enforces. The ALREADY-WRITTEN results/a3d-dev-20260828-01/manifest.json correctly still says 'eval-spec-v1.5' — that run executed under, and reports, the spec version that actually governed it at the time (main() must never be called again per the standing 'do not rerun A3-D' rule, so this constant's only live consumers going forward are the comparator-arm path and the stress path, both of which execute now, under v1.8)."

This is definitive, first-party evidence: the constant was **manually bumped once**, at Stage 7.3, specifically because the author's own stated intent is that it track "HEAD's tagged state as of any run launched now." Three more tags have been cut since that bump (`eval-spec-v1.9` → `fbe09c6`, `eval-spec-v1.10` → `125eae8`, plus the untagged `code-freeze-holdout` → `4d45db4`), and the constant was not bumped again for any of them. The code's own documented intent, unmet by its current value, is itself the evidence that this is a drift/oversight, not a deliberate freeze of "v1.8" as the intended reporting label.

### Minimal safe fix (not implemented)

Change `src/rrx/eval/runner.py:58` from `SPEC_VERSION = "eval-spec-v1.8"` to the value corresponding to the actual frozen contract in force for the holdout run — a one-line, one-file change, since both consumers already read this single constant with no other call site to update. **This requires a prior decision this audit does not make**: which label is correct is exactly the open question from the v1.10/v1.11 investigation (`docs/DAY8-FREEZE-CONFLICT.md`) — `"eval-spec-v1.10"` (matching the `code-freeze-holdout` tag's own annotation) or some other value, depending on how that ambiguity is resolved. The fix is mechanically trivial; the *value* to put there is not this audit's call.

**Not implemented in this pass**, per instruction.

---

## Issue 3 — Holdout run log / retry policy

### STATUS: **NOT SPECIFIED**

### `results/holdout_runs.md` existence

```
$ test -f results/holdout_runs.md && echo EXISTS || echo MISSING
MISSING
```
Confirmed absent at `4d45db4`. No `results/holdout/` directory exists either. No `scripts/` directory and no `run_holdout.py` (or similarly named entry point) exists anywhere in the repository — the plan's §C3 "dedicated entry-point script" has not been built yet.

### What is specified

`EVAL.md:227-235` (§3.5):
> "| `holdout` | 2,000 | 9,000–10,999 | **Once** per candidate release |
> ...
> All `[DESIGN]`. Every holdout run — including unsuccessful ones — is logged in `results/holdout_runs.md`."

This specifies: the split size/seeds, that holdout runs once per candidate release, and that every run (successful or not) must be logged in a named file. It does **not** specify the unit of "a run," what happens on partial failure, or whether a second attempt is ever permitted.

`src/rrx/harness/splits.py:36-39,50-62` specifies the **authorization guard** (covered fully in the prior Step 0 extraction): `holdout_indices(authorized=True)` required, raises `HoldoutNotAuthorizedError` otherwise, docstring reiterating "every run - successful or not - must be logged." This is an access-control specification, not a retry/resume specification — it says nothing about what a caller may do after a failed attempt.

`src/rrx/agent/openai_client.py:82-89,232-241` specifies transport-level (single-API-call) retry behavior for the A3-LLM planner: `OpenAI(timeout=60.0, max_retries=0)` — the SDK's own internal retries are explicitly disabled ("`max_retries=0` disables the SDK's internal retries entirely... makes the 'one call, one attempt' claim true end to end," `openai_client.py:87-89`). This is real, frozen, in-repository retry semantics — but it governs one LLM HTTP call, not a run-level crash/resume policy, and **A3-LLM is excluded from `holdout` entirely** (per the Step 0 finding, `EVAL.md:888-893`), so this setting has no bearing on any arm that will actually run on holdout (A0, A1, A2-strengthened, A3-D, A4 — none of which call an LLM).

### What is NOT SPECIFIED

Full-text search confirms these return **zero results** anywhere in `EVAL.md`, `CHANGELOG.md`, `docs/A3-DESIGN.md`, or any file under `src/rrx/harness/` or `src/rrx/eval/`:

```
$ grep -in "resume\|crash" EVAL.md CHANGELOG.md docs/A3-DESIGN.md
(no output)
$ grep -rin "resume\|crash" src/rrx/harness/ src/rrx/eval/
(no output)
```

(`retry` appears throughout `EVAL.md`/`SIM.md`/`src/rrx/harness/runner.py`, but exclusively in the sense of Razorpay's own T+1/T+2/T+3 auto-charge retry engine — a simulated *payment* mechanic, unrelated to run-level retry/crash-resume for the evaluation harness itself.)

Specifically absent:
- A definition of "one run" for `results/holdout_runs.md` purposes (per-arm vs. per-session).
- Any statement of whether a crashed/partial holdout attempt may be re-executed, for any arm (deterministic or otherwise).
- Any distinction between "deterministic arm replay is safe because it's the same computation" vs. "any repeat is a new draw" — this reasoning appears only in `docs/DAY8-HOLDOUT-PLAN.md §G` (the plan author's own proposed policy, explicitly offered as an unadopted recommendation — "I am not resolving it for you" — not repository content).
- Any attempt-count cap, or format/schema for `results/holdout_runs.md` itself (no template, header, or example row exists anywhere, since the file doesn't exist).

### Conclusion for Issue 3

This is a genuine specification gap, not an implementation gap — there is no code to point to that is "wrong," because no code or spec text addresses this at all. Per instruction, no policy is invented and `results/holdout_runs.md` is not created here.

---

## Summary

| Issue | Status | Root file/line | Fix scope (not yet done) |
|---|---|---|---|
| 1. Per-episode persistence | **BLOCKER** | `src/rrx/eval/arms.py:244-379`, `src/rrx/eval/runner.py:453-522` (discard `results` after aggregation) | Add one write step per writer function, serializing already-in-memory `list[EpisodeResult]` to a per-episode JSONL keyed by index. No simulator/policy/gate change needed. |
| 2. Spec version provenance | **BLOCKER** | `src/rrx/eval/runner.py:58` (`SPEC_VERSION = "eval-spec-v1.8"`) | One-line constant update, once the v1.10/v1.11 label question is settled. Both consumers (`runner.py:500`, `arms.py:346`) already read this single source. |
| 3. Holdout run log / retry policy | **NOT SPECIFIED** | `results/holdout_runs.md` (absent); `EVAL.md:227-235` (silent on retry/resume/"one run") | Requires a human ruling before authorization, then a new file — not an existing-code fix. |

No file was modified to produce this report beyond creating `docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md` itself.
