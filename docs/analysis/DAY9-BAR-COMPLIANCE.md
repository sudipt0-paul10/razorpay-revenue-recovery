# DAY 9 — BAR COMPLIANCE AUDIT

**Status:** Day 9, Stage 6. A skeptical, implementation-level audit of
whether this repository's claims are actually evidenced. Read-only —
no production code, evaluation artifact, or holdout artifact was
modified to produce this document. Where a gap was found, it is reported
here, not fixed. All test/lint/checksum commands below were re-run this
session, not assumed from earlier stages.

---

## 1. Audit scope

This audit inspects the repository as it stands at commit `ecc857b`
(HEAD at audit start) plus this document's own addition. It answers one
question per requirement: **does a concrete, inspectable artifact
support this claim, or does only prose support it?** Twelve of the
fourteen listed sections below map directly to the eleven numbered
requirements in this stage's authorization; §1/§2/§14 are scope and
synthesis sections.

**Not in scope, per this stage's hard rules:** modifying
`src/rrx/agent/`, `src/rrx/sim/`, `EVAL.md`, any holdout artifact, the
cost model, or rerunning/tuning anything. Every finding below is
diagnostic; none is auto-remediated.

## 2. Authoritative requirements

**No external Razorpay-provided rubric, brief, or rules document exists
anywhere in this repository.** A repository-wide search
(`grep -rln "Track 03\|buildathon"`) finds exactly two one-line
characterizations — `CLAUDE.md:3` and `docs/PITCH.md:3`, both reading
"Razorpay AI Buildathon, Track 03 — AI Revenue Recovery" — and no
document elaborating specific track judging criteria, deliverable
formats, or scoring weights. **This project's actual authoritative
requirements are self-imposed**, encoded in `EVAL.md §7`'s five
pre-registered success criteria and `§10`'s freeze checklist. Absent an
external rubric, this audit treats two things as authoritative: (a)
`EVAL.md`'s own pre-registered criteria, and (b) the eleven specific
audit requirements enumerated in this stage's own authorization prompt,
which is the closest artifact this repository has to an external
checklist. No requirement is invented from outside these two sources.

## 3. Money recovered

**Classification: MISSING / SUBMISSION RISK for a headline ₹ figure.
PASS WITH LIMITATION for the underlying accounting machinery.**

A full-repository search (`RESULTS.md`, `docs/PITCH.md`, `ARCHITECTURE.md`)
for `₹`, `_inr` aggregates, `net_value`, or `gross_recovered` finds **no
aggregate recovered-₹ figure anywhere** — only the field name
`invoice_amount_inr` (per-episode, in `episode_results.jsonl`, never
summed and published) and `llm_cost_inr` (a manifest field, always `0.0`
for A3-D since it never calls an LLM). `RESULTS.md` reports **rates
only** (invoice recovery rate, subscription rescue rate) — never a ₹
sum, never a net-value calculation.

1. **Is recovered money actually represented?** Only implicitly, via
   `invoice_amount_inr` on each per-episode record — never aggregated,
   summed, or reported as a headline figure anywhere.
2. **Can a reviewer see a ₹ amount rather than only recovery rates?**
   **No**, in any officially published artifact (`RESULTS.md`,
   `metrics.json`). `docs/analysis/DAY9-NET-VALUE.md` (Day 9 Stage 1,
   explicitly labeled a diagnostic, not an official metric) computes a
   break-even ₹/contact figure using two labeled reference assumptions
   for expected invoice value — it does **not** produce a "total ₹
   recovered" number, and states explicitly why one is not derivable
   from published aggregates without touching raw per-episode holdout
   data (which that document declined to do, per its own contamination
   boundary).
3. **Is the calculation reproducible?** The cost model
   (`configs/costs.yaml`) is fully registered and reproducible
   (successful-capture fee 2.36%, messaging costs per channel,
   annoyance penalty). What is *not* reproducible from any existing
   artifact is a per-arm total ₹ recovered, because no code path
   currently sums `invoice_amount_inr` over recovered episodes and
   writes it to any `metrics.json` or `RESULTS.md` table.
4. **Are transaction/capture fees handled consistently?** Yes, on paper
   — `configs/costs.yaml`'s `net_recovered_formula` is well-specified
   and applies uniformly across arms in principle. It has never actually
   been evaluated against any run's real invoice-amount data to produce
   a number.
5. **Are any monetary claims merely hypothetical?** The only monetary
   claims in this repository beyond registered cost inputs are in
   `docs/analysis/DAY9-NET-VALUE.md`, which is explicit, throughout, that
   its invoice-value inputs are labeled `ASSUMPTION`/`INFERENCE`, not
   measured. No other document in the repository makes a ₹ claim of any
   kind.

**What artifact would close this gap:** a new, explicitly-registered
metric — e.g. `total_invoice_inr_recovered = sum(invoice_amount_inr for
recovered episodes)` — computed from the already-committed
`episode_results.jsonl` files (which do carry `invoice_amount_inr` per
episode) and added to `compute_metrics()`'s output for future runs. This
is a **methodology/code change** (a new metric definition), which this
audit stage is expressly forbidden from making — reported here, not
implemented.

**Per this stage's explicit instruction:** no ₹ recovered figure is
invented here. **MISSING / SUBMISSION RISK** is the correct label for
the headline claim; the underlying registered cost inputs are real and
reproducible.

## 4. Escalation / action control

**Classification: PASS — IMPLEMENTED + EVIDENCED.**

Every `EVAL.md §5.2` row has an implementation file and a passing test,
re-run this session (`python -m pytest tests/test_gate_rules.py -v`, 14
tests, **all PASSED**):

| Control | Implementation | Test | Result this session |
|---|---|---|---|
| No agent-initiated retry (R1) | `src/rrx/agent/gate.py` | `test_r1_rejects_out_of_schema_action_type`, `test_r1_accepts_in_schema_action_type` | PASSED |
| No contact to cancelled/expired (R2) | `src/rrx/agent/gate.py` | `test_r2_rejects_contact_to_cancelled_subscription`, `test_r2_accepts_contact_to_non_terminal_subscription` | PASSED |
| Remedy match — no card-change for balance conditions (R3) | `src/rrx/agent/gate.py` | `test_r3_rejects_card_change_for_insufficient_funds`, `test_r3_accepts_card_change_for_card_expired` | PASSED |
| No contact after risk flag (R4) | `src/rrx/agent/gate.py` | `test_r4_rejects_contact_for_payment_risk_check_failed`, `test_r4_accepts_contact_for_a_non_risk_decline_code` | PASSED |
| Contact budget cap (R5) | `src/rrx/agent/gate.py` | `test_r5_rejects_contact_when_budget_exhausted`, `test_r5_accepts_contact_when_budget_remains` | PASSED |
| Quiet hours (R6) | `src/rrx/agent/gate.py` | `test_r6_rejects_an_out_of_window_send_hour`, `test_r6_accepts_the_fixed_in_window_send_hour` | PASSED |
| Unverified codes (R8) | `src/rrx/agent/gate.py` | `test_r8_rejects_contact_for_an_unverified_decline_code`, `test_r8_accepts_contact_for_a_known_good_decline_code` | PASSED |
| Legal executor mapping (§7.1 item E) | `src/rrx/harness/runner.py` | `tests/test_executor_mapping_enforcement.py` (10 tests) | PASSED |
| Remedy matching, full policy | `src/rrx/agent/policy.py` (16-rule table) | `tests/test_a3d_policy.py` (40 tests: totality, determinism, reason-code admissibility) | PASSED |

**Evidence artifact beyond tests:** the sealed holdout `metrics.json` for
A3-D (`results/holdout/4d45db461943/a3_d/metrics.json`) shows all eight
safety-invariant counts at zero, cross-checked in this audit against a
**fresh** `sha256sum -c SHA256SUMS` (all 21 files `OK`, re-run this
session).

## 5. Stopping rules

**Classification: PASS WITH LIMITATION** (one row, budget exhaustion,
lacks a dedicated runtime negative test — see §7E below for full detail;
every other row is directly evidenced).

| Stopping mechanism | Evidence | Status |
|---|---|---|
| `STOP` action (explicit) | `src/rrx/agent/policy.py` rules R-01/02/03/05/06/07; ledger `executed_action.action_type=="STOP"` (311 real occurrences in sealed holdout ledger, independently counted this audit's predecessor stage) | PASS — IMPLEMENTED + EVIDENCED |
| Contact budget exhaustion | `src/rrx/harness/runner.py`, `tick_type="budget_exhausted"` set by control-flow structure before the policy is ever called | PASS WITH LIMITATION (see §7E) |
| Retry window (`retry_window_open` reason code) | `src/rrx/agent/policy.py` R-04/R-09/R-10; ledger `reason_code` field | PASS — IMPLEMENTED + EVIDENCED |
| Cancelled-at-open | `src/rrx/harness/runner.py:190-196`, `src/rrx/sim/engine.py:~438-443` — early return before any tick | PASS — IMPLEMENTED + EVIDENCED, **independently re-verified this audit's predecessor stage (Day 9 Stage 3) against the sealed ledger**: 111/2,000 A3-D holdout episodes are `subscription_cancelled_by_customer`, all with zero contacts and zero ledger records, identical across all five arms |
| Gate rejection | `src/rrx/agent/gate.py`; `tests/test_gate_rejection_fallback.py` (7 tests, all PASSED this session) | PASS — IMPLEMENTED + EVIDENCED |

## 6. Audit trail

**Classification: PASS WITH LIMITATION.**

1. **Can a reviewer trace an action through the ledger?** Yes, for
   A3-D. Every tick produces one `LedgerRecord`
   (`src/rrx/agent/ledger.py`) with `tick`, `tick_type`, `reason_code`,
   `gate_verdict`, `gate_rule_fired`, `executed_action`,
   `fallback_reason`, `rationale` (rule id), `view_hash`. Verified this
   session by direct inspection of `results/audit_sample/a3d_holdout_ledger_sample.jsonl`
   (561 lines: 1 header + 560 real records across 20 episodes,
   `range(9000, 11000, 100)`).
2. **Are decisions attributable to structured rules?** Yes — every
   A3-D wakeup record's `rationale` field is the exact decision-table
   rule id (`R-01`…`R-16`), not free text. This was the basis of Day 9
   Stage 3's entire mechanism-attribution analysis.
3. **Are LLM decisions traceable where they exist?** Yes, where A3-LLM
   evidence exists at all (dev only — see §8): `raw_output`,
   `prompt_hash`, `tokens_in`/`tokens_out`, `latency_ms`, `model_version`
   are all populated fields, independently confirmed non-null in a real
   GPT-C6 dev ledger this audit's predecessor session inspected
   directly.
4. **Is the audit sample representative?** It is **mechanically
   selected** (`range(9000, 11000, 100)`, 20 indices, pre-declared before
   any holdout access, per `docs/DAY8-AUDIT-SAMPLE-RULING.md`), not
   cherry-picked — that is a real, verifiable property. It is **not**
   statistically representative of rare paths: A3-D is gate-compliant by
   construction, so the sample necessarily shows zero gate rejections and
   zero fallback reasons, by construction, regardless of which 20
   episodes were drawn.
5. **What does the audit sample NOT demonstrate?** Per
   `docs/DAY8-AUDIT-SAMPLE-RULING.md §5` itself (self-disclosed, not
   found by this audit): it does not, and cannot, demonstrate coverage
   of every `tick_type`, every gate-rejection path (R1–R8), or every
   `fallback_reason` value — that coverage is the job of the separate
   synthetic test suite (`tests/test_gate_rules.py` et al., §4 above),
   independently confirmed passing this session.

## 7. Failure handling

**High-priority re-verification, independent of documentation, per this
stage's instruction.**

**A. API timeout — TESTED.** `tests/test_a3_llm_forced_failure_parity.py::test_forced_timeout_a3_llm_reproduces_a3d_over_the_full_dev_split`
— **PASSED** this session. Injects `StubLLMClient(raises=PlannerTimeoutError)`, runs the real `run_episode_a3` runner over the full dev split, confirms A3-LLM's forced-timeout behavior is byte-identical to A3-D's.

**B. Unparseable LLM output — TESTED.** `tests/test_planner_fallback_ledger.py::test_b_unparseable_fallback_reaches_the_ledger` — **PASSED** this session. `StubLLMClient(response="this is not json at all")`, real runner, real ledger record inspected.

**C. Schema violation — TESTED.** `tests/test_planner_fallback_ledger.py::test_c_schema_violation_fallback_reaches_the_ledger` — **PASSED** this session. Valid JSON, out-of-enum `reason_code`.

**D. Gate rejection — TESTED.** `tests/test_gate_rejection_fallback.py::test_gate_rejected_llm_proposal_falls_back_to_a3d_end_to_end` — **PASSED** this session. Syntactically valid but gate-rejected (R4) proposal, real end-to-end fallback.

**E. Budget exhaustion — STRUCTURALLY IMPLEMENTED, NOT INDEPENDENTLY RUNTIME-TESTED. Confirmed independently, not merely re-quoted from Stage 0.** `src/rrx/harness/runner.py` sets `tick_type = "budget_exhausted"` in a branch structurally evaluated before the policy-invocation branch (`if tick_type == TICK_WAKEUP: ... proposal = policy(view)`), so a budget-exhausted tick cannot reach the policy call by direct control-flow structure — confirmed by re-reading the source this session. `tests/test_gate_rules.py::test_r5_rejects_contact_when_budget_exhausted` — **PASSED** this session — tests the *gate's own* defensive R5 rule in isolation, bypassing the runner entirely; it is not a spy-on-policy-callable test through the real runner. **No such dedicated test exists in the current suite** (`grep -rn "budget_exhausted" tests/` finds references in assertions and fixtures, no test that mocks the policy callable and asserts zero invocations specifically for a budget-exhausted tick). Classification: **structurally handled, not runtime-tested.**

**F. Mid-episode state change / stale state — SPECIFIED, ARCHITECTURALLY UNREACHABLE, NOT IMPLEMENTED. Independently re-verified, not merely re-quoted.** `tests/test_stale_state_unreachable.py` (3 tests, **all PASSED** this session): `test_no_source_file_ever_assigns_stale_state_as_a_fallback_reason` (AST-walks source, confirms `"stale_state"` is never assigned as a live value), `test_view_passed_to_the_gate_is_the_identical_object_the_policy_saw` (runs 50 real dev episodes, confirms object identity), `test_nothing_executes_between_the_policy_call_and_the_gate_call_in_source`. This is not a runtime demonstration of the injection→fallback→ledger sequence — it is three separate proofs that the sequence **cannot currently occur** in `sim-v1`. Per the stage's instruction, this audit does **not** attempt to fix this — it is reported as-is.

**Summary table for §7:**

| Mode | Classification |
|---|---|
| A. API timeout | TESTED |
| B. Unparseable LLM output | TESTED |
| C. Schema violation | TESTED |
| D. Gate rejection | TESTED |
| E. Budget exhaustion | STRUCTURALLY HANDLED, NOT RUNTIME-TESTED |
| F. Mid-episode state change | SPECIFIED, ARCHITECTURALLY UNREACHABLE, NOT IMPLEMENTED |

## 8. AI / LLM evidence

**Classification: PASS WITH LIMITATION for dev evidence; NOT APPLICABLE / EXCLUDED BY DESIGN for holdout.**

**What is actually AI-powered in the submitted system, stated plainly:**
**A3-D — the arm that ran on `holdout` and is the subject of every
`RESULTS.md` verdict — is NOT an LLM agent. It is a pure, deterministic,
16-rule decision table** (`src/rrx/agent/policy.py`), with no network
call, no randomness beyond the shared CRN substreams, and (confirmed
again this session) `llm_cost_inr=0.0` on every A3-D holdout record.
**A3-LLM is the actual LLM-integrated arm** (`gpt-5-mini`, via
`src/rrx/agent/openai_client.py`/`planner.py`), and it **never ran on
holdout at all** — excluded entirely, for a pre-declared budget reason
(`EVAL.md §7.1` item A), before any holdout access.

| Claim | Evidence status |
|---|---|
| A3-LLM completed dev evidence | **EVIDENCED.** GPT-C1–C6, each N=500, dev seeds 1000–1499. `results/tuning_log.md` Entry 4. GPT-C6's ledger independently inspected this audit's predecessor session: 2,038/2,038 wakeup ticks carry non-null `raw_output`, real `latency_ms` (e.g. 8,669ms), `model_version="gpt-5-mini"`. |
| Actual model version | `gpt-5-mini` (snapshot `gpt-5-mini-2025-08-07`), recorded in every A3-LLM `manifest.json`/ledger record. |
| Actual raw outputs | Present, non-null, per-tick (`raw_output` field). |
| Model metadata | `model_version`, `tokens_in`, `tokens_out`, `latency_ms` all populated. |
| Prompt hashes | `prompt_hash` populated per tick. |
| Fallback behavior | Verified via §7 A–D above, all TESTED. |
| A3-LLM holdout status | **EXCLUDED ENTIRELY.** No A3-LLM holdout figure exists, and none may be inferred (`EVAL.md §7.1` item A, `RESULTS.md §3A` criterion 4). |
| GPT-C1–C6 evidence | All six cells completed at N=500 (`results/tuning_log.md` Entry 4). One prior interrupted run (`gpt-c6-...-01`, 164/500) is preserved as defect provenance, explicitly excluded from the official comparison. |
| GPT-C2 full-N confirmation | **NOT EXECUTED.** `EVAL.md §7.1` item B.1: the prescribed N=2,000 confirmation run was never performed; GPT-C2's selection rests on N=500 evidence only. |
| Nondeterminism repeats | **NOT EXECUTED.** `EVAL.md §7.1` item B.2: the three prescribed repeat runs were never performed; this project holds **no** A3-LLM run-to-run variance evidence. |

**Submission-safety check, stated explicitly per the stage's instruction:**
No artifact in this repository claims A3-LLM was holdout-validated
(re-confirmed this session: `RESULTS.md §3A` criteria 4/5 explicitly
mark A3-LLM's absence as N/A-by-design, not silently omitted). No
artifact describes A3-D as an LLM or AI-reasoning agent — `ARCHITECTURE.md §4`
explicitly states "no network call, no randomness beyond the CRN
substreams." **The one risk**: `docs/PITCH.md` does not mention A3-LLM
anywhere in its nine sections (confirmed this session by a full re-read)
— the pitch's entire "what we tested" narrative is A0/A1/A2-strengthened/A3-D/A4.
This is safe in the sense that it cannot overclaim about an unvalidated
arm it never mentions, but it also means the pitch, as currently
written, does not showcase the actual LLM integration work at all for an
"AI Buildathon" submission — a narrative choice worth the team's
attention, not a factual error.

## 9. Reproducibility

**Classification: PASS WITH LIMITATION.**

- **Git state:** HEAD `ecc857b` (before this document), clean working
  tree at audit start (`git status --short` confirmed empty this
  session). All tags re-verified this session by **dereferencing
  annotated tags to their commit objects** (`git rev-parse <tag>^{commit}`,
  not the bare tag object hash, which returned different-looking but
  non-contradictory values on a first, incorrect pass this session —
  corrected before drawing any conclusion): `code-freeze-holdout` →
  `4d45db461943978637673a5611a429e0fe826065`, `holdout-run-4d45db461943-sealed`
  → `2d451088ef5105b5075b5f4990803da5230e00bb`, `eval-spec-v1.10` →
  `125eae8841562f6d5eccab58e055400340e71af6` — all **exactly match**
  every prior document's citation. **No tag has moved.**
- **Deterministic seeds:** `MASTER_SEED=20260825`,
  `BOOTSTRAP_SEED=20260826`, unchanged, confirmed in source this session.
- **Result manifests:** present for every run inspected this audit
  series (`manifest.json`, 11-field schema).
- **Test suite, re-run this session:** `python -m pytest -q` →
  **2,284 passed, 1 failed** (`tests/test_stage5_falsification.py::test_1_policy_ordering`,
  the same pre-existing, documented, byte-identical rejection cited in
  `CHANGELOG.md` since before A3-D existed — **not a regression**,
  confirmed identical to Stage 0's count). CI (`.github/workflows/ci.yml`)
  correctly excludes this file from its blocking test step and runs it
  separately as a non-blocking, documented diagnostic (`continue-on-error: true`).
- **Lint, re-run this session — NEW FINDING, not present at Stage 0:**
  `python -m ruff check .` → **44 errors, all in three Day 9 diagnostic
  scripts** (`scripts/day9_frontier.py`: 17, `scripts/day9_mechanism_attribution.py`:
  14, `scripts/day9_decompose.py`: 13 — 43 line-length (`E501`), 1 unused
  import (`F401`)). **Zero errors in `src/` or `tests/`.** `.github/workflows/ci.yml`'s
  "Run Ruff" step runs `ruff check .` with no path restriction — **CI
  would currently fail on this step**, entirely due to this audit
  series' own diagnostic tooling, not any production or evaluation
  code. This is a genuine, current, previously-unreported finding. Per
  this stage's audit-only mandate, it is **reported, not fixed**.
- **Documented reproduction command mismatch (pre-existing, re-confirmed
  unchanged):** `EVAL.md §6` states "Reproducible via `make eval
  RUN=<run_id>`." `Makefile`'s `eval` target does not accept or forward a
  `RUN` variable; `rrx.eval.runner.main()` has no CLI argument parsing.
  Confirmed still true this session (`Makefile`, `src/rrx/eval/runner.py`
  unchanged since `LIMITATIONS.md §4.2` documented this).
- **Holdout execution command:** `python scripts/run_holdout.py --i-have-authorized-the-holdout`
  — guarded, tag-verified, matches `results/holdout_runs.md`'s record
  exactly.

## 10. Safety invariants

**Classification: PASS — IMPLEMENTED + EVIDENCED, across dev, holdout,
stress, and the Stage 4 frontier.**

| Split | Artifact | Result |
|---|---|---|
| `dev` | `results/a3d-dev-20260828-01/metrics.json` | All 8 invariants zero |
| `holdout` | `results/holdout/4d45db461943/a3_d/metrics.json`, re-checksummed this session (`SHA256SUMS`, all 21 files `OK`) | All 8 invariants zero |
| `stress` | `results/stress-20260829-a3d/metrics.json`, re-read this session | All 8 invariants zero; `audit_coverage.ok=true`, 300/300 |
| Day 9 Stage 4 frontier (7 dev threshold points, not an official split) | `results/day9_frontier/threshold_{1..7}.json`, re-read this session | All 8 invariants zero at **every** tested threshold |

This is not a repetition of `RESULTS.md`'s `PASS` — every row above was
independently re-opened and re-read this session, not assumed.

## 11. Experimental integrity

**Classification: PASS, clean.**

- **Holdout frozen and preserved:** the single sealed run
  (`results/holdout/4d45db461943/`) is unmodified — re-verified by
  checksum this session, both before and after every Day 9 diagnostic
  stage's execution (per each stage's own commit history).
- **No A3.1 holdout result exists:** confirmed — `grep -rn "A3\.1\|a3_1"`
  across the repository finds zero occurrences outside this audit
  series' own explicit statements that A3.1 was never created (`CHANGELOG.md`,
  `docs/analysis/DAY9-FRONTIER.md`).
- **Stage 4 remained dev-only:** confirmed — `scripts/day9_frontier.py`
  contains no reference to `holdout_indices` (re-`grep`-verified this
  session), only `dev_indices`.
- **Day 9 diagnostics did not modify holdout artifacts:** confirmed by
  re-running `sha256sum -c SHA256SUMS` this session — all 21 files `OK`.
- **SHA256 seals remain valid:** confirmed, same check.

## 12. Documentation consistency

**Classification: No outright contradictions found. Several
staleness/omission gaps found (documents predate Day 9 and do not yet
reflect Day 9 findings — this is expected staleness, not a factual
error, since Day 9 postdates all of them).**

- `RESULTS.md`, `docs/PITCH.md`, `ARCHITECTURE.md` all state A3-D's
  holdout failure plainly and consistently — no document anywhere
  claims A3-D passed criterion 2. Re-confirmed by full re-read this
  session.
- No document claims A3-LLM was holdout-validated (§8 above).
- **Day 9 findings (Stages 1–4) are not yet reflected in `LIMITATIONS.md`,
  `RESULTS.md`, `ARCHITECTURE.md`, or `docs/PITCH.md`** — none of those
  documents mention the Stage 4 dev-only non-dominated-threshold finding,
  the R-16 `DESIGN-AMBIGUOUS` adjudication, or the Stage 2/3 mechanism
  decomposition. This is **staleness by chronology** (those documents
  were last substantively touched at or before commit `ba6f3c1`,
  predating every Day 9 stage), not a contradiction — nothing in them
  asserts something Day 9 disproves. Per this stage's explicit
  instruction, these documents are **not rewritten** here; the gap is
  reported only.
- `results/sensitivity.md` — re-confirmed this session, still 0/26
  cells complete, consistent with `LIMITATIONS.md §3.3`'s claim.
- No document overclaims sensitivity, A3-LLM's N=500 status, or the
  frontier result — because the frontier result did not exist in any
  document prior to this Day 9 series, there is nothing to contradict.

## 13. Submission artifacts

| Artifact | Status |
|---|---|
| Pitch/demo script | **PRESENT.** `docs/PITCH.md`, 9 sections plus a 5-step demo script, re-read in full this session. Honest, matches `RESULTS.md` exactly. |
| Architecture explanation | **PRESENT.** `ARCHITECTURE.md`, 221 lines, re-read in full this session — thorough, internally consistent, cites the known `run_params.json` defect accurately. |
| Architecture diagram | **PARTIAL — re-classified this session, more precisely than Stage 0's finding.** Stage 0 reported "no architecture image/vector artifact exists," which remains true (`find` for `*.png`/`*.svg`/`*.drawio`/`*.mmd` still returns nothing). **However, `ARCHITECTURE.md §9` does contain a text-based ASCII box diagram** (re-read this session, lines 179–221) — a real, if not graphical, diagram artifact. Corrected classification: no image/vector diagram; a text diagram does exist. |
| README | **EMPTY. SUBMISSION BLOCKER.** `README.md` is 0 bytes, and has been since its first commit (`e362985`, "Set up project skeleton") — confirmed this session via `git log --all -- README.md` (one commit, the initial empty scaffold) and direct read (empty-file warning). For a submission whose other documentation (`ARCHITECTURE.md`, `docs/PITCH.md`, `RESULTS.md`) is unusually thorough, an empty top-level `README.md` is the single most visible gap a reviewer will hit first. |
| Results | **PRESENT.** `RESULTS.md`, thorough, criterion-by-criterion, sealed-artifact-sourced. |
| Limitations | **PRESENT.** `LIMITATIONS.md`, thorough, five-category taxonomy, re-confirmed accurate (if not yet Day-9-updated) this session. |
| Reproducibility instructions | **PRESENT WITH KNOWN DEFECT.** `EVAL.md §6`'s documented `make eval RUN=<run_id>` command does not work as written (§9 above) — a pre-existing, previously disclosed defect, unchanged. |
| Evidence artifacts | **PRESENT.** Sealed holdout directory, checksums, audit sample, tuning log, manifests — all independently re-verified this session. |

## 14. Open issues and severity

| # | Issue | Classification |
|---|---|---|
| 1 | Missing `eval-spec-v1.11` tag/changelog entry | **Minor process issue, already adequately disclosed.** `docs/DAY8-FREEZE-CONFLICT.md` investigated this fully; concluded narrative-only, no numeric/methodological effect. Re-confirmed this session: still no `v1.11` tag exists, nothing has changed. |
| 2 | Missing `eval-spec-v1.5` tag | **Minor process issue, not previously investigated in depth.** `CHANGELOG.md` contains a full `eval-spec-v1.5` entry with no corresponding tag. Not adjudicated by any prior Day 8/9 document. Flagged here as a genuinely open, unresolved item — narrower in scope than issue 1 (no committed investigation exists for it). |
| 3 | Holdout `run_params.json` metadata defect (`policy: "<unknown>"`) | **Already adequately disclosed.** `RESULTS.md §13`, `ARCHITECTURE.md §8` both state it plainly, with root cause and confirmation it doesn't affect any number. |
| 4 | GPT-C1–C6 methodology-integrity issue (authorization ambiguity vs. the original N=6 budget) | **Significant limitation, already adequately disclosed.** `LIMITATIONS.md §4.1` states this plainly and precisely — unresolved, not hidden. |
| 5 | A3-LLM N=500-only evidence, no full-N confirmation, no nondeterminism repeats | **Significant limitation, already adequately disclosed.** `EVAL.md §7.1` items B.1/B.2, `LIMITATIONS.md §3.1`. |
| 6 | Sensitivity analysis 0/26 | **Significant limitation, already adequately disclosed.** `results/sensitivity.md`, `LIMITATIONS.md §3.3`. Re-confirmed unchanged this session. |
| 7 | R-16 `ambiguous_decline` day-3 `DESIGN-AMBIGUOUS` case | **Minor, newly disclosed this Day 9 series (Stage 4).** Not yet reflected in `LIMITATIONS.md` — a real, small (285/8,045 ticks, 3.5%) open design question, not a submission blocker. |
| 8 | Budget-exhaustion lacks dedicated runtime negative test | **Minor, already adequately disclosed.** `LIMITATIONS.md §2.2` states this precisely; independently re-confirmed this session (§7E above). |
| 9 | Stale-state specified-but-not-implemented | **Significant limitation, already adequately disclosed, and architecturally hard to close.** `LIMITATIONS.md §2.3`; independently re-confirmed this session (§7F above). Closing it requires a `sim-v1` architecture change (giving the gate independent live-state access), explicitly out of scope for any Day 9 stage. |
| 10 *(new, found this audit)* | Empty `README.md` | **SUBMISSION BLOCKER.** See §13. |
| 11 *(new, found this audit)* | `ruff check .` currently fails (44 errors, all in Day 9 diagnostic scripts, zero in `src/`/`tests/`) | **Minor process issue, but currently breaks CI's Ruff step.** Not previously disclosed anywhere — Stage 0's "ruff passed" finding is now stale, entirely due to this Day 9 series' own tooling. |

---

## Master requirement table

| Requirement | Status | Evidence | Gap | Submission impact |
|---|---|---|---|---|
| 1. Measured money recovered | **DOCUMENTED ONLY** (rates yes, ₹ aggregate no) | `configs/costs.yaml` (registered, reproducible); `episode_results.jsonl` per-episode `invoice_amount_inr` | No code path sums recovered ₹ into any published metric | Cannot show a headline ₹ figure if asked; rates alone are defensible but weaker for a "revenue recovery" track |
| 2. Escalation / action control (R1–R8) | **PASS — IMPLEMENTED + EVIDENCED** | `src/rrx/agent/gate.py`; 14/14 `test_gate_rules.py` + 10/10 `test_executor_mapping_enforcement.py`, all re-run PASSED this session; sealed holdout `metrics.json` all-zero, re-checksummed | None | None |
| 3. Stopping rules | **PASS WITH LIMITATION** | STOP/retry-window/cancelled-at-open/gate-rejection all directly evidenced; budget exhaustion structural-only | Budget exhaustion lacks dedicated runtime negative test (item 8) | Minor — structural correctness is real, just not independently runtime-proven |
| 4. Audit trail | **PASS WITH LIMITATION** | `results/audit_sample/`, 561 real records, mechanically selected; structured `rationale`/`reason_code`/`gate_verdict` fields | Sample cannot demonstrate rare gate-rejection/fallback paths by construction (A3-D is gate-compliant); that coverage lives in the separate test suite instead | None if both artifacts are presented together; a risk only if the audit sample is presented alone as "complete coverage" |
| 5. Failure handling (A–F) | **PASS WITH LIMITATION** | A–D: TESTED, all re-run PASSED this session. E: STRUCTURALLY HANDLED. F: SPECIFIED, ARCHITECTURALLY UNREACHABLE | E lacks a dedicated runtime test; F cannot be runtime-demonstrated in `sim-v1` at all | Both already disclosed in `LIMITATIONS.md`; submission-safe as long as E/F are not described as "tested" |
| 6. AI / LLM evidence | **PASS WITH LIMITATION** (dev); **NOT APPLICABLE** (holdout, by design) | GPT-C1–C6 real ledgers with `raw_output`/`latency_ms`/`model_version`; A3-D confirmed non-LLM (`llm_cost_inr=0.0` always) | No full-N=2000 confirmation, no nondeterminism repeats, no holdout run for A3-LLM (all pre-declared exclusions) | Submission-safe if stated precisely (this repo does); risk only if a reader conflates A3-D with "the AI" |
| 7. Reproducibility | **PASS WITH LIMITATION** | Git/tags/seeds all re-verified exact-match this session; 2,284/2,285 tests passing | `make eval RUN=<run_id>` documented command doesn't work as written; **`ruff check .` currently fails (44 errors, new finding)** | Lint failure would show as a red CI step if reviewed today — easy, low-risk fix, not yet made |
| 8. Safety invariants | **PASS — IMPLEMENTED + EVIDENCED** | All 8 invariants zero on dev, holdout, stress, and all 7 Stage-4 frontier points — every row independently re-opened this session | None | None |
| 9. Experimental integrity | **PASS** | Holdout checksums re-verified before/after every Day 9 stage; no A3.1 anywhere; Stage 4 confirmed dev-only; no tag moved (re-verified with correct annotated-tag dereferencing) | None | None |
| 10. Documentation consistency | **PASS WITH LIMITATION** | No factual contradictions found across README/RESULTS/LIMITATIONS/ARCHITECTURE/PITCH | `LIMITATIONS.md`/`RESULTS.md`/`ARCHITECTURE.md`/`docs/PITCH.md` all predate Day 9 Stages 1–4 and don't yet reflect those findings | Staleness, not error; low impact, worth a future update pass |
| 11. Submission artifacts | **PASS WITH LIMITATION** | Pitch, architecture doc + text diagram, results, limitations all present and thorough | **`README.md` is empty — SUBMISSION BLOCKER**; no image/vector architecture diagram (text diagram exists) | README gap is the single most visible issue an external reviewer would hit first |

---

## Final report

**1. Overall submission status: READY WITH DISCLOSED LIMITATIONS** —
contingent on closing item 10 (empty `README.md`), which this audit
classifies as an actual **SUBMISSION BLOCKER**, not a limitation. Every
other open item is either already disclosed adequately or minor.

**2. Submission blockers:**
- Empty `README.md` (item 10). This is the one item on this list that
  should not simply be "disclosed" — it needs actual content before
  submission, since it is the first thing most reviewers open.

**3. Evidence gaps:**
- No aggregate ₹ recovered figure anywhere (§3) — real, but the
  underlying accounting is sound and the gap is precisely scoped (a new
  metric definition, not a missing capability).
- Budget-exhaustion and stale-state failure modes lack full runtime
  proof (§7E/F) — both already disclosed in `LIMITATIONS.md`, both
  independently re-confirmed this session, neither newly discovered.

**4. Documentation inconsistencies:** **None found that are factual
contradictions.** The only gap is chronological staleness — `LIMITATIONS.md`,
`RESULTS.md`, `ARCHITECTURE.md`, and `docs/PITCH.md` all predate Day 9
Stages 1–4 and do not yet mention their findings. Nothing in them is
false as a result; they are simply incomplete relative to the newest
evidence.

**5. Is ₹ recovered currently defensible?** **No, not as a headline
number.** The registered cost model and per-episode invoice-amount data
are real and reproducible, but no artifact currently aggregates them
into a ₹ recovered figure. `docs/analysis/DAY9-NET-VALUE.md`'s
break-even analysis is the closest artifact, and it is explicit that its
inputs are labeled assumptions, not measurements.

**6. Is failure handling sufficiently evidenced?** **Yes, for 4 of 6
sub-modes (A–D, all directly tested this session); the remaining 2 (E, F)
are honestly and precisely classified as structurally-handled/architecturally-unreachable
rather than tested — which is itself defensible, submission-safe framing
as long as it is stated that way and not rounded up to "tested."** This
repository already states it that way, and this audit independently
confirms the classification is accurate.

**7. Is the AI/LLM story submission-safe?** **Yes, factually.** No
document overclaims A3-D as an LLM agent or A3-LLM as holdout-validated.
The one narrative risk is that `docs/PITCH.md` doesn't mention A3-LLM at
all, which is safe but may undersell the project's actual AI-integration
work for an AI-track submission — a framing choice for the team, not a
correctness issue.

**8. Is reproducibility clean?** **Mostly.** Git/tag/seed state is
exactly as documented (re-verified, including correcting an
annotated-tag dereferencing mistake mid-audit before concluding anything
from it). The test suite is unchanged and healthy (2,284/2,285). **Lint
is currently broken** (44 new errors, entirely in this Day 9 series' own
diagnostic scripts, zero in production code) — a genuine, previously
unreported, easily-scoped finding.

**9. Recommended next action:** two small, well-scoped fixes, both
outside this stage's audit-only mandate and therefore not made here:
(a) write `README.md` — treat this as the actual submission blocker it
is; (b) run `ruff check . --fix` (or manually wrap long lines) on the
three `scripts/day9_*.py` files to restore a clean CI Ruff step — this
touches only this audit series' own diagnostic tooling, not any
production or evaluation-locked file, so it should be low-risk to
authorize separately. Neither is done in this stage.
