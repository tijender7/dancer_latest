#!/usr/bin/env python3
"""
Find Music Images Only - Specifically for Music Automation

This script finds ONLY the music automation images and sends them for approval.
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
from datetime import datetime, timedelta

# Load environment variables from parent directory
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Setup logging with UTF-8 support
import io
console_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
console_handler = logging.StreamHandler(console_stream)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(console_handler)

# Constants
SCRIPT_DIR = Path(__file__).resolve().parent
DANCERS_CONTENT = Path("H:/dancers_content")
COMFYUI_OUTPUT_DIR = Path("D:/Comfy_UI_V20/ComfyUI/output")  # Actual ComfyUI output
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR.parent / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"

def find_latest_music_run_folder():
    """Find the most recent Run_*_music folder"""
    logger.info("🎵 Searching for latest music run folder...")
    
    pattern = str(DANCERS_CONTENT / "Run_*_music")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        logger.error("❌ No music run folders found!")
        logger.error(f"   Searched pattern: {pattern}")
        return None
    
    # Sort by modification time (newest first)
    latest_folder = max(music_folders, key=lambda f: Path(f).stat().st_mtime)
    latest_path = Path(latest_folder)
    
    logger.info(f"✅ Found latest music run: {latest_path.name}")
    logger.info(f"📁 Full path: {latest_path}")
    
    return latest_path

def find_music_images_in_comfyui_output():
    """Find music images in ComfyUI's actual output directory"""
    logger.info("🔍 Searching for music images in ComfyUI output directory...")
    logger.info(f"📁 ComfyUI Output Directory: {COMFYUI_OUTPUT_DIR}")
    
    if not COMFYUI_OUTPUT_DIR.exists():
        logger.error(f"❌ ComfyUI output directory not found: {COMFYUI_OUTPUT_DIR}")
        return []
    
    # Calculate time threshold (last 4 hours)
    time_threshold = datetime.now() - timedelta(hours=4)
    logger.info(f"⏰ Looking for images newer than: {time_threshold}")
    
    # Find all PNG and JPG files in ComfyUI output
    image_patterns = ["**/*.png", "**/*.jpg", "**/*.jpeg"]
    recent_images = []
    
    for pattern in image_patterns:
        for image_path in COMFYUI_OUTPUT_DIR.glob(pattern):
            try:
                # Check modification time
                mod_time = datetime.fromtimestamp(image_path.stat().st_mtime)
                
                if mod_time > time_threshold:
                    # Filter out video frames and other automation outputs
                    filename = image_path.name.lower()
                    
                    # Skip video outputs, approved images, etc.
                    if any(skip_word in filename for skip_word in [
                        'video_swapped', 'approved_', 'batch0_', 'batch1_', 'batch2_', 'batch3_'
                    ]):
                        continue
                    
                    recent_images.append({
                        "image_path": str(image_path),
                        "filename": image_path.name,
                        "mod_time": mod_time,
                        "size": image_path.stat().st_size,
                        "folder": str(image_path.parent.relative_to(COMFYUI_OUTPUT_DIR))
                    })
                    
            except Exception as e:
                logger.debug(f"Error checking {image_path}: {e}")
    
    # Sort by modification time (newest first)
    recent_images.sort(key=lambda x: x["mod_time"], reverse=True)
    
    logger.info(f"✅ Found {len(recent_images)} potential music images")
    
    # Show all found images with full paths
    for i, img in enumerate(recent_images):
        logger.info(f"   📷 {i+1}: {img['filename']}")
        logger.info(f"      📁 Path: {img['folder']}")
        logger.info(f"      ⏰ Time: {img['mod_time']}")
        logger.info(f"      📏 Size: {img['size']:,} bytes")
        logger.info("")
    
    return recent_images

def find_music_images_in_date_folder():
    """Find music images in today's date folder"""
    today = datetime.now().strftime("%y%m%d")  # 250623 format
    date_folder = DANCERS_CONTENT / today
    
    logger.info(f"🗓️ Searching in today's date folder: {date_folder}")
    
    if not date_folder.exists():
        logger.warning(f"⚠️ Date folder doesn't exist: {date_folder}")
        return []
    
    # Find all PNG and JPG files
    image_patterns = ["*.png", "*.jpg", "*.jpeg"]
    images = []
    
    for pattern in image_patterns:
        for image_path in date_folder.glob(pattern):
            try:
                # Check modification time
                mod_time = datetime.fromtimestamp(image_path.stat().st_mtime)
                
                # Filter out video outputs and other automation outputs
                filename = image_path.name.lower()
                
                # Skip video outputs, approved images, etc.
                if any(skip_word in filename for skip_word in [
                    'video_swapped', 'approved_', 'batch0_', 'batch1_', 'batch2_', 'batch3_'
                ]):
                    continue
                
                images.append({
                    "image_path": str(image_path),
                    "filename": image_path.name,
                    "mod_time": mod_time,
                    "size": image_path.stat().st_size,
                    "folder": str(image_path.parent.name)
                })
                
            except Exception as e:
                logger.debug(f"Error checking {image_path}: {e}")
    
    # Sort by modification time (newest first)
    images.sort(key=lambda x: x["mod_time"], reverse=True)
    
    logger.info(f"✅ Found {len(images)} potential music images in date folder")
    
    # Show all found images with full paths
    for i, img in enumerate(images):
        logger.info(f"   📷 {i+1}: {img['filename']}")
        logger.info(f"      📁 Folder: {img['folder']}")
        logger.info(f"      ⏰ Time: {img['mod_time']}")
        logger.info(f"      📏 Size: {img['size']:,} bytes")
        logger.info("")
    
    return images

def start_telegram_approval(images):
    """Start Telegram approval process"""
    logger.info("📱 Starting Telegram approval process...")
    
    if not SEND_TELEGRAM_SCRIPT.exists():
        logger.error(f"❌ Telegram script not found: {SEND_TELEGRAM_SCRIPT}")
        return False
    
    if not images:
        logger.error("❌ No images to send for approval")
        return False
    
    try:
        # Prepare telegram script arguments
        args = [sys.executable, str(SEND_TELEGRAM_SCRIPT)]
        
        # Add image paths
        for img in images:
            args.append(img["image_path"])
        
        logger.info(f"📤 Sending {len(images)} images for Telegram approval...")
        logger.info(f"🔗 Bot Token: {os.getenv('TELEGRAM_BOT_TOKEN', 'Not set')[:20]}...")
        logger.info(f"💬 Chat ID: {os.getenv('TELEGRAM_CHAT_ID', 'Not set')}")
        
        # Start telegram approval process
        process = subprocess.Popen(args, cwd=str(SCRIPT_DIR))
        
        logger.info("✅ Telegram approval process started")
        logger.info("   📱 Check your Telegram bot for approval messages")
        
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram approval: {e}")
        return False

def main():
    """Main execution"""
    logger.info("🎵 FIND MUSIC IMAGES ONLY - Music Automation Image Discovery")
    logger.info("=" * 70)
    
    try:
        # Strategy 1: Look in ComfyUI output directory
        logger.info("🔍 STRATEGY 1: Search ComfyUI output directory")
        comfyui_images = find_music_images_in_comfyui_output()
        
        # Strategy 2: Look in date folder
        logger.info("\n🔍 STRATEGY 2: Search date folder")
        date_images = find_music_images_in_date_folder()
        
        # Strategy 3: Look in music run folders
        logger.info("\n🔍 STRATEGY 3: Check music run folder")
        music_run = find_latest_music_run_folder()
        if music_run:
            logger.info(f"📁 Music run folder: {music_run}")
            logger.info("   ℹ️  Note: Images might be in ComfyUI output, not run folder")
        
        # Choose the best set of images
        if comfyui_images:
            logger.info(f"\n✅ Using {len(comfyui_images)} images from ComfyUI output")
            selected_images = comfyui_images
        elif date_images:
            logger.info(f"\n✅ Using {len(date_images)} images from date folder")
            selected_images = date_images
        else:
            logger.error("\n❌ No suitable music images found!")
            logger.error("💡 Suggestion: Run the music automation first to generate images")
            return False
        
        # Limit to reasonable number
        if len(selected_images) > 20:
            logger.info(f"📊 Limiting to 20 most recent images (from {len(selected_images)} found)")
            selected_images = selected_images[:20]
        
        # Show final selection
        logger.info(f"\n📋 FINAL SELECTION - {len(selected_images)} images:")
        for i, img in enumerate(selected_images, 1):
            logger.info(f"   {i}. {img['filename']} ({img['mod_time']})")
        
        # Start approval
        approval_process = start_telegram_approval(selected_images)
        
        if approval_process:
            logger.info("\n✅ Images sent for approval!")
            logger.info("📱 Check your Telegram bot to approve/reject images")
            return True
        else:
            return False
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Music images found and sent for approval!")
        else:
            print("\n❌ Failed to find or send music images!")
    except KeyboardInterrupt:
        print("\n⏹️ Process interrupted")