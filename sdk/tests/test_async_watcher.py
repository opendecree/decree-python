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
        f._load_initial("a")

        c1 = Change(field_path="x", old_value="a", new_value="b", version=1)
        c2 = Change(field_path="x", old_value="b", new_value="c", version=2)

        # Populate via the internal helpers (matching the production path).
        f._update("b", c1)
        f._update("c", c2)
        f._stop()

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

    def test_on_callback_error_hook_is_called(self):
        errors: list[Exception] = []
        f = AsyncWatchedField("x", int, 0, on_callback_error=errors.append)
        f._load_initial("1")

        @f.on_change
        def bad_cb(old: int, new: int) -> None:
            raise ValueError("boom")

        change = Change(field_path="x", old_value="1", new_value="2", version=1)
        f._update("2", change)

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
        assert str(errors[0]) == "boom"
        assert f.value == 2

    def test_on_callback_error_hook_via_field_method(self):
        errors: list[Exception] = []
        stub = MagicMock()
        pb2 = MagicMock()
        mock_resp = MagicMock()
        mock_resp.config.values = []
        stub.GetConfig = AsyncMock(return_value=mock_resp)

        w = AsyncConfigWatcher(stub, pb2, "t1", timeout=5.0)
        f = w.field("x", int, default=0, on_callback_error=errors.append)
        f._load_initial("1")

        @f.on_change
        def bad_cb(old: int, new: int) -> None:
            raise RuntimeError("fail")

        change = Change(field_path="x", old_value="1", new_value="2", version=1)
        f._update("2", change)

        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)

    # --- Bounded queue tests ---

    def test_dropped_changes_starts_at_zero(self):
        f = AsyncWatchedField("x", str, "", max_queue_size=5)
        assert f.dropped_changes == 0

    def test_queue_fills_without_dropping_below_limit(self):
        f = AsyncWatchedField("x", str, "", max_queue_size=3)
        for i in range(3):
            c = Change(field_path="x", old_value=str(i), new_value=str(i + 1), version=i)
            f._update(str(i + 1), c)

        assert f.dropped_changes == 0
        assert len(f._change_queue) == 3

    def test_oldest_entry_dropped_when_queue_full(self):
        f = AsyncWatchedField("x", str, "", max_queue_size=3)
        for i in range(5):
            c = Change(field_path="x", old_value=str(i), new_value=str(i + 1), version=i)
            f._update(str(i + 1), c)

        assert f.dropped_changes == 2
        assert len(f._change_queue) == 3
        versions = [c.version for c in f._change_queue]
        assert versions == [2, 3, 4]

    def test_drop_logs_warning(self, caplog):
        import logging

        f = AsyncWatchedField("payments.fee", str, "", max_queue_size=2)
        with caplog.at_level(logging.WARNING, logger="opendecree.async_watcher"):
            for i in range(4):
                c = Change(
                    field_path="payments.fee", old_value=str(i), new_value=str(i + 1), version=i
                )
                f._update(str(i + 1), c)

        assert f.dropped_changes == 2
        warning_records = [r for r in caplog.records if "dropped" in r.message]
        assert len(warning_records) == 2
        assert "payments.fee" in warning_records[0].message

    def test_max_queue_size_constructor_arg(self):
        f = AsyncWatchedField("x", str, "", max_queue_size=10)
        assert f._max_queue_size == 10

    def test_default_max_queue_size(self):
        from opendecree.async_watcher import _DEFAULT_MAX_QUEUE_SIZE

        f = AsyncWatchedField("x", str, "")
        assert f._max_queue_size == _DEFAULT_MAX_QUEUE_SIZE
        assert _DEFAULT_MAX_QUEUE_SIZE == 1024

    @pytest.mark.asyncio
    async def test_changes_spurious_wake_skipped(self):
        f = AsyncWatchedField("x", str, "")
        f._load_initial("a")

        # Set event without putting anything in the queue → spurious wake
        f._queue_event.set()

        async def _collect_first():
            async for c in f.changes():
                return c

        task = asyncio.create_task(_collect_first())
        # Yield twice so the task can process the spurious wake (clears event, loops back)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        # Now deliver a real change + stop
        change = Change(field_path="x", old_value="a", new_value="b", version=1)
        f._update("b", change)

        result = await asyncio.wait_for(task, timeout=2.0)
        assert result.new_value == "b"

    @pytest.mark.asyncio
    async def test_changes_iterator_after_overflow(self):
        f = AsyncWatchedField("x", str, "", max_queue_size=2)
        for i in range(4):
            c = Change(field_path="x", old_value=str(i), new_value=str(i + 1), version=i)
            f._update(str(i + 1), c)
        f._stop()

        collected = [c async for c in f.changes()]
        assert len(collected) == 2
        assert collected[0].version == 2
        assert collected[1].version == 3


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

    @pytest.mark.asyncio
    async def test_auth_metadata_forwarded(self):
        """metadata= is passed to both GetConfig and Subscribe."""
        stub = MagicMock()
        pb2 = MagicMock()

        mock_resp = MagicMock()
        mock_resp.config.values = []
        stub.GetConfig = AsyncMock(return_value=mock_resp)

        auth_meta = [("x-subject", "svc"), ("x-role", "superadmin")]
        w = AsyncConfigWatcher(stub, pb2, "t1", timeout=5.0, metadata=auth_meta)
        w.field("fee", float, default=0.0)

        async def empty_stream():
            return
            yield

        stub.Subscribe.return_value = empty_stream()

        await w.start()
        await asyncio.sleep(0.05)
        await w.stop()

        stub.GetConfig.assert_awaited_once()
        _, get_kwargs = stub.GetConfig.call_args
        assert get_kwargs.get("metadata") == auth_meta

        stub.Subscribe.assert_called_once()
        _, sub_kwargs = stub.Subscribe.call_args
        assert sub_kwargs.get("metadata") == auth_meta

    @pytest.mark.asyncio
    async def test_processes_stream_response(self):
        from opendecree._generated.centralconfig.v1 import types_pb2

        w = self._make_watcher()
        fee = w.field("fee", float, default=0.0)

        response = MagicMock()
        response.change.field_path = "fee"
        response.change.HasField.side_effect = lambda name: name in ("old_value", "new_value")
        response.change.old_value = types_pb2.TypedValue(string_value="0.0")
        response.change.new_value = types_pb2.TypedValue(string_value="1.5")
        response.change.version = 1
        response.change.changed_by = ""

        async def stream_with_one_response():
            yield response
            # Stream ends normally (server closed)

        w._stub.Subscribe = MagicMock(return_value=stream_with_one_response())

        await w.start()
        await asyncio.sleep(0.2)
        await w.stop()

        assert fee.value == pytest.approx(1.5)

    @pytest.mark.asyncio
    async def test_stream_loop_returns_when_stopped_during_iteration(self):
        from opendecree._generated.centralconfig.v1 import types_pb2

        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        response = MagicMock()
        response.change.field_path = "fee"
        response.change.HasField.side_effect = lambda name: name in ("old_value", "new_value")
        response.change.old_value = types_pb2.TypedValue(string_value="0.0")
        response.change.new_value = types_pb2.TypedValue(string_value="1.5")
        response.change.version = 1
        response.change.changed_by = ""

        async def stream_already_stopped():
            w._stopped = True  # mark stopped before the loop body runs
            yield response

        w._stub.Subscribe = MagicMock(return_value=stream_already_stopped())

        await w.start()
        await asyncio.sleep(0.2)

        assert w._task is not None
        assert w._task.done()
        await w.stop()

    @pytest.mark.asyncio
    async def test_stream_aiorpc_error_while_stopped_exits_cleanly(self):
        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        async def error_after_stop():
            w._stopped = True  # mark stopped before raising
            raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, "gone")
            yield  # makes it an async generator

        w._stub.Subscribe = MagicMock(return_value=error_after_stop())

        await w.start()
        await asyncio.sleep(0.2)

        # Task should have exited cleanly (stopped=True path)
        assert w._task is not None
        assert w._task.done()
        await w.stop()

    @pytest.mark.asyncio
    async def test_task_name_sanitizes_control_chars(self):
        stub = MagicMock()
        pb2 = MagicMock()
        mock_resp = MagicMock()
        mock_resp.config.values = []
        stub.GetConfig = AsyncMock(return_value=mock_resp)

        async def empty_stream():
            return
            yield

        stub.Subscribe.return_value = empty_stream()

        w = AsyncConfigWatcher(stub, pb2, "tenant\x00evil\x1f", timeout=5.0)
        await w.start()
        assert w._task is not None
        assert "\x00" not in w._task.get_name()
        assert "\x1f" not in w._task.get_name()
        assert "tenantevil" in w._task.get_name()
        await w.stop()
