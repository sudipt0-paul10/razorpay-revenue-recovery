"""Day 6 Stage 6B required test #20: the holdout guard remains intact
after adding the A3-LLM scaffolding.

Per Day 6 Decision 5, this file deliberately never calls
`holdout_indices(authorized=True)` - only the refusal path is exercised.
Confirming the guard raises without authorization is sufficient to prove
"the guard is intact"; exercising the authorized path is unnecessary for
that purpose and is explicitly prohibited for this stage regardless.
"""

from __future__ import annotations

import pytest

from rrx.harness.splits import HoldoutNotAuthorizedError, holdout_indices


def test_holdout_indices_refuses_without_authorization():
    with pytest.raises(HoldoutNotAuthorizedError):
        holdout_indices()


def test_holdout_indices_refuses_with_explicit_authorized_false():
    with pytest.raises(HoldoutNotAuthorizedError):
        holdout_indices(authorized=False)
