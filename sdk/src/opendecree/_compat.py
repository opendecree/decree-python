"""Server version compatibility checking.

Provides runtime version checking against the ServerService endpoint.
Results are cached per client instance.
"""

from __future__ import annotations

from typing import Any

from packaging.specifiers import InvalidSpecifier, Specifier
from packaging.version import InvalidVersion, Version

import opendecree
from opendecree.errors import IncompatibleServerError
from opendecree.types import ServerVersion


def fetch_server_version(stub: Any, pb2: Any, timeout: float) -> ServerVersion:
    """Call ServerService.GetServerInfo and return a ServerVersion.

    Args:
        stub: ServerServiceStub instance.
        pb2: server_service_pb2 module.
        timeout: RPC timeout in seconds.

    Returns:
        ServerVersion with version and commit strings.
    """
    resp = stub.GetServerInfo(pb2.GetServerInfoRequest(), timeout=timeout)
    return ServerVersion(version=resp.version, commit=resp.commit)


async def async_fetch_server_version(stub: Any, pb2: Any, timeout: float) -> ServerVersion:
    """Async variant of fetch_server_version.

    Args:
        stub: ServerServiceStub instance (async).
        pb2: server_service_pb2 module.
        timeout: RPC timeout in seconds.

    Returns:
        ServerVersion with version and commit strings.
    """
    resp = await stub.GetServerInfo(pb2.GetServerInfoRequest(), timeout=timeout)
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
        if not _satisfies(parsed, constraint.strip()):
            raise IncompatibleServerError(
                f"Server version {server_version} is not compatible with this SDK "
                f"(requires {supported_range})"
            )


def _parse_version(version: str) -> Version | None:
    """Parse a version string via PEP 440, or None if unparseable."""
    try:
        return Version(version)
    except InvalidVersion:
        return None


def _satisfies(version: Version, constraint: str) -> bool:
    """Check if a Version satisfies a single constraint like '>=0.3.0'."""
    try:
        return version in Specifier(constraint, prereleases=True)
    except InvalidSpecifier:
        return True
