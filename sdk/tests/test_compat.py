"""Tests for version compatibility checking."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opendecree._compat import (
    _parse_version,
    _satisfies,
    async_fetch_server_version,
    check_version_compatible,
    fetch_server_version,
)
from opendecree.errors import IncompatibleServerError
from opendecree.types import ServerVersion

# --- _parse_version ---


def test_parse_semver():
    assert _parse_version("0.3.1") == (0, 3, 1)


def test_parse_with_v_prefix():
    assert _parse_version("v1.2.3") == (1, 2, 3)


def test_parse_major_only():
    assert _parse_version("2") == (2,)


def test_parse_dev():
    assert _parse_version("dev") is None


def test_parse_empty():
    assert _parse_version("") is None


# --- _satisfies ---


def test_satisfies_gte():
    assert _satisfies((0, 3, 1), ">=0.3.0") is True
    assert _satisfies((0, 3, 0), ">=0.3.0") is True
    assert _satisfies((0, 2, 9), ">=0.3.0") is False


def test_satisfies_lt():
    assert _satisfies((0, 9, 0), "<1.0.0") is True
    assert _satisfies((1, 0, 0), "<1.0.0") is False


def test_satisfies_eq():
    assert _satisfies((1, 2, 3), "==1.2.3") is True
    assert _satisfies((1, 2, 4), "==1.2.3") is False


def test_satisfies_neq():
    assert _satisfies((1, 2, 4), "!=1.2.3") is True
    assert _satisfies((1, 2, 3), "!=1.2.3") is False


def test_satisfies_padding():
    """Shorter version tuples are padded with zeros."""
    assert _satisfies((1,), ">=1.0.0") is True
    assert _satisfies((1,), "<2.0.0") is True


def test_satisfies_invalid_constraint():
    assert _satisfies((1, 0, 0), "garbage") is True


# --- check_version_compatible ---


def test_compatible_version():
    check_version_compatible("0.3.1", ">=0.3.0,<1.0.0")  # should not raise


def test_incompatible_too_old():
    with pytest.raises(IncompatibleServerError, match="not compatible"):
        check_version_compatible("0.2.0", ">=0.3.0,<1.0.0")


def test_incompatible_too_new():
    with pytest.raises(IncompatibleServerError, match="not compatible"):
        check_version_compatible("1.0.0", ">=0.3.0,<1.0.0")


def test_dev_version_skips_check():
    check_version_compatible("dev", ">=0.3.0,<1.0.0")  # should not raise


def test_uses_default_range():
    # Default is SUPPORTED_SERVER_VERSION = ">=0.3.0,<1.0.0"
    check_version_compatible("0.5.0")  # should not raise


# --- fetch_server_version ---


def test_fetch_server_version():
    stub = MagicMock()
    pb2 = MagicMock()
    resp = MagicMock()
    resp.version = "0.3.1"
    resp.commit = "abc123"
    stub.GetServerVersion.return_value = resp

    sv = fetch_server_version(stub, pb2, timeout=5.0)
    assert sv == ServerVersion(version="0.3.1", commit="abc123")
    stub.GetServerVersion.assert_called_once()


@pytest.mark.asyncio
async def test_async_fetch_server_version():
    stub = MagicMock()
    pb2 = MagicMock()
    resp = MagicMock()
    resp.version = "0.3.1"
    resp.commit = "abc123"
    stub.GetServerVersion = AsyncMock(return_value=resp)

    sv = await async_fetch_server_version(stub, pb2, timeout=5.0)
    assert sv == ServerVersion(version="0.3.1", commit="abc123")


# --- ConfigClient.server_version + check_compatibility ---


def test_client_server_version_cached():
    """server_version property fetches once, returns cached."""
    with patch("opendecree.client.create_channel"):
        from opendecree import ConfigClient

        client = ConfigClient.__new__(ConfigClient)
        client._timeout = 5.0

        mock_stub = MagicMock()
        resp = MagicMock()
        resp.version = "0.3.1"
        resp.commit = "abc123"
        mock_stub.GetServerVersion.return_value = resp
        client._version_stub = mock_stub
        client._version_pb2 = MagicMock()
        client._server_version = None

        # First call fetches
        v1 = client.server_version
        assert v1.version == "0.3.1"
        assert mock_stub.GetServerVersion.call_count == 1

        # Second call returns cached
        v2 = client.server_version
        assert v2 is v1
        assert mock_stub.GetServerVersion.call_count == 1


def test_client_check_compatibility_passes():
    with patch("opendecree.client.create_channel"):
        from opendecree import ConfigClient

        client = ConfigClient.__new__(ConfigClient)
        client._timeout = 5.0
        client._server_version = ServerVersion(version="0.3.1", commit="abc")
        client._version_stub = MagicMock()
        client._version_pb2 = MagicMock()

        client.check_compatibility()  # should not raise


def test_client_check_compatibility_fails():
    with patch("opendecree.client.create_channel"):
        from opendecree import ConfigClient

        client = ConfigClient.__new__(ConfigClient)
        client._timeout = 5.0
        client._server_version = ServerVersion(version="0.1.0", commit="abc")
        client._version_stub = MagicMock()
        client._version_pb2 = MagicMock()

        with pytest.raises(IncompatibleServerError):
            client.check_compatibility()
