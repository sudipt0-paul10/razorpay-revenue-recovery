# A3-LLM tuning log

Required artifact per `docs/A3-DESIGN.md §18` ("Every configuration tried,
including losing ones, is recorded in `results/tuning_log.md`") and
`EVAL.md §6A`. This file did not exist before this entry (confirmed by
`git log --all -- results/tuning_log.md`, no history).

---

## Entry 1 — Day 6 Stage 6E-Amendment: freezing the six A3-LLM configuration contents

**Status: an explicit Day-6 methodological amendment, not a recovered
historical specification.** This entry does not claim `eval-spec-v1.7`
ever defined C1–C6's content — it did not, and this entry says so
plainly.

### The omission this entry resolves

`docs/A3-DESIGN.md §18` ("Pre-registered tuning and sweep") establishes,
and this entry leaves entirely unchanged:

- **N = 6** A3-LLM dev configurations (a count).
- **N = 500** DEV episodes per configuration, evaluated on the
  500-episode subsample — **the first 500 `dev` indices, seeds
  1000–1499** — not full `dev`.
- Only the eventually-**selected** configuration is subsequently run on
  full `dev` (N=2,000).
- The simulator's own six `[MODEL]`-tagged sweep-grid parameters
  (`configs/model_params.yaml`) are held at **nominal/unperturbed**
  values throughout tuning — a different "six" from the six A3-LLM
  configurations below; not to be conflated with it.

What `§18` never states, anywhere, and what a repository-wide search
(`EVAL.md`, `docs/A3-DESIGN.md`, `CHANGELOG.md`, `configs/model_params.yaml`,
and this file's own prior nonexistence) confirmed absent before this
entry: **what distinguishes configuration 1 from configuration 2 through
6** — no axis of variation (prompt wording, decoding parameters,
anything else) was ever specified. This was identified and reported as a
genuine methodological gap during Day 6 Stage 6E (session record, not a
repository artifact), **before any A3-LLM tuning episode of any
configuration had been run** — `results/` contains no A3-LLM result
directory of any kind at the time of this entry (verified: only
`a0-dev-20260828-01/`, `a1-dev-20260828-01/`, `a2s-dev-20260828-01/`,
`a3d-dev-20260828-01/`, `capture/`, `sensitivity.md` exist).

### The amendment

The following six configurations are now explicitly frozen, **before
observing any tuning outcome**, resolving the gap above:

**Common to all six** (unchanged from `§18`/this entry's own text —
identical across every configuration, no configuration varies these):

| Field | Value |
|---|---|
| Provider | Google Gemini Developer API |
| Model | `gemini-3.1-flash-lite` (Day 6 Stage 6D: confirmed stable/GA via `ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite`, 2026-08-28) |
| `template_version` | `a3-llm-prompt-v1` (`rrx.agent.prompt.TEMPLATE_VERSION`) — identical prompt text across all six |
| Output schema | The frozen 4-key A3-LLM schema (`action_type`, `remedy`, `reason_code`, `rationale`) — identical, `rrx.agent.planner.parse_llm_output` remains sole authority regardless of any provider-side structured-output request |
| Simulator parameters | Nominal (unperturbed sweep grid) |
| A3-D fallback / gate / executor | Unmodified — `src/rrx/agent/policy.py`, `src/rrx/agent/gate.py`, `src/rrx/harness/runner.py`'s gate-rejection hook, all exactly as frozen at Stage 6C/6B closure |
| DEV sample | First 500 `dev` indices, **seeds 1000–1499** (`rrx.harness.splits.dev_indices()[:500]`) |
| N | 500 episodes per configuration |

**Varying — the ONLY two parameters that differ across C1–C6:**

| ID | `thinking_level` | `temperature` |
|---|---|---|
| C1 | `minimal` | 0.0 |
| C2 | `low` | 0.0 |
| C3 | `medium` | 0.0 |
| C4 | `minimal` | 1.0 |
| C5 | `low` | 1.0 |
| C6 | `medium` | 1.0 |

`high` thinking level and any parameter beyond `thinking_level`/
`temperature` are deliberately excluded — six configurations, no C7, no
substitutions.

**API mechanism, verified before freezing (not assumed):**
`thinking_level` is a real, current Gemini API parameter — confirmed
2026-08-28 via `ai.google.dev` — set as
`GenerateContentConfig(thinking_config=ThinkingConfig(thinking_level=...))`,
with `minimal`/`low`/`medium`/`high` all valid values for the Gemini 3
model family (default `high` if unspecified, which is exactly why every
one of C1–C6 sets it explicitly rather than relying on the default).
`gemini-3.1-flash-lite` was independently confirmed in Stage 6D to
support the model family's `thinking_level` mechanism generally; this
entry did not find any documented exclusion of `flash-lite` from it.

### Rationale (recorded verbatim as given, not independently re-derived)

This is an explicit methodological amendment, not a claim that v1.7
originally contained these six definitions. The purpose is to resolve
the genuine omission while keeping the tuning space narrow and
interpretable. The six configurations vary only LLM decoding/reasoning
settings; the prompt, model, simulator, policy/gate/executor, schema,
DEV sample, and evaluation machinery remain fixed. `high` thinking level
is excluded because it introduces substantially greater reasoning/latency
cost without being necessary for a compact six-cell design. Temperature
is restricted to 0.0 and 1.0 so the matrix tests the existing
deterministic setting against Gemini 3's documented default temperature.

**This rationale, and the C1–C6 matrix itself, were fixed before any of
the six configurations had been executed and before any tuning outcome
of any kind existed** — including before the Stage 6D 10-episode smoke
test's 10/34 `schema_violation` observation was allowed to influence
this matrix in any way. That observation is recorded (Stage 6D
deliverable, prior session turn) but played no role in selecting
`thinking_level`/`temperature` as the varied axes, nor in choosing
`minimal`/`low`/`medium` over `high`, nor in choosing 0.0/1.0 over any
other temperature pair.

### Selection rule (unchanged — recorded here for completeness, not re-authored)

Established at **Day 6 Stage 6B (Decision 3)** — a session-level
operational decision resolving `§18`'s separate, already-identified gap
(no selection procedure was ever specified either) — **not** itself
`eval-spec-v1.7` document text, and this entry does not claim otherwise:

**Eligibility** — a configuration is eligible only if:
1. Its prescribed 500-episode DEV run completes.
2. It violates no frozen safety invariant (`EVAL.md §5.2`).
3. It respects the frozen contact-budget constraint — **`EVAL.md §2`,
   line 77: "Every arm gets 3 contacts per episode, within 09:00–21:00
   IST, not counting Razorpay's automatic email"** (cross-checked against
   `configs/episode.yaml#/agent_budget/max_contacts_per_episode: 3` and
   `data/decline_codes.yaml#/defaults/global_caps/max_contacts_per_episode: 3`
   — all three agree).
4. It produces valid required artifacts.

**Among eligible configurations, select lexicographically:**
1. Highest subscription rescue rate.
2. If tied, highest invoice recovery rate.
3. If still tied, lowest total contacts.
4. If still exactly tied, lowest configuration ID.

Only already-defined/frozen evaluation metrics are used; no new metric;
no holdout/stress data; no comparison against A3-D as a selection
criterion (A3-D remains the frozen comparator for later DEV/holdout
analysis, not a tie-breaker among C1–C6).

### Freeze-time provenance

| Field | Value |
|---|---|
| Freeze date | 2026-08-28 |
| Repository HEAD at freeze | `7fde138620ce587ae18bd95abe52e71ed75f376a` (tag `eval-spec-v1.7`) |
| `EVAL.md` modified by this entry? | No |
| `SIM.md` modified by this entry? | No |
| `docs/A3-DESIGN.md` modified by this entry? | No |
| `src/rrx/agent/policy.py` modified? | No |
| `src/rrx/agent/gate.py` modified? | No |
| `src/rrx/sim/` modified? | No |
| Holdout accessed? | No — `holdout_indices(authorized=True)` not called |
| Stress accessed? | No — `stress_indices()` not called |
| Tuning results observed before this freeze? | **None — zero A3-LLM configurations had been executed at any sample size before this entry was written** |
| Pricing provenance for any later cost accounting | `ai.google.dev/gemini-api/docs/pricing`, retrieved 2026-08-28: gemini-3.1-flash-lite paid tier $0.25/1M input tokens, $1.50/1M output tokens; actual Free Tier spend is always reported separately as `0.0`, never conflated with the paid-equivalent estimate (Day 6 Stage 6D) |

**No configuration has been executed as of this entry.** Execution
(Stage 6E resumption) is a separate, later step, explicitly not
authorized by this entry alone.

---

## Entry 2 — Day 6 Stage 6H: GPT-5-mini provider-specific tuning methodology

**Status: a provider-specific methodological amendment, appended after
Entry 1. Entry 1 (the Gemini six-cell matrix, its provenance, and its
partial C1 execution record) is unmodified, unrenamed, and not
reinterpreted by this entry — this is an append-only addition.**

### Relationship to Entry 1 — separate experiments, not a replacement

**Gemini C1–C6 and GPT-C1–C6 are separate, provider-specific
experiments.** Stage 6E executed Gemini configuration C1 and stopped at
a confirmed official hard limit: 15 requests/minute for
gemini-3.1-flash-lite's free tier (9/500 episodes completed before the
stop). **That result remains preserved exactly as recorded in Entry 1
and in `results/a3llm-c1-dev500-20260828-01/` — nothing about it is
rewritten, renamed, or reinterpreted by this entry.** The 9 completed
Gemini episodes are explicitly excluded from, and can never be pooled
into, any GPT-based tuning cohort or comparison — they were produced
under a different provider, a different model, and a different prompt
configuration than any GPT-C1–C6 cell, so none of the "identical
prompt/template/model" commonality this project requires across a
configuration set holds between them. **GPT-C1 through GPT-C6, defined
below, are the frozen GPT tuning cells** for any future GPT-based tuning
execution; they do not supersede, extend, or renumber Gemini C1–C6.

### Why the Gemini matrix's parameters do not transfer

**Empirically confirmed (Day 6 Stage 6G.1, one live HTTP request against
`gpt-5-mini`):**

```
POST https://api.openai.com/v1/chat/completions
{"model": "gpt-5-mini", "messages": [...], "temperature": 0.5}

-> HTTP 400
{"error": {"message": "Unsupported value: 'temperature' does not support 0.5
 with this model. Only the default (1) value is supported.",
 "type": "invalid_request_error", "param": "temperature",
 "code": "unsupported_value"}}
```

**Precise finding, stated exactly:** non-default `temperature` values are
unsupported for `gpt-5-mini` — the API accepts only its own default (`1`)
and rejects any other explicit value with a model-specific
`invalid_request_error`. This is not "temperature is rejected outright";
omitting the parameter (letting the default apply) is expected to work,
though that specific case was not itself separately tested. **Because of
this, `temperature` is not usable as a GPT-5-mini experimental axis at
all** — Gemini's `temperature` (0.0 vs 1.0) axis has no GPT-native
counterpart, and the project therefore omits the `temperature` parameter
entirely from every GPT-C1–C6 request rather than passing any explicit
value, default or otherwise.

Separately: `gpt-5-mini`'s `reasoning_effort` parameter is a distinct
provider mechanism from Gemini's `thinking_level`. No claim of behavioral
equivalence between same-named or similarly-named levels across the two
providers is made anywhere in this entry, Entry 1, or the Stage
6G/6G.1/6H reconnaissance that preceded it.

### GPT-native six-cell matrix — frozen

**Empirical probe provenance (Day 6 Stage 6G.1), stated precisely:**
three successful live calls were made against `gpt-5-mini`:

1. `reasoning_effort=minimal`, `verbosity=low`
2. `reasoning_effort=medium`, `verbosity=medium`
3. `reasoning_effort=low`, `verbosity` omitted

All three returned successful, strict-structured-output JSON, with no
malformed or prefixed output observed in any of the three.
**`reasoning_effort=low` combined with `verbosity=low` was NOT itself
directly tested** — call 3 above tested `low` reasoning effort with
verbosity omitted, not set to `low`; this entry does not claim otherwise.

**Scope correction — probe schema provenance.** The probe script
(`gpt_probe.py`, repo root, untracked) that produced these three calls
used a JSON schema with the project's correct four key **names**
(`action_type`, `remedy`, `reason_code`, `rationale`) but **placeholder
enum values, not this project's actual frozen ones** —
`action_type: ["retry","hold","stop"]`,
`remedy: ["none","same_method","alternate_method"]`,
`reason_code: ["insufficient_funds","temporary_failure","hard_decline"]`
— versus the real frozen contract (`CONTACT|WAIT|STOP`;
`card_change|topup_reminder|null`; the real 7-value `reason_code` enum
from `rrx.agent.reason_codes.REASON_CODES`). **What these three calls
empirically validated:** `gpt-5-mini` routing/authentication, strict
Structured Outputs mode functioning end to end, and successful exercise
of the four required JSON key **names**. **What they did NOT validate:**
`gpt-5-mini`'s behavior against this project's actual
`action_type`/`remedy`/`reason_code` enum-value contract — that remains
unverified pending a probe (or smoke test) built against the real schema
values.

| Cell | `reasoning_effort` | prompt `disclosure` |
|---|---|---|
| `GPT-C1` | minimal | low |
| `GPT-C2` | minimal | high |
| `GPT-C3` | low | low |
| `GPT-C4` | low | high |
| `GPT-C5` | medium | low |
| `GPT-C6` | medium | high |

**Provider-qualified cell IDs (`GPT-C1`…`GPT-C6`), not bare `C1`–`C6`** —
deliberately distinct from Gemini's `C1`–`C6` because a Gemini
`a3llm-c1-dev500-20260828-01/` result directory already exists on disk;
reusing bare `C1` would create an ambiguous or colliding run identifier
between two different providers.

**The experimental factors are reasoning effort × prompt disclosure** —
exactly two axes, six cells, matching the original six-configuration
budget exactly. **N = 500 DEV episodes per cell. Dev seeds 1000–1499**
(the same first-500-dev-indices subsample as Entry 1) — the six-cell
count, N, and seed allocation are all preserved unchanged from the
original v1.7-established budget and from Entry 1's own structure.

### Prompt `disclosure` — frozen definitions

Derived entirely from the already-frozen `docs/A3-DESIGN.md §7`
reason_code table, as encoded in
`rrx.agent.reason_codes.ADMISSIBLE_DECLINE_CODES` and
`rrx.agent.reason_codes.TYPICAL_ACTION` — **no new policy content is
invented; both disclosure levels expose only content that already exists
in the frozen codebase.**

**`disclosure=low`:** expose only the existing bare `reason_code` enum
list in the prompt (identical to the current, already-shipped
`rrx.agent.prompt.render_prompt` text — no change to that path). No
mapping from reason codes to typical actions or admissible decline codes
is exposed.

**`disclosure=high`:** expose, for every reason code, its existing
`TYPICAL_ACTION`, its existing sorted `ADMISSIBLE_DECLINE_CODES`, and the
existing `post_halt_rescue` condition requiring
`subscription_state == halted` (present in §7's prose and in
`rrx.agent.planner.parse_llm_output`'s own admissibility check, though
not encoded in the `ADMISSIBLE_DECLINE_CODES` dict itself).

### Fixed parameters — identical across all six GPT-C1–C6 cells

| Field | Value |
|---|---|
| Provider | OpenAI |
| Model | `gpt-5-mini` (snapshot `gpt-5-mini-2025-08-07`) |
| `temperature` | Omitted from every request (model default applies) — not an experimental factor, per the finding above |
| `verbosity` | **`low`**, fixed, for all six cells — **not** an experimental factor |
| Output schema | Unchanged existing four-key strict structured-output schema (`action_type`, `remedy`, `reason_code`, `rationale`) |
| Parser | `rrx.agent.planner.parse_llm_output`, unmodified |
| Fallback taxonomy | Unchanged 5-value set (`timeout`, `unparseable`, `schema_violation`, `gate_rejected`, `stale_state`) |
| Gate | `src/rrx/agent/gate.py`, unmodified |
| Executor | Unmodified |
| Simulator | Unmodified |
| N | 500 per cell |
| Dev seeds | 1000–1499 |

**`verbosity=low` rationale (recorded as given, not independently
re-derived):** verbosity is not a meaningful experimental factor for the
project's primary behavioral metrics and primarily affects output
length/rationale. Fixing it at `low` minimizes unnecessary token
consumption while keeping the experimental focus on reasoning effort and
prompt disclosure.

### Cost provenance

Documented `gpt-5-mini` pricing (CITE:
`developers.openai.com/api/docs/models/gpt-5-mini`, retrieved
2026-08-28): **$0.25 / 1M input tokens, $2.00 / 1M output tokens.** No
six-cell cost estimate is asserted by this entry — no real GPT-5-mini
token-usage data exists yet (the one empirical call made under this
entry's provenance returned an `invalid_request_error`, not a
completion, and produced no usage data). **Actual GPT token usage must
be measured during the experiment itself, particularly because
`reasoning_effort` can change reasoning-token consumption** — GPT-5-family
reasoning models bill internal reasoning tokens as output tokens even
when not shown as visible completion text, so cost cannot be
extrapolated from Gemini's measured workload (a different provider, a
different reasoning mechanism, no reasoning-token overhead in that
figure at all). `configs/costs.yaml` is unchanged by this entry.

### Not yet executed

**No GPT-C1–C6 configuration has been executed as of this entry.**
Execution is a separate, later, explicitly-authorized step. This entry
freezes only the six-cell definition, the fixed parameters, and the
disclosure-level content — nothing about GPT-5-mini tuning outcomes is
known or claimed here.

---

## Entry 3 — Day 6 Stage 6J: GPT-C1 live smoke-test provenance

**Status: a smoke-test provenance record, NOT a tuning result.** This
entry documents a ≤10-episode connectivity/integration check of the
`GPT-C1` cell defined in Entry 2 — it does not constitute, contribute to,
or substitute for any of the six pre-registered GPT-C1–C6 tuning runs
(each N=500). **No tuning configuration other than `GPT-C1` was executed,
and `GPT-C1` itself was executed only at this 10-episode smoke-test
scale, never at its frozen N=500.** The historical Gemini entries (Entry
1) remain untouched by this record. **This entry does not alter the
frozen GPT-C1–C6 methodology (Entry 2) in any way** — no parameter,
definition, or fixed value recorded there is changed here.

### Configuration exercised

| Field | Value |
|---|---|
| Cell | `GPT-C1` |
| Model | `gpt-5-mini` |
| `reasoning_effort` | `minimal` |
| Prompt disclosure | `low` |
| `verbosity` | `low` |
| `temperature` | Omitted from the actual OpenAI API request (per Entry 2's frozen finding) |

### Execution

- Episodes: **10/10 completed**, DEV split, seeds **1000–1499**'s first
  ten indices — **1000–1009**. No holdout or stress index accessed.
- Live OpenAI calls: **23** (one per wake-up tick across the 10
  episodes).
- Outcome breakdown: **successful 21, schema_violation 1, gate_rejected
  1, unparseable 0, timeout 0.**
- Quota/rate-limit events: **0.**

**The 23-call sample is far too small to estimate a stable fallback
rate.** One `schema_violation` and one `gate_rejected` occurred; at
n=23 this could plausibly range from a rare occurrence to a much more
common one — no rate estimate, confidence interval, or projection is
drawn from these two events by this entry. **Both were handled entirely
by the existing, unmodified fallback architecture (A3-D re-invoked for
the same view/tick, re-gated, executed normally) — neither was
investigated, explained, or "fixed"; they are recorded as observed
behavior only.**

### Token / latency / cost

| Metric | Value |
|---|---|
| `tokens_in` total | 9,231 |
| `tokens_out` total | 1,853 |
| `tokens_in` mean | 401.3 |
| `tokens_out` mean | 80.6 |
| `latency_ms` min | 1,563.9 |
| `latency_ms` mean | 2,532.2 |
| `latency_ms` max | 8,491.5 |
| Estimated paid-equivalent USD exposure | ≈ **$0.00601** (from `rrx.agent.openai_client.estimated_paid_equivalent_usd`, officially published rates, computed from the actual observed token totals above — not invented) |
| Ledger `cost`/`cost_inr` | **`0.0` on every tick** — per the documented USD→INR accounting gap (`rrx.agent.openai_client`'s module docstring): this is NOT actual zero spend, only an artifact of the frozen ledger field's ₹ denomination and the absence of any authorized conversion rate. |

### Cache replay

Cache flipped to replay mode, live client replaced with a poisoned stub
guaranteed to fail if called: **0 live calls made during replay, all 10
`EpisodeResult`s reproduced exactly**, matching the original live run.

### Security / scope

- API-key leakage: **none observed** — captured output contained only
  aggregate statistics, no raw prompt/response text, no key material.
- Holdout/stress access: **none.**
- Repository changes caused by the smoke test itself: **none** —
  verified via `git status --short`/`git diff --stat` before and after
  the run, byte-identical.
- The smoke-test script and its output summary were kept outside the
  repository (session scratchpad only) — not added to `tests/`, not
  committed, no permanent test artifact created. `gpt_probe.py` (Stage
  6G.1's untracked empirical-probe artifact) was left untouched.

---

## Entry 4 — Day 6 final closure: GPT-C1–C6 tuning complete, GPT-C2 selected (PROVISIONAL)

**Status: a closure record. Entries 1–3 above, and every historical
result they describe, are unmodified by this entry — this is an
append-only addition, not a rewrite.**

### Tuning execution: complete

All six frozen configurations (`GPT-C1` through `GPT-C6`, as defined in
Entry 2) have each completed their full prescribed **N = 500** DEV
episodes, dev seeds **1000–1499**, exactly once, with zero holdout/stress
access at any point. Official result directories:

| Cell | Directory |
|---|---|
| GPT-C1 | `results/a3llm-gpt-c1-dev500-20260828-01/` |
| GPT-C2 | `results/a3llm-gpt-c2-dev500-20260829-01/` |
| GPT-C3 | `results/a3llm-gpt-c3-dev500-20260829-01/` |
| GPT-C4 | `results/a3llm-gpt-c4-dev500-20260829-01/` |
| GPT-C5 | `results/a3llm-gpt-c5-dev500-20260829-01/` |
| GPT-C6 | `results/a3llm-gpt-c6-dev500-20260829-02/` |

**`results/a3llm-gpt-c6-dev500-20260829-01/` is excluded from the
official six-cell comparison.** It is an interrupted run (164/500
episodes, `progress.json` status `"in_progress"`), produced before the
OpenAI SDK transport fix (explicit `timeout=60.0`, `max_retries=0` —
see `src/rrx/agent/openai_client.py`'s module docstring) that a live run
of this same cell exposed. It is preserved, unmodified, as audit
provenance of that defect and its fix — not as a candidate result, and
never to be pooled with or substituted for the official C6 result above.

### Selected configuration: GPT-C2 — PROVISIONAL, N=500-based only

Applying the pre-registered selection rule (Entry 2, originally Day 6
Stage 6B Decision 3) mechanically to the six completed results: **the
configuration with the highest subscription rescue rate, no tie, is
`GPT-C2`.**

| Field | Value |
|---|---|
| `reasoning_effort` | `minimal` |
| `disclosure` | `high` |
| `verbosity` | `low` |
| Subscription rescue rate (N=500) | 0.544 (highest of the six; runner-up `GPT-C1` at 0.542) |

**This selection is based entirely on N = 500 DEV tuning evidence.**
`docs/A3-DESIGN.md §18` / `EVAL.md §6A` prescribe a further step for the
selected configuration: a full **N = 2,000** DEV confirmation run.
**That run has NOT been executed.** This is a deliberate decision to
stop further live API spending at this point in the project — not an
oversight, not a silent skip, and not a claim that the step was
completed.

**GPT-C2 must NOT be described as full-DEV validated.** Everything
known about GPT-C2 beyond the raw N=500 numbers above (its behavior
relative to the other five cells, its cost/latency/reliability
characteristics) comes from the same N=500 run and carries the same
evidentiary weight — a single 500-episode DEV sample, not a full-cohort
or holdout-confirmed result. No statistical significance is claimed for
its margin over the runner-up (Day 6 Stage 6T found paired bootstrap
analysis impossible from the stored artifacts — no per-episode outcome
data was persisted for any GPT cell, only aggregate rates).

### What this entry does not do

This entry does not select GPT-C2 for holdout evaluation, does not run
or schedule the N=2,000 confirmation, does not access holdout or stress
data, and does not alter the six-configuration budget, the selection
rule, or any of Entries 1–3. It records where the GPT tuning phase
actually stopped, and why, so a later reader cannot mistake N=500
tuning evidence for a validated final result.
