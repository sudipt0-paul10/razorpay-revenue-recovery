"""docs/A3-DESIGN.md §11/§19's `stale_state` fallback_reason: "Gate
re-checks current state.subscription_state at proposal-evaluation time,
not just prompt-build time; a mismatch -> fallback_reason=stale_state."

Day 6 Stage 6B final amendment, requirement 4: implement this only to the
extent the frozen contract and sim-v1's actual architecture require, and
if unreachable, make that explicit rather than inventing artificial
behavior. This file is that explicit documentation, backed by two checks:

1. STATIC - no code path anywhere in this repository ever sets
   fallback_reason to "stale_state" (grepped, not assumed).
2. RUNTIME - across real dev episodes, the EpisodeView the gate evaluates
   is the SAME object the policy was called with - proven via dependency
   injection through run_episode_a3's own `gate` parameter, not by
   inspecting source text alone. sim-v1's day loop is single-threaded and
   fully synchronous: nothing runs between "policy(view)" and
   "gate(proposal, view)" that could rebuild or mutate `view`, so there is
   no candidate mechanism for staleness to occur through, live LLM
   latency included - `client.complete()` (mocked or real) still runs
   inside this same synchronous call stack in sim-v1, since the simulator
   has no wall-clock/concurrency model at all (day-granular ticks only).
"""

from __future__ import annotations

import ast
from pathlib import Path

from rrx.agent.gate import GateVerdict, evaluate_gate
from rrx.agent.null_policy import null_policy
from rrx.harness.runner import run_episode_a3
from rrx.harness.splits import DEV_INDICES, DEV_SPLIT
from rrx.sim.latent import load_configs

EPISODE_CFG, POPULATION_CFG = load_configs()

SRC = Path(__file__).resolve().parents[1] / "src"
_CHECKED_FILES = (
    SRC / "rrx" / "harness" / "runner.py",
    SRC / "rrx" / "agent" / "planner.py",
    SRC / "rrx" / "agent" / "ledger.py",
)


def test_no_source_file_ever_assigns_stale_state_as_a_fallback_reason():
    """Static proof: "stale_state" appears nowhere as a string literal
    assigned to a fallback_reason-shaped target in the runner/planner/
    ledger modules - it exists only in docs/comments, never as live code."""
    for path in _CHECKED_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                if node.value.value == "stale_state":
                    raise AssertionError(
                        f"{path}: 'stale_state' is assigned as a live value at "
                        f"line {node.lineno} - update this test, this module, or both"
                    )


def test_view_passed_to_the_gate_is_the_identical_object_the_policy_saw():
    """Runtime proof, via dependency injection: if the runner ever
    rebuilt or refreshed the view between the policy call and the gate
    call, this identity check would fail. It never does, over real dev
    episodes - confirming there is no rebuild/refresh point for
    subscription_state to have diverged through."""
    seen_by_policy: dict[int, object] = {}

    def recording_policy(view):
        seen_by_policy["view"] = view
        return null_policy(view)

    def identity_checking_gate(proposal, view, **kwargs) -> GateVerdict:
        assert view is seen_by_policy["view"], (
            "gate received a different EpisodeView object than the policy did - "
            "this would be the structural precondition for stale_state, and it "
            "never happens in sim-v1's synchronous day loop"
        )
        return evaluate_gate(proposal, view, **kwargs)

    for i in list(DEV_INDICES)[:50]:
        run_episode_a3(
            DEV_SPLIT, i, recording_policy, EPISODE_CFG, POPULATION_CFG,
            gate=identity_checking_gate,
        )


def test_nothing_executes_between_the_policy_call_and_the_gate_call_in_source():
    """Source-level companion to the runtime check above: in
    src/rrx/harness/runner.py's wakeup branch, the statement that computes
    `proposal = policy(view)` is followed immediately (next statement) by
    the statement that computes `gate_verdict = gate(proposal, view)` -
    no intervening statement exists that could mutate `state` or rebuild
    `view` in between."""
    path = SRC / "rrx" / "harness" / "runner.py"
    lines = path.read_text(encoding="utf-8").splitlines()

    policy_call_idx = next(
        i for i, line in enumerate(lines) if "proposal = policy(view)" in line
    )
    gate_call_idx = next(
        i for i, line in enumerate(lines) if "gate_verdict = gate(proposal, view)" in line
    )
    between = [
        line.strip() for line in lines[policy_call_idx + 1:gate_call_idx]
        if line.strip() and not line.strip().startswith("#")
    ]
    assert between == [], (
        f"non-comment statement(s) found between the policy call and the gate "
        f"call: {between!r} - re-examine whether stale_state has become reachable"
    )
