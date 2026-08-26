# Changelog

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
