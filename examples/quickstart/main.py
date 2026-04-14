#!/usr/bin/env python3
"""Quickstart: connect to OpenDecree and read typed configuration values.

This is the simplest possible example — context manager, typed get().

Run:
    python main.py

Requires a running decree server with seeded data (see ../README.md).
"""

from datetime import timedelta
from pathlib import Path

from opendecree import ConfigClient


def main() -> None:
    tenant_id = get_tenant_id()

    # Context manager closes the gRPC channel automatically.
    with ConfigClient("localhost:9090", subject="quickstart-example") as client:
        # get() returns str by default.
        name = client.get(tenant_id, "app.name")
        print(f"app.name:          {name}")

        # Pass a type to get a typed value — no string parsing needed.
        debug = client.get(tenant_id, "app.debug", bool)
        print(f"app.debug:         {debug}")

        rate_limit = client.get(tenant_id, "server.rate_limit", int)
        print(f"server.rate_limit: {rate_limit}")

        timeout = client.get(tenant_id, "server.timeout", timedelta)
        print(f"server.timeout:    {timeout}")

        fee_rate = client.get(tenant_id, "payments.fee_rate", float)
        print(f"payments.fee_rate: {fee_rate}")

        # set() and set_many() for writes.
        client.set(tenant_id, "app.debug", "true")
        print("\nSet app.debug = true")

        debug = client.get(tenant_id, "app.debug", bool)
        print(f"app.debug:         {debug}")


def get_tenant_id() -> str:
    import os

    if v := os.environ.get("TENANT_ID"):
        return v
    tenant_file = Path(__file__).parent.parent / ".tenant-id"
    if tenant_file.exists():
        return tenant_file.read_text().strip()
    raise SystemExit("Set TENANT_ID env var or run 'make setup' from the examples directory")


if __name__ == "__main__":
    main()
