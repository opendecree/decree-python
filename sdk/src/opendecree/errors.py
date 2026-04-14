"""Exception hierarchy for the OpenDecree SDK.

Maps gRPC status codes to typed Python exceptions.
"""

from __future__ import annotations

import grpc


class DecreeError(Exception):
    """Base exception for all OpenDecree SDK errors."""

    def __init__(self, message: str, code: grpc.StatusCode | None = None) -> None:
        """Create a DecreeError.

        Args:
            message: Human-readable error description.
            code: The gRPC status code that caused this error, if any.
        """
        super().__init__(message)
        self.code = code


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


_STATUS_MAP: dict[grpc.StatusCode, type[DecreeError]] = {
    grpc.StatusCode.NOT_FOUND: NotFoundError,
    grpc.StatusCode.ALREADY_EXISTS: AlreadyExistsError,
    grpc.StatusCode.INVALID_ARGUMENT: InvalidArgumentError,
    grpc.StatusCode.FAILED_PRECONDITION: LockedError,
    grpc.StatusCode.ABORTED: ChecksumMismatchError,
    grpc.StatusCode.PERMISSION_DENIED: PermissionDeniedError,
    grpc.StatusCode.UNAUTHENTICATED: PermissionDeniedError,
    grpc.StatusCode.UNAVAILABLE: UnavailableError,
}


def map_grpc_error(err: grpc.RpcError) -> DecreeError:
    """Convert a gRPC ``RpcError`` to a typed ``DecreeError``.

    Maps known gRPC status codes to specific exception subclasses.
    Unknown codes produce a generic ``DecreeError``.
    """
    code = err.code()
    details = err.details()
    exc_class = _STATUS_MAP.get(code, DecreeError)
    return exc_class(details or str(err), code)
