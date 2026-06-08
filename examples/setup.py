#!/usr/bin/env python3
"""Seed the decree server with example data.

Reads seed.yaml, creates the schema, tenant, and initial config values.
Writes the tenant ID to .tenant-id so examples can find it automatically.

Usage:
    python setup.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    seed_file = Path(__file__).parent / "seed.yaml"
    tenant_id_file = Path(__file__).parent / ".tenant-id"
    addr = os.environ.get("DECREE_ADDR", "localhost:9090")

    # Use the decree CLI to seed — it handles schema creation, tenant
    # creation, and config import in one command.
    # --auto-publish: tenants can only be created against a published
    #   schema version, and imported versions start as unpublished drafts.
    # --subject: the server rejects unauthenticated requests (empty
    #   x-subject), and the CLI does not set one by default.
    result = subprocess.run(
        [
            "decree", "seed",
            "--server", addr,
            "--insecure",
            "--auto-publish",
            "--subject", "examples-setup",
            "--output", "json",
            str(seed_file),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error seeding: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # `decree seed -o json` prints a [][string] table: a header row
    # ["RESOURCE", "ID", "CREATED", "DETAILS"] followed by one row per
    # resource, e.g. ["tenant", "<id>", "true", ""].
    rows = json.loads(result.stdout)
    for row in rows:
        if row[0] == "tenant":
            tenant_id = row[1]
            tenant_id_file.write_text(tenant_id)
            print(f"Tenant: {tenant_id}")
            print("Tenant ID written to .tenant-id")
            return

    print(f"Could not find tenant row in output:\n{result.stdout}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
