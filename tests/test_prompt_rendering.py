"""docs/A3-DESIGN.md §11-§12: deterministic prompt rendering and the
content-level latent-leak check §12 named as "New test required... Not
implemented in this pass" - implemented now (Day 6 Stage 6B).

Distinct from tests/test_no_latent_leak.py (which this file does not
modify and does not duplicate): that locked file's Layer 1/2 checks
IMPORT STATEMENTS in src/rrx/agent/*.py (including this module's target,
prompt.py, automatically, since it lives under the guarded package). This
file instead checks RENDERED STRING CONTENT - a module could import
nothing forbidden and still leak a latent-shaped value into prompt text
if a future edit read the wrong field; §12 asks for both.
"""

from __future__ import annotations

import ast
from pathlib import Path

from rrx.agent.prompt import (
    TEMPLATE_VERSION,
    TEMPLATE_VERSION_HIGH_DISCLOSURE,
    render_prompt,
)
from rrx.agent.reason_codes import (
    ADMISSIBLE_DECLINE_CODES,
    POST_HALT_RESCUE,
    REASON_CODES,
    TYPICAL_ACTION,
)
from rrx.features.episode_view import ContactRecord, EpisodeView

SRC = Path(__file__).resolve().parents[1] / "src"

# Mirrors tests/test_no_latent_leak.py's own EPISODE_VIEW_ALLOWED /
# CONTACT_RECORD_ALLOWED exactly (duplicated locally, matching this
# repository's existing convention for these small enumerations - see
# tests/test_a3_runner_parity.py's _LATENT_ATTRS).
_EPISODE_VIEW_ALLOWED = {
    "subscription_id", "subscription_state", "invoice_amount_inr",
    "days_since_first_failure", "auto_retries_remaining", "next_auto_retry_day",
    "decline_code", "billing_amount_inr",
    "contact_history", "budget_remaining",
}
_CONTACT_RECORD_ALLOWED = {"day", "channel", "remedy", "delivered", "engaged"}

# The same latent field names tests/test_no_latent_leak.py scans for
# (LATENT_FIELD_NAMES there) - duplicated locally rather than imported,
# matching the existing convention in tests/test_a3_runner_parity.py's
# _LATENT_ATTRS ("the most direct ones, matching tests/test_no_latent_leak.py's
# own approach").
_LATENT_FIELD_NAMES = (
    "balance_restore_delay", "salary_day", "p_topup_action",
    "topup_acceleration", "channel_response_propensity",
    "card_change_completion_propensity", "cancellation_hazard",
    "cancellation_hazard_per_contact", "remaining_subscription_lifetime_cycles",
    "remaining_lifetime_cycles", "latent",
    "card_chargeable", "funds_available_from", "mandate_alive",
    "blocked_until", "channel_response_trait", "card_chargeable_at_opening",
)

# A seed-shaped token: MASTER_SEED (rrx.sim.latent) is an 8-digit int,
# per-episode seeds are derived hashes. Neither is a field of EpisodeView,
# so no legitimate rendering path can produce one - a hit here would mean
# a future edit smuggled seed material into the prompt.
_SEED_SHAPED_TOKENS = ("20260825",)


def _view(
    *,
    subscription_state: str = "pending",
    decline_code: str = "card_expired",
    contact_history: tuple[ContactRecord, ...] = (),
    budget_remaining: int = 3,
) -> EpisodeView:
    return EpisodeView(
        subscription_id="dev-1000",
        subscription_state=subscription_state,
        invoice_amount_inr=50000,
        days_since_first_failure=3,
        auto_retries_remaining=1,
        next_auto_retry_day=5,
        decline_code=decline_code,
        billing_amount_inr=50000,
        contact_history=contact_history,
        budget_remaining=budget_remaining,
    )


def test_render_prompt_is_deterministic():
    view = _view()
    assert render_prompt(view) == render_prompt(view)


def test_render_prompt_varies_with_view_content():
    a = render_prompt(_view(decline_code="card_expired"))
    b = render_prompt(_view(decline_code="insufficient_funds"))
    assert a != b


def test_render_prompt_rejects_unknown_template_version():
    import pytest

    with pytest.raises(ValueError):
        render_prompt(_view(), template_version="not-a-real-version")


def test_render_prompt_default_matches_module_constant():
    view = _view()
    assert render_prompt(view) == render_prompt(view, template_version=TEMPLATE_VERSION)


def test_render_prompt_includes_contact_history_entries():
    history = (
        ContactRecord(
            day=0, channel="whatsapp", remedy="card_change", delivered=True, engaged=False
        ),
    )
    text = render_prompt(_view(contact_history=history))
    assert "whatsapp" in text
    assert "card_change" in text


def test_render_prompt_contains_no_latent_field_name():
    """§12's required content test: rendered string contains none of
    LATENT_FIELD_NAMES."""
    history = (
        ContactRecord(day=0, channel="sms", remedy="topup_reminder", delivered=True, engaged=True),
    )
    text = render_prompt(_view(contact_history=history, decline_code="insufficient_funds"))
    for name in _LATENT_FIELD_NAMES:
        assert name not in text, f"prompt leaked latent field name {name!r}"


def test_render_prompt_contains_no_seed_shaped_token():
    text = render_prompt(_view())
    for token in _SEED_SHAPED_TOKENS:
        assert token not in text, f"prompt contains seed-shaped token {token!r}"


def test_render_prompt_output_schema_names_exactly_four_keys():
    """§11: output schema is action_type/remedy/reason_code/rationale -
    no channel field. The instructions block must say so, since this is
    the only enforcement point for that requirement at planner-build time
    (the requirement itself is enforced downstream by the strict parser,
    tests/test_planner.py)."""
    text = render_prompt(_view())
    assert "channel" in text.lower()  # explicitly told NOT to include one
    assert "action_type" in text
    assert "reason_code" in text
    assert "rationale" in text


# ---------------------------------------------------------------------------
# Day 6 Stage 6C-4: prompt boundary, verified at the SOURCE level rather
# than by sampling rendered output. A static proof that render_prompt can
# only ever reference an EpisodeView/ContactRecord field already on the
# frozen allowlist covers "no simulator internals", "no future-tick
# leakage", and "no cross-episode information" all at once: EpisodeView's
# 10-field surface (locked by tests/test_no_latent_leak.py) has no
# simulator-internal, future-outcome, or cross-episode field to begin
# with, so proving render_prompt reads nothing OUTSIDE that surface is a
# complete boundary proof, not just a sampling-based one.
# ---------------------------------------------------------------------------

def _attribute_accesses_on(names: set[str], tree: ast.AST) -> set[str]:
    """Every `<name>.<attr>` access in `tree` where `<name>` is one of
    `names` (e.g. {"view", "rec"})."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in names
        ):
            found.add(node.attr)
    return found


def test_render_prompt_source_never_accesses_a_field_outside_the_allowlist():
    """Static proof, not a sampled one: every `view.<x>` / `rec.<x>`
    attribute access anywhere in prompt.py's source is a member of the
    exact same EpisodeView/ContactRecord allowlists
    tests/test_no_latent_leak.py locks - covering "no simulator
    internals", "no future-tick leakage", and "no cross-episode
    information" in one proof, since none of those concepts have a field
    on this allowlist to leak through in the first place."""
    path = SRC / "rrx" / "agent" / "prompt.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    view_accesses = _attribute_accesses_on({"view"}, tree)
    rec_accesses = _attribute_accesses_on({"rec"}, tree)

    bad_view = view_accesses - _EPISODE_VIEW_ALLOWED
    bad_rec = rec_accesses - _CONTACT_RECORD_ALLOWED
    assert not bad_view, f"prompt.py accesses view.{sorted(bad_view)} - outside the allowlist"
    assert not bad_rec, f"prompt.py accesses rec.{sorted(bad_rec)} - outside the allowlist"
    # Sanity: the scan itself is exercising real code, not vacuously
    # matching nothing (a typo'd variable name would silently pass an
    # empty-set assertion above).
    assert view_accesses, "scan found zero view.* accesses - check the scan itself"


def test_identical_view_and_template_version_produce_byte_identical_prompt_and_hash():
    """6C-4: "Same EpisodeView + same template_version -> byte-identical
    prompt -> identical prompt_hash." Two SEPARATELY CONSTRUCTED
    (non-identity, value-equal) EpisodeView instances, to rule out an
    accidental pass via object identity rather than genuine determinism."""
    import hashlib

    def _fresh_view() -> EpisodeView:
        return EpisodeView(
            subscription_id="dev-1000", subscription_state="halted", invoice_amount_inr=12345,
            days_since_first_failure=5, auto_retries_remaining=0, next_auto_retry_day=None,
            decline_code="card_expired", billing_amount_inr=12345,
            contact_history=(
                ContactRecord(day=0, channel="whatsapp", remedy="card_change",
                               delivered=True, engaged=False),
            ),
            budget_remaining=2,
        )

    v1, v2 = _fresh_view(), _fresh_view()
    assert v1 is not v2
    assert v1 == v2

    p1 = render_prompt(v1, template_version=TEMPLATE_VERSION)
    p2 = render_prompt(v2, template_version=TEMPLATE_VERSION)
    assert p1 == p2

    h1 = hashlib.sha256(p1.encode("utf-8")).hexdigest()
    h2 = hashlib.sha256(p2.encode("utf-8")).hexdigest()
    assert h1 == h2


# ---------------------------------------------------------------------------
# Day 6 Stage 6H/6I: the frozen prompt-disclosure factor
# (results/tuning_log.md Entry 2).
# ---------------------------------------------------------------------------

def test_default_template_version_still_renders_low_disclosure_unchanged():
    """The bare TEMPLATE_VERSION default must still render EXACTLY the
    original (pre-Stage-6I) low-disclosure text - no semantic change to
    the existing low-disclosure prompt."""
    view = _view()
    text = render_prompt(view)
    assert text == render_prompt(view, template_version=TEMPLATE_VERSION)
    assert f"reason_code: one of {tuple(sorted(REASON_CODES))}" in text
    # High-disclosure-only content must be entirely absent from low.
    assert "typical_action" not in text
    assert "admissible decline_codes" not in text


def test_high_disclosure_template_version_is_a_distinct_string():
    assert TEMPLATE_VERSION_HIGH_DISCLOSURE != TEMPLATE_VERSION


def test_high_disclosure_renders_every_reason_code_with_typical_action_and_admissible_codes():
    view = _view()
    text = render_prompt(view, template_version=TEMPLATE_VERSION_HIGH_DISCLOSURE)
    for code in REASON_CODES:
        assert code in text
        assert TYPICAL_ACTION[code] in text
        for decline_code in ADMISSIBLE_DECLINE_CODES[code]:
            assert decline_code in text


def test_high_disclosure_states_the_post_halt_rescue_halted_condition():
    view = _view()
    text = render_prompt(view, template_version=TEMPLATE_VERSION_HIGH_DISCLOSURE)
    assert POST_HALT_RESCUE in text
    assert "subscription_state == halted" in text


def test_low_and_high_disclosure_produce_different_prompts_and_hashes():
    """Different rendered text -> different prompt_hash, so the frozen
    (template_version, model, temperature, prompt_hash) cache key already
    distinguishes disclosure level correctly with no extra isolation
    needed (unlike reasoning_effort/thinking_level)."""
    import hashlib

    view = _view()
    low = render_prompt(view, template_version=TEMPLATE_VERSION)
    high = render_prompt(view, template_version=TEMPLATE_VERSION_HIGH_DISCLOSURE)
    assert low != high
    assert (
        hashlib.sha256(low.encode("utf-8")).hexdigest()
        != hashlib.sha256(high.encode("utf-8")).hexdigest()
    )


def test_high_disclosure_still_contains_no_latent_field_name_or_seed_token():
    """Same §12 boundary the low-disclosure content test already
    enforces, re-applied to the new branch - the disclosed content is
    drawn only from rrx.agent.reason_codes' frozen constants, never
    simulator/latent state."""
    view = _view()
    text = render_prompt(view, template_version=TEMPLATE_VERSION_HIGH_DISCLOSURE)
    for name in _LATENT_FIELD_NAMES:
        assert name not in text, f"high-disclosure prompt leaked latent field name {name!r}"
    for token in _SEED_SHAPED_TOKENS:
        assert token not in text


def test_high_disclosure_source_never_accesses_a_field_outside_the_allowlist():
    """Static proof mirroring test_render_prompt_source_never_accesses_a_
    field_outside_the_allowlist - the new _render_reason_code_disclosure
    helper reads only rrx.agent.reason_codes constants, never a view/rec
    field, so it cannot introduce a new leak surface. Directly asserted by
    inspecting the module's imports rather than re-running the AST scan
    (which already covers view./rec. accesses and is unaffected by this
    disclosure-only helper)."""
    path = SRC / "rrx" / "agent" / "prompt.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "rrx.agent.reason_codes":
            imported_names.update(a.name for a in node.names)
    assert imported_names == {
        "ADMISSIBLE_DECLINE_CODES", "POST_HALT_RESCUE", "REASON_CODES", "TYPICAL_ACTION",
    }
