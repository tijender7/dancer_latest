#!/usr/bin/env python3
"""
Crop to Reels Format Script
Converts 4K upscaled videos to YouTube Shorts format (9:16 aspect ratio)
"""

import os
import sys
import subprocess
from pathlib import Path
import json
from datetime import datetime

# === CONFIGURATION ===
DANCERS_CONTENT_BASE = Path(r"H:\dancers_content")
UPSCALED_SUBFOLDER = "4k_upscaled"
COMPILED_SUBFOLDER = "compiled"
REELS_SUBFOLDER = "reels"

# Output settings for YouTube Shorts
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920  # 9:16 aspect ratio
TARGET_BITRATE = "8M"
TARGET_FPS = 30

def find_latest_run_folder():
    """Find the most recent Run_ folder."""
    try:
        run_folders = sorted(
            [d for d in DANCERS_CONTENT_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime, reverse=True
        )
        if not run_folders:
            print("ERROR: No 'Run_*' folders found.")
            return None
        return run_folders[0]
    except Exception as e:
        print(f"ERROR: Could not find run folders: {e}")
        return None

def find_upscaled_videos(run_folder):
    """Find all 4K upscaled videos ready for cropping."""
    upscaled_dir = run_folder / UPSCALED_SUBFOLDER / COMPILED_SUBFOLDER
    if not upscaled_dir.exists():
        print(f"ERROR: Upscaled directory not found: {upscaled_dir}")
        return []
    
    video_files = list(upscaled_dir.glob("*.mp4"))
    print(f"Found {len(video_files)} upscaled videos to convert to reels format")
    return video_files

def create_reels_directory(run_folder):
    """Create the reels output directory."""
    reels_dir = run_folder / UPSCALED_SUBFOLDER / COMPILED_SUBFOLDER / REELS_SUBFOLDER
    reels_dir.mkdir(parents=True, exist_ok=True)
    return reels_dir

def crop_video_to_reels(input_path, output_path):
    """Crop video to 9:16 aspect ratio using FFmpeg."""
    
    # FFmpeg command to crop and resize for YouTube Shorts
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        "-r", str(TARGET_FPS),
        "-b:v", TARGET_BITRATE,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",  # Overwrite output file
        str(output_path)
    ]
    
    print(f"Converting: {input_path.name}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ SUCCESS: {output_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {input_path.name}")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ ERROR: FFmpeg not found. Please install FFmpeg and add it to PATH")
        return False

def main():
    print("=" * 60)
    print("📱 CROP TO REELS FORMAT CONVERTER")
    print("=" * 60)
    
    # Step 1: Find latest run
    run_folder = find_latest_run_folder()
    if not run_folder:
        sys.exit(1)
    print(f"Using run folder: {run_folder.name}")
    
    # Step 2: Find upscaled videos
    upscaled_videos = find_upscaled_videos(run_folder)
    if not upscaled_videos:
        print("No upscaled videos found to convert")
        sys.exit(0)
    
    # Step 3: Create reels directory
    reels_dir = create_reels_directory(run_folder)
    print(f"Output directory: {reels_dir}")
    
    # Step 4: Convert each video
    successful_conversions = 0
    failed_conversions = 0
    
    for video_path in upscaled_videos:
        # Generate output filename
        output_filename = f"reel_{video_path.stem}.mp4"
        output_path = reels_dir / output_filename
        
        # Skip if already exists
        if output_path.exists():
            print(f"⏭️ SKIP: {output_filename} already exists")
            continue
        
        # Convert video
        if crop_video_to_reels(video_path, output_path):
            successful_conversions += 1
        else:
            failed_conversions += 1
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("📊 CONVERSION SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {successful_conversions}")
    print(f"❌ Failed: {failed_conversions}")
    print(f"📁 Output directory: {reels_dir}")
    print("=" * 60)
    
    if successful_conversions > 0:
        print("🎉 Videos ready for YouTube Shorts upload!")
        sys.exit(0)
    else:
        print("❌ No videos were successfully converted")
        sys.exit(1)

if __name__ == "__main__":
    main()