Razorpay Revenue Recovery — Claude Code Instructions
1. Project
This is a buildathon project for a payment-recovery agent (Razorpay AI Buildathon, Track 03 — AI Revenue Recovery).
The repository uses a `src` layout:

```text
src/rrx/
├── agent/
├── audit/
├── features/
├── gates/
├── integrations/
├── sim/
├── spec/
└── tools/

tests/
configs/

```

The project is evaluated through a frozen evaluation specification (`EVAL.md`) and deterministic tests. Evaluation integrity is more important than making tests pass by changing the evaluation.

`EVAL.md` tags every claim with a provenance tier: `[CITE]` (external fact, needs URL + retrieval date), `[INVARIANT]` (a constraint we impose, needs an enforcing test), `[DESIGN]` (experimental choice, no bearing on validity), `[MODEL]` (world assumption that could change the conclusion, needs a row in the sweep grid). When writing code, configs, or docs in this repo, preserve this tagging convention rather than inventing untagged constants — an unlabeled magic number in a config file is exactly the kind of thing a reviewer will flag.

2. Current Phase
The project is currently in the Day 1 evaluation/infrastructure phase.
Do NOT jump ahead and build:

* the recovery agent
* the simulator
* a dashboard
* live-payment workflows
* model training
* new experimental strategies

unless explicitly instructed.
Prefer the smallest implementation necessary to satisfy the current task.

"Day 1 infra" concretely means closing out `EVAL.md §11`'s freeze checklist (population/episode configs populated, `EpisodeView` implemented as a dataclass, the consistency tests passing, `decline_codes.yaml` cross-checked). Once that checklist is fully checked and `eval-spec-v1` is tagged, treat that as the signal to ask before starting agent/sim work — not a green light to start it automatically.

3. Locked Evaluation Surface
Do NOT modify these files unless the user explicitly authorizes it:

* `EVAL.md`
* `configs/model_params.yaml`
* `configs/population.yaml`
* `configs/episode.yaml`
* `configs/costs.yaml`
* `data/decline_codes.yaml`
* `tests/test_model_params_registry.py`
* `tests/test_sweep_grid.py`
* `tests/test_failure_mix_simplex.py`

This list is illustrative, not exhaustive. Any test file that enforces an `EVAL.md §5.2` safety gate (e.g. `test_gate_*.py`, `test_audit_coverage.py`, `test_unverified_not_emitted.py`) or the `§3.4` no-latent-leak invariant (`test_no_latent_leak.py`) is locked under the same rule the moment it exists in the repo, whether or not it's named explicitly above. Do not weaken, delete, skip, xfail, or remove an assertion in one of these files to make a run go green — that applies to every file matching this description, not just the ones enumerated by name.

Do not change evaluation definitions, populations, model parameters, success criteria, or experimental decisions merely to make implementation tests pass.

Do not create or move git tags (e.g. `eval-spec-v1`) without explicit authorization — tagging signifies the spec is frozen per `EVAL.md §11`, and that's a call for the user to make, not the agent.

If a locked file appears incorrect, stop and explain the problem before changing it.

4. Evaluation Integrity
The evaluation environment must remain independent of the agent's behavior.
Never introduce:

* hidden information
* new model parameters
* new configuration keys
* undocumented experimental decisions
* data leakage
* future information into an episode
* changes to the frozen population solely to improve results

Concretely: `rrx.agent` and `rrx.features` must never import `rrx.sim.latent`, directly or transitively — that boundary is what makes uplift attributable to the pre-registered advantage sources in `EVAL.md §3.4` rather than a leak. When extending `EpisodeView`, only add fields that are in the `§3.4` signal table; an extra "convenience" field is the most likely way a leak enters quietly.

If a candidate agent (once built) fails to beat the A2 baseline on holdout, that is a result to report, not a bug to fix by re-tuning and re-running holdout until the number looks good. `EVAL.md §7` calls this out explicitly — every holdout run, successful or not, gets logged.

When implementing features, preserve the existing evaluation contract.
If uncertain whether a proposed change affects evaluation integrity, stop and ask the user.

5. Testing Rules
Before fixing an unexpected test failure:

1. Run the relevant test.
2. Show the exact failure.
3. Explain the likely cause.
4. Distinguish whether it is:
   * an implementation bug
   * a test bug
   * an environment/dependency problem
   * a pre-existing unrelated failure
5. Propose the smallest valid fix.

Do not silently fix failures without reporting what failed.
After implementation changes, normally run:

```text
python -m pytest -q
python -m ruff check .

```

For targeted changes, also run the relevant test file directly.
Do not claim a test is fixed unless it has actually been run.

6. Scope Discipline
Before modifying code:

* inspect the existing implementation
* understand how the current modules connect
* reuse existing abstractions
* avoid duplicate implementations
* avoid unrelated refactoring
* avoid changing public interfaces unnecessarily

Do not add dependencies unless they are genuinely required.
If a dependency is required, explain:

* why it is required
* whether it is runtime or development-only
* whether it changes the default installation surface

Do not create new architecture merely because it might be useful later. Do not delete or replace existing modules simply because they are not currently needed — the empty-looking `agent/`, `sim/`, `gates/`, `tools/` directories are placeholders for later phases, not dead code.

7. Razorpay Safety & Data Provenance
Development and evaluation use Razorpay Test Mode.
Do NOT:

* use live Razorpay credentials
* perform real-money transactions
* introduce live-payment behavior
* bypass the existing test-mode guard

Keep credential handling explicit and minimal.
Do not add environment-based credential plumbing or additional credential entry points unless explicitly requested.
The Razorpay integration should remain offline-safe during tests.

This extends beyond API calls: all fixtures, test data, and populations must be synthetic, generated from `configs/population.yaml` via `src/rrx/sim/`. Do not introduce real customer, merchant, or production-derived data anywhere in the repo — including one-off test fixtures, sample CSVs, or debugging scratch files.

8. Current Integration Surface
The following files are part of the current implementation:

```text
src/rrx/features/__init__.py
src/rrx/features/episode_view.py
src/rrx/integrations/__init__.py
src/rrx/integrations/razorpay_client.py

tests/test_no_latent_leak.py
tests/test_razorpay_test_mode.py

```

Treat these as existing implementation, not invitations to redesign the architecture.
When integrating them:

* preserve their intended public surface
* fix actual integration defects
* do not redesign them without explicit authorization
* `episode_view.py`'s `EpisodeView` fields must match the `EVAL.md §3.4` signal table exactly — see §4 above on why extra fields are a leak risk, not a convenience

The existing `src/rrx/spec/registry.py` and related tests are part of the established project and should not be casually refactored.

9. Communication
Be concise and explicit.
For important changes, report:

* files changed
* reason for each change
* tests run
* final pass/fail result
* any remaining issue

If the requested change conflicts with a locked rule, do not work around the rule silently. Explain the conflict and ask for authorization.
Do not invent requirements that are not present in the repository, evaluation specification, or user's instructions.
When several implementation choices are possible, prefer the smallest change that preserves the existing architecture and evaluation integrity.