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

## Custom interceptors

Pass `interceptors` to inject your own gRPC client interceptors — for logging, metrics,
custom tracing, or anything else that needs to observe or modify outbound RPCs:

```python
import grpc

client = ConfigClient(
    "localhost:9090",
    subject="myapp",
    interceptors=[my_logging_interceptor, my_metrics_interceptor],
)
```

`ConfigClient` accepts `grpc.UnaryUnaryClientInterceptor` / `grpc.UnaryStreamClientInterceptor`
instances; `AsyncConfigClient` accepts `grpc.aio.ClientInterceptor` instances (passed
directly to the `grpc.aio` channel).

On `ConfigClient`, interceptor order (outermost first) is:

1. **OTel** (if `otel=True`)
2. **Your `interceptors`**, in list order
3. **The SDK's internal auth interceptor** (innermost — attaches `subject`/`role`/
   `tenant_id`/token metadata last, closest to the wire)

This means your interceptors see the call before auth metadata is attached, and can inspect
or wrap the call as it travels outward through any later layers (e.g. OTel spans).

On `AsyncConfigClient`, `grpc.aio` doesn't support channel-level interceptor stacking the
same way — auth metadata is attached directly per call rather than via an interceptor.
There, order is simply **OTel first, then your `interceptors`**.

## OpenTelemetry

Pass `otel=True` to trace all RPCs with OpenTelemetry:

```python
client = ConfigClient("localhost:9090", otel=True)
```

Requires the optional extra:

```bash
pip install 'opendecree[otel]'
```

The OTel interceptor is outermost and wraps all other interceptors (including any you pass
via `interceptors`), so every outbound RPC appears as a span in your traces.

## Version compatibility

The SDK can check that the server it's talking to is within its supported version range
(`opendecree.SUPPORTED_SERVER_VERSION`, e.g. `">=0.3.0,<1.0.0"`).

### Automatic check on first call

Pass `check_version=True` to the constructor to run the check lazily before the first RPC:

```python
client = ConfigClient("localhost:9090", subject="myapp", check_version=True)

# Raises IncompatibleServerError here if the server is outside the supported range.
client.get("tenant-id", "payments.fee")
```

The check runs once per client instance and is cached.

### Manual checks

Call `get_server_version()` to fetch (and cache) the server's version and commit:

```python
info = client.get_server_version()
print(info.version)  # e.g. "0.3.1"
print(info.commit)   # server build's git commit hash
```

Call `check_compatibility()` to explicitly raise if the cached (or freshly fetched) server
version is outside the supported range:

```python
from opendecree import IncompatibleServerError

try:
    client.check_compatibility()
except IncompatibleServerError as e:
    print(f"server is incompatible with this SDK: {e}")
```

`IncompatibleServerError` inherits from `DecreeError` — see
[Error handling](#error-handling) below. `AsyncConfigClient` exposes the same
`get_server_version()` and `check_compatibility()` methods — `await` them there.

!!! note "Unparseable versions skip the check"
    If the server reports a version string that isn't valid PEP 440 (e.g. a `"dev"` build),
    the compatibility check is skipped rather than raising.

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
