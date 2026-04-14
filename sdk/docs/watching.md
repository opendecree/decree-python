# Watching for Changes

Live config subscriptions via `ConfigWatcher` and `WatchedField[T]`.

## Basic usage

Create a watcher from a client. Register fields before entering the context manager:

```python
from opendecree import ConfigClient

with ConfigClient("localhost:9090", subject="myapp") as client:
    with client.watch("tenant-id") as watcher:
        fee = watcher.field("payments.fee", float, default=0.01)
        enabled = watcher.field("payments.enabled", bool, default=False)

        # Read current values
        print(fee.value)      # 0.025 (float, always fresh)
        print(enabled.value)  # True (bool)
```

The watcher:
1. Loads the current config snapshot on enter
2. Subscribes to changes via gRPC server-streaming
3. Updates field values atomically in the background
4. Auto-reconnects with exponential backoff on connection loss
5. Stops the background thread on exit

## WatchedField[T]

Each registered field returns a `WatchedField[T]` with:

### `.value` — current value

```python
fee = watcher.field("payments.fee", float, default=0.01)
print(fee.value)  # always the latest value, thread-safe
```

### `__bool__` — natural conditionals

```python
enabled = watcher.field("payments.enabled", bool, default=False)

if enabled:  # uses __bool__, checks the live value
    print("Feature is enabled")
```

Falsy values: `False`, `0`, `0.0`, `""`, `None`.

### `on_change` — callbacks

```python
@fee.on_change
def handle_fee_change(old: float, new: float):
    print(f"Fee changed: {old} -> {new}")
```

Callbacks run on the watcher's background thread. Keep them fast — slow callbacks block other field updates.

### `changes()` — blocking iterator

```python
for change in fee.changes():
    print(f"{change.field_path}: {change.old_value} -> {change.new_value}")
```

The iterator blocks until a change arrives. It stops when the watcher exits.

## Supported types

| Type | Example | Default suggestion |
|------|---------|-------------------|
| `str` | `"hello"` | `""` |
| `int` | `42` | `0` |
| `float` | `3.14` | `0.0` |
| `bool` | `True` | `False` |
| `timedelta` | `timedelta(seconds=30)` | `timedelta()` |

## Lifecycle

Register fields **before** the `with` block. Fields cannot be added after the watcher starts:

```python
watcher = client.watch("tenant-id")

# Register fields first
fee = watcher.field("payments.fee", float, default=0.01)

# Then start
with watcher:
    print(fee.value)
```

Or equivalently:

```python
with client.watch("tenant-id") as watcher:
    fee = watcher.field("payments.fee", float, default=0.01)
    # ...
```

Wait — fields must be registered **before** `start()`. When using the two-line form, register between `watch()` and `with`. When using the one-line form, the watcher loads a snapshot on enter, so fields registered inside the `with` block will get their initial values from the snapshot.

## Auto-reconnect

If the gRPC stream drops (server restart, network issue), the watcher automatically reconnects with exponential backoff:

- Initial delay: 1 second
- Maximum delay: 30 seconds
- Multiplier: 2x
- Jitter: 0.5x–1.5x

During reconnection, `field.value` returns the last known value. No action needed from your code.

## Multiple watchers

You can create multiple watchers for different tenants:

```python
with ConfigClient("localhost:9090", subject="myapp") as client:
    with client.watch("tenant-a") as watcher_a:
        with client.watch("tenant-b") as watcher_b:
            fee_a = watcher_a.field("payments.fee", float, default=0.01)
            fee_b = watcher_b.field("payments.fee", float, default=0.01)
            # Both update independently
```

## Next steps

- [Async Usage](async.md) — async watcher with `async for` iteration
- [Configuration](configuration.md) — client options (auth, TLS, retry)
