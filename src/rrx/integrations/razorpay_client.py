"""Razorpay client wrapper.

EVAL.md §3 [INVARIANT]: live calls are test-mode only - this module raises
unless the key matches ^rzp_test_.

The guard runs in __init__, before the SDK object is constructed and before
any socket is opened. A live key never reaches the network path.
"""

from __future__ import annotations

import re

TEST_KEY_PATTERN = re.compile(r"^rzp_test_[A-Za-z0-9]+$")
LIVE_KEY_PREFIX = "rzp_live_"


class LiveKeyRejected(RuntimeError):
    """Raised when a non-test key is supplied. EVAL.md §3 [INVARIANT]."""


def assert_test_mode_key(key_id: str | None) -> str:
    """Validate a Razorpay key id. Returns it on success, raises otherwise.

    Pure and offline. Called before any client construction so that a live
    key is rejected before a network call is possible.
    """
    if not isinstance(key_id, str) or not key_id:
        raise LiveKeyRejected(
            "No Razorpay key id supplied. This project runs in test mode only."
        )
    if key_id.startswith(LIVE_KEY_PREFIX):
        raise LiveKeyRejected(
            "Live Razorpay key rejected. EVAL.md §3 permits test-mode keys "
            "only; no live key may reach the network path."
        )
    if not TEST_KEY_PATTERN.match(key_id):
        raise LiveKeyRejected(
            f"Key id does not match ^rzp_test_: {key_id[:12]!r}..."
        )
    return key_id


def _build_sdk_client(key_id: str, key_secret: str):
    """Isolated so tests can monkeypatch it and prove the guard fires first."""
    import razorpay  # imported lazily; not needed for the guard

    return razorpay.Client(auth=(key_id, key_secret))


class RazorpayClient:
    def __init__(self, key_id: str | None, key_secret: str | None) -> None:
        # Guard first. Nothing is constructed and no socket is opened until
        # this returns.
        self.key_id = assert_test_mode_key(key_id)
        if not key_secret:
            raise LiveKeyRejected("No Razorpay key secret supplied.")
        self._sdk = _build_sdk_client(self.key_id, key_secret)

    @property
    def sdk(self):
        return self._sdk
