#!/usr/bin/env python3
"""
Instagram Graph API Video Poster
Safe, compliant Instagram video posting using official Instagram Graph API
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# === CONFIGURATION ===
# Instagram Graph API credentials
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")  # Instagram Business Account ID
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")  # Facebook Page ID

# Directory settings
DANCERS_CONTENT_BASE = Path(r"H:\dancers_content")
UPSCALED_SUBFOLDER = "4k_upscaled"
COMPILED_SUBFOLDER = "compiled"

# Tracking file
POSTED_LOG_FILE = Path("posted_videos_graph_api.json")

# Upload settings
DELAY_BETWEEN_UPLOADS_SECONDS = 600  # 10 minutes between uploads (be conservative)
MAX_UPLOADS_PER_RUN = 5  # Limit uploads per run to avoid rate limits

# Instagram Graph API endpoints
GRAPH_API_VERSION = "v18.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

class InstagramGraphAPIPoster:
    def __init__(self):
        self.access_token = INSTAGRAM_ACCESS_TOKEN
        self.instagram_user_id = INSTAGRAM_USER_ID
        self.page_id = INSTAGRAM_PAGE_ID
        
        # Validate credentials
        if not all([self.access_token, self.instagram_user_id]):
            print("❌ ERROR: Missing Instagram Graph API credentials in .env file")
            print("Required: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID")
            sys.exit(1)
    
    def test_credentials(self):
        """Test if Instagram credentials are valid."""
        print("🔍 Testing Instagram Graph API credentials...")
        
        url = f"{GRAPH_BASE_URL}/{self.instagram_user_id}"
        params = {
            "access_token": self.access_token,
            "fields": "account_type,username,name"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            username = data.get('username', 'Unknown')
            account_type = data.get('account_type', 'Unknown')
            
            print(f"✅ Connected to Instagram: @{username} ({account_type})")
            
            if account_type != 'BUSINESS':
                print("⚠️  WARNING: Account should be BUSINESS type for posting")
                return False
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Instagram API test failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return False
    
    def upload_video_to_instagram(self, video_path: Path, caption: str = "") -> bool:
        """Upload video to Instagram using Graph API."""
        print(f"📤 Uploading: {video_path.name}")
        
        try:
            # Step 1: Create media container
            container_id = self._create_media_container(video_path, caption)
            if not container_id:
                return False
            
            # Step 2: Wait for processing
            if not self._wait_for_processing(container_id):
                return False
            
            # Step 3: Publish media
            media_id = self._publish_media(container_id)
            if not media_id:
                return False
            
            print(f"✅ Successfully uploaded! Media ID: {media_id}")
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    def _create_media_container(self, video_path: Path, caption: str) -> str:
        """Create media container for video upload."""
        print("   📦 Creating media container...")
        
        url = f"{GRAPH_BASE_URL}/{self.instagram_user_id}/media"
        
        # Read video file
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {
                'access_token': self.access_token,
                'media_type': 'REELS',  # Use REELS for better reach
                'caption': caption
            }
            
            try:
                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()
                result = response.json()
                
                container_id = result.get('id')
                if container_id:
                    print(f"   ✅ Container created: {container_id}")
                    return container_id
                else:
                    print(f"   ❌ No container ID in response: {result}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Container creation failed: {e}")
                if hasattr(e, 'response') and e.response:
                    print(f"   Response: {e.response.text}")
                return None
    
    def _wait_for_processing(self, container_id: str, max_wait: int = 300) -> bool:
        """Wait for video processing to complete."""
        print("   ⏳ Waiting for video processing...")
        
        url = f"{GRAPH_BASE_URL}/{container_id}"
        params = {
            'access_token': self.access_token,
            'fields': 'status_code,status'
        }
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                status_code = data.get('status_code')
                status = data.get('status', 'Unknown')
                
                print(f"   📊 Status: {status} (Code: {status_code})")
                
                if status_code == 'FINISHED':
                    print("   ✅ Processing complete!")
                    return True
                elif status_code == 'ERROR':
                    print(f"   ❌ Processing failed: {status}")
                    return False
                elif status_code in ['IN_PROGRESS', 'PROCESSING']:
                    print("   ⏳ Still processing, waiting 10 seconds...")
                    time.sleep(10)
                else:
                    print(f"   ⚠️  Unknown status: {status_code}")
                    time.sleep(10)
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Status check failed: {e}")
                time.sleep(10)
        
        print("   ❌ Processing timeout reached")
        return False
    
    def _publish_media(self, container_id: str) -> str:
        """Publish the media container."""
        print("   🚀 Publishing media...")
        
        url = f"{GRAPH_BASE_URL}/{self.instagram_user_id}/media_publish"
        data = {
            'access_token': self.access_token,
            'creation_id': container_id
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            result = response.json()
            
            media_id = result.get('id')
            if media_id:
                print(f"   ✅ Published! Media ID: {media_id}")
                return media_id
            else:
                print(f"   ❌ No media ID in response: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Publishing failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return None

def get_posted_videos():
    """Load list of already posted videos."""
    if not POSTED_LOG_FILE.exists():
        return []
    try:
        with open(POSTED_LOG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def add_to_posted_log(video_path: Path):
    """Add video to posted log."""
    posted_list = get_posted_videos()
    posted_list.append({
        "filename": video_path.name,
        "path": str(video_path),
        "posted_at": datetime.now().isoformat()
    })
    with open(POSTED_LOG_FILE, 'w') as f:
        json.dump(posted_list, f, indent=4)

def find_unposted_upscaled_videos():
    """Find unposted upscaled videos."""
    print("🔍 Searching for latest Run folder...")
    
    try:
        run_folders = sorted(
            [d for d in DANCERS_CONTENT_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not run_folders:
            print("❌ No Run folders found")
            return []
        
        latest_run = run_folders[0]
        print(f"📁 Using: {latest_run.name}")
        
    except Exception as e:
        print(f"❌ Error finding Run folder: {e}")
        return []
    
    upscaled_dir = latest_run / UPSCALED_SUBFOLDER / COMPILED_SUBFOLDER
    if not upscaled_dir.exists():
        print(f"❌ Directory not found: {upscaled_dir}")
        return []
    
    print(f"📂 Scanning: {upscaled_dir}")
    
    # Find upscaled videos
    all_videos = sorted(upscaled_dir.glob("*_upscaled.mp4"), key=lambda p: p.stat().st_ctime)
    print(f"📹 Found {len(all_videos)} upscaled videos")
    
    # Filter out already posted
    posted_videos = get_posted_videos()
    posted_filenames = [item.get('filename') if isinstance(item, dict) else item for item in posted_videos]
    
    unposted = [v for v in all_videos if v.name not in posted_filenames]
    print(f"📤 Found {len(unposted)} unposted videos")
    
    return unposted

def main():
    print("=" * 60)
    print("📱 Instagram Graph API Video Poster")
    print("=" * 60)
    
    # Initialize poster
    poster = InstagramGraphAPIPoster()
    
    # Test credentials
    if not poster.test_credentials():
        print("❌ Credential test failed. Please check your .env file.")
        sys.exit(1)
    
    # Find videos to post
    videos_to_post = find_unposted_upscaled_videos()
    
    if not videos_to_post:
        print("✨ All videos already posted!")
        sys.exit(0)
    
    # Limit uploads per run
    if len(videos_to_post) > MAX_UPLOADS_PER_RUN:
        print(f"⚠️  Found {len(videos_to_post)} videos, limiting to {MAX_UPLOADS_PER_RUN} per run")
        videos_to_post = videos_to_post[:MAX_UPLOADS_PER_RUN]
    
    print(f"📤 Will upload {len(videos_to_post)} videos")
    
    # Upload videos
    successful = 0
    failed = 0
    
    for i, video_path in enumerate(videos_to_post):
        print(f"\n{'='*60}")
        print(f"📹 Video {i+1}/{len(videos_to_post)}: {video_path.name}")
        print(f"{'='*60}")
        
        if poster.upload_video_to_instagram(video_path):
            add_to_posted_log(video_path)
            successful += 1
            print(f"✅ Upload successful!")
        else:
            failed += 1
            print(f"❌ Upload failed!")
        
        # Wait between uploads (except for last video)
        if i < len(videos_to_post) - 1:
            print(f"⏳ Waiting {DELAY_BETWEEN_UPLOADS_SECONDS} seconds before next upload...")
            time.sleep(DELAY_BETWEEN_UPLOADS_SECONDS)
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 UPLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📹 Total: {len(videos_to_post)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()