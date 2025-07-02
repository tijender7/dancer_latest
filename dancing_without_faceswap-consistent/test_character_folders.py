#!/usr/bin/env python3
"""
Test the updated find_character_folders function
"""
import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

def find_latest_run_folder(base_dir, prefix):
    all_entries = os.listdir(base_dir)
    run_folders = []
    for entry in all_entries:
        full_path = os.path.join(base_dir, entry)
        if os.path.isdir(full_path) and entry.startswith(prefix):
            run_folders.append(full_path)
    if not run_folders:
        raise FileNotFoundError(f"No folders starting with '{prefix}' found under {base_dir}")
    return max(run_folders, key=lambda p: os.path.getmtime(p))

def find_character_folders(latest_run_folder_path):
    """Find all character folders in phase3_videos (character-aware structure)"""
    phase3_videos_dir = None
    
    # Look for phase3_videos directory
    for item in os.listdir(latest_run_folder_path):
        item_path = os.path.join(latest_run_folder_path, item)
        if os.path.isdir(item_path) and "phase3_videos" in item:
            phase3_videos_dir = item_path
            break
    
    if not phase3_videos_dir:
        raise FileNotFoundError(f"No phase3_videos folder found in {latest_run_folder_path}")
    
    # NEW CHARACTER-AWARE STRUCTURE: Look for character folders directly in phase3_videos
    character_folders = {}
    for item in os.listdir(phase3_videos_dir):
        item_path = os.path.join(phase3_videos_dir, item)
        if os.path.isdir(item_path) and item.startswith("character_"):
            character_id = item.replace("character_", "")
            
            # Find the date subdirectory within this character folder
            date_subdirs = [os.path.join(item_path, name) for name in os.listdir(item_path) 
                           if os.path.isdir(os.path.join(item_path, name))]
            
            if date_subdirs:
                # Use the latest date folder for this character
                character_date_dir = max(date_subdirs, key=lambda p: os.path.getmtime(p))
                character_folders[character_id] = character_date_dir
                print(f"✅ Found character_{character_id}: {character_date_dir}")
            else:
                print(f"⚠️ Warning: No date folder found in character_{character_id}")
    
    if not character_folders:
        raise FileNotFoundError(f"No character folders found in {phase3_videos_dir}. Expected character-aware structure: phase3_videos/character_X/date/")
    
    print(f"📁 Total characters found: {len(character_folders)}")
    return character_folders

def main():
    print("🔍 Testing Character-Aware Beat Sync Folder Detection")
    print("=" * 60)
    
    try:
        BASE_DANCERS_DIR = "/mnt/h/dancers_content"
        RUN_PREFIX = "Run_"
        
        latest_run_folder_path = find_latest_run_folder(BASE_DANCERS_DIR, RUN_PREFIX)
        print(f"👉 Latest run folder detected: {latest_run_folder_path}")
        
        character_folders = find_character_folders(latest_run_folder_path)
        print(f"👉 Found {len(character_folders)} characters: {sorted(character_folders.keys())}")
        
        # Test video file detection
        print(f"\n📹 Checking videos in each character folder:")
        for char_id, folder_path in character_folders.items():
            video_files = [f for f in os.listdir(folder_path) if f.endswith('.mp4')]
            print(f"   Character {char_id}: {len(video_files)} videos")
            for video in video_files:
                print(f"      - {video}")
        
        print(f"\n✅ SUCCESS: Character-aware folder detection working!")
        print(f"🎬 Ready for beat sync with {len(character_folders)} characters")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()