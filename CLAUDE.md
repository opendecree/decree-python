# OpenDecree Python SDK — Claude Context

## Overview

Python SDK for the OpenDecree configuration service. Wraps the gRPC API with sync and async
clients, a field-watching subscription layer, and optional OpenTelemetry instrumentation.

## Tech Stack

| Concern | Tool |
|---------|------|
| Language | Python 3.10+ |
| Transport | grpcio |
| Serialization | protobuf, googleapis-common-protos |
| Code generation | grpcio-tools (Docker) |
| Lint / format | ruff |
| Type checking | mypy |
| Tests | pytest, pytest-asyncio |
| Docs | mkdocs (material) + mkdocstrings |

## Development

### Prerequisites

Python 3.10+, Docker (for proto generation), Make.

### Key Commands

```bash
make generate      # regenerate proto stubs + _constants.py (Docker)
make lint          # ruff check + format check
make typecheck     # mypy
make test          # pytest (unit)
make integration   # pytest -m integration (requires live server)
make pre-commit    # lint + typecheck + test
```

### Layout

```
sdk/
├── src/opendecree/   # public package
│   ├── _generated/   # generated proto stubs (committed)
│   └── ...
├── tests/            # unit + integration tests
└── pyproject.toml
```

## Coding Guidelines

See [coding-guidelines.md](https://github.com/opendecree/decree/blob/main/docs/development/coding-guidelines.md)
for the shared philosophy (vanilla principle, minimal deps) and the Python-specific section
(runtime deps, type annotations, asyncio patterns, ruff enforcement).

## Conventions

- Generated proto stubs live in `sdk/src/opendecree/_generated/` and are committed
- `_constants.py` is generated from `pyproject.toml` via `build/gen-constants.py`
- Apache 2.0 license
