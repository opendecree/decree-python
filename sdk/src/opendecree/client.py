"""Synchronous ConfigClient for OpenDecree.

The ConfigClient wraps the gRPC ConfigService with a Pythonic API:
- Overloaded get() for typed reads (str by default, or int/float/bool/timedelta)
- Context manager for clean channel lifecycle
- watch() factory for live config subscriptions (Phase 4)
- Automatic retry with exponential backoff

All writes send string values — the server coerces to the schema-defined type.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from opendecree.watcher import ConfigWatcher

import grpc

from opendecree._channel import create_channel
from opendecree._compat import check_version_compatible, fetch_server_version
from opendecree._interceptors import AuthInterceptor, _build_metadata
from opendecree._retry import RetryConfig, with_retry
from opendecree._stubs import (
    ensure_stubs,
    make_string_typed_value,
    process_get_all_response,
    process_get_response,
)
from opendecree.errors import map_grpc_error
from opendecree.types import ServerVersion


class ConfigClient:
    """Synchronous client for reading and writing OpenDecree configuration values.

    Use as a context manager for clean channel lifecycle::

        with ConfigClient("localhost:9090", subject="myapp") as client:
            val = client.get("tenant-id", "payments.fee")
            retries = client.get("tenant-id", "payments.retries", int)
    """

    def __init__(
        self,
        target: str,
        *,
        subject: str | None = None,
        role: str = "superadmin",
        tenant_id: str | None = None,
        token: str | None = None,
        insecure: bool = True,
        credentials: grpc.ChannelCredentials | None = None,
        timeout: float = 10.0,
        retry: RetryConfig | None = None,
    ) -> None:
        """Create a new ConfigClient.

        Args:
            target: gRPC server address (e.g., ``"localhost:9090"``).
            subject: Identity for ``x-subject`` metadata header.
            role: Role for ``x-role`` metadata header. Defaults to ``"superadmin"``.
            tenant_id: Default tenant for ``x-tenant-id`` metadata header.
            token: Bearer token. When set, metadata headers are not sent.
            insecure: Use plaintext (no TLS). Defaults to True for local dev.
            credentials: TLS channel credentials. Overrides *insecure*.
            timeout: Default per-RPC timeout in seconds. Defaults to 10.
            retry: Retry configuration. Defaults to ``RetryConfig()``.
                Pass ``None`` to disable retry.
        """
        self._timeout = timeout
        self._retry = retry if retry is not None else RetryConfig()

        metadata = _build_metadata(subject=subject, role=role, tenant_id=tenant_id, token=token)
        interceptors: list[grpc.UnaryUnaryClientInterceptor] = []
        if metadata:
            interceptors.append(AuthInterceptor(metadata))

        channel = create_channel(target, insecure=insecure, credentials=credentials)
        if interceptors:
            self._channel = grpc.intercept_channel(channel, *interceptors)
        else:
            self._channel = channel
        self._raw_channel = channel  # keep ref for close()

        cs_pb2, cs_grpc = ensure_stubs()
        self._stub = cs_grpc.ConfigServiceStub(self._channel)
        self._pb2 = cs_pb2

        from opendecree._generated.centralconfig.v1 import (
            version_service_pb2,
            version_service_pb2_grpc,
        )

        self._version_stub = version_service_pb2_grpc.VersionServiceStub(self._channel)
        self._version_pb2 = version_service_pb2
        self._server_version: ServerVersion | None = None

    def close(self) -> None:
        """Close the underlying gRPC channel."""
        self._raw_channel.close()

    def __enter__(self) -> ConfigClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def server_version(self) -> ServerVersion:
        """The server's version, fetched once and cached.

        Returns:
            ServerVersion with version and commit strings.

        Raises:
            UnavailableError: If the server is unreachable.
        """
        if self._server_version is None:
            self._server_version = fetch_server_version(
                self._version_stub, self._version_pb2, self._timeout
            )
        return self._server_version

    def check_compatibility(self) -> None:
        """Check that the server version is compatible with this SDK.

        Fetches the server version (cached) and compares it against
        ``opendecree.SUPPORTED_SERVER_VERSION``.

        Raises:
            IncompatibleServerError: If the server version is outside the
                supported range.
            UnavailableError: If the server is unreachable.
        """
        check_version_compatible(self.server_version.version)

    # --- get() with @overload for type safety ---

    @overload
    def get(self, tenant_id: str, field_path: str) -> str: ...

    @overload
    def get(self, tenant_id: str, field_path: str, type: type[bool]) -> bool: ...

    @overload
    def get(self, tenant_id: str, field_path: str, type: type[int]) -> int: ...

    @overload
    def get(self, tenant_id: str, field_path: str, type: type[float]) -> float: ...

    @overload
    def get(self, tenant_id: str, field_path: str, type: type[timedelta]) -> timedelta: ...

    @overload
    def get(
        self,
        tenant_id: str,
        field_path: str,
        type: type[str],
        *,
        nullable: bool,
    ) -> str | None: ...

    def get(
        self,
        tenant_id: str,
        field_path: str,
        type: type | None = None,
        *,
        nullable: bool = False,
    ) -> object:
        """Get a config value, optionally converting to a specific type.

        Without a type argument, returns the raw string value.
        With a type argument, converts and returns the typed value.

        Args:
            tenant_id: Tenant UUID.
            field_path: Dot-separated field path (e.g., "payments.fee").
            type: Target type (str, int, float, bool, timedelta). Defaults to str.
            nullable: If True, return None for null/unset values instead of raising.

        Returns:
            The config value, converted to the requested type.

        Raises:
            NotFoundError: If the field has no value (and nullable is False).
            TypeMismatchError: If the value cannot be converted to the requested type.
        """
        target_type = type or str

        def _call() -> object:
            resp = self._stub.GetField(
                self._pb2.GetFieldRequest(tenant_id=tenant_id, field_path=field_path),
                timeout=self._timeout,
            )
            return process_get_response(resp, target_type, field_path, tenant_id, nullable)

        try:
            return with_retry(self._retry, _call)
        except grpc.RpcError as e:
            raise map_grpc_error(e) from e

    def get_all(self, tenant_id: str) -> dict[str, str]:
        """Get all config values for a tenant.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            A dict mapping field paths to their string values.

        Raises:
            NotFoundError: If the tenant does not exist.
        """

        def _call() -> dict[str, str]:
            resp = self._stub.GetConfig(
                self._pb2.GetConfigRequest(tenant_id=tenant_id),
                timeout=self._timeout,
            )
            return process_get_all_response(resp)

        try:
            return with_retry(self._retry, _call)
        except grpc.RpcError as e:
            raise map_grpc_error(e) from e

    def set(self, tenant_id: str, field_path: str, value: str) -> None:
        """Set a config value.

        The value is sent as a string — the server coerces it to the
        schema-defined type (integer, bool, etc.).

        Args:
            tenant_id: Tenant UUID.
            field_path: Dot-separated field path (e.g., ``"payments.fee"``).
            value: The value as a string.

        Raises:
            NotFoundError: If the field does not exist in the schema.
            LockedError: If the field is locked.
            InvalidArgumentError: If the value fails validation.
        """

        def _call() -> None:
            self._stub.SetField(
                self._pb2.SetFieldRequest(
                    tenant_id=tenant_id,
                    field_path=field_path,
                    value=make_string_typed_value(value),
                ),
                timeout=self._timeout,
            )

        try:
            with_retry(self._retry, _call)
        except grpc.RpcError as e:
            raise map_grpc_error(e) from e

    def set_many(
        self,
        tenant_id: str,
        values: dict[str, str],
        *,
        description: str = "",
    ) -> None:
        """Atomically set multiple config values.

        Args:
            tenant_id: Tenant UUID.
            values: Dict mapping field paths to string values.
            description: Optional description for the audit log.

        Raises:
            NotFoundError: If a field does not exist in the schema.
            LockedError: If any field is locked.
            InvalidArgumentError: If any value fails validation.
        """

        def _call() -> None:
            updates = [
                self._pb2.FieldUpdate(
                    field_path=fp,
                    value=make_string_typed_value(v),
                )
                for fp, v in values.items()
            ]
            self._stub.SetFields(
                self._pb2.SetFieldsRequest(
                    tenant_id=tenant_id,
                    updates=updates,
                    description=description,
                ),
                timeout=self._timeout,
            )

        try:
            with_retry(self._retry, _call)
        except grpc.RpcError as e:
            raise map_grpc_error(e) from e

    def set_null(self, tenant_id: str, field_path: str) -> None:
        """Set a config field to null.

        Args:
            tenant_id: Tenant UUID.
            field_path: Dot-separated field path.

        Raises:
            NotFoundError: If the field does not exist in the schema.
            LockedError: If the field is locked.
        """

        def _call() -> None:
            self._stub.SetField(
                self._pb2.SetFieldRequest(
                    tenant_id=tenant_id,
                    field_path=field_path,
                    # No value field → server interprets as null.
                ),
                timeout=self._timeout,
            )

        try:
            with_retry(self._retry, _call)
        except grpc.RpcError as e:
            raise map_grpc_error(e) from e

    def watch(self, tenant_id: str) -> ConfigWatcher:
        """Create a config watcher for a tenant.

        Use as a context manager — auto-starts on enter, auto-stops on exit::

            with client.watch("tenant-id") as watcher:
                fee = watcher.field("payments.fee", float, default=0.01)
                print(fee.value)

        The watcher uses the client's gRPC channel and auth settings.
        """
        from opendecree.watcher import ConfigWatcher

        return ConfigWatcher(self._stub, self._pb2, tenant_id, self._timeout)
