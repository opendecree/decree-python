# Quick Start

Get up and running with the OpenDecree Python SDK in under 5 minutes.

## Install

```bash
pip install opendecree
```

## Prerequisites

You need a running OpenDecree server (v0.3.0+). For local development:

```bash
# In the decree repo
docker compose up -d
```

The server defaults to `localhost:9090` with no authentication required.

## Read a config value

```python
from opendecree import ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    fee = client.get("tenant-id", "payments.fee")
    print(fee)  # "0.5%"
```

The `with` block manages the gRPC connection — it opens on enter and closes on exit.

## Typed reads

Pass a type argument to `get()` for automatic conversion:

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    retries = client.get("tenant-id", "payments.retries", int)       # → int
    enabled = client.get("tenant-id", "payments.enabled", bool)      # → bool
    rate    = client.get("tenant-id", "payments.fee_rate", float)    # → float
```

Supported types: `str` (default), `int`, `float`, `bool`, `timedelta`.

## Write a value

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    client.set("tenant-id", "payments.fee", "0.5%")

    # Bulk writes
    client.set_many("tenant-id", {"a": "1", "b": "2"}, description="batch update")

    # Set to null
    client.set_null("tenant-id", "payments.fee")
```

## Watch for changes

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    with client.watch("tenant-id") as watcher:
        fee = watcher.field("payments.fee", float, default=0.01)

        print(fee.value)  # current value, always fresh

        @fee.on_change
        def on_fee_change(old: float, new: float):
            print(f"Fee changed: {old} -> {new}")
```

See [Watching](watching.md) for more patterns.

## Async

All APIs have async equivalents:

```python
from opendecree import AsyncConfigClient

async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    fee = await client.get("tenant-id", "payments.fee")
    retries = await client.get("tenant-id", "payments.retries", int)
```

See [Async Usage](async.md) for the full async API.

## Error handling

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

## Next steps

- [Configuration](configuration.md) — all client options (auth, TLS, retry, timeouts)
- [Watching](watching.md) — live subscriptions and change patterns
- [Async Usage](async.md) — async client and watcher
- [OpenDecree concepts](https://github.com/zeevdr/decree) — schemas, typed values, versioning
