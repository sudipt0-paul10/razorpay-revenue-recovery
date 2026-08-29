# DAY 8 — HOLDOUT EXECUTION PLAN

**Status:** PLAN ONLY. Nothing executed. Holdout not accessed.
**Prepared against:** `code-freeze-holdout` → `4d45db461943978637673a5611a429e0fe826065`; `eval-spec-v1.10` → `125eae8841562f6d5eccab58e055400340e71af6`
**Reviewer position:** independent evaluation reviewer
**Verdict:** **YELLOW** — see §L.

---

## READ THIS FIRST — the evidence base for this plan

This plan was written from Day-5-era repository dumps (`eval-spec-v1.4`) plus working notes reaching approximately `v1.7`. **The frozen contract is `v1.10`.** Three or more amendments sit between what I can read and what is actually frozen — including, per working notes, the §7 criterion-2 defect amendment and the comparator tie-set pre-registration, both of which are *load-bearing for the holdout comparison itself*.

Therefore:

- Every contract statement in §A carries an explicit **confidence tag** and a **verification instruction**.
- §A is not the contract. §A is a *hypothesis about the contract* that Step 0 must confirm or correct.
- **If Step 0 returns any answer that contradicts §A, this plan is void and must be revised before execution.** Do not reconcile silently. Do not proceed on "close enough."

A plan that assumes the spec is a plan that contaminates the holdout by acting on the wrong criterion. The extraction pass is not bureaucracy; it is the only thing standing between a stale reading and an unrepeatable run.

---

## A. FROZEN CONTRACT

### A.0 — Step 0 is mandatory and blocking

Before any preflight, Claude Code performs a **read-only contract extraction** at `4d45db4`, answering the twelve questions below by quoting `EVAL.md` / `SIM.md` / `docs/A3-DESIGN.md` / `configs/*.yaml` / `CHANGELOG.md` **verbatim with file and line numbers**. No code is written. No holdout is touched. Output is a single file, `docs/DAY8-CONTRACT-EXTRACT.md`, committed on a branch, reviewed by you before §B begins.

Extraction rules:
- Quote, don't paraphrase. Line-numbered.
- Where the spec is silent, write `NOT SPECIFIED` — never fill the gap.
- Where two documents conflict, quote both and write `CONFLICT`, do not resolve.
- Read the `CHANGELOG.md` entries for v1.5 → v1.10 in full; these carry the amendments this plan cannot see.

### A.1 — Contract questions, best-evidence answers, and what must be verified

| # | Question | Best-evidence answer (confidence) | Verify by |
|---|---|---|---|
| 1 | Which arms must run on holdout? | Criterion 2 needs `{A0, A1, A2-as-adopted}` (bounded set) and criterion 2's *target* needs `A4` (gap = A4 − best bounded). Plus the A3 arm(s). **Minimum: A0, A1, A2-strengthened, A4, A3-D.** (HIGH on the set logic; MEDIUM on whether v1.10 renamed/re-scoped it) | `EVAL.md §4`, §4.1, §4.2, §7 criteria 2–3 |
| 2 | Is A3-LLM included, excluded, or separate? | **UNRESOLVED — the single largest open item.** §7 says "A3"; §4.2 splits A3 into A3-D and A3-LLM and states A3-D is *not required* to clear the 40%-gap criterion — which implies A3-LLM is the §7 subject. But §6A requires the A3-LLM configuration to be *selected on dev* and only the selected configuration re-run; working notes indicate the tuning sweep was **not completed**. **If no A3-LLM configuration was selected and frozen on dev, A3-LLM is not eligible to run on holdout at all.** (LOW confidence — must be read) | `EVAL.md §4.2`, §6A, §7; `results/tuning_log.md`; `configs/model_params.yaml` `frozen_policies`; CHANGELOG v1.5–v1.10 |
| 3 | Holdout size and seed range | **N = 2,000, indices 9,000–10,999**, `HOLDOUT_SPLIT = "holdout"`, `HOLDOUT_SEED_START = 9000`, `HOLDOUT_N = 2000`. Master seed `20260825`. (HIGH — matches `splits.py` and your stated brief) | `src/rrx/harness/splits.py`; `EVAL.md §3.5` |
| 4 | Exact metrics | Primary (Regime B): invoice recovery rate; subscription rescue rate; contacts per invoice recovered; contacts per subscription rescued; total contacts across cohort; median/p90 time-to-rescue. Secondary (Regime A): net value; cancellations attributable to contact volume. Broken out: `card_declined`/`payment_failed` bucket; `cancelled`-at-open bucket. (HIGH) | `EVAL.md §5`, §5.1 |
| 5 | Exact success criteria | Five pre-registered criteria (§7): (1) all §5.2 invariants hold on dev/holdout/stress; (2) per metric independently, A3 > best bounded non-agent arm, 95% CI on the difference excluding zero; (3) total contacts and contacts-per-rescue ≤ *that same* comparator arm; (4) uplift attributable to §3.4 structures with residual reported; (5) graceful handling of three injected failure modes. Target `[DESIGN]`: A3 captures **≥40% of the (A4 − best-bounded) gap** on both primary metrics. (MEDIUM-HIGH — v1.10 amended criterion 2 per working notes) | `EVAL.md §7`; CHANGELOG v1.5–v1.10 |
| 6 | Comparator / tie-set rule | Comparator is **dynamic per metric**: best-performing bounded non-agent arm on *that* metric, bounded set = `{A0, A1, A2-as-adopted}`, A4 and diagnostics (A1-U) excluded. Ties (95% CI on pairwise difference includes zero) reported explicitly, not resolved by point estimate. **Tie resolution: A3 must clear every member of the tied set** — working notes record this as the pre-registration ruling; it *must* be confirmed as committed text. (MEDIUM — this is the highest-stakes verification in the list) | `EVAL.md §7` criterion 2; CHANGELOG v1.5–v1.10 |
| 7 | Safety / gate invariants | §5.2's eight rows → gate rules R1–R6, R8 (there is no R7; row 7 "no audit record" is a *structural runner invariant*, one ledger record per tick). Precedence: `R2, R4 → R3 → R1, R8 → R5, R6`. R5 and R6 are enforcement-by-construction (planner never invoked at `budget_remaining == 0`; executor stamps fixed `send_hour = 10:00 IST`). R2 unreachable via real ticks in `sim-v1`. **Any non-zero value on any row is a P0 bug with a written post-mortem, not a score.** (HIGH) | `EVAL.md §5.2`; `docs/A3-DESIGN.md §8`; `src/rrx/agent/gate.py` |
| 8 | Artifact / provenance requirements | `EVAL.md §6`: every run writes `results/<run_id>/manifest.json` with **eleven fields** — git SHA, spec version, config hash, seed, arm, regime, sweep cell, model version, timestamp, wall-clock, LLM cost. `docs/A3-DESIGN.md §22`: `ledger.jsonl` and `llm_cache*.jsonl` gitignored; `results/audit_sample/` committed; manifests and aggregates always committed. (HIGH on the schema; **MEDIUM on whether the writer is actually wired** — it was defined-but-never-invoked as of Day 5) | `EVAL.md §6`; `src/rrx/spec/manifest.py`; `.gitignore`; grep for `write_manifest` call sites |
| 9 | Authorization mechanism | `rrx.harness.splits.holdout_indices(authorized=True)` — the *only* exposure of the range; `_HOLDOUT_INDICES` is underscore-private. Raises `HoldoutNotAuthorizedError` otherwise. `EVAL.md §3.5`: holdout runs **once per candidate release**, and **every run — successful or not — must be logged in `results/holdout_runs.md`**. (HIGH on the code guard; **verify `results/holdout_runs.md` exists** — it did not as of Day 5) | `src/rrx/harness/splits.py`; `EVAL.md §3.5`; `ls results/` |
| 10 | Frozen randomness / seeds / model params | Master seed `20260825`; bootstrap seed `20260826`, 10,000 resamples, 95% CI, via `rrx.sim.run_stage3.paired_bootstrap_ci`. CRN enabled with `substream_isolation: per_variable` across eight named substreams. `configs/model_params.yaml` `frozen_policies: [A2, A3-D, A3-LLM]`, `win_criterion.comparator: A2` (sweep-grid only, **not** the §7 comparator). `sweep.split: dev` — **holdout is never swept.** For `gpt-5-mini`, `temperature != 1` returns HTTP 400, so "temperature 0 where supported" is vacuously satisfied; nondeterminism evidence rests on the three repeat runs. (HIGH on seeds/CRN; MEDIUM on model params at v1.10) | `configs/model_params.yaml`; `configs/episode.yaml`; `configs/population.yaml`; `EVAL.md §6`; CHANGELOG |
| 11 | What must NOT change after freeze | `EVAL.md`, `SIM.md`, `docs/A3-DESIGN.md`, all `configs/*.yaml`, arm definitions, thresholds, comparator rules, gate rules, prompt text, model parameters, seeds, split definitions, metric definitions, the statistical procedure. `EVAL.md §10`: after the tag, the only reason to reopen is a **discovered validity defect — never to improve expected A3 performance.** (HIGH) | `EVAL.md §10` |
| 12 | Sensitivity status | Registry: 26 cells, 21 required wins (`ceil(0.80 × 26)`), pinned by `test_required_wins_is_ceil_of_eighty_percent`. **Sweep not run; results PENDING.** Crucially: `sweep.split: dev` — **sensitivity does not gate the holdout and is not a holdout blocker.** It is a *reporting* gap that must be disclosed, not repaired by touching holdout. (HIGH) | `configs/model_params.yaml`; `results/sensitivity.md` |

### A.2 — Contract items I could not locate at all

These must be answered by Step 0 or declared `NOT SPECIFIED`:

- **Retry / crash-resume policy for a once-only holdout run.** §3.5 says every run, successful or not, is *logged* — it does not say whether a second attempt after a crash is permitted, nor what "a run" means when it dies at episode 1,400 of 2,000. **This is a genuine gap and it must be closed before authorization** (see §G).
- **Which split criterion 5 (failure injection) is demonstrated on.** Criterion 1 explicitly names dev/holdout/stress; criterion 5 names no split. Strict reading: not on holdout.
- **Whether A2-original and A2-corrected-v1 are to be run on holdout** for transparency, or only A2-as-adopted.
- **Whether A1-U (diagnostic, unbounded) runs on holdout.**
- **Whether the §7 "A3" subject is A3-LLM, A3-D, or both** (see A.1 #2).
- **What constitutes "one run" for `results/holdout_runs.md`** — one entry per arm, or one entry per holdout session?

---

## B. PREFLIGHT CHECKLIST

All of §B executes **before** authorization and touches **only** dev/stress. Every item is a hard gate: a failure stops the sequence, it does not get worked around.

**B1 — Repository state**
1. `git rev-parse code-freeze-holdout` → must equal `4d45db461943978637673a5611a429e0fe826065`.
2. `git rev-parse eval-spec-v1.10` → must equal `125eae8841562f6d5eccab58e055400340e71af6`.
3. `git status --porcelain` → must be empty. No stashes, no untracked files under `src/`, `configs/`, `data/`.
4. Check out the freeze commit explicitly (detached HEAD at `4d45db4`) so no branch tip can drift under the run.
5. `git tag --verify` both annotated tags; record the annotation text into the run log.
6. `git diff eval-spec-v1.10 code-freeze-holdout -- EVAL.md SIM.md docs/A3-DESIGN.md configs/ data/` → **must be empty**. If the code freeze moved any spec or config surface after the spec tag, stop and report.

**B2 — Test baseline**
7. Full suite: expect **2231 passed, 1 failed**, the single failure being `tests/test_stage5_falsification.py::test_1_policy_ordering`. Any other count or any other failing test = STOP.
8. Reproduce the known failure's *numbers*, not just its failure: `A1=0.4840, A2=0.4485, diff=-0.0355, CI=[-0.0465,-0.0250]`. Byte-identical reproduction is the drift detector. A failure that fails *differently* is a new defect.
9. `python -m ruff check .` → clean.

**B3 — Environment provenance**
10. Record: Python version, OS, `pip freeze` (hashed), CPU, and a `sha256sum` of every file under `configs/` and `data/`.
11. Compute and record the config hash that `manifest.json` will carry. If no config-hash function exists, that is a manifest-schema gap — report it, do not invent one.

**B4 — Harness readiness (the part most likely to bite)**
12. Confirm `write_manifest` / `RunManifest` is **actually invoked** by the runner. As of Day 5 it was defined but never called by any non-test code. If manifests are still not wired, **the holdout run will produce no provenance and must not proceed.**
13. Confirm the runner **persists per-episode `EpisodeResult` vectors**, not just aggregates. Paired bootstrap requires per-episode paired data; a Day-6 run already discarded these once and needed a capture-only reproduction. On holdout there is no second chance.
14. Confirm ledger writing is wired end-to-end and produces one record per tick.
15. Confirm `results/holdout_runs.md` exists. If it does not, create it **before** authorization as an empty, committed, pre-declared log — creating it after the run looks like backfill.

**B5 — Rehearsal (strongly recommended, non-optional in my view)**
16. Execute the **exact command line** intended for holdout, for **every arm**, with only the split argument changed to `stress` (N=300, seeds 5000–5299). This proves: the CLI accepts the arguments, artifacts land in the right paths with the right names, manifests are written with all eleven fields, ledgers are complete, the aggregation script consumes the artifacts, and the invariant checks run. A once-only holdout run is not the place to discover a typo in an output path.
17. Confirm the rehearsal's artifacts are written under a clearly separate directory and are **deleted or clearly namespaced** so they can never be confused with holdout artifacts at aggregation time.

**B6 — A3-LLM specific (only if A3-LLM is eligible per A.1 #2)**
18. Confirm a **single selected configuration** exists, recorded in `results/tuning_log.md`, with a commit SHA predating the freeze.
19. Confirm the pinned model version string and that it is what the API will actually serve.
20. Confirm API key present, quota sufficient, and estimated cost computed (2,000 episodes × wake-ups per episode × tokens). Record the estimate *before* the run.
21. Confirm cache file path is holdout-specific and empty at start.
22. Confirm the prompt builder passes the latent-leak invariant test.

**B7 — Deliverable reality check (not a technical gate, but a submission gate)**
23. Architecture diagram: status. Pitch video script: status. `RESULTS.md` skeleton with empty tables pre-committed: status. `LIMITATIONS.md`: status. Failure-injection implementation (§7 criterion 5): status. Any `[CITE-PENDING]` items still open: status.

---

## C. AUTHORIZATION STEP

Authorization is a **human act recorded in the repository before execution**, not a flag typed at a shell.

**C1.** You write and commit a pre-declaration to `results/holdout_runs.md`, *before* the run, containing:
- Timestamp, git SHA (`4d45db4`), spec version (`eval-spec-v1.10`)
- The complete, final list of arms to be run — **frozen at this moment, not extendable afterward**
- The exact command line for each arm, verbatim
- Split, N, seed range, master seed
- The pre-registered retry rule (§G), quoted
- Explicit statement: "Holdout has not been accessed prior to this entry."
- Your signature line: an explicit, unambiguous authorization sentence.

**C2.** Commit and tag this pre-declaration (`holdout-authorized-<date>`). The tag is the audit anchor: it proves the arm list and commands were fixed before any number existed.

**C3.** Exactly **one** call site in the entire repository passes `authorized=True`. It lives in a dedicated entry-point script (e.g. `scripts/run_holdout.py`) that:
- Requires an explicit CLI flag such as `--i-have-authorized-the-holdout` with no default
- Refuses to run if `git status` is dirty or HEAD ≠ `4d45db4`
- Refuses to run if `results/holdout/` already contains a completed run for this SHA
- Appends a start entry to `results/holdout_runs.md` as its first action
- Never catches `HoldoutNotAuthorizedError` and retries

**C4.** Grep the repository to confirm no other `authorized=True` literal exists anywhere outside tests. Any test that passes `authorized=True` must be confirmed to use a mocked range, not the real one.

---

## D. EXACT EXECUTION SEQUENCE

### D.1 — Commands

**I am not writing the command strings.** I do not have the repository, and inventing a CLI that does not exist would violate the requirement that this plan be built on the actual implementation. Step 0 must extract the real invocation surface and record it in `docs/DAY8-CONTRACT-EXTRACT.md`. The command block in `results/holdout_runs.md` (§C1) is then filled with the real strings and frozen.

What each command must satisfy, whatever its actual syntax:
- Explicit `--split holdout`, explicit `--n 2000`, explicit `--seed-start 9000`, explicit `--master-seed 20260825`, explicit `--arm <name>`, explicit `--run-id <run_id>`
- No default-valued parameter that could silently differ from dev
- Output directory passed explicitly, not derived
- stdout and stderr redirected to a file, **not** to a terminal a human is watching (see D.4)

### D.2 — Arm ordering

**Deterministic arms first, A3-LLM last.**

Order: `A0 → A1 → A2-strengthened → [A2-original, A2-corrected-v1, A1-U if in scope] → A4 → A3-D → A3-LLM`.

*Rationale, with the tradeoff stated:* the holdout is spent at first access regardless of ordering, so ordering cannot protect the split. What ordering protects is **completeness under partial failure**. Deterministic arms are free, fast, and exactly reproducible from the frozen code — if one crashes, re-executing it is a mechanical replay, not a re-roll. A3-LLM is the only arm that is costly, nondeterministic, and irreproducible. Running it last means a mid-run API collapse leaves every deterministic result already banked and sealed.

*The counter-argument I considered and rejected:* running A3-LLM first surfaces API failure earliest. But an early API failure would then sit alongside zero banked results and create pressure to "just restart the whole thing" — which is precisely the pressure the once-only rule exists to resist.

### D.3 — Arm-set decision (decide before authorization, not during)

Because the holdout is once-only, **an arm omitted now can never be added later.** This argues for running every deterministic arm in the single pass: A2-original and A2-corrected-v1 (transparency, and they cost nothing), A1-U (the "does more contact help" diagnostic).

The objection — that extra arms look like fishing — does not hold *provided* the comparator set is pre-registered and fixed. `{A0, A1, A2-as-adopted}` are the only comparator-eligible arms; A4 is reference; A1-U and the other A2 variants are reported but **structurally ineligible** to be selected as the comparator. Write that ineligibility into the pre-declaration explicitly, and the extra arms become transparency, not fishing.

**Recommendation:** run all deterministic arms. **Decide this in §C1 and never revisit it.**

### D.4 — Isolation of each run

- One process per arm. No shared mutable state between arms.
- Each arm writes to its own directory; a run refuses to start if its directory already exists.
- stdout/stderr → `results/holdout/<run_id>/<arm>/stdout.log`. **Nobody reads these logs until every arm has completed** (see §H).
- CRN guarantee: every arm consumes the same episode indices with the same master seed and per-variable substream isolation, so episode *i* presents an identical latent world to every arm. This is what makes the paired bootstrap valid. Verify post-run (§I), not by peeking mid-run.
- No network access for deterministic arms — verify by running them with networking disabled if the environment permits. A deterministic arm that needs the network is a defect.

### D.5 — Sequence

1. Step 0 contract extraction → your review → plan revision if needed
2. §B preflight, all items, all green
3. §C authorization pre-declaration committed and tagged
4. Execute arms in §D.2 order, each isolated per §D.4
5. On completion of the **final** arm: seal (§E.3)
6. Only then: aggregate (§F), verify invariants (§I), compare against criteria (§F.3)
7. Generate report (§J)

---

## E. ARTIFACT / PROVENANCE REQUIREMENTS

### E.1 — Per-arm artifacts

`results/holdout/<run_id>/<arm>/` containing:

| Artifact | Content | Committed? |
|---|---|---|
| `manifest.json` | All eleven `EVAL.md §6` fields | Yes |
| `episode_results.jsonl` | Per-episode result vector, 2,000 records, keyed by episode index | Yes (needed for paired bootstrap reproduction) |
| `aggregates.json` | Integer counts and rates for every §5 metric | Yes |
| `ledger.jsonl` | One record per tick | Gitignored per §22; hash committed |
| `stdout.log` | Captured console output | Yes |
| `llm_cache_holdout.jsonl` | A3-LLM only | Gitignored per §22; hash committed |
| `env.json` | Python/OS/package versions, config hashes | Yes |

### E.2 — Run-level artifacts

`results/holdout/<run_id>/`:
- `holdout_manifest.json` — arm list, commands, start/end timestamps, SHA, spec version
- `SHA256SUMS` — hash of every artifact including gitignored ones
- `invariant_report.json` — §I outputs
- `comparison.json` — §F outputs

### E.3 — Sealing

After the last arm finishes and **before any aggregation or inspection**:
1. Compute `SHA256SUMS` over the whole run directory.
2. Commit everything committable.
3. Tag `holdout-run-<run_id>-sealed`.
4. Append the completion entry to `results/holdout_runs.md`.

The seal tag is the evidence that the raw numbers existed, unmodified, before anyone looked at them. It is the single most valuable artifact for a skeptical panel.

### E.4 — Ledger handling

- Ledgers are large and gitignored, but their **hashes and a sampled excerpt are committed**.
- `results/audit_sample/` gets a committed sample of holdout ledger records — this is the audit-trail deliverable the track's bar explicitly demands, and a holdout-derived sample is stronger evidence than a dev-derived one.
- Sample selection must be **mechanical and pre-declared** (e.g. "first 20 records of episodes 9000, 9500, 10000, 10500"), never "the interesting ones." Declare the selection rule in §C1.
- Ledger completeness is an invariant check (§I), not a spot check.

---

## F. METRICS AND SUCCESS CRITERIA

### F.1 — Aggregation

- Aggregate **only from `episode_results.jsonl`**, never from parsed stdout.
- Recompute every aggregate independently and assert exact integer agreement with `aggregates.json`. Disagreement = STOP.
- Paired bootstrap: `rrx.sim.run_stage3.paired_bootstrap_ci`, 10,000 resamples, 95% CI, bootstrap seed `20260826`, paired on episode index. Frozen — no alternative test, no adjustment.

### F.2 — Comparator selection algorithm (must be executed mechanically, in this order)

For each primary metric M ∈ {invoice recovery rate, subscription rescue rate}, independently:

1. Compute rate for each bounded non-agent arm in `{A0, A1, A2-as-adopted}`. A4, A1-U, and non-adopted A2 variants are **ineligible**.
2. Identify the highest point estimate; call it the leader.
3. Compute paired-bootstrap CI on leader − each other bounded arm. Any arm whose CI includes zero joins the **tied set** with the leader.
4. **Tie rule:** A3 must clear **every member of the tied set** on M — CI on each difference excluding zero. *(Verify this is the committed v1.10 text. If v1.10 instead says something weaker, use v1.10, not this.)*
5. Criterion 3's contact comparison uses **the same arm(s)** that criterion 2 used for M — for a tied set, the strict reading is every member.
6. Target: A3's rate ≥ best-bounded rate + 0.40 × (A4 rate − best-bounded rate), computed **on holdout**, with holdout's own A4 and holdout's own best-bounded. Dev's 0.5090 / 0.5499 are illustrative only and must not be reused as thresholds.

### F.3 — Criteria evaluation

Produce a pass/fail line per criterion with the supporting number:

| Criterion | Evaluated as |
|---|---|
| 1 — Invariants on dev/holdout/stress | §I invariant report; all eight §5.2 rows = 0 |
| 2 — Rate superiority per metric | §F.2, both metrics, CI excluding zero against every tied-set member |
| 3 — Contact discipline | Total contacts and contacts-per-rescue ≤ comparator's, per metric |
| 4 — Attribution to §3.4 structures | A3-LLM − A3-D paired bootstrap; unexplained residual reported |
| 5 — Failure-mode handling | **Not evaluated on holdout** (strict reading; flag §K) |
| Target | 40%-of-gap formula, computed on holdout |

**Declared failure is a pre-registered outcome.** The spec already says: if A3 cannot beat the best bounded arm at equal budget, report that, keep the harness, and pitch the gating and audit layer as the contribution. Do not re-tune. Do not re-run. A published honest miss with this methodology is a stronger hiring signal than an unfalsifiable win.

---

## G. FAILURE / RETRY POLICY

**This is the largest procedural gap in the frozen spec and it must be closed before authorization.** §3.5 requires every run — successful or not — to be logged, but does not define whether a second attempt is permitted, or what a "run" is when it dies partway.

Improvising this rule *during* a failed run, with partial numbers on disk, is exactly how contamination happens. It must be written blind — before any holdout number exists — and committed as part of §C1.

I am not resolving it for you. Here are the options with tradeoffs; **you rule**:

**Option 1 — Strictly once (hardest line).** Any crash ends the holdout. Report what completed and why it stopped.
*Pro:* unimpeachable. *Con:* a transient disk error destroys the evaluation. Disproportionate.

**Option 2 — Deterministic replay permitted, nondeterministic not (my recommendation).**
- A **deterministic** arm (A0, A1, A2 variants, A1-U, A4, A3-D) that crashes may be re-executed from scratch with byte-identical inputs. Justification: with frozen code, frozen config, frozen seeds and no network, replay is not a second sample — it is the same computation completed. The result is provably the same run. Every attempt, successful or not, is logged in `results/holdout_runs.md` with the failure reason.
- An **A3-LLM** crash may be resumed **only** from its existing cache, with identical seeds, identical prompt, identical model version, identical parameters, and no config change of any kind. Uncached episodes are re-requested; cached ones replay. Any resume is disclosed in `RESULTS.md`.
- **No parameter, prompt, config, seed, or arm definition may change between attempts.** A crash whose fix requires a code change ends the holdout for that arm; the code change is a post-holdout defect record, not a rerun ticket.
- Attempt count per arm is capped (propose 2) and declared in advance.

**Option 3 — Any run may be repeated if logged.** Too permissive; "logged" is not a constraint if the number of attempts is unbounded.

**API failure handling (A3-LLM), within whichever option you pick:** in-request transport retries (HTTP 429/5xx/timeout) are an implementation detail of a single logical call and are permitted **only if** they were already implemented and frozen at `4d45db4`. Verify this in Step 0 — do not add retry logic now. A frozen fallback path already exists in the spec (`fallback_reason ∈ {timeout, unparseable, schema_violation, gate_rejected, stale_state}`, fallback target A3-D): an API failure that exhausts frozen retries becomes a **logged fallback event and the run continues**. That is the designed behaviour and it is also direct evidence for §7 criterion 5. Fallback rate must be reported prominently, not buried.

**Answers to your explicit questions:**

- **Are retries permitted?** Only under the rule you freeze in §C1, and only in the sense above. Nothing improvised.
- **Can any result be discarded?** **No.** Not one episode, not one arm, not one attempt. Every attempt is logged whether or not it is used.
- **Can any result be selectively rerun?** **No.** Selective rerun conditioned on an observed value is the definition of contamination. Whole-arm deterministic replay after a crash is permitted under Option 2 only because it is *unconditioned on the result* — the trigger is a crash, not a number.
- **Can we inspect holdout results before all arms finish?** **No.** See §H.

---

## H. CONTAMINATION SAFEGUARDS

**What contamination is, in this project:** any path by which a holdout number influences a decision that should have been made without it. Concretely — re-tuning after seeing a result; changing the comparator, threshold, tie rule, or metric after seeing a result; discarding an arm or episode because of its value; re-running conditioned on a value; selecting an audit sample because of what it shows; changing prompt or config between attempts; writing `RESULTS.md` narrative from memory of dev rather than from holdout artifacts.

**Safeguards, in order of strength:**

1. **Pre-declaration (§C1).** Arm list, commands, comparator rule, tie rule, retry rule, and audit-sample selection rule are committed and tagged before the first episode runs. Anything not declared cannot be added.
2. **The single guarded call site (§C3).** One `authorized=True`, one entry-point script, refusing to run on a dirty tree or a non-freeze HEAD.
3. **No-peek discipline.** stdout goes to files; nobody opens them until the seal. Aggregation, comparison, and criteria evaluation happen only after the last arm completes and the run is sealed. *Practical enforcement: the aggregation script should refuse to run unless every declared arm's directory contains a complete `episode_results.jsonl` and `manifest.json`.*
4. **Sealing before analysis (§E.3).** Hash-and-tag the raw artifacts before anyone looks. This makes post-hoc modification detectable rather than merely forbidden.
5. **Mechanical comparator selection (§F.2).** The comparator is computed by code from a pre-registered algorithm, not chosen by a human reading a table.
6. **Append-only run log.** `results/holdout_runs.md` records every attempt including failures. A clean log with exactly one entry is *less* credible than an honest log with a crash and a declared replay.

**What holdout information is allowed to influence anything afterward?**

- **Allowed:** the contents of `RESULTS.md`; the pass/fail determination against §7; the honest narrative in the README, `LIMITATIONS.md`, pitch script, and architecture doc; a post-hoc *observation* clearly labelled as post-hoc and excluded from the pre-registered claim; a discovered validity defect, recorded as a defect with no re-run.
- **Forbidden:** any change to agent policy, prompt, gate, config, model parameters, thresholds, comparator rule, tie rule, metric definitions, arm definitions, or the simulator. Any second holdout run for this candidate release. Any selection of what to show based on what looks good.

The rule of thumb: **holdout results may change what you say; they may never change what you built or how you measured it.**

**Guarantee against accidental pre-authorization access:** the underscore-private `_HOLDOUT_INDICES`, the `authorized=False` default, the raising guard, the single call site, the grep check in §C4, and the fact that no run has ever been executed with the flag. Add one more if it is cheap: a test asserting that no module outside `scripts/run_holdout.py` contains the literal `authorized=True`. That is a new *test*, not a spec change — but confirm in Step 0 that adding a test to a frozen tree is acceptable under your freeze convention, or defer it.

---

## I. POST-RUN VERIFICATION

Run after sealing, before interpretation. All are pass/fail; any failure is reported, never silently fixed.

1. **Split identity.** Every manifest records split `holdout`, N = 2,000, indices 9,000–10,999. Every `episode_results.jsonl` contains exactly 2,000 records with exactly those indices, no duplicates, no gaps.
2. **CRN identity.** For a sample of episode indices, confirm the latent world is identical across arms — the frozen falsification test #4 (CRN identity) is the existing mechanism; use it, don't write a new one.
3. **Gate invariants (§5.2, all eight rows).** Every row must be 0. Report gate rejection *counts* by rule as well — non-zero rejections are evidence the gate works; non-zero *violations* are a P0.
4. **Budget invariant.** No episode exceeds 3 contacts for any bounded arm. A1-U is exempt by definition — confirm it is reported separately and excluded from comparator eligibility.
5. **Ledger completeness.** One record per tick, per episode, per A3 arm. Structural, not sampled.
6. **Audit coverage.** 100% of actions carry a machine-readable reason code and rationale.
7. **Manifest completeness.** All eleven fields present and non-null in every arm's manifest. Model version pinned for A3-LLM.
8. **Aggregate reproduction.** Independently recompute every aggregate from per-episode data; exact integer match required.
9. **Bootstrap reproduction.** Re-run the paired bootstrap from committed per-episode vectors with seed `20260826`; must reproduce identically.
10. **Taxonomy validity.** Every `tick_type` ∈ 4 values, `reason_code` ∈ 7 values, `gate_rule_fired` ∈ {R1–R6, R8, null}, `fallback_reason` ∈ 5 values ∪ {null}.
11. **A3-LLM specifics.** Cache hit/miss counts; fallback rate by reason; total cost vs. pre-run estimate; model version served == model version pinned.
12. **Hash integrity.** Re-verify `SHA256SUMS` after analysis to prove nothing was edited.

---

## J. FINAL REPORTING

`RESULTS.md`, written **from the sealed artifacts only** — never from memory, never from dev figures. Structure:

1. **Provenance header** — SHA `4d45db4`, `eval-spec-v1.10`, run id, seal tag, date, split, N, seeds.
2. **Holdout access record** — the `results/holdout_runs.md` entry, quoted, including any failures and replays.
3. **Headline table** — every arm × every §5 metric, no arm omitted.
4. **Criterion-by-criterion verdict** — §F.3, each with its number and CI, pass or fail stated plainly.
5. **Comparator determination** — which arm won each metric, the tied set if any, and the mechanical selection trace.
6. **Target evaluation** — the 40%-of-gap computation shown in full with holdout's own A4 and best-bounded values.
7. **Restraint evidence** — wait rate, contacts per rescue, total contacts. This is the project's thesis; give it its own section.
8. **Gate and audit evidence** — invariant table (all zeros), gate rejection counts by rule, ledger completeness, link to `results/audit_sample/`.
9. **A3-LLM reliability** — fallback rate by reason, nondeterminism evidence from the three repeat runs, the `temperature != 1` constraint stated prominently, cost.
10. **Known gaps, stated first-person and without softening:**
    - Sensitivity sweep **not run**; 26 cells / 21 required wins registered but `PENDING`. State that the registry and pass mark were fixed in advance and the sweep is unexecuted — that is a scope gap, not a hidden result.
    - `tests/test_stage5_falsification.py::test_1_policy_ordering` fails: A1 outperforms A2 on invoice recovery on dev, contradicting the pre-registered ordering. Pre-existing, reproduced byte-identically at freeze. **Lead with this in the write-up.** A failing falsification test that you publish is credibility; one a panel finds is a fatal wound.
    - §7 criterion 5 (failure injection) status.
    - Regime A is invented; every headline number is Regime B.
    - Simulator realism limits; the world was written by us.
11. **Reproduction instructions** — exact commands, exact SHA, exact seeds.

Then the two deliverables that are not code: **architecture doc/diagram** and **5-minute pitch script**. Both must be written from `EVAL.md` and the sealed results, not from memory of earlier conceptions of the project.

---

## K. KNOWN AMBIGUITIES / RISKS

**Ambiguities — flagged, not resolved:**

- **K1. A3-LLM's holdout eligibility.** §7 says "A3"; §4.2 splits it; §6A requires a dev-selected configuration. If the tuning sweep never selected and froze one, A3-LLM cannot run on holdout without violating §6A — and A3-D alone is explicitly *not* required to clear the 40%-gap criterion. **This is the plan's blocking ambiguity.**
- **K2. Tie-set rule text.** Working notes record the "A3 must clear every tied member" ruling, but I cannot confirm it is committed in v1.10. If it is not, the tie rule is genuinely unspecified, and specifying it after the holdout runs would be post-hoc.
- **K3. Retry/crash-resume rule.** Unspecified (§G). Must be frozen before authorization.
- **K4. Criterion 5's split.** Failure injection names no split. Strict reading: not holdout.
- **K5. "One run" definition** for `results/holdout_runs.md` — per arm or per session.
- **K6. Non-adopted A2 variants and A1-U on holdout** — in or out of scope.
- **K7. §7 criterion 4** ("uplift attributable to §3.4 structures, with unexplained residual reported") has no stated computational procedure beyond A3-LLM − A3-D. What counts as "attributable" is not operationalized.

**Risks:**

- **R1. Provenance machinery may still be unwired.** As of Day 5, `write_manifest` was never invoked and per-episode results were discarded once already on Day 6. If either is still true at `4d45db4`, the holdout produces unprovable results. **B4 catches this; it is the most likely preflight failure.**
- **R2. Sensitivity `PENDING` weakens the §8 threat-2 answer.** Not a holdout blocker (`sweep.split: dev`), but a panel will ask. It must be disclosed, not glossed.
- **R3. The failing falsification test is a live interview question.** "Your own pre-registered ordering test fails" is the first thing a skeptical reviewer will find. Have the answer written down before the video.
- **R4. Calendar.** Six days to September 5. Architecture diagram and pitch script at zero. The holdout run is a few hours of compute; the diagram and script are the binding constraint. **If forced to choose, cut experiment scope, not deliverables — an unsubmitted evaluation scores zero.**
- **R5. `[CITE-PENDING]` items** must close before freeze.
- **R6. Cost/time of A3-LLM on 2,000 episodes** — estimate before authorizing, not after starting.
- **R7. Rehearsal skipped.** If §B5 is skipped to save time and the holdout run then fails on a path typo, you will be improvising retry policy under pressure. Do not skip it.

---

## L. VERDICT

# YELLOW

The plan's *shape* is sound and the safeguards are adequate. It cannot be handed to Claude Code as an execution order yet, because three things must close first — and none of them requires touching the holdout.

**Must close before this becomes GREEN:**

1. **Step 0 contract extraction at `4d45db4`.** Everything in §A is a hypothesis built on a v1.4 reading. Verify or correct all twelve answers plus §A.2's six gaps. If anything contradicts §A, revise this plan before executing it.
2. **Rule on A3-LLM's holdout eligibility (K1).** If no dev-selected, frozen configuration exists in `results/tuning_log.md` at or before the freeze, A3-LLM does not run on holdout, and you need an explicit, committed decision about what §7's "A3" then refers to. That decision must be made *now*, blind to holdout results.
3. **Freeze the retry/crash-resume rule (K3, §G) and the audit-sample selection rule, in `results/holdout_runs.md`, before authorization.**

**Also required, and mechanical:** confirm manifest writing and per-episode result persistence are wired (B4 #12–13); create `results/holdout_runs.md` if absent (B4 #15); run the stress-split rehearsal (B5).

**Not blockers:** the sensitivity `PENDING` state (holdout is never swept) and the known falsification-test failure (pre-existing, documented, must reproduce byte-identically).

**On the honest question you asked me to keep answering — demo-grade or submission-grade:** the *methodology* is well past submission-grade and is the strongest thing here. The *submission* is not, and the gap is not evaluation rigor. It is the architecture diagram and the pitch script, both at zero with six days left. The holdout run is worth a few hours. Guard the rest for the deliverables.