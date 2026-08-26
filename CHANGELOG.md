# Changelog

## Day 2 Stage 2 — 2026-08-26

Sweep-cell materialization and a reproducibility control. No agent, clock,
cohort generator, or manifest — those remain out of scope per this stage's
brief.

### Cell -> resolved-config resolver

- `src/rrx/spec/resolver.py`: new pure `resolve_config(episode_cfg,
  population_cfg, cell)`, dispatched by each cell's declared `handle` (not
  by pattern-matching `cell_id`). Returns fresh deep copies; never mutates
  its inputs. Resolves all 26 `enumerate_cells()` cells except
  `invoice_amount`, which raises `NotImplementedError` naming the
  unresolved invoice-authority question (`population.yaml#/invoice_amount_inr`
  vs `episode.yaml#/invoice_amount_inr#mu_expression` - two independent
  representations, no consumer for either today, so no basis to pick one).
- `failure_mix_weights` bucket-mass cells update only
  `population.yaml#/failure_mix/conditions` - the representation
  `model_params.yaml`'s `owner_path` names and the one
  `rrx.spec.registry.expand_to_conditions` actually consumes.
  `population.yaml#/opening_conditions[*]/weight` is a separate
  representation (consumed only by
  `tests/test_population_matches_decline_codes.py` and, apparently,
  `EVAL.md §3.2`'s hand-maintained table - the `make docs` generator that
  comment references does not exist in this repository) with no test or
  code proving the two agree. Left deliberately unsynchronized rather than
  silently patched to match, per the discovered-duplication rule for this
  stage - see `tests/test_sweep_materialization.py`'s module docstring and
  `test_failure_mix_bucket_cell_changes_only_failure_mix_conditions`.

### Sweep reachability

`tests/test_sweep_materialization.py` classifies all 26 cells:
**10/26 simulator-reachable** (`balance_restore_timing` x2 handles x2,
`channel_response_propensity`, `card_change_completion_propensity`,
`failure_mix_weights.ambiguous_cause_split` - each has a live consumer in
`rrx.sim.latent`) and **16/26 materializer-only** (`invoice_amount`, the six
`failure_mix_weights` bucket-mass cells, `cancellation_hazard_and_ltv` - no
opening-condition selector, invoice sampler, or cancellation/LTV sampler
exists yet). Reachable cells get a smoke test proving the resolved config
moves the relevant sampled statistic in the declared direction relative to
baseline; materializer-only cells are resolved but no consumer is invented
to inflate the count.

### Reproducibility control

Not performance-motivated. `pyproject.toml`: `numpy>=2.0` -> `numpy==2.5.2`
(the installed version) - an unpinned lower bound lets a future numpy/RNG
implementation change silently shift every sampled value while the frozen
CRN seeding (`seed_for_substream`) and calling code stay identical.
`tests/test_latent_snapshot.py` pins six known `(split, episode_index,
opening_condition)` -> `LatentState` cases (one per SIM.md §2 mechanism
family, across both `dev` and `holdout`) recorded against numpy 2.5.2, so a
future deliberate dependency bump that changes sampled outputs fails loudly
here instead of silently.

### Verification

- `python -m pytest -q`: see run output in the Stage 2 report.
- `python -m ruff check .`: see run output in the Stage 2 report.
- No frozen spec file (`EVAL.md`, `SIM.md`, `configs/episode.yaml`,
  `configs/population.yaml`, `configs/model_params.yaml`) modified.
- Does not move or delete `eval-spec-v1` or `eval-spec-v1.1`. Does not tag
  `sim-v1` (deferred; manifest work is Stage 4).

## eval-spec-v1.1 — 2026-08-26

Not performance-motivated. No agent (A2, A3, or otherwise) exists yet in this
repository — Day 2 is still simulator-construction stage. These changes
close gaps and a documentation defect discovered while writing `SIM.md`,
under `EVAL.md §10`'s discovered-validity-defect clause.

### `send_subscription_link` excluded from the v1 action space

Q1 research (2026-08-26) found no primary Razorpay documentation supporting
a customer-facing link that clears an already-failed subscription invoice
for a domestic card — the claim `EVAL.md §1.2`'s action-space table makes for
that row. Three real Razorpay mechanisms exist and none matches: the
card-change email link restores the subscription but does not re-attempt
previous charges; manual invoice charge is Dashboard-only and explicitly
unsupported for domestic cards; Subscription Links are for initial
authorisation only, not existing-invoice recovery.

- `EVAL.md`: added a `[DEFECT, eval-spec-v1.1]` footnote immediately below
  the `§1.2` action-space table, recording the finding. The frozen table
  itself is unchanged, per `§10`.
- `SIM.md`: `send_subscription_link` removed from the action-space and
  message-content tables (`§3`); `link_clears_failed_invoice` removed from
  outcome resolution (`§5`) — invoice recovery is now auto-retry-only;
  `§6` Tier 3 family 5 (remedy completion propensity) now reads "card change
  only"; `§9` records the resolution.

### Two config gaps resolved — and genuinely swept

Both were flagged as open in `SIM.md` at Day 2 Stage 0 and are folded into
their existing `[MODEL]` families — no seventh family created.

- **`P(card | ambiguous decline)`** — `configs/population.yaml`'s
  `ambiguous_decline` entry gets `p_card_cause: 0.50` (`basis:
  project_inference`, max-entropy rationale) and
  `UNRESOLVED_intra_group_split` flips to `false`. Folded into
  `failure_mix_weights` via `configs/model_params.yaml`'s new
  `definition.ambiguous_cause_split`, `sweep_required: true`, cells
  `0.35` / `0.65` (±30%).
- **`bank_technical_error` clearance** — `configs/episode.yaml`'s `latent`
  section gets `bank_technical_error_clearance` (`Uniform(0, 2]` days).
  Folded into `balance_restore_timing` via `configs/model_params.yaml`'s new
  `definition.transient_block_clearance`, `sweep_required: true`, cells
  `[0, 1.4]` / `[0, 2.6]` (±30% on the upper bound).

**Correction (same day, before commit):** these two were initially marked
`sweep_required: true` with no `sweep.cells`, so they silently contributed
**zero** cells to `enumerate_cells()` — `sweep_required` was documentation
only, not enforced. `test_model_params_swept.py` did not catch this because
none of its checks looked inside a parameter's `definition:` block; only
top-level `handle`/`sweep.cells` were read. This is a gap in the `EVAL.md
§0` enforcement mechanism, not just these two entries, and is fixed here:

- `src/rrx/spec/registry.py`: `enumerate_cells()` now recurses into every
  canonical parameter's `definition:` block and generates cells for any node
  marked `sweep_required: true` with a `sweep.cells` low/high pair. Added
  `find_sweep_required_nodes()`, `unswept_required_entries()` (returns every
  `sweep_required` node with no matching cell), and `scalar_valued_handles()`
  (distinguishes a declared-scalar magnitude from a corrupted bucket-vector
  cell, for `test_failure_mix_simplex.py`'s companion check below).
- `tests/test_model_params_swept.py`: cell-count arithmetic updated
  **22 → 26** (28 with the topup toggle) — an **increase** in sweep
  coverage, not a relaxation: the old count of 22 simply omitted two
  `[MODEL]` parameters that should always have been in the grid.
  `test_failure_mix_contributes_twelve_cells` → **fourteen** (the six
  buckets' 12, plus `ambiguous_cause_split`'s own 2).
  `test_required_wins_is_ceil_of_eighty_percent` updated to `ceil(0.8×26)=21`
  / `ceil(0.8×28)=23`. `test_scalar_handles_have_two_directional_cells`
  rewritten to check per-`handle` rather than per-`parameter`, since
  `balance_restore_timing` now legitimately has two independent handles.
  Added `test_all_sweep_required_entries_produce_cells` (real config: no
  `sweep_required` node may contribute zero cells) and
  `test_sweep_required_with_zero_cells_is_detected` (regression, on a
  synthetic registry, reproducing today's exact bug shape to prove the
  detection mechanism itself works).
- `tests/test_failure_mix_simplex.py`: `test_all_generated_failure_mix_cells_are_valid_simplexes`
  now skips non-`dict`-valued cells (the new `ambiguous_cause_split` cells
  are scalars, not bucket vectors, and were never meant to be simplex-checked).
  Added `test_scalar_cells_are_declared_scalar_not_corrupted_vectors` as a
  companion so that guard cannot silently swallow a genuine defect: any
  non-dict `failure_mix_weights` cell must correspond to a handle explicitly
  declared scalar in `model_params.yaml`, or the test fails.

**Second correction (same day, before commit):** the first correction fixed
whether a `sweep_required` node contributes cells at all, but two sibling
checks in `tests/test_model_params_swept.py` —
`test_scalar_cells_are_thirty_percent_from_baseline` and
`test_probability_cells_within_clamp` — read only a parameter's top-level
`handle`/`sweep.cells` and so were still blind to anything nested inside
`definition:`. `ambiguous_cause_split`'s `0.35`/`0.65` was therefore enforced
as neither ±30% from its own `0.50` baseline nor within the `[0, 1]`
probability clamp — the same blindness `find_sweep_required_nodes()` exists
to fix, left in place in these two sibling tests. Fixed here, both extended
to reuse `find_sweep_required_nodes()`:

- `test_scalar_cells_are_thirty_percent_from_baseline` now also checks every
  definition-nested `sweep_required` node's cells against its own declared
  baseline at ±30%. `transient_block_clearance`'s cells are `[lower, upper]`
  day-bound lists, not a bare scalar — **chose option (2a)**: the check
  applies to the upper bound only (the `support_days_upper_bound` handle)
  against the baseline's own upper bound (`2` days), since the lower bound
  is fixed at `0` by design and is not what the magnitude sweeps. Rejected
  (2b) (a silent/stated exemption) because the upper bound genuinely is a
  ±30%-swept `[MODEL]` magnitude and a real check was available at no extra
  cost.
- `test_probability_cells_within_clamp` now also checks every
  definition-nested `sweep_required` node whose cells are scalar (a
  probability) against `probability_clamp`. `transient_block_clearance`'s
  list-valued day-bound cells are explicitly excluded here, stated in the
  test body: a day count of `2.6` failing a `[0, 1]` clamp would be a false
  positive, not a real defect — it is checked instead, correctly, by the
  ±30% test above.
- Added `test_thirty_percent_check_catches_a_bad_definition_nested_cell`
  (regression, same shape as `test_sweep_required_with_zero_cells_is_
  detected`): corrupts `ambiguous_cause_split`'s `high` cell to `0.99` on a
  synthetic registry and asserts the new check catches it, proving the
  extension actually works rather than merely happening to pass on today's
  already-correct values.

### Verification

- `python -m pytest -q`: 188 passed (all locked tests green, including both
  corrections to `test_model_params_swept.py` and `test_failure_mix_simplex.py`).
- Sweep cell count: 22 → 26, unchanged by the second correction (it added
  enforcement, not cells; 24 → 28 with the topup toggle on — that toggle's
  own on/off semantics are unchanged).
- `git diff -- EVAL.md`: exactly one added paragraph (the `§1.2` footnote);
  no other line changed.

Does not move or delete the `eval-spec-v1` tag.
