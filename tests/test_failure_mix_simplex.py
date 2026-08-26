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
    scalar_valued_handles,
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
    """eval-spec-v1.1: failure_mix_weights now also carries
    ambiguous_cause_split's scalar p_card_cause cells (not a bucket-mass
    perturbation), so this loop is scoped to dict-valued (bucket-vector)
    cells only. See test_scalar_cells_are_declared_scalar_not_corrupted_
    vectors below for the companion check that keeps this guard honest."""
    for c in enumerate_cells(reg):
        if c.parameter != "failure_mix_weights" or not isinstance(c.value, dict):
            continue
        assert sum(c.value.values()) == pytest.approx(1.0, abs=TOL), c.cell_id
        cond = expand_to_conditions(c.value, MEMBERS, CONDITIONS)
        assert sum(cond.values()) == pytest.approx(1.0, abs=TOL), c.cell_id
        assert all(v >= 0 for v in cond.values()), c.cell_id


def test_scalar_cells_are_declared_scalar_not_corrupted_vectors():
    """Companion to the isinstance(c.value, dict) guard above. Without this,
    a future bucket-vector cell malformed into a scalar would be silently
    skipped by that guard rather than caught. Every failure_mix_weights cell
    whose value is NOT a dict must correspond to a handle explicitly
    declared scalar-valued in model_params.yaml's definition: block
    (eval-spec-v1.1's ambiguous_cause_split.p_card_cause); any other
    non-dict cell is a defect, not an expected shape."""
    scalar_handles = scalar_valued_handles(reg, "failure_mix_weights")
    assert scalar_handles, "expected at least ambiguous_cause_split's p_card_cause"
    for c in enumerate_cells(reg):
        if c.parameter != "failure_mix_weights" or isinstance(c.value, dict):
            continue
        assert c.handle in scalar_handles, (
            f"{c.cell_id}: scalar-valued (value={c.value!r}) but handle "
            f"{c.handle!r} is not declared scalar in model_params.yaml "
            f"(declared scalar handles: {sorted(scalar_handles)})"
        )
