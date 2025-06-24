#!/usr/bin/env python3
"""
Approval Only Script - Handle Telegram approval for existing generated images

This script finds existing generated images and sends them for Telegram approval
without regenerating anything.
"""

# Set UTF-8 encoding for Windows console
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
import json
import glob
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Load environment variables from parent directory
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)
print(f"DEBUG: Loading environment from: {env_path}")

# Setup logging with UTF-8 support
import io
console_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
console_handler = logging.StreamHandler(console_stream)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# File logging
log_directory = Path(__file__).parent / "logs"
log_directory.mkdir(exist_ok=True)
log_file = log_directory / f"approval_only_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Constants
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content")
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"
TELEGRAM_APPROVALS_JSON = TELEGRAM_APPROVALS_DIR / "telegram_approvals.json"
APPROVAL_FILENAME = "approved_images.json"

def find_latest_music_run():
    """Find the most recent Run_*_music_images folder"""
    logger.info("🔍 Searching for latest music run folder...")
    
    pattern = str(COMFYUI_OUTPUT_DIR_BASE / "Run_*_music_images")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        logger.error("❌ No music run folders found!")
        logger.error(f"   Searched in: {COMFYUI_OUTPUT_DIR_BASE}")
        logger.error(f"   Pattern: Run_*_music_images")
        return None
    
    # Sort by modification time (newest first)
    latest_folder = max(music_folders, key=lambda f: Path(f).stat().st_mtime)
    latest_path = Path(latest_folder)
    
    logger.info(f"✅ Found latest run: {latest_path.name}")
    logger.info(f"   📁 Path: {latest_path}")
    
    return latest_path

def collect_existing_images(run_folder):
    """Collect all generated images from the run folder"""
    logger.info("📸 Collecting existing generated images...")
    
    # Look for images in date subfolders
    date_folders = [f for f in run_folder.iterdir() if f.is_dir() and f.name.startswith("2025")]
    
    if not date_folders:
        logger.error("❌ No date folders found in run directory")
        return []
    
    # Use the most recent date folder
    latest_date_folder = max(date_folders, key=lambda f: f.stat().st_mtime)
    logger.info(f"📅 Using date folder: {latest_date_folder.name}")
    
    # Find all image files
    image_extensions = ["*.png", "*.jpg", "*.jpeg"]
    collected_images = []
    
    for ext in image_extensions:
        for image_path in latest_date_folder.glob(ext):
            # Try to extract segment info from filename
            filename = image_path.name
            segment_id = "unknown"
            
            # Try to extract segment number from filename patterns
            import re
            segment_match = re.search(r'segment[_\s]*(\d+)', filename, re.IGNORECASE)
            if segment_match:
                segment_id = int(segment_match.group(1))
            
            image_info = {
                "image_path": str(image_path),
                "filename": filename,
                "segment_id": segment_id,
                "file_size": image_path.stat().st_size,
                "created_time": image_path.stat().st_mtime
            }
            collected_images.append(image_info)
    
    # Sort by segment_id if available, otherwise by filename
    collected_images.sort(key=lambda x: (x["segment_id"] if isinstance(x["segment_id"], int) else 999, x["filename"]))
    
    logger.info(f"✅ Collected {len(collected_images)} images")
    for i, img in enumerate(collected_images[:5]):  # Show first 5
        logger.info(f"   📷 {i+1}: {img['filename']} (Segment {img['segment_id']})")
    
    if len(collected_images) > 5:
        logger.info(f"   ... and {len(collected_images) - 5} more images")
    
    return collected_images

def start_telegram_approval(collected_images):
    """Start Telegram approval process for generated images"""
    logger.info("📱 Starting Telegram approval process...")
    
    if not SEND_TELEGRAM_SCRIPT.exists():
        logger.error(f"❌ Telegram script not found: {SEND_TELEGRAM_SCRIPT}")
        return False
    
    if not collected_images:
        logger.error("❌ No images to send for approval")
        return False
    
    try:
        # Prepare telegram script arguments - pass individual image paths
        args = [sys.executable, str(SEND_TELEGRAM_SCRIPT)]
        
        # Add each image path as a separate argument
        for image_info in collected_images:
            image_path = image_info["image_path"]
            args.append(str(image_path))
            
        logger.info(f"📤 Sending {len(collected_images)} images for Telegram approval...")
        logger.info(f"🔗 Bot Token: {os.getenv('TELEGRAM_BOT_TOKEN', 'Not set')[:20]}...")
        logger.info(f"💬 Chat ID: {os.getenv('TELEGRAM_CHAT_ID', 'Not set')}")
        
        # Start telegram approval process
        process = subprocess.Popen(args, cwd=str(SCRIPT_DIR))
        
        logger.info("✅ Telegram approval process started")
        logger.info(f"   📱 Check your Telegram bot for approval messages")
        logger.info(f"   💾 Approvals will be saved to: {TELEGRAM_APPROVALS_JSON}")
        
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram approval: {e}")
        return False

def wait_for_approvals():
    """Wait for user to approve images via Telegram"""
    logger.info("⏳ Waiting for Telegram approvals...")
    logger.info("   📱 Use your Telegram bot to approve/reject images")
    logger.info("   ⌨️  Press Ctrl+C to skip approval and use all images")
    
    try:
        while True:
            if TELEGRAM_APPROVALS_JSON.exists():
                try:
                    with open(TELEGRAM_APPROVALS_JSON, 'r') as f:
                        approvals = json.load(f)
                    
                    if approvals and len(approvals) > 0:
                        logger.info(f"✅ Found {len(approvals)} approvals!")
                        return approvals
                    
                except (json.JSONDecodeError, KeyError):
                    pass
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        logger.info("⏹️  Approval wait interrupted by user")
        return None

def main():
    """Main execution flow"""
    logger.info("🎭 APPROVAL ONLY - Music Images Telegram Approval")
    logger.info("=" * 60)
    
    try:
        # Step 1: Find latest music run
        run_folder = find_latest_music_run()
        if not run_folder:
            return False
        
        # Step 2: Collect existing images
        collected_images = collect_existing_images(run_folder)
        if not collected_images:
            logger.error("❌ No images found to approve")
            return False
        
        # Step 3: Start Telegram approval
        approval_process = start_telegram_approval(collected_images)
        if not approval_process:
            return False
        
        # Step 4: Wait for approvals
        approvals = wait_for_approvals()
        
        # Step 5: Save approvals to run folder
        if approvals:
            approval_file = run_folder / APPROVAL_FILENAME
            with open(approval_file, 'w') as f:
                json.dump(approvals, f, indent=2)
            
            logger.info(f"💾 Approvals saved to: {approval_file}")
            logger.info(f"✅ Approval process completed with {len(approvals)} approved images")
        else:
            logger.info("⚠️  No approvals received - you can run the full pipeline to use all images")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Approval process completed!")
        else:
            print("\n❌ Approval process failed!")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
        sys.exit(1)