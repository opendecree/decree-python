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
    """

    max_attempts: int = 3
    initial_backoff: float = 0.1  # seconds
    max_backoff: float = 5.0  # seconds
    multiplier: float = 2.0
    retryable_codes: tuple[grpc.StatusCode, ...] = field(
        default=(
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
        )
    )


def with_retry(config: RetryConfig | None, fn: Callable[[], T]) -> T:
    """Execute fn with retry on transient gRPC errors (sync)."""
    if config is None:
        return fn()

    last_err: Exception | None = None
    backoff = config.initial_backoff

    for attempt in range(config.max_attempts):
        try:
            return fn()
        except grpc.RpcError as e:
            code = e.code()
            if code not in config.retryable_codes or attempt == config.max_attempts - 1:
                raise
            last_err = e
            jitter = random.uniform(0.5, 1.5)
            time.sleep(backoff * jitter)
            backoff = min(backoff * config.multiplier, config.max_backoff)

    raise last_err  # type: ignore[misc]  # pragma: no cover


async def async_with_retry(config: RetryConfig | None, fn: Callable[[], Awaitable[T]]) -> T:
    """Execute fn with retry on transient gRPC errors (async)."""
    if config is None:
        return await fn()

    last_err: Exception | None = None
    backoff = config.initial_backoff

    for attempt in range(config.max_attempts):
        try:
            return await fn()
        except grpc.aio.AioRpcError as e:
            code = e.code()
            if code not in config.retryable_codes or attempt == config.max_attempts - 1:
                raise
            last_err = e
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(backoff * jitter)
            backoff = min(backoff * config.multiplier, config.max_backoff)

    raise last_err  # type: ignore[misc]  # pragma: no cover
