"""Canonical A1 (`src/rrx/baselines/a1.py`) — enforcing tests for the
`eval-spec-v1.6` (`EVAL.md §4.3`, `[CONSEQUENTIAL-2]`) adoption.

Mirrors `tests/test_a2_variants.py`'s conventions for the sibling baseline
module. Two concerns, kept separate:

1. Behavioral equivalence: canonical `a1_action_for_day` must produce
   exactly the same output, for every day 0-30, that the original
   `tests/test_stage5_falsification.py`-local "A1-ish" definition did
   (`"card_change" if day in (0, 3) else None`) - the relocation must not
   have changed a single decision.
2. Enforcement of the frozen `eval-spec-v1.6` operationalization itself:
   schedule exactly {0, 3}, remedy exactly `card_change`, independent of
   `opening_condition_key`/`subscription_state`, no other day contacts.

No adaptivity, no gate, no `Proposal`/`reason_code` machinery is
introduced or tested here - `EVAL.md §4.3` is explicit that A1's naive,
ungated behavior is its deliberate strawman role, not something to soften.
"""

from __future__ import annotations

import pytest

from rrx.agent.reason_codes import ALL_DECLINE_CODES
from rrx.baselines.a1 import a1_action_for_day

_ALL_STATES = ("pending", "halted", "active", "cancelled")
# Every real decline_code, plus the one non-decline-code opening-condition
# key ("regardless of ... reason" must hold even for a key a1_action_for_day
# was never written to special-case) and an arbitrary unknown string, since
# the function is documented to never read this parameter at all.
_ALL_CONDITION_KEYS = sorted(ALL_DECLINE_CODES) + [
    "subscription_cancelled_by_customer",
    "totally_unrecognized_key",
]


# ---------------------------------------------------------------------------
# 1. Behavioral equivalence with the pre-relocation "A1-ish" definition
# ---------------------------------------------------------------------------

def _original_a1_ish(opening_condition_key: str, day: int, subscription_state: str) -> str | None:
    """The exact pre-relocation body, reproduced verbatim here ONLY as a
    fixed comparison target for the equivalence check below - not
    imported, not reused elsewhere, so this test does not depend on the
    canonical module to define its own oracle."""
    return "card_change" if day in (0, 3) else None


@pytest.mark.parametrize("day", range(0, 31))
@pytest.mark.parametrize("condition_key", _ALL_CONDITION_KEYS)
@pytest.mark.parametrize("state", _ALL_STATES)
def test_canonical_a1_matches_pre_relocation_behavior_exactly(condition_key, day, state):
    """The relocation from tests/test_stage5_falsification.py into
    src/rrx/baselines/a1.py must not have changed a single decision, for
    any day 0-30, any condition, any state."""
    assert a1_action_for_day(condition_key, day, state) == _original_a1_ish(
        condition_key, day, state
    )


# ---------------------------------------------------------------------------
# 2. Enforcement of the frozen eval-spec-v1.6 operationalization
# ---------------------------------------------------------------------------

def test_canonical_a1_schedule_is_exactly_day_0_and_3():
    contact_days = {
        day for day in range(0, 31)
        if a1_action_for_day("card_expired", day, "pending") is not None
    }
    assert contact_days == {0, 3}


def test_canonical_a1_remedy_is_exactly_card_change():
    assert a1_action_for_day("card_expired", 0, "pending") == "card_change"
    assert a1_action_for_day("card_expired", 3, "pending") == "card_change"


def test_canonical_a1_never_proposes_topup_reminder():
    """eval-spec-v1.6 explicitly did not adopt topup_reminder (EVAL.md
    §4.3's decision-space paragraph) - this must never appear."""
    for key in _ALL_CONDITION_KEYS:
        for day in range(0, 31):
            for state in _ALL_STATES:
                assert a1_action_for_day(key, day, state) != "topup_reminder"


@pytest.mark.parametrize("day", (0, 3))
@pytest.mark.parametrize("condition_key", _ALL_CONDITION_KEYS)
@pytest.mark.parametrize("state", _ALL_STATES)
def test_canonical_a1_content_days_are_independent_of_condition_and_state(
    condition_key, day, state
):
    """§4's 'regardless of state or reason' - the contact days' remedy
    must be card_change no matter which decline_code/state is passed."""
    assert a1_action_for_day(condition_key, day, state) == "card_change"


@pytest.mark.parametrize("day", [d for d in range(0, 31) if d not in (0, 3)])
def test_canonical_a1_no_contact_on_any_other_day(day):
    for key in _ALL_CONDITION_KEYS:
        for state in _ALL_STATES:
            assert a1_action_for_day(key, day, state) is None
