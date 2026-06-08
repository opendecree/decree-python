"""Smoke test for the live-config example."""

import signal
import subprocess
import sys

import pytest


@pytest.mark.example
def test_live_config_runs() -> None:
    """Verify the example connects, prints current values, then starts watching."""
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        # Expected — the example blocks on changes(). SIGINT triggers its
        # own handler (signal.signal(... lambda *_: sys.exit(0))), which
        # flushes stdout on the way out.
        proc.send_signal(signal.SIGINT)
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

    assert "Current values:" in stdout, f"stdout: {stdout}\nstderr: {stderr}"
    assert "Watching for changes" in stdout
