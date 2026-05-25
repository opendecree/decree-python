"""Retry logic with exponential backoff and jitter.

Provides both sync (with_retry) and async (async_with_retry) variants.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

import grpc
import grpc.aio

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including the first).
        initial_backoff: Initial backoff duration in seconds.
        max_backoff: Maximum backoff duration in seconds.
        multiplier: Backoff multiplier between attempts.
        retryable_codes: gRPC status codes that trigger a retry.
        total_timeout: Overall wall-clock budget in seconds shared across all
            attempts. When set, backoff sleeps are clipped to the remaining
            budget and no further attempt is made once the budget is exhausted.
            None means no global limit (original behavior).
    """

    max_attempts: int = 3
    initial_backoff: float = 0.1  # seconds
    max_backoff: float = 5.0  # seconds
    multiplier: float = 2.0
    retryable_codes: tuple[grpc.StatusCode, ...] = field(
        default=(
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.RESOURCE_EXHAUSTED,
        )
    )
    total_timeout: float | None = None


def write_safe_config(base: RetryConfig | None) -> RetryConfig | None:
    """Return a retry config safe for non-idempotent writes.

    Strips DEADLINE_EXCEEDED from retryable codes — a timeout does not guarantee
    the server hasn't already applied the write, so retrying risks double-apply.
    Returns None when base is None (retry disabled).
    """
    if base is None:
        return None
    safe_codes = tuple(c for c in base.retryable_codes if c != grpc.StatusCode.DEADLINE_EXCEEDED)
    if not safe_codes:
        return None
    return RetryConfig(
        max_attempts=base.max_attempts,
        initial_backoff=base.initial_backoff,
        max_backoff=base.max_backoff,
        multiplier=base.multiplier,
        retryable_codes=safe_codes,
        total_timeout=base.total_timeout,
    )


def with_retry(config: RetryConfig | None, fn: Callable[[], T]) -> T:
    """Execute fn with retry on transient gRPC errors (sync)."""
    if config is None:
        return fn()

    deadline = time.monotonic() + config.total_timeout if config.total_timeout is not None else None
    last_err: Exception | None = None
    backoff = config.initial_backoff

    for attempt in range(config.max_attempts):
        if deadline is not None and time.monotonic() >= deadline:
            break
        try:
            return fn()
        except grpc.RpcError as e:
            code = e.code()
            if code not in config.retryable_codes or attempt == config.max_attempts - 1:
                raise
            last_err = e
            jitter = random.uniform(0.5, 1.5)
            sleep_time = backoff * jitter
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                sleep_time = min(sleep_time, remaining)
            time.sleep(sleep_time)
            backoff = min(backoff * config.multiplier, config.max_backoff)

    raise last_err  # type: ignore[misc]  # pragma: no cover


async def async_with_retry(config: RetryConfig | None, fn: Callable[[], Awaitable[T]]) -> T:
    """Execute fn with retry on transient gRPC errors (async)."""
    if config is None:
        return await fn()

    deadline = time.monotonic() + config.total_timeout if config.total_timeout is not None else None
    last_err: Exception | None = None
    backoff = config.initial_backoff

    for attempt in range(config.max_attempts):
        if deadline is not None and time.monotonic() >= deadline:
            break
        try:
            return await fn()
        except grpc.aio.AioRpcError as e:
            code = e.code()
            if code not in config.retryable_codes or attempt == config.max_attempts - 1:
                raise
            last_err = e
            jitter = random.uniform(0.5, 1.5)
            sleep_time = backoff * jitter
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                sleep_time = min(sleep_time, remaining)
            await asyncio.sleep(sleep_time)
            backoff = min(backoff * config.multiplier, config.max_backoff)

    raise last_err  # type: ignore[misc]  # pragma: no cover
