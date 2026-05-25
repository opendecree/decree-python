"""Shared base class for WatchedField and AsyncWatchedField."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Generic, TypeVar

from opendecree._convert import convert_value

T = TypeVar("T")

_logger = logging.getLogger("opendecree.watcher")

_RECONNECT_INITIAL = 1.0
_RECONNECT_MAX = 30.0
_RECONNECT_MULTIPLIER = 2.0
_DEFAULT_CHANGE_QUEUE_SIZE = 1024


def _validate_max_queue_size(max_queue_size: int) -> int:
    """Validate a positive change queue size."""
    if max_queue_size <= 0:
        raise ValueError("max_queue_size must be greater than 0")
    return max_queue_size


class _WatchedFieldBase(Generic[T]):
    """Common state and helpers shared by WatchedField and AsyncWatchedField."""

    def __init__(
        self,
        path: str,
        type_: type[T],
        default: T,
        *,
        on_callback_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._path = path
        self._type = type_
        self._default = default
        self._value: T = default
        self._is_set = False
        self._callbacks: list[Callable[[T, T], None]] = []
        self._on_callback_error = on_callback_error
        self._dropped_changes = 0

    @property
    def path(self) -> str:
        """The field path this value tracks."""
        return self._path

    @property
    def dropped_changes(self) -> int:
        """Number of queued changes dropped because the change queue was full."""
        return self._dropped_changes

    def on_change(self, fn: Callable[[T, T], None]) -> Callable[[T, T], None]:
        """Register a callback for value changes. Can be used as a decorator.

        The callback receives (old_value, new_value).
        """
        self._callbacks.append(fn)
        return fn

    def __bool__(self) -> bool:
        """Truthy based on the current value. False for False, 0, '', None."""
        return bool(self._value)

    def _apply_raw(self, raw_value: str | None) -> tuple[T, T]:
        """Set _value/_is_set from a raw string. Returns (old, new). Caller must lock if needed."""
        old = self._value
        if raw_value is not None:
            self._value = convert_value(raw_value, self._type)  # type: ignore[assignment]
            self._is_set = True
        else:
            self._value = self._default
            self._is_set = False
        return old, self._value

    def _fire_callbacks(self, old: T, new: T) -> None:
        """Invoke registered callbacks when the value changes."""
        if old != new:
            for cb in self._callbacks:
                try:
                    cb(old, new)
                except Exception as exc:
                    if self._on_callback_error is not None:
                        self._on_callback_error(exc)
                    else:
                        _logger.exception("Error in on_change callback for %s", self._path)
