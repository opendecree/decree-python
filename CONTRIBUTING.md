# Contributing to OpenDecree Python SDK

Thank you for your interest in contributing! This guide covers how to set up your development environment, build, test, and submit changes.

## Prerequisites

- **Python** (3.11+)
- **Docker**
- **Make**

That's it. All dev tools (ruff, mypy, pytest, protoc) run inside Docker — no local installation needed.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/opendecree/decree-python.git
cd decree-python

# Build the tools image (one-time)
make tools

# Run the full check suite
make lint && make typecheck && make test
```

## Development Cycle

```
edit code -> lint -> typecheck -> test -> commit -> PR
```

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make generate` | Regenerate proto stubs from BSR |
| `make lint` | Lint with ruff (check + format) |
| `make format` | Auto-format with ruff |
| `make typecheck` | Type check with mypy (strict) |
| `make test` | Run tests with coverage (pytest) |
| `make build` | Build sdist + wheel |
| `make clean` | Remove build artifacts |

### Proto Stubs

Generated proto stubs live in `sdk/src/opendecree/_generated/` and are committed to git. If the upstream `.proto` files change, regenerate with:

```bash
make generate
```

This requires the `decree` repo checked out alongside `decree-python` (for proto source files).

## Project Structure

```
sdk/
├── src/opendecree/          # SDK source
│   ├── client.py            # ConfigClient (sync)
│   ├── async_client.py      # AsyncConfigClient
│   ├── watcher.py           # ConfigWatcher (sync)
│   ├── async_watcher.py     # AsyncConfigWatcher
│   ├── errors.py            # Exception hierarchy
│   ├── types.py             # Dataclass return types
│   ├── _channel.py          # gRPC channel factory
│   ├── _interceptors.py     # Auth metadata interceptors
│   ├── _retry.py            # Exponential backoff retry
│   ├── _convert.py          # TypedValue conversion
│   ├── _stubs.py            # Lazy proto stub loading
│   └── _generated/          # Proto stubs (committed)
├── tests/                   # pytest test suite
├── docs/                    # Usage documentation
└── pyproject.toml           # Package metadata + tool config
```

## Testing

```bash
make test
```

Tests use pytest with pytest-asyncio. Coverage must stay above 80% (enforced in pyproject.toml). Tests mock gRPC stubs — no running server needed.

## Code Style

- **Linting and formatting**: ruff (replaces black + isort + flake8)
- **Type checking**: mypy in strict mode
- Run `make lint && make typecheck` before submitting

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure `make lint && make typecheck && make test` passes
5. Open a pull request against `main`

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
