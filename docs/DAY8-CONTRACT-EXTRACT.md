# DAY 8 — STEP 0: CONTRACT EXTRACTION

**Method:** Read-only inspection at commit `4d45db461943978637673a5611a429e0fe826065`. No file modified, no test executed, no holdout index accessed, no preflight step run, no authorization performed. Checklist is `docs/DAY8-HOLDOUT-PLAN.md` §A.1 (12 questions) and §A.2 (6 unresolved items), reproduced and answered below in order.

**Rule followed throughout:** quote, don't paraphrase; where the repository is silent, write `NOT SPECIFIED`; where two committed sources disagree, write `CONFLICT` and do not resolve it.

---

## 0. Repository/tag verification

```
$ git rev-parse HEAD
4d45db461943978637673a5611a429e0fe826065

$ git rev-parse code-freeze-holdout^{commit}
4d45db461943978637673a5611a429e0fe826065

$ git rev-parse eval-spec-v1.10^{commit}
125eae8841562f6d5eccab58e055400340e71af6

$ git status --porcelain
?? docs/handoff/
?? docs/DAY8-CONTRACT-EXTRACT.md   (this file, being created)
?? docs/DAY8-HOLDOUT-PLAN.md
?? gpt_probe.py
```

`HEAD` and `code-freeze-holdout` (an annotated tag) resolve to the same commit, matching the plan's premise. **`eval-spec-v1.10` is a distinct, earlier commit** (`125eae8`) — `code-freeze-holdout`/`HEAD` (`4d45db4`) is one commit *after* the `eval-spec-v1.10` tag. This is load-bearing for §12 and the CONFLICT recorded there: "the frozen v1.10 contract" and "the code-freeze-holdout commit" are not byte-identical.

```
$ git show 4d45db4 --stat
 CLAUDE.md                                          | 177 ++++++++
 EVAL.md                                            |  10 +
 LIMITATIONS.md                                     | 462 +++++++++++++++++++++
 docs/A3-DESIGN.md                                  |   9 +
 results/a0-dev-20260828-01/manifest.json           |  13 +
 ... (results/ artifacts for a0/a1/a2s/a3d dev runs, capture/, sensitivity.md, stress-*, tuning_log.md, etc.)
```

`CHANGELOG.md` is **not** in this commit's diff — `4d45db4` changes `EVAL.md` and `docs/A3-DESIGN.md` without a corresponding `CHANGELOG.md` entry. Full consequence under §12.

Working tree was already at this commit; no checkout was necessary.

---

## A.1 — The twelve contract questions

### Q1. Which arms must run on holdout?

**SPECIFIED — exactly five, named explicitly.**

> "The single `holdout` run authorized under §3.5 evaluates exactly five arms: **A0, A1, A2-strengthened, A3-D, A4.**"
— `EVAL.md:885-886` (§7.1 item A, `[AMENDMENT, eval-spec-v1.8]`)

This supersedes the plan's §A.1 #1 "best-evidence" guess (which correctly named the same five but flagged it MEDIUM confidence pending v1.10 confirmation, and separately wondered whether A3-LLM belonged in the list). It is committed text, unchanged through v1.9 and v1.10 (neither CHANGELOG entry touches §7.1 item A). A3-LLM is explicitly **not** one of the five — see Q2.

### Q2. Is A3-LLM included, excluded, or separate?

**SPECIFIED — excluded from `holdout`, for a declared budget reason, not a performance reason.**

> "**A3-LLM is excluded from `holdout` for one reason: the paid-API budget required to run a live planner across 2,000 `holdout` episodes is not available.** No replayable cache exists for `holdout` seeds 9000–10999; the §6A cache covers `dev` seeds 1000–1499 only. This exclusion is declared before any `holdout` access and is not, and may not later be represented as, a decision informed by A3-LLM's measured performance."
— `EVAL.md:888-893`

> "Where §7's criteria say 'A3,' they are evaluated on `holdout` against **A3-D**. A3-D is the arm subject to criteria 1–4."
— `EVAL.md:897-898`

> "A3-LLM's Day-6 result — configuration GPT-C2 (`reasoning_effort=minimal`, `disclosure=high`, `verbosity=low`), selected mechanically under §6A's pre-registered selection rule at N=500 on `dev` seeds 1000–1499 — is a **development-only secondary result**. It is not scored against §7."
— `EVAL.md:899-902`

Cross-checked against `results/tuning_log.md:464-484` (Entry 4): GPT-C2 was selected on N=500 (dev seeds 1000–1499), and the prescribed N=2,000 full-dev confirmation run "has **NOT** been executed... a deliberate decision to stop further live API spending... not an oversight." This matches `EVAL.md §7.1` item B.1 verbatim.

**This fully resolves the plan's "single largest open item" (its own K1/#2).** Not LOW confidence — it is committed, unambiguous text, unchanged from v1.8 through v1.10.

### Q3. Holdout size and seed range

**SPECIFIED — matches the plan exactly.**

```
HOLDOUT_SPLIT = "holdout"
HOLDOUT_SEED_START = 9000
HOLDOUT_N = 2000
_HOLDOUT_INDICES = range(HOLDOUT_SEED_START, HOLDOUT_SEED_START + HOLDOUT_N)  # 9000-10999
```
— `src/rrx/harness/splits.py:25-28`

> "| `holdout` | 2,000 | 9,000–10,999 | **Once** per candidate release |"
— `EVAL.md:232`

`MASTER_SEED: int = 20260825` — `src/rrx/sim/latent.py:40`.

### Q4. Exact metrics

**SPECIFIED.**

> "**Primary (Regime B — counted)**
> - **Invoice recovery rate** — failed invoice paid within the window
> - **Subscription rescue rate** — Subscription returns to `active` within the window
> - Contacts per invoice recovered; contacts per subscription rescued
> - **Total contacts across the cohort** — the ratio alone misleads when outcome counts differ
> - Median and p90 time-to-rescue
>
> **Secondary (Regime A — monetised)**
> - Net value = invoice ₹ recovered + preserved LTV − contact costs − LLM cost − expected cancellation cost
> - Cancellations attributable to contact volume
>
> **Broken out separately:** the `card_declined` / `payment_failed` bucket (24% of the population, where the fail-safe costs most), and the `cancelled`-at-open bucket (5%, where the correct answer is to do nothing)."
— `EVAL.md:563-574`

Matches the plan verbatim.

### Q5. Exact success criteria

**SPECIFIED, with one confirmed correction relative to the plan.**

> "1. All §5.2 invariants hold on `dev`, `holdout`, `stress`.
> 2. On `holdout` under Regime B: for EACH primary metric ... A3's rate exceeds the best-performing bounded non-agent arm's rate on that same metric, 95% CI on the difference excluding zero. Bounded non-agent arms = {A0, A1, A2 (as finally adopted, §4.1)}. A4 is excluded ... as are diagnostic/scratch arms (e.g. A1-U). ...
> 3. Total contacts (A3) ≤ total contacts (comparator arm from criterion 2, same metric), **and** contacts per rescue (A3) ≤ that same comparator arm's. ...
> 4. Uplift attributable to the §3.4 structures, with unexplained residual reported.
> 5. Graceful handling of three injected failure modes — API timeout, malformed/hallucinated LLM action, subscription state changing mid-episode — run continuing, failure visible in the ledger."
— `EVAL.md:773-777`

Target: "A3 captures ≥40% of the A4 minus best-bounded-arm gap on both primary metrics on `holdout`." — `EVAL.md:783`.

Confirmed by `EVAL.md §7.1` item A (`EVAL.md:897-898`, quoted under Q2): criteria 1–4 are evaluated against **A3-D**, since A3-LLM is excluded. Criterion 5 is addressed separately — see §A.2 item 2 below.

The plan rated this MEDIUM-HIGH pending v1.10 confirmation of the tie-set text; that text is confirmed committed — see Q6.

### Q6. Comparator / tie-set rule

**SPECIFIED — committed verbatim, unchanged since `eval-spec-v1.7`, through v1.8/v1.9/v1.10.**

> "1. On EACH primary metric independently, the bounded-arm comparator determination is made using HOLDOUT data, never DEV results.
> 2. Identify the bounded arm with the highest HOLDOUT point estimate for that metric.
> 3. The comparator set for that metric consists of: that highest-point-estimate bounded arm, plus every other bounded arm whose pairwise 95% CI against it (on holdout) includes zero.
> 4. A3 satisfies criterion 2 on that metric only if A3's holdout rate exceeds EVERY member of that comparator set, with the 95% CI on each corresponding A3-minus-comparator-arm difference excluding zero.
> 5. If the comparator set contains more than one arm, that tie is reported explicitly ...
> 6. Criterion 3 inherits the comparator set defined under criterion 2 for that metric. A3 must therefore satisfy both contact constraints ... against EVERY member of the comparator set ...
> 7. If the comparator set contains exactly one arm, this rule reduces exactly to the pre-existing §7 criteria 2/3 ..."
— `EVAL.md:821-841`

This is precisely the rule the plan's §F.2/§K2 flagged as needing verification ("Working notes record this as the pre-registration ruling; it *must* be confirmed as committed text"). **It is confirmed, word-for-word, at `EVAL.md:821-841`.** Plan's §K2 is resolved: SPECIFIED, not "genuinely unspecified."

### Q7. Safety / gate invariants

**SPECIFIED.**

Gate table: `EVAL.md:591-606` (eight rows, R1–R8 minus a genuine R7 gap — see below). Enforcement notes: `EVAL.md:608-627`.

> "A non-zero value on any row is a P0 bug with a written post-mortem, not a score to improve."
— `EVAL.md:606`

`src/rrx/agent/gate.py:1-2`:
> "The safety gate (docs/A3-DESIGN.md §8) - R1-R8, in the frozen precedence order R2, R4 -> R3 -> R1, R8 -> R5, R6."

Confirmed by reading the function (`gate.py:75-106`): the implemented branches are R2, R4, R3, R1, R8, R5, R6 — **seven rules, no R6a/R7 branch exists in code.** `docs/A3-DESIGN.md:296-305`'s table maps gate row 7 ("No audit record: 0") to "Runner invariant — one ledger record per tick, structurally guaranteed" — i.e., row 7 is a **structural invariant, not a numbered gate rule** (matches the plan's own hypothesis exactly: "there is no R7; row 7 ... is a structural runner invariant").

Precedence confirmed identical in both `EVAL.md` and `docs/A3-DESIGN.md:307`: `R2, R4 → R3 → R1, R8 → R5, R6`.

R5/R6 enforcement-by-construction and R2's practical unreachability are confirmed verbatim at `docs/A3-DESIGN.md:298-305`.

### Q8. Artifact / provenance requirements

**SPECIFIED for the eleven-field manifest schema; PARTIALLY CONFLICT / gap on wiring and on per-episode persistence.**

> "Every run writes `results/<run_id>/manifest.json`: git SHA, spec version, config hash, seed, arm, regime, sweep cell, model version, timestamp, wall-clock, LLM cost."
— `EVAL.md:708`

Eleven-field dataclass confirmed at `src/rrx/spec/manifest.py:29-44` (`RunManifest`).

**Wiring — resolved in the agent's favor relative to the plan's Day-5-era doubt.** `write_manifest(...)` is actually invoked at two call sites: `src/rrx/eval/arms.py:362` and `src/rrx/eval/runner.py:511`. This is no longer "defined but never invoked" — it is wired as of `4d45db4`.

**CONFLICT — `spec_version` field does not say "eval-spec-v1.10."**

```
SPEC_VERSION = "eval-spec-v1.8"
```
— `src/rrx/eval/runner.py:58`, consumed at `runner.py:500` and (via `eval_runner.SPEC_VERSION`) `arms.py:346`.

Every `manifest.json` this code path produces — including, if unmodified, any future `holdout` run — will self-report `spec_version: "eval-spec-v1.8"`, not `"eval-spec-v1.10"`. This is a live discrepancy between the manifest-writing code and the actual frozen spec version at `4d45db4`. Not resolved here.

**Separately, `configs/model_params.yaml:16` declares `spec_version: eval-spec-v1-draft`** — a third, different string, inside a locked config file. Quoted, not resolved.

**Gap — no per-episode outcome vector is written by the standard per-arm run path.** `src/rrx/eval/runner.py:490-496` writes `ledger.jsonl` (per-tick, A3 arms only) and `metrics.json` (aggregates); no `episode_results.jsonl` or equivalent per-episode file is written by this path for any arm. `results/tuning_log.md:492-494` states this gap explicitly for the A3-LLM tuning cells: "Day 6 Stage 6T found paired bootstrap analysis impossible from the stored artifacts — no per-episode outcome data was persisted for any GPT cell, only aggregate rates." A **separate**, out-of-band mechanism exists for four dev canonical runs only — `results/capture/{a0,a1,a2s,a3d}-dev-20260828-01/episodes.jsonl` — but there is no `capture/` directory for A4, and no such mechanism is invoked by the standard run path at all. The plan's E.1 table assumes `episode_results.jsonl` is a per-arm artifact the harness produces; **as of `4d45db4` it is not**, except via the separate, manually-invoked capture mechanism.

`docs/A3-DESIGN.md §22` (artifact policy) confirmed at `docs/A3-DESIGN.md:953-972`; `.gitignore` confirmed to gitignore exactly `results/**/ledger.jsonl` and `results/**/llm_cache*.jsonl`, consistent with that section.

### Q9. Authorization mechanism

**SPECIFIED for the code guard; CONFIRMED MISSING for the required log.**

```python
def holdout_indices(*, authorized: bool = False) -> range:
    if not authorized:
        raise HoldoutNotAuthorizedError(...)
    return _HOLDOUT_INDICES
```
— `src/rrx/harness/splits.py:50-62`. `_HOLDOUT_INDICES` is module-private (line 28); no other module-level export exposes the holdout range.

```
$ grep -rn "authorized=True" .
```
returns exactly one production hit outside tests/docs: `EVAL.md:302` (prose, not code) and `results/tuning_log.md:155` (prose, log entry stating it was never called). No source file passes `authorized=True`. `tests/test_holdout_guard_intact.py:18-25` exercises only the *refusal* path (`authorized=False` / omitted), per its own docstring ("deliberately never calls `holdout_indices(authorized=True)`").

> "Every `holdout` run — including unsuccessful ones — is logged in `results/holdout_runs.md`."
— `EVAL.md:235`

```
$ test -f results/holdout_runs.md && echo EXISTS || echo MISSING
MISSING
```

Confirmed: this file does not exist at `4d45db4`. The plan's B4 #15 flags this as a preflight blocker ("create it... before authorization"); Step 0 confirms the condition it warns about is still true.

### Q10. Frozen randomness / seeds / model params

**SPECIFIED.**

- `MASTER_SEED: int = 20260825` — `src/rrx/sim/latent.py:40`.
- `BOOTSTRAP_SEED = 20260826` — `src/rrx/sim/run_stage3.py:31`, used as the default `seed` parameter (`run_stage3.py:51`) of the paired-bootstrap function.
- CRN / substream isolation:
  ```
  common_random_numbers:
    enabled: true
    substream_isolation: per_variable
    substreams:
      - invoice_amount
      - failure_condition
      - balance_restore
      - topup_acceleration
      - channel_response
      - card_change_completion
      - cancellation_hazard
      - remaining_lifetime
  ```
  — `configs/model_params.yaml:38-53`. Eight named substreams, matching the plan's claim exactly.
- `frozen_policies: [A2, A3-D, A3-LLM]` and `win_criterion.comparator: A2` (sweep-grid-only comparator, distinct from the §7 holdout comparator) — `configs/model_params.yaml:26-37`.
- `sweep.split: dev` — `configs/model_params.yaml:21`, comment: "HOLDOUT is never swept." Confirms the plan's claim directly.

**CONFLICT (self-referential, inside this same file):** `configs/model_params.yaml:16` reads `spec_version: eval-spec-v1-draft` — stale relative to every tagged version since `eval-spec-v1`. This is a locked file; not modified here, only quoted.

Model version pin (`gpt-5-mini`, temperature constraint) is corroborated by `EVAL.md:1039` ("`gpt-5-mini` rejects any value other than `1`") and `results/tuning_log.md` (cited under Q2); not independently re-verified against a live API call, per instruction not to touch anything live.

### Q11. What must NOT change after freeze

**SPECIFIED.**

> "**After the tag, the only reason to reopen this file is a discovered validity defect — never to improve expected A3 performance.**"
— `EVAL.md:1133`

This is the literal sentence the plan paraphrased; confirmed verbatim, exact line. `SIM.md:20` carries the same rule for the simulator: "defect — never to improve an agent's expected performance."

Note on the surrounding checklist (`EVAL.md:1119-1131`): its final line item — `- [ ] Tagged eval-spec-v1` — is **still unchecked** in the file at `4d45db4`, even though the `eval-spec-v1` git tag has existed since `0617f78` (Day 1). This checklist block is preserved historical text from the original Day-1 freeze and was never updated as later `eval-spec-v1.x` tags were cut; flagged as a stale-but-harmless artifact, not acted on.

### Q12. Sensitivity status

**SPECIFIED for cell count/pass mark; CONFLICT on version provenance (see below).**

- Registry: `enumerate_cells()` produces 26 cells under `include_topup_acceleration_cells: false` (`EVAL.md:949-951`, `configs/model_params.yaml`); pass mark `ceil(0.80 × 26) = 21/26` (`EVAL.md:959`).
- `configs/model_params.yaml:33` still carries the stale comment `# ceil(0.80 * 22) = 18` — the YAML comment was never updated to match the 26-cell correction, even though the enforcing test (`tests/test_model_params_swept.py`, per `EVAL.md:951-952`) checks the corrected number. Quoted, not fixed (locked file).
- `results/sensitivity.md` exists (`4177` bytes) and, per the note below, has been regenerated to show 26 cells with pass mark 21/26 — **all outcome columns (`clamped`, `invoice CI`, `rescue CI`, `win`) remain `PENDING` in every row.** Sweep has not been run for any arm.

**CONFLICT — an `eval-spec-v1.11`-labeled correction exists inside the "v1.10" frozen text, with no corresponding tag or CHANGELOG entry.**

`EVAL.md:963-971` (inside §7.1, which is otherwise entirely `eval-spec-v1.8` text) reads:

> "> `[CORRECTION, eval-spec-v1.11]` The sentence immediately above describes the state at `eval-spec-v1.8`'s own writing — the artifact genuinely carried the stale 22-cell structure at that time. Stage 7.4 (commit `588b6c0`) subsequently regenerated `results/sensitivity.md` from the registry. The artifact now contains 26 cells and states pass mark 21/26. All outcome columns (`clamped`, `invoice CI`, `rescue CI`, `win`) remain `PENDING` in every row — no actual sensitivity sweep has been run. This note does not alter the v1.8 sentence it follows; it records that the regeneration it anticipated has since occurred."

An identical `[CORRECTION, eval-spec-v1.11]` note also exists at `docs/A3-DESIGN.md:850-858` (added in the same commit).

Facts, established by `git log`/`git show`, not inference:

1. **Both notes were introduced in the `4d45db4` commit itself** (`git show 4d45db4 -- EVAL.md docs/A3-DESIGN.md`) — the same commit that is `code-freeze-holdout`/`HEAD`. Commit message: "Preserve pre-holdout evaluation provenance" — no mention of a v1.11 amendment.
2. **No `eval-spec-v1.11` git tag exists anywhere in the repository** (`git tag --list` tops out at `eval-spec-v1.10` → `125eae8`).
3. **`CHANGELOG.md` was not modified by `4d45db4`** (absent from its diff `--stat`) and has no `eval-spec-v1.11` section — its newest entry is titled `## eval-spec-v1.10 ...` (`CHANGELOG.md:3`).
4. The event these notes describe (`588b6c0`, "Generate sensitivity artifact from registry") **chronologically precedes** the `eval-spec-v1.10` tag commit (`125eae8`) in the commit graph — i.e., the regeneration happened *before* v1.10 was tagged, but the note describing it was written *after* v1.10 was tagged, under a version label (`v1.11`) that was never formalized.

**Consequence, stated without resolving it:** "the frozen v1.10 contract" is not a single unambiguous artifact. The `eval-spec-v1.10` **tag** (`125eae8`) does not contain these two notes. The `code-freeze-holdout` **tag**/`HEAD` (`4d45db4`) — the commit this entire Step 0 extraction is required to read — does contain them, self-labeled as a version that was never tagged and never given a `CHANGELOG.md` entry. Per this project's own rule ("Any change after the tag is a new tagged version with a changelog entry," `EVAL.md:7`), this is a process violation on its own terms. This document does not decide whether `code-freeze-holdout` or `eval-spec-v1.10` is authoritative for the sensitivity-status question, or whether the sensitivity content is in-scope or out-of-scope content for `code-freeze-holdout`'s freeze — that is a decision for the plan's revision step (§L), not for Step 0.

---

## A.2 — The six unresolved items

### 1. Retry / crash-resume policy for a once-only holdout run

**NOT SPECIFIED.** `EVAL.md §3.5` (`EVAL.md:227-304`) requires every run, successful or not, to be logged in `results/holdout_runs.md`, and states holdout runs "**Once** per candidate release" (`EVAL.md:232`), but nowhere defines whether a second attempt after a crash is permitted, nor what constitutes "a run" if it fails partway. No other section of `EVAL.md`, `SIM.md`, or `docs/A3-DESIGN.md` addresses retry/resume for `holdout`. Confirmed absent by full read of both documents. The plan's §G is the plan author's own proposed resolution (not yet adopted) — it is not repository content and is not treated as SPECIFIED here.

### 2. Which split criterion 5 (failure injection) is demonstrated on

**NOT SPECIFIED — confirmed by contrast.**

> "1. All §5.2 invariants hold on `dev`, `holdout`, `stress`."
— `EVAL.md:773` (criterion 1 names all three splits explicitly)

> "5. Graceful handling of three injected failure modes — API timeout, malformed/hallucinated LLM action, subscription state changing mid-episode — run continuing, failure visible in the ledger."
— `EVAL.md:777` (criterion 5 names no split at all)

`EVAL.md §7.1` item D (`EVAL.md:973-987`) describes *how* criterion 5 is satisfied (against a stubbed planner, no live API calls) but likewise never names a split. `docs/A3-DESIGN.md §19` (`docs/A3-DESIGN.md:868-877`) describes the three failure-mode/ledger mappings with no split reference either. The plan's "strict reading: not on holdout" is a reasonable inference from the contrast with criterion 1's explicit three-split list, but it is an inference, not committed text — recorded here as `NOT SPECIFIED`, not resolved.

### 3. Whether A2-original and A2-corrected-v1 run on holdout

**SPECIFIED — they do not.**

`EVAL.md §7.1` item A's five-arm holdout list (`EVAL.md:885-886`, quoted under Q1) is exhaustive: "**exactly five arms: A0, A1, A2-strengthened, A3-D, A4.**" Neither A2-original nor A2-corrected-v1 appears. Both remain independently runnable and documented (`EVAL.md §4.1`, `EVAL.md:326-367`) for transparency on `dev`, but the `holdout` arm set is closed at v1.8 and unmodified through v1.10. This resolves the plan's own K6 for these two variants.

### 4. Whether A1-U (diagnostic, unbounded) runs on holdout

**SPECIFIED as excluded by the same v1.8 five-arm list (Q1) — and separately confirmed to have no implementation anywhere in the repository.**

`EVAL.md:774` (criterion 2) names A1-U explicitly as excluded: "as are diagnostic/scratch arms (e.g. A1-U)." It is also absent from the five-arm holdout list under Q1/§A.2 item 3.

```
$ grep -rni "A1-U|A1_U|a1_u" .
```
returns matches only in `EVAL.md` (prose defining the arm), `docs/DAY8-HOLDOUT-PLAN.md`, and the two `docs/handoff/DAY5-CONTEXT-DUMP*.md` read-only inspection files. **No file under `src/`, `tests/`, or `configs/` implements A1-U.** It exists in this repository as a specified-but-unbuilt row in the `EVAL.md §4` arm table (`EVAL.md:318`) only.

### 5. Whether the §7 "A3" subject is A3-LLM, A3-D, or both

**SPECIFIED — resolved identically to Q2.** `EVAL.md:897-898`: "Where §7's criteria say 'A3,' they are evaluated on `holdout` against **A3-D**." A3-LLM's role is `dev`-only and explicitly non-scored (`EVAL.md:901-902`, quoted under Q2). This closes the plan's own K1 ("the plan's blocking ambiguity") as SPECIFIED, not blocking.

### 6. What constitutes "one run" for `results/holdout_runs.md`

**NOT SPECIFIED.** `EVAL.md:235` requires logging "every `holdout` run — including unsuccessful ones" but does not define the unit of "a run" (per-arm vs. per-session). No other passage in `EVAL.md`, `docs/A3-DESIGN.md`, or `src/rrx/harness/splits.py` defines this term. The file the definition would presumably live in, `results/holdout_runs.md`, does not exist (confirmed under Q9), so there is no precedent entry to infer a convention from either.

---

## Summary — what must be resolved in the plan before it can move past YELLOW

1. **§12 / the `eval-spec-v1.11` finding is new information the plan did not have and must account for.** The plan was written assuming a clean "v1.10 contract"; `code-freeze-holdout` in fact contains untagged, unlogged `v1.11`-labeled content one commit past the `eval-spec-v1.10` tag. This needs an explicit decision (not made here): is `code-freeze-holdout` the authoritative freeze point (in which case the missing tag/CHANGELOG entry for v1.11 is itself a process gap to record), or is `eval-spec-v1.10` (`125eae8`) the actual frozen spec and `4d45db4` an out-of-band addition that should not have been included under the `code-freeze-holdout` label?
2. **Q2/Q5/§A.2#5 (A3-LLM's holdout eligibility) is fully resolved by committed text — the plan's K1 is closed, not blocking.** The plan can drop K1 as an open ambiguity; `EVAL.md §7.1` item A settles it.
3. **Q6/§A.2's tie-set text (K2) is fully resolved by committed text — confirmed present verbatim at `EVAL.md:821-841`.**
4. **§A.2 items 3 and 4 (K6) are resolved — A2-original, A2-corrected-v1, and A1-U are all excluded from the five-arm holdout set** by the same v1.8 amendment.
5. **§A.2 items 1 and 6 (K3, K5) remain genuinely unspecified** — no repository text of any kind addresses retry/crash-resume or the definition of "one run." These still require the human ruling the plan's §G/§L already anticipated.
6. **§A.2 item 2 (K4) remains an inference, not a specified fact** — criterion 5 names no split; the "not on holdout" reading is reasonable but not written anywhere.
7. **New gaps not in the plan's original ambiguity list, surfaced by this extraction:**
   - `SPEC_VERSION = "eval-spec-v1.8"` hardcoded in `src/rrx/eval/runner.py:58` will mislabel every manifest produced by the current code, including a future holdout run, unless corrected before authorization.
   - No per-episode outcome file (`episode_results.jsonl` or equivalent) is written by the standard per-arm run path (`src/rrx/eval/runner.py`, `src/rrx/eval/arms.py`) for any arm — the only precedent for per-episode persistence is the separate, manually-invoked `results/capture/` mechanism, which has no A4 output and was not run against a v1.8+/v1.10 codebase. This directly affects the plan's B4 #13 and E.1 `episode_results.jsonl` expectation.
   - `configs/model_params.yaml:16`'s self-declared `spec_version: eval-spec-v1-draft` and the stale `ceil(0.80 * 22) = 18` comment at line 33 are both quoted as-is; this is a locked file and neither was touched.
   - `results/holdout_runs.md` is confirmed absent, consistent with the plan's own B4 #15 expectation.
   - `write_manifest` **is** wired into two call sites (`src/rrx/eval/arms.py:362`, `src/rrx/eval/runner.py:511`) — this resolves the plan's B4 #12 concern in the affirmative (contrary to the Day-5-era doubt the plan cites).

**Not done in this pass, per instruction:** no test suite run, no `ruff` run, no preflight item executed, no holdout index accessed or authorized, no edit to `EVAL.md`, `SIM.md`, any `configs/*.yaml`, any arm/gate/comparator/seed/prompt/model-parameter definition, or any other frozen surface. This file and `docs/DAY8-HOLDOUT-PLAN.md` are the only files touched this session.
