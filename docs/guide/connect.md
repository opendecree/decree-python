# Connecting

How to create and configure `ConfigClient` and `AsyncConfigClient`.

## Basic connection

```python
from opendecree import ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    val = client.get("tenant-id", "payments.fee")
```

Use `ConfigClient` as a context manager — the gRPC channel opens on enter and closes on exit.
For async code, use `AsyncConfigClient` with `async with`.

## Constructor options

```python
ConfigClient(
    target,                          # gRPC server address (host:port)
    *,
    subject: str | None = None,      # x-subject metadata header
    role: str = "superadmin",        # x-role metadata header
    tenant_id: str | None = None,    # x-tenant-id metadata header
    token: str | None = None,        # Bearer token (JWT mode)
    insecure: bool = True,           # plaintext — default for local dev
    credentials = None,              # grpc.ChannelCredentials for TLS
    timeout: float = 10.0,           # per-RPC timeout in seconds
    retry: RetryConfig | None = ..., # retry config (None to disable)
    check_version: bool = False,     # verify server version on first call
    otel: bool = False,              # wire OpenTelemetry interceptor
)
```

`AsyncConfigClient` accepts the same options.

## Authentication

### Metadata headers (default)

The server reads identity from gRPC metadata headers. No tokens required.

```python
client = ConfigClient(
    "localhost:9090",
    subject="myapp",       # who is making the request
    role="superadmin",     # role (default: superadmin)
)
```

For non-superadmin roles, include `tenant_id` to scope access:

```python
client = ConfigClient(
    "localhost:9090",
    subject="alice",
    role="admin",
    tenant_id="tenant-123",
)
```

To allow access to multiple tenants, pass a comma-separated list:

```python
client = ConfigClient(
    "localhost:9090",
    subject="alice",
    role="admin",
    tenant_id="tenant-123,tenant-456",
)
```

### Bearer token (JWT mode)

If the server has JWT auth enabled, pass a token instead:

```python
client = ConfigClient(
    "localhost:9090",
    token="eyJhbGciOiJS...",
)
```

When `token` is set, `subject`, `role`, and `tenant_id` are ignored — access is
determined by the JWT `tenant_ids` claim.

!!! warning "TLS required in production"
    Sending a bearer token over a plaintext channel will raise a `UserWarning`. Use
    `insecure=False` with proper TLS credentials when running in production.

## TLS

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

Transient errors are retried automatically with exponential backoff and jitter. The default
policy retries up to 3 times on `UNAVAILABLE`, `DEADLINE_EXCEEDED`, and `RESOURCE_EXHAUSTED`.

```python
from opendecree import ConfigClient, RetryConfig

client = ConfigClient(
    "localhost:9090",
    retry=RetryConfig(
        max_attempts=5,
        initial_backoff=0.2,
        max_backoff=10.0,
        multiplier=2.0,
    ),
)

# Disable retry entirely
client = ConfigClient("localhost:9090", retry=None)
```

**Reads** (`get`, `get_all`) retry on both `UNAVAILABLE` and `DEADLINE_EXCEEDED` — reads
are idempotent.

**Writes** (`set`, `set_many`, `set_null`) retry only on `UNAVAILABLE` by default, because
`DEADLINE_EXCEEDED` does not guarantee the server hasn't already applied the write. To opt
a write into `DEADLINE_EXCEEDED` retry, pass an `idempotency_key`:

```python
import uuid

client.set(
    "tenant-id",
    "feature_flags.dark_mode",
    "true",
    idempotency_key=str(uuid.uuid4()),
)
```

Only use `idempotency_key` when a duplicate apply is harmless for your use case.

## Timeouts

The `timeout` parameter sets the default per-RPC deadline in seconds (default: 10):

```python
client = ConfigClient("localhost:9090", timeout=30.0)
```

## OpenTelemetry

Pass `otel=True` to trace all RPCs with OpenTelemetry:

```python
client = ConfigClient("localhost:9090", otel=True)
```

Requires the optional extra:

```bash
pip install 'opendecree[otel]'
```

The OTel interceptor is outermost and wraps all other interceptors, so every outbound RPC
appears as a span in your traces.

## Error handling

All exceptions inherit from `DecreeError`:

| Exception | gRPC Code | When |
|-----------|-----------|------|
| `NotFoundError` | NOT_FOUND | Field or tenant does not exist |
| `AlreadyExistsError` | ALREADY_EXISTS | Duplicate create |
| `InvalidArgumentError` | INVALID_ARGUMENT | Bad request data |
| `LockedError` | FAILED_PRECONDITION | Field is locked |
| `ChecksumMismatchError` | ABORTED | Optimistic concurrency conflict |
| `PermissionDeniedError` | PERMISSION_DENIED / UNAUTHENTICATED | Auth failure |
| `UnavailableError` | UNAVAILABLE | Server unreachable |
| `TypeMismatchError` | — | Wrong type in typed getter |
| `IncompatibleServerError` | — | Server version mismatch |
| `TimeoutError` | DEADLINE_EXCEEDED | RPC deadline exceeded |

```python
from opendecree import ConfigClient, NotFoundError, LockedError

with ConfigClient("localhost:9090", subject="myapp") as client:
    try:
        val = client.get("tenant-id", "nonexistent.field")
    except NotFoundError:
        print("Field not found")
    except LockedError:
        print("Field is locked")
```
