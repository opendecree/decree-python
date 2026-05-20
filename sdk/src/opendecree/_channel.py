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


def _token_call_credentials(token: str) -> grpc.CallCredentials:
    """Return gRPC call credentials that inject a Bearer token."""

    def _callback(context: object, callback: object) -> None:  # type: ignore[type-arg]
        assert callable(callback)
        callback([("authorization", f"Bearer {token}")], None)

    return grpc.metadata_call_credentials(_callback)


def create_channel(
    target: str,
    *,
    insecure: bool = True,
    credentials: grpc.ChannelCredentials | None = None,
    token: str | None = None,
) -> grpc.Channel:
    """Create a gRPC channel with sensible defaults.

    When *token* is provided and TLS is active (``insecure=False`` or
    *credentials* is given), the token is embedded via
    ``composite_channel_credentials`` so it is protected by the TLS layer.
    On an insecure channel the token is sent as a raw header — callers should
    warn the user before allowing this.
    """
    channel_creds: grpc.ChannelCredentials | None = credentials
    if channel_creds is None and not insecure:
        channel_creds = grpc.ssl_channel_credentials()

    if channel_creds is not None:
        if token:
            channel_creds = grpc.composite_channel_credentials(
                channel_creds, _token_call_credentials(token)
            )
        return grpc.secure_channel(target, channel_creds, options=_DEFAULT_OPTIONS)

    return grpc.insecure_channel(target, options=_DEFAULT_OPTIONS)


def create_aio_channel(
    target: str,
    *,
    insecure: bool = True,
    credentials: grpc.ChannelCredentials | None = None,
    token: str | None = None,
) -> grpc.aio.Channel:
    """Create an async gRPC channel with sensible defaults.

    When *token* is provided and TLS is active (``insecure=False`` or
    *credentials* is given), the token is embedded via
    ``composite_channel_credentials`` so it is protected by the TLS layer.
    On an insecure channel the token is sent as a raw header — callers should
    warn the user before allowing this.
    """
    channel_creds: grpc.ChannelCredentials | None = credentials
    if channel_creds is None and not insecure:
        channel_creds = grpc.ssl_channel_credentials()

    if channel_creds is not None:
        if token:
            channel_creds = grpc.composite_channel_credentials(
                channel_creds, _token_call_credentials(token)
            )
        return grpc.aio.secure_channel(target, channel_creds, options=_DEFAULT_OPTIONS)

    return grpc.aio.insecure_channel(target, options=_DEFAULT_OPTIONS)
