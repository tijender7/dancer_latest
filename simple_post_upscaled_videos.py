#!/usr/bin/env python3
"""
Simple Social Media Video Poster - Instagram Only
Uses existing Instagram username/password (no complex API setup needed)
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# Load environment variables
load_dotenv()

# === CONFIGURATION ===
# Directory settings (matches upscale_4k_parallel.py)
COMFYUI_OUTPUT_DIR_BASE = Path(r"H:\dancers_content")
UPSCALE_SUBFOLDER = "4k_upscaled"
COMPILED_SUBFOLDER = "compiled"

# Instagram credentials
INSTA_USERNAME = os.getenv("INSTA_USERNAME")
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD")

# Settings
DELAY_BETWEEN_UPLOADS_SECONDS = 300  # 5 minutes between uploads
POSTED_LOG_FILE = Path("posted_videos_simple.json")

class SimpleInstagramPoster:
    def __init__(self):
        self.client = None
        self.validate_credentials()
    
    def validate_credentials(self):
        """Validate Instagram credentials."""
        if not all([INSTA_USERNAME, INSTA_PASSWORD]):
            print("❌ Missing Instagram credentials in .env file")
            print("   Required: INSTA_USERNAME, INSTA_PASSWORD")
            sys.exit(1)
        
        print("✅ Instagram credentials found")
    
    def login(self):
        """Login to Instagram."""
        self.client = Client()
        session_file = Path(f"{INSTA_USERNAME}_session.json")
        
        print("🔐 Logging into Instagram...")
        
        try:
            # Try to load existing session
            if session_file.exists():
                print("   📱 Loading existing session...")
                self.client.load_settings(session_file)
            
            # Login
            self.client.login(INSTA_USERNAME, INSTA_PASSWORD)
            
            if not self.client.user_id:
                raise LoginRequired("Login verification failed")
            
            # Save session
            self.client.dump_settings(session_file)
            
            print(f"✅ Successfully logged in as: @{self.client.username}")
            return True
            
        except LoginRequired as e:
            print(f"❌ Login failed: {e}")
            print("   This might be due to:")
            print("   • 2FA required")
            print("   • Suspicious login detected")
            print("   • Rate limiting")
            return False
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def post_video(self, video_path: Path, caption: str = "") -> bool:
        """Post video to Instagram."""
        if not self.client:
            print("❌ Not logged in to Instagram")
            return False
        
        try:
            print(f"📤 Uploading: {video_path.name}")
            
            # Upload as reel
            self.client.clip_upload(
                path=str(video_path),
                caption=caption
            )
            
            print("✅ Upload successful!")
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False

def get_posted_videos():
    """Load list of posted videos."""
    if not POSTED_LOG_FILE.exists():
        return []
    try:
        with open(POSTED_LOG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def add_to_posted_log(video_path: Path, success: bool):
    """Add video to posted log."""
    posted_list = get_posted_videos()
    posted_list.append({
        "filename": video_path.name,
        "path": str(video_path),
        "posted_at": datetime.now().isoformat(),
        "success": success
    })
    with open(POSTED_LOG_FILE, 'w') as f:
        json.dump(posted_list, f, indent=4)

def find_latest_upscaled_videos():
    """Find the latest upscaled videos."""
    if not COMFYUI_OUTPUT_DIR_BASE.is_dir():
        print(f"❌ Base directory not found: {COMFYUI_OUTPUT_DIR_BASE}")
        return []
    
    # Find latest Run folder
    print("🔍 Searching for latest Run folder...")
    try:
        run_folders = sorted(
            [d for d in COMFYUI_OUTPUT_DIR_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not run_folders:
            print("❌ No Run folders found")
            return []
        
        latest_run = run_folders[0]
        print(f"📁 Using latest run: {latest_run.name}")
        
    except Exception as e:
        print(f"❌ Error finding Run folder: {e}")
        return []
    
    # Find upscaled videos
    upscaled_dir = latest_run / UPSCALE_SUBFOLDER / COMPILED_SUBFOLDER
    if not upscaled_dir.is_dir():
        print(f"❌ Upscaled directory not found: {upscaled_dir}")
        return []
    
    print(f"📂 Scanning: {upscaled_dir}")
    all_videos = sorted(upscaled_dir.glob("*_upscaled.mp4"), key=lambda p: p.stat().st_ctime)
    print(f"📹 Found {len(all_videos)} upscaled videos total")
    
    # Filter out already posted successful uploads
    posted_videos = get_posted_videos()
    successfully_posted = [item.get('filename') for item in posted_videos if item.get('success')]
    
    unposted = [v for v in all_videos if v.name not in successfully_posted]
    print(f"📤 Found {len(unposted)} unposted videos")
    
    return unposted

def main():
    print("=" * 60)
    print("📱 SIMPLE INSTAGRAM VIDEO POSTER")
    print("🎬 Auto-upload upscaled videos to Instagram")
    print("=" * 60)
    
    # Initialize poster
    poster = SimpleInstagramPoster()
    
    # Login
    if not poster.login():
        print("❌ Failed to login to Instagram")
        sys.exit(1)
    
    # Find videos to post
    videos_to_post = find_latest_upscaled_videos()
    
    if not videos_to_post:
        print("✨ All videos already posted or no new videos found!")
        sys.exit(0)
    
    print(f"\n🎯 Will upload {len(videos_to_post)} videos")
    print(f"⏱️  Estimated time: {len(videos_to_post) * 5} minutes")
    
    # Confirm before starting
    try:
        response = input(f"\n🚀 Ready to upload {len(videos_to_post)} videos? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Upload cancelled")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n❌ Upload cancelled")
        sys.exit(0)
    
    # Process each video
    successful = 0
    failed = 0
    
    for i, video_path in enumerate(videos_to_post):
        print(f"\n{'='*60}")
        print(f"🎬 Video {i+1}/{len(videos_to_post)}: {video_path.name}")
        print(f"{'='*60}")
        
        # Upload video
        success = poster.post_video(video_path)
        
        # Log result
        add_to_posted_log(video_path, success)
        
        if success:
            successful += 1
            print("✅ Upload completed successfully!")
        else:
            failed += 1
            print("❌ Upload failed!")
        
        # Wait before next upload (except for last video)
        if i < len(videos_to_post) - 1:
            print(f"⏳ Waiting {DELAY_BETWEEN_UPLOADS_SECONDS} seconds before next upload...")
            time.sleep(DELAY_BETWEEN_UPLOADS_SECONDS)
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 UPLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful uploads: {successful}")
    print(f"❌ Failed uploads: {failed}")
    print(f"📹 Total videos: {len(videos_to_post)}")
    print(f"📈 Success rate: {(successful/len(videos_to_post)*100):.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()