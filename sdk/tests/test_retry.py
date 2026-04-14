"""Tests for retry logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import grpc.aio
import pytest

from opendecree._retry import RetryConfig, async_with_retry, with_retry
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
