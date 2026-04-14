"""Shared helpers for loading generated proto stubs and building TypedValues."""

from __future__ import annotations

from types import ModuleType
from typing import Any


def ensure_stubs() -> tuple[ModuleType, ModuleType]:
    """Lazy-load ConfigService proto stubs on first use.

    Returns (config_service_pb2, config_service_pb2_grpc).
    """
    from opendecree._generated.centralconfig.v1 import (
        config_service_pb2 as cs_pb2,
    )
    from opendecree._generated.centralconfig.v1 import (
        config_service_pb2_grpc as cs_grpc,
    )

    return cs_pb2, cs_grpc


def make_string_typed_value(value: str) -> Any:
    """Create a TypedValue proto with string_value set.

    The server accepts string values for all field types and performs
    type coercion based on the schema definition.
    """
    from opendecree._generated.centralconfig.v1 import types_pb2

    return types_pb2.TypedValue(string_value=value)


def process_get_response(
    resp: Any,
    target_type: type,
    field_path: str,
    tenant_id: str,
    nullable: bool,
) -> object:
    """Extract and convert a value from a GetField response.

    Shared by both sync and async clients.
    """
    from opendecree._convert import convert_value, typed_value_to_string
    from opendecree.errors import NotFoundError

    if not resp.value.HasField("value"):
        if nullable:
            return None
        raise NotFoundError(f"field {field_path!r} has no value for tenant {tenant_id!r}")
    raw = typed_value_to_string(resp.value.value)
    return convert_value(raw, target_type)


def process_get_all_response(resp: Any) -> dict[str, str]:
    """Extract all values from a GetConfig response as a string dict.

    Shared by both sync and async clients.
    """
    from opendecree._convert import typed_value_to_string

    result: dict[str, str] = {}
    for cv in resp.config.values:
        if cv.HasField("value"):
            result[cv.field_path] = typed_value_to_string(cv.value)
    return result
