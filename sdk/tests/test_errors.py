"""Tests for error mapping."""

import datetime

import grpc
import grpc.aio
from google.protobuf import any_pb2, duration_pb2
from google.rpc import error_details_pb2, status_pb2

from opendecree.errors import (
    AlreadyExistsError,
    CancelledError,
    ChecksumMismatchError,
    DecreeError,
    LockedError,
    NotFoundError,
    PermissionDeniedError,
    ResourceExhaustedError,
    TimeoutError,
    UnimplementedError,
    UnavailableError,
    map_grpc_error,
)
from tests.conftest import FakeRpcError


def _make_retry_metadata(seconds: int, nanos: int = 0) -> grpc.aio.Metadata:
    retry_info = error_details_pb2.RetryInfo(
        retry_delay=duration_pb2.Duration(seconds=seconds, nanos=nanos)
    )
    detail = any_pb2.Any()
    detail.Pack(retry_info)
    rpc_status = status_pb2.Status(details=[detail])
    return grpc.aio.Metadata(("grpc-status-details-bin", rpc_status.SerializeToString()))


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


def test_deadline_exceeded_maps_to_timeout():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED))
    assert isinstance(err, TimeoutError)
    assert err.code == grpc.StatusCode.DEADLINE_EXCEEDED


def test_resource_exhausted():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.RESOURCE_EXHAUSTED))
    assert isinstance(err, ResourceExhaustedError)


def test_cancelled():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.CANCELLED))
    assert isinstance(err, CancelledError)


def test_unimplemented():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.UNIMPLEMENTED))
    assert isinstance(err, UnimplementedError)


def test_trailing_metadata_captured():
    meta = grpc.aio.Metadata(("x-custom", "value"))
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.UNAVAILABLE, trailing_metadata=meta))
    assert err.trailing_metadata is not None
    assert dict(err.trailing_metadata).get("x-custom") == "value"


def test_no_trailing_metadata():
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.NOT_FOUND))
    assert err.trailing_metadata is None
    assert err.retry_after is None


def test_retry_info_parsed():
    meta = _make_retry_metadata(seconds=5, nanos=500_000_000)
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.RESOURCE_EXHAUSTED, trailing_metadata=meta))
    assert err.retry_after == datetime.timedelta(seconds=5, microseconds=500_000)


def test_retry_info_nanos_precision():
    meta = _make_retry_metadata(seconds=0, nanos=250_000_000)
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED, trailing_metadata=meta))
    assert err.retry_after == datetime.timedelta(microseconds=250_000)


def test_no_retry_info_in_metadata():
    meta = grpc.aio.Metadata(("x-other", "val"))
    err = map_grpc_error(FakeRpcError(grpc.StatusCode.UNAVAILABLE, trailing_metadata=meta))
    assert err.retry_after is None
