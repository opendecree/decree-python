"""OpenDecree Python SDK — schema-driven configuration management."""

from importlib.metadata import version as _pkg_version

__version__ = _pkg_version("opendecree")

SUPPORTED_SERVER_VERSION = ">=0.3.0,<1.0.0"
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
    UnimplementedError,
    UnavailableError,
)
from opendecree.types import Change, ConfigValue, FieldUpdate, ServerVersion
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
    "ConfigValue",
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
    "UnimplementedError",
    "UnavailableError",
    "WatchedField",
    "__version__",
]
