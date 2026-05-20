"""Exception hierarchy for the OpenDecree SDK.

Maps gRPC status codes to typed Python exceptions.
"""

from __future__ import annotations

import datetime

import grpc
import grpc.aio
from google.rpc import error_details_pb2, status_pb2


class DecreeError(Exception):
    """Base exception for all OpenDecree SDK errors."""

    def __init__(
        self,
        message: str,
        code: grpc.StatusCode | None = None,
        *,
        trailing_metadata: grpc.aio.Metadata | None = None,
        retry_after: datetime.timedelta | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.trailing_metadata = trailing_metadata
        self.retry_after = retry_after


class NotFoundError(DecreeError):
    """Raised when a requested resource does not exist."""


class AlreadyExistsError(DecreeError):
    """Raised when attempting to create a resource that already exists."""


class InvalidArgumentError(DecreeError):
    """Raised when a request contains invalid arguments."""


class LockedError(DecreeError):
    """Raised when a field is locked and cannot be modified."""


class ChecksumMismatchError(DecreeError):
    """Raised when an optimistic concurrency check fails."""


class PermissionDeniedError(DecreeError):
    """Raised when the caller lacks permission for the operation."""


class UnavailableError(DecreeError):
    """Raised when the server is unavailable."""


class IncompatibleServerError(DecreeError):
    """Raised when the server version is incompatible with this SDK."""


class TypeMismatchError(DecreeError):
    """Raised when a typed getter receives a value of the wrong type."""


class TimeoutError(DecreeError):
    """Raised when the operation deadline was exceeded."""


class ResourceExhaustedError(DecreeError):
    """Raised when a resource quota or rate limit is exceeded."""


class CancelledError(DecreeError):
    """Raised when the operation was cancelled."""


class UnimplementedError(DecreeError):
    """Raised when the server has not implemented the operation."""


_STATUS_MAP: dict[grpc.StatusCode, type[DecreeError]] = {
    grpc.StatusCode.NOT_FOUND: NotFoundError,
    grpc.StatusCode.ALREADY_EXISTS: AlreadyExistsError,
    grpc.StatusCode.INVALID_ARGUMENT: InvalidArgumentError,
    grpc.StatusCode.FAILED_PRECONDITION: LockedError,
    grpc.StatusCode.ABORTED: ChecksumMismatchError,
    grpc.StatusCode.PERMISSION_DENIED: PermissionDeniedError,
    grpc.StatusCode.UNAUTHENTICATED: PermissionDeniedError,
    grpc.StatusCode.UNAVAILABLE: UnavailableError,
    grpc.StatusCode.DEADLINE_EXCEEDED: TimeoutError,
    grpc.StatusCode.RESOURCE_EXHAUSTED: ResourceExhaustedError,
    grpc.StatusCode.CANCELLED: CancelledError,
    grpc.StatusCode.UNIMPLEMENTED: UnimplementedError,
}


def _parse_retry_after(metadata: grpc.aio.Metadata) -> datetime.timedelta | None:
    for key, value in metadata:
        if key != "grpc-status-details-bin" or not isinstance(value, bytes):
            continue
        rpc_status = status_pb2.Status()
        rpc_status.ParseFromString(value)
        for detail in rpc_status.details:
            retry_info = error_details_pb2.RetryInfo()
            if detail.Unpack(retry_info):
                d = retry_info.retry_delay
                return datetime.timedelta(seconds=d.seconds, microseconds=d.nanos // 1000)
    return None


def map_grpc_error(err: grpc.RpcError) -> DecreeError:
    """Convert a gRPC ``RpcError`` to a typed ``DecreeError``.

    Maps known gRPC status codes to specific exception subclasses.
    Unknown codes produce a generic ``DecreeError``.
    """
    code = err.code()
    details = err.details()
    trailing: grpc.aio.Metadata | None = getattr(err, "trailing_metadata", lambda: None)()
    retry_after = _parse_retry_after(trailing) if trailing else None
    exc_class = _STATUS_MAP.get(code, DecreeError)
    return exc_class(details or str(err), code, trailing_metadata=trailing, retry_after=retry_after)
