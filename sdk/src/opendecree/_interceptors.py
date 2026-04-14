"""gRPC metadata interceptors for authentication.

The sync client uses AuthInterceptor to inject metadata via intercept_channel.
The async client injects metadata directly on each call since grpc.aio does
not support intercept_channel.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import grpc


def _build_metadata(
    *,
    subject: str | None,
    role: str,
    tenant_id: str | None,
    token: str | None,
) -> list[tuple[str, str]]:
    """Build auth metadata pairs from client options.

    If a Bearer token is provided, it takes precedence over metadata headers.
    Otherwise, x-subject, x-role, and x-tenant-id headers are set.
    """
    if token:
        return [("authorization", f"Bearer {token}")]
    pairs: list[tuple[str, str]] = []
    if subject:
        pairs.append(("x-subject", subject))
    if role:
        pairs.append(("x-role", role))
    if tenant_id:
        pairs.append(("x-tenant-id", tenant_id))
    return pairs


class AuthInterceptor(
    grpc.UnaryUnaryClientInterceptor,  # type: ignore[misc]
    grpc.UnaryStreamClientInterceptor,  # type: ignore[misc]
):
    """Sync interceptor that injects auth metadata into every call.

    Used by ConfigClient via grpc.intercept_channel().
    """

    def __init__(self, metadata: list[tuple[str, str]]) -> None:
        self._metadata = metadata

    def intercept_unary_unary(
        self,
        continuation: Callable[..., Any],
        client_call_details: grpc.ClientCallDetails,
        request: Any,
    ) -> Any:
        new_details = _inject_metadata(client_call_details, self._metadata)
        return continuation(new_details, request)

    def intercept_unary_stream(
        self,
        continuation: Callable[..., Any],
        client_call_details: grpc.ClientCallDetails,
        request: Any,
    ) -> Any:
        new_details = _inject_metadata(client_call_details, self._metadata)
        return continuation(new_details, request)


def _inject_metadata(
    details: grpc.ClientCallDetails,
    extra: list[tuple[str, str]],
) -> grpc.ClientCallDetails:
    """Return a new ClientCallDetails with extra metadata appended."""
    metadata: list[tuple[str, str]] = list(details.metadata or [])
    metadata.extend(extra)
    return _ClientCallDetails(
        method=details.method,
        timeout=details.timeout,
        metadata=metadata,
        credentials=details.credentials,
    )


class _ClientCallDetails(grpc.ClientCallDetails):  # type: ignore[misc]
    """Concrete implementation of ClientCallDetails for sync interceptors."""

    def __init__(
        self,
        method: str,
        timeout: float | None,
        metadata: Sequence[tuple[str, str]] | None,
        credentials: grpc.CallCredentials | None,
    ) -> None:
        self.method = method
        self.timeout = timeout
        self.metadata = metadata
        self.credentials = credentials
