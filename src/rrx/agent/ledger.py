"""Day 4 foundation: no-op stub only.

Real per-tick JSONL audit records (docs/A3-DESIGN.md §14) are out of
scope for Task 4A. This stub is called once per day by the runner
(§3 step 9) so that call site exists in the day-loop contract, but it
writes nothing anywhere.
"""

from __future__ import annotations

from typing import Any


def no_op_ledger_record(**kwargs: Any) -> None:
    """Records nothing. Real ledger persistence (§14) is future work."""
    return None
