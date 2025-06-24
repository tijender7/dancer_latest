#!/usr/bin/env python3
"""
Find Generated Images Script

This script finds the most recently generated images from ComfyUI's output directory
and sends them for Telegram approval.
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
COMFYUI_OUTPUT_DIR = Path("H:/dancers_content")
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR.parent / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"

def find_recent_images(hours_back=2):
    """Find images generated in the last few hours"""
    logger.info(f"🔍 Searching for images generated in the last {hours_back} hours...")
    logger.info(f"📁 ComfyUI Output Directory: {COMFYUI_OUTPUT_DIR}")
    
    if not COMFYUI_OUTPUT_DIR.exists():
        logger.error(f"❌ ComfyUI output directory not found: {COMFYUI_OUTPUT_DIR}")
        return []
    
    # Calculate time threshold
    time_threshold = datetime.now() - timedelta(hours=hours_back)
    logger.info(f"⏰ Looking for images newer than: {time_threshold}")
    
    # Find all PNG and JPG files
    image_patterns = ["**/*.png", "**/*.jpg", "**/*.jpeg"]
    recent_images = []
    
    for pattern in image_patterns:
        for image_path in COMFYUI_OUTPUT_DIR.glob(pattern):
            try:
                # Check modification time
                mod_time = datetime.fromtimestamp(image_path.stat().st_mtime)
                
                if mod_time > time_threshold:
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
    
    logger.info(f"✅ Found {len(recent_images)} recent images")
    
    # Show first 10 images
    for i, img in enumerate(recent_images[:10]):
        logger.info(f"   📷 {i+1}: {img['filename']} ({img['folder']}) - {img['mod_time']}")
    
    if len(recent_images) > 10:
        logger.info(f"   ... and {len(recent_images) - 10} more images")
    
    return recent_images

def filter_music_images(images):
    """Filter images that are likely from the music generation"""
    logger.info("🎵 Filtering for music-related images...")
    
    # Look for patterns that indicate music generation
    music_patterns = [
        "api_flux",  # Workflow name
        "music",     # Music-related
        "segment",   # Segment-based generation
        "shiv",      # Deity name
        "lord"       # Deity title
    ]
    
    filtered_images = []
    
    for img in images:
        filename_lower = img["filename"].lower()
        folder_lower = img["folder"].lower()
        
        # Check if filename or folder contains music-related patterns
        is_music_related = any(pattern in filename_lower or pattern in folder_lower 
                             for pattern in music_patterns)
        
        # Also check by file size (music images are typically larger)
        is_large_enough = img["size"] > 100000  # > 100KB
        
        if is_music_related or is_large_enough:
            filtered_images.append(img)
    
    logger.info(f"🎵 Filtered to {len(filtered_images)} music-related images")
    return filtered_images

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
    logger.info("🔍 FIND GENERATED IMAGES - Music Images Search & Approval")
    logger.info("=" * 60)
    
    try:
        # Step 1: Find recent images
        recent_images = find_recent_images(hours_back=3)  # Look back 3 hours
        
        if not recent_images:
            logger.info("⚠️  No recent images found. Trying to look further back...")
            recent_images = find_recent_images(hours_back=24)  # Try 24 hours
        
        if not recent_images:
            logger.error("❌ No recent images found in ComfyUI output directory")
            return False
        
        # Step 2: Filter for music-related images
        music_images = filter_music_images(recent_images)
        
        if not music_images:
            logger.warning("⚠️  No music-related images found, using all recent images")
            music_images = recent_images[:60]  # Take first 60 images
        
        # Step 3: Limit to reasonable number for approval
        if len(music_images) > 60:
            logger.info(f"📊 Limiting to 60 most recent images (from {len(music_images)} found)")
            music_images = music_images[:60]
        
        # Step 4: Start approval
        approval_process = start_telegram_approval(music_images)
        
        if approval_process:
            logger.info("✅ Images sent for approval!")
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
            print("\n✅ Images found and sent for approval!")
        else:
            print("\n❌ Failed to find or send images!")
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted")