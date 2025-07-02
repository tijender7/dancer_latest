#!/usr/bin/env python3
"""
reorganize_characters_correctly.py

Fix the character organization by grouping videos by TRUE character ID.
This fixes the current run where each variation got its own folder.
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

def extract_true_character_id(filename):
    """Extract TRUE character ID from filename (ignore variation number)"""
    # Example: video_1-2_timestamp.mp4 -> character ID = 1
    pattern = r'video_(\d+)-\d+'
    match = re.search(pattern, filename)
    if match:
        return match.group(1)  # Return only the first number (true character)
    return None

def analyze_current_organization():
    """Analyze the current (wrong) organization"""
    print("🔍 Analyzing Current Character Organization...")
    print("=" * 60)
    
    latest_run = find_latest_run_folder()
    print(f"📁 Latest run: {latest_run}")
    
    # Find phase3_videos directory
    phase3_dir = None
    for item in latest_run.iterdir():
        if item.is_dir() and "phase3_videos" in item.name:
            phase3_dir = item
            break
    
    if not phase3_dir:
        raise FileNotFoundError(f"No phase3_videos directory found in {latest_run}")
    
    # Find date subdirectory  
    date_dirs = [d for d in phase3_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        raise FileNotFoundError(f"No date subdirectory found in {phase3_dir}")
    
    date_dir = max(date_dirs, key=lambda p: p.stat().st_mtime)
    print(f"📁 Date directory: {date_dir}")
    
    # Analyze current wrong organization
    wrong_char_folders = [d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith("character_")]
    print(f"\n❌ Current Wrong Organization: {len(wrong_char_folders)} folders")
    
    video_distribution = {}
    for folder in wrong_char_folders:
        videos = list(folder.glob("*.mp4"))
        if videos:
            for video in videos:
                true_char_id = extract_true_character_id(video.name)
                if true_char_id not in video_distribution:
                    video_distribution[true_char_id] = []
                video_distribution[true_char_id].append(video)
    
    print(f"\n✅ TRUE Character Distribution:")
    for char_id in sorted(video_distribution.keys(), key=int):
        video_count = len(video_distribution[char_id])
        print(f"   Character {char_id}: {video_count} videos")
        for video in video_distribution[char_id]:
            print(f"      - {video.name}")
    
    return date_dir, video_distribution

def reorganize_correctly():
    """Reorganize videos by TRUE character ID"""
    print(f"\n🗂️ Reorganizing Videos by TRUE Character ID...")
    print("=" * 60)
    
    date_dir, video_distribution = analyze_current_organization()
    
    # Remove all existing wrong character folders
    print(f"\n🗑️ Removing wrong character folders...")
    wrong_folders = [d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith("character_")]
    for folder in wrong_folders:
        print(f"   Removing: {folder.name}")
        shutil.rmtree(folder)
    
    # Create correct character folders and move videos
    print(f"\n📁 Creating correct character folders...")
    for char_id in sorted(video_distribution.keys(), key=int):
        videos = video_distribution[char_id]
        
        # Create correct character folder
        correct_folder = date_dir / f"character_{char_id}"
        correct_folder.mkdir(exist_ok=True)
        print(f"\n✅ Created character_{char_id}/ with {len(videos)} videos:")
        
        # Move videos to correct folder
        for video_path in videos:
            new_path = correct_folder / video_path.name
            
            # Since videos are currently in wrong folders, we need to move them
            try:
                shutil.move(str(video_path), str(new_path))
                print(f"   ✅ {video_path.name}")
            except Exception as e:
                print(f"   ❌ Error moving {video_path.name}: {e}")
    
    # Verify the new organization
    print(f"\n📊 Verification - New Correct Organization:")
    correct_folders = [d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith("character_")]
    
    total_videos = 0
    for folder in sorted(correct_folders, key=lambda x: int(x.name.split('_')[1])):
        char_id = folder.name.replace("character_", "")
        videos = list(folder.glob("*.mp4"))
        video_count = len(videos)
        total_videos += video_count
        print(f"   📁 character_{char_id}: {video_count} videos")
    
    print(f"\n✅ Total videos organized: {total_videos}")
    return date_dir, len(correct_folders)

def calculate_beat_sync_output(num_characters):
    """Calculate expected beat sync output"""
    audio_dir = Path("/mnt/d/Comfy_UI_V20/ComfyUI/output/dancer/instagram_audio")
    audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.mp4"))
    
    total_compilations = num_characters * len(audio_files)
    
    print(f"\n📈 Beat Sync Calculation:")
    print(f"   Characters: {num_characters}")
    print(f"   Audio files: {len(audio_files)}")
    print(f"   Total compilations: {num_characters} × {len(audio_files)} = {total_compilations}")
    
    if total_compilations <= 100:
        print(f"   ✅ Manageable number of compilations!")
    else:
        print(f"   ⚠️ Large number of compilations - consider reducing")
    
    return total_compilations

def main():
    """Main function"""
    print("🚀 Character Reorganization - Fix Current Run")
    print("=" * 60)
    
    try:
        # First analyze what we have
        date_dir, video_distribution = analyze_current_organization()
        
        if not video_distribution:
            print("❌ No videos found to reorganize!")
            return
        
        # Ask for confirmation
        print(f"\n⚠️ This will reorganize {sum(len(v) for v in video_distribution.values())} videos")
        print(f"   From: {len([d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith('character_')])} wrong folders")
        print(f"   To: {len(video_distribution)} correct character folders")
        
        response = input(f"\nProceed with reorganization? (y/N): ")
        if response.lower() != 'y':
            print("❌ Reorganization cancelled")
            return
        
        # Perform reorganization
        reorganized_dir, num_characters = reorganize_correctly()
        
        # Calculate beat sync impact
        total_compilations = calculate_beat_sync_output(num_characters)
        
        print(f"\n🎉 Reorganization Complete!")
        print(f"📁 Location: {reorganized_dir}")
        print(f"🎬 Ready for beat sync: python beat_sync_character_separated.py")
        print(f"📊 Expected output: {total_compilations} diverse compilation videos")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()