# Watching for Changes

Live config subscriptions via `ConfigWatcher` and `WatchedField[T]`.

## Basic usage

Create a watcher from a client, register fields, then use it as a context manager:

```python
from opendecree import ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    with client.watch("tenant-id") as watcher:
        fee = watcher.field("payments.fee", float, default=0.01)
        enabled = watcher.field("payments.enabled", bool, default=False)

        print(fee.value)      # current value (float), always fresh
        print(enabled.value)  # current value (bool)
```

The watcher:

1. Loads the current config snapshot on enter
2. Subscribes to changes via gRPC server-streaming
3. Updates field values atomically in a background thread
4. Auto-reconnects with exponential backoff on connection loss
5. Stops the background thread on exit

!!! note "Register fields before starting"
    Call `watcher.field()` before entering the `with watcher:` block. Registering fields
    after `start()` raises `RuntimeError`.

## WatchedField[T]

Each registered field returns a `WatchedField[T]` instance.

### Reading the current value

```python
fee = watcher.field("payments.fee", float, default=0.01)
print(fee.value)  # always the latest value, thread-safe
```

### Boolean checks

`WatchedField` implements `__bool__`, so it works naturally in conditionals:

```python
enabled = watcher.field("payments.enabled", bool, default=False)

if enabled:
    print("Feature is enabled")
```

Falsy values: `False`, `0`, `0.0`, `""`, `None`.

### Callbacks with `on_change`

```python
@fee.on_change
def handle_fee_change(old: float, new: float):
    print(f"Fee changed: {old} -> {new}")
```

Callbacks run on the watcher's background thread. Keep them fast — slow callbacks delay
processing of subsequent field updates.

### Blocking iteration with `changes()`

```python
for change in fee.changes():
    print(f"{change.field_path}: {change.old_value} -> {change.new_value}")
```

The iterator blocks until a change arrives and stops when the watcher exits.

## Supported field types

| Type | Example value | Suggested default |
|------|--------------|-------------------|
| `str` | `"hello"` | `""` |
| `int` | `42` | `0` |
| `float` | `3.14` | `0.0` |
| `bool` | `True` | `False` |
| `timedelta` | `timedelta(seconds=30)` | `timedelta()` |

## Auto-reconnect

If the gRPC stream drops (server restart, network blip), the watcher reconnects automatically
with exponential backoff:

- Initial delay: 1 second
- Maximum delay: 30 seconds
- Multiplier: 2×
- Jitter: 0.5×–1.5×

During reconnection, `field.value` returns the last known value. No action needed from your code.

## Multiple tenants

Each watcher is scoped to one tenant. Use multiple watchers for multiple tenants:

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    watcher_a = client.watch("tenant-a")
    watcher_b = client.watch("tenant-b")
    fee_a = watcher_a.field("payments.fee", float, default=0.01)
    fee_b = watcher_b.field("payments.fee", float, default=0.01)

    with watcher_a, watcher_b:
        print(fee_a.value, fee_b.value)
```

## Async watcher

`AsyncConfigClient` provides an equivalent `AsyncConfigWatcher`:

```python
from opendecree import AsyncConfigClient

async with AsyncConfigClient("localhost:9090", subject="myapp") as client:
    async with client.watch("tenant-id") as watcher:
        fee = watcher.field("payments.fee", float, default=0.01)
        print(fee.value)

        # Async iteration
        async for change in fee.changes():
            print(f"{change.old_value} -> {change.new_value}")
```

Callbacks work the same as the sync watcher — they are plain functions, not coroutines.

## Fork safety

gRPC channels are **not fork-safe**. Do not create a `ConfigClient` before calling `os.fork()`.
This includes implicit forks from `multiprocessing.Pool`, Gunicorn workers, and similar frameworks.

After a fork, the child inherits the open channel in an undefined state, which can cause hangs,
crashes, or silent data corruption.

**Fix: create the client inside the worker process.**

```python
from multiprocessing import Pool
from opendecree import ConfigClient

def worker(tenant_id: str) -> str:
    with ConfigClient("localhost:9090", subject="myapp") as client:
        return client.get(tenant_id, "payments.fee")

with Pool(4) as pool:
    results = pool.map(worker, ["tenant-a", "tenant-b"])
```

If you must use `multiprocessing`, prefer the `spawn` start method (default on macOS and Windows):

```python
import multiprocessing
multiprocessing.set_start_method("spawn")
```

The same restriction applies to `ConfigWatcher` — the background thread does not survive a fork.
Stop the watcher before forking, or start it inside the child process.
