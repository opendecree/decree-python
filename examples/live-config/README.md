# Live Config

Watch configuration values change in real time using `ConfigWatcher`.

## What it shows

- `client.watch()` to create a watcher
- `watcher.field()` to register typed fields with defaults
- `@field.on_change` decorator for reactive callbacks
- `field.changes()` blocking iterator for change events
- `field.value` for reading the current value at any time

## Run

```bash
cd examples
make setup
cd live-config
python main.py
```

Then in another terminal:
```bash
decree config set <tenant-id> server.rate_limit 500
```

## Next

- [fastapi-integration](../fastapi-integration/) — watcher in a web server
- [error-handling](../error-handling/) — retry, nullable, error hierarchy

## Learn more

- [Python SDK on PyPI](https://pypi.org/project/opendecree/)
