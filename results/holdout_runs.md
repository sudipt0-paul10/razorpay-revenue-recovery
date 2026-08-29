# Holdout run log

Required by `EVAL.md §3.5`: *"Every holdout run — including unsuccessful ones — is logged in `results/holdout_runs.md`."*

This file was created empty, before any `holdout` access, as part of the Day 8 pre-holdout provenance blocker audit (`docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md`, Issue 3) — its absence was itself one of the confirmed blockers. It is now updated, still before any `holdout` access, to close the retry-policy / "one run" gap that same audit identified, per the Day 8 pre-authorization decision recorded below. No arm command, no run entry, and no authorization declaration appear yet — those remain a separate, later step (`docs/DAY8-HOLDOUT-PLAN.md §C`).

**Holdout has not been accessed as of this update.** `rrx.harness.splits.holdout_indices(authorized=True)` has never been called anywhere in this repository's history (confirmed by `git grep -n "authorized=True"` returning no production call site).

**Implementation state this policy governs:** commit `9de817e7983c9f75842d96628ed712e929473ef1` — the frozen `code-freeze-holdout` implementation (`4d45db461943978637673a5611a429e0fe826065`) plus the verified Day 8 provenance fixes (per-episode persistence, `spec_version` correction) committed on top of it. The evaluation contract itself remains `eval-spec-v1.10`; this implementation SHA changes only how faithfully a run reports and persists its own results, not what is measured, compared, or gated. Recorded here, once, so this log's own commands (once filled in) are legible against a fixed reference — not repeated as a caveat on every future entry.

---

## Definition: "one run"

**One holdout run means one complete execution of one declared arm for the candidate release.** Concretely:

- The unit this log tracks is `(arm, attempt)` — not "the holdout session" as a whole. Five arms are declared for holdout (`EVAL.md §7.1` item A): A0, A1, A2-strengthened, A3-D, A4. Each gets its own line item(s) below, independently.
- "Complete" means the arm's full declared index range (`holdout`, N=2,000, seeds 9,000–10,999) finished — every episode processed, all artifacts for that run (`manifest.json`, `episode_results.jsonl`, `metrics.json`, `run_params.json`, and `ledger.jsonl` for A3-D) written to that run's own directory.
- A run that does not reach "complete" is a **failed attempt**, not a partial success — see the retry policy below for what happens next.

## Retry / crash-resume policy `[PRE-REGISTERED — Day 8, before any holdout attempt]`

This closes the gap `docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md` (Issue 3) and `docs/DAY8-HOLDOUT-PLAN.md` (§G, §A.2 item 1) identified as genuinely unspecified in the frozen contract. It is written now, blind — no holdout attempt of any kind has occurred, and no result of any kind exists to have shaped this rule.

1. **Deterministic holdout arms — A0, A1, A2-strengthened, A3-D, A4 — may be replayed from scratch after a genuine execution crash.** ("Genuine execution crash" means the process terminated abnormally or failed to complete — an environment/infrastructure failure, not a disagreeable result.) Because these arms are frozen code over frozen config with frozen seeds and no network access, a replay from identical inputs is the same computation completed, not a second independent sample.
2. **Maximum 2 attempts per arm.** If an arm fails twice, **stop and report the failure — do not improvise a third attempt.**
3. **A replay must use identical code, config, seed, split, and parameters, and the identical arm definition** as the failed attempt. No change of any kind to code, config, seeds, prompts, model parameters, arm logic, or gate rules is permitted between attempts. If a crash's fix would require a code change, that ends the holdout for that arm; the code change is recorded as a post-holdout defect, not used to enable a rerun.
4. **No episode may be selectively rerun.** A replay re-executes the arm's entire declared index range from scratch — never a subset chosen after seeing which episodes succeeded or failed.
5. **No rerun of any kind may be triggered by an observed result, metric, or outcome.** The only trigger for a second attempt is a crash (the process did not complete). A completed run that produced an unwelcome number is not eligible for a second attempt under this policy — that is the single-use holdout rule (`EVAL.md §3.5`) operating exactly as intended.
6. **Every attempt is logged below, including failed ones**, with: arm, attempt number, start timestamp, outcome (complete / crashed), and — if crashed — the failure reason. A clean log with one entry per arm is not more credible than an honest log recording a crash and its permitted replay; an *unlogged* attempt is the only thing this policy treats as a violation in itself.
7. This policy applies **only** to genuine crashes of the five deterministic arms above. It does not create, and must not be read as creating, any allowance for A3-LLM (excluded from `holdout` entirely, `EVAL.md §7.1` item A) or for any form of result-conditioned re-execution.

**Still explicitly not decided here** (out of scope for this policy, tracked separately): the exact command line for each arm, the run-id naming convention, and the audit-sample selection rule (`docs/DAY8-HOLDOUT-PLAN.md §C1`, §E.4) — those belong to the authorization pre-declaration, not this log's structural definition.

---

## FINAL AUTHORIZATION DECLARATION

**Status: AUTHORIZED. This is the §C1 pre-declaration `docs/DAY8-HOLDOUT-PLAN.md §C` requires before any holdout execution.**

### 1. Authorization timestamp

`2026-08-30T02:52:14+05:30`

### 2. Implementation SHA

`443bb12e9024c916dc21f8e0e690ba76624a4fff`

(Ancestry: `code-freeze-holdout` = `4d45db461943978637673a5611a429e0fe826065`, plus the Day 8 provenance/infrastructure commits on top of it — `9de817e` provenance fixes, `ac82edd` retry-policy documentation, `86930b2` evidentiary files, `443bb12` guarded runner + analysis infrastructure. All four are documentation/tooling additions verified in prior Day 8 sessions to not alter evaluation methodology, metrics, criteria, or simulator/agent behavior.)

### 3. Evaluation contract

`eval-spec-v1.10` — tag resolves to commit `125eae8841562f6d5eccab58e055400340e71af6`.

### 4. Holdout arms — exactly these five

- A0
- A1
- A2-strengthened
- A3-D
- A4

Per `EVAL.md §7.1` item A: *"The single `holdout` run authorized under §3.5 evaluates exactly five arms: A0, A1, A2-strengthened, A3-D, A4."* (`EVAL.md:885-886`)

### 5. Explicit exclusions

- **A3-LLM** — excluded from `holdout` entirely, for a declared budget reason (`EVAL.md §7.1` item A, `EVAL.md:888-893`), not a performance reason. Where `EVAL.md §7`'s criteria say "A3," they are evaluated on holdout against A3-D only.
- **A1-U** — diagnostic/scratch arm, explicitly excluded from the comparator and from the holdout arm set (`EVAL.md:774`, `EVAL.md:885-886`). Also has no implementation anywhere in this repository.
- **A2-original** — retained for transparency on `dev`, not part of the five-arm holdout set.
- **A2-corrected-v1** — same as A2-original: a `dev`-only transparency variant, not part of the five-arm holdout set.

### 6. Holdout parameters

- Split: `holdout`
- N: `2000`
- Seed range: `9000–10999`
- Master seed: `20260825`

(`src/rrx/harness/splits.py:25-28`; `EVAL.md:232`.)

### 7. Exact execution command

```
python scripts/run_holdout.py --i-have-authorized-the-holdout
```

One single invocation runs all five arms sequentially (A0 → A1 → A2-strengthened → A3-D → A4); there is no separate per-arm command. **This command has not been executed as of this declaration.**

### 8. One-run definition

Exactly as committed above (commit `ac82edd`, "Definition: 'one run'" section of this file): one holdout run means one complete execution of one declared arm for the candidate release, tracked per `(arm, attempt)`; "complete" means the arm's full 2,000-episode range finished with every artifact (`manifest.json`, `episode_results.jsonl`, `metrics.json`, `run_params.json`, and `ledger.jsonl` for A3-D) written. Not restated in full here to avoid two documents drifting apart — the section above is authoritative.

### 9. Retry / crash-resume policy

Exactly as committed above (commit `ac82edd`, "Retry / crash-resume policy" section of this file) — restated in summary, not amended:

- Deterministic holdout arms only (A0, A1, A2-strengthened, A3-D, A4) may be replayed, and only after a **genuine execution crash** — never a disagreeable result.
- **Maximum 2 attempts per arm.** A second failure means stop and report; no third attempt.
- A replay must use **identical** code, config, seed, split, parameters, and arm definition. A crash requiring a code fix ends the holdout for that arm; the fix is a post-holdout defect record, not a rerun ticket.
- No selective episode reruns. No rerun of any kind triggered by an observed result, metric, or outcome.
- Every attempt — successful or crashed — is logged in this file.
- The A3-LLM-specific carve-out in that policy's item 7 remains present but is **moot for this authorization**, since A3-LLM is excluded from holdout entirely (§5 above).

The section above (lines 21-33 of this file) is authoritative; this is a summary pointer to it, not a second copy that could drift.

### 10. Audit sample rule

Exactly as established in `docs/DAY8-AUDIT-SAMPLE-RULING.md` (committed `443bb12`): applies only to A3-D's `ledger.jsonl` (the one gitignored, per-tick artifact among the five arms); the sample is the 20 episode indices `range(9000, 11000, 100)` = `{9000, 9100, ..., 10900}`, with **every** ledger record present for each — not a fixed count — and a legitimate zero-record episode (`subscription_cancelled_by_customer`) disclosed as-is, never silently dropped or replaced by a substitute index. This rule is **not** rewritten here into an outcome-dependent one; `docs/DAY8-AUDIT-SAMPLE-RULING.md` is authoritative and is not modified by this declaration.

### 11. Holdout access statement

**Holdout has not been accessed prior to this authorization.** `rrx.harness.splits.holdout_indices(authorized=True)` has never been called anywhere in this repository's history as of this declaration (confirmed by `git grep -n "authorized=True"` returning no production call site, re-verified immediately before writing this entry).

### 12. Freeze statement

**The five-arm set, the holdout parameters (split/N/seed-range/master-seed), the retry/crash-resume policy, the one-run definition, the audit-sample rule, and the execution command declared above are frozen as of this authorization and may not be changed afterward based on any observed result.** Per the standing project rule (`EVAL.md:7`): "Any change after the tag is a new tagged version with a changelog entry." A discovered validity defect may still be recorded and acted upon (per `EVAL.md:1133`, the same standard governing `EVAL.md` itself), but no element of this declaration may be altered merely because a holdout number, once observed, is unwelcome.

### 13. Preflight and verification references

- §B preflight (`docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md`): B1 (repository state; two items flagged — untracked-file cleanliness, since resolved by commits `86930b2`/`443bb12`, and the pre-existing `v1.10`/`v1.11` documentation conflict, `docs/DAY8-FREEZE-CONFLICT.md`, which remains open but is documentation-only and does not alter methodology), B2 PASS (`2240 passed, 1 failed` — the 1 failure reproduces `tests/test_stage5_falsification.py::test_1_policy_ordering`'s pre-existing, byte-identical numbers), B3 PASS (environment/config hashes recorded), B4 PASS (manifest writing, per-episode persistence, ledger completeness, `results/holdout_runs.md` existence all confirmed), B5 PASS (300-episode stress rehearsal, all five arms, zero safety-invariant violations, artifacts correct and isolated).
- Provenance fixes: commit `9de817e` (per-episode persistence + `spec_version` correction to `eval-spec-v1.10`), verified by 59 focused tests plus the B5 rehearsal.
- Guarded runner + analysis infrastructure: commit `443bb12` (`scripts/run_holdout.py`, `src/rrx/eval/holdout_analysis.py`), verified by 37 focused tests, ruff clean.
- No holdout result, metric, or observed number appears anywhere in this declaration or in any commit referenced above.

---

## RE-AUTHORIZATION — CORRECTED IMPLEMENTATION SHA

**Status: RE-AUTHORIZED. This section supersedes only the "Implementation SHA" and execution-readiness aspects of the FINAL AUTHORIZATION DECLARATION above. Every other frozen element of that declaration — arm set, exclusions, holdout parameters, one-run definition, retry/crash-resume policy, audit sample rule — is carried forward unchanged and is not restated in full here to avoid two documents drifting apart.**

### Re-authorization timestamp

`2026-08-30T03:18:06+05:30`

### Reference to the original authorization

This re-authorization references, and does not replace, the **FINAL AUTHORIZATION DECLARATION** above, originally committed at `53bd1223691f0c1c09cce7bb754f123c3f38f38b` ("Authorize Day 8 holdout evaluation") and anchored by the annotated tag `holdout-authorized-20260830`. **That commit and that tag are unchanged, unmoved, and not recreated by this update.** This section exists because the implementation SHA that declaration named — `53bd122` itself — could not actually be executed against, for the reason recorded below.

### Refused execution attempt

The first authorized invocation of `python scripts/run_holdout.py --i-have-authorized-the-holdout`, run against the authorized state (`HEAD = 53bd122`), was **refused by the script's own precondition guard** before reaching any holdout-related code:

```
HEAD is 53bd1223691f0c1c09cce7bb754f123c3f38f38b,
expected the authorized implementation 86930b2bdd87f997f0dab2fe6df6a17ba8b69cb7.
```

This was a bug in `scripts/run_holdout.py` itself: its `IMPLEMENTATION_SHA` constant had been pinned to `86930b2` (HEAD at the time the script was written) and was never updated when the subsequent authorization-declaration commit (`53bd122`) became the actual authorized state. The guard performed correctly — refusing to proceed under a HEAD it did not recognize — and no code path past that check was reached.

**Confirmed: no holdout indices were accessed, `holdout_indices(authorized=True)` was never called, and no holdout data of any kind was read, written, or inspected during this refused attempt.** The refusal occurred at the earliest precondition check, before the script's own index-access line.

Per the retry/crash-resume policy above (item 6): *"Every attempt is logged below, including failed ones."* This was not a simulation crash within a running arm (no arm ever started), but it is logged here in the same spirit — as the honest record of what was attempted and why it did not proceed — rather than left undocumented. It does not count against the policy's "maximum 2 attempts per arm" (item 2), since no arm's execution began; that budget remains fully available.

### Corrective action taken

- `scripts/run_holdout.py`'s `IMPLEMENTATION_SHA` corrected from `86930b2bdd87f997f0dab2fe6df6a17ba8b69cb7` to `53bd1223691f0c1c09cce7bb754f123c3f38f38b`, committed as `659b515` ("Fix holdout authorization SHA guard"), together with a focused regression test (`tests/test_run_holdout_script.py::test_rejects_old_authorized_implementation_sha_and_accepts_current_one`) proving both that the old SHA is still rejected and that the corrected pin is accepted.
- Diff `53bd122..659b515` inspected and confirmed to touch **only** `scripts/run_holdout.py` and `tests/test_run_holdout_script.py` — no change to `EVAL.md`, `SIM.md`, any `configs/*.yaml`, `data/`, `src/rrx/harness/splits.py`, `src/rrx/sim/`, this file, or `docs/DAY8-AUDIT-SAMPLE-RULING.md`. `CODE_FREEZE_HOLDOUT_SHA`, `EVAL_SPEC_V1_10_SHA`, `HOLDOUT_ARMS`, `HOLDOUT_SPLIT`, and the `MASTER_SEED` import are all unchanged (present in the diff only as unmodified context, never as an added/removed line). The correction is exactly and only the execution-guard's implementation-SHA pin plus its test.
- 13 focused tests pass (`tests/test_run_holdout_script.py`); ruff clean.

### Corrected executable implementation

**`659b515fe3a2c99e2a3d47ed66700af10d9fea9e` is now the implementation this authorization executes against.** `scripts/run_holdout.py`'s own `IMPLEMENTATION_SHA` constant is the single source of truth for this check going forward — this section records that it was deliberately corrected, not silently.

### What is NOT changed by this re-authorization

The arm set (A0, A1, A2-strengthened, A3-D, A4), the exclusions (A3-LLM, A1-U, A2-original, A2-corrected-v1), the holdout parameters (split=`holdout`, N=`2000`, seed range `9000–10999`, master seed `20260825`), the one-run definition, the retry/crash-resume policy, and the audit sample rule (`docs/DAY8-AUDIT-SAMPLE-RULING.md`) are **all unchanged** from the original declaration. This re-authorization corrects *which commit may execute*, not *what is measured, compared, gated, or logged*.

### Re-authorization statement

**Execution is re-authorized against implementation `659b515`, under the evaluation contract `eval-spec-v1.10` (`125eae8841562f6d5eccab58e055400340e71af6`), on the exact terms already frozen in the FINAL AUTHORIZATION DECLARATION above.** No holdout index has been accessed prior to this re-authorization. The execution command remains:

```
python scripts/run_holdout.py --i-have-authorized-the-holdout
```

---

## Entries

- `2026-08-30T03:18:06+05:30` | arm=(none — precondition check, no arm reached) | attempt=1 | status=REFUSED | reason=implementation SHA guard mismatch (HEAD 53bd122 vs pinned 86930b2, since corrected in commit 659b515) | holdout data accessed: no
