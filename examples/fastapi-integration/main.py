#!/usr/bin/env python3
"""FastAPI Integration: live config in a web server using lifespan.

Demonstrates AsyncConfigWatcher as a FastAPI lifespan dependency — config
values are always fresh without polling or restarting.

Run:
    pip install fastapi uvicorn
    python main.py

Then visit http://localhost:8000/config or http://localhost:8000/features.

Requires a running decree server with seeded data (see ../README.md).
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from opendecree import AsyncConfigClient

# Watcher fields — populated during lifespan startup.
rate_limit: object = None
timeout: object = None
debug: object = None
dark_mode: object = None
beta_access: object = None


@asynccontextmanager
async def lifespan(app: object) -> AsyncIterator[None]:
    """Start the config watcher on startup, stop on shutdown."""
    global rate_limit, timeout, debug, dark_mode, beta_access

    tenant_id = get_tenant_id()

    client = AsyncConfigClient("localhost:9090", subject="fastapi-example")
    watcher = client.watch(tenant_id)

    rate_limit = watcher.field("server.rate_limit", int, default=100)
    timeout = watcher.field("server.timeout", timedelta, default=timedelta(seconds=30))
    debug = watcher.field("app.debug", bool, default=False)
    dark_mode = watcher.field("features.dark_mode", bool, default=False)
    beta_access = watcher.field("features.beta_access", bool, default=False)

    await watcher.start()
    try:
        yield
    finally:
        await watcher.stop()
        await client.close()


def create_app() -> object:
    """Create the FastAPI app with decree lifespan."""
    try:
        from fastapi import FastAPI
    except ImportError:
        raise SystemExit("Install FastAPI first: pip install fastapi uvicorn")

    app = FastAPI(title="Decree + FastAPI Example", lifespan=lifespan)

    @app.get("/config")
    async def get_config() -> dict:
        """Returns live server config — always fresh, no polling."""
        return {
            "rate_limit": rate_limit.value,
            "timeout": str(timeout.value),
            "debug": debug.value,
        }

    @app.get("/features")
    async def get_features() -> dict:
        """Returns live feature flags."""
        return {
            "dark_mode": dark_mode.value,
            "beta_access": beta_access.value,
        }

    return app


app = create_app()


def get_tenant_id() -> str:
    if v := os.environ.get("TENANT_ID"):
        return v
    tenant_file = Path(__file__).parent.parent / ".tenant-id"
    if tenant_file.exists():
        return tenant_file.read_text().strip()
    raise SystemExit("Set TENANT_ID env var or run 'make setup' from the examples directory")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
