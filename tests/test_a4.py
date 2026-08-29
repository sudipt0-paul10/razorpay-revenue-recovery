"""Canonical A4 (`src/rrx/baselines/a4.py`) — enforcing equivalence test
for its promotion from `tests/test_stage5_falsification.py`'s test-local
`run_a4_episode`.

Mirrors `tests/test_a1.py`'s convention for the sibling baseline-promotion
module: the relocation must not change a single decision. Unlike A1
(a pure per-day policy function), A4 is a full episode-loop function with
its own latent-state draw, so equivalence is checked by running BOTH the
canonical and the original test-local implementation over the same real
dev episodes and comparing their `EpisodeResult`s field-for-field, rather
than by re-deriving day-by-day actions.

`tests/test_stage5_falsification.py` itself is not imported here for its
pytest collection side effects - only its `run_a4_episode` function object,
exactly as `tests/test_a2_variants.py`/`test_a1.py` already import
production code, just in the opposite direction (test module -> test
module) since the original implementation has not been deleted from there.
"""

from __future__ import annotations

from rrx.baselines.a4 import A4_MAX_CONTACTS, run_a4_episode
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()


def _original_run_a4_episode(split, i, episode_cfg, population_cfg, master_seed):
    """The pre-relocation body's own module, imported directly - not
    reproduced here - so a future edit to either copy cannot silently drift
    without this test noticing (a hand-copied "verbatim" oracle could rot
    independently of the original; importing the original cannot)."""
    from tests.test_stage5_falsification import run_a4_episode as original

    return original(split, i, episode_cfg, population_cfg, master_seed=master_seed)


def test_canonical_a4_max_contacts_matches_original():
    from tests.test_stage5_falsification import A4_MAX_CONTACTS as original_max_contacts

    assert A4_MAX_CONTACTS == original_max_contacts


def test_canonical_a4_matches_pre_relocation_behavior_over_real_dev_episodes():
    """Every field of EpisodeResult must match, for every dev index in a
    representative sample spanning every opening_condition_key (not just
    the first N, which under-samples rarer buckets like
    payment_risk_check_failed at 1% weight)."""
    seen_conditions: set[str] = set()
    checked = 0
    for i in DEV_INDICES:
        canonical = run_a4_episode(DEV_SPLIT, i, EPISODE_CFG, POPULATION_CFG, master_seed=20260825)
        original = _original_run_a4_episode(
            DEV_SPLIT, i, EPISODE_CFG, POPULATION_CFG, master_seed=20260825
        )
        assert canonical == original, f"divergence at dev index {i}"
        seen_conditions.add(canonical.opening_condition_key)
        checked += 1
        if len(seen_conditions) >= 9 and checked >= 500:
            break

    # Sanity: this loop must have actually exercised a real spread of
    # opening conditions, not silently short-circuited on the first one.
    assert len(seen_conditions) >= 8, (
        f"only saw {sorted(seen_conditions)} - expected broader coverage of "
        "EVAL.md §3.2's 9 opening conditions"
    )


def test_canonical_a4_never_exceeds_the_shared_contact_budget():
    for i in list(DEV_INDICES)[:300]:
        result = run_a4_episode(DEV_SPLIT, i, EPISODE_CFG, POPULATION_CFG, master_seed=20260825)
        assert result.contacts_sent <= A4_MAX_CONTACTS


def test_canonical_a4_matches_original_on_the_cancelled_at_open_bucket():
    """Explicit coverage of the terminal-at-open early-return branch,
    which the broad sweep above may or may not land on given its 5% weight."""
    found = False
    for i in DEV_INDICES:
        canonical = run_a4_episode(DEV_SPLIT, i, EPISODE_CFG, POPULATION_CFG, master_seed=20260825)
        if canonical.opening_condition_key == "subscription_cancelled_by_customer":
            original = _original_run_a4_episode(
                DEV_SPLIT, i, EPISODE_CFG, POPULATION_CFG, master_seed=20260825
            )
            assert canonical == original
            assert canonical.contacts_sent == 0
            found = True
            break
    assert found, "no subscription_cancelled_by_customer episode found in DEV_INDICES"
