"""Tests for public data types."""

from opendecree.types import Change, ConfigValue, ServerVersion


def test_config_value_frozen():
    cv = ConfigValue(field_path="a.b", value="1", checksum="abc")
    assert cv.field_path == "a.b"
    assert cv.value == "1"
    assert cv.checksum == "abc"
    assert cv.description == ""


def test_change():
    c = Change(field_path="x", old_value="1", new_value="2", version=3, changed_by="alice")
    assert c.field_path == "x"
    assert c.old_value == "1"
    assert c.new_value == "2"
    assert c.version == 3
    assert c.changed_by == "alice"


def test_change_nullable():
    c = Change(field_path="x", old_value=None, new_value="2", version=1)
    assert c.old_value is None
    assert c.changed_by == ""


def test_server_version():
    sv = ServerVersion(version="0.3.1", commit="abc123")
    assert sv.version == "0.3.1"
    assert sv.commit == "abc123"
