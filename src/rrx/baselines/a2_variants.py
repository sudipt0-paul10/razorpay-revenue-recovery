"""A2 baseline variants — Day 3 approved corrections/strengthening.

DELIBERATELY OUTSIDE `src/rrx/sim/`: sim-v1 (commit
bbfa55d68a97ca9f41a9b151477b193db5054ffe) freezes `src/rrx/sim/` including
`engine.py`'s `a2_action_for_day` (the "A2-original" policy). This module
does not import, monkeypatch, or otherwise mutate anything in `rrx.sim` -
it defines two NEW policy callables with `rrx.sim.engine`'s own
`(opening_condition_key, day, subscription_state) -> action | None`
interface, delegating to `engine.a2_action_for_day` for every branch that
is unchanged. They can be registered into `rrx.sim.engine._POLICIES` at
runtime under new arm keys (e.g. "A2_CORRECTED_V1", "A2_STRENGTHENED") the
same way `tests/test_stage5_falsification.py` already registers "A1" -
`engine.py`'s source is never touched, and the existing "A0"/"A2" keys
(A2-original) are never overwritten, so A2-original stays reproducible
under its own name.

Four independently-justified changes vs `engine.a2_action_for_day`, kept
distinct per the Day 3 review's explicit instruction not to blur
correction and strengthening rationales:

1. Card-broken bucket (`card_expired`, `debit_instrument_blocked`,
   `card_not_enabled_group`): second card_change contact moves T+5 -> T+3
   ["CORRECTION" — `a2_corrected_v1_action_for_day` and
   `a2_strengthened_action_for_day` both apply this]. Justified purely by
   EVAL.md §1.1/§1.3 ("auto-retries T+1...T+3" / "invoice recovery... only
   possible while auto-retries remain") plus `episode.yaml`'s own
   `halt_boundary_day: 3` - a T+5 contact for this bucket's invoice-
   relevant remedy is scheduled at a day the frozen simulator's own
   boundary makes structurally invoice-irrelevant, independent of any
   comparison to A1/A4.

2. Card-broken bucket: T+5 restored as a THIRD contact (T+0/T+3/T+5)
   ["STRENGTHENING", `a2_strengthened_action_for_day` only]. Not a
   correction of (1) - a deliberate use of the 3rd budget slot
   (`episode.yaml#/agent_budget/max_contacts_per_episode: 3`) for a
   post-halt rescue attempt. `episode.yaml#/payment_method_change_effect/
   while_halted` already names `subscription_rescued` as a reachable
   outcome, and `engine.py`'s existing (unmodified) post-halt-rescue block
   fires for exactly this bucket, since `card_chargeable_at_opening=False`
   for all three card-broken keys. Day 3 diagnostic measured a real
   rescue-rate gain from this addition with zero invoice-recovery cost.

3. `bank_technical_error`: the T+5 card_change contact is now guarded by
   `subscription_state in ("pending", "halted")` ["CORRECTION" - both
   variants]. This restores, verbatim, a conditional clause
   ("card-change prompt at T+5 if still failing") that was present in the
   EVAL.md §4 text committed before commit 337e0060e9f5af013e4b8362623a0
   4e57a8f3f66101d deleted §4 - `engine.a2_action_for_day`'s existing
   implementation dropped this guard, and since `blocked_until` for this
   condition is always <= 2 (episode.yaml's `bank_technical_error_
   clearance` support is `[0, 2]`, retry_days include day 2), recovery is
   *always* already resolved before day 5, so the unguarded version sends
   a guaranteed-useless contact 100% of the time (confirmed empirically
   on the dev cohort: 51/51 bank_technical_error episodes). This is a
   restoration of previously-written intent, not new design.

4. `transaction_limit_exceeded`: the T+5 card_change fallback is removed
   entirely, leaving only the T+1 topup_reminder ["CORRECTION" - both
   variants]. `latent.py`'s `_MECHANISM_ISOLATED_KEYS` branch draws
   `card_chargeable=True` at opening for this condition, identically to
   `insufficient_funds` - `_apply_card_naming_effect` is therefore an
   equally guaranteed no-op here, which is exactly the situation EVAL.md
   §5.2's remedy-match gate ("Card-change prompts for insufficient_funds:
   0") already exists to prevent. The gate's literal text names only
   `insufficient_funds`; this widens the same underlying principle to the
   mechanically identical condition, rather than leaving an inconsistent
   carve-out. `blocked_until=BLOCKED_INDEFINITELY` means the invoice can
   never recover in-window regardless of this fallback either way, so the
   change affects only wasted-contact accounting, never the invoice/
   rescue metrics (confirmed empirically: 0% for this condition under
   every arm tested).

All other opening conditions (`insufficient_funds`, `ambiguous_decline`,
`subscription_cancelled_by_customer`, `payment_risk_check_failed`) are
untouched and delegate to `engine.a2_action_for_day` unchanged.
"""

from __future__ import annotations

from rrx.sim import engine


def a2_corrected_v1_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """A2-original with changes (1), (3), (4) above. Same contact COUNT as
    A2-original for the card-broken bucket (2 contacts, just retimed)."""
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3) else None

    if opening_condition_key == "bank_technical_error":
        if day == 5 and subscription_state in ("pending", "halted"):
            return "card_change"
        return None

    if opening_condition_key == "transaction_limit_exceeded":
        return "topup_reminder" if day == 1 else None

    return engine.a2_action_for_day(opening_condition_key, day, subscription_state)


def a2_strengthened_action_for_day(
    opening_condition_key: str, day: int, subscription_state: str
) -> str | None:
    """a2_corrected_v1_action_for_day PLUS change (2): the card-broken
    bucket's third, post-halt rescue-only contact at T+5. Uses the full
    3-contact budget for that bucket; every other condition is identical
    to a2_corrected_v1_action_for_day."""
    if opening_condition_key in engine._CARD_BROKEN_KEYS:
        return "card_change" if day in (0, 3, 5) else None
    return a2_corrected_v1_action_for_day(opening_condition_key, day, subscription_state)
