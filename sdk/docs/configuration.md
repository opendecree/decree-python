# Configuration

All client options for `ConfigClient` and `AsyncConfigClient`.

## Constructor

```python
ConfigClient(
    target="localhost:9090",     # gRPC server address (host:port)
    *,
    # Auth (metadata headers)
    subject: str | None = None,  # x-subject header
    role: str = "superadmin",    # x-role header
    tenant_id: str | None = None,# x-tenant-id header
    token: str | None = None,    # Bearer token (alternative to metadata)

    # Connection
    insecure: bool = True,       # plaintext (no TLS) — default for dev
    credentials: grpc.ChannelCredentials | None = None,  # TLS credentials

    # Behavior
    timeout: float = 10.0,       # default RPC timeout in seconds
    retry: RetryConfig | None = RetryConfig(),  # retry config (None to disable)
)
```

`AsyncConfigClient` accepts the same options.

## Authentication

OpenDecree supports two auth modes:

### Metadata headers (default)

The server reads identity from gRPC metadata headers. No JWT or tokens needed.

```python
client = ConfigClient(
    "localhost:9090",
    subject="myapp",           # who is making the request
    role="superadmin",         # role (default: superadmin)
    tenant_id="tenant-123",   # optional: default tenant for all calls
)
```

Non-superadmin roles require a `tenant_id`. For users with access to multiple tenants,
pass a comma-separated list:

```python
client = ConfigClient(
    "localhost:9090",
    subject="alice",
    role="admin",
    tenant_id="tenant-123,tenant-456",  # access to multiple tenants
)
```

Each API call specifies which tenant to operate on via the `tenant_id` parameter.
The server validates that the requested tenant is in the caller's allowed list.

### Bearer token

For JWT-enabled servers, pass a token instead:

```python
client = ConfigClient(
    "localhost:9090",
    token="eyJhbGciOiJS...",
)
```

The JWT `tenant_ids` claim (array) determines which tenants the caller can access.
When a `token` is provided, metadata headers (`subject`, `role`, `tenant_id`) are ignored.

## TLS

By default, clients connect without TLS (`insecure=True`). For production:

```python
import grpc

creds = grpc.ssl_channel_credentials(
    root_certificates=open("ca.pem", "rb").read(),
)

client = ConfigClient(
    "decree.example.com:443",
    insecure=False,
    credentials=creds,
    subject="myapp",
)
```

## Retry

Transient gRPC errors are retried automatically with exponential backoff and jitter.

```python
from opendecree import ConfigClient, RetryConfig

# Custom retry settings
client = ConfigClient(
    "localhost:9090",
    retry=RetryConfig(
        max_attempts=5,
        initial_backoff=0.2,     # seconds
        max_backoff=10.0,        # seconds
        multiplier=2.0,
        retryable_codes=(
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
        ),
    ),
)

# Disable retry
client = ConfigClient("localhost:9090", retry=None)
```

Default: 3 attempts, 0.1s initial backoff, 5s max, 2x multiplier.

### Read vs. write retry semantics

**Reads** (`get`, `get_all`) retry on both `UNAVAILABLE` and `DEADLINE_EXCEEDED` — reads are
idempotent so a duplicate is always safe.

**Writes** (`set`, `set_many`, `set_null`) retry only on `UNAVAILABLE` by default.
`DEADLINE_EXCEEDED` is excluded because the server may have already applied the write before the
client timed out — retrying without coordination would double-apply the change (duplicate audit
log entry, version bump).

To opt a write into `DEADLINE_EXCEEDED` retry, pass an `idempotency_key`:

```python
import uuid

# Only use this when a duplicate apply is harmless for your use case.
client.set(
    "tenant-id",
    "feature_flags.dark_mode",
    "true",
    idempotency_key=str(uuid.uuid4()),  # unique per request
)
```

Use `idempotency_key` only when the write is genuinely safe to apply more than once — for example,
setting a field to a known constant value.

## Timeouts

The `timeout` parameter sets the default per-RPC deadline in seconds:

```python
client = ConfigClient("localhost:9090", timeout=30.0)
```

Default: 10 seconds.

## Server version

Fetch the server version explicitly with `get_server_version()`. The value is cached after the
first call.

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    version = client.get_server_version()
    print(version.version)
```

For async clients, await the same method:

```python
async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    version = await client.get_server_version()
    print(version.version)
```

The sync-only `server_version` property is deprecated for one release. Use
`get_server_version()` for both sync and async clients.

## Error types

All exceptions inherit from `DecreeError`:

| Exception | gRPC Code | When |
|-----------|-----------|------|
| `NotFoundError` | NOT_FOUND | Field or tenant doesn't exist |
| `AlreadyExistsError` | ALREADY_EXISTS | Duplicate create |
| `InvalidArgumentError` | INVALID_ARGUMENT | Bad request data |
| `LockedError` | FAILED_PRECONDITION | Field is locked |
| `ChecksumMismatchError` | ABORTED | Optimistic concurrency conflict |
| `PermissionDeniedError` | PERMISSION_DENIED / UNAUTHENTICATED | Auth failure |
| `UnavailableError` | UNAVAILABLE | Server unreachable |
| `TypeMismatchError` | — | Wrong type passed to typed getter |
| `IncompatibleServerError` | — | Server version mismatch |

## Return types

All return types are frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class ConfigValue:
    field_path: str
    value: str
    checksum: str
    description: str

@dataclass(frozen=True, slots=True)
class Change:
    field_path: str
    old_value: str | None
    new_value: str | None
    version: int
    changed_by: str
```
