"""Tests for the async ConfigClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import grpc.aio
import pytest

from opendecree.async_client import AsyncConfigClient
from opendecree.errors import DecreeError, NotFoundError, UnavailableError
from opendecree.types import FieldUpdate
from tests.conftest import FakeRpcError


class TestAsyncConfigClientUnit:
    """Unit tests with mocked gRPC stubs."""

    def _make_client(self) -> AsyncConfigClient:
        """Create an AsyncConfigClient with mocked internals."""
        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_channel = MagicMock()
            mock_ch.return_value = mock_channel
            client = AsyncConfigClient("localhost:9090", subject="test")

        client._stub = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_get_string(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(string_value="hello")
        client._stub.GetField = AsyncMock(return_value=mock_resp)

        result = await client.get("t1", "payments.fee")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_get_int(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(integer_value=42)
        client._stub.GetField = AsyncMock(return_value=mock_resp)

        result = await client.get("t1", "retries", int)
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_bool(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(bool_value=True)
        client._stub.GetField = AsyncMock(return_value=mock_resp)

        result = await client.get("t1", "enabled", bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_float(self):
        client = self._make_client()
        from opendecree._generated.centralconfig.v1 import types_pb2

        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = True
        mock_resp.value.value = types_pb2.TypedValue(number_value=3.14)
        client._stub.GetField = AsyncMock(return_value=mock_resp)

        result = await client.get("t1", "rate", float)
        assert result == pytest.approx(3.14)

    @pytest.mark.asyncio
    async def test_get_nullable_returns_none(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = False
        client._stub.GetField = AsyncMock(return_value=mock_resp)

        result = await client.get("t1", "field", str, nullable=True)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_not_found_raises(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.value.HasField.return_value = False
        client._stub.GetField = AsyncMock(return_value=mock_resp)

        with pytest.raises(NotFoundError):
            await client.get("t1", "field")

    @pytest.mark.asyncio
    async def test_get_grpc_error(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")
        client._stub.GetField = AsyncMock(side_effect=err)

        with pytest.raises(UnavailableError):
            await client.get("t1", "field")

    @pytest.mark.asyncio
    async def test_get_all(self):
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
        client._stub.GetConfig = AsyncMock(return_value=mock_resp)

        result = await client.get_all("t1")
        assert result == {"a": "1", "b": "2"}

    @pytest.mark.asyncio
    async def test_set(self):
        client = self._make_client()
        client._stub.SetField = AsyncMock(return_value=MagicMock())

        await client.set("t1", "payments.fee", "0.5%")
        client._stub.SetField.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_with_metadata(self):
        client = self._make_client()
        client._stub.SetField = AsyncMock(return_value=MagicMock())

        await client.set(
            "t1",
            "payments.fee",
            "0.5%",
            description="fee increase",
            value_description="Q2 rate",
            expected_checksum="abc123",
        )
        req = client._stub.SetField.call_args[0][0]
        assert req.description == "fee increase"
        assert req.value_description == "Q2 rate"
        assert req.expected_checksum == "abc123"

    @pytest.mark.asyncio
    async def test_set_many(self):
        client = self._make_client()
        client._stub.SetFields = AsyncMock(return_value=MagicMock())

        updates = [FieldUpdate("a", "1"), FieldUpdate("b", "2")]
        await client.set_many("t1", updates, description="batch")
        client._stub.SetFields.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_many_with_per_field_metadata(self):
        client = self._make_client()
        client._stub.SetFields = AsyncMock(return_value=MagicMock())

        updates = [
            FieldUpdate("a", "1", expected_checksum="cs1", value_description="first"),
            FieldUpdate("b", "2"),
        ]
        await client.set_many("t1", updates)
        client._stub.SetFields.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_null(self):
        client = self._make_client()
        client._stub.SetField = AsyncMock(return_value=MagicMock())

        await client.set_null("t1", "payments.fee")
        client._stub.SetField.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_grpc_error(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")
        client._stub.GetConfig = AsyncMock(side_effect=err)

        with pytest.raises(UnavailableError):
            await client.get_all("t1")

    @pytest.mark.asyncio
    async def test_set_grpc_error(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")
        client._stub.SetField = AsyncMock(side_effect=err)

        with pytest.raises(UnavailableError):
            await client.set("t1", "payments.fee", "0.5%")

    @pytest.mark.asyncio
    async def test_set_many_grpc_error(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")
        client._stub.SetFields = AsyncMock(side_effect=err)

        with pytest.raises(UnavailableError):
            await client.set_many("t1", [FieldUpdate("a", "1")])

    @pytest.mark.asyncio
    async def test_set_null_grpc_error(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "down")
        client._stub.SetField = AsyncMock(side_effect=err)

        with pytest.raises(UnavailableError):
            await client.set_null("t1", "payments.fee")

    @pytest.mark.asyncio
    async def test_set_does_not_retry_on_deadline_exceeded(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED)
        client._stub.SetField = AsyncMock(side_effect=err)

        with patch("opendecree._retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(DecreeError):
                await client.set("t1", "payments.fee", "0.5%")

        client._stub.SetField.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_retries_on_deadline_exceeded_with_idempotency_key(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED)
        client._stub.SetField = AsyncMock(side_effect=[err, None])

        with patch("opendecree._retry.asyncio.sleep", new_callable=AsyncMock):
            await client.set("t1", "payments.fee", "0.5%", idempotency_key="idem-1")

        assert client._stub.SetField.call_count == 2

    @pytest.mark.asyncio
    async def test_set_many_does_not_retry_on_deadline_exceeded(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED)
        client._stub.SetFields = AsyncMock(side_effect=err)

        with patch("opendecree._retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(DecreeError):
                await client.set_many("t1", [FieldUpdate("a", "1")])

        client._stub.SetFields.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_null_does_not_retry_on_deadline_exceeded(self):
        client = self._make_client()
        err = FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED)
        client._stub.SetField = AsyncMock(side_effect=err)

        with patch("opendecree._retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(DecreeError):
                await client.set_null("t1", "payments.fee")

        client._stub.SetField.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_channel = AsyncMock()
            mock_ch.return_value = mock_channel

            async with AsyncConfigClient("localhost:9090") as client:
                assert client is not None

            mock_channel.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_returns_watcher(self):
        client = self._make_client()

        # Mock GetConfig for initial snapshot load
        mock_resp = MagicMock()
        mock_resp.config.values = []
        client._stub.GetConfig = AsyncMock(return_value=mock_resp)

        # Mock Subscribe to return an empty async iterator
        async def _empty_stream():
            return
            yield  # makes this an async generator

        client._stub.Subscribe = MagicMock(return_value=_empty_stream())

        ctx = client.watch("t1")
        async with ctx as watcher:
            assert watcher is not None

    def test_custom_interceptors_passed_to_channel(self):
        custom = MagicMock()
        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            AsyncConfigClient("localhost:9090", interceptors=[custom])
        assert mock_ch.call_args.kwargs["interceptors"] == [custom]

    def test_no_interceptors_by_default(self):
        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            AsyncConfigClient("localhost:9090")
        assert mock_ch.call_args.kwargs.get("interceptors") is None

    def test_multiple_custom_interceptors_preserved(self):
        a = MagicMock()
        b = MagicMock()
        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            AsyncConfigClient("localhost:9090", interceptors=[a, b])
        assert mock_ch.call_args.kwargs["interceptors"] == [a, b]
