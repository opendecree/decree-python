"""Smoke test for the error-handling example."""

import subprocess
import sys

import pytest


@pytest.mark.example
def test_error_handling_runs() -> None:
    """Verify the error-handling example runs without errors."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "Nullable reads" in result.stdout
    assert "Error hierarchy" in result.stdout
    assert "NotFoundError:" in result.stdout
