"""Verify generated stubs don't pollute sys.path or shadow external packages."""

import sys
import types


def test_no_syspath_pollution():
    import opendecree  # noqa: F401

    for entry in sys.path:
        assert "opendecree/_generated" not in entry, (
            f"sys.path polluted with generated dir: {entry}"
        )


def test_centralconfig_not_top_level_module():
    import opendecree  # noqa: F401

    assert "centralconfig" not in sys.modules, (
        "bare 'centralconfig' leaked into sys.modules — import shadowing possible"
    )


def test_no_shadowing_with_external_centralconfig():
    sentinel = types.ModuleType("centralconfig")
    sentinel.__version__ = "external"
    sys.modules.setdefault("centralconfig", sentinel)

    import opendecree  # noqa: F401
    from opendecree._generated.centralconfig.v1 import types_pb2  # noqa: F401

    assert sys.modules["centralconfig"] is sentinel, (
        "opendecree import replaced external 'centralconfig' module"
    )
