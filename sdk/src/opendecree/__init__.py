"""OpenDecree Python SDK — schema-driven configuration management."""

from importlib.metadata import version as _pkg_version

__version__ = _pkg_version("opendecree")

from opendecree._constants import SUPPORTED_SERVER_VERSION

PROTO_VERSION = "v1"

from opendecree._convert import URL
from opendecree._retry import RetryConfig
from opendecree.async_client import AsyncConfigClient
from opendecree.async_watcher import AsyncConfigWatcher, AsyncWatchedField
from opendecree.client import ConfigClient
from opendecree.errors import (
    AlreadyExistsError,
    CancelledError,
    ChecksumMismatchError,
    DecreeError,
    IncompatibleServerError,
    InvalidArgumentError,
    LockedError,
    NotFoundError,
    PermissionDeniedError,
    ResourceExhaustedError,
    TimeoutError,
    TypeMismatchError,
    UnavailableError,
    UnimplementedError,
)
from opendecree.types import Change, FieldUpdate, ServerVersion
from opendecree.watcher import ConfigWatcher, WatchedField

__all__ = [
    "PROTO_VERSION",
    "SUPPORTED_SERVER_VERSION",
    "URL",
    "AlreadyExistsError",
    "AsyncConfigClient",
    "AsyncConfigWatcher",
    "AsyncWatchedField",
    "CancelledError",
    "Change",
    "ChecksumMismatchError",
    "ConfigClient",
    "ConfigWatcher",
    "DecreeError",
    "FieldUpdate",
    "IncompatibleServerError",
    "InvalidArgumentError",
    "LockedError",
    "NotFoundError",
    "PermissionDeniedError",
    "ResourceExhaustedError",
    "RetryConfig",
    "ServerVersion",
    "TimeoutError",
    "TypeMismatchError",
    "UnavailableError",
    "UnimplementedError",
    "WatchedField",
    "__version__",
]
