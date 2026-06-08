# Types and Values

How OpenDecree's schema field types map to Python types, and how to read and write
typed values — including atomic multi-field writes with `set_many`.

## Go-to-Python type mapping

The server stores every config value as a string and validates it against a
schema-defined field type. The SDK converts between that wire representation and
native Python types at the boundary — both when reading with a typed `get()` and
(for `watch()`) when registering a field.

| Schema field type | Python type | Notes |
|-------------------|-------------|-------|
| `integer` | `int` | Decimal string, e.g. `"42"`, `"-1"` |
| `number` | `float` | Decimal string, e.g. `"3.14"`, `"-99.9"` |
| `string` | `str` | Free-form text |
| `bool` | `bool` | `"true"`/`"1"` → `True`, `"false"`/`"0"` → `False` |
| `time` | `datetime` | RFC 3339 string, parsed with `datetime.fromisoformat` |
| `duration` | `timedelta` | Go-style duration string, e.g. `"24h"`, `"30m"`, `"500ms"`, `"1h30m"` |
| `url` | `str` (`opendecree.URL`) | `URL` is a type alias for `str` — semantically distinct, converted identically |
| `json` | `dict` / `list` | JSON-decoded; the result must match the requested container type |

`opendecree.URL` exists so you can express intent in your own type annotations
(e.g. `watcher.field("webhooks.endpoint", URL)`) — at runtime it behaves exactly
like `str`.

## Supported `get()` types

Pass the target type as the third positional argument to `get()` to receive a
converted value instead of the raw string:

```python
from datetime import datetime, timedelta

from opendecree import URL, ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    name: str = client.get("tenant-id", "service.name")
    retries: int = client.get("tenant-id", "payments.retries", int)
    fee: float = client.get("tenant-id", "payments.fee", float)
    enabled: bool = client.get("tenant-id", "payments.enabled", bool)
    deploy_at: datetime = client.get("tenant-id", "release.deploy_at", datetime)
    timeout: timedelta = client.get("tenant-id", "payments.timeout", timedelta)
    webhook: URL = client.get("tenant-id", "webhooks.endpoint", URL)
    metadata: dict = client.get("tenant-id", "service.metadata", dict)
    tags: list = client.get("tenant-id", "service.tags", list)
```

Supported types: `str` (default), `int`, `float`, `bool`, `datetime`, `timedelta`,
`dict`, `list`. `URL` is an alias for `str`.

For `dict`/`list`, the SDK JSON-decodes the raw value and checks that the decoded
result is an instance of the requested container type — decoding `{"a": 1}` as
`list` (or `[1, 2]` as `dict`) raises `TypeMismatchError`.

```python
try:
    metadata = client.get("tenant-id", "service.metadata", dict)
except TypeMismatchError:
    print("value is not a JSON object")
```

`AsyncConfigClient.get()` supports the same set of types — `await` the call instead.

### Nullable reads

Pass `nullable=True` to get `None` back for unset/null fields instead of raising
`NotFoundError`:

```python
description = client.get("tenant-id", "service.description", str, nullable=True)
if description is None:
    print("not set")
```

## Writing values

`set`, `set_many`, and `set_null` all send the `value` argument as a **string**
on the wire — there's no separate typed-write API. The server validates the
written value against the field's declared schema type.

!!! warning "Currently string-typed fields only"
    The SDK always sends writes as a string-valued `TypedValue`. The server
    requires the value's wire representation to match the field's declared type
    exactly (no coercion), so `set`/`set_many`/`set_null` only work against
    `string`-typed fields today — writing to a `bool`, `integer`, `number`,
    `time`, `duration`, `url`, or `json` field raises `InvalidArgumentError`
    (e.g. `"expected bool value"`). This is a known SDK limitation, not
    something to work around in your own code.

```python
client.set("tenant-id", "service.name", "checkout-api")
client.set("tenant-id", "payments.currency", "EUR")
```

## Bulk writes with `set_many` and `FieldUpdate`

`set_many` atomically applies a batch of field updates in a single version — either
all of them succeed, or none do. Each update is a `FieldUpdate`:

```python
@dataclass(frozen=True, slots=True)
class FieldUpdate:
    field_path: str
    value: str
    expected_checksum: str | None = None
    value_description: str | None = None
```

| Field | Type | Meaning |
|-------|------|---------|
| `field_path` | `str` | Dot-separated field path, e.g. `"payments.fee"` |
| `value` | `str` | The value as a string (same wire format as `set`) |
| `expected_checksum` | `str \| None` | Optional per-field optimistic-concurrency check — the whole batch is rejected with `ChecksumMismatchError` if any field's current checksum doesn't match |
| `value_description` | `str \| None` | Optional description stored with this specific value |

```python
from opendecree import ConfigClient, FieldUpdate

with ConfigClient("localhost:9090", subject="myapp") as client:
    client.set_many(
        "tenant-id",
        [
            FieldUpdate("service.name", "checkout-api"),
            FieldUpdate("payments.currency", "EUR"),
            FieldUpdate(
                "service.region",
                "us-east-1",
                expected_checksum="abc123",
                value_description="moved for latency",
            ),
        ],
        description="tune service settings",
    )
```

Like `set`, `set_many` is currently limited to `string`-typed fields — see the
warning above.

`set_many` accepts the same `description` and `idempotency_key` keyword arguments
as `set` (see [Connecting → Retry](connect.md#retry) for retry/idempotency
semantics — bulk writes are subject to the same write-safety rules).

`AsyncConfigClient.set_many` works identically with `await`.

## `watch()` field types

`ConfigWatcher.field()` and `AsyncConfigWatcher.field()` support a smaller set of
types than `get()` — see [Watching → Supported field types](watch.md#supported-field-types)
for the list and suggested defaults.
