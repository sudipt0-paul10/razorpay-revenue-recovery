"""Day 4 foundation: a policy with zero intelligence.

Used only to exercise the A3 runner's execution path
(docs/A3-DESIGN.md Task 4A §3, §16's byte-identity proof). Always
proposes WAIT - no rule logic, no randomness, no LLM calls, no reading of
`view`. This is NOT A3-D (src/rrx/agent/policy.py, not implemented in
this pass) - deliberately kept in a separate module so it is never
mistaken for, or later expanded into, the real deterministic ablation.
"""

from __future__ import annotations

from rrx.agent.proposal import Proposal
from rrx.features.episode_view import EpisodeView

# Not one of docs/A3-DESIGN.md §7's 7 frozen reason_code values - this
# policy has no decision logic to justify any of those, and assigning one
# would fabricate a reason this policy does not have. The gate/ledger are
# no-op stubs in this pass (src/rrx/agent/gate.py, ledger.py), so nothing
# validates this value against the §7 enum yet; that validation is future
# gate work, out of scope for Task 4A.
NULL_POLICY_REASON_CODE = "null_policy_no_reasoning"


def null_policy(view: EpisodeView) -> Proposal:
    """Always WAIT. `view` is accepted (matching the real policy
    signature) but never inspected - this policy carries no logic to
    inspect it with."""
    return Proposal(
        action_type="WAIT",
        remedy=None,
        rationale="null_policy: always WAIT, no decision logic",
        reason_code=NULL_POLICY_REASON_CODE,
    )
