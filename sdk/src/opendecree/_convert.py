"""Type conversion between proto TypedValue and Python native types.

The server stores all values internally as strings. The SDK converts between
the proto TypedValue representation and Python types (str, int, float, bool,
timedelta) at the boundary.
"""

from __future__ import annotations

from datetime import timedelta

from opendecree.errors import TypeMismatchError


def _parse_timedelta(s: str) -> timedelta:
    """Parse a Go-style duration string (e.g., '24h', '30m', '500ms') to timedelta.

    Supported units: h (hours), m (minutes), s (seconds), ms (milliseconds),
    us/µs (microseconds), ns (nanoseconds). Compound forms like '1h30m' work.
    """
    if not s:
        return timedelta()

    total_seconds = 0.0
    i = 0
    while i < len(s):
        # Parse number.
        start = i
        while i < len(s) and (s[i].isdigit() or s[i] == "."):
            i += 1
        if start == i:
            raise ValueError(f"invalid duration: {s!r}")
        num = float(s[start:i])

        # Parse unit.
        unit_start = i
        while i < len(s) and s[i].isalpha():
            i += 1
        unit = s[unit_start:i]

        match unit:
            case "h":
                total_seconds += num * 3600
            case "m":
                total_seconds += num * 60
            case "s":
                total_seconds += num
            case "ms":
                total_seconds += num / 1000
            case "us" | "\u00b5s":
                total_seconds += num / 1_000_000
            case "ns":
                total_seconds += num / 1_000_000_000
            case _:
                raise ValueError(f"unknown duration unit: {unit!r} in {s!r}")

    return timedelta(seconds=total_seconds)


def convert_value(raw: str, target_type: type) -> object:
    """Convert a raw string value to the target Python type.

    Supported types: str, int, float, bool, timedelta.

    Raises:
        TypeMismatchError: If the value cannot be converted to the target type.
    """
    if target_type is str:
        return raw
    try:
        if target_type is int:
            return int(raw)
        if target_type is float:
            return float(raw)
        if target_type is bool:
            if raw.lower() in ("true", "1"):
                return True
            if raw.lower() in ("false", "0"):
                return False
            raise ValueError(f"cannot convert {raw!r} to bool")
        if target_type is timedelta:
            return _parse_timedelta(raw)
    except (ValueError, OverflowError) as e:
        raise TypeMismatchError(f"cannot convert {raw!r} to {target_type.__name__}: {e}") from e

    raise TypeMismatchError(f"unsupported type: {target_type.__name__}")


def typed_value_to_string(tv: object) -> str:
    """Extract the string representation from a proto TypedValue.

    The TypedValue oneof has 8 variants: integer_value, number_value,
    string_value, bool_value, time_value, duration_value, url_value, json_value.
    Each is converted to its canonical string form.
    """
    from opendecree._generated.centralconfig.v1 import types_pb2

    if not isinstance(tv, types_pb2.TypedValue):
        return str(tv)

    kind = tv.WhichOneof("kind")
    if kind is None:
        return ""

    val = getattr(tv, kind)

    # Handle each variant explicitly for clarity and correctness.
    match kind:
        case "bool_value":
            return "true" if val else "false"
        case "time_value":
            return str(val.ToJsonString())
        case "duration_value":
            # Use integer arithmetic to avoid float precision issues.
            total_ns = val.seconds * 1_000_000_000 + val.nanos
            if total_ns == 0:
                return "0s"
            total_s = total_ns // 1_000_000_000
            remainder_ns = total_ns % 1_000_000_000
            if remainder_ns == 0:
                if total_s >= 3600 and total_s % 3600 == 0:
                    return f"{total_s // 3600}h"
                if total_s >= 60 and total_s % 60 == 0:
                    return f"{total_s // 60}m"
                return f"{total_s}s"
            # Has sub-second component — use float seconds.
            total_float = total_ns / 1_000_000_000
            return f"{total_float}s"
        case "integer_value" | "number_value" | "string_value" | "url_value" | "json_value":
            return str(val)
        case _:
            return str(val)
