"""Tests for write-side TypedValue construction."""

from datetime import UTC, datetime, timedelta

import pytest

from opendecree._convert import URL
from opendecree._generated.centralconfig.v1 import types_pb2
from opendecree._stubs import make_typed_value


def test_make_typed_value_string():
    tv = make_typed_value("hello")
    assert tv.WhichOneof("kind") == "string_value"
    assert tv.string_value == "hello"


def test_make_typed_value_url():
    tv = make_typed_value(URL("https://example.com"))
    assert tv.WhichOneof("kind") == "url_value"
    assert tv.url_value == "https://example.com"


def test_make_typed_value_bool():
    tv = make_typed_value(True)
    assert tv.WhichOneof("kind") == "bool_value"
    assert tv.bool_value is True


def test_make_typed_value_bool_not_integer():
    # bool is a subclass of int — must be checked first.
    tv = make_typed_value(False)
    assert tv.WhichOneof("kind") == "bool_value"


def test_make_typed_value_integer():
    tv = make_typed_value(42)
    assert tv.WhichOneof("kind") == "integer_value"
    assert tv.integer_value == 42


def test_make_typed_value_number():
    tv = make_typed_value(3.14)
    assert tv.WhichOneof("kind") == "number_value"
    assert tv.number_value == pytest.approx(3.14)


def test_make_typed_value_time():
    dt = datetime(2024, 1, 15, 12, 30, tzinfo=UTC)
    tv = make_typed_value(dt)
    assert tv.WhichOneof("kind") == "time_value"
    assert tv.time_value.ToDatetime(tzinfo=UTC) == dt


def test_make_typed_value_duration():
    tv = make_typed_value(timedelta(hours=1, minutes=30))
    assert tv.WhichOneof("kind") == "duration_value"
    assert tv.duration_value.ToTimedelta() == timedelta(hours=1, minutes=30)


def test_make_typed_value_json_dict():
    tv = make_typed_value({"a": 1})
    assert tv.WhichOneof("kind") == "json_value"
    assert tv.json_value == '{"a": 1}'


def test_make_typed_value_json_list():
    tv = make_typed_value([1, 2, 3])
    assert tv.WhichOneof("kind") == "json_value"
    assert tv.json_value == "[1, 2, 3]"


def test_make_typed_value_unsupported_type():
    with pytest.raises(TypeError, match="unsupported value type for set"):
        make_typed_value(object())


def test_make_typed_value_returns_typed_value_proto():
    assert isinstance(make_typed_value("x"), types_pb2.TypedValue)
