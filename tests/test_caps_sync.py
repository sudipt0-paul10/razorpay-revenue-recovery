"""Caps consistency between the two files that each restate the contact
budget.

data/decline_codes.yaml (defaults.global_caps) and configs/episode.yaml
(episode.window_days, agent_budget) both hard-code the same three numbers.
EVAL.md §10 requires them to agree; nothing previously asserted it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from rrx.spec.registry import config_dir

REPO_ROOT = config_dir().parent


def _load(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


decline_caps = _load(REPO_ROOT / "data" / "decline_codes.yaml")["defaults"]["global_caps"]
episode = _load(REPO_ROOT / "configs" / "episode.yaml")


def test_max_contacts_per_episode_agrees():
    assert (decline_caps["max_contacts_per_episode"]
            == episode["agent_budget"]["max_contacts_per_episode"])


def test_episode_window_days_agrees():
    assert decline_caps["episode_window_days"] == episode["episode"]["window_days"]


def test_quiet_hours_agree():
    q = decline_caps["quiet_hours_ist"]
    ab = episode["agent_budget"]["quiet_hours_ist"]
    assert q["start"] == ab["contact_window_start"]
    assert q["end"] == ab["contact_window_end"]
