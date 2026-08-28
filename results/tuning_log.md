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
