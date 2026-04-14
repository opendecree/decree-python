# Quickstart

The simplest OpenDecree example — connect and read typed config values.

## What it shows

- `ConfigClient` as a context manager (auto-closes channel)
- `get()` with type overloads: `str`, `bool`, `int`, `float`, `timedelta`
- `set()` for writing values

## Run

```bash
cd examples
make setup      # seed schema + tenant
cd quickstart
python main.py
```

## Next

- [async-client](../async-client/) — same thing with `async`/`await`
- [live-config](../live-config/) — watch values change in real time

## Learn more

- [Python SDK on PyPI](https://pypi.org/project/opendecree/)
