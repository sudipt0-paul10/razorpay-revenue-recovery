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

    # Any [MODEL] magnitude nested inside a parameter's definition: block and
    # marked sweep_required: true must reach the grid too - EVAL.md §0 does
    # not exempt nested magnitudes. Distinct from the include_topup special
    # case above: p_topup_action uses swept: false (an open, un-swept toggle
    # per DEFECT 1), not sweep_required, so it is untouched by this loop.
    for name in CANONICAL_MODEL_PARAMS:
        p = reg.parameters[name]
        definition = p.get("definition")
        if not definition:
            continue
        for path, node in _sweep_required_nodes(definition):
            sweep = node.get("sweep") or {}
            node_cells = sweep.get("cells")
            if not node_cells:
                # Deliberately lenient: a sweep_required node with no cells
                # contributes none here. tests/test_model_params_swept.py's
                # test_all_sweep_required_entries_produce_cells is what turns
                # this into a failure, so the gap is caught at test time with
                # a clear message rather than as a silent skip.
                continue
            for direction in reg.sweep["directions"]:
                if direction not in node_cells:
                    continue
                cells.append(Cell(
                    cell_id=f"{name}.{path}.{direction}",
                    parameter=name,
                    handle=sweep.get("handle", path),
                    direction=direction,
                    value=node_cells[direction],
                ))

    return cells


def _sweep_required_nodes(node: Any, path: str = "") -> list[tuple[str, dict]]:
    """Recursively find every dict node with sweep_required: true.

    Does not descend into a node once found - a sweep_required node is a
    leaf for this purpose, not a container of further sweep_required nodes.
    """
    found: list[tuple[str, dict]] = []
    if isinstance(node, dict):
        if node.get("sweep_required") is True:
            found.append((path, node))
            return found
        for key, value in node.items():
            sub_path = f"{path}.{key}" if path else key
            found.extend(_sweep_required_nodes(value, sub_path))
    return found


def find_sweep_required_nodes(reg: Registry) -> list[tuple[str, str]]:
    """(parameter, path) for every sweep_required: true node anywhere in
    any of the six canonical parameters' definition: blocks."""
    out: list[tuple[str, str]] = []
    for name in CANONICAL_MODEL_PARAMS:
        definition = reg.parameters[name].get("definition")
        if not definition:
            continue
        out.extend((name, path) for path, _ in _sweep_required_nodes(definition))
    return out


def scalar_valued_handles(reg: Registry, parameter: str) -> set[str]:
    """Handles, among `parameter`'s definition-nested sweep_required nodes,
    whose declared sweep.cells values are scalars rather than vectors/dicts.

    Lets a caller distinguish a legitimate scalar [MODEL] magnitude (e.g.
    failure_mix_weights.ambiguous_cause_split's p_card_cause) from a
    bucket-vector cell that has been corrupted into a scalar - see
    tests/test_failure_mix_simplex.py's companion assertion to the
    isinstance(c.value, dict) guard.
    """
    definition = reg.parameters[parameter].get("definition")
    if not definition:
        return set()
    out: set[str] = set()
    for path, node in _sweep_required_nodes(definition):
        sweep = node.get("sweep") or {}
        node_cells = sweep.get("cells") or {}
        if node_cells and all(isinstance(v, (int, float))
                              for v in node_cells.values()):
            out.add(sweep.get("handle", path))
    return out


def unswept_required_entries(reg: Registry,
                              cells: list[Cell] | None = None) -> list[str]:
    """'{parameter}.{path}' for every sweep_required: true node that has no
    corresponding cell in enumerate_cells(reg).

    This is the check that today's bug needed: ambiguous_cause_split and
    transient_block_clearance were both marked sweep_required: true but had
    no sweep.cells, so enumerate_cells() silently produced zero cells for
    them and no existing test noticed, because none of them looked inside
    definition: blocks.
    """
    cells = cells if cells is not None else enumerate_cells(reg)
    missing: list[str] = []
    for name, path in find_sweep_required_nodes(reg):
        prefix = f"{name}.{path}."
        if not any(c.parameter == name and c.cell_id.startswith(prefix)
                   for c in cells):
            missing.append(f"{name}.{path}")
    return missing


def required_wins(n_cells: int, reg: Registry) -> int:
    thr = reg.sweep["majority_threshold"]
    if reg.sweep.get("rounding", "ceil") == "ceil":
        return math.ceil(thr * n_cells)
    return round(thr * n_cells)
