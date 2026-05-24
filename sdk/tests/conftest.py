"""Shared test fixtures and helpers."""

from __future__ import annotations

import os
import uuid

import grpc
import grpc.aio
import pytest

from opendecree._generated.centralconfig.v1 import (
    schema_service_pb2,
    schema_service_pb2_grpc,
    types_pb2,
)

# ---------------------------------------------------------------------------
# Integration fixtures — skipped unless DECREE_TEST_ADDR is set
# ---------------------------------------------------------------------------


def _integration_addr() -> str | None:
    return os.environ.get("DECREE_TEST_ADDR")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-skip integration tests when DECREE_TEST_ADDR is not set."""
    if _integration_addr():
        return
    skip = pytest.mark.skip(reason="DECREE_TEST_ADDR not set")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def decree_addr() -> str:
    addr = _integration_addr()
    if not addr:
        pytest.skip("DECREE_TEST_ADDR not set")
    return addr


@pytest.fixture(scope="session")
def grpc_channel(decree_addr: str) -> grpc.Channel:
    channel = grpc.insecure_channel(decree_addr)
    yield channel
    channel.close()


@pytest.fixture(scope="session")
def schema_stub(grpc_channel: grpc.Channel) -> schema_service_pb2_grpc.SchemaServiceStub:
    return schema_service_pb2_grpc.SchemaServiceStub(grpc_channel)


def _superadmin_metadata() -> list[tuple[str, str]]:
    return [("x-decree-subject", "pytest"), ("x-decree-role", "superadmin")]


@pytest.fixture(scope="session")
def live_schema(
    schema_stub: schema_service_pb2_grpc.SchemaServiceStub,
) -> tuple[str, int]:
    """Create + publish a schema; return (schema_id, version).

    Cleaned up after the session via DeleteSchema.
    """
    meta = _superadmin_metadata()
    tag = uuid.uuid4().hex[:8]
    resp = schema_stub.CreateSchema(
        schema_service_pb2.CreateSchemaRequest(
            name=f"pytest-{tag}",
            description="Created by pytest integration suite",
            fields=[
                types_pb2.SchemaField(
                    path="greeting",
                    type=types_pb2.FIELD_TYPE_STRING,
                ),
                types_pb2.SchemaField(
                    path="count",
                    type=types_pb2.FIELD_TYPE_INT,
                ),
                types_pb2.SchemaField(
                    path="ratio",
                    type=types_pb2.FIELD_TYPE_NUMBER,
                    nullable=True,
                ),
                types_pb2.SchemaField(
                    path="enabled",
                    type=types_pb2.FIELD_TYPE_BOOL,
                ),
            ],
        ),
        metadata=meta,
    )
    schema_id: str = resp.schema.id
    version: int = resp.schema.current_version

    schema_stub.PublishSchema(
        schema_service_pb2.PublishSchemaRequest(id=schema_id),
        metadata=meta,
    )

    yield schema_id, version

    schema_stub.DeleteSchema(
        schema_service_pb2.DeleteSchemaRequest(id=schema_id),
        metadata=meta,
    )


@pytest.fixture(scope="session")
def live_tenant(
    schema_stub: schema_service_pb2_grpc.SchemaServiceStub,
    live_schema: tuple[str, int],
) -> str:
    """Create a tenant against the live schema; return tenant_id (name slug).

    Cleaned up after the session via DeleteTenant.
    """
    meta = _superadmin_metadata()
    schema_id, version = live_schema
    tag = uuid.uuid4().hex[:8]
    name = f"pytest-{tag}"
    resp = schema_stub.CreateTenant(
        schema_service_pb2.CreateTenantRequest(
            name=name,
            schema_id=schema_id,
            schema_version=version,
        ),
        metadata=meta,
    )
    tenant_id: str = resp.tenant.id
    yield name
    schema_stub.DeleteTenant(
        schema_service_pb2.DeleteTenantRequest(id=tenant_id),
        metadata=meta,
    )


class FakeRpcError(grpc.aio.AioRpcError):
    """A concrete RpcError for testing.

    AioRpcError is a subclass of grpc.RpcError, so this works for both
    sync and async error handling.
    """

    def __init__(
        self,
        code: grpc.StatusCode,
        details: str = "test",
        trailing_metadata: grpc.aio.Metadata | None = None,
    ) -> None:
        # AioRpcError.__init__ expects (code, initial_metadata, trailing_metadata,
        # details, debug_error_string).
        super().__init__(code, None, trailing_metadata, details, None)  # type: ignore[arg-type]
