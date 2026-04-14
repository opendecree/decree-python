"""Tests for the async ConfigWatcher."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import grpc
import grpc.aio
import pytest

from opendecree.async_watcher import AsyncConfigWatcher, AsyncWatchedField
from opendecree.types import Change
from tests.conftest import FakeRpcError

# --- AsyncWatchedField unit tests ---


class TestAsyncWatchedField:
    def test_default_value(self):
        f = AsyncWatchedField("x", float, 0.01)
        assert f.value == 0.01
        assert f.path == "x"

    def test_load_initial(self):
        f = AsyncWatchedField("x", int, 0)
        f._load_initial("42")
        assert f.value == 42

    def test_bool_truthy(self):
        f = AsyncWatchedField("x", bool, False)
        assert not f
        f._load_initial("true")
        assert f

    def test_update_fires_callback(self):
        f = AsyncWatchedField("x", float, 0.0)
        f._load_initial("1.0")
        results: list[tuple[float, float]] = []

        @f.on_change
        def cb(old: float, new: float) -> None:
            results.append((old, new))

        change = Change(field_path="x", old_value="1.0", new_value="2.0", version=1)
        f._update("2.0", change)

        assert results == [(1.0, 2.0)]
        assert f.value == 2.0

    def test_update_no_callback_if_same(self):
        f = AsyncWatchedField("x", str, "")
        f._load_initial("hello")
        results: list[tuple[str, str]] = []

        @f.on_change
        def cb(old: str, new: str) -> None:
            results.append((old, new))

        change = Change(field_path="x", old_value="hello", new_value="hello", version=1)
        f._update("hello", change)
        assert results == []

    def test_update_null_resets_to_default(self):
        f = AsyncWatchedField("x", float, 0.01)
        f._load_initial("5.0")

        change = Change(field_path="x", old_value="5.0", new_value=None, version=1)
        f._update(None, change)
        assert f.value == 0.01

    @pytest.mark.asyncio
    async def test_changes_iterator(self):
        f = AsyncWatchedField("x", str, "")

        c1 = Change(field_path="x", old_value="a", new_value="b", version=1)
        c2 = Change(field_path="x", old_value="b", new_value="c", version=2)

        f._change_queue.put_nowait(c1)
        f._change_queue.put_nowait(c2)
        f._change_queue.put_nowait(None)  # sentinel

        collected = [c async for c in f.changes()]
        assert len(collected) == 2
        assert collected[0].new_value == "b"
        assert collected[1].new_value == "c"

    def test_repr(self):
        f = AsyncWatchedField("payments.fee", float, 0.01)
        assert "payments.fee" in repr(f)

    def test_callback_exception_is_logged(self):
        f = AsyncWatchedField("x", int, 0)
        f._load_initial("1")

        @f.on_change
        def bad_cb(old: int, new: int) -> None:
            raise ValueError("boom")

        change = Change(field_path="x", old_value="1", new_value="2", version=1)
        f._update("2", change)  # should not raise
        assert f.value == 2


# --- AsyncConfigWatcher unit tests ---


class TestAsyncConfigWatcher:
    def _make_watcher(self) -> AsyncConfigWatcher:
        stub = MagicMock()
        pb2 = MagicMock()

        mock_resp = MagicMock()
        mock_resp.config.values = []
        stub.GetConfig = AsyncMock(return_value=mock_resp)

        return AsyncConfigWatcher(stub, pb2, "t1", timeout=5.0)

    def test_register_field(self):
        w = self._make_watcher()
        f = w.field("rate", float, default=0.01)
        assert isinstance(f, AsyncWatchedField)
        assert f.value == 0.01

    @pytest.mark.asyncio
    async def test_cannot_register_after_start(self):
        w = self._make_watcher()

        async def empty_stream():
            return
            yield

        w._stub.Subscribe.return_value = empty_stream()

        await w.start()
        with pytest.raises(RuntimeError, match="Cannot register"):
            w.field("x", str, default="")
        await w.stop()

    @pytest.mark.asyncio
    async def test_double_start_raises(self):
        w = self._make_watcher()

        async def empty_stream():
            return
            yield

        w._stub.Subscribe.return_value = empty_stream()

        await w.start()
        with pytest.raises(RuntimeError, match="already started"):
            await w.start()
        await w.stop()

    @pytest.mark.asyncio
    async def test_snapshot_loads_initial(self):
        stub = MagicMock()
        pb2 = MagicMock()

        from opendecree._generated.centralconfig.v1 import types_pb2

        cv = MagicMock()
        cv.field_path = "rate"
        cv.HasField.return_value = True
        cv.value = types_pb2.TypedValue(string_value="42")

        mock_resp = MagicMock()
        mock_resp.config.values = [cv]
        stub.GetConfig = AsyncMock(return_value=mock_resp)

        w = AsyncConfigWatcher(stub, pb2, "t1", timeout=5.0)
        rate = w.field("rate", int, default=0)

        async def empty_stream():
            return
            yield

        stub.Subscribe.return_value = empty_stream()

        await w.start()
        await asyncio.sleep(0.05)
        await w.stop()

        assert rate.value == 42

    @pytest.mark.asyncio
    async def test_context_manager(self):
        w = self._make_watcher()

        async def empty_stream():
            return
            yield

        w._stub.Subscribe.return_value = empty_stream()
        w.field("fee", float, default=0.0)

        async with w:
            assert w._task is not None

        assert w._task is None

    def test_process_change(self):
        w = self._make_watcher()
        fee = w.field("rate", float, default=0.0)
        fee._load_initial("1.0")

        from opendecree._generated.centralconfig.v1 import types_pb2

        change = MagicMock()
        change.field_path = "rate"
        change.HasField.side_effect = lambda name: name in ("old_value", "new_value")
        change.old_value = types_pb2.TypedValue(string_value="1.0")
        change.new_value = types_pb2.TypedValue(string_value="2.0")
        change.version = 5
        change.changed_by = "alice"

        w._process_change(change)
        assert fee.value == 2.0

    def test_process_change_unknown_field_ignored(self):
        w = self._make_watcher()
        w.field("known", str, default="")

        change = MagicMock()
        change.field_path = "unknown"

        w._process_change(change)  # should not raise

    @pytest.mark.asyncio
    async def test_reconnect_on_unavailable(self):
        """Subscribe raises UNAVAILABLE, watcher reconnects then stops."""
        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        call_count = 0

        def _subscribe_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, "connection lost")

            async def empty():
                return
                yield

            return empty()

        w._stub.Subscribe = MagicMock(side_effect=_subscribe_side_effect)

        await w.start()
        await asyncio.sleep(2.5)
        await w.stop()

        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_stops_loop(self):
        """Non-retryable gRPC error stops the subscribe loop."""
        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        w._stub.Subscribe = MagicMock(
            side_effect=FakeRpcError(grpc.StatusCode.PERMISSION_DENIED, "forbidden")
        )

        await w.start()
        await asyncio.sleep(0.5)
        # Task should have exited on its own.
        assert w._task is not None
        assert w._task.done()
        await w.stop()
