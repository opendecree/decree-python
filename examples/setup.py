#!/usr/bin/env python3
"""Seed the decree server with example data.

Reads seed.yaml, creates the schema, tenant, and initial config values.
Writes the tenant ID to .tenant-id so examples can find it automatically.

Usage:
    python setup.py
"""

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
    result = subprocess.run(
        ["decree", "seed", "--addr", addr, str(seed_file)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error seeding: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Parse tenant ID from output (line: "Tenant:  <id> (created=true)")
    for line in result.stdout.splitlines():
        if line.startswith("Tenant:"):
            tenant_id = line.split()[1]
            tenant_id_file.write_text(tenant_id)
            print(result.stdout, end="")
            print(f"Tenant ID written to .tenant-id")
            return

    print(f"Could not parse tenant ID from output:\n{result.stdout}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
