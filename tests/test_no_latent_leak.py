"""EVAL.md §3.4 [INVARIANT]: latent simulator state is architecturally
unreachable from the agent.

Three independent enforcement layers, all deterministic and offline:

  1. STATIC   - AST scan of rrx/agent and rrx/features for any import that
                reaches rrx.sim.latent. Catches the direct case and does
                not execute agent code.
  2. RUNTIME  - import rrx.agent and rrx.features in a clean subprocess and
                assert rrx.sim.latent never lands in sys.modules. Catches
                transitive leaks through an intermediate module, which the
                AST scan cannot see.
  3. SURFACE  - EpisodeView's field set, and ContactRecord's, must each be a
                subset of the §3.4 allowlist and contain no latent field
                name. ContactRecord is checked separately because it is
                nested inside contact_history: the EpisodeView field scan
                sees the tuple, not what is in it.

Layer 3 fails if EpisodeView does not exist. That is intentional:
EVAL.md §10 requires it as a dataclass before eval-spec-v1.

eval-spec-v1.2 (2026-08-26): EVAL.md §3.4 itself now records (via a
[DEFECT, eval-spec-v1.2] footnote directly below its 16-field list) that
the v1 EpisodeView surface is the narrower 10-field EPISODE_VIEW_ALLOWED
below, not the frozen list's literal text - the frozen 16-field list is
preserved unrewritten as the target for a future version, per §10's rule
against rewriting frozen text. This allowlist enforces that footnoted v1
surface, so its "subset of the §3.4 allowlist" description in layer 3
above is accurate against the CURRENT (amended) EVAL.md §3.4, not a
stale/narrower stand-in for it - the enforcing test and the specification
it enforces genuinely agree.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
GUARDED_PACKAGES = ("rrx/agent", "rrx/features")

# Reaching any of these gives access to latent state.
FORBIDDEN_MODULES = ("rrx.sim.latent", "rrx.sim")

# EVAL.md §3.4's v1 surface, per its own [DEFECT, eval-spec-v1.2] footnote -
# 10 fields, not the frozen 16-field list's literal text (that list is
# preserved unrewritten as a future-version target, per EVAL.md §10). Six
# fields (decline_source, billing_cycle_day, completed_billing_cycles,
# customer_tenure_days, prior_pending_episodes, prior_recovery_channel) are
# deliberately removed rather than populated with fabricated values - see
# the footnote itself, src/rrx/features/episode_view.py's module docstring,
# SIM.md §10, and CHANGELOG.md for the full recorded reasoning.
EPISODE_VIEW_ALLOWED = {
    "subscription_id", "subscription_state", "invoice_amount_inr",
    "days_since_first_failure", "auto_retries_remaining", "next_auto_retry_day",
    "decline_code", "billing_amount_inr",
    "contact_history", "budget_remaining",
}

# Day 2 Stage 4B: contact_history[] : (day, channel, remedy, delivered,
# engaged) - `ts` renamed to `day` (RULING 1: relative time, no calendar
# anchor). A separate surface: EPISODE_VIEW_ALLOWED admits the
# contact_history field itself, which says nothing about what each entry
# carries.
CONTACT_RECORD_ALLOWED = {"day", "channel", "remedy", "delivered", "engaged"}

# EVAL.md §3.3 / SIM.md §1 - latent fields the agent must never see.
# Includes rrx.sim.latent.LatentState's own dataclass field names directly
# (card_chargeable, funds_available_from, mandate_alive, blocked_until,
# channel_response_trait) - added Day 2 Stage 4 after finding these five,
# the most direct latent field names in the codebase, were missing from
# this set entirely; only card_change_completion_propensity (also a
# LatentState field) had been listed.
LATENT_FIELD_NAMES = {
    "balance_restore_delay", "salary_day", "p_topup_action",
    "topup_acceleration", "channel_response_propensity",
    "card_change_completion_propensity", "cancellation_hazard",
    "cancellation_hazard_per_contact", "remaining_subscription_lifetime_cycles",
    "remaining_lifetime_cycles", "latent",
    "card_chargeable", "funds_available_from", "mandate_alive",
    "blocked_until", "channel_response_trait", "card_chargeable_at_opening",
}

# Types that may legitimately appear as an EpisodeView/ContactRecord field's
# annotation. Anything else (e.g. a bare `object`, an unresolvable forward
# reference, or a type imported from rrx.sim) is a potential indirect-leak
# vector - a field typed to hold a whole object (LatentState, an engine
# _EpisodeState, an RNG) rather than a plain observable value. Day 2 Stage
# 4B: date/datetime dropped - RULING 1 makes every time field a relative
# `int` day; the simulator has no calendar anchor anywhere.
_ALLOWED_FIELD_TYPES = {"str", "int", "bool"}


def _guarded_source_files() -> list[Path]:
    out: list[Path] = []
    for pkg in GUARDED_PACKAGES:
        d = SRC / pkg
        if d.is_dir():
            out.extend(sorted(d.rglob("*.py")))
    return out


def _imported_modules(path: Path) -> set[str]:
    """Every module name this file imports, as dotted paths."""
    # encoding is explicit: the default is the locale codepage (cp1252 on
    # Windows), which mojibakes or outright raises on the non-ASCII this
    # codebase uses freely. A guard must not be environment-dependent.
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:          # relative import, not a rrx.* path
                continue
            mod = node.module or ""
            names.add(mod)
            for a in node.names:
                names.add(f"{mod}.{a.name}" if mod else a.name)
    return names


def _violates(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in FORBIDDEN_MODULES)


# --------------------------------------------------------------------------
# Layer 1 - static
# --------------------------------------------------------------------------

def test_features_package_exists():
    """rrx/features holds EpisodeView, which EVAL.md §10 requires before
    eval-spec-v1. This is a Day 1 obligation and must pass now."""
    assert (SRC / "rrx/features").is_dir(), (
        "src/rrx/features missing; EpisodeView is on the §10 freeze checklist."
    )


def test_agent_package_guard_status():
    """rrx/agent is a Day 6-7 deliverable. Layers 1 and 2 are vacuous for it
    until it exists - skipped rather than silently green, so the gap stays
    visible in the test report."""
    if not (SRC / "rrx/agent").is_dir():
        pytest.skip("rrx/agent not built yet (Day 6-7); latent guard is armed")
    assert True


@pytest.mark.parametrize(
    "path", _guarded_source_files() or [pytest.param(None, marks=pytest.mark.skip(
        reason="no source files in rrx/agent or rrx/features yet"))],
    ids=lambda p: str(p.relative_to(SRC)) if p else "none",
)
def test_no_forbidden_import_statement(path):
    bad = sorted(n for n in _imported_modules(path) if _violates(n))
    assert not bad, (
        f"{path.relative_to(SRC)} imports {bad}. EVAL.md §3.4 forbids the "
        "agent layer from reaching latent simulator state."
    )


# --------------------------------------------------------------------------
# Layer 2 - runtime transitive
# --------------------------------------------------------------------------

@pytest.mark.parametrize("module", ["rrx.agent", "rrx.features"])
def test_no_transitive_latent_import(module):
    """Importing the agent layer must not pull rrx.sim.latent into
    sys.modules by any path, however indirect."""
    if not (SRC / module.replace(".", "/")).is_dir():
        pytest.skip(f"{module} not created yet")

    code = (
        "import sys, importlib\n"
        f"importlib.import_module({module!r})\n"
        "leaked = [m for m in sys.modules if m == 'rrx.sim.latent' "
        "or m.startswith('rrx.sim.latent.')]\n"
        "print(','.join(leaked))\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd=SRC.parent,
        # PYTHONPATH is the only variable this test needs to control. Replacing
        # the whole environment strips SystemRoot/COMSPEC on Windows and the
        # PATH a venv interpreter needs to find its DLLs, turning an unrelated
        # startup failure into a confusing leak-test failure.
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert r.returncode == 0, f"import of {module} failed:\n{r.stderr}"
    leaked = r.stdout.strip()
    assert not leaked, f"{module} transitively imports {leaked}"


# --------------------------------------------------------------------------
# Layer 3 - EpisodeView surface
# --------------------------------------------------------------------------

def _episode_view():
    try:
        from rrx.features.episode_view import EpisodeView  # noqa: PLC0415
    except ImportError:
        try:
            from rrx.features import EpisodeView  # noqa: PLC0415
        except ImportError:
            pytest.fail(
                "EpisodeView not importable from rrx.features. EVAL.md §10 "
                "requires it as a dataclass before eval-spec-v1."
            )
    return EpisodeView


def _contact_record():
    try:
        from rrx.features.episode_view import ContactRecord  # noqa: PLC0415
    except ImportError:
        try:
            from rrx.features import ContactRecord  # noqa: PLC0415
        except ImportError:
            pytest.fail(
                "ContactRecord not importable from rrx.features. EVAL.md §3.4 "
                "pins the contact_history entry shape as part of the surface."
            )
    return ContactRecord


def test_episode_view_is_a_dataclass():
    assert is_dataclass(_episode_view())


def test_episode_view_exposes_no_field_outside_the_allowlist():
    got = {f.name for f in fields(_episode_view())}
    extra = got - EPISODE_VIEW_ALLOWED
    assert not extra, (
        f"EpisodeView exposes {sorted(extra)}, which EVAL.md §3.4 does not "
        "list. Any field beyond the allowlist is a potential leak."
    )


def test_episode_view_field_set_equals_the_allowlist_exactly():
    """Positive set-equality (Day 2 Stage 4), not just 'no extras': the
    prior test above only catches fields ADDED beyond the allowlist - a
    field silently DROPPED (e.g. budget_remaining removed) would still pass
    it, but EVAL.md §3.4 requires the agent to see every one of these
    fields, not a subset. Fails in both directions."""
    got = {f.name for f in fields(_episode_view())}
    assert got == EPISODE_VIEW_ALLOWED, (
        f"EpisodeView fields {sorted(got)} != EVAL.md §3.4 allowlist "
        f"{sorted(EPISODE_VIEW_ALLOWED)} - missing: "
        f"{sorted(EPISODE_VIEW_ALLOWED - got)}, extra: {sorted(got - EPISODE_VIEW_ALLOWED)}"
    )


def test_episode_view_exposes_no_latent_field():
    got = {f.name for f in fields(_episode_view())}
    leaked = got & LATENT_FIELD_NAMES
    assert not leaked, f"EpisodeView exposes latent state: {sorted(leaked)}"


def test_contact_record_is_a_dataclass():
    assert is_dataclass(_contact_record())


def test_contact_record_exposes_no_field_outside_the_allowlist():
    """Without this, a latent field hidden one level down in a
    contact_history entry passes all three layers."""
    got = {f.name for f in fields(_contact_record())}
    extra = got - CONTACT_RECORD_ALLOWED
    assert not extra, (
        f"ContactRecord exposes {sorted(extra)}, which EVAL.md §3.4 does not "
        "list for contact_history entries."
    )


def test_contact_record_field_set_equals_the_allowlist_exactly():
    """Positive set-equality (Day 2 Stage 4, updated Stage 4B): entries are
    pinned to EXACTLY (day, channel, remedy, delivered, engaged) - `day`
    per RULING 1 (relative time, `ts` renamed), `engaged` deliberately kept
    as observable historical information, not just absent-of-extras."""
    got = {f.name for f in fields(_contact_record())}
    assert got == CONTACT_RECORD_ALLOWED, (
        f"ContactRecord fields {sorted(got)} != EVAL.md §3.4 allowlist "
        f"{sorted(CONTACT_RECORD_ALLOWED)} - missing: "
        f"{sorted(CONTACT_RECORD_ALLOWED - got)}, extra: {sorted(got - CONTACT_RECORD_ALLOWED)}"
    )


def test_contact_record_exposes_no_latent_field():
    got = {f.name for f in fields(_contact_record())}
    leaked = got & LATENT_FIELD_NAMES
    assert not leaked, f"ContactRecord exposes latent state: {sorted(leaked)}"


# --------------------------------------------------------------------------
# Layer 3, extended (Day 2 Stage 4) - indirect leakage through nested
# objects/references. Full runtime-value inspection isn't possible (nothing
# in the repository constructs an EpisodeView instance yet - see the Stage 4
# report), so this checks what the CURRENT architecture makes checkable:
# every field's declared type is a plain observable value type (never an
# object reference to rrx.sim.latent.LatentState or similar), and both
# dataclasses are frozen + slotted, which structurally forecloses attaching
# a latent reference to an instance after construction (no __dict__ to stash
# one in, no attribute reassignment to swap one in).
# --------------------------------------------------------------------------

def _annotation_names(cls) -> dict[str, str]:
    """Field name -> the type name(s) written in its annotation string
    (e.g. "tuple[ContactRecord, ...]" -> {"tuple", "ContactRecord"}).
    String-based (not typing.get_type_hints) so this works without
    resolving forward references, and so a field annotated with a type from
    an unimported/unexpected module still shows up as a plain name to check
    against the allow-list, rather than raising or silently resolving.
    """
    import re

    out: dict[str, set[str]] = {}
    for f in fields(cls):
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", f.type))
        out[f.name] = tokens - {"None", "tuple"}
    return out


def test_episode_view_field_types_are_all_plain_observable_values():
    """No EpisodeView field may be typed to hold an object reference other
    than ContactRecord (itself checked separately) - ruling out a field
    that could carry a whole LatentState, an engine _EpisodeState, or an
    RNG instead of a plain value."""
    allowed = _ALLOWED_FIELD_TYPES  # next_auto_retry_day: int | None (RULING 1)
    for name, tokens in _annotation_names(_episode_view()).items():
        if name == "contact_history":
            assert tokens == {"ContactRecord"}, (name, tokens)
            continue
        bad = tokens - allowed
        assert not bad, f"EpisodeView.{name} has non-observable-value type token(s): {bad}"


def test_contact_record_field_types_are_all_plain_observable_values():
    for name, tokens in _annotation_names(_contact_record()).items():
        bad = tokens - _ALLOWED_FIELD_TYPES
        assert not bad, f"ContactRecord.{name} has non-observable-value type token(s): {bad}"


def _dummy_instance(cls):
    kwargs = {}
    for f in fields(cls):
        tokens = _annotation_names(cls)[f.name]
        if "ContactRecord" in tokens:
            kwargs[f.name] = ()
        elif "bool" in tokens:
            kwargs[f.name] = True
        elif "int" in tokens:
            kwargs[f.name] = 0
        elif "date" in tokens or "datetime" in tokens:
            import datetime as _dt

            kwargs[f.name] = _dt.datetime.now()
        else:
            kwargs[f.name] = "x"
    return cls(**kwargs)


def test_episode_view_and_contact_record_are_frozen():
    """frozen=True forecloses reassigning a field to a latent reference
    after construction."""
    import dataclasses

    for cls in (_episode_view(), _contact_record()):
        instance = _dummy_instance(cls)
        with pytest.raises(dataclasses.FrozenInstanceError):
            instance.__setattr__(fields(cls)[0].name, object())


def test_episode_view_and_contact_record_reject_arbitrary_new_attributes():
    """slots=True forecloses stashing a latent reference under a new
    attribute name post-construction - there is no __dict__ to hold it in.
    frozen+slots together raise TypeError for an unknown attribute name in
    CPython (not AttributeError - a documented interaction quirk, verified
    empirically for this interpreter), rather than the FrozenInstanceError
    an existing-field reassignment raises - either way, the assignment must
    fail, which is what actually matters here."""
    for cls in (_episode_view(), _contact_record()):
        instance = _dummy_instance(cls)
        with pytest.raises((AttributeError, TypeError)):
            instance.__setattr__("_smuggled_latent_ref", object())
