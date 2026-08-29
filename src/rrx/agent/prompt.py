"""Deterministic prompt renderer for A3-LLM (docs/A3-DESIGN.md §11-§12).

`render_prompt` is a pure function of (EpisodeView, template_version) - no
`rrx.sim` import (no structural need for one: every value below is read
directly off `view`), no I/O, no randomness, no clock/RNG/seed access.
Lives under `src/rrx/agent/`, so it inherits `tests/test_no_latent_leak.py`'s
guarded-package import checks automatically, with zero modification to that
locked file.

§12's latent-leak invariant: the rendered string may reference only
EpisodeView/ContactRecord field values plus the fixed, project-internal
reason_code/action-space vocabulary (itself already part of the frozen
audit taxonomy, EVAL.md §5.4 - not simulator or latent information). No
`rrx.sim.latent` field name, RNG state, or seed value is ever formatted
into the output. `tests/test_prompt_rendering.py` is the enforcing test §12
called for and marked "Not implemented in this pass" - implemented now.
"""

from __future__ import annotations

from rrx.agent.reason_codes import (
    ADMISSIBLE_DECLINE_CODES,
    POST_HALT_RESCUE,
    REASON_CODES,
    TYPICAL_ACTION,
)
from rrx.features.episode_view import EpisodeView

# §13 cache-key component. Changing the rendered template text requires
# bumping this - a new template_version is a new tuning configuration
# (EVAL.md §6A), not a silent edit to "a3-llm-prompt-v1"'s existing text.
TEMPLATE_VERSION = "a3-llm-prompt-v1"

# Day 6 Stage 6H/6I: the "high" prompt-disclosure level (results/
# tuning_log.md Entry 2) renders different text than TEMPLATE_VERSION, so
# it gets its own distinct template_version string - not a runtime flag on
# the same version. This is deliberate: `rrx.agent.llm_cache.CacheKey`'s
# frozen (template_version, model, temperature, prompt_hash) key already
# distinguishes disclosure levels correctly as long as they map to
# different template_version strings, with zero change to that key's
# shape (unlike reasoning_effort/thinking_level, which needs a separate,
# per-configuration isolated-cache-instance strategy - see
# rrx.agent.openai_client's module docstring).
TEMPLATE_VERSION_HIGH_DISCLOSURE = "a3-llm-prompt-v1-high-disclosure"

# Maps each valid template_version to its disclosure level. "low" is the
# ORIGINAL, unmodified prompt.py behavior - TEMPLATE_VERSION's rendered
# text is byte-identical to before this dict/mapping existed.
_DISCLOSURE_BY_TEMPLATE_VERSION = {
    TEMPLATE_VERSION: "low",
    TEMPLATE_VERSION_HIGH_DISCLOSURE: "high",
}

_ACTION_TYPES = ("CONTACT", "WAIT", "STOP")
_REMEDIES = ("card_change", "topup_reminder")
_REASON_CODES_SORTED = tuple(sorted(REASON_CODES))


def _render_reason_code_disclosure(*, high: bool) -> str:
    """`disclosure=low` (default, unchanged): the bare reason_code enum
    list only - identical to this module's original, pre-Stage-6I text.
    `disclosure=high` (results/tuning_log.md Entry 2): additionally
    renders, per reason_code, its existing frozen `TYPICAL_ACTION` and
    sorted `ADMISSIBLE_DECLINE_CODES` (docs/A3-DESIGN.md §7), plus the
    existing `post_halt_rescue` halted-state condition - content that
    already exists in `rrx.agent.reason_codes`; nothing new is invented
    here."""
    if not high:
        return f"reason_code: one of {_REASON_CODES_SORTED}\n"

    lines = ["reason_code options (typical_action, admissible decline_codes):"]
    for code in _REASON_CODES_SORTED:
        admissible = ", ".join(sorted(ADMISSIBLE_DECLINE_CODES[code]))
        suffix = " (only when subscription_state == halted)" if code == POST_HALT_RESCUE else ""
        lines.append(f"  {code}: {TYPICAL_ACTION[code]} - {admissible}{suffix}")
    return "\n".join(lines) + "\n"


def _render_contact_history(view: EpisodeView) -> str:
    if not view.contact_history:
        return "  (none)"
    return "\n".join(
        f"  - day={rec.day} channel={rec.channel} remedy={rec.remedy} "
        f"delivered={rec.delivered} engaged={rec.engaged}"
        for rec in view.contact_history
    )


def render_prompt(view: EpisodeView, *, template_version: str = TEMPLATE_VERSION) -> str:
    """docs/A3-DESIGN.md §11: "Input: EpisodeView + template_version -
    nothing else." Every line below is derived from one of those two
    arguments; no other object is read.

    Output-schema instructions mirror §11 exactly: four keys
    (action_type, remedy, reason_code, rationale), no `channel` key (§6,
    §20 - channel is pinned to AGENT_CHANNEL at the executor, never chosen
    by any policy, LLM included).

    Day 6 Stage 6H/6I: `template_version` also selects the frozen prompt
    `disclosure` level (results/tuning_log.md Entry 2) -
    `TEMPLATE_VERSION` (default, unchanged) renders `low` disclosure;
    `TEMPLATE_VERSION_HIGH_DISCLOSURE` renders `high`. No other
    template_version value is valid.
    """
    if template_version not in _DISCLOSURE_BY_TEMPLATE_VERSION:
        raise ValueError(
            f"unknown template_version {template_version!r}; only "
            f"{sorted(_DISCLOSURE_BY_TEMPLATE_VERSION)!r} are implemented"
        )
    disclosure = _DISCLOSURE_BY_TEMPLATE_VERSION[template_version]
    reason_code_block = _render_reason_code_disclosure(high=(disclosure == "high"))

    return (
        "You are the payment-recovery decision policy for one subscription "
        "episode. Decide the single best action for THIS decision point "
        "only, using only the information below.\n\n"
        "[episode]\n"
        f"subscription_id: {view.subscription_id}\n"
        f"subscription_state: {view.subscription_state}\n"
        f"decline_code: {view.decline_code}\n"
        f"invoice_amount_inr: {view.invoice_amount_inr}\n"
        f"billing_amount_inr: {view.billing_amount_inr}\n"
        f"days_since_first_failure: {view.days_since_first_failure}\n"
        f"auto_retries_remaining: {view.auto_retries_remaining}\n"
        f"next_auto_retry_day: {view.next_auto_retry_day}\n"
        f"budget_remaining: {view.budget_remaining}\n\n"
        f"[contact_history]\n{_render_contact_history(view)}\n\n"
        "[allowed actions]\n"
        f"action_type: one of {_ACTION_TYPES}\n"
        f"remedy: one of {_REMEDIES} if action_type is CONTACT, else null\n"
        f"{reason_code_block}\n"
        "[response format]\n"
        "Respond with a single JSON object with EXACTLY these four keys "
        "and no others: action_type, remedy, reason_code, rationale. Do "
        "not include a channel or timing field - channel and send time "
        "are not yours to choose.\n"
    )
