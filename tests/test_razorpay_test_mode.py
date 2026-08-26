"""EVAL.md §3 [INVARIANT]: razorpay_client raises unless the key matches
^rzp_test_.

No network access anywhere in this file. The SDK constructor is replaced
with a tripwire that fails the test if it is ever reached with a bad key,
which is how we prove the guard fires *before* the network path rather
than merely alongside it.
"""

from __future__ import annotations

import pytest

from rrx.integrations import razorpay_client as rc
from rrx.integrations.razorpay_client import LiveKeyRejected, assert_test_mode_key

VALID_TEST_KEYS = ["rzp_test_1DP5mmOlF5G5ag", "rzp_test_abc123XYZ"]

REJECTED_KEYS = [
    "rzp_live_1DP5mmOlF5G5ag",   # live key
    "rzp_live_",                 # bare live prefix
    "RZP_TEST_1DP5mmOlF5G5ag",   # wrong case - prefix match is exact
    " rzp_test_1DP5mmOlF5G5ag",  # leading whitespace
    "rzp_test_1DP5mmOlF5G5ag ",  # trailing whitespace
    "rzp_test_",                 # prefix with no body
    "xrzp_test_1DP5mmOlF5G5ag",  # prefix not anchored at start
    "sk_test_1DP5mmOlF5G5ag",    # wrong vendor
    "",
    None,
]


@pytest.fixture
def tripwire(monkeypatch):
    """Any call to the SDK constructor is a failure unless the test expects it."""
    calls = []

    def _fake(key_id, key_secret):
        calls.append(key_id)
        return object()

    monkeypatch.setattr(rc, "_build_sdk_client", _fake)
    return calls


# -- pure guard -------------------------------------------------------------

@pytest.mark.parametrize("key", VALID_TEST_KEYS)
def test_test_mode_keys_accepted(key):
    assert assert_test_mode_key(key) == key


@pytest.mark.parametrize("key", REJECTED_KEYS)
def test_non_test_keys_rejected(key):
    with pytest.raises(LiveKeyRejected):
        assert_test_mode_key(key)


def test_live_key_error_message_names_the_invariant():
    with pytest.raises(LiveKeyRejected, match="test-mode"):
        assert_test_mode_key("rzp_live_1DP5mmOlF5G5ag")


# -- client construction ----------------------------------------------------

@pytest.mark.parametrize("key", VALID_TEST_KEYS)
def test_client_constructs_with_test_key(key, tripwire):
    client = rc.RazorpayClient(key, "secret")
    assert client.key_id == key
    assert tripwire == [key]


@pytest.mark.parametrize("key", REJECTED_KEYS)
def test_client_rejects_before_sdk_is_built(key, tripwire):
    """The load-bearing assertion: the SDK constructor is never reached, so
    no live key can reach a socket."""
    with pytest.raises(LiveKeyRejected):
        rc.RazorpayClient(key, "secret")
    assert tripwire == [], f"SDK constructed for rejected key {key!r}"


def test_missing_secret_rejected_even_with_valid_test_key(tripwire):
    with pytest.raises(LiveKeyRejected):
        rc.RazorpayClient("rzp_test_1DP5mmOlF5G5ag", "")
    assert tripwire == []


def test_guard_is_offline():
    """assert_test_mode_key must not import the SDK or touch the network."""
    import sys

    sys.modules.pop("razorpay", None)
    assert_test_mode_key("rzp_test_1DP5mmOlF5G5ag")
    assert "razorpay" not in sys.modules
