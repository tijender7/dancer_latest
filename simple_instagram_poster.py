import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# ==============================================================================
#  CONFIGURATION
# ==============================================================================
# Load environment variables from .env file
load_dotenv()

# --- Instagram Credentials ---
INSTA_USERNAME = os.getenv("INSTA_USERNAME")
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD")

# --- Directory Settings (Must match your video cropper script) ---
DANCERS_CONTENT_BASE = Path(r"H:\dancers_content")
UPSCALED_SUBFOLDER = "4k_upscaled"
COMPILED_SUBFOLDER = "compiled"
REELS_SUBFOLDER = "reels"

# --- Tracking File ---
POSTED_LOG_FILE = Path("posted_videos.json")

# --- UPLOAD DELAY ---
# IMPORTANT: Delay in seconds between each upload to avoid spamming Instagram's API.
# 300 seconds = 5 minutes. 600 = 10 minutes.
# Do not set this too low. A value between 300 and 900 is recommended.
DELAY_BETWEEN_UPLOADS_SECONDS = 300 

# ==============================================================================
#  HELPER FUNCTIONS (Same as before, with minor logging adjustments)
# ==============================================================================

def login_to_instagram(client: Client):
    """Logs into Instagram, using a cached session if available."""
    session_file = Path(f"{INSTA_USERNAME}_session.json")
    print("INFO: Attempting to log in to Instagram...")
    try:
        if session_file.exists():
            client.load_settings(session_file)
            print("INFO: Loaded existing session.")
        
        client.login(INSTA_USERNAME, INSTA_PASSWORD)
        if not client.user_id:
            raise LoginRequired("Login check failed. 2FA might be required.")
        client.dump_settings(session_file)
        print(f"✅ SUCCESS: Logged in as '{client.username}'.")
        return True
    except LoginRequired:
        print("\n❌ CRITICAL: Login failed. Session invalid or 2FA required.")
        return False
    except Exception as e:
        print(f"\n❌ CRITICAL: An unexpected error during login: {e}\n")
        return False

def get_posted_videos():
    """Loads the list of already posted video filenames from the log file."""
    if not POSTED_LOG_FILE.exists():
        return []
    try:
        with open(POSTED_LOG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def add_to_posted_log(video_path: Path):
    """Adds a video filename to the log of posted videos."""
    posted_list = get_posted_videos()
    posted_list.append(video_path.name)
    with open(POSTED_LOG_FILE, 'w') as f:
        json.dump(posted_list, f, indent=4)
    # No print statement here, we will summarize at the end.

def find_all_unposted_upscaled_videos():
    """
    Finds ALL upscaled videos that have not yet been posted.
    Returns a list of Path objects.
    """
    print("INFO: Searching for the latest 'Run_*' folder...")
    try:
        run_folders = sorted(
            [d for d in DANCERS_CONTENT_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not run_folders:
            print("ERROR: No 'Run_*' folders found.")
            return []
        latest_run_folder = run_folders[0]
        print(f"INFO: Using latest run folder: {latest_run_folder.name}")
    except Exception as e:
        print(f"ERROR: Could not find latest run folder: {e}")
        return []

    upscaled_dir = latest_run_folder / UPSCALED_SUBFOLDER / COMPILED_SUBFOLDER
    if not upscaled_dir.is_dir():
        print(f"ERROR: Upscaled directory not found at: {upscaled_dir}")
        return []

    print(f"INFO: Scanning for unposted upscaled videos in: {upscaled_dir}")
    posted_videos = get_posted_videos()
    all_upscaled = sorted(upscaled_dir.glob("*_upscaled.mp4"), key=lambda p: p.stat().st_ctime)
    
    print(f"INFO: Found {len(all_upscaled)} upscaled videos total")
    
    unposted_videos = [
        video_path for video_path in all_upscaled if video_path.name not in posted_videos
    ]
    
    print(f"INFO: Found {len(unposted_videos)} unposted upscaled videos")
    return unposted_videos

# ==============================================================================
#  MAIN SCRIPT LOGIC
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Instagram Manual Bulk Reel Uploader")
    print("=" * 60)

    # Validate configuration
    if not all([INSTA_USERNAME, INSTA_PASSWORD]):
        print("CRITICAL: INSTA_USERNAME or INSTA_PASSWORD not set in .env file. Exiting.")
        sys.exit(1)
    if not DANCERS_CONTENT_BASE.is_dir():
        print(f"CRITICAL: Base directory not found: {DANCERS_CONTENT_BASE}. Exiting.")
        sys.exit(1)

    # Initialize the Instagram client
    client = Client()

    # Step 1: Login
    if not login_to_instagram(client):
        sys.exit(1)

    # Step 2: Find all videos to post
    videos_to_post = find_all_unposted_upscaled_videos()

    if not videos_to_post:
        print("\n✨ All videos are already posted. Nothing to do.")
        sys.exit(0)

    total_videos = len(videos_to_post)
    print(f"\n▶️ Found {total_videos} new upscaled videos to upload.")
    
    successful_uploads = 0
    failed_uploads = 0

    # Step 3: Loop and upload all videos
    for i, video_path in enumerate(videos_to_post):
        print("-" * 60)
        print(f"UPLOADING VIDEO {i + 1} of {total_videos}: '{video_path.name}'")
        
        try:
            client.clip_upload(
                path=video_path,
                caption=""  # No caption, as requested
            )
            print(f"  ✅ SUCCESS: Uploaded successfully!")
            add_to_posted_log(video_path)
            successful_uploads += 1

            # If this is not the last video, wait before uploading the next one
            if i < total_videos - 1:
                print(f"  ⏳ WAITING for {DELAY_BETWEEN_UPLOADS_SECONDS} seconds before next upload...")
                time.sleep(DELAY_BETWEEN_UPLOADS_SECONDS)

        except Exception as e:
            print(f"  ❌ FAILED: The upload for '{video_path.name}' failed.")
            print(f"     Error details: {e}")
            print("     This video will be skipped and retried on the next run.")
            failed_uploads += 1
            # Optional: Add a shorter wait time after a failure
            if i < total_videos - 1:
                print("  ⏳ WAITING for 60 seconds after failure before trying the next video...")
                time.sleep(60)

    # Step 4: Final Summary
    print("\n" + "=" * 60)
    print("BULK UPLOAD COMPLETE")
    print("-" * 60)
    print(f"  Successful uploads: {successful_uploads}")
    print(f"  Failed uploads:     {failed_uploads}")
    print(f"  Total processed:    {total_videos}")
    print("=" * 60)