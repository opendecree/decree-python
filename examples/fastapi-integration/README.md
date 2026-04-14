# FastAPI Integration

Live configuration in a FastAPI web server using `AsyncConfigWatcher` as a lifespan dependency.

## What it shows

- `AsyncConfigWatcher` started/stopped via FastAPI lifespan
- `field.value` in route handlers — always fresh, no polling
- Feature flags and server config as separate endpoints

## Run

```bash
cd examples
make setup
pip install fastapi uvicorn
cd fastapi-integration
python main.py
```

Then:
```bash
curl http://localhost:8000/config
curl http://localhost:8000/features
```

Change a value and refresh:
```bash
decree config set <tenant-id> features.dark_mode false
curl http://localhost:8000/features
```

## Dependencies

This example requires `fastapi` and `uvicorn` in addition to `opendecree`:

```bash
pip install opendecree fastapi uvicorn
```

## Next

- [error-handling](../error-handling/) — retry, nullable, error hierarchy

## Learn more

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Python SDK on PyPI](https://pypi.org/project/opendecree/)
