"""Public data types returned by the OpenDecree SDK.

All types are frozen, slotted dataclasses — immutable and fast.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfigValue:
    """A single configuration value.

    Attributes:
        field_path: Dot-separated field path (e.g., ``"payments.fee"``).
        value: The raw string value.
        checksum: xxHash checksum of the value.
        description: Optional description set when the value was written.
    """

    field_path: str
    value: str
    checksum: str
    description: str = ""


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
class ServerVersion:
    """Server version information from the VersionService.

    Attributes:
        version: Semantic version string (e.g., ``"0.3.1"``).
        commit: Git commit hash of the server build.
    """

    version: str
    commit: str
