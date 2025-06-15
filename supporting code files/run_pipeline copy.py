#!/usr/bin/env python
"""Sequentially run the dancer automation pipeline.

This script starts the local API server in the background and then
executes the main automation, beat synchronization, and 4K upscaling
scripts in order. The API server is terminated once all steps finish.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

API_SERVER = ROOT / "api_server_v5_without_faceswap.py"
AUTOMATION_SCRIPT = ROOT / "main_automation_without_faceswap.py"
BEAT_SYNC_SCRIPT = ROOT / "beat_sync_single.py"
UPSCALE_SCRIPT = ROOT / "upscale_4k_parallel.py"


def run_step(cmd: list[str]) -> None:
    """Run a command and raise if it fails."""
    print(f"\n=== Running: {' '.join(cmd)} ===")
    subprocess.run(cmd, check=True)


def main() -> None:
    # Start the API server in the background
    api_proc = subprocess.Popen([sys.executable, str(API_SERVER)])
    try:
        # Give the server a moment to start up
        time.sleep(5)

        # Run remaining steps sequentially
        run_step([sys.executable, str(AUTOMATION_SCRIPT)])
        run_step([sys.executable, str(BEAT_SYNC_SCRIPT)])
        run_step([sys.executable, str(UPSCALE_SCRIPT)])
    finally:
        print("Stopping API server…")
        api_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api_proc.kill()


if __name__ == "__main__":
    main()