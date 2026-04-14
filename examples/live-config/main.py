#!/usr/bin/env python3
"""Live Config: watch configuration values change in real time.

Demonstrates ConfigWatcher with the @on_change decorator pattern and the
blocking changes() iterator. Run this, then change values with the decree
CLI and watch the output update.

Run:
    python main.py

Requires a running decree server with seeded data (see ../README.md).
"""

import signal
import sys
from datetime import timedelta
from pathlib import Path

from opendecree import ConfigClient


def main() -> None:
    tenant_id = get_tenant_id()

    with ConfigClient("localhost:9090", subject="live-config-example") as client:
        # Create a watcher and register fields with types and defaults.
        watcher = client.watch(tenant_id)
        rate_limit = watcher.field("server.rate_limit", int, default=100)
        timeout = watcher.field("server.timeout", timedelta, default=timedelta(seconds=30))
        debug = watcher.field("app.debug", bool, default=False)

        # Use the @on_change decorator to react to changes.
        @rate_limit.on_change
        def on_rate_limit_change(old: int, new: int) -> None:
            print(f"  [callback] rate_limit: {old} → {new}")

        @debug.on_change
        def on_debug_change(old: bool, new: bool) -> None:
            print(f"  [callback] debug: {old} → {new}")

        # Context manager starts the subscription and stops on exit.
        with watcher:
            print("Current values:")
            print(f"  server.rate_limit: {rate_limit.value}")
            print(f"  server.timeout:    {timeout.value}")
            print(f"  app.debug:         {debug.value}")
            print()
            print("Watching for changes... (Ctrl+C to stop)")
            print("Try: decree config set <tenant-id> server.rate_limit 500")

            # Block on the changes() iterator — yields Change objects.
            signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
            for change in rate_limit.changes():
                print(f"  [change] {change.field_path}: {change.old_value} → {change.new_value}")


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
