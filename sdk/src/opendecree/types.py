"""Public data types returned by the OpenDecree SDK.

All types are frozen, slotted dataclasses — immutable and fast.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

#: Native Python value accepted by `set`/`set_many`/`FieldUpdate`. The SDK
#: picks the wire `TypedValue` variant from the value's runtime type — see
#: `make_typed_value` in `_stubs.py`. `URL` (a `str` subtype) is covered by
#: `str` here but still selects the distinct `url_value` wire variant.
ConfigValue = str | int | float | bool | datetime | timedelta | dict[str, Any] | list[Any]


@dataclass(frozen=True, slots=True)
class Change:
    """A configuration change event from a subscription.

    Attributes:
        field_path: Dot-separated field path that changed.
        old_value: Previous value as a string, or ``None`` if newly created.
        new_value: New value as a string, or ``None`` if set to null.
        version: Config version number after this change.
        changed_by: Identity of who made the change.
    """

    field_path: str
    old_value: str | None
    new_value: str | None
    version: int
    changed_by: str = ""


@dataclass(frozen=True, slots=True)
class FieldUpdate:
    """A single field update for use with :meth:`ConfigClient.set_many`.

    Attributes:
        field_path: Dot-separated field path (e.g., ``"payments.fee"``).
        value: The value as a native Python type matching the field's schema
            type — ``str``, ``int``, ``float``, ``bool``, ``datetime``,
            ``timedelta``, ``dict``, ``list``, or ``URL`` (for ``url``-typed
            fields). The SDK converts it to the matching wire representation.
        expected_checksum: When set, the server rejects the write if the
            current value's checksum does not match (optimistic concurrency).
        value_description: Optional description stored with this specific value.
    """

    field_path: str
    value: ConfigValue
    expected_checksum: str | None = None
    value_description: str | None = None


@dataclass(frozen=True, slots=True)
class ServerVersion:
    """Server version information from the ServerService.

    Attributes:
        version: Semantic version string (e.g., ``"0.3.1"``).
        commit: Git commit hash of the server build.
    """

    version: str
    commit: str
