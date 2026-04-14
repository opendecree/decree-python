# Error Handling

Retry configuration, nullable fields, and the typed error hierarchy.

## What it shows

- `RetryConfig` — customize retry attempts, backoff, and max delay
- `nullable=True` — return `None` for missing values instead of raising
- `set_null()` — explicitly null a field
- Error hierarchy: `NotFoundError`, `InvalidArgumentError`, `DecreeError` base
- Disabling retry with `retry=None`

## Run

```bash
cd examples
make setup
cd error-handling
python main.py
```

## Error types

| Exception | When |
|-----------|------|
| `NotFoundError` | Field or tenant doesn't exist |
| `InvalidArgumentError` | Value fails schema validation |
| `LockedError` | Field is locked |
| `ChecksumMismatchError` | Optimistic concurrency conflict |
| `PermissionDeniedError` | Auth failure |
| `UnavailableError` | Server unreachable (retryable) |
| `TypeMismatchError` | SDK can't convert value to requested type |
| `DecreeError` | Base class for all of the above |

## Learn more

- [Python SDK on PyPI](https://pypi.org/project/opendecree/)
