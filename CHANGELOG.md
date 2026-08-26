# Changelog

## sim-v1 — simulator freeze — 2026-08-26

Freeze-only stage. No simulator, config, or test change. Freezes the
`SIM.md` §0/§1 simulator surface — `src/rrx/sim/`, `configs/episode.yaml`,
`configs/population.yaml`, `configs/model_params.yaml`,
`configs/costs.yaml`, `SIM.md` — at the Day 2 Stage 5 commit
`cdd118ad9ef0f8cb145a1aab846fe2e3a2d4ba3a`, under `eval-spec-v1.2`.

### Verification at freeze time

- Frozen surface (`src/rrx/sim/`, `configs/`, `EVAL.md`, `SIM.md`)
  verified diff-empty against `cdd118ad9ef0f8cb145a1aab846fe2e3a2d4ba3a`.
- Ordinary regression suite: 537 passed, 0 failed.
- Stage 5 falsification suite (`tests/test_stage5_falsification.py`,
  run standalone): 4 of 5 passed; Test 1 (policy ordering) rejected,
  reproducing the Stage 5 record above (`A1=0.4840, A2=0.4485,
  diff=-0.0355, CI=[-0.0465,-0.0250]`) byte-for-byte — no drift, the
  Stage 5 finding is not re-evaluated or reinterpreted here.
- Test 1's A1/A2 figures are computed on the `dev` split, episode indices
  `range(1000, 3000)` (2000 episodes), `MASTER_SEED=20260825`
  (`tests/test_stage5_falsification.py:42-44,303-307,334`); no holdout
  split is used.
- `python -m ruff check .`: all checks passed.

### Integrity mechanism

`sim-v1` is an annotated git tag pointing at this commit, following the
same convention already used for `eval-spec-v1` / `v1.1` / `v1.2`: the
tag annotation plus this changelog entry constitute the freeze record.
No config-hash or manifest-file mechanism exists anywhere in this
repository, and none is introduced by this entry.

### Deferred work, explicitly preserved

A per-run manifest and config-hash mechanism — referenced only in
passing at `EVAL.md` §3.3 ("the realised mean is recorded in each run
manifest") with no schema specified there — remains unbuilt. It was
flagged as deferred at Stage 2 (`sim-v1 (deferred; manifest work is
Stage 4)`, this file's Stage 2 entry) and was not delivered in Stages
3, 4, 4B, or 5. `sim-v1` freezes the simulator's code/config surface
only via the git commit/tag; it does not supply per-run provenance
capture. That machinery must exist before the first evaluation run.

## Day 2 Stage 5 — falsification tests, closed — 2026-08-26

Five falsification tests (`tests/test_stage5_falsification.py`, SIM.md §8).
No simulator, A0, A1-ish, A2, A4, or config change was made at any point in
this stage to obtain a result - every number below is as-observed.

### Results

|  | invoice recovery | subscription rescue |
|---|---:|---:|
| A0 | 0.3525 | 0.4055 |
| A1-ish | 0.4840 | 0.5095 |
| A2 | 0.4485 | 0.5180 |
| A4 (equal 3-contact budget) | 0.5465 | 0.5670 |

A4 − A2: invoice recovery +0.0980 (CI [+0.0855, +0.1115]); subscription
rescue +0.0490 (CI [+0.0390, +0.0595]).

### Test-design defect (corrected, not a simulator finding)

The original A4 arm used exactly one contact while A1-ish/A2 could use up
to three - not an equal-budget comparison, so the original A4-vs-A2 result
(A4 invoice recovery 0.4545) **is not, and must not be described as, a
simulator falsification or a falsification of the A4 oracle.** It was an
arm-definition defect. Corrected by giving A4 the identical 3-contact
budget (`episode.yaml#/agent_budget/max_contacts_per_episode`), applying
its existing latent-informed decision logic (unchanged: which content, for
which condition, chosen from full T=0 latent access, never from future RNG
outcomes) across up to three attempts instead of one. Under the corrected
budget A4 clearly beats A2 on both metrics (table above) - an
arm-definition correction restoring the intended comparison, not tuning
toward a desired result.

### Genuine falsification finding: the ordering hypothesis is rejected

`SIM.md §8` test 1's hypothesis (A4 > A2 > A1-ish > A0) is **rejected**,
specifically and only because **A1-ish beats A2 on invoice recovery**
(0.4840 vs 0.4485; paired-bootstrap diff -0.0355, CI [-0.0465, -0.0250],
clearly excludes zero). Mechanism verified, not merely asserted: A2's own
frozen schedule places its second contact for the card-broken bucket and
`ambiguous_decline` at T+5/T+7 - always after the T+3 invoice-retry
boundary, so those contacts can only ever affect post-halt rescue, never
invoice recovery. A1-ish's naive fixed T+3 contact lands exactly on the
last retry day, and under the within-day-ordering ruling, that same-day
engagement is visible to that day's own retry check - a real chance A2's
schedule structurally forfeits on the card-broken + `ambiguous_decline`
buckets (58% of the population). No simulator or policy change was made to
alter this finding; it stands as reported. **This is not a claim that "the
simulator failed"** - every other mechanism it depends on (the retry gate,
CRN, the halt boundary, the responsiveness signal) passed its own
falsification test this stage. It is a specific, actionable finding about
A2's frozen schedule.

### Test 2 (wrong-remedy null) — PASSED, with a flagged stale figure

Recovery comparable to A0 (WRONG_REMEDY 0.3595 vs A0 0.3525). Actual
contact ratio: **1.8378× A2**, not 3×. `SIM.md §8`'s "3x" figure predates
A2's exact schedule being fixed and is flagged as stale/unsupported by the
current A2 schedule - not tuned toward, recorded as observed.

### Tests 3–5 — PASSED

- **Test 3 (timing null):** post-halt topup effect exactly zero (636/636
  `insufficient_funds` episodes byte-identical to A0).
- **Test 4 (CRN identity):** 0 mismatches across all arms, including the
  corrected A4, over 300 episode indices.
- **Test 5 (responsiveness-signal null, Stage 4B narrowed formulation):**
  adaptive-vs-control effect +0.0383 at baseline concentration (pre-declared
  threshold: must exceed +0.02 - met), +0.0173 at high concentration
  (pre-declared tolerance: within ±0.02 - met). θ_c variance collapsed
  >1000×.

### Empirical A4 reference - not a target

The A4 headroom over A2 (+9.8 points invoice recovery, +4.9 points
subscription rescue) is an **empirical oracle/reference gap under this
simulator's defined information and 3-contact budget** - not a
mathematical theoretical maximum, and not a guaranteed target for a future
A3.

A4 provides an empirical oracle/reference of 0.5670 subscription rescue
and 0.5465 invoice recovery under the frozen simulator's equal 3-contact
budget; A4 − A2 headroom is +0.0490 rescue and +0.0980 invoice recovery;
`EVAL.md §3.3`'s cited "15% relative target" (the `§7` it names is
referenced but not written as a section anywhere in `EVAL.md` - the figure
itself is real text at `§3.3`, not a fabricated number) would require A3
to reach approximately 0.5957 rescue from the A2 baseline of 0.5180
(0.5180 × 1.15); this exceeds the observed A4 empirical oracle/reference
of 0.5670, so the pre-registered target appears unreachable under the
frozen simulator, equal 3-contact budget, and A4's information set - this
is an empirical finding about the target's reachability, **not** a change
to the target or to `EVAL.md`.

### Test reporting (kept separate, per this closure's instruction)

- **Ordinary regression suite** (everything except the intentional Stage 5
  falsification assertions): all PASS.
- **Stage 5 falsification suite:** 4 of 5 hypotheses PASS (timing null, CRN
  identity, responsiveness-signal null, wrong-remedy null); **1 of 5 FAILS/
  REJECTED** (the policy-ordering hypothesis, for the A1-vs-A2 reason
  above - not weakened or altered to obtain a pass).

`python -m ruff check .`: all checks passed. Not committed. `EVAL.md` and
`SIM.md` untouched throughout Stage 5.

## eval-spec-v1.2 — 2026-08-26

Closes the specification/test inconsistency the Day 2 Stage 4B review
identified: `EVAL.md §3.4` still specified its original 16-field
`EpisodeView` surface while the implementation (and `tests/
test_no_latent_leak.py`'s enforcing allowlist) had already moved to the
narrower 10-field v1 surface documented in `SIM.md §10`. `SIM.md §0`
authorizes *logging and reporting* such a conflict without editing
`EVAL.md`, but not permanently redefining the enforced surface as if that
resolved it - so `EVAL.md` needed an actual amendment, following the exact
precedent `eval-spec-v1.1` already established for
`send_subscription_link` (a `[DEFECT, eval-spec-vX]` footnote, the frozen
text recorded rather than rewritten).

### EVAL.md — one footnote added, frozen text unchanged

`git diff -- EVAL.md`: exactly one added block, directly below §3.4's
16-field list (verified - no other line in the file changed). The footnote
(`[DEFECT, eval-spec-v1.2]`):

- records that 6 of the 16 fields have no honest producer anywhere in the
  built simulator (`decline_source`, `billing_cycle_day`,
  `completed_billing_cycles`, `customer_tenure_days`,
  `prior_pending_episodes`, `prior_recovery_channel`) and were not
  fabricated - producing them would mean inventing a new `[MODEL]`
  parameter or mechanism outside the frozen six;
- records the two time-representation renames: `next_auto_retry_date` →
  `next_auto_retry_day`, `contact_history[].ts` → `.day` - no calendar
  anchor exists anywhere in this simulator, and none is invented;
- enumerates, for the first time in this file, the three pre-registered
  sources of A3 advantage §3.4's own title names but never previously
  listed explicitly (assembled from this file's field grouping and
  `SIM.md`'s cross-references), and states each one's v1 status:
  retry-window timing (fully preserved), remedy matching (preserved via
  `decline_code` alone), channel selection (narrowed to within-episode
  adaptive contact - persistent episode-level response propensity inferred
  from observable `contact_history.engaged`, with cross-episode
  customer-history learning and tenure-based inference explicitly out of
  v1).

The frozen 16-field list itself is untouched - it remains the target
surface for a future version, not a claim about what v1 delivers now.

### Complete schema delta (EVAL.md §3.4 original -> v1 EpisodeView)

**Removed (6, no producer anywhere in the repository, not fabricated):**
`decline_source`, `billing_cycle_day`, `completed_billing_cycles`,
`customer_tenure_days`, `prior_pending_episodes`, `prior_recovery_channel`.

**Renamed + type-changed (2, RULING 1 - relative time, no calendar anchor):**
`next_auto_retry_date: date | None` -> `next_auto_retry_day: int | None`;
`ContactRecord.ts: datetime` -> `ContactRecord.day: int`.

**Retained fields with narrowed/clarified semantics (2):**
- `billing_amount_inr` - name and type unchanged, but now explicitly
  aliased to `invoice_amount_inr` (no independent recurring-price figure
  exists anywhere in the repository) rather than left as an independently
  undefined quantity.
- `decline_code` - name and type unchanged (`str`), but now explicitly
  defined as the observable, group-level `opening_condition_key` (e.g.
  `"ambiguous_decline"` for that bucket) rather than an unspecified
  granularity.

**Retained, unchanged (6):** `subscription_id`, `subscription_state`,
`invoice_amount_inr`, `days_since_first_failure`, `auto_retries_remaining`,
`budget_remaining` - and `contact_history` itself (its entry shape changed
per the rename above, but the field's presence/role did not).

### tests/test_no_latent_leak.py - enforcing test now genuinely agrees with EVAL.md

Updated the module docstring and the `EPISODE_VIEW_ALLOWED` comment to
state plainly that this allowlist enforces the CURRENT (eval-spec-v1.2
amended) `EVAL.md §3.4`, not a stand-in that merely happens to be narrower
than it. No change to the allowlist's actual contents (already correct
from Stage 4B) or to any test's pass/fail behavior.

### Verification

- `python -m pytest -q`: see the closure report for the exact count.
- `python -m ruff check .`: all checks passed.
- `latent.py`, all of `configs/`, retry/outcome mechanics, and A0/A2 policy
  behavior confirmed unmodified.
- Tagged `eval-spec-v1.2` after tests were confirmed green (see the
  closure report for the exact commit SHA).

## Day 2 Stage 4B — 2026-08-26

Completes the minimum honest EpisodeView boundary identified by the Day 2
Stage 4 gap analysis: EpisodeView is now actually constructed from real
simulator state, with a deliberately narrowed field set rather than
fabricated values for the fields with no honest producer. No Stage 5, no
A3, no gates - out of scope per this pass's brief.

### RULING 1 — relative time, [DESIGN] schema ruling

No calendar anchor exists anywhere in this simulator, and none is invented.
`EpisodeView.next_auto_retry_date: date | None` → `next_auto_retry_day: int
| None`; `ContactRecord.ts: datetime` → `ContactRecord.day: int`. Recorded
in `SIM.md §10`.

### RULING 2 — decline_code, group-level

`EpisodeView.decline_code` is the observable `opening_condition_key` itself
- `"ambiguous_decline"` for that bucket, never the resolved latent
Bernoulli cause. Matches population.yaml's own note ("A3 and A2 both see
only decline_code for this bucket"). Additive observation only -
`rrx.sim.engine.build_episode_view` reads `cohort.opening_condition_key`;
nothing about outcome resolution changes.

### RULING 3 — decline_source removed

Not modeled in v1: the term is undefined anywhere in `EVAL.md`, `SIM.md`,
or any config (verified by repository-wide search). Removed from
`EpisodeView` rather than fabricated. **v1 makes the remedy-matching
decision using `decline_code` alone.** Recorded in `SIM.md §10`.

### RULING 4 — channel-selection narrowed; no cross-episode history model

`customer_tenure_days`, `prior_pending_episodes`, `prior_recovery_channel`
removed from `EpisodeView`. The v1 channel-selection advantage is narrowed
to within-episode adaptive contact: inferring persistent episode-level
response propensity from observable `contact_history.engaged` alone. This
is a genuine narrowing of `EVAL.md §3.4`'s third pre-registered advantage,
not a silent drop - full reasoning and what remains/is removed recorded in
`SIM.md §10`.

### RULING 5 — tenure coupling not implemented

Confirmed (again) that `rrx.sim.latent._sample_channel_response_trait`
implements only the raw `Beta(mean, concentration)` draw - no
`tenure_coupling` logit shift, no seventh model parameter, `latent.py`
untouched this pass. `SIM.md §8`'s falsification test #5 is given a
narrowed definition in `SIM.md §10` (concentration-only manipulation,
matching the mechanism that actually exists) - **recorded, not implemented
or run.** Stage 5 work.

### RULING 6 — contact_history, real runtime logging

`_EpisodeState.contact_history: list[ContactRecord]` (engine.py); every
`_send_message` call now appends a record built from values it already
computes (`day`, `channel`, a `remedy` derived from `names_card`/
`names_dues` - `"card_change"` / `"topup_reminder"` / `"both"` for the
dual-content automatic email, matching `SIM.md §3`'s own action table -
`delivered=True` per `SIM.md §3`'s `"delivered (1.0 in v1)"`, and the
already-resolved `engaged` bool). Purely observational: nothing reads
`contact_history` back into engagement probability, card/dues effects, the
retry gate, contact budget, or either policy. Confirmed by the full test
suite passing unchanged (537 passed, same A0/A2 outcome behavior as before
this pass).

### RULING 7 — EpisodeView actually constructed

`rrx.sim.engine.build_episode_view(cohort, state, day, episode_cfg, split,
i) -> EpisodeView` - a positive construction (every field copied out as a
plain value; never a reference to `state`, `cohort`, `LatentState`, or an
RNG). Wired into `run_episode` via a new, fully backward-compatible opt-in
parameter: `run_episode(..., capture_view_at_day=None)` returns the exact
same bare `EpisodeResult` as before when omitted (verified: every existing
Stage 3 test, including the byte-identical replay-determinism test, passes
unchanged); passing an integer day additionally returns
`(EpisodeResult, EpisodeView | None)`, the `EpisodeView` captured as of the
end of that day's mechanics (`None` if that day is never reached - the
`subscription_cancelled_by_customer` early-return path). No agent or
planner created; nothing consumes the view for policy decisions.

### RULING 8 — final field set, billing-fields investigation

Investigated per the ruling before implementing:
- `billing_amount_inr` — **retained**, aliased to `invoice_amount_inr`. No
  separate recurring-price figure exists anywhere in the repository;
  `model_params.yaml`'s `valued_at: billing_amount_inr` never distinguishes
  the two. Defensible equivalence, not invention.
- `billing_cycle_day`, `completed_billing_cycles` — **removed/deferred**.
  No distribution or producer exists anywhere in the repository for
  either. Not invented.
- `subscription_id` — `f"{split}-{i}"`, the deterministic existing episode
  identity, as directed.

**Final v1 EpisodeView field set (10 fields, down from EVAL.md §3.4's 16):**
`subscription_id`, `subscription_state`, `invoice_amount_inr`,
`days_since_first_failure`, `auto_retries_remaining`,
`next_auto_retry_day`, `decline_code`, `billing_amount_inr`,
`contact_history`, `budget_remaining`.

### RULING 9 — EVAL.md untouched; conflict recorded in SIM.md instead

`EVAL.md` was not modified. The narrowing conflict with `EVAL.md §3.4`'s
16-field list is recorded explicitly in `SIM.md §10` (new section, per
`SIM.md §0`'s own rule: conflicts with `EVAL.md` are "a defect to be logged
and reported, never resolved by editing `EVAL.md`"), and in this entry.
The v1 observable surface is narrower than `EVAL.md §3.4`'s original list;
this is stated plainly, not minimized.

### RULING 10 — tests

New `tests/test_episode_view_construction.py` (16 tests): real runtime
construction, backward-compatible default return, `None` on an unreached
day, capture determinism, `contact_history` population and remedy mapping,
no-simulator-object check on real constructed instances, relative-day
retry-window fields (before/during/after halt), `decline_code` group-level
mapping (including `ambiguous_decline` specifically), `billing_amount_inr`
aliasing, and removed-fields-absent. `tests/test_no_latent_leak.py` updated
for the narrowed allowlists (`EPISODE_VIEW_ALLOWED`, `CONTACT_RECORD_
ALLOWED`, `_ALLOWED_FIELD_TYPES` - `date`/`datetime` dropped, no longer
used by any field) - all 18 of its tests (12 pre-existing Stage 4 + this
pass's field-set updates) still pass.

### Verification

- Targeted: `tests/test_no_latent_leak.py` (18 passed),
  `tests/test_episode_view_construction.py` (16 passed).
- `python -m pytest -q`: 537 passed.
- `python -m ruff check .`: all checks passed.
- `latent.py`, all of `configs/`, `EVAL.md`, retry/outcome mechanics, and
  A0/A2 policy behavior confirmed unmodified.
- Not committed.

## Day 2 Stage 3 — 2026-08-26

Thin end-to-end simulator: cohort generator, clock/retry engine,
action-effect resolver, A0, A2, and the first reproducible A0-vs-A2 result.
No A3, no manifest, no holdout, no Razorpay integration - out of scope per
this stage's brief.

### Discovered defect, fixed (authorized): `blocked_until` default

`src/rrx/sim/latent.py::draw_latent_state` defaulted `blocked_until` to
`BLOCKED_INDEFINITELY` (`math.inf`) unconditionally, overriding it only for
`bank_technical_error`. Since SIM.md §4's retry AND-gate requires
`t >= blocked_until` for every condition, this silently made auto-retry
success impossible for `insufficient_funds`, `ambiguous_decline`,
`card_expired`, `debit_instrument_blocked`, and `card_not_enabled_group` -
91% of the population - regardless of `card_chargeable`/
`funds_available_from`. This contradicted SIM.md §3's explicit claim that
transient-mode `insufficient_funds` customers recover "with no agent
action," and SIM.md's own "Discovered semantic clarification" scopes the
indefinite-block reading of "never" to `transaction_limit_exceeded` /
`payment_risk_check_failed` only. Confirmed empirically before the fix: a
2000-episode A0 dev run recovered invoices only via `bank_technical_error`
(51/51), zero via `insufficient_funds`.

Fix (authorized by user decision, 2026-08-26): default changed to `0.0`
(non-blocking); `transaction_limit_exceeded`/`payment_risk_check_failed`
now set `BLOCKED_INDEFINITELY` explicitly. Updated the three locked-behavior
assertions in `tests/test_latent_sampling.py` and re-pinned the four
affected cases in `tests/test_latent_snapshot.py` (the snapshot correctly
failed on this change - exactly what it exists to catch; only `blocked_until`
moved, every other pinned field is unchanged).

### Three model clarifications - applied to SIM.md (Day 2 Stage 3 final closing pass, 2026-08-26)

Recorded directly in `SIM.md` (§2, §4, §5) in this pass, labeled "Model
ruling" with the date, per CLAUDE.md's locked-file rule (edits authorized by
explicit user instruction). Earlier revisions of this changelog entry and of
`engine.py`'s docstrings described these as "approved 2026-08-26" while
still unrecorded in SIM.md; that was inaccurate and was corrected before
this pass ever labeled anything "approved" prematurely again.

- **Within-day ordering (SIM.md §4).** A message sent and engaged with on
  day t changes physical state before that day's end-of-day retry reads it.
  Implemented in `rrx.sim.engine._send_message` / `run_episode`'s day loop:
  contacts/emails scheduled for day t are resolved before day t's retry
  check.
- **`blocked_until` "never" (SIM.md §2).** Non-blocking (`0.0`) for every
  row except `transaction_limit_exceeded`/`payment_risk_check_failed`,
  which receive the indefinite-block value explicitly. See the "Discovered
  defect" entry below - this is the specification-level record of that
  fix.
- **Post-halt card rescue, narrower form (SIM.md §5).** Only episodes whose
  `card_chargeable` was `false` AT OPENING may be rescued post-halt when
  `card_chargeable` becomes `true`. Episodes already `card_chargeable =
  true` at opening (`insufficient_funds`, `transaction_limit_exceeded`,
  `payment_risk_check_failed`) never transition to `active` merely because
  a post-halt message occurs.

  **Why this rule exists - discovered implementation bug it fixes:** the
  ORIGINAL (broader) rule as first implemented tested the CURRENT value of
  `card_chargeable` at the end of every post-halt message, not whether that
  message caused a false→true TRANSITION. Since `insufficient_funds`/
  `transaction_limit_exceeded`/`payment_risk_check_failed` all have
  `card_chargeable = true` from T=0 (SIM.md §2), this meant the halt-
  transition automatic email alone flipped `subscription_state` to
  `"active"` unconditionally the instant it was sent, with no engagement
  required. Confirmed empirically before the fix: of 2000 dev episodes,
  every single non-recovered `insufficient_funds` (195/195), `transaction_
  limit_exceeded` (23/23), and `payment_risk_check_failed` (21/21) episode
  was reported as rescued (100%). Card-broken/ambiguous-decline buckets
  were unaffected in practice, because for those, `card_chargeable`
  becoming true pre-halt would already have recovered the invoice on the
  next retry day, so halting with `card_chargeable` already true could only
  happen via the very message being evaluated.

  **Fixed:** `_EpisodeState` now records `card_chargeable_at_opening` once,
  at construction, and `_send_message`'s rescue check requires it to be
  `False`. Re-ran the 2000-episode dev smoke after the fix: of the same
  195/23/21 non-recovered episodes, 0/0/0 are now reported as rescued -
  confirming the fix is genuinely connected to the runtime path, not merely
  documented. A0/A2 subscription rescue rate dropped from 0.5850/0.6850 to
  0.4055/0.5180; invoice recovery rate (0.3525/0.4485) is unchanged, as
  expected - this fix only ever touches `subscription_rescued`.

### A2 policy verified against the repository, not memory (Day 2 Stage 3 final closing pass, 2026-08-26)

Searched `EVAL.md`, `SIM.md`, `configs/`, and the whole repository for any
written A2 reference-policy schedule. Finding: **none exists.** `EVAL.md`
has no `## 4.` heading (confirmed again by listing every `##`/`###`
heading - the file jumps `## 3. Population` -> `## 5. Metrics`). `SIM.md`
defines world mechanics only and never prescribes agent policy. No
policy/reference-policy file exists anywhere in `configs/` or the repo
(confirmed by search - the only files matching "reference policy"/"a2
policy" are this changelog and `engine.py` itself). `EVAL.md §3.2`'s table
states `insufficient_funds`'s remedy as "Top-up reminder **before** retries
exhaust" with no mention of any card-change fallback, at T+5 or otherwise.
No occurrence of the string "T+5" exists in `EVAL.md` or `SIM.md` at all.

**Conclusion: the entire A2 day-offset schedule in `rrx.sim.engine.
a2_action_for_day` - including every T+0/T+1/T+5/T+7 in it - was dictated
directly in conversation and has no other source.** It was never copied
from EVAL.md; describing it as "EVAL.md §4's reference policy" (as an
earlier turn did) does not resolve to real text in the file. This is not a
new finding this pass invented - it restates and confirms what the Stage 3
audit already established about `§4` not existing - but this pass
additionally confirms there is no T+5-for-`insufficient_funds` rule
anywhere in the written spec to have a discrepancy against: the current
code (no fallback for `insufficient_funds`, ever) matches the *absence* of
any such written rule, and separately matches `EVAL.md §5.2`'s actual,
real, written gate ("Card-change prompts for `insufficient_funds`: 0",
`test_gate_remedy_match.py`, which does not exist yet as a file). The
previously-written "`EVAL.md §5.2` supersedes `§4`" framing is dropped -
there is no `§4` for anything to supersede. `engine.py`'s
`a2_action_for_day` docstring has been corrected accordingly.

### New simulator modules

- `src/rrx/sim/rng.py`: `rng_for_child_stream` - extends the frozen
  per-variable substream isolation to per-message/per-engagement draws via
  `seed_for_substream`'s existing hash (`"<root>:<child>"`), without a ninth
  top-level substream and without modifying `latent.py`'s frozen
  `SUBSTREAM_NAMES`/`rng_for_substream`.
- `src/rrx/sim/cohort.py`: opening-condition selection (from the
  authoritative `population.yaml#/failure_mix/conditions`, via a
  `failure_condition:opening_condition_select` child stream kept independent
  of the existing ambiguous-cause Bernoulli) and invoice-amount sampling
  (first real use of the `invoice_amount` substream; authority resolved by
  the same `owner_path` convention that resolved failure-mix -
  `tests/test_invoice_amount_representations_agree.py` confirms
  `population.yaml`/`episode.yaml`'s two invoice representations agree at
  baseline).
- `src/rrx/sim/engine.py`: the clock, retry AND-gate, action-effect
  resolver (card-naming, dues-naming/top-up), A0 (no contact, ever) and A2
  (EVAL.md §5.2-compliant reference policy - `insufficient_funds` gets only
  a T+1 top-up, never a card-change fallback, so the "0 card-change prompts
  for insufficient_funds" gate holds by construction).
- `src/rrx/sim/run_stage3.py`: batch A0/A2 run (dev, 2000 episodes, seeds
  1000-2999) plus paired bootstrap 95% CI (reusing
  `model_params.yaml#/sweep/win_criterion`'s existing convention, not a new
  statistical framework). Prints to stdout only - no manifest, no results
  directory.

### Tests

`tests/test_cohort.py`, `test_engine_mechanics.py`, `test_engine_policies.py`,
`test_topup_crn.py`, `test_stage3_run.py`,
`test_invoice_amount_representations_agree.py` (new);
`test_failure_mix_representations_agree.py` now imports its key-mapping from
`rrx.sim.cohort` instead of a duplicated local copy.

### Regime A cancellation - not implemented (scope exclusion, not a gap to silently fill)

No cancellation-hazard mechanism exists anywhere in `rrx.sim.engine` -
nothing reads `episode_cfg["latent"]["cancellation"]`, no hazard draw, no
LTV computation. This was an explicit, stated Stage 3 scope exclusion (the
10-item SIMULATOR SCOPE list has no cancellation/Regime A item), not
something dropped silently. Consequence: there is no runtime "Regime A
cancellation cannot occur in Regime B" gate to test, because there is no
Regime A mechanism for such a gate to guard. Any claim that Stage 3
validates Regime A/Regime B cancellation-gating behavior would be false -
Stage 3 validates nothing about cancellation, in either direction, and no
test in this stage's suite asserts otherwise. This must be built as real
work in a later stage, not invented to make a test pass.

### Stage 3 closing pass — 2026-08-26

- Added `test_no_retry_evaluated_after_halt_even_if_and_gate_would_pass`
  (`tests/test_engine_mechanics.py`): monkeypatches `draw_latent_state`/
  `sample_cohort_episode` to force a state that provably satisfies the full
  retry AND-gate on a post-halt day, and confirms `invoice_recovered`
  stays `False` - closing the coverage gap flagged in the Stage 3 audit
  (previously only a statistical, black-box observation existed).
- Added `test_run_episode_full_replay_is_byte_identical`
  (`tests/test_engine_mechanics.py`): calls `run_episode()` twice with
  identical inputs across both arms and 120 episode indices, asserting full
  `EpisodeResult` equality - exercises the engine's own engagement/
  completion/topup RNG consumption, not just cohort/latent determinism -
  closing the other coverage gap flagged in the audit.
- Added a `payment_risk_check_failed` case to
  `tests/test_latent_snapshot.py`, pinning `blocked_until ==
  BLOCKED_INDEFINITELY` for it. The blocked_until defect fix's `elif key in
  ("transaction_limit_exceeded", "payment_risk_check_failed")` branch
  previously had only `transaction_limit_exceeded` pinned by a snapshot
  case; a future edit dropping `payment_risk_check_failed` from that tuple
  would have passed every existing snapshot test.
- Corrected "approved 2026-08-26" language in `engine.py`'s module
  docstring and `a2_action_for_day`'s docstring, and "frozen rulings" in
  `test_engine_mechanics.py`'s docstring, to accurately describe both
  rulings as proposed/pending - neither has been approved or written into
  SIM.md.
- `src/rrx/sim/run_stage3.py`: renamed the printed/reported metric labels
  "wasted attempts" → `no_op_contacts` and "hard-decline retry rate" →
  `remedy_mismatch_rate`, since there are no agent-controlled payment-retry
  attempts in this model (Razorpay's auto-retry is the only retry mechanism,
  and the agent has no retry action at all - EVAL.md §1.1/§1.2) and
  describing a mismatched contact as a "retry attempt" or "hard decline
  retry" mischaracterizes what it actually is (a contact whose content
  didn't change physical state). Underlying calculations unchanged; only
  the local variable names and printed labels moved.

### Final closing pass — narrower rescue implemented, SIM.md updated (2026-08-26)

- Implemented the narrower post-halt rescue rule in `rrx.sim.engine`
  (`_EpisodeState.card_chargeable_at_opening`, gated check in
  `_send_message`) - see above.
- Added `test_a_card_broken_at_open_episode_can_be_post_halt_rescued`,
  `test_b_already_chargeable_at_open_episode_cannot_be_post_halt_rescued`,
  and `test_insufficient_funds_and_kin_structurally_cannot_be_post_halt_
  rescued` to `tests/test_engine_mechanics.py`.
- Applied all three model clarifications to `SIM.md` (§2, §4, §5), labeled
  "Model ruling (2026-08-26, Day 2 Stage 3 closing)" - see above.
- Verified the A2 policy against the actual repository contents (see above)
  and corrected `engine.py`'s docstrings accordingly.
- Re-ran the 2000-episode dev smoke; numbers reported in the Stage 3 final
  closing report (not reproduced here to avoid a second source of truth for
  a non-formal smoke run).

### Verification

- `python -m pytest -q`: 515 passed.
- `python -m ruff check .`: all checks passed.
- No frozen spec file modified except the three authorized `SIM.md`
  clarifications recorded above; `EVAL.md`, all of `configs/`, and
  `data/decline_codes.yaml` remain untouched.

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
