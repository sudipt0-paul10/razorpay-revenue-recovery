"""Canonical A1 — adopted `eval-spec-v1.6` (`EVAL.md §4.3`,
`[CONSEQUENTIAL-2]`).

`EVAL.md §4`'s A1 row ("Same two contacts to everyone at T+0 and T+3,
regardless of state or reason") froze A1's SCHEDULE from this project's
original authorship onward. It never specified the contact's
remedy/content - that gap sat open until `eval-spec-v1.6`.

The implementation below is behaviorally IDENTICAL to
`tests/test_stage5_falsification.py::a1_action_for_day`, the Stage-5
"A1-ish" diagnostic construction (introduced Day 2 Stage 5, commit
`cdd118a`) whose own docstring there states the `card_change` content
choice was "declared here, since the task does not specify one" - an
admission it was invented for a falsification test, not derived from
frozen text. That construction was never itself canonical; `EVAL.md
§4.3` records the full provenance chain and the mechanism-based rationale
for adopting `card_change` (not `topup_reminder`) as this project's
formal, consequential decision.

This module makes that adopted operationalization canonical and
importable from production code - the same treatment
`src/rrx/baselines/a2_variants.py` already gives A2-corrected-v1/A2-
strengthened. `tests/test_stage5_falsification.py` imports
`a1_action_for_day` from here rather than maintaining a second local
definition; its own historical "A1-ish" label and diagnostic framing are
preserved in that file's comments as provenance, not erased.

No behavior change from the diagnostic construction. No adaptivity: no
`Proposal`, no gate, no `reason_code`, no engagement/state/decline-code
awareness of any kind - `EVAL.md §4.3`'s explicit reading is that A1's
naive, ungated behavior is its deliberate strawman role, not something
this module should soften.

Matches `rrx.sim.engine`'s standard
`(opening_condition_key, day, subscription_state) -> action | None`
policy-callable interface, so it can be registered into
`engine._POLICIES` the same way `a2_strengthened_action_for_day` already
is (`src/rrx/eval/arms.py`, `tests/test_a2_variants.py`). `rrx.sim.engine`
is never imported or modified by this module.
"""

from __future__ import annotations


def a1_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """Canonical A1 (`EVAL.md §4`, content adopted `EVAL.md §4.3`
    `eval-spec-v1.6`): `card_change` at T+0 and T+3, for every episode,
    regardless of `opening_condition_key` or `subscription_state` - no
    remedy matching, no adaptivity. `opening_condition_key` and
    `subscription_state` are accepted only to match the standard policy
    signature; neither is read."""
    return "card_change" if day in (0, 3) else None
