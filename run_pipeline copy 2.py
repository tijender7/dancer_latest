#!/usr/bin/env python
"""Sequentially run the complete dancer automation and distribution pipeline.

This script manages the entire workflow:
1. Starts the local API server in the background.
2. Runs video generation, beat-syncing, and upscaling.
3. Crops the final videos for social media.
4. Uploads the cropped videos to YouTube.
5. Terminates the API server once all steps are complete.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# --- Configuration ---
# Set the root directory to the script's location
ROOT = Path(__file__).resolve().parent

# === VIDEO GENERATION SCRIPTS ===
API_SERVER = ROOT / "api_server_v5_without_faceswap.py"
AUTOMATION_SCRIPT = ROOT / "main_automation_without_faceswap.py"
BEAT_SYNC_SCRIPT = ROOT / "beat_sync_single.py"
UPSCALE_SCRIPT = ROOT / "upscale_4k_parallel.py"

# === POST-PROCESSING AND UPLOAD SCRIPTS ===
# (Updated with your exact filenames and Instagram step removed)
REELS_CROP_SCRIPT = ROOT / "crop_to_reels.py"
YOUTUBE_POST_SCRIPT = ROOT / "youtube_shorts_poster.py"


def run_step(cmd: list[str], step_name: str) -> None:
    """Run a command with clear logging and raise an exception if it fails."""
    print("\n" + "="*60)
    print(f"▶️  STARTING STEP: {step_name}")
    print(f"    Executing command: {' '.join(cmd)}")
    print("="*60)
    
    # Using check=True will automatically raise an error if the script returns a non-zero exit code
    subprocess.run(cmd, check=True)
    
    print("\n" + "-"*60)
    print(f"✅ FINISHED STEP: {step_name}")
    print("-"*60)


def main() -> None:
    """Main function to orchestrate the entire pipeline."""
    # Start the API server as a background process
    print("🚀 Starting the background API server...")
    api_proc = subprocess.Popen([sys.executable, str(API_SERVER)])
    
    try:
        # Give the server a moment to initialize before starting the main tasks
        print("    Waiting for 5 seconds for the server to spin up...")
        time.sleep(5)

        # --- Run all pipeline steps in sequential order ---
        run_step([sys.executable, str(AUTOMATION_SCRIPT)], "Video Generation")
        run_step([sys.executable, str(BEAT_SYNC_SCRIPT)], "Beat Synchronization")
        run_step([sys.executable, str(UPSCALE_SCRIPT)], "4K Upscaling")
        
        # --- Post-processing and Uploading ---
        run_step([sys.executable, str(REELS_CROP_SCRIPT)], "Cropping Videos for Reels/Shorts")
        run_step([sys.executable, str(YOUTUBE_POST_SCRIPT)], "Uploading to YouTube")

        print("\n🎉🎉🎉 ALL PIPELINE STEPS COMPLETED SUCCESSFULLY! 🎉🎉🎉")

    except subprocess.CalledProcessError as e:
        print("\n" + "!"*60)
        print(f"❌ A CRITICAL ERROR OCCURRED IN A SUB-PROCESS.")
        print(f"   The pipeline has been stopped.")
        print(f"   Failed command: {' '.join(e.cmd)}")
        print(f"   Exit code: {e.returncode}")
        print("!"*60)

    except Exception as e:
        print("\n" + "!"*60)
        print(f"❌ AN UNEXPECTED ERROR OCCURRED: {e}")
        print(f"   The pipeline has been stopped.")
        print("!"*60)

    finally:
        # This block will always run, whether the steps succeeded or failed.
        print("\n🛑 Stopping the background API server...")
        api_proc.terminate()
        try:
            # Wait for the process to terminate gracefully
            api_proc.wait(timeout=10)
            print("    API server stopped.")
        except subprocess.TimeoutExpired:
            # If it doesn't stop, force kill it
            print("    API server did not respond, killing process.")
            api_proc.kill()


if __name__ == "__main__":
    main()