# OpenDecree Python SDK Examples

Runnable examples demonstrating the OpenDecree Python SDK.

## Setup

Start the decree server and seed example data:

```bash
# From this directory
make setup
```

This starts PostgreSQL, Redis, and the decree server via Docker Compose,
then creates an example schema, tenant, and initial config values.

The tenant ID is written to `.tenant-id` — examples read it automatically.

## Prerequisites

```bash
pip install opendecree
```

For the FastAPI example, also install:
```bash
pip install fastapi uvicorn
```

## Examples

| Example | What it shows | Server required |
|---------|--------------|-----------------|
| [quickstart](quickstart/) | Context manager, typed `get()`, `set()` | Yes |
| [async-client](async-client/) | `async with`, `await`, `asyncio.gather()` | Yes |
| [live-config](live-config/) | `ConfigWatcher`, `@on_change` decorator, `changes()` iterator | Yes |
| [fastapi-integration](fastapi-integration/) | `AsyncConfigWatcher` as FastAPI lifespan dependency | Yes |
| [error-handling](error-handling/) | `RetryConfig`, `nullable=True`, error hierarchy | Yes |

## Running an example

```bash
# After make setup:
cd quickstart
python main.py
```

Or run all examples as tests:

```bash
make test
```

## Teardown

```bash
make down
```

## Learn more

- [Python SDK on PyPI](https://pypi.org/project/opendecree/)
- [OpenDecree docs](https://github.com/zeevdr/decree)
