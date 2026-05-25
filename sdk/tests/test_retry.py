"""Tests for retry logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import grpc.aio
import pytest

from opendecree._retry import RetryConfig, async_with_retry, with_retry, write_safe_config
from tests.conftest import FakeRpcError


def test_no_retry_config():
    """When config is None, just call the function once."""
    fn = MagicMock(return_value=42)
    assert with_retry(None, fn) == 42
    fn.assert_called_once()


def test_success_first_try():
    fn = MagicMock(return_value="ok")
    result = with_retry(RetryConfig(max_attempts=3), fn)
    assert result == "ok"
    fn.assert_called_once()


def test_retry_on_unavailable():
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    fn = MagicMock(side_effect=[err, err, "ok"])

    with patch("opendecree._retry.time.sleep"):
        result = with_retry(RetryConfig(max_attempts=3), fn)

    assert result == "ok"
    assert fn.call_count == 3


def test_no_retry_on_not_found():
    err = FakeRpcError(grpc.StatusCode.NOT_FOUND)
    fn = MagicMock(side_effect=err)

    with pytest.raises(grpc.RpcError):
        with_retry(RetryConfig(max_attempts=3), fn)

    fn.assert_called_once()


def test_exhausted_retries():
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    fn = MagicMock(side_effect=err)

    with patch("opendecree._retry.time.sleep"):
        with pytest.raises(grpc.RpcError):
            with_retry(RetryConfig(max_attempts=2), fn)

    assert fn.call_count == 2


def test_retry_config_defaults():
    cfg = RetryConfig()
    assert cfg.max_attempts == 3
    assert cfg.initial_backoff == 0.1
    assert cfg.max_backoff == 5.0
    assert cfg.multiplier == 2.0
    assert grpc.StatusCode.UNAVAILABLE in cfg.retryable_codes
    assert grpc.StatusCode.DEADLINE_EXCEEDED in cfg.retryable_codes
    assert grpc.StatusCode.RESOURCE_EXHAUSTED in cfg.retryable_codes


def test_retry_on_resource_exhausted():
    err = FakeRpcError(grpc.StatusCode.RESOURCE_EXHAUSTED)
    fn = MagicMock(side_effect=[err, "ok"])

    with patch("opendecree._retry.time.sleep"):
        result = with_retry(RetryConfig(max_attempts=3), fn)

    assert result == "ok"
    assert fn.call_count == 2


def test_write_safe_config_strips_deadline_exceeded():
    base = RetryConfig()
    safe = write_safe_config(base)
    assert safe is not None
    assert grpc.StatusCode.UNAVAILABLE in safe.retryable_codes
    assert grpc.StatusCode.DEADLINE_EXCEEDED not in safe.retryable_codes
    assert safe.max_attempts == base.max_attempts
    assert safe.initial_backoff == base.initial_backoff
    assert safe.max_backoff == base.max_backoff
    assert safe.multiplier == base.multiplier


def test_write_safe_config_none_passthrough():
    assert write_safe_config(None) is None


def test_write_safe_config_all_codes_removed_returns_none():
    cfg = RetryConfig(retryable_codes=(grpc.StatusCode.DEADLINE_EXCEEDED,))
    assert write_safe_config(cfg) is None


# --- Async retry ---


@pytest.mark.asyncio
async def test_async_no_retry_config():
    async def fn() -> int:
        return 42

    assert await async_with_retry(None, fn) == 42


@pytest.mark.asyncio
async def test_async_retry_on_unavailable():
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    call_count = 0

    async def fn() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise err
        return "ok"

    with patch("opendecree._retry.asyncio.sleep", new_callable=AsyncMock):
        result = await async_with_retry(RetryConfig(max_attempts=3), fn)

    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_async_no_retry_on_not_found():
    err = FakeRpcError(grpc.StatusCode.NOT_FOUND)

    async def fn() -> str:
        raise err

    with pytest.raises(grpc.aio.AioRpcError):
        await async_with_retry(RetryConfig(max_attempts=3), fn)


@pytest.mark.asyncio
async def test_async_exhausted_retries():
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)

    async def fn() -> str:
        raise err

    with patch("opendecree._retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(grpc.aio.AioRpcError):
            await async_with_retry(RetryConfig(max_attempts=2), fn)


# --- Deadline budget ---


def test_deadline_clips_sleep():
    """Sleep is clipped to remaining budget so total wall time stays bounded."""
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    fn = MagicMock(side_effect=[err, "ok"])
    slept: list[float] = []

    with patch("opendecree._retry.time.sleep", side_effect=lambda s: slept.append(s)):
        # monotonic: [deadline=0.0, loop-top-0=0.0, remaining=0.05, loop-top-1=0.05]
        with patch("opendecree._retry.time.monotonic", side_effect=[0.0, 0.0, 0.05, 0.05]):
            result = with_retry(RetryConfig(max_attempts=3, total_timeout=0.1), fn)

    assert result == "ok"
    assert slept[0] <= 0.05 + 1e-9  # clipped to remaining budget


def test_deadline_exhausted_raises_immediately():
    """When budget is gone after a failure, raises without sleeping."""
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    fn = MagicMock(side_effect=err)
    slept: list[float] = []

    with patch("opendecree._retry.time.sleep", side_effect=lambda s: slept.append(s)):
        # monotonic calls: [deadline_start=0.0, loop-top-0=0.0, remaining-check=0.2 (over budget)]
        with patch("opendecree._retry.time.monotonic", side_effect=[0.0, 0.0, 0.2]):
            with pytest.raises(grpc.RpcError):
                with_retry(RetryConfig(max_attempts=3, total_timeout=0.1), fn)

    assert slept == []


def test_deadline_already_passed_before_second_attempt():
    """Loop-top deadline check stops further attempts once budget is exhausted."""
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    fn = MagicMock(side_effect=[err, "ok"])

    with patch("opendecree._retry.time.sleep"):
        # monotonic: [deadline=0.0, loop-top-0=0.0, remaining=0.05 (ok), loop-top-1=0.2 (over)]
        with patch("opendecree._retry.time.monotonic", side_effect=[0.0, 0.0, 0.05, 0.2]):
            with pytest.raises(grpc.RpcError):
                with_retry(RetryConfig(max_attempts=3, total_timeout=0.1), fn)

    assert fn.call_count == 1


def test_write_safe_config_preserves_total_timeout():
    base = RetryConfig(total_timeout=30.0)
    safe = write_safe_config(base)
    assert safe is not None
    assert safe.total_timeout == 30.0


@pytest.mark.asyncio
async def test_async_deadline_exhausted_raises_immediately():
    err = FakeRpcError(grpc.StatusCode.UNAVAILABLE)
    slept: list[float] = []

    async def fn() -> str:
        raise err

    async def fake_sleep(s: float) -> None:
        slept.append(s)

    with patch("opendecree._retry.asyncio.sleep", side_effect=fake_sleep):
        # monotonic: [deadline_start=0.0, loop-top-0=0.0, remaining-check=0.2 (over budget)]
        with patch("opendecree._retry.time.monotonic", side_effect=[0.0, 0.0, 0.2]):
            with pytest.raises(grpc.aio.AioRpcError):
                await async_with_retry(RetryConfig(max_attempts=3, total_timeout=0.1), fn)

    assert slept == []
