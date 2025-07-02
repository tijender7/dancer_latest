#!/usr/bin/env python3
"""
select_best_characters.py

Since we have 19 characters with 1 video each, select the best 3-5 characters
for compilation and create a manageable beat sync process.
"""

import os
import shutil
import re
from pathlib import Path

def find_latest_run_folder():
    """Find the latest run folder"""
    base_dir = Path("/mnt/h/dancers_content")
    run_folders = [f for f in base_dir.iterdir() if f.is_dir() and f.name.startswith("Run_")]
    if not run_folders:
        raise FileNotFoundError("No run folders found")
    return max(run_folders, key=lambda p: p.stat().st_mtime)

def analyze_all_characters():
    """Analyze all 19 characters"""
    print("🔍 Analyzing All Characters...")
    print("=" * 60)
    
    latest_run = find_latest_run_folder()
    print(f"📁 Latest run: {latest_run}")
    
    # Find phase3_videos directory
    phase3_dir = None
    for item in latest_run.iterdir():
        if item.is_dir() and "phase3_videos" in item.name:
            phase3_dir = item
            break
    
    date_dirs = [d for d in phase3_dir.iterdir() if d.is_dir()]
    date_dir = max(date_dirs, key=lambda p: p.stat().st_mtime)
    
    # Get all character folders
    char_folders = [d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith("character_")]
    
    print(f"🎭 Found {len(char_folders)} characters")
    
    # Analyze each character
    characters = {}
    for folder in sorted(char_folders, key=lambda x: int(x.name.split('_')[1])):
        char_id = folder.name.replace("character_", "")
        videos = list(folder.glob("*.mp4"))
        
        if videos:
            video_file = videos[0]
            video_size = video_file.stat().st_size
            characters[char_id] = {
                'folder': folder,
                'video_file': video_file,
                'video_size': video_size
            }
    
    return date_dir, characters

def select_best_characters(characters, num_to_select=4):
    """Select best characters based on video file size (quality indicator)"""
    print(f"\n🎯 Selecting Top {num_to_select} Characters...")
    print("-" * 40)
    
    # Sort by video file size (larger = potentially better quality)
    sorted_chars = sorted(characters.items(), key=lambda x: x[1]['video_size'], reverse=True)
    
    selected = {}
    for i, (char_id, info) in enumerate(sorted_chars[:num_to_select]):
        selected[char_id] = info
        size_mb = info['video_size'] / (1024 * 1024)
        print(f"✅ Character {char_id}: {size_mb:.1f} MB")
    
    print(f"\n📊 Selected {len(selected)} characters for compilation")
    return selected

def create_selected_characters_folder(date_dir, selected_characters):
    """Create a new folder with only selected characters"""
    
    # Create selected_characters subfolder
    selected_dir = date_dir / "selected_characters"
    if selected_dir.exists():
        shutil.rmtree(selected_dir)
    selected_dir.mkdir()
    
    print(f"\n📁 Creating selected characters folder: {selected_dir}")
    
    # Copy selected character folders
    for char_id, info in selected_characters.items():
        src_folder = info['folder']
        dst_folder = selected_dir / f"character_{char_id}"
        shutil.copytree(src_folder, dst_folder)
        print(f"   ✅ Copied character_{char_id}")
    
    return selected_dir

def create_beat_sync_script_for_selected():
    """Create a modified beat sync script that works with selected characters"""
    
    beat_sync_content = '''#!/usr/bin/env python3
"""
beat_sync_selected_characters.py
Modified beat sync that uses only selected characters folder.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to path to import the original script functions
sys.path.append(str(Path(__file__).parent))

# Import everything from the original script
from beat_sync_character_separated import *

def find_character_folders_selected(latest_run_folder_path):
    """Find character folders in the selected_characters directory"""
    phase3_videos_dir = None
    
    # Look for phase3_videos directory
    for item in os.listdir(latest_run_folder_path):
        item_path = os.path.join(latest_run_folder_path, item)
        if os.path.isdir(item_path) and "phase3_videos" in item:
            phase3_videos_dir = item_path
            break
    
    if not phase3_videos_dir:
        raise FileNotFoundError(f"No phase3_videos folder found in {latest_run_folder_path}")
    
    # Look for date subdirectory
    subdirs = [os.path.join(phase3_videos_dir, name) for name in os.listdir(phase3_videos_dir) 
               if os.path.isdir(os.path.join(phase3_videos_dir, name))]
    
    if not subdirs:
        raise FileNotFoundError(f"No date subdirectory found in {phase3_videos_dir}")
    
    date_dir = max(subdirs, key=lambda p: os.path.getmtime(p))
    
    # Look for selected_characters folder
    selected_dir = os.path.join(date_dir, "selected_characters")
    if not os.path.exists(selected_dir):
        raise FileNotFoundError(f"No selected_characters folder found in {date_dir}")
    
    # Find character folders in selected_characters
    character_folders = {}
    for item in os.listdir(selected_dir):
        item_path = os.path.join(selected_dir, item)
        if os.path.isdir(item_path) and item.startswith("character_"):
            character_id = item.replace("character_", "")
            character_folders[character_id] = item_path
    
    if not character_folders:
        raise FileNotFoundError(f"No character folders found in {selected_dir}")
    
    return character_folders

# Override the main execution
if __name__ == "__main__":
    loaded_source_clips = {}
    
    try:
        latest_run_folder_path = find_latest_run_folder(BASE_DANCERS_DIR, RUN_PREFIX)
        print(f"👉 Latest run folder detected: {latest_run_folder_path}")
        
        # Use the selected characters function instead
        character_folders = find_character_folders_selected(latest_run_folder_path)
        print(f"👉 Found {len(character_folders)} SELECTED characters: {list(character_folders.keys())}")

        ALL_VIDEOS_CONTAINER_DIR = os.path.join(latest_run_folder_path, "all_videos")
        TARGET_COMPILED_DIR_FOR_UPSCALER = os.path.join(ALL_VIDEOS_CONTAINER_DIR, "compiled_selected_characters")
        os.makedirs(TARGET_COMPILED_DIR_FOR_UPSCALER, exist_ok=True)
        print(f"Created/found target compiled directory: {TARGET_COMPILED_DIR_FOR_UPSCALER}")

        print(f"📁 Audio source: {INSTAGRAM_AUDIO_DIR}")
        print(f"📁 Output: {TARGET_COMPILED_DIR_FOR_UPSCALER}")

        audio_files = glob.glob(os.path.join(INSTAGRAM_AUDIO_DIR, "*.mp4")) + glob.glob(os.path.join(INSTAGRAM_AUDIO_DIR, "*.mp3"))
        if not audio_files:
            raise ValueError(f"No audio files (.mp4, .mp3) found in {INSTAGRAM_AUDIO_DIR}")
        audio_files.sort()
        print(f"Found {len(audio_files)} audio files")

        # Process each character × audio combination
        successful_renders = 0
        total_combinations = len(character_folders) * len(audio_files)
        
        print(f"\\n🎬 Starting SELECTED character compilation generation...")
        print(f"📊 Total combinations: {total_combinations} ({len(character_folders)} characters × {len(audio_files)} songs)")
        
        for character_id, character_folder in character_folders.items():
            print(f"\\n{'='*80}")
            print(f"🎭 Processing Selected Character {character_id}")
            print(f"📁 Character folder: {character_folder}")
            
            character_video_offset = 0
            
            for audio_file in tqdm(audio_files, desc=f"Character {character_id} Audio Files"):
                
                result_path, next_start_index = process_audio_for_character(
                    audio_file, 
                    character_id,
                    character_folder,
                    loaded_source_clips, 
                    TARGET_COMPILED_DIR_FOR_UPSCALER,
                    start_clip_index=character_video_offset 
                )
                
                if result_path:
                    successful_renders += 1
                    character_video_offset = next_start_index
                    print(f"✅ Successfully created: {os.path.basename(result_path)}")

        print(f"\\n🎉 Complete! Successfully rendered {successful_renders}/{total_combinations} SELECTED character videos")
        print(f"📊 Results:")
        print(f"   - {len(character_folders)} SELECTED characters processed")
        print(f"   - {len(audio_files)} songs processed") 
        print(f"   - {successful_renders} total compilation videos generated")
        print(f"📁 All outputs saved in: {TARGET_COMPILED_DIR_FOR_UPSCALER}")

    except Exception as e:
        print(f"\\n\\nFATAL ERROR: An unhandled exception occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\\n🔒 Finalizing: Closing all cached source video files...")
        for clip_path, clip_obj in loaded_source_clips.items():
            try: 
                if hasattr(clip_obj, 'close'):
                    clip_obj.close()
            except Exception as e_close: 
                print(f"Warning: Error closing {os.path.basename(clip_path)}: {e_close}")
        loaded_source_clips.clear()
        print("Script execution finished.")
'''
    
    script_path = Path("/mnt/d/Comfy_UI_V20/ComfyUI/output/dancer/dancing_without_faceswap-consistent/beat_sync_selected_characters.py")
    with open(script_path, 'w') as f:
        f.write(beat_sync_content)
    
    print(f"✅ Created: {script_path}")
    return script_path

def main():
    """Main function"""
    print("🚀 Select Best Characters for Compilation")
    print("=" * 60)
    
    try:
        # Analyze all characters
        date_dir, all_characters = analyze_all_characters()
        
        if len(all_characters) <= 4:
            print(f"✅ Only {len(all_characters)} characters found - using all of them")
            selected = all_characters
        else:
            # Select best 4 characters
            selected = select_best_characters(all_characters, num_to_select=4)
        
        # Create selected characters folder
        selected_dir = create_selected_characters_folder(date_dir, selected)
        
        # Create modified beat sync script
        beat_sync_script = create_beat_sync_script_for_selected()
        
        # Calculate output
        audio_dir = Path("/mnt/d/Comfy_UI_V20/ComfyUI/output/dancer/instagram_audio")
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.mp4"))
        total_compilations = len(selected) * len(audio_files)
        
        print(f"\n🎉 Setup Complete!")
        print(f"📁 Selected characters: {selected_dir}")
        print(f"🎬 Beat sync script: {beat_sync_script}")
        print(f"📊 Expected output: {total_compilations} compilation videos")
        print(f"\n⚡ Next step:")
        print(f"   python beat_sync_selected_characters.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()