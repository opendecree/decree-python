"""gRPC channel factory with keepalive configuration."""

from __future__ import annotations

import grpc

# Default channel options for keepalive and reconnection.
_DEFAULT_OPTIONS: list[tuple[str, int]] = [
    ("grpc.keepalive_time_ms", 30000),
    ("grpc.keepalive_timeout_ms", 10000),
    ("grpc.keepalive_permit_without_calls", 1),
    ("grpc.initial_reconnect_backoff_ms", 1000),
    ("grpc.max_reconnect_backoff_ms", 30000),
]


def create_channel(
    target: str,
    *,
    insecure: bool = True,
    credentials: grpc.ChannelCredentials | None = None,
) -> grpc.Channel:
    """Create a gRPC channel with sensible defaults."""
    if credentials is not None:
        return grpc.secure_channel(target, credentials, options=_DEFAULT_OPTIONS)
    if insecure:
        return grpc.insecure_channel(target, options=_DEFAULT_OPTIONS)
    return grpc.secure_channel(target, grpc.ssl_channel_credentials(), options=_DEFAULT_OPTIONS)


def create_aio_channel(
    target: str,
    *,
    insecure: bool = True,
    credentials: grpc.ChannelCredentials | None = None,
) -> grpc.aio.Channel:
    """Create an async gRPC channel with sensible defaults."""
    if credentials is not None:
        return grpc.aio.secure_channel(target, credentials, options=_DEFAULT_OPTIONS)
    if insecure:
        return grpc.aio.insecure_channel(target, options=_DEFAULT_OPTIONS)
    return grpc.aio.secure_channel(target, grpc.ssl_channel_credentials(), options=_DEFAULT_OPTIONS)
