"""Smoke test for the quickstart example."""

import subprocess
import sys

import pytest


@pytest.mark.example
def test_quickstart_runs() -> None:
    """Verify the quickstart example runs without errors."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "app.name:" in result.stdout
    assert "payments.fee_rate:" in result.stdout
