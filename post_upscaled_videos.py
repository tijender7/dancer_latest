#!/usr/bin/env python3
"""
Unified Social Media Video Poster
Automatically posts upscaled videos to Facebook and Instagram after upscale_4k_parallel.py completes.
Monitors the upscale output directory and posts new videos to both platforms.
"""

import os
import sys
import json
import time
import requests
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

# Social media credentials
INSTA_USERNAME = os.getenv("INSTA_USERNAME")
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

# Upload settings
DELAY_BETWEEN_PLATFORMS = 60  # 1 minute between Instagram and Facebook
DELAY_BETWEEN_VIDEOS = 300   # 5 minutes between different videos
POSTED_LOG_FILE = Path("posted_videos_unified.json")

# Facebook Graph API
GRAPH_API_VERSION = "v18.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

class SocialMediaPoster:
    def __init__(self):
        self.instagram_client = None
        self.validate_credentials()
    
    def validate_credentials(self):
        """Validate all required credentials."""
        required_instagram = [INSTA_USERNAME, INSTA_PASSWORD]
        optional_graph = [INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID]
        optional_facebook = [FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID]
        
        if not all(required_instagram):
            print("❌ Missing Instagram credentials (INSTA_USERNAME, INSTA_PASSWORD)")
            sys.exit(1)
        
        # Check which platforms are available
        self.use_instagram_basic = True
        self.use_instagram_graph = all(optional_graph)
        self.use_facebook = all(optional_facebook)
        
        print(f"✅ Instagram Basic API: {'Enabled' if self.use_instagram_basic else 'Disabled'}")
        print(f"✅ Instagram Graph API: {'Enabled' if self.use_instagram_graph else 'Disabled'}")
        print(f"✅ Facebook Pages API: {'Enabled' if self.use_facebook else 'Disabled'}")
        
        if not any([self.use_instagram_basic, self.use_instagram_graph, self.use_facebook]):
            print("❌ No social media platforms configured!")
            sys.exit(1)
    
    def login_instagram_basic(self):
        """Login to Instagram using basic API."""
        if not self.use_instagram_basic:
            return False
            
        self.instagram_client = Client()
        session_file = Path(f"{INSTA_USERNAME}_session.json")
        
        try:
            if session_file.exists():
                self.instagram_client.load_settings(session_file)
            
            self.instagram_client.login(INSTA_USERNAME, INSTA_PASSWORD)
            if not self.instagram_client.user_id:
                raise LoginRequired("Login check failed")
            
            self.instagram_client.dump_settings(session_file)
            print(f"✅ Instagram Basic: Logged in as {self.instagram_client.username}")
            return True
            
        except Exception as e:
            print(f"❌ Instagram Basic login failed: {e}")
            return False
    
    def post_to_instagram_basic(self, video_path: Path, caption: str = "") -> bool:
        """Post video to Instagram using basic API."""
        if not self.use_instagram_basic or not self.instagram_client:
            return False
            
        try:
            print(f"📤 Posting to Instagram (Basic): {video_path.name}")
            self.instagram_client.clip_upload(path=video_path, caption=caption)
            print("✅ Instagram Basic: Upload successful!")
            return True
        except Exception as e:
            print(f"❌ Instagram Basic upload failed: {e}")
            return False
    
    def post_to_instagram_graph(self, video_path: Path, caption: str = "") -> bool:
        """Post video to Instagram using Graph API."""
        if not self.use_instagram_graph:
            return False
            
        try:
            print(f"📤 Posting to Instagram (Graph): {video_path.name}")
            
            # Create media container
            container_id = self._create_instagram_container(video_path, caption)
            if not container_id:
                return False
            
            # Wait for processing
            if not self._wait_for_instagram_processing(container_id):
                return False
            
            # Publish
            media_id = self._publish_instagram_media(container_id)
            if media_id:
                print("✅ Instagram Graph: Upload successful!")
                return True
            
        except Exception as e:
            print(f"❌ Instagram Graph upload failed: {e}")
        
        return False
    
    def post_to_facebook(self, video_path: Path, caption: str = "") -> bool:
        """Post video to Facebook Page."""
        if not self.use_facebook:
            return False
            
        try:
            print(f"📤 Posting to Facebook: {video_path.name}")
            
            url = f"{GRAPH_BASE_URL}/{FACEBOOK_PAGE_ID}/videos"
            
            with open(video_path, 'rb') as video_file:
                files = {'file': video_file}
                data = {
                    'access_token': FACEBOOK_PAGE_ACCESS_TOKEN,
                    'description': caption,
                    'published': 'true'
                }
                
                response = requests.post(url, files=files, data=data, timeout=600)
                response.raise_for_status()
                result = response.json()
                
                if result.get('id'):
                    print(f"✅ Facebook: Upload successful! Post ID: {result['id']}")
                    return True
                else:
                    print(f"❌ Facebook: No post ID in response: {result}")
                    return False
                    
        except Exception as e:
            print(f"❌ Facebook upload failed: {e}")
            return False
    
    def _create_instagram_container(self, video_path: Path, caption: str) -> str:
        """Create Instagram media container."""
        url = f"{GRAPH_BASE_URL}/{INSTAGRAM_USER_ID}/media"
        
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {
                'access_token': INSTAGRAM_ACCESS_TOKEN,
                'media_type': 'REELS',
                'caption': caption
            }
            
            response = requests.post(url, files=files, data=data, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get('id')
    
    def _wait_for_instagram_processing(self, container_id: str, max_wait: int = 300) -> bool:
        """Wait for Instagram video processing."""
        url = f"{GRAPH_BASE_URL}/{container_id}"
        params = {
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'fields': 'status_code'
        }
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            status_code = data.get('status_code')
            if status_code == 'FINISHED':
                return True
            elif status_code == 'ERROR':
                return False
            
            time.sleep(10)
        
        return False
    
    def _publish_instagram_media(self, container_id: str) -> str:
        """Publish Instagram media."""
        url = f"{GRAPH_BASE_URL}/{INSTAGRAM_USER_ID}/media_publish"
        data = {
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'creation_id': container_id
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()
        return result.get('id')
    
    def post_video_to_all_platforms(self, video_path: Path) -> dict:
        """Post video to all configured platforms."""
        results = {
            'instagram_basic': False,
            'instagram_graph': False,
            'facebook': False
        }
        
        print(f"\n🎬 Processing: {video_path.name}")
        print("=" * 60)
        
        # Post to Instagram (prefer Graph API if available)
        if self.use_instagram_graph:
            results['instagram_graph'] = self.post_to_instagram_graph(video_path)
            if results['instagram_graph']:
                time.sleep(DELAY_BETWEEN_PLATFORMS)
        elif self.use_instagram_basic:
            results['instagram_basic'] = self.post_to_instagram_basic(video_path)
            if results['instagram_basic']:
                time.sleep(DELAY_BETWEEN_PLATFORMS)
        
        # Post to Facebook
        if self.use_facebook:
            results['facebook'] = self.post_to_facebook(video_path)
        
        return results

def get_posted_videos():
    """Load list of posted videos."""
    if not POSTED_LOG_FILE.exists():
        return []
    try:
        with open(POSTED_LOG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def add_to_posted_log(video_path: Path, results: dict):
    """Add video to posted log with platform results."""
    posted_list = get_posted_videos()
    posted_list.append({
        "filename": video_path.name,
        "path": str(video_path),
        "posted_at": datetime.now().isoformat(),
        "platforms": results,
        "success": any(results.values())
    })
    with open(POSTED_LOG_FILE, 'w') as f:
        json.dump(posted_list, f, indent=4)

def find_latest_upscaled_videos():
    """Find the latest upscaled videos that haven't been posted."""
    if not COMFYUI_OUTPUT_DIR_BASE.is_dir():
        print(f"❌ Base directory not found: {COMFYUI_OUTPUT_DIR_BASE}")
        return []
    
    # Find latest Run folder
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
    print(f"📹 Found {len(all_videos)} upscaled videos")
    
    # Filter out already posted
    posted_videos = get_posted_videos()
    posted_filenames = [item.get('filename') for item in posted_videos if item.get('success')]
    
    unposted = [v for v in all_videos if v.name not in posted_filenames]
    print(f"📤 Found {len(unposted)} unposted videos")
    
    return unposted

def main():
    print("=" * 70)
    print("🚀 UNIFIED SOCIAL MEDIA VIDEO POSTER")
    print("📱 Instagram + Facebook Automation")
    print("=" * 70)
    
    # Initialize poster
    poster = SocialMediaPoster()
    
    # Login to Instagram Basic if needed
    if poster.use_instagram_basic:
        if not poster.login_instagram_basic():
            print("❌ Instagram Basic login failed")
            if not poster.use_instagram_graph and not poster.use_facebook:
                sys.exit(1)
    
    # Find videos to post
    videos_to_post = find_latest_upscaled_videos()
    
    if not videos_to_post:
        print("✨ All videos already posted or no new videos found!")
        sys.exit(0)
    
    print(f"\n🎯 Will process {len(videos_to_post)} videos")
    
    # Process each video
    successful_videos = 0
    total_platforms_success = 0
    total_platforms_attempted = 0
    
    for i, video_path in enumerate(videos_to_post):
        print(f"\n🎬 Video {i+1}/{len(videos_to_post)}")
        
        # Post to all platforms
        results = poster.post_video_to_all_platforms(video_path)
        
        # Track results
        successful_platforms = sum(results.values())
        attempted_platforms = len([k for k, v in results.items() if poster.__dict__.get(f'use_{k.split("_")[0]}', False)])
        
        total_platforms_success += successful_platforms
        total_platforms_attempted += attempted_platforms
        
        if successful_platforms > 0:
            successful_videos += 1
        
        # Log the result
        add_to_posted_log(video_path, results)
        
        # Summary for this video
        print(f"📊 Results: {successful_platforms}/{attempted_platforms} platforms successful")
        
        # Wait before next video (except for last one)
        if i < len(videos_to_post) - 1:
            print(f"⏳ Waiting {DELAY_BETWEEN_VIDEOS} seconds before next video...")
            time.sleep(DELAY_BETWEEN_VIDEOS)
    
    # Final summary
    print(f"\n{'='*70}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Videos processed: {successful_videos}/{len(videos_to_post)}")
    print(f"🎯 Platform uploads: {total_platforms_success}/{total_platforms_attempted}")
    print(f"📈 Success rate: {(total_platforms_success/total_platforms_attempted*100):.1f}%" if total_platforms_attempted > 0 else "N/A")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()