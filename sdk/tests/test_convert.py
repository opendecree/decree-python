"""Tests for type conversion."""

from datetime import timedelta

import pytest

from opendecree._convert import _parse_timedelta, convert_value, typed_value_to_string
from opendecree.errors import TypeMismatchError


def test_convert_str():
    assert convert_value("hello", str) == "hello"


def test_convert_int():
    assert convert_value("42", int) == 42


def test_convert_int_negative():
    assert convert_value("-1", int) == -1


def test_convert_int_invalid():
    with pytest.raises(TypeMismatchError, match="cannot convert"):
        convert_value("not-a-number", int)


def test_convert_float():
    assert convert_value("3.14", float) == pytest.approx(3.14)


def test_convert_float_invalid():
    with pytest.raises(TypeMismatchError, match="cannot convert"):
        convert_value("abc", float)


def test_convert_bool_true():
    assert convert_value("true", bool) is True
    assert convert_value("True", bool) is True
    assert convert_value("1", bool) is True


def test_convert_bool_false():
    assert convert_value("false", bool) is False
    assert convert_value("False", bool) is False
    assert convert_value("0", bool) is False


def test_convert_bool_invalid():
    with pytest.raises(TypeMismatchError, match="cannot convert"):
        convert_value("maybe", bool)


def test_convert_timedelta_hours():
    assert convert_value("24h", timedelta) == timedelta(hours=24)


def test_convert_timedelta_minutes():
    assert convert_value("30m", timedelta) == timedelta(minutes=30)


def test_convert_timedelta_seconds():
    assert convert_value("500s", timedelta) == timedelta(seconds=500)


def test_convert_timedelta_milliseconds():
    assert convert_value("100ms", timedelta) == timedelta(milliseconds=100)


def test_convert_timedelta_compound():
    assert convert_value("1h30m", timedelta) == timedelta(hours=1, minutes=30)


def test_convert_timedelta_invalid():
    with pytest.raises(TypeMismatchError, match="cannot convert"):
        convert_value("not-a-duration", timedelta)


def test_convert_unsupported_type():
    with pytest.raises(TypeMismatchError, match="unsupported type"):
        convert_value("hello", list)  # type: ignore[arg-type]


def test_parse_timedelta_empty():
    assert _parse_timedelta("") == timedelta()


def test_parse_timedelta_microseconds():
    assert _parse_timedelta("500us") == timedelta(microseconds=500)


def test_parse_timedelta_nanoseconds():
    td = _parse_timedelta("1000ns")
    assert td == timedelta(microseconds=1)


def test_parse_timedelta_unknown_unit():
    with pytest.raises(ValueError, match="unknown duration unit"):
        _parse_timedelta("5x")


# --- typed_value_to_string tests ---


def test_typed_value_to_string_not_typed_value():
    """Non-TypedValue objects fall back to str()."""
    assert typed_value_to_string("hello") == "hello"
    assert typed_value_to_string(42) == "42"


def test_typed_value_to_string_none_kind():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue()  # no kind set
    assert typed_value_to_string(tv) == ""


def test_typed_value_to_string_string():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(string_value="hello")
    assert typed_value_to_string(tv) == "hello"


def test_typed_value_to_string_integer():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(integer_value=42)
    assert typed_value_to_string(tv) == "42"


def test_typed_value_to_string_number():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(number_value=3.14)
    assert typed_value_to_string(tv) == "3.14"


def test_typed_value_to_string_bool_true():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(bool_value=True)
    assert typed_value_to_string(tv) == "true"


def test_typed_value_to_string_bool_false():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(bool_value=False)
    assert typed_value_to_string(tv) == "false"


def test_typed_value_to_string_url():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(url_value="https://example.com")
    assert typed_value_to_string(tv) == "https://example.com"


def test_typed_value_to_string_json():
    from opendecree._generated.centralconfig.v1 import types_pb2

    tv = types_pb2.TypedValue(json_value='{"key": "val"}')
    assert typed_value_to_string(tv) == '{"key": "val"}'


def test_typed_value_to_string_duration_zero():
    from google.protobuf.duration_pb2 import Duration

    from opendecree._generated.centralconfig.v1 import types_pb2

    d = Duration(seconds=0, nanos=0)
    tv = types_pb2.TypedValue(duration_value=d)
    assert typed_value_to_string(tv) == "0s"


def test_typed_value_to_string_duration_hours():
    from google.protobuf.duration_pb2 import Duration

    from opendecree._generated.centralconfig.v1 import types_pb2

    d = Duration(seconds=7200, nanos=0)
    tv = types_pb2.TypedValue(duration_value=d)
    assert typed_value_to_string(tv) == "2h"


def test_typed_value_to_string_duration_minutes():
    from google.protobuf.duration_pb2 import Duration

    from opendecree._generated.centralconfig.v1 import types_pb2

    d = Duration(seconds=300, nanos=0)
    tv = types_pb2.TypedValue(duration_value=d)
    assert typed_value_to_string(tv) == "5m"


def test_typed_value_to_string_duration_seconds():
    from google.protobuf.duration_pb2 import Duration

    from opendecree._generated.centralconfig.v1 import types_pb2

    d = Duration(seconds=45, nanos=0)
    tv = types_pb2.TypedValue(duration_value=d)
    assert typed_value_to_string(tv) == "45s"


def test_typed_value_to_string_duration_fractional():
    from google.protobuf.duration_pb2 import Duration

    from opendecree._generated.centralconfig.v1 import types_pb2

    d = Duration(seconds=1, nanos=500_000_000)
    tv = types_pb2.TypedValue(duration_value=d)
    assert typed_value_to_string(tv) == "1.5s"


def test_typed_value_to_string_time():
    from google.protobuf.timestamp_pb2 import Timestamp

    from opendecree._generated.centralconfig.v1 import types_pb2

    t = Timestamp(seconds=1700000000, nanos=0)
    tv = types_pb2.TypedValue(time_value=t)
    result = typed_value_to_string(tv)
    assert "2023" in result  # RFC 3339 format
