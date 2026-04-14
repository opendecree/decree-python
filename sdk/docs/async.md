# Async Usage

The SDK provides async equivalents for all sync APIs, built on `grpc.aio`.

## AsyncConfigClient

```python
from opendecree import AsyncConfigClient

async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    # Typed gets (same overload pattern as sync)
    fee = await client.get("tenant-id", "payments.fee")              # → str
    retries = await client.get("tenant-id", "payments.retries", int) # → int
    enabled = await client.get("tenant-id", "payments.enabled", bool)# → bool

    # Get all config
    all_config = await client.get_all("tenant-id")  # → dict[str, str]

    # Writes
    await client.set("tenant-id", "payments.fee", "0.5%")
    await client.set_many("tenant-id", {"a": "1", "b": "2"})
    await client.set_null("tenant-id", "payments.fee")
```

Same constructor options as `ConfigClient` — see [Configuration](configuration.md).

## AsyncConfigWatcher

```python
from opendecree import AsyncConfigClient

async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    async with client.watch("tenant-id") as watcher:
        fee = watcher.field("payments.fee", float, default=0.01)
        enabled = watcher.field("payments.enabled", bool, default=False)

        # .value works the same
        print(fee.value)

        # __bool__ works the same
        if enabled:
            print("enabled")
```

### Async change iteration

Use `async for` instead of `for`:

```python
async with client.watch("tenant-id") as watcher:
    fee = watcher.field("payments.fee", float, default=0.01)

    async for change in fee.changes():
        print(f"{change.old_value} -> {change.new_value}")
```

### Callbacks

Callbacks work the same as the sync watcher — they are plain functions (not coroutines):

```python
@fee.on_change
def handle_change(old: float, new: float):
    print(f"Fee changed: {old} -> {new}")
```

## Differences from sync

| Aspect | Sync | Async |
|--------|------|-------|
| Client | `ConfigClient` | `AsyncConfigClient` |
| Context manager | `with` | `async with` |
| Methods | `client.get(...)` | `await client.get(...)` |
| Watcher | `ConfigWatcher` | `AsyncConfigWatcher` |
| Change iterator | `for change in field.changes()` | `async for change in field.changes()` |
| Background work | Thread | asyncio Task |
| Callbacks | Same (plain functions) | Same (plain functions) |

The public API is otherwise identical — same constructor options, same `get()` overloads, same `WatchedField[T]` interface.

## When to use async

Use the async API when:
- Your application already uses asyncio (FastAPI, aiohttp, etc.)
- You need to manage many concurrent connections efficiently

Use the sync API when:
- Your application is synchronous (Flask, Django, scripts)
- Simplicity matters more than concurrency

Both APIs are equally capable and tested.
