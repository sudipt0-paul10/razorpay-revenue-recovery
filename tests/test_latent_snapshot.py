"""Reproducibility control (Day 2 Stage 2), not a performance change.

pyproject.toml now pins `numpy==2.5.2` exactly rather than `numpy>=2.0`,
because a numpy/BitGenerator implementation change can silently shift every
downstream sampled value while the frozen (split, i, substream) seed and the
code that calls it stay byte-identical - the exact pin makes the dependency
fixed instead of merely "compatible"; this snapshot is what makes the
CONSEQUENCES of ever deliberately bumping it visible, by pinning the known
output of the frozen sha256 CRN scheme (rrx.sim.latent.seed_for_substream)
against a numpy version + RNG algorithm, not just the config that produced
it. A future numpy upgrade (or RNG algorithm change) that alters these values
must be a deliberate, reviewed decision - this test turns a silent drift into
a loud, specific failure.

Recorded 2026-08-26 against numpy 2.5.2, from the frozen configs/episode.yaml
and configs/population.yaml (eval-spec-v1.1), via
rrx.sim.latent.draw_latent_state.

Re-pinned 2026-08-26 (Day 2 Stage 3): the discovered blocked_until defect fix
in rrx.sim.latent.draw_latent_state (default changed from BLOCKED_INDEFINITELY
to 0.0 for every row except transaction_limit_exceeded/payment_risk_check_
failed - see latent.py's inline comment) deliberately changes blocked_until
for insufficient_funds, ambiguous_decline, card_expired, and
subscription_cancelled_by_customer. This is exactly the kind of deliberate,
reviewed change this snapshot exists to make visible - only blocked_until
moves for those four cases; every other pinned field is unchanged.

Extended 2026-08-26 (Stage 3 closing): added a payment_risk_check_failed
case. Without it, the fix's `elif key in ("transaction_limit_exceeded",
"payment_risk_check_failed"): blocked_until = BLOCKED_INDEFINITELY` branch
had only transaction_limit_exceeded pinned - a future edit that dropped
payment_risk_check_failed from that tuple (silently reverting it to the new
non-blocking 0.0 default) would have passed every existing snapshot case.
"""

from __future__ import annotations

import math

import pytest

from rrx.sim.latent import draw_latent_state, load_configs
from rrx.spec.registry import enumerate_cells, load_registry
from rrx.spec.resolver import resolve_config

# (split, episode_index, opening_condition_key) -> expected LatentState fields.
# One case per SIM.md §2 mechanism family: funds-restore draw
# (insufficient_funds), the ambiguous-cause Bernoulli + funds-restore
# (ambiguous_decline), the transient-block-clearance draw
# (bank_technical_error), a card-broken row (card_expired), the
# mandate-dead row (subscription_cancelled_by_customer), and a
# blocked-indefinitely row (transaction_limit_exceeded) - plus a second
# split (holdout) to prove the snapshot isn't split-blind.
CASES = [
    ("dev", 0, "insufficient_funds"),
    ("dev", 7, "ambiguous_decline"),
    ("holdout", 3, "bank_technical_error"),
    ("dev", 0, "card_expired"),
    ("dev", 0, "subscription_cancelled_by_customer"),
    ("dev", 42, "transaction_limit_exceeded"),
    ("dev", 3, "payment_risk_check_failed"),
]

EXPECTED = {
    ("dev", 0, "insufficient_funds"): dict(
        card_chargeable=True,
        funds_available_from=1.6536396778130673,
        mandate_alive=True,
        blocked_until=0.0,
        channel_response_trait=0.22447021524047975,
        card_change_completion_propensity=0.7752548930132623,
    ),
    ("dev", 7, "ambiguous_decline"): dict(
        card_chargeable=True,
        funds_available_from=2.5261980692690233,
        mandate_alive=True,
        blocked_until=0.0,
        channel_response_trait=0.1038889585360483,
        card_change_completion_propensity=0.20105177132455626,
    ),
    ("holdout", 3, "bank_technical_error"): dict(
        card_chargeable=True,
        funds_available_from=0.0,
        mandate_alive=True,
        blocked_until=0.2106051722882183,
        channel_response_trait=0.5514758531365137,
        card_change_completion_propensity=0.5984075034992703,
    ),
    ("dev", 0, "card_expired"): dict(
        card_chargeable=False,
        funds_available_from=0.0,
        mandate_alive=True,
        blocked_until=0.0,
        channel_response_trait=0.22447021524047975,
        card_change_completion_propensity=0.7752548930132623,
    ),
    ("dev", 0, "subscription_cancelled_by_customer"): dict(
        card_chargeable=True,
        funds_available_from=0.0,
        mandate_alive=False,
        blocked_until=0.0,
        channel_response_trait=0.22447021524047975,
        card_change_completion_propensity=0.7752548930132623,
    ),
    ("dev", 42, "transaction_limit_exceeded"): dict(
        card_chargeable=True,
        funds_available_from=0.0,
        mandate_alive=True,
        blocked_until=math.inf,
        channel_response_trait=0.38915305166384123,
        card_change_completion_propensity=0.6728599492796269,
    ),
    ("dev", 3, "payment_risk_check_failed"): dict(
        card_chargeable=True,
        funds_available_from=0.0,
        mandate_alive=True,
        blocked_until=math.inf,
        channel_response_trait=0.23317590755004153,
        card_change_completion_propensity=0.3212817101033693,
    ),
}


@pytest.fixture(scope="module")
def configs():
    return load_configs()


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c[0]}:{c[1]}:{c[2]}")
def test_latent_state_snapshot_is_byte_identical(configs, case):
    split, i, key = case
    episode_cfg, population_cfg = configs
    state = draw_latent_state(split, i, key, episode_cfg, population_cfg)
    expected = EXPECTED[case]

    assert state.card_chargeable == expected["card_chargeable"]
    assert state.mandate_alive == expected["mandate_alive"]
    assert state.blocked_until == expected["blocked_until"]
    assert state.funds_available_from == pytest.approx(
        expected["funds_available_from"], abs=1e-12
    )
    assert state.channel_response_trait == pytest.approx(
        expected["channel_response_trait"], abs=1e-12
    )
    assert state.card_change_completion_propensity == pytest.approx(
        expected["card_change_completion_propensity"], abs=1e-12
    )


# ---------------------------------------------------------------------------
# Resolver -> sampler path.
#
# The six cases above snapshot draw_latent_state() against the BASELINE
# config only - they would pass identically even if resolve_config() were
# broken or never called. This case instead runs a real enumerate_cells()
# Cell through resolve_config() and snapshots draw_latent_state() on the
# RESOLVED config it returns, at the same (split, i, key) triple as the
# first baseline case above, so the two pinned values can be compared
# directly: channel_response_trait must differ from the baseline snapshot
# (proving the resolved config actually reached the sampler), while every
# other field must stay identical (proving the cell only moved the one
# substream/path it declares ownership of - balance_restore and
# card_change_completion are untouched by this cell).
# ---------------------------------------------------------------------------

RESOLVED_CASE = ("dev", 0, "insufficient_funds")
RESOLVED_CELL_ID = "channel_response_propensity.high"

RESOLVED_EXPECTED = dict(
    card_chargeable=True,
    funds_available_from=1.6536396778130673,
    mandate_alive=True,
    blocked_until=0.0,
    channel_response_trait=0.29672285249034863,
    card_change_completion_propensity=0.7752548930132623,
)


def test_resolver_materialized_snapshot_is_byte_identical():
    reg = load_registry()
    cell = next(c for c in enumerate_cells(reg) if c.cell_id == RESOLVED_CELL_ID)
    assert cell.parameter == "channel_response_propensity"
    assert cell.handle == "trait_mean"
    assert cell.value == pytest.approx(0.364)

    episode_cfg, population_cfg = load_configs()
    episode_resolved, population_resolved = resolve_config(episode_cfg, population_cfg, cell)

    split, i, key = RESOLVED_CASE
    state = draw_latent_state(split, i, key, episode_resolved, population_resolved)

    assert state.card_chargeable == RESOLVED_EXPECTED["card_chargeable"]
    assert state.mandate_alive == RESOLVED_EXPECTED["mandate_alive"]
    assert state.blocked_until == RESOLVED_EXPECTED["blocked_until"]
    assert state.funds_available_from == pytest.approx(
        RESOLVED_EXPECTED["funds_available_from"], abs=1e-12
    )
    assert state.channel_response_trait == pytest.approx(
        RESOLVED_EXPECTED["channel_response_trait"], abs=1e-12
    )
    assert state.card_change_completion_propensity == pytest.approx(
        RESOLVED_EXPECTED["card_change_completion_propensity"], abs=1e-12
    )

    # Proof this pins the resolver -> sampler path, not merely the baseline
    # sampler: the resolved trait must differ from the baseline snapshot for
    # this exact (split, i, key), and every other field must match it
    # exactly - only the one substream this cell owns moved.
    baseline = EXPECTED[RESOLVED_CASE]
    assert state.channel_response_trait != pytest.approx(
        baseline["channel_response_trait"], abs=1e-9
    )
    assert state.funds_available_from == pytest.approx(
        baseline["funds_available_from"], abs=1e-12
    )
    assert state.card_change_completion_propensity == pytest.approx(
        baseline["card_change_completion_propensity"], abs=1e-12
    )
