"""Optional OpenTelemetry gRPC instrumentation.

Lazily imports opentelemetry-instrumentation-grpc so the core SDK does not
require OTel as a dependency. Install the optional extra:

    pip install 'opendecree[otel]'
"""

from __future__ import annotations

from typing import Any

_HINT = "Install: pip install 'opendecree[otel]'"


def make_sync_interceptor() -> Any:
    """Return an OpenTelemetryClientInterceptor for use with grpc.intercept_channel."""
    try:
        from opentelemetry.instrumentation.grpc import OpenTelemetryClientInterceptor
    except ImportError as exc:
        raise ImportError(
            f"opentelemetry-instrumentation-grpc is required when otel=True. {_HINT}"
        ) from exc
    return OpenTelemetryClientInterceptor()


def make_aio_interceptors() -> list[Any]:
    """Return OTel interceptors for a grpc.aio channel.

    Uses the internal _aio_client module — there is no public per-channel API
    for async OTel instrumentation in opentelemetry-instrumentation-grpc.
    """
    try:
        from opentelemetry.instrumentation.grpc._aio_client import (
            OpenTelemetryAioClientInterceptor,
        )
    except ImportError as exc:
        raise ImportError(
            f"opentelemetry-instrumentation-grpc is required when otel=True. {_HINT}"
        ) from exc
    return [OpenTelemetryAioClientInterceptor()]
