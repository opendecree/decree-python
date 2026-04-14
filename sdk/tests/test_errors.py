"""Tests for error mapping."""

import grpc

from opendecree.errors import (
    AlreadyExistsError,
    ChecksumMismatchError,
    DecreeError,
    LockedError,
    NotFoundError,
    PermissionDeniedError,
    UnavailableError,
    map_grpc_error,
)
from tests.conftest import FakeRpcError


def test_not_found():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.NOT_FOUND, "gone"))
    assert isinstance(err, NotFoundError)
    assert err.code == grpc.StatusCode.NOT_FOUND
    assert "gone" in str(err)


def test_already_exists():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.ALREADY_EXISTS))
    assert isinstance(err, AlreadyExistsError)


def test_failed_precondition_maps_to_locked():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.FAILED_PRECONDITION))
    assert isinstance(err, LockedError)


def test_aborted_maps_to_checksum():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.ABORTED))
    assert isinstance(err, ChecksumMismatchError)


def test_permission_denied():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.PERMISSION_DENIED))
    assert isinstance(err, PermissionDeniedError)


def test_unauthenticated_maps_to_permission():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.UNAUTHENTICATED))
    assert isinstance(err, PermissionDeniedError)


def test_unavailable():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.UNAVAILABLE))
    assert isinstance(err, UnavailableError)


def test_unknown_code_falls_back():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.INTERNAL, "oops"))
    assert type(err) is DecreeError
    assert err.code == grpc.StatusCode.INTERNAL


def test_empty_details():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.NOT_FOUND, ""))
    assert isinstance(err, NotFoundError)
