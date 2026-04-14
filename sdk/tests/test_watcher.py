"""Tests for the sync ConfigWatcher."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import grpc
import pytest

from opendecree.watcher import _SENTINEL_CHANGE, ConfigWatcher, WatchedField
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

        from opendecree.types import Change

        c1 = Change(field_path="x", old_value="a", new_value="b", version=1)
        c2 = Change(field_path="x", old_value="b", new_value="c", version=2)

        # Put changes then sentinel.
        f._change_queue.put(c1)
        f._change_queue.put(c2)
        f._change_queue.put(_SENTINEL_CHANGE)

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
