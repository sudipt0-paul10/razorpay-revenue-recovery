"""Simplex invariants for the failure-mix sweep (locked decision 3).

Every generated cell must remain a valid probability vector, and the
within-bucket ratios must be untouched.
"""

import pytest

from rrx.spec.registry import (
    enumerate_cells,
    expand_to_conditions,
    load_registry,
    perturb_bucket,
    resolve_owner_path,
)

reg = load_registry()
P = reg.parameters["failure_mix_weights"]
BUCKETS = {b: s["baseline"] for b, s in P["handle"]["buckets"].items()}
MEMBERS = {b: s["members"] for b, s in P["handle"]["buckets"].items()}
CONDITIONS = resolve_owner_path(P["owner_path"])["conditions"]
TOL = 1e-9


def test_baseline_conditions_sum_to_one():
    assert sum(CONDITIONS.values()) == pytest.approx(1.0, abs=TOL)


def test_bucket_baselines_equal_sum_of_members():
    """Keeps the bucket layer honest against EVAL.md §3.2's table."""
    for bucket, base in BUCKETS.items():
        got = sum(CONDITIONS[m] for m in MEMBERS[bucket])
        assert got == pytest.approx(base, abs=TOL), f"{bucket}: {got} != {base}"


def test_every_condition_belongs_to_exactly_one_bucket():
    assigned = [m for ms in MEMBERS.values() for m in ms]
    assert sorted(assigned) == sorted(CONDITIONS)
    assert len(assigned) == len(set(assigned))


@pytest.mark.parametrize("bucket", list(BUCKETS))
@pytest.mark.parametrize("direction", ["low", "high"])
def test_perturbed_buckets_sum_to_one(bucket, direction):
    out = perturb_bucket(BUCKETS, bucket, direction, P["sweep"]["magnitude"])
    assert sum(out.values()) == pytest.approx(1.0, abs=TOL)


@pytest.mark.parametrize("bucket", list(BUCKETS))
@pytest.mark.parametrize("direction", ["low", "high"])
def test_perturbed_buckets_non_negative(bucket, direction):
    out = perturb_bucket(BUCKETS, bucket, direction, P["sweep"]["magnitude"])
    assert all(0.0 <= v <= 1.0 for v in out.values()), out


@pytest.mark.parametrize("bucket", list(BUCKETS))
@pytest.mark.parametrize("direction", ["low", "high"])
def test_target_bucket_moved_exactly_thirty_percent(bucket, direction):
    mag = P["sweep"]["magnitude"]
    f = (1 - mag) if direction == "low" else (1 + mag)
    out = perturb_bucket(BUCKETS, bucket, direction, mag)
    assert out[bucket] == pytest.approx(BUCKETS[bucket] * f, rel=1e-9)


@pytest.mark.parametrize("bucket", list(BUCKETS))
@pytest.mark.parametrize("direction", ["low", "high"])
def test_non_target_ratios_preserved(bucket, direction):
    """The whole point of renormalise-across-buckets: the other buckets
    keep their relative proportions."""
    out = perturb_bucket(BUCKETS, bucket, direction, P["sweep"]["magnitude"])
    others = [b for b in BUCKETS if b != bucket]
    ref = others[0]
    for b in others[1:]:
        assert out[b] / out[ref] == pytest.approx(
            BUCKETS[b] / BUCKETS[ref], rel=1e-9)


@pytest.mark.parametrize("bucket", list(BUCKETS))
@pytest.mark.parametrize("direction", ["low", "high"])
def test_within_bucket_ratios_preserved(bucket, direction):
    out = perturb_bucket(BUCKETS, bucket, direction, P["sweep"]["magnitude"])
    cond = expand_to_conditions(out, MEMBERS, CONDITIONS)
    assert sum(cond.values()) == pytest.approx(1.0, abs=TOL)
    for b, names in MEMBERS.items():
        if len(names) < 2:
            continue
        ref = names[0]
        for n in names[1:]:
            assert cond[n] / cond[ref] == pytest.approx(
                CONDITIONS[n] / CONDITIONS[ref], rel=1e-9)


def test_all_generated_failure_mix_cells_are_valid_simplexes():
    for c in enumerate_cells(reg):
        if c.parameter != "failure_mix_weights":
            continue
        assert sum(c.value.values()) == pytest.approx(1.0, abs=TOL), c.cell_id
        cond = expand_to_conditions(c.value, MEMBERS, CONDITIONS)
        assert sum(cond.values()) == pytest.approx(1.0, abs=TOL), c.cell_id
        assert all(v >= 0 for v in cond.values()), c.cell_id
