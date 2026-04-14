"""Basic tests to verify the package is importable."""

import opendecree


def test_version():
    assert opendecree.__version__ == "0.1.0"


def test_supported_server_version():
    assert opendecree.SUPPORTED_SERVER_VERSION == ">=0.3.0,<1.0.0"


def test_proto_version():
    assert opendecree.PROTO_VERSION == "v1"
