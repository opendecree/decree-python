"""gRPC channel factory with keepalive configuration."""

from __future__ import annotations

import grpc

_DEFAULT_KEEPALIVE_TIME_MS = 30000
_DEFAULT_KEEPALIVE_TIMEOUT_MS = 10000
_DEFAULT_KEEPALIVE_PERMIT_WITHOUT_CALLS = 1
_DEFAULT_RECONNECT_BACKOFF_INITIAL_MS = 1000
_DEFAULT_RECONNECT_BACKOFF_MAX_MS = 30000


def _build_options(
    max_send_message_length: int | None,
    max_recv_message_length: int | None,
    keepalive_time_ms: int,
    keepalive_timeout_ms: int,
    keepalive_permit_without_calls: int,
    reconnect_backoff_initial_ms: int,
    reconnect_backoff_max_ms: int,
) -> list[tuple[str, int]]:
    opts: list[tuple[str, int]] = [
        ("grpc.keepalive_time_ms", keepalive_time_ms),
        ("grpc.keepalive_timeout_ms", keepalive_timeout_ms),
        ("grpc.keepalive_permit_without_calls", keepalive_permit_without_calls),
        ("grpc.initial_reconnect_backoff_ms", reconnect_backoff_initial_ms),
        ("grpc.max_reconnect_backoff_ms", reconnect_backoff_max_ms),
    ]
    if max_send_message_length is not None:
        opts.append(("grpc.max_send_message_length", max_send_message_length))
    if max_recv_message_length is not None:
        opts.append(("grpc.max_receive_message_length", max_recv_message_length))
    return opts


def _token_call_credentials(token: str) -> grpc.CallCredentials:
    """Return gRPC call credentials that inject a Bearer token."""

    def _callback(context: object, callback: object) -> None:
        assert callable(callback)
        callback([("authorization", f"Bearer {token}")], None)

    return grpc.metadata_call_credentials(_callback)


def create_channel(
    target: str,
    *,
    insecure: bool = True,
    credentials: grpc.ChannelCredentials | None = None,
    token: str | None = None,
    max_send_message_length: int | None = None,
    max_recv_message_length: int | None = None,
    keepalive_time_ms: int = _DEFAULT_KEEPALIVE_TIME_MS,
    keepalive_timeout_ms: int = _DEFAULT_KEEPALIVE_TIMEOUT_MS,
    keepalive_permit_without_calls: int = _DEFAULT_KEEPALIVE_PERMIT_WITHOUT_CALLS,
    reconnect_backoff_initial_ms: int = _DEFAULT_RECONNECT_BACKOFF_INITIAL_MS,
    reconnect_backoff_max_ms: int = _DEFAULT_RECONNECT_BACKOFF_MAX_MS,
) -> grpc.Channel:
    """Create a gRPC channel with sensible defaults.

    When *token* is provided and TLS is active (``insecure=False`` or
    *credentials* is given), the token is embedded via
    ``composite_channel_credentials`` so it is protected by the TLS layer.
    On an insecure channel the token is sent as a raw header — callers should
    warn the user before allowing this.

    Pass *max_send_message_length* or *max_recv_message_length* (bytes) to
    override gRPC's 4 MB default, which can be too small for large JSON values.
    """
    options = _build_options(
        max_send_message_length,
        max_recv_message_length,
        keepalive_time_ms,
        keepalive_timeout_ms,
        keepalive_permit_without_calls,
        reconnect_backoff_initial_ms,
        reconnect_backoff_max_ms,
    )

    channel_creds: grpc.ChannelCredentials | None = credentials
    if channel_creds is None and not insecure:
        channel_creds = grpc.ssl_channel_credentials()

    if channel_creds is not None:
        if token:
            channel_creds = grpc.composite_channel_credentials(
                channel_creds, _token_call_credentials(token)
            )
        return grpc.secure_channel(target, channel_creds, options=options)

    return grpc.insecure_channel(target, options=options)


def create_aio_channel(
    target: str,
    *,
    insecure: bool = True,
    credentials: grpc.ChannelCredentials | None = None,
    token: str | None = None,
    max_send_message_length: int | None = None,
    max_recv_message_length: int | None = None,
    keepalive_time_ms: int = _DEFAULT_KEEPALIVE_TIME_MS,
    keepalive_timeout_ms: int = _DEFAULT_KEEPALIVE_TIMEOUT_MS,
    keepalive_permit_without_calls: int = _DEFAULT_KEEPALIVE_PERMIT_WITHOUT_CALLS,
    reconnect_backoff_initial_ms: int = _DEFAULT_RECONNECT_BACKOFF_INITIAL_MS,
    reconnect_backoff_max_ms: int = _DEFAULT_RECONNECT_BACKOFF_MAX_MS,
) -> grpc.aio.Channel:
    """Create an async gRPC channel with sensible defaults.

    When *token* is provided and TLS is active (``insecure=False`` or
    *credentials* is given), the token is embedded via
    ``composite_channel_credentials`` so it is protected by the TLS layer.
    On an insecure channel the token is sent as a raw header — callers should
    warn the user before allowing this.

    Pass *max_send_message_length* or *max_recv_message_length* (bytes) to
    override gRPC's 4 MB default, which can be too small for large JSON values.
    """
    options = _build_options(
        max_send_message_length,
        max_recv_message_length,
        keepalive_time_ms,
        keepalive_timeout_ms,
        keepalive_permit_without_calls,
        reconnect_backoff_initial_ms,
        reconnect_backoff_max_ms,
    )

    channel_creds: grpc.ChannelCredentials | None = credentials
    if channel_creds is None and not insecure:
        channel_creds = grpc.ssl_channel_credentials()

    if channel_creds is not None:
        if token:
            channel_creds = grpc.composite_channel_credentials(
                channel_creds, _token_call_credentials(token)
            )
        return grpc.aio.secure_channel(target, channel_creds, options=options)

    return grpc.aio.insecure_channel(target, options=options)
