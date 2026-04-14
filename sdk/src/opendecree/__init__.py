"""OpenDecree Python SDK — schema-driven configuration management."""

__version__ = "0.1.0"

SUPPORTED_SERVER_VERSION = ">=0.3.0,<1.0.0"
PROTO_VERSION = "v1"

from opendecree._retry import RetryConfig
from opendecree.async_client import AsyncConfigClient
from opendecree.async_watcher import AsyncConfigWatcher, AsyncWatchedField
from opendecree.client import ConfigClient
from opendecree.errors import (
    AlreadyExistsError,
    ChecksumMismatchError,
    DecreeError,
    IncompatibleServerError,
    InvalidArgumentError,
    LockedError,
    NotFoundError,
    PermissionDeniedError,
    TypeMismatchError,
    UnavailableError,
)
from opendecree.types import Change, ConfigValue, ServerVersion
from opendecree.watcher import ConfigWatcher, WatchedField

__all__ = [
    "PROTO_VERSION",
    "SUPPORTED_SERVER_VERSION",
    "AlreadyExistsError",
    "AsyncConfigClient",
    "AsyncConfigWatcher",
    "AsyncWatchedField",
    "Change",
    "ChecksumMismatchError",
    "ConfigClient",
    "ConfigValue",
    "ConfigWatcher",
    "DecreeError",
    "IncompatibleServerError",
    "InvalidArgumentError",
    "LockedError",
    "NotFoundError",
    "PermissionDeniedError",
    "RetryConfig",
    "ServerVersion",
    "TypeMismatchError",
    "UnavailableError",
    "WatchedField",
    "__version__",
]
