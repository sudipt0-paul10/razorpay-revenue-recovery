"""Loader for configs/model_params.yaml.

Spec machinery only. Contains no simulation, no agent, no policy.
Its whole job is to make EVAL.md §8.2 machine-checkable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# The canonical six. This list is the assertion target for
# tests/test_model_params_registry.py and must match EVAL.md §8.2 verbatim.
# Adding a seventh is a spec change requiring a new eval-spec version tag.
CANONICAL_MODEL_PARAMS: tuple[str, ...] = (
    "invoice_amount",
    "failure_mix_weights",
    "balance_restore_timing",
    "channel_response_propensity",
    "card_change_completion_propensity",
    "cancellation_hazard_and_ltv",
)

REQUIRED_FIELDS = ("eval_section", "status", "provenance", "kind",
                   "owner_path", "regime", "handle", "sweep")

VALID_STATUS = {"specified", "unspecified"}


def config_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "configs"


@dataclass(frozen=True)
class Registry:
    raw: dict[str, Any]

    @property
    def parameters(self) -> dict[str, Any]:
        return self.raw["parameters"]

    @property
    def sweep(self) -> dict[str, Any]:
        return self.raw["sweep"]

    def specified(self) -> dict[str, Any]:
        return {k: v for k, v in self.parameters.items()
                if v.get("status") == "specified"}

    def unspecified(self) -> dict[str, Any]:
        return {k: v for k, v in self.parameters.items()
                if v.get("status") == "unspecified"}


def load_registry(path: Path | None = None) -> Registry:
    path = path or (config_dir() / "model_params.yaml")
    with open(path) as fh:
        return Registry(yaml.safe_load(fh))


def resolve_owner_path(owner_path: str, cfg_dir: Path | None = None) -> Any:
    """Resolve 'population.yaml#/a/b' to the value at that key path.

    Raises KeyError/FileNotFoundError if the pointer is stale. This is the
    test that keeps the registry from drifting away from the configs.
    """
    cfg_dir = cfg_dir or config_dir()
    if "#" not in owner_path:
        raise ValueError(f"owner_path missing '#' fragment: {owner_path}")
    filename, fragment = owner_path.split("#", 1)
    with open(cfg_dir / filename) as fh:
        doc = yaml.safe_load(fh)
    node = doc
    for part in [p for p in fragment.strip("/").split("/") if p]:
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"{owner_path}: no key {part!r}")
        node = node[part]
    return node


# --------------------------------------------------------------------------
# Failure-mix bucket perturbation (locked decision 3)
# --------------------------------------------------------------------------

def perturb_bucket(buckets: dict[str, float], target: str,
                   direction: str, magnitude: float = 0.30) -> dict[str, float]:
    """Scale one bucket's mass by (1 +/- magnitude), renormalise the rest.

    The non-target buckets are rescaled proportionally so their relative
    ratios are untouched and the whole vector still sums to 1.0.
    """
    if target not in buckets:
        raise KeyError(target)
    if direction not in ("low", "high"):
        raise ValueError(direction)

    factor = (1.0 - magnitude) if direction == "low" else (1.0 + magnitude)
    new_target = buckets[target] * factor
    if not 0.0 <= new_target <= 1.0:
        raise ValueError(f"{target} {direction} leaves [0,1]: {new_target}")

    others_mass = sum(v for k, v in buckets.items() if k != target)
    if others_mass <= 0:
        raise ValueError("no residual mass to renormalise")
    scale = (1.0 - new_target) / others_mass

    out = {k: (new_target if k == target else v * scale)
           for k, v in buckets.items()}
    return out


def expand_to_conditions(bucket_weights: dict[str, float],
                         members: dict[str, list[str]],
                         baseline_conditions: dict[str, float]
                         ) -> dict[str, float]:
    """Split each bucket's mass across its member conditions using the
    BASELINE within-bucket ratios (locked decision 3)."""
    out: dict[str, float] = {}
    for bucket, mass in bucket_weights.items():
        names = members[bucket]
        base = {n: baseline_conditions[n] for n in names}
        total = sum(base.values())
        for n in names:
            out[n] = mass * (base[n] / total)
    return out


# --------------------------------------------------------------------------
# Cell enumeration
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    cell_id: str
    parameter: str
    handle: str
    direction: str
    value: Any
    low_information: bool = False


def enumerate_cells(reg: Registry) -> list[Cell]:
    """One-at-a-time grid. Baseline is not a cell; it is the reference run."""
    cells: list[Cell] = []
    include_topup = reg.sweep.get("include_topup_acceleration_cells", False)

    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        if p["status"] != "specified" or not p["sweep"].get("swept", False):
            continue

        if p["kind"] == "vector_simplex":
            for bucket, spec in p["handle"]["buckets"].items():
                for direction in reg.sweep["directions"]:
                    cells.append(Cell(
                        cell_id=f"{name}.{bucket}.{direction}",
                        parameter=name,
                        handle=f"bucket_mass:{bucket}",
                        direction=direction,
                        value=perturb_bucket(
                            {b: s["baseline"]
                             for b, s in p["handle"]["buckets"].items()},
                            bucket, direction, p["sweep"]["magnitude"]),
                        low_information=spec.get("low_information", False),
                    ))
        else:
            for direction in reg.sweep["directions"]:
                cells.append(Cell(
                    cell_id=f"{name}.{direction}",
                    parameter=name,
                    handle=p["handle"]["name"],
                    direction=direction,
                    value=p["sweep"]["cells"][direction],
                ))

    if include_topup:
        base = (reg.parameters["balance_restore_timing"]["definition"]
                ["topup_acceleration"]["p_topup_action"])
        mag = reg.sweep["default_magnitude"]
        for direction, f in (("low", 1 - mag), ("high", 1 + mag)):
            cells.append(Cell(
                cell_id=f"balance_restore_timing.topup_acceleration.{direction}",
                parameter="balance_restore_timing",
                handle="p_topup_action",
                direction=direction,
                value=round(base * f, 6),
            ))

    return cells


def required_wins(n_cells: int, reg: Registry) -> int:
    thr = reg.sweep["majority_threshold"]
    if reg.sweep.get("rounding", "ceil") == "ceil":
        return math.ceil(thr * n_cells)
    return round(thr * n_cells)
