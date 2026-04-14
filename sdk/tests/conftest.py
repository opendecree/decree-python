"""Shared test fixtures and helpers."""

from __future__ import annotations

import grpc
import grpc.aio


class FakeRpcError(grpc.aio.AioRpcError):
    """A concrete RpcError for testing.

    AioRpcError is a subclass of grpc.RpcError, so this works for both
    sync and async error handling.
    """

    def __init__(self, code: grpc.StatusCode, details: str = "test") -> None:
        # AioRpcError.__init__ expects (code, initial_metadata, trailing_metadata,
        # details, debug_error_string).
        super().__init__(code, None, None, details, None)  # type: ignore[arg-type]
