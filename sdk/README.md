# OpenDecree Python SDK

[![CI](https://github.com/opendecree/decree-python/actions/workflows/ci.yml/badge.svg)](https://github.com/opendecree/decree-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/opendecree)](https://pypi.org/project/opendecree/)
[![Python](https://img.shields.io/pypi/pyversions/opendecree)](https://pypi.org/project/opendecree/)
[![Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen)](https://github.com/opendecree/decree-python)
[![License](https://img.shields.io/github/license/opendecree/decree-python)](https://github.com/opendecree/decree-python/blob/main/LICENSE)

Python SDK for [OpenDecree](https://github.com/opendecree/decree) — schema-driven configuration management.

> **Alpha** — This SDK is under active development. APIs and behavior may change without notice between versions.

## Install

```bash
pip install opendecree
```

## Quick Start

```python
from opendecree import ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    # Get config values (default: string)
    fee = client.get("tenant-id", "payments.fee")

    # Typed gets via overload
    retries = client.get("tenant-id", "payments.retries", int)
    enabled = client.get("tenant-id", "payments.enabled", bool)

    # Set values
    client.set("tenant-id", "payments.fee", "0.5%")
```

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

## Documentation

Full documentation, including guides and the API reference, is published at
**[opendecree.github.io/decree-python](https://opendecree.github.io/decree-python)**:

- [Connecting](https://opendecree.github.io/decree-python/guide/connect/) — client options (auth, TLS, retry, timeouts, error handling)
- [Watching](https://opendecree.github.io/decree-python/guide/watch/) — live subscriptions and change patterns
- [Async Usage](https://opendecree.github.io/decree-python/guide/async/) — async client and watcher
- [API Reference](https://opendecree.github.io/decree-python/api/) — full auto-generated API docs

For detailed concepts (schemas, typed values, versioning, auth), see the [main OpenDecree docs](https://github.com/opendecree/decree).

## Typing

This package is fully typed. It ships a `py.typed` marker and `.pyi` stub files for the generated gRPC layer, so mypy, pyright, and similar tools work without additional configuration.

## Requirements

- Python 3.11+
- A running OpenDecree server (v0.3.0+)

## License

Apache License 2.0 — see [LICENSE](https://github.com/opendecree/decree-python/blob/main/LICENSE).
