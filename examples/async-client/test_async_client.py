"""Smoke test for the async-client example."""

import subprocess
import sys

import pytest


@pytest.mark.example
def test_async_client_runs() -> None:
    """Verify the async-client example runs without errors."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "app.name:" in result.stdout
    assert "Concurrent reads:" in result.stdout
