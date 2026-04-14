"""Asynchronous ConfigWatcher for live configuration subscriptions.

The async watcher subscribes to config changes via gRPC server-streaming
using asyncio. Registered fields are updated atomically and can be read
at any time via the .value property.

Usage::

    async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
        async with client.watch("tenant-id") as watcher:
            fee = watcher.field("payments.fee", float, default=0.01)
            if fee:
                print(f"Current fee: {fee.value}")

            async for change in fee.changes():
                print(f"{change.old_value} -> {change.new_value}")
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator, Callable
from typing import Any, Generic, TypeVar

import grpc.aio

from opendecree._convert import convert_value, typed_value_to_string
from opendecree._stubs import process_get_all_response
from opendecree.types import Change

logger = logging.getLogger("opendecree.async_watcher")

T = TypeVar("T")

# Default reconnect backoff parameters.
_RECONNECT_INITIAL = 1.0
_RECONNECT_MAX = 30.0
_RECONNECT_MULTIPLIER = 2.0


class AsyncWatchedField(Generic[T]):
    """A live, thread-safe configuration field with a typed value (async variant).

    Updated automatically by the watcher's asyncio task.
    """

    def __init__(self, path: str, type_: type[T], default: T) -> None:
        self._path = path
        self._type = type_
        self._default = default
        self._value: T = default
        self._is_set = False
        self._callbacks: list[Callable[[T, T], None]] = []
        self._change_queue: asyncio.Queue[Change | None] = asyncio.Queue()

    @property
    def path(self) -> str:
        """The field path this value tracks."""
        return self._path

    @property
    def value(self) -> T:
        """The current value — always fresh."""
        return self._value

    def __bool__(self) -> bool:
        """Truthy based on the current value. False for False, 0, '', None."""
        return bool(self._value)

    def __repr__(self) -> str:
        return f"AsyncWatchedField({self._path!r}, value={self._value!r})"

    def on_change(self, fn: Callable[[T, T], None]) -> Callable[[T, T], None]:
        """Register a callback for value changes. Can be used as a decorator.

        The callback receives (old_value, new_value) and is called from the
        watcher's asyncio task.
        """
        self._callbacks.append(fn)
        return fn

    async def changes(self) -> AsyncIterator[Change]:
        """Async iterator that yields Change events for this field.

        Yields Change objects until the watcher is stopped.
        """
        while True:
            change = await self._change_queue.get()
            if change is None:  # sentinel
                return
            yield change

    def _update(self, raw_value: str | None, change: Change) -> None:
        """Update the field value from a raw string. Called by the watcher task."""
        old = self._value
        if raw_value is not None:
            self._value = convert_value(raw_value, self._type)  # type: ignore[assignment]
            self._is_set = True
        else:
            self._value = self._default
            self._is_set = False

        new = self._value
        if old != new:
            for cb in self._callbacks:
                try:
                    cb(old, new)
                except Exception:
                    logger.exception("Error in on_change callback for %s", self._path)

        self._change_queue.put_nowait(change)

    def _load_initial(self, raw_value: str) -> None:
        """Set initial value from snapshot. No callbacks fired."""
        self._value = convert_value(raw_value, self._type)  # type: ignore[assignment]
        self._is_set = True

    def _stop(self) -> None:
        """Signal the changes() iterator to stop."""
        self._change_queue.put_nowait(None)


class AsyncConfigWatcher:
    """Watches a tenant's configuration for live changes (async variant).

    Created via async_client.watch(). Use as an async context manager —
    auto-starts on enter, auto-stops on exit.
    """

    def __init__(self, stub: Any, pb2: Any, tenant_id: str, timeout: float) -> None:
        self._stub = stub
        self._pb2 = pb2
        self._tenant_id = tenant_id
        self._timeout = timeout
        self._fields: dict[str, AsyncWatchedField] = {}  # type: ignore[type-arg]
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._stopped = False

    def field(self, path: str, type_: type[T], *, default: T) -> AsyncWatchedField[T]:
        """Register a field to watch.

        Must be called before the watcher is started (before __aenter__).

        Args:
            path: Dot-separated field path (e.g., "payments.fee").
            type_: Python type to convert values to (str, int, float, bool, timedelta).
            default: Default value when the field is null or not set.

        Returns:
            An AsyncWatchedField that tracks the live value.
        """
        if self._task is not None:
            raise RuntimeError("Cannot register fields after watcher has started")
        watched = AsyncWatchedField(path, type_, default)
        self._fields[path] = watched
        return watched

    async def start(self) -> None:
        """Start watching — loads initial snapshot and subscribes to changes."""
        if self._task is not None:
            raise RuntimeError("Watcher already started")

        await self._load_snapshot()
        self._stopped = False
        self._task = asyncio.create_task(
            self._subscribe_loop(), name=f"decree-watcher-{self._tenant_id}"
        )

    async def stop(self) -> None:
        """Stop watching and cancel the background task."""
        self._stopped = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        for f in self._fields.values():
            f._stop()

    async def __aenter__(self) -> AsyncConfigWatcher:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    async def _load_snapshot(self) -> None:
        """Load the current config values as the initial snapshot."""
        resp = await self._stub.GetConfig(
            self._pb2.GetConfigRequest(tenant_id=self._tenant_id),
            timeout=self._timeout,
        )
        all_values = process_get_all_response(resp)
        for path, watched in self._fields.items():
            if path in all_values:
                watched._load_initial(all_values[path])

    async def _subscribe_loop(self) -> None:
        """Background task: subscribe to changes with auto-reconnect."""
        backoff = _RECONNECT_INITIAL
        field_paths = list(self._fields.keys())

        while not self._stopped:
            try:
                stream = self._stub.Subscribe(
                    self._pb2.SubscribeRequest(
                        tenant_id=self._tenant_id,
                        field_paths=field_paths,
                    ),
                )
                backoff = _RECONNECT_INITIAL

                async for response in stream:
                    if self._stopped:
                        return
                    self._process_change(response.change)

                # Stream ended normally (server closed) — reconnect with backoff.
                if not self._stopped:
                    jitter = random.uniform(0.5, 1.5)
                    await asyncio.sleep(backoff * jitter)
                    backoff = min(backoff * _RECONNECT_MULTIPLIER, _RECONNECT_MAX)
                    continue

            except grpc.aio.AioRpcError as e:
                if self._stopped:
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
                    await asyncio.sleep(sleep_time)
                    backoff = min(backoff * _RECONNECT_MULTIPLIER, _RECONNECT_MAX)
                else:
                    logger.error("Subscription failed with non-retryable error: %s", e)
                    return
            except asyncio.CancelledError:
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
