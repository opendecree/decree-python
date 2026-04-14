#!/usr/bin/env python3
"""Async Client: connect to OpenDecree using asyncio.

Demonstrates the AsyncConfigClient — same API as ConfigClient but fully
async. Uses `async with` for lifecycle and `await` for all operations.

Run:
    python main.py

Requires a running decree server with seeded data (see ../README.md).
"""

import asyncio
from datetime import timedelta
from pathlib import Path

from opendecree import AsyncConfigClient


async def main() -> None:
    tenant_id = get_tenant_id()

    # Async context manager — closes the gRPC channel on exit.
    async with AsyncConfigClient("localhost:9090", subject="async-example") as client:
        # All operations are awaitable.
        name = await client.get(tenant_id, "app.name")
        print(f"app.name:          {name}")

        debug = await client.get(tenant_id, "app.debug", bool)
        print(f"app.debug:         {debug}")

        rate_limit = await client.get(tenant_id, "server.rate_limit", int)
        print(f"server.rate_limit: {rate_limit}")

        timeout = await client.get(tenant_id, "server.timeout", timedelta)
        print(f"server.timeout:    {timeout}")

        fee_rate = await client.get(tenant_id, "payments.fee_rate", float)
        print(f"payments.fee_rate: {fee_rate}")

        # Concurrent reads with asyncio.gather — faster than sequential.
        print("\nConcurrent reads:")
        name, debug, rate_limit = await asyncio.gather(
            client.get(tenant_id, "app.name"),
            client.get(tenant_id, "app.debug", bool),
            client.get(tenant_id, "server.rate_limit", int),
        )
        print(f"  app.name:          {name}")
        print(f"  app.debug:         {debug}")
        print(f"  server.rate_limit: {rate_limit}")

        # Atomic multi-write.
        await client.set_many(
            tenant_id,
            {"app.debug": "true", "server.rate_limit": "200"},
            description="async example update",
        )
        print("\nUpdated app.debug=true, server.rate_limit=200")

        debug = await client.get(tenant_id, "app.debug", bool)
        rate_limit = await client.get(tenant_id, "server.rate_limit", int)
        print(f"  app.debug:         {debug}")
        print(f"  server.rate_limit: {rate_limit}")


def get_tenant_id() -> str:
    import os

    if v := os.environ.get("TENANT_ID"):
        return v
    tenant_file = Path(__file__).parent.parent / ".tenant-id"
    if tenant_file.exists():
        return tenant_file.read_text().strip()
    raise SystemExit("Set TENANT_ID env var or run 'make setup' from the examples directory")


if __name__ == "__main__":
    asyncio.run(main())
