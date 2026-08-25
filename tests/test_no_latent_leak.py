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

# EVAL.md §3.4 - the complete EpisodeView surface. Nothing else is visible.
EPISODE_VIEW_ALLOWED = {
    "subscription_id", "subscription_state", "invoice_amount_inr",
    "days_since_first_failure", "auto_retries_remaining", "next_auto_retry_date",
    "decline_code", "decline_source",
    "billing_cycle_day", "billing_amount_inr", "completed_billing_cycles",
    "customer_tenure_days", "prior_pending_episodes", "prior_recovery_channel",
    "contact_history", "budget_remaining",
}

# EVAL.md §3.4 - contact_history[] : (ts, channel, remedy, delivered, engaged).
# A separate surface: EPISODE_VIEW_ALLOWED admits the contact_history field
# itself, which says nothing about what each entry carries.
CONTACT_RECORD_ALLOWED = {"ts", "channel", "remedy", "delivered", "engaged"}

# EVAL.md §3.3 - latent fields the agent must never see.
LATENT_FIELD_NAMES = {
    "balance_restore_delay", "salary_day", "p_topup_action",
    "topup_acceleration", "channel_response_propensity",
    "card_change_completion_propensity", "cancellation_hazard",
    "cancellation_hazard_per_contact", "remaining_subscription_lifetime_cycles",
    "remaining_lifetime_cycles", "latent",
}


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


def test_contact_record_exposes_no_latent_field():
    got = {f.name for f in fields(_contact_record())}
    leaked = got & LATENT_FIELD_NAMES
    assert not leaked, f"ContactRecord exposes latent state: {sorted(leaked)}"
