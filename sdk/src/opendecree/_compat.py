"""Server version compatibility checking.

Provides runtime version checking against the VersionService endpoint.
Results are cached per client instance.
"""

from __future__ import annotations

import re
from typing import Any

import opendecree
from opendecree.errors import IncompatibleServerError
from opendecree.types import ServerVersion


def fetch_server_version(stub: Any, pb2: Any, timeout: float) -> ServerVersion:
    """Call VersionService.GetServerVersion and return a ServerVersion.

    Args:
        stub: VersionServiceStub instance.
        pb2: version_service_pb2 module.
        timeout: RPC timeout in seconds.

    Returns:
        ServerVersion with version and commit strings.
    """
    resp = stub.GetServerVersion(pb2.GetServerVersionRequest(), timeout=timeout)
    return ServerVersion(version=resp.version, commit=resp.commit)


async def async_fetch_server_version(stub: Any, pb2: Any, timeout: float) -> ServerVersion:
    """Async variant of fetch_server_version.

    Args:
        stub: VersionServiceStub instance (async).
        pb2: version_service_pb2 module.
        timeout: RPC timeout in seconds.

    Returns:
        ServerVersion with version and commit strings.
    """
    resp = await stub.GetServerVersion(pb2.GetServerVersionRequest(), timeout=timeout)
    return ServerVersion(version=resp.version, commit=resp.commit)


def check_version_compatible(server_version: str, supported_range: str | None = None) -> None:
    """Check if a server version satisfies the supported range.

    Args:
        server_version: Server version string (e.g., ``"0.3.1"``).
        supported_range: Version range (e.g., ``">=0.3.0,<1.0.0"``).
            Defaults to ``opendecree.SUPPORTED_SERVER_VERSION``.

    Raises:
        IncompatibleServerError: If the server version is outside the supported range.
    """
    if supported_range is None:
        supported_range = opendecree.SUPPORTED_SERVER_VERSION

    parsed = _parse_version(server_version)
    if parsed is None:
        # Can't parse (e.g., "dev") — skip check.
        return

    for constraint in supported_range.split(","):
        constraint = constraint.strip()
        if not _satisfies(parsed, constraint):
            raise IncompatibleServerError(
                f"Server version {server_version} is not compatible with this SDK "
                f"(requires {supported_range})"
            )


def _parse_version(version: str) -> tuple[int, ...] | None:
    """Parse a semver string into a tuple of ints, or None if unparseable."""
    match = re.match(r"^v?(\d+(?:\.\d+)*)", version)
    if not match:
        return None
    return tuple(int(p) for p in match.group(1).split("."))


def _satisfies(version: tuple[int, ...], constraint: str) -> bool:
    """Check if a version tuple satisfies a single constraint like '>=0.3.0'."""
    match = re.match(r"^(>=|<=|>|<|==|!=)(.+)$", constraint)
    if not match:
        return True

    op = match.group(1)
    target = _parse_version(match.group(2))
    if target is None:
        return True

    # Pad to same length for comparison.
    max_len = max(len(version), len(target))
    v = version + (0,) * (max_len - len(version))
    t = target + (0,) * (max_len - len(target))

    ops = {
        ">=": v >= t,
        "<=": v <= t,
        ">": v > t,
        "<": v < t,
        "==": v == t,
        "!=": v != t,
    }
    return ops[op]
