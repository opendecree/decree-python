"""Basic tests to verify the package is importable."""

import re
from importlib.metadata import version as _pkg_version

import opendecree


def test_version():
    assert opendecree.__version__ == _pkg_version("opendecree")
    assert re.match(r"^\d+\.\d+\.\d+([abrc]\d+|\.post\d+|\.dev\d+)?$", opendecree.__version__)


def test_supported_server_version():
    assert opendecree.SUPPORTED_SERVER_VERSION == ">=0.3.0,<1.0.0"


def test_proto_version():
    assert opendecree.PROTO_VERSION == "v1"
