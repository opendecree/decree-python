# Async Client

The same quickstart flow using `AsyncConfigClient` with `async`/`await`.

## What it shows

- `AsyncConfigClient` as an async context manager (`async with`)
- `await client.get()` for non-blocking reads
- `asyncio.gather()` for concurrent reads — faster than sequential
- `await client.set_many()` for atomic multi-writes

## Run

```bash
cd examples
make setup
cd async-client
python main.py
```

## Next

- [live-config](../live-config/) — async watcher with live updates
- [fastapi-integration](../fastapi-integration/) — async client in a web app

## Learn more

- [Python SDK on PyPI](https://pypi.org/project/opendecree/)
