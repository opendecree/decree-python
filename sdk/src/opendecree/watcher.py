"""Synchronous ConfigWatcher for live configuration subscriptions.

The watcher runs a background thread that subscribes to config changes via
gRPC server-streaming. Registered fields are updated atomically and can be
read at any time via the .value property.

Usage::

    with ConfigClient("localhost:9090", subject="myapp") as client:
        with client.watch("tenant-id") as watcher:
            fee = watcher.field("payments.fee", float, default=0.01)
            if fee:
                print(f"Current fee: {fee.value}")
"""

from __future__ import annotations

import logging
import queue
import random
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any, Generic, TypeVar

import grpc

from opendecree._convert import convert_value, typed_value_to_string
from opendecree._stubs import process_get_all_response
from opendecree.types import Change

logger = logging.getLogger("opendecree.watcher")

T = TypeVar("T")

# Default reconnect backoff parameters.
_RECONNECT_INITIAL = 1.0
_RECONNECT_MAX = 30.0
_RECONNECT_MULTIPLIER = 2.0


class WatchedField(Generic[T]):
    """A live, thread-safe configuration field with a typed value.

    Attributes are updated automatically by the watcher's background thread.
    """

    def __init__(self, path: str, type_: type[T], default: T) -> None:
        self._path = path
        self._type = type_
        self._default = default
        self._value: T = default
        self._is_set = False
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[T, T], None]] = []
        self._change_queue: queue.Queue[Change] = queue.Queue()

    @property
    def path(self) -> str:
        """The field path this value tracks."""
        return self._path

    @property
    def value(self) -> T:
        """The current value — always fresh, thread-safe."""
        with self._lock:
            return self._value

    def __bool__(self) -> bool:
        """Truthy based on the current value. False for False, 0, '', None."""
        return bool(self.value)

    def __repr__(self) -> str:
        return f"WatchedField({self._path!r}, value={self.value!r})"

    def on_change(self, fn: Callable[[T, T], None]) -> Callable[[T, T], None]:
        """Register a callback for value changes. Can be used as a decorator.

        The callback receives (old_value, new_value) and is called from the
        watcher's background thread.
        """
        self._callbacks.append(fn)
        return fn

    def changes(self) -> Iterator[Change]:
        """Blocking iterator that yields Change events for this field.

        Blocks until a change arrives or the watcher is stopped.
        Yields Change objects with old_value and new_value as strings.
        """
        while True:
            try:
                change = self._change_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if change is _SENTINEL_CHANGE:
                return
            yield change

    def _update(self, raw_value: str | None, change: Change) -> None:
        """Update the field value from a raw string. Called by the watcher thread."""
        with self._lock:
            old = self._value
            if raw_value is not None:
                self._value = convert_value(raw_value, self._type)  # type: ignore[assignment]
                self._is_set = True
            else:
                self._value = self._default
                self._is_set = False

        # Notify callbacks (outside the lock to avoid deadlocks).
        new = self._value
        if old != new:
            for cb in self._callbacks:
                try:
                    cb(old, new)
                except Exception:
                    logger.exception("Error in on_change callback for %s", self._path)

        self._change_queue.put(change)

    def _load_initial(self, raw_value: str) -> None:
        """Set initial value from snapshot. No callbacks fired."""
        with self._lock:
            self._value = convert_value(raw_value, self._type)  # type: ignore[assignment]
            self._is_set = True

    def _stop(self) -> None:
        """Signal the changes() iterator to stop."""
        self._change_queue.put(_SENTINEL_CHANGE)


# Sentinel to signal the changes() iterator to stop.
_SENTINEL_CHANGE = Change(field_path="", old_value=None, new_value=None, version=-1)


class ConfigWatcher:
    """Watches a tenant's configuration for live changes.

    Created via client.watch(). Use as a context manager — auto-starts on
    enter, auto-stops on exit.
    """

    def __init__(self, stub: Any, pb2: Any, tenant_id: str, timeout: float) -> None:
        self._stub = stub
        self._pb2 = pb2
        self._tenant_id = tenant_id
        self._timeout = timeout
        self._fields: dict[str, WatchedField] = {}  # type: ignore[type-arg]
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def field(self, path: str, type_: type[T], *, default: T) -> WatchedField[T]:
        """Register a field to watch.

        Must be called before the watcher is started (before __enter__).

        Args:
            path: Dot-separated field path (e.g., "payments.fee").
            type_: Python type to convert values to (str, int, float, bool, timedelta).
            default: Default value when the field is null or not set.

        Returns:
            A WatchedField that tracks the live value.
        """
        if self._thread is not None:
            raise RuntimeError("Cannot register fields after watcher has started")
        watched = WatchedField(path, type_, default)
        self._fields[path] = watched
        return watched

    def start(self) -> None:
        """Start watching — loads initial snapshot and subscribes to changes."""
        if self._thread is not None:
            raise RuntimeError("Watcher already started")

        self._load_snapshot()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._subscribe_loop, daemon=True, name=f"decree-watcher-{self._tenant_id}"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop watching and clean up the background thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        for f in self._fields.values():
            f._stop()

    def __enter__(self) -> ConfigWatcher:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def _load_snapshot(self) -> None:
        """Load the current config values as the initial snapshot."""
        resp = self._stub.GetConfig(
            self._pb2.GetConfigRequest(tenant_id=self._tenant_id),
            timeout=self._timeout,
        )
        all_values = process_get_all_response(resp)
        for path, watched in self._fields.items():
            if path in all_values:
                watched._load_initial(all_values[path])

    def _subscribe_loop(self) -> None:
        """Background thread: subscribe to changes with auto-reconnect."""
        backoff = _RECONNECT_INITIAL
        field_paths = list(self._fields.keys())

        while not self._stop_event.is_set():
            try:
                stream = self._stub.Subscribe(
                    self._pb2.SubscribeRequest(
                        tenant_id=self._tenant_id,
                        field_paths=field_paths,
                    ),
                )
                backoff = _RECONNECT_INITIAL  # reset on successful connect

                for response in stream:
                    if self._stop_event.is_set():
                        return
                    self._process_change(response.change)

            except grpc.RpcError as e:
                if self._stop_event.is_set():
                    return
                code = e.code()
                if code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.INTERNAL):
                    jitter = random.uniform(0.5, 1.5)
                    sleep_time = backoff * jitter
                    logger.warning(
                        "Subscription lost (code=%s), reconnecting in %.1fs",
                        code,
                        sleep_time,
                    )
                    # Sleep in small intervals so we can check stop_event.
                    deadline = time.monotonic() + sleep_time
                    while time.monotonic() < deadline and not self._stop_event.is_set():
                        time.sleep(0.1)
                    backoff = min(backoff * _RECONNECT_MULTIPLIER, _RECONNECT_MAX)
                else:
                    logger.error("Subscription failed with non-retryable error: %s", e)
                    return

    def _process_change(self, change: Any) -> None:
        """Process a single ConfigChange from the stream."""
        field_path = change.field_path
        watched = self._fields.get(field_path)
        if watched is None:
            return

        old_raw = typed_value_to_string(change.old_value) if change.HasField("old_value") else None
        new_raw = typed_value_to_string(change.new_value) if change.HasField("new_value") else None

        sdk_change = Change(
            field_path=field_path,
            old_value=old_raw,
            new_value=new_raw,
            version=change.version,
            changed_by=change.changed_by,
        )
        watched._update(new_raw, sdk_change)
