"""Tests for the sync ConfigClient."""

from unittest.mock import MagicMock, patch

import grpc
import pytest

import opendecree
from opendecree.errors import NotFoundError, UnavailableError
from tests.conftest import FakeRpcError


class TestConfigClientImport:
    """Test that the client is importable and has the expected API."""

    def test_import(self):
        assert hasattr(opendecree, "ConfigClient")

    def test_version_constants(self):
        assert opendecree.__version__ == "0.1.0"
        assert opendecree.SUPPORTED_SERVER_VERSION == ">=0.3.0,<1.0.0"
        assert opendecree.PROTO_VERSION == "v1"


class TestConfigClientUnit:
    """Unit tests with mocked gRPC stubs."""

    def _make_client(self):
        """Create a ConfigClient with mocked internals."""
        with patch("opendecree.client.create_channel") as mock_ch:
            mock_channel = MagicMock()
            mock_ch.return_value = mock_channel

            with patch("opendecree.client.grpc.intercept_channel") as mock_intercept:
                mock_intercept.return_value = mock_channel

                client = opendecree.ConfigClient(
                    "localhost:9090",
                    subject="test",
                )

        # Replace stub with mock.
        client._stub = MagicMock()
        return client

    def test_get_string(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(string_value="hello")
        client._stub.GetField.return_value = mock_resp

        result = client.get("t1", "payments.fee")
        assert result == "hello"

    def test_get_int(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(integer_value=42)
        client._stub.GetField.return_value = mock_resp

        result = client.get("t1", "retries", int)
        assert result == 42

    def test_get_bool(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(bool_value=True)
        client._stub.GetField.return_value = mock_resp

        result = client.get("t1", "enabled", bool)
        assert result is True

    def test_get_float(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(number_value=3.14)
        client._stub.GetField.return_value = mock_resp

        result = client.get("t1", "rate", float)
        assert result == pytest.approx(3.14)

    def test_get_nullable_returns_none(self):
        client = self._make_client()

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = False
        client._stub.GetField.return_value = mock_resp

        result = client.get("t1", "field", str, nullable=True)
        assert result is None

    def test_get_not_found_raises(self):
        client = self._make_client()

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = False
        client._stub.GetField.return_value = mock_resp

        with pytest.raises(NotFoundError):
            client.get("t1", "field")

    def test_get_grpc_error(self):
        client = self._make_client()
        client._stub.GetField.side_effect = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")

        with pytest.raises(UnavailableError):
            client.get("t1", "field")

    def test_get_all(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        cv1 = MagicMock()
        cv1.field_path = "a"
        cv1.HasField.return_value = True
        cv1.value = types_pb2.TypedValue(string_value="1")

        cv2 = MagicMock()
        cv2.field_path = "b"
        cv2.HasField.return_value = True
        cv2.value = types_pb2.TypedValue(string_value="2")

        mock_resp = MagicMock()
        mock_resp.config.values = [cv1, cv2]
        client._stub.GetConfig.return_value = mock_resp

        result = client.get_all("t1")
        assert result == {"a": "1", "b": "2"}

    def test_set(self):
        client = self._make_client()
        client._stub.SetField.return_value = MagicMock()

        client.set("t1", "payments.fee", "0.5%")
        client._stub.SetField.assert_called_once()

    def test_set_many(self):
        client = self._make_client()
        client._stub.SetFields.return_value = MagicMock()

        client.set_many("t1", {"a": "1", "b": "2"}, description="batch")
        client._stub.SetFields.assert_called_once()

    def test_set_null(self):
        client = self._make_client()
        client._stub.SetField.return_value = MagicMock()

        client.set_null("t1", "payments.fee")
        client._stub.SetField.assert_called_once()

    def test_get_all_grpc_error(self):
        client = self._make_client()
        client._stub.GetConfig.side_effect = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")

        with pytest.raises(UnavailableError):
            client.get_all("t1")

    def test_set_grpc_error(self):
        client = self._make_client()
        client._stub.SetField.side_effect = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")

        with pytest.raises(UnavailableError):
            client.set("t1", "payments.fee", "0.5%")

    def test_set_many_grpc_error(self):
        client = self._make_client()
        client._stub.SetFields.side_effect = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")

        with pytest.raises(UnavailableError):
            client.set_many("t1", {"a": "1"})

    def test_set_null_grpc_error(self):
        client = self._make_client()
        client._stub.SetField.side_effect = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")

        with pytest.raises(UnavailableError):
            client.set_null("t1", "payments.fee")

    def test_no_interceptor_when_no_metadata(self):
        """Client with no subject/token/role skips interceptor (line 69)."""
        with patch("opendecree.client.create_channel") as mock_ch:
            mock_channel = MagicMock()
            mock_ch.return_value = mock_channel

            with patch("opendecree.client.grpc.intercept_channel") as mock_intercept:
                # Must override role="" to produce empty metadata
                opendecree.ConfigClient("localhost:9090", role="")
                mock_intercept.assert_not_called()

    def test_context_manager(self):
        with patch("opendecree.client.create_channel") as mock_ch:
            mock_channel = MagicMock()
            mock_ch.return_value = mock_channel

            with opendecree.ConfigClient("localhost:9090") as client:
                assert client is not None

            mock_channel.close.assert_called_once()

    def test_watch_returns_context(self):
        client = self._make_client()
        ctx = client.watch("t1")
        assert ctx is not None
        with ctx as watcher:
            assert watcher is not None
