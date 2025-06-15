import os
import sys
import time
import json
import pickle
import random
from pathlib import Path

# --- Google API Libraries ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ==============================================================================
#  CONFIGURATION
# ==============================================================================

# --- File Paths ---
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_PICKLE_FILE = 'youtube_token.pickle'
CONTENT_PLAN_FILE = 'content_plan.json'  # ** NEW: The file for all our text content **
POSTED_LOG_FILE = Path("posted_to_youtube.json")

# --- Directory Settings ---
DANCERS_CONTENT_BASE = Path(r"H:\dancers_content")
UPSCALED_SUBFOLDER = "4k_upscaled"
COMPILED_SUBFOLDER = "compiled"
REELS_SUBFOLDER = "reels"

# --- API and Upload Settings ---
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
MIN_DELAY_SECONDS = 180  # 3 minutes
MAX_DELAY_SECONDS = 480  # 8 minutes
VIDEO_PRIVACY_STATUS = "public"
ENABLE_AGE_RESTRICTION = True  # ** NEW: Toggle for 18+ age restriction **

# ==============================================================================
#  HELPER FUNCTIONS (Authentication, Logging, etc.)
# ==============================================================================

def get_authenticated_service():
    creds = None
    token_pickle_path = Path(TOKEN_PICKLE_FILE)
    if token_pickle_path.exists():
        with open(token_pickle_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_pickle_path, 'wb') as token:
            pickle.dump(creds, token)
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def load_content_plan():
    """Loads the title/description/tag combinations from the JSON file."""
    try:
        with open(CONTENT_PLAN_FILE, 'r') as f:
            plan = json.load(f)
            if "content_blocks" not in plan or not plan["content_blocks"]:
                print(f"❌ CRITICAL: Your '{CONTENT_PLAN_FILE}' is missing 'content_blocks' or is empty.")
                return None
            return plan["content_blocks"]
    except FileNotFoundError:
        print(f"❌ CRITICAL: The content plan file '{CONTENT_PLAN_FILE}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"❌ CRITICAL: Could not decode '{CONTENT_PLAN_FILE}'. Please check for JSON errors.")
        return None

def get_posted_videos():
    if not POSTED_LOG_FILE.exists(): return []
    try:
        with open(POSTED_LOG_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return []

def add_to_posted_log(video_path: Path):
    posted_list = get_posted_videos()
    posted_list.append(video_path.name)
    with open(POSTED_LOG_FILE, 'w') as f: json.dump(posted_list, f, indent=4)

def find_all_unposted_videos():
    try:
        run_folders = sorted(
            [d for d in DANCERS_CONTENT_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime, reverse=True
        )
        if not run_folders:
            print("ERROR: No 'Run_*' folders found."); return []
        reels_dir = run_folders[0] / UPSCALED_SUBFOLDER / COMPILED_SUBFOLDER / REELS_SUBFOLDER
        if not reels_dir.is_dir():
            print(f"ERROR: Reels directory not found at: {reels_dir}"); return []
    except Exception as e:
        print(f"ERROR: Could not find run folder: {e}"); return []
    
    posted_videos = get_posted_videos()
    all_reels = sorted(reels_dir.glob("*.mp4"), key=lambda p: p.stat().st_ctime)
    return [p for p in all_reels if p.name not in posted_videos]

def create_upload_request_body(chosen_content):
    """Creates the request body with proper age restriction settings."""
    request_body = {
        "snippet": {
            "title": chosen_content["title_template"],
            "description": chosen_content["description_template"],
            "tags": chosen_content["tags"],
            "categoryId": "17"  # 17=Sports, 24=Entertainment
        },
        "status": {
            "privacyStatus": VIDEO_PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False  # ** NEW: Explicit declaration **
        }
    }
    
    # ** NEW: Add age restriction if enabled **
    if ENABLE_AGE_RESTRICTION:
        request_body["contentDetails"] = {
            "contentRating": {
                "ytRating": "ytAgeRestricted"
            }
        }
    
    return request_body

# ==============================================================================
#  MAIN SCRIPT LOGIC
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("YouTube Shorts Uploader with Age Restriction")
    print("=" * 60)
    
    if ENABLE_AGE_RESTRICTION:
        print("🔞 AGE RESTRICTION: Enabled (18+ only)")
    else:
        print("👨‍👩‍👧‍👦 AGE RESTRICTION: Disabled (All ages)")

    # Step 1: Load the content plan from JSON
    print(f"INFO: Loading content from '{CONTENT_PLAN_FILE}'...")
    content_blocks = load_content_plan()
    if not content_blocks:
        sys.exit(1)
    print(f"✅ INFO: Successfully loaded {len(content_blocks)} content blocks.")

    # Step 2: Authenticate with Google
    try:
        youtube_service = get_authenticated_service()
    except Exception as e:
        print(f"❌ CRITICAL: Authentication failed: {e}"); sys.exit(1)

    # Step 3: Find videos to upload
    videos_to_upload = find_all_unposted_videos()
    if not videos_to_upload:
        print("\n✨ All videos are already posted. Nothing new to upload."); sys.exit(0)

    total_videos = len(videos_to_upload)
    print(f"\n▶️ Found {total_videos} new videos to upload.")

    # Step 4: Loop and upload each video
    for i, video_path in enumerate(videos_to_upload):
        print("-" * 60)
        print(f"UPLOADING VIDEO {i + 1} of {total_videos}: '{video_path.name}'")
        
        # ** NEW: Randomly select a content block for this video **
        chosen_content = random.choice(content_blocks)
        
        # ** NEW: Use the helper function to create request body **
        request_body = create_upload_request_body(chosen_content)
        
        print(f"  📝 Using title: {request_body['snippet']['title']}")
        if ENABLE_AGE_RESTRICTION:
            print("  🔞 Age restriction: ENABLED (18+ only)")

        try:
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            insert_request = youtube_service.videos().insert(
                part=",".join(request_body.keys()),
                body=request_body,
                media_body=media
            )
            print("  ⏳ Starting upload to YouTube...")
            response = insert_request.execute()
            
            print(f"  ✅ SUCCESS: Uploaded! Video ID: {response.get('id')}")
            add_to_posted_log(video_path)

            if i < total_videos - 1:
                delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"  😴 WAITING for {delay // 60}m {delay % 60}s...")
                time.sleep(delay)

        except HttpError as e:
            print(f"  ❌ FAILED (HTTP Error): {e}")
            # ** NEW: Check if it's a content rating error **
            if "contentRating" in str(e):
                print("  💡 TIP: Try disabling age restriction (set ENABLE_AGE_RESTRICTION = False)")
        except Exception as e:
            print(f"  ❌ FAILED (Unexpected Error): {e}")

    print("\n" + "=" * 60)
    print("✅ SCRIPT FINISHED.")
    print("=" * 60)