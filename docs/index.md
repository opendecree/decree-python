# OpenDecree Python SDK

[![CI](https://github.com/opendecree/decree-python/actions/workflows/ci.yml/badge.svg)](https://github.com/opendecree/decree-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/opendecree)](https://pypi.org/project/opendecree/)
[![Python](https://img.shields.io/pypi/pyversions/opendecree)](https://pypi.org/project/opendecree/)
[![License](https://img.shields.io/github/license/opendecree/decree-python)](https://github.com/opendecree/decree-python/blob/main/LICENSE)

Python SDK for [OpenDecree](https://github.com/opendecree/decree) — schema-driven configuration management.

!!! warning "Alpha"
    This SDK is under active development. APIs and behavior may change without notice between versions.

## Install

```bash
pip install opendecree
```

## Requirements

- Python 3.11+
- A running OpenDecree server (v0.3.0+)

## Quick Start

```python
from opendecree import ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    # Get a config value (returns str by default)
    fee = client.get("tenant-id", "payments.fee")

    # Typed reads — pass the target type
    retries = client.get("tenant-id", "payments.retries", int)
    enabled = client.get("tenant-id", "payments.enabled", bool)

    # Write a value
    client.set("tenant-id", "payments.fee", "0.5%")
```

The `with` block manages the gRPC channel lifecycle — it opens on enter and closes on exit.

## Watch for Changes

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    with client.watch("tenant-id") as watcher:
        fee = watcher.field("payments.fee", float, default=0.01)
        enabled = watcher.field("payments.enabled", bool, default=False)

        if enabled:
            print(f"Current fee: {fee.value}")

        @fee.on_change
        def on_fee_change(old: float, new: float):
            print(f"Fee changed: {old} -> {new}")
```

## Async

```python
from opendecree import AsyncConfigClient

async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    val = await client.get("tenant-id", "payments.fee")
    retries = await client.get("tenant-id", "payments.retries", int)
```

## Examples

Runnable examples are available in the [`examples/`](https://github.com/opendecree/decree-python/tree/main/examples) directory of the repository.

| Example | What it shows |
|---------|--------------|
| [quickstart](https://github.com/opendecree/decree-python/tree/main/examples/quickstart) | Context manager, typed `get()`, `set()` |
| [async-client](https://github.com/opendecree/decree-python/tree/main/examples/async-client) | `async with`, `await`, `asyncio.gather()` |
| [live-config](https://github.com/opendecree/decree-python/tree/main/examples/live-config) | `ConfigWatcher`, `@on_change`, `changes()` |
| [fastapi-integration](https://github.com/opendecree/decree-python/tree/main/examples/fastapi-integration) | Async watcher as FastAPI lifespan dependency |
| [error-handling](https://github.com/opendecree/decree-python/tree/main/examples/error-handling) | `RetryConfig`, `nullable=True`, error hierarchy |

## Next Steps

- [Connecting](guide/connect.md) — all client options (auth, TLS, retry, timeouts)
- [Watching](guide/watch.md) — live subscriptions and change patterns
- [Async Usage](guide/async.md) — async client and watcher
- [API Reference](api/index.md) — full auto-generated API docs

For server concepts (schemas, typed values, versioning, auth), see the [main OpenDecree docs](https://github.com/opendecree/decree).
