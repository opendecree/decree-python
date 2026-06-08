"""Shared helpers for loading generated proto stubs and building TypedValues."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any

from opendecree._convert import URL
from opendecree.types import ConfigValue


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


def make_typed_value(value: ConfigValue) -> Any:
    """Build a TypedValue proto whose oneof variant matches `value`'s Python type.

    This is the write-side mirror of `convert_value`: the server requires the
    populated oneof variant to match the field's declared schema type exactly
    (no coercion), so the SDK picks the variant from the value's runtime type
    rather than looking up the schema (which would cost an extra round trip).

    | Python type           | TypedValue variant |
    |-----------------------|--------------------|
    | `bool`                | `bool_value`       |
    | `URL`                 | `url_value`        |
    | `str`                 | `string_value`     |
    | `int`                 | `integer_value`    |
    | `float`               | `number_value`     |
    | `datetime`            | `time_value`       |
    | `timedelta`           | `duration_value`   |
    | `dict` / `list`       | `json_value`       |

    `bool` is checked before `int` (it's a subclass), and `URL` before `str`
    (same reason) — `URL` is a `str` subtype precisely so a write can
    distinguish a `url`-typed field from a plain `string`-typed one.
    """
    from google.protobuf import duration_pb2, timestamp_pb2

    from opendecree._generated.centralconfig.v1 import types_pb2

    if isinstance(value, bool):
        return types_pb2.TypedValue(bool_value=value)
    if isinstance(value, URL):
        return types_pb2.TypedValue(url_value=value)
    if isinstance(value, str):
        return types_pb2.TypedValue(string_value=value)
    if isinstance(value, int):
        return types_pb2.TypedValue(integer_value=value)
    if isinstance(value, float):
        return types_pb2.TypedValue(number_value=value)
    if isinstance(value, datetime):
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(value)
        return types_pb2.TypedValue(time_value=ts)
    if isinstance(value, timedelta):
        d = duration_pb2.Duration()
        d.FromTimedelta(value)
        return types_pb2.TypedValue(duration_value=d)
    if isinstance(value, (dict, list)):
        return types_pb2.TypedValue(json_value=json.dumps(value))
    raise TypeError(f"unsupported value type for set(): {type(value).__name__}")


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
