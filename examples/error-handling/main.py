#!/usr/bin/env python3
"""Error Handling: retry configuration, nullable fields, and error hierarchy.

Demonstrates Python-specific patterns for robust config access:
- RetryConfig for transient failure recovery
- nullable=True for graceful handling of missing values
- Typed exception hierarchy for precise error handling

Run:
    python main.py

Requires a running decree server with seeded data (see ../README.md).
"""

from pathlib import Path

from opendecree import (
    ConfigClient,
    InvalidArgumentError,
    NotFoundError,
    RetryConfig,
    UnavailableError,
)


def main() -> None:
    tenant_id = get_tenant_id()

    # --- Custom retry configuration ---
    # Default is 3 attempts with exponential backoff.
    # Customize for your use case.
    retry = RetryConfig(
        max_attempts=5,
        initial_backoff=0.2,
        max_backoff=10.0,
    )

    with ConfigClient("localhost:9090", subject="error-example", retry=retry) as client:
        # --- Nullable reads ---
        # Without nullable, missing values raise NotFoundError.
        # With nullable=True, they return None instead.
        print("=== Nullable reads ===")
        value = client.get(tenant_id, "app.name", str, nullable=True)
        print(f"app.name (exists):           {value!r}")

        # set_null makes a field return None with nullable=True.
        client.set_null(tenant_id, "app.debug")
        value = client.get(tenant_id, "app.debug", str, nullable=True)
        print(f"app.debug (after set_null):  {value!r}")

        # Restore it.
        client.set(tenant_id, "app.debug", "false")
        print(f"app.debug (restored):        {client.get(tenant_id, 'app.debug', bool)!r}")

        # --- Error hierarchy ---
        print("\n=== Error hierarchy ===")

        # NotFoundError — field doesn't exist.
        try:
            client.get(tenant_id, "nonexistent.field")
        except NotFoundError as e:
            print(f"NotFoundError:        {e}")

        # InvalidArgumentError — value fails validation.
        try:
            client.set(tenant_id, "server.rate_limit", "-1")
        except InvalidArgumentError as e:
            print(f"InvalidArgumentError: {e}")

        # All decree errors share a common base class.
        try:
            client.get(tenant_id, "nonexistent.field")
        except Exception as e:
            # In production, catch the specific type you care about.
            from opendecree import DecreeError

            if isinstance(e, DecreeError):
                print(f"DecreeError base:     {type(e).__name__}: {e}")

        # --- Retry behavior ---
        print("\n=== Retry ===")
        print(f"Configured: {retry.max_attempts} attempts, "
              f"{retry.initial_backoff}s initial backoff, "
              f"{retry.max_backoff}s max backoff")
        print("Retries are automatic on UNAVAILABLE and DEADLINE_EXCEEDED.")

        # To disable retry entirely:
        no_retry_client = ConfigClient(
            "localhost:9090",
            subject="no-retry-example",
            retry=None,
        )
        with no_retry_client:
            val = no_retry_client.get(tenant_id, "app.name")
            print(f"No-retry read:       {val!r}")


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
