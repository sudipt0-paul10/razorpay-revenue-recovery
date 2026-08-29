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

## Entries

*(No entries yet. No holdout attempt — successful, crashed, or otherwise — has occurred as of this update.)*
