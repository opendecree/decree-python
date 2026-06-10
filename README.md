# OpenDecree Python SDK

[![CI](https://github.com/opendecree/decree-python/actions/workflows/ci.yml/badge.svg)](https://github.com/opendecree/decree-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/opendecree)](https://pypi.org/project/opendecree/)
[![License](https://img.shields.io/github/license/opendecree/decree-python)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-opendecree.github.io-teal)](https://opendecree.github.io/decree-python)
[![codecov](https://codecov.io/gh/opendecree/decree-python/graph/badge.svg)](https://codecov.io/gh/opendecree/decree-python)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/opendecree/decree-python)

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

> **Fork safety:** gRPC channels are not fork-safe. Create `ConfigClient` (and start any watcher)
> *after* forking — not before. See [Fork safety](https://opendecree.github.io/decree-python/guide/watch/#fork-safety) for details.

## Async

```python
from opendecree import AsyncConfigClient

async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    val = await client.get("tenant-id", "payments.fee")
    retries = await client.get("tenant-id", "payments.retries", int)
```

## Examples

Runnable examples in the [`examples/`](examples/) directory:

| Example | What it shows |
|---------|--------------|
| [quickstart](examples/quickstart/) | Context manager, typed `get()`, `set()` |
| [async-client](examples/async-client/) | `async with`, `await`, `asyncio.gather()` |
| [live-config](examples/live-config/) | `ConfigWatcher`, `@on_change`, `changes()` |
| [fastapi-integration](examples/fastapi-integration/) | Async watcher as FastAPI lifespan dependency |
| [error-handling](examples/error-handling/) | `RetryConfig`, `nullable=True`, error hierarchy |

## Documentation

Full documentation, including guides and the API reference, is published at
**[opendecree.github.io/decree-python](https://opendecree.github.io/decree-python)**:

- [Connecting](https://opendecree.github.io/decree-python/guide/connect/) — client options (auth, TLS, retry, timeouts, error handling)
- [Watching](https://opendecree.github.io/decree-python/guide/watch/) — live subscriptions and change patterns
- [Async Usage](https://opendecree.github.io/decree-python/guide/async/) — async client and watcher
- [API Reference](https://opendecree.github.io/decree-python/api/) — full auto-generated API docs

For detailed concepts (schemas, typed values, versioning, auth), see the [main OpenDecree docs](https://github.com/opendecree/decree).

## Supply Chain Security

Each release wheel is signed with [Sigstore](https://www.sigstore.dev/) via the GitHub Actions
OIDC identity. Attestations are visible on the [PyPI project page](https://pypi.org/project/opendecree/).

To verify a downloaded wheel locally:

```bash
pip download opendecree --no-deps
gh attestation verify opendecree-*.whl --repo opendecree/decree-python
```

> See [decree#16](https://github.com/opendecree/decree/issues/16) for the org-wide attestation plan.

## Requirements

- Python 3.11+
- A running OpenDecree server (v0.8.0 – v0.x, pre-1.0)

## Questions?

Head to [OpenDecree Discussions](https://github.com/orgs/opendecree/discussions) — our community hub covers all OpenDecree repos.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
