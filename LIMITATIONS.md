# RR-X — Limitations

This document is an honest record of the limitations, gaps, and
unresolved questions in the **current** state of this repository. It
distinguishes five different kinds of statement, and readers should not
collapse them into one another:

1. **Limitations of the experimental setup itself** (e.g., evaluating
   inside a frozen simulator rather than production).
2. **Behavior that is specified but not implemented** (exists in
   `EVAL.md`/`docs/A3-DESIGN.md` text, has no corresponding code path).
3. **Behavior that is implemented but incompletely tested** (the code
   exists and is structurally sound, but a specific negative/runtime
   proof is missing).
4. **Current execution status** (what has and has not actually been run
   yet, as of this writing).
5. **Repository/evaluation-process issues** (documentation that no
   longer matches implementation, methodology changes made outside the
   project's own amendment process).

Every claim below was checked against the repository as it currently
stands, not against an earlier design intent. Where a status could not
be established from current evidence, this document says so rather than
guessing.

---

## 1. Frozen Simulator and Generalization

RR-X's agent, gate, executor, and every comparator arm (A0/A1/A2-family/
A3-D/A3-LLM/A4) are evaluated entirely inside `sim-v1`, a frozen,
synthetic simulator (`src/rrx/sim/`, frozen at commit `bbfa55d`) driven
by `configs/population.yaml`/`configs/episode.yaml`/`configs/costs.yaml`
and `data/decline_codes.yaml`. No live Razorpay transaction, real
customer, or production data is used anywhere in training, tuning, or
evaluation.

This means the results this project produces:

- Establish evidence **within the defined evaluation population and
  simulator mechanics** described by `EVAL.md §1`–`§3` — a specific,
  pre-registered set of decline-code buckets, latent-state dynamics, and
  cost assumptions.
- Do **not** automatically establish production performance. The
  simulator's latent-state model, response propensities, and cost
  figures are `[MODEL]`/`[DESIGN]`/`[CITE]`-tagged assumptions (per
  `EVAL.md`'s own provenance-tier convention, `EVAL.md §0`), not
  measurements of real customer behavior.
- Do **not** establish universal superiority of LLM-based planning over
  rule-based baselines — only a specific comparison, under this
  simulator's specific mechanics, against this project's specific
  bounded-arm comparator set (`EVAL.md §7` criterion 2: `{A0, A1, A2}`).
- Leave simulator-to-production generalization as an **open question**
  this project does not attempt to close. Whatever a holdout result
  eventually shows, it is a statement about `sim-v1`, not about
  Razorpay's live payment-recovery environment.

**Evidence:** `EVAL.md §1`–`§3` (population/simulator definition);
`src/rrx/sim/` (frozen, `sim-v1`); `CLAUDE.md §7` (test-mode-only,
synthetic-data-only project constraint).

---

## 2. Failure-Handling Coverage

`docs/A3-DESIGN.md §19` pre-registers three failure-injection modes for
the A3-LLM planner. Their evidence status is **not uniform** — one
sub-case is specified but structurally unreachable, and one has weaker
test coverage than the others. Both distinctions are made explicit
below rather than folded into a single "failure handling is tested"
claim.

### 2.1 Verified failure paths

The following `fallback_reason` values are genuinely exercised
end-to-end: a synthetic LLM client injects the failure condition, the
real `rrx.harness.runner.run_episode_a3` runner executes it, the
deterministic A3-D fallback fires, and an actual emitted `LedgerRecord`
is inspected and asserted on.

| `fallback_reason` | Injection mechanism | End-to-end test |
|---|---|---|
| `timeout` | `StubLLMClient(raises=PlannerTimeoutError(...))` | `tests/test_a3_llm_forced_failure_parity.py::test_forced_timeout_a3_llm_reproduces_a3d_over_the_full_dev_split` |
| `unparseable` | `StubLLMClient(response="this is not json at all")` | `tests/test_planner_fallback_ledger.py::test_b_unparseable_fallback_reaches_the_ledger` |
| `schema_violation` | Valid JSON, out-of-enum `reason_code` | `tests/test_planner_fallback_ledger.py::test_c_schema_violation_fallback_reaches_the_ledger` |
| `gate_rejected` | Syntactically/schema-valid but gate-rejected (R4) proposal | `tests/test_gate_rejection_fallback.py::test_gate_rejected_llm_proposal_falls_back_to_a3d_end_to_end` |

All four tests run through the real `run_episode_a3` runner (not a
direct handler call) and pass as of this writing.

**Evidence:** `src/rrx/agent/planner.py:242-352` (`invoke_planner`);
`src/rrx/harness/runner.py:280-331` (gate-rejection fallback hook);
`tests/test_planner_fallback_ledger.py`, `tests/test_gate_rejection_fallback.py`,
`tests/test_a3_llm_forced_failure_parity.py` (full pass).

### 2.2 Budget exhaustion test coverage

**Implementation: structurally enforced.** When `view.budget_remaining
== 0`, the runner sets `tick_type = "budget_exhausted"` in an `elif`
branch that is evaluated *before* the code path that would call the
policy (`if tick_type == TICK_WAKEUP: ... proposal = policy(view)`).
Because `tick_type` can only hold one value, the policy call is
unreachable on a budget-exhausted tick by direct control-flow structure,
not by a runtime check that could be bypassed. The tick still produces
exactly one ledger record (`tick_type="budget_exhausted"`, `proposal`
and `gate_verdict` both `None`).

**Test evidence: a dedicated negative planner-not-called test is
absent.** No test in the current suite wraps the `policy` callable in a
spy/mock and asserts zero invocations specifically for a
budget-exhausted tick through the real runner. The closest existing
coverage is `tests/test_gate_rules.py::test_r5_rejects_contact_when_budget_exhausted`,
which tests the gate's own defensive R5 rule in isolation (bypassing the
runner entirely), and a comment in `tests/test_a3d_policy.py` that
records the assumption (`REACHABLE_BUDGETS = (1, 2, 3)`) without
independently verifying it against a live run.

Do not read this as "budget exhaustion is unimplemented" — the
enforcement is real and verifiable by direct code reading. It is
specifically the *dedicated runtime proof* that is missing.

**Evidence:** `src/rrx/harness/runner.py:217-222,243` (tick_type
assignment and wakeup-gated policy call); `tests/test_gate_rules.py:129`
(`test_r5_rejects_contact_when_budget_exhausted`);
`tests/test_a3d_policy.py:70-72` (documented assumption, not an
independent proof).

### 2.3 Mid-episode stale-state path

**Classification: SPECIFIED BUT NOT IMPLEMENTED IN sim-v1.**

`docs/A3-DESIGN.md §19` specifies a third failure mode: a subscription's
state changing mid-episode between prompt-build time and gate-evaluation
time, which should produce `fallback_reason="stale_state"`. This
requires the gate to inspect the simulator's *current* live state
separately from the `EpisodeView` snapshot the policy already saw.

The current `evaluate_gate` signature is:

```python
def evaluate_gate(
    proposal: Proposal, view: EpisodeView, *, send_hour: str = AGENT_SEND_HOUR
) -> GateVerdict:
```

It receives only the same frozen `EpisodeView` the policy was called
with — no separate live-state parameter, and no second read of
`state.subscription_state` exists anywhere in the gate or runner. As a
structural consequence, no implemented code path can currently produce
`stale_state`:

- **Static proof:** `tests/test_stale_state_unreachable.py::test_no_source_file_ever_assigns_stale_state_as_a_fallback_reason`
  AST-walks `runner.py`/`planner.py`/`ledger.py` and confirms
  `"stale_state"` is never assigned as a live value anywhere — it exists
  only in comments/docstrings and as a defined member of the
  `fallback_reason` enum.
- **Runtime proof:** `tests/test_stale_state_unreachable.py::test_view_passed_to_the_gate_is_the_identical_object_the_policy_saw`
  runs 50 real dev episodes and confirms the object identity of `view`
  is unchanged between the policy call and the gate call, every time.
- **Source-adjacency proof:** `tests/test_stale_state_unreachable.py::test_nothing_executes_between_the_policy_call_and_the_gate_call_in_source`
  confirms no statement in `runner.py` sits between `proposal =
  policy(view)` and `gate_verdict = gate(proposal, view)` that could
  mutate state in between.

This is not a runtime-tested failure path with a passing test that
demonstrates the injection → fallback → ledger sequence — it is the
opposite: three separate proofs that the sequence cannot currently
occur. `sim-v1`'s day loop is single-threaded and fully synchronous,
with no wall-clock or concurrency model, so there is currently no
mechanism by which `subscription_state` could diverge between
view-construction and gate-evaluation. **This matters because the
current system cannot demonstrate the §19 stale-state injection path
until the gate/evaluation architecture is extended to give the gate
independent access to current simulator state — a change to the
architecture, not just a new test.**

**Evidence:** `src/rrx/agent/gate.py:72-74` (`evaluate_gate` signature);
`tests/test_stale_state_unreachable.py:45-111` (all three proofs, full
file); `docs/A3-DESIGN.md §19` (specification).

---

## 3. Evaluation Status

### 3.1 Configuration selection

A provisional A3-LLM configuration selection **has** been made and
recorded, but with an explicit scope limitation the repository itself
states plainly. `results/tuning_log.md` Entry 4 ("Day 6 final closure:
GPT-C1–C6 tuning complete, GPT-C2 selected (PROVISIONAL)") records that
applying the pre-registered lexicographic selection rule to the six
completed GPT-C1–C6 results (each N=500, dev seeds 1000–1499) selects
**GPT-C2** (`reasoning_effort=minimal`, `disclosure=high`,
`verbosity=low`) on highest subscription rescue rate (0.544), no tie.

The entry itself, and this document, are explicit that this selection
is **not** a completed evaluation result:

- Selection is based on **N=500 DEV evidence only** — the full N=2,000
  DEV confirmation run that `docs/A3-DESIGN.md §18` prescribes for the
  selected configuration has **not** been executed.
- GPT-C2 must not be described as full-DEV validated.
- Holdout has not been accessed for selection or for anything else (see
  §3.2).
- The selection itself sits on top of an unresolved methodology
  question about whether the GPT-C1–C6 matrix it was drawn from is
  authorized tuning evidence at all — see §4.1. This document does not
  repeat that analysis here beyond flagging the dependency.

**Evidence:** `results/tuning_log.md`, Entry 4 (committed at commit
`26ba176`, "Complete Day 6 GPT tuning and select C2");
`docs/A3-DESIGN.md §18` (full-dev confirmation requirement for the
selected configuration).

### 3.2 Holdout

**Method (as specified):** `EVAL.md §3.5` defines `holdout` as N=2,000
episodes, seeds 9,000–10,999, to be used **once per candidate release**,
and only after configuration selection is frozen. `results/holdout_runs.md`
is required to log every holdout run, successful or not.
`src/rrx/harness/splits.py::holdout_indices()` enforces this
procedurally: it raises `HoldoutNotAuthorizedError` unless called with
`authorized=True`, which no code path in this repository currently
does.

**Current status:** holdout has **not yet been run**. `results/holdout_runs.md`
does not exist in the repository. No holdout data has been inspected,
loaded, or referenced by any tuning or selection artifact found in this
repository. `tests/test_holdout_guard_intact.py` exercises only the
refusal path (`holdout_indices()` without authorization raises) and
never calls `authorized=True`.

Do not read the method description above as implying a holdout result
exists — it does not. The method and the current execution status are
two different facts, both stated here so they are not conflated.

**Evidence:** `EVAL.md §3.5`; `src/rrx/harness/splits.py:50-62`
(`holdout_indices`, `HoldoutNotAuthorizedError`); `tests/test_holdout_guard_intact.py`
(refusal-path-only coverage); absence of `results/holdout_runs.md`
(confirmed by direct filesystem check).

### 3.3 Sensitivity analysis

`results/sensitivity.md` currently shows **0 / 26 cells complete**
("PENDING" in every `invoice CI`/`rescue CI`/`win` column, "Cells won:
PENDING / 26. Pass mark 21."). No sweep has been run for any arm at any
sweep cell as of this writing. `EVAL.md §6A` pre-registers a
contingency for reduced sweep scope if the full 26-cell sweep proves
cost-prohibitive, but no such reduction has been declared in
`results/sensitivity.md` — the file simply has not been populated yet.

This is not evidence that sensitivity analysis is unnecessary or
optional for this project — `EVAL.md §6A` requires it, and the pass
threshold (21/26 cells) remains the pre-registered bar. It is simply
not yet done.

**Evidence:** `results/sensitivity.md` (full file, "PENDING" in every
data row); `EVAL.md §6A` (sweep requirement and contingency clause).

### 3.4 Currently unavailable metrics

Two metrics `EVAL.md §5` pre-registers are **not currently computable**
from any existing run artifact in this repository:

- **Median and p90 time-to-rescue.** `rrx.eval.runner.UNAVAILABLE_METRICS["median_time_to_rescue_days"]`
  states plainly that `EpisodeResult` (the frozen dataclass every arm's
  runner returns) carries no day-of-outcome field for any arm — this
  metric would require either extending that frozen dataclass or
  re-simulating every episode once per day, neither of which has been
  done.
- **Regime-A net value.** `rrx.eval.runner.UNAVAILABLE_METRICS["regime_a_net_value"]`
  states that `EVAL.md §3.3`'s cancellation-hazard valuation mechanic is
  "not implemented anywhere in `src/rrx/sim/`" — `src/rrx/sim/latent.py`'s
  own `SUBSTREAM_NAMES` docstring confirms the `cancellation_hazard`
  substream is "declared here for completeness only" and never drawn.

Both metrics should be treated as **unavailable**, not as zero, not
computed, and not silently omitted from any final claim — a reader
should not infer "no cancellation cost" or "no time-to-rescue
difference" from their absence. They are pre-registered but currently
un-produceable from this repository's existing artifacts.

**Evidence:** `src/rrx/eval/runner.py`, `UNAVAILABLE_METRICS` dict
(module-level constant, both entries with their stated reasons);
`src/rrx/sim/latent.py`, `SUBSTREAM_NAMES` docstring.

---

## 4. Methodology Integrity

### 4.1 Additional GPT-C1–C6 tuning matrix

The pre-registered A3-LLM tuning budget, per `EVAL.md §6A` and
`docs/A3-DESIGN.md §18`, is **N = 6 dev configurations**, evaluated on a
500-episode subsample (dev seeds 1000–1499). This repository currently
contains evidence of **two** six-configuration matrices under that same
"N=6" framing:

1. A Gemini-based matrix (`C1`–`C6`), frozen in a committed,
   `CHANGELOG`-referenced commit (`0d49ec1`), of which only `C1`
   completed 9/500 episodes before a provider rate limit stopped it.
2. A GPT-based matrix (`GPT-C1`–`GPT-C6`, provider `gpt-5-mini`), which
   all six cells now completed and which produced the provisional
   selection described in §3.1.

The GPT matrix was defined and committed (`results/tuning_log.md`
Entries 2–4, commit `26ba176`) **without a corresponding `EVAL.md §6A`
text amendment, without a `CHANGELOG.md` entry, and without a spec
version tag** — a departure from this repository's own established
practice for every other prior methodology or budget change (`eval-spec-v1.1`
through `v1.7`, each accompanied by a committed `CHANGELOG.md` entry, an
append-only `EVAL.md` text addition, and in six of seven cases a
matching git tag). `results/tuning_log.md` Entry 2 itself states the two
matrices are "separate, provider-specific experiments" that do not
supersede or replace one another — meaning, on its own text, this is
not a like-for-like substitution within the original six-slot budget,
but an additional one.

**Status, stated precisely:** the GPT-C1–C6 matrix's standing as
official tuning evidence under the frozen `EVAL.md §6A` methodology is
**unresolved and unauthorized as of this writing**, unless and until a
proper `EVAL.md` amendment is made addressing whether it replaces the
Gemini matrix within the existing N=6 budget, or is authorized as an
additional N=6 (making the effective budget N=12), or is treated as
exploratory/diagnostic evidence outside the pre-registered budget
entirely. It must not be silently combined with, or treated as
interchangeable with, the originally authorized N=6 budget without that
amendment.

**This is a methodology-integrity and evidence-provenance issue, not a
finding about model performance.** Nothing here implies GPT-C2 (or any
other GPT cell) performed poorly, unreliably, or incorrectly — the
concern is procedural: which artifacts are entitled to count as the
pre-registered tuning evidence, decided through the same amendment
process every other methodology decision in this repository has gone
through.

**Evidence:** `EVAL.md §6A` (N=6 budget, no provider specified);
`docs/A3-DESIGN.md §18` (same); `results/tuning_log.md` Entries 1–4
(Gemini matrix freeze, GPT matrix definition, GPT-C1 smoke test, final
selection); `CHANGELOG.md` (zero occurrences of "GPT-C", confirmed by
direct search); commit `26ba176` diff (touches `results/tuning_log.md`
and source/test files, does not touch `EVAL.md` or `CHANGELOG.md`).

### 4.2 Evaluation-command mismatch

`EVAL.md §6` states runs are "Reproducible via `make eval RUN=<run_id>`."
The current repository implementation does not support this command as
written:

- `Makefile`'s `eval` target is `python -m rrx.eval.runner` — it does
  not reference a `$(RUN)` make variable or pass any argument through to
  the invoked module.
- `rrx.eval.runner.main()` accepts `run_id` only as a Python function
  parameter, defaulting to the hardcoded constant `RUN_ID =
  "a3d-dev-20260828-01"`; the module implements no `argparse`,
  `sys.argv`, or environment-variable handling that could receive a
  `RUN=<run_id>` value from `make`.
- Separately, `Makefile`'s `sweep` target is `python -m rrx.eval.runner
  --sweep`; `rrx.eval.runner` has no `--sweep` flag or any CLI argument
  handling at all, so this target would fail if invoked as written.

**The documented reproduction command should not be treated as verified
until this is reconciled.** This document does not modify the `Makefile`
or `rrx/eval/runner.py` to fix the mismatch — it only records that it
exists.

**Evidence — documentation location:** `EVAL.md §6`, line containing
"Reproducible via `make eval RUN=<run_id>`." **Evidence — implementation
location:** `Makefile:9-13` (`eval`/`sweep` targets); `src/rrx/eval/runner.py`
`main()` signature (`results_dir: Path | None = None, run_id: str =
RUN_ID, indices: list[int] | None = None` — no CLI parsing).

---

## 5. Information Boundary

The A3-LLM planner is architecturally restricted to an `EpisodeView`
(`src/rrx/features/episode_view.py`), not unrestricted simulator state.
Two distinct layers of protection exist for this boundary, and they
prove different things:

**Import/boundary protection — implemented and tested.**
`rrx.agent` and `rrx.features` never import `rrx.sim` or `rrx.sim.latent`,
directly or transitively. `tests/test_no_latent_leak.py` enforces this
two ways: a static AST check that neither guarded package's source ever
names `rrx.sim`/`rrx.sim.latent`, and a runtime subprocess check that
`rrx.sim.latent` never appears in `sys.modules` after importing
`rrx.agent`/`rrx.features` in a clean process. The same file also
confirms `EpisodeView`/`ContactRecord` expose exactly the field
allowlist `EVAL.md §3.4` specifies (`test_episode_view_field_set_equals_the_allowlist_exactly`,
`test_contact_record_field_set_equals_the_allowlist_exactly`) and no
latent-named dataclass field (`test_episode_view_exposes_no_latent_field`,
`test_contact_record_exposes_no_latent_field`).

**Prompt-content assertion — also implemented and tested, but in a
different file than `docs/A3-DESIGN.md §12` might suggest.**
`docs/A3-DESIGN.md §12` calls for a test that renders a synthetic
`EpisodeView` through the actual prompt and asserts none of
`LATENT_FIELD_NAMES` appear in the rendered string. `test_no_latent_leak.py`
itself does **not** contain this — it checks dataclass field names, not
rendered prompt text. The actual rendered-prompt-content assertion lives
in `tests/test_prompt_rendering.py::test_render_prompt_contains_no_latent_field_name`
(and its sibling `test_render_prompt_contains_no_seed_shaped_token`),
which does construct a synthetic `EpisodeView`, call `render_prompt`,
and assert the forbidden field names are absent from the output string.
`docs/A3-DESIGN.md §12`'s own text still says this test is "Not
implemented in this pass" — that line is stale relative to the current
repository; the test exists, just under a different filename than the
section's own cross-reference names.

**The distinction that matters:** import isolation (no latent object
ever reaches `rrx.agent`) and prompt-content isolation (no latent
*value* appears in the rendered text sent to the LLM) are two separate
guarantees, verified by two separate tests in two separate files. Do
not treat the existence of one as evidence for the other.

**Evidence:** `src/rrx/features/episode_view.py` (the guarded
`EpisodeView` type); `tests/test_no_latent_leak.py:172-183` (import
isolation, static + runtime), `:236-256` (field allowlist), `:259-296`
(no latent field names on the dataclasses); `tests/test_prompt_rendering.py:123-131`
(rendered-prompt-content assertion); `docs/A3-DESIGN.md §12` (stale
"Not implemented in this pass" note).

---

## 6. What the Results Will Not Establish

Independent of any specific number this evaluation eventually produces,
the following are outside what this project's current design and
implementation can support:

- **Production payment-recovery performance.** Every result is a
  statement about `sim-v1`, a synthetic, frozen simulator — not a
  statement about real Razorpay merchants, customers, or transactions
  (§1).
- **A completed holdout verdict.** No holdout run has occurred (§3.2);
  `EVAL.md §7`'s success criteria are adjudicated on holdout only, and
  none of the descriptive DEV-split comparisons produced so far
  constitute or substitute for that determination.
- **A validated final A3-LLM configuration.** The current selection
  (GPT-C2) is provisional, based on N=500 DEV evidence, pending both a
  full N=2,000 DEV confirmation run and the unresolved tuning-budget
  authorization question in §4.1 (§3.1).
- **A completed sensitivity/robustness case.** 0 of 26 pre-registered
  sensitivity cells have been run (§3.3).
- **Monetary net value or time-to-rescue claims.** Both are
  pre-registered metrics currently unavailable from any existing
  artifact, not zero and not favorable by omission (§3.4).
- **A demonstrated mid-episode-state-change failure response.** This
  mode is specified but architecturally unreachable in the current
  simulator; no test or run can currently exercise it (§2.3).
- **Independently verified enforcement of the budget-exhaustion
  guarantee at runtime**, as distinct from its structural correctness by
  code inspection (§2.2).

This document should be read alongside the V1 (architecture), V2
(evaluation design), and V3 (failure-flow) diagrams — it does not modify
or supersede any of them, and none of the above limitations required or
resulted in any change to those diagrams, `EVAL.md`, `docs/A3-DESIGN.md`,
`CHANGELOG.md`, `results/tuning_log.md`, evaluation configuration, source
code, or tests.
