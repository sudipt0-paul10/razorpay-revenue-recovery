# ARCHITECTURE.md — RR-X System Architecture

Describes the repository as it actually exists at the sealed Day 8 holdout state (`code-freeze-holdout` → `4d45db461943978637673a5611a429e0fe826065`, plus the Day 8 provenance/infrastructure commits on top of it, per `results/holdout_runs.md`). Every module and path named below is real and present in the repository at the time of writing; nothing here describes a planned-but-unbuilt capability unless explicitly marked as such.

---

## 1. Problem being solved

Razorpay retries a failed subscription auto-charge automatically, on a fixed schedule the merchant cannot control (`EVAL.md §1.1`). The merchant cannot trigger or reschedule that retry. What the merchant *can* do is decide **whether to contact the customer, when, on which channel, with which of a small set of remedies — and when to stop** (`EVAL.md §1.2`). This repository builds and evaluates an agent that makes exactly that decision, for domestic-card subscription failures, with two distinct recoverable outcomes tracked separately (`EVAL.md §1.3`):

- **Invoice recovery** — the specific failed invoice gets paid (only possible while Razorpay's own auto-retries are still running).
- **Subscription rescue** — the subscription returns to `active` (future billing preserved, even if the specific failed invoice is lost).

---

## 2. System architecture

### Simulator / environment — `src/rrx/sim/`

- `latent.py` — draws the hidden per-episode state (`LatentState`: `card_chargeable`, `funds_available_from`, `mandate_alive`, `blocked_until`) from the six `[MODEL]` parameters in `configs/model_params.yaml`. Defines `MASTER_SEED = 20260825`. Latent state is architecturally unreachable from `rrx.agent`/`rrx.features` (`tests/test_no_latent_leak.py`).
- `cohort.py` — `sample_cohort_episode()`: draws each episode's opening condition (`insufficient_funds`, `card_expired`, `ambiguous_decline`, etc., per `configs/population.yaml`'s weights) and invoice amount.
- `rng.py` — common-random-number (CRN) substream isolation, so the same episode index presents an identical latent world to every arm.
- `engine.py` — `run_episode()`, the day-loop simulator for the non-agent arms, dispatched through a `_POLICIES` dict keyed by arm name; the frozen `EpisodeResult` dataclass every arm's outcome is reported through; Razorpay's auto-retry engine (`configs/episode.yaml`: retry days `[1, 2, 3]`, `halt_boundary_day: 3`, 30-day episode window).
- `run_stage3.py` — `paired_bootstrap_ci()` (the frozen statistical procedure, `BOOTSTRAP_SEED = 20260826`, `N_BOOTSTRAP_RESAMPLES = 10_000`, 95% CI).

### Population and episode generation

Driven entirely by `configs/population.yaml` (opening-condition weights, invoice-amount distribution) and `configs/episode.yaml` (window length, retry schedule, contact budget, wake-up cadence, cost/effect parameters) — no hand-typed fixtures. `configs/model_params.yaml` is the single source of truth for the six canonical `[MODEL]` sweep parameters and their sensitivity-sweep registry (`src/rrx/spec/registry.py`).

### Evaluation harness

- `src/rrx/harness/splits.py` — the three frozen splits: `dev` (seeds 1000–2999), `stress` (seeds 5000–5299), `holdout` (seeds 9000–10999, N=2000, gated behind `holdout_indices(authorized=True)`).
- `src/rrx/harness/runner.py` — `run_episode_a3()`, the `EpisodeView`-driven day-loop for the A3 arms specifically (`WAKEUP_DAYS = {0, 1, 2, 3, 5, 7, 14}` plus engagement-triggered wake-ups).
- `src/rrx/eval/arms.py` — `run_official_arm()` / `run_arm_cohort()`, the single dispatch point that runs any of the five wired arms over a given split and writes its artifacts.
- `src/rrx/eval/runner.py` — the original A3-D dev-run driver (`main()`), plus the shared metrics/manifest/episode-result writers every arm's artifacts go through.
- `src/rrx/eval/stress.py` — the `stress`-split driver (`run_stress_suite()`), reusing `run_official_arm()`.
- `src/rrx/eval/holdout_analysis.py` — the post-sealing analysis module (§5/§6 below).
- `src/rrx/spec/manifest.py`, `src/rrx/spec/registry.py`, `src/rrx/spec/resolver.py`, `src/rrx/spec/sensitivity_doc.py` — the manifest schema, the sweep-cell registry, and supporting spec machinery.

### Recovery arms

| Arm | Implementation | Policy interface |
|---|---|---|
| **A0** | `rrx.sim.engine` (`_POLICIES["A0"]`) | No contact at all — the floor. |
| **A1** | `rrx.baselines.a1.a1_action_for_day` | Canonical naive dunning: `card_change` at T+0 and T+3, regardless of condition (`EVAL.md §4.3`). |
| **A2-strengthened** | `rrx.baselines.a2_variants.a2_strengthened_action_for_day` | Condition-aware fixed schedule, adopted as the final bounded A2 (`EVAL.md §4.1.2`). |
| **A3-D** | `rrx.agent.policy.a3d_policy` via `rrx.harness.runner.run_episode_a3` | Deterministic, `EpisodeView`-driven, gated — §4 below. |
| **A4** | `rrx.baselines.a4.run_a4_episode` | Oracle: full latent-state access, same 3-contact budget, empirical upper reference only — **not** a deployable comparator (`EVAL.md §7`). |

A0/A1/A2-strengthened share `rrx.sim.engine.run_episode()`'s plain `(opening_condition_key, day, subscription_state) -> action | None` policy interface — no `EpisodeView`, no gate, no ledger. A3-LLM (the LLM-planner arm, `rrx.agent.planner.A3LLMPolicy`) exists in the codebase but is **excluded from the holdout split entirely**, for a declared budget reason (`EVAL.md §7.1` item A) — it is not part of the sealed holdout run this document otherwise describes.

### A3-D decision/policy path

`EpisodeView` (`src/rrx/features/episode_view.py`, 10 frozen fields: `subscription_id`, `subscription_state`, `invoice_amount_inr`, `days_since_first_failure`, `auto_retries_remaining`, `next_auto_retry_day`, `decline_code`, `billing_amount_inr`, `contact_history`, `budget_remaining`) → `rrx.agent.policy.a3d_policy(view) -> Proposal` → `rrx.agent.gate.evaluate_gate(proposal, view) -> GateVerdict` → executor (`_send_message` primitives) → one `LedgerRecord` per tick.

### Contact / fallback mechanics

- **Contact budget:** 3 per episode for every arm (`configs/episode.yaml#/agent_budget/max_contacts_per_episode`).
- **Wake-up cadence (A3 only):** the fixed day set `{0, 1, 2, 3, 5, 7, 14}` plus any day following new engagement, suppressed once the subscription reaches a terminal state or the budget is exhausted (`src/rrx/harness/runner.py`).
- **Tick taxonomy:** every A3 tick is exactly one of `wakeup | no_wakeup | budget_exhausted | terminal_suppressed` (`EVAL.md §5.4`).
- **Fallback (A3-LLM only, not exercised in the sealed holdout):** on `timeout | unparseable | schema_violation | gate_rejected | stale_state | no_executor_mapping`, the episode's tick falls back to A3-D's own decision (`rrx.agent.planner`).

### Metrics and artifact generation

Every arm run (`rrx.eval.arms.run_official_arm`) writes, per `src/rrx/eval/runner.py`:

- `manifest.json` — the frozen 11-field `RunManifest` (`rrx.spec.manifest`): `git_sha`, `spec_version`, `config_hash`, `seed`, `arm`, `regime`, `sweep_cell`, `model_version`, `timestamp`, `wall_clock_seconds`, `llm_cost_inr`.
- `episode_results.jsonl` — one JSON record per episode (`episode_index` + every `EpisodeResult` field), via `rrx.eval.runner.write_episode_results`.
- `metrics.json` — aggregate rates/counts, via `compute_metrics()` (A3-D) or `compute_metrics_results_only()` (the non-ledger arms).
- `run_params.json` — a reproducibility sidecar (split, index range, seed, arm, policy/runner qualnames).
- `ledger.jsonl` — one `LedgerRecord` per tick, **A3-D only** among the holdout arms (gitignored; A0/A1/A2-strengthened/A4 have no gate/ledger mechanism at all).

### Holdout execution and sealing

`scripts/run_holdout.py` is the single guarded entry point (§5 below). Once run, its output lands under `results/holdout/<code-freeze-holdout-sha[:12]>/<arm>/`. Sealing (`docs/DAY8-HOLDOUT-PLAN.md §E.3`) computes a `SHA256SUMS` manifest over every artifact (including the gitignored ledger) and anchors it with an annotated `holdout-run-<id>-sealed` tag.

### Post-run analysis

`src/rrx/eval/holdout_analysis.py`'s `analyze_holdout()` reads only the sealed `episode_results.jsonl`/`metrics.json` files, independently recomputes every metric, cross-checks it against the committed aggregate, runs the frozen paired bootstrap, applies the comparator/tie-set rule, and evaluates criteria 2 and 3 plus the 40%-of-gap target. Its output for the sealed Day 8 run is recorded in `RESULTS.md`.

---

## 3. Data flow

```text
episode/population (configs/population.yaml, episode.yaml
   via rrx.sim.latent + rrx.sim.cohort)
        │
        ▼
   arm / policy   ── A0/A1/A2-strengthened: rrx.sim.engine._POLICIES
        │           ── A3-D: EpisodeView → rrx.agent.policy.a3d_policy
        │           ── A4:  rrx.baselines.a4 (full latent access)
        ▼
   simulator      ── rrx.sim.engine.run_episode()  (A0/A1/A2-family, A4)
                   ── rrx.harness.runner.run_episode_a3()  (A3-D)
        │
        ▼
recovery / contact decision  ── Proposal → gate (A3-D only) → executor
        │
        ▼
   EpisodeResult   (rrx.sim.engine, shared dataclass, every arm)
        │
        ▼
 metrics / artifacts  ── episode_results.jsonl, metrics.json,
                          manifest.json, run_params.json,
                          ledger.jsonl (A3-D only)
        │
        ▼
      analysis      ── rrx.eval.holdout_analysis.analyze_holdout()
```

---

## 4. A3-D in detail

**Decision logic.** `rrx.agent.policy.a3d_policy(view: EpisodeView) -> Proposal` is a **pure, deterministic, first-match-wins 16-rule table** (`R-01` through `R-16`), a literal transcription of `docs/A3-DESIGN.md §10A.4`. Each rule is pre-registered as `[FORCED]` (mechanically derivable from simulator mechanics), `[FORCED mechanically]` (every available action is a provable no-op), or `[DESIGN]` (a genuine, disclosed choice). No network call, no randomness beyond the CRN substreams every arm already shares.

**Contact budget.** Identical to every other arm: 3 contacts per episode (`configs/episode.yaml#/agent_budget/max_contacts_per_episode`). A3-D gets more *decision points* (the 7-day wake-up cadence plus engagement triggers) than a fixed-schedule arm, never a larger budget.

**Safety invariants / gates.** `rrx.agent.gate.evaluate_gate()` implements `EVAL.md §5.2`'s eight safety rows as rules `R1–R6, R8` (there is no numbered `R7` — that row, "no audit record," is a structural runner invariant: one `LedgerRecord` per tick, not a gate rule), checked in the frozen precedence `R2, R4 → R3 → R1, R8 → R5, R6`:

| Gate rule | Checks |
|---|---|
| R1 | No agent-initiated payment retry (defensive — no such action exists in the schema) |
| R2 | No `CONTACT` when `subscription_state ∈ {cancelled, expired}` (defensive; unreachable via real A3-D output — such episodes never generate a runner tick at all) |
| R3 | No `card_change` remedy for `insufficient_funds` / `transaction_limit_exceeded` |
| R4 | No `CONTACT` after `payment_risk_check_failed` |
| R5 | Budget cap (enforcement-by-construction: the runner never invokes the policy once `budget_remaining == 0`) |
| R6 | Quiet hours (vacuous in `sim-v1`: the executor always stamps a fixed `10:00 IST` send hour) |
| R8 | No unverified/attended-only decline codes reach the agent (defensive — already guaranteed by cohort generation) |

A3-D is gate-compliant by construction — its own 16-rule table never proposes a violating action — which is why the sealed holdout's `metrics.json` shows every safety-invariant count at zero (`RESULTS.md §10`).

**How A3-D differs from the bounded comparator arms (A0/A1/A2-strengthened).** Those three run through `rrx.sim.engine.run_episode()`'s plain `(opening_condition_key, day, subscription_state) -> action` interface: no `EpisodeView`, no gate, no per-tick ledger, no reason-code taxonomy, and a fixed (non-adaptive) contact schedule. A3-D runs through the separate `EpisodeView`-driven, gated, ledger-recording path (`rrx.harness.runner.run_episode_a3`), with an adaptive wake-up schedule and full per-tick audit trail — while sharing the identical 3-contact budget, the identical simulator mechanics, and the identical CRN-drawn world per episode index. Any measured difference is attributable to the three pre-registered `EVAL.md §3.4` advantage sources (retry-window timing, remedy matching, within-episode adaptive contact), not to a different budget, a different population, or a different world.

---

## 5. Evaluation architecture

- **`dev` vs `holdout` separation:** `dev` (seeds 1000–2999) is used for all development, tuning, and diagnostic work; `holdout` (seeds 9000–10999, N=2000) is single-use per candidate release (`EVAL.md §3.5`) and is exposed only through `rrx.harness.splits.holdout_indices(authorized=True)`.
- **Frozen evaluation contract:** the `eval-spec-v1.10` tag (`EVAL.md`'s frozen state). `code-freeze-holdout` separately anchors the frozen implementation surface (`EVAL.md`, `SIM.md`, `configs/`, `data/`, `src/rrx/sim/`, `src/rrx/agent/`, `src/rrx/features/`).
- **Authorization guard:** `scripts/run_holdout.py` — requires an explicit `--i-have-authorized-the-holdout` flag (no default); before touching anything, re-verifies `code-freeze-holdout`/`eval-spec-v1.10`, a clean working tree, that the evaluation-relevant paths are byte-identical to `code-freeze-holdout` (a content diff, not a whole-repo commit-SHA pin — see §6), and that the `holdout-authorized-latest` tag — resolved dynamically via `git rev-parse` at runtime, never a hardcoded literal — names the current commit exactly. Obtains indices only via `holdout_indices(authorized=True)`, never by reconstructing the range from the public seed-start/count constants.
- **Sealed holdout artifacts:** `results/holdout/<code-freeze-holdout-sha[:12]>/<arm>/`, anchored by `holdout-run-<id>-sealed` plus `SHA256SUMS`.
- **Post-run statistical analysis:** `rrx.eval.holdout_analysis.analyze_holdout()`, described in §2 and §6.

---

## 6. Reproducibility / provenance

| Anchor | Value / mechanism |
|---|---|
| Master seed | `20260825` (`rrx.sim.latent.MASTER_SEED`) |
| Bootstrap seed | `20260826`, 10,000 resamples, 95% CI (`rrx.sim.run_stage3`) |
| Config hash | SHA-256 over `episode.yaml` + `population.yaml`, recorded in every `manifest.json` |
| Implementation SHA | The executing `git_sha`, recorded in every `manifest.json` |
| Evaluation contract | `eval-spec-v1.10` tag |
| Frozen implementation anchor | `code-freeze-holdout` tag (immutable) |
| Authorization anchors | `holdout-authorized-<date>[-suffix]` tags (immutable, append-only audit trail) plus `holdout-authorized-latest` (the one tag the runner resolves dynamically at execution time) |
| Seal anchor | `holdout-run-<id>-sealed` tag (immutable) |

The evaluation-surface check (§5) — a content diff against `code-freeze-holdout` over a fixed path list, rather than a hardcoded whole-repo commit SHA — exists specifically so that documentation, tooling, and re-authorization commits (which never touch that path list) do not require editing `scripts/run_holdout.py` on every commit; only a real change to the frozen surface fails the check.

---

## 7. Failure handling

- **Deterministic-arm retry policy** (`results/holdout_runs.md`): A0, A1, A2-strengthened, A3-D, and A4 may be replayed from scratch **only** after a genuine execution crash (the process failing to complete) — never because a completed run produced an unwelcome number. Maximum 2 attempts per arm; a second failure stops and is reported, not retried a third time. A replay must use identical code, config, seed, split, parameters, and arm definition; a crash whose fix requires a code change ends the holdout for that arm and is recorded as a post-holdout defect instead.
- **No result-conditioned reruns:** no episode may be selectively rerun, and no rerun of any kind may be triggered by an observed result, metric, or outcome. Every attempt — successful or crashed — is logged.
- **A3-LLM carve-out:** the retry policy's language extends in principle to A3-LLM's LLM-call layer, but is moot for this holdout since A3-LLM is excluded from the holdout arm set entirely (§2).

---

## 8. Known limitation

`results/holdout/<id>/a3_d/run_params.json` records `"policy": "<unknown>"` and `"runner": "rrx.sim.engine.run_episode"` — both incorrect; A3-D actually executes via `rrx.agent.policy.a3d_policy` / `rrx.harness.runner.run_episode_a3`. Root cause: `src/rrx/eval/arms.py`'s `_POLICY_QUALNAME` dict has no entry for the A3-D arm key. This defect **predates Day 8** (present identically in the already-committed `results/stress-20260829-a3d/run_params.json`) and, per `RESULTS.md §13`, **does not affect execution or any numerical result** — `manifest.json`'s `arm` field is correct, the actual code path executed was independently confirmed, and every sealed metric was independently recomputed from `episode_results.jsonl` and matched the committed `metrics.json` exactly.

---

## 9. Architecture diagram

```text
                          ┌────────────────────────────┐
                          │   configs/ (population,     │
                          │   episode, model_params,    │
                          │   costs) + data/            │
                          └──────────────┬───────────────┘
                                         │
                         ┌───────────────▼────────────────┐
                         │  src/rrx/sim/                    │
                         │  latent.py · cohort.py · rng.py  │
                         │  engine.py (run_episode, A0/A1/  │
                         │  A2-family + A4 day-loop)         │
                         └───────┬───────────────┬──────────┘
                                 │               │
                 ┌───────────────┘               └───────────────────┐
                 ▼                                                    ▼
    A0 / A1 / A2-strengthened / A4                          A3-D (agent path)
    rrx.sim.engine / rrx.baselines               EpisodeView → rrx.agent.policy.a3d_policy
    (no gate, no ledger)                          → rrx.agent.gate (R1-R8) → executor
                 │                                          via rrx.harness.runner.run_episode_a3
                 │                                                    │
                 └───────────────┬────────────────────────────────────┘
                                 ▼
                        EpisodeResult (shared dataclass)
                                 │
                                 ▼
             rrx.eval.arms / rrx.eval.runner (per-arm writer)
      manifest.json · episode_results.jsonl · metrics.json ·
             run_params.json · ledger.jsonl (A3-D only)
                                 │
                    ┌────────────┴─────────────┐
                    ▼                           ▼
      scripts/run_holdout.py            rrx.eval.holdout_analysis
      (guarded entry point,             (post-seal: recompute, bootstrap,
       tag-based authorization)          comparator/tie-set, criteria, target)
                    │                           │
                    ▼                           ▼
      results/holdout/<sha>/<arm>/  ──►   RESULTS.md
      SHA256SUMS + holdout-run-
      <id>-sealed tag
```
