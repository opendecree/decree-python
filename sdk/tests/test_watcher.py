"""Tests for the sync ConfigWatcher."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import grpc
import pytest

from opendecree.watcher import ConfigWatcher, WatchedField
from tests.conftest import FakeRpcError

# --- WatchedField unit tests ---


class TestWatchedField:
    def test_default_value(self):
        f = WatchedField("x", float, 0.01)
        assert f.value == 0.01
        assert f.path == "x"

    def test_load_initial(self):
        f = WatchedField("x", int, 0)
        f._load_initial("42")
        assert f.value == 42

    def test_bool_truthy(self):
        f = WatchedField("x", bool, False)
        assert not f
        f._load_initial("true")
        assert f

    def test_bool_falsy_zero(self):
        f = WatchedField("x", int, 0)
        assert not f

    def test_bool_falsy_empty_string(self):
        f = WatchedField("x", str, "")
        assert not f

    def test_update_fires_callback(self):
        f = WatchedField("x", float, 0.0)
        f._load_initial("1.0")
        results = []

        @f.on_change
        def cb(old: float, new: float) -> None:
            results.append((old, new))

        from opendecree.types import Change

        change = Change(field_path="x", old_value="1.0", new_value="2.0", version=1)
        f._update("2.0", change)

        assert results == [(1.0, 2.0)]
        assert f.value == 2.0

    def test_update_no_callback_if_same_value(self):
        f = WatchedField("x", str, "")
        f._load_initial("hello")
        results = []

        @f.on_change
        def cb(old: str, new: str) -> None:
            results.append((old, new))

        from opendecree.types import Change

        change = Change(field_path="x", old_value="hello", new_value="hello", version=1)
        f._update("hello", change)

        assert results == []  # no callback since value didn't change

    def test_update_null_resets_to_default(self):
        f = WatchedField("x", float, 0.01)
        f._load_initial("5.0")

        from opendecree.types import Change

        change = Change(field_path="x", old_value="5.0", new_value=None, version=1)
        f._update(None, change)

        assert f.value == 0.01

    def test_changes_iterator(self):
        f = WatchedField("x", str, "")
        f._load_initial("a")

        from opendecree.types import Change

        c1 = Change(field_path="x", old_value="a", new_value="b", version=1)
        c2 = Change(field_path="x", old_value="b", new_value="c", version=2)

        # Put changes then sentinel via the public internal helpers.
        f._update("b", c1)
        f._update("c", c2)
        f._stop()

        collected = list(f.changes())
        assert len(collected) == 2
        assert collected[0].new_value == "b"
        assert collected[1].new_value == "c"

    def test_repr(self):
        f = WatchedField("payments.fee", float, 0.01)
        assert "payments.fee" in repr(f)
        assert "0.01" in repr(f)

    def test_callback_exception_is_logged(self):
        f = WatchedField("x", int, 0)
        f._load_initial("1")

        @f.on_change
        def bad_cb(old: int, new: int) -> None:
            raise ValueError("boom")

        from opendecree.types import Change

        change = Change(field_path="x", old_value="1", new_value="2", version=1)
        # Should not raise — exception is logged.
        f._update("2", change)
        assert f.value == 2

    def test_on_callback_error_hook_is_called(self):
        errors: list[Exception] = []
        f = WatchedField("x", int, 0, on_callback_error=errors.append)
        f._load_initial("1")

        @f.on_change
        def bad_cb(old: int, new: int) -> None:
            raise ValueError("boom")

        from opendecree.types import Change

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
        stub.GetConfig.return_value = mock_resp

        w = ConfigWatcher(stub, pb2, "t1", timeout=5.0)
        f = w.field("x", int, default=0, on_callback_error=errors.append)
        f._load_initial("1")

        @f.on_change
        def bad_cb(old: int, new: int) -> None:
            raise RuntimeError("fail")

        from opendecree.types import Change

        change = Change(field_path="x", old_value="1", new_value="2", version=1)
        f._update("2", change)

        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)

    # --- Bounded queue tests ---

    def test_dropped_changes_starts_at_zero(self):
        f = WatchedField("x", str, "", max_queue_size=5)
        assert f.dropped_changes == 0

    def test_queue_fills_without_dropping_below_limit(self):
        from opendecree.types import Change

        f = WatchedField("x", str, "", max_queue_size=3)
        for i in range(3):
            c = Change(field_path="x", old_value=str(i), new_value=str(i + 1), version=i)
            f._update(str(i + 1), c)

        assert f.dropped_changes == 0
        assert len(f._change_queue) == 3

    def test_oldest_entry_dropped_when_queue_full(self):
        from opendecree.types import Change

        f = WatchedField("x", str, "", max_queue_size=3)
        changes = [
            Change(field_path="x", old_value=str(i), new_value=str(i + 1), version=i)
            for i in range(5)
        ]
        for i, c in enumerate(changes):
            f._update(str(i + 1), c)

        # Two oldest entries were dropped.
        assert f.dropped_changes == 2
        # Queue still holds exactly max_queue_size entries (the newest 3).
        assert len(f._change_queue) == 3
        versions = [c.version for c in f._change_queue]
        assert versions == [2, 3, 4]

    def test_drop_logs_warning(self, caplog):
        import logging

        from opendecree.types import Change

        f = WatchedField("payments.fee", str, "", max_queue_size=2)
        with caplog.at_level(logging.WARNING, logger="opendecree.watcher"):
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
        f = WatchedField("x", str, "", max_queue_size=10)
        assert f._max_queue_size == 10

    def test_default_max_queue_size(self):
        from opendecree.watcher import _DEFAULT_MAX_QUEUE_SIZE

        f = WatchedField("x", str, "")
        assert f._max_queue_size == _DEFAULT_MAX_QUEUE_SIZE
        assert _DEFAULT_MAX_QUEUE_SIZE == 1024

    def test_changes_blocks_until_change_arrives(self):
        import threading

        f = WatchedField("x", str, "")
        f._load_initial("a")

        results: list = []
        done = threading.Event()

        def consume():
            for c in f.changes():
                results.append(c)
                break
            done.set()

        t = threading.Thread(target=consume, daemon=True)
        t.start()

        time.sleep(0.05)  # let thread enter the wait

        from opendecree.types import Change

        change = Change(field_path="x", old_value="a", new_value="b", version=1)
        f._update("b", change)
        f._stop()

        done.wait(timeout=2.0)
        t.join(timeout=2.0)

        assert len(results) == 1
        assert results[0].new_value == "b"

    def test_changes_iterator_after_overflow(self):
        from opendecree.types import Change

        f = WatchedField("x", str, "", max_queue_size=2)
        for i in range(4):
            c = Change(field_path="x", old_value=str(i), new_value=str(i + 1), version=i)
            f._update(str(i + 1), c)
        f._stop()

        collected = list(f.changes())
        # Only the 2 newest changes survive.
        assert len(collected) == 2
        assert collected[0].version == 2
        assert collected[1].version == 3


# --- ConfigWatcher unit tests ---


class TestConfigWatcher:
    def _make_watcher(self) -> ConfigWatcher:
        """Create a watcher with mocked gRPC internals."""
        stub = MagicMock()
        pb2 = MagicMock()

        # Mock GetConfig to return empty config.
        mock_config_resp = MagicMock()
        mock_config_resp.config.values = []
        stub.GetConfig.return_value = mock_config_resp

        return ConfigWatcher(stub, pb2, "t1", timeout=5.0)

    def test_register_field(self):
        w = self._make_watcher()
        f = w.field("payments.fee", float, default=0.01)
        assert isinstance(f, WatchedField)
        assert f.value == 0.01

    def test_cannot_register_after_start(self):
        w = self._make_watcher()
        # Mock Subscribe to return an empty iterator.
        w._stub.Subscribe.return_value = iter([])

        w.start()
        with pytest.raises(RuntimeError, match="Cannot register"):
            w.field("x", str, default="")
        w.stop()

    def test_double_start_raises(self):
        w = self._make_watcher()
        w._stub.Subscribe.return_value = iter([])
        w.start()
        with pytest.raises(RuntimeError, match="already started"):
            w.start()
        w.stop()

    def test_snapshot_loads_initial_values(self):
        stub = MagicMock()
        pb2 = MagicMock()

        from opendecree._generated.centralconfig.v1 import types_pb2

        cv = MagicMock()
        cv.field_path = "rate"
        cv.HasField.return_value = True
        cv.value = types_pb2.TypedValue(string_value="42")

        mock_resp = MagicMock()
        mock_resp.config.values = [cv]
        stub.GetConfig.return_value = mock_resp

        w = ConfigWatcher(stub, pb2, "t1", timeout=5.0)
        rate = w.field("rate", int, default=0)

        # Mock Subscribe to return empty so the thread exits.
        stub.Subscribe.return_value = iter([])
        w.start()
        time.sleep(0.1)
        w.stop()

        assert rate.value == 42

    def test_context_manager(self):
        w = self._make_watcher()
        w._stub.Subscribe.return_value = iter([])

        w.field("fee", float, default=0.0)

        with w:
            assert w._thread is not None

        # Thread should be stopped after exit.
        assert w._thread is None

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

        # Should not raise.
        w._process_change(change)

    def test_reconnect_on_unavailable(self):
        """Subscribe raises UNAVAILABLE, watcher reconnects then stops."""
        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        call_count = 0

        def _subscribe_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, "connection lost")
            # Second call: return empty iterator so thread exits.
            return iter([])

        w._stub.Subscribe.side_effect = _subscribe_side_effect

        w.start()
        time.sleep(2.5)  # enough for one reconnect cycle
        w.stop()

        assert call_count >= 2

    def test_non_retryable_error_stops_loop(self):
        """Non-retryable gRPC error stops the subscribe loop."""
        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        w._stub.Subscribe.side_effect = FakeRpcError(grpc.StatusCode.PERMISSION_DENIED, "forbidden")

        w.start()
        time.sleep(0.5)
        w.stop()

        # Thread should have exited on its own due to non-retryable error.
        assert w._thread is None

    def test_reconnects_after_clean_stream_close(self):
        """Clean server-side stream close triggers a reconnect."""
        import unittest.mock as mock

        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        call_count = 0

        def _subscribe_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return iter([])  # clean close — server FIN
            # Stop after the second call so the thread exits.
            w._stop_event.set()
            return iter([])

        w._stub.Subscribe.side_effect = _subscribe_side_effect

        with mock.patch("opendecree.watcher._RECONNECT_INITIAL", 0.2):
            w.start()
            time.sleep(1.0)
            w.stop()

        assert call_count >= 2

    def test_clean_close_applies_backoff(self):
        """Reconnect after a clean close is delayed, not immediate."""
        import unittest.mock as mock

        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        call_count = 0
        timestamps: list[float] = []

        def _subscribe_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            timestamps.append(time.monotonic())
            if call_count == 1:
                return iter([])  # clean close
            w._stop_event.set()
            return iter([])

        w._stub.Subscribe.side_effect = _subscribe_side_effect

        with mock.patch("opendecree.watcher._RECONNECT_INITIAL", 0.2):
            w.start()
            time.sleep(1.0)
            w.stop()

        assert len(timestamps) >= 2
        gap = timestamps[1] - timestamps[0]
        # Minimum gap is jitter_min (0.5) * RECONNECT_INITIAL (0.2) = 0.1s.
        assert gap >= 0.05

    def test_stop_cancels_stream_and_joins_thread(self):
        """stop() cancels the gRPC stream so the background thread exits cleanly."""
        import threading

        w = self._make_watcher()
        w.field("fee", float, default=0.0)

        # A blocking iterator that only unblocks when cancel() is called.
        cancelled = threading.Event()

        class _BlockingIter:
            def __iter__(self):
                return self

            def __next__(self):
                # Block until cancelled.
                cancelled.wait(timeout=10.0)
                raise StopIteration

            def cancel(self):
                cancelled.set()

        blocking_stream = _BlockingIter()
        w._stub.Subscribe.return_value = blocking_stream

        w.start()
        time.sleep(0.1)  # let the thread reach the blocking iterator

        thread_ref = w._thread
        assert thread_ref is not None
        assert thread_ref.is_alive()

        w.stop()

        # Thread must have joined within the timeout.
        assert not thread_ref.is_alive()
        assert w._thread is None

    def test_thread_name_sanitizes_control_chars(self):
        stub = MagicMock()
        pb2 = MagicMock()
        mock_resp = MagicMock()
        mock_resp.config.values = []
        stub.GetConfig.return_value = mock_resp
        stub.Subscribe.return_value = iter([])

        w = ConfigWatcher(stub, pb2, "tenant\x00evil\x1f", timeout=5.0)
        w.start()
        assert w._thread is not None
        assert "\x00" not in w._thread.name
        assert "\x1f" not in w._thread.name
        assert "tenantevil" in w._thread.name
        w.stop()

    def test_processes_stream_response(self):
        from opendecree._generated.centralconfig.v1 import types_pb2

        stub = MagicMock()
        pb2 = MagicMock()
        mock_config_resp = MagicMock()
        mock_config_resp.config.values = []
        stub.GetConfig.return_value = mock_config_resp

        w = ConfigWatcher(stub, pb2, "t1", timeout=5.0)
        fee = w.field("fee", float, default=0.0)

        response = MagicMock()
        response.change.field_path = "fee"
        response.change.HasField.side_effect = lambda name: name in ("old_value", "new_value")
        response.change.old_value = types_pb2.TypedValue(string_value="0.0")
        response.change.new_value = types_pb2.TypedValue(string_value="1.5")
        response.change.version = 1
        response.change.changed_by = ""

        stub.Subscribe.return_value = iter([response])

        w.start()
        time.sleep(0.2)
        w.stop()

        assert fee.value == pytest.approx(1.5)

    def test_stream_loop_returns_when_stopped_during_iteration(self):
        stub = MagicMock()
        pb2 = MagicMock()
        mock_config_resp = MagicMock()
        mock_config_resp.config.values = []
        stub.GetConfig.return_value = mock_config_resp

        w = ConfigWatcher(stub, pb2, "t1", timeout=5.0)
        w.field("fee", float, default=0.0)

        class StopThenYieldStream:
            def __iter__(self):
                return self

            def __next__(self):
                w._stop_event.set()  # mark stopped before the loop body runs
                response = MagicMock()
                response.change.field_path = "fee"
                response.change.HasField.side_effect = lambda name: (
                    name
                    in (
                        "old_value",
                        "new_value",
                    )
                )
                from opendecree._generated.centralconfig.v1 import types_pb2

                response.change.old_value = types_pb2.TypedValue(string_value="0.0")
                response.change.new_value = types_pb2.TypedValue(string_value="1.5")
                response.change.version = 1
                response.change.changed_by = ""
                return response

            def cancel(self):
                pass

        stub.Subscribe.return_value = StopThenYieldStream()

        w.start()
        time.sleep(0.2)
        w.stop()

        # Thread exited via early return on line 248
        assert w._thread is None

    def test_stream_rpc_error_while_stopped_exits_cleanly(self):
        stub = MagicMock()
        pb2 = MagicMock()
        mock_config_resp = MagicMock()
        mock_config_resp.config.values = []
        stub.GetConfig.return_value = mock_config_resp

        w = ConfigWatcher(stub, pb2, "t1", timeout=5.0)
        w.field("fee", float, default=0.0)

        class ErrorStream:
            def __iter__(self):
                return self

            def __next__(self):
                w._stop_event.set()  # mark stopped before raising
                raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, "gone")

            def cancel(self):
                pass

        stub.Subscribe.return_value = ErrorStream()

        w.start()
        time.sleep(0.2)
        w.stop()

        # Thread should have exited on line 265 return path
        assert w._thread is None
