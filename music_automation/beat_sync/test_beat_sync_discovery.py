#!/usr/bin/env python3
"""
Test script to verify folder and file discovery logic
without requiring heavy dependencies like librosa and moviepy
"""

import os
import glob
from pathlib import Path
from datetime import datetime

# --- Configuration ---
DANCERS_CONTENT_BASE = Path("H:/dancers_content")
SONGS_DIR = Path("D:/Comfy_UI_V20/ComfyUI/output/dancer/songs")
OUTPUT_FOLDER_NAME = "music_video_compiled"

def find_latest_music_run_folder():
    """Find the most recent Run_*_music_images folder"""
    print("🔍 Searching for latest music run folder...")
    
    if not DANCERS_CONTENT_BASE.exists():
        raise FileNotFoundError(f"Dancers content directory not found: {DANCERS_CONTENT_BASE}")
    
    pattern = str(DANCERS_CONTENT_BASE / "Run_*_music_images")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        raise FileNotFoundError("No Run_*_music_images folders found")
    
    # Sort by modification time, newest first
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    latest_folder = Path(music_folders[0])
    
    print(f"✅ Found latest music run: {latest_folder.name}")
    print(f"   Full path: {latest_folder}")
    print(f"   Modified: {datetime.fromtimestamp(latest_folder.stat().st_mtime)}")
    
    return latest_folder

def find_video_clips_in_music_folder(music_folder):
    """Find video clips in the date subfolder within all_videos"""
    print(f"📁 Searching for video clips in: {music_folder.name}")
    
    all_videos_dir = music_folder / "all_videos"
    if not all_videos_dir.exists():
        raise FileNotFoundError(f"all_videos directory not found in {music_folder}")
    
    # Find date subfolders (should be 6-digit date like 250622)
    date_folders = [
        d for d in all_videos_dir.iterdir() 
        if d.is_dir() and d.name.isdigit() and len(d.name) == 6
    ]
    
    if not date_folders:
        raise FileNotFoundError(f"No date subfolder found in {all_videos_dir}")
    
    # Use the most recent date folder
    date_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    video_clips_folder = date_folders[0]
    
    print(f"📂 Using date folder: {video_clips_folder.name}")
    
    # Get all video files
    video_extensions = ["*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"]
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(video_clips_folder.glob(ext))
    
    if not video_files:
        raise FileNotFoundError(f"No video files found in {video_clips_folder}")
    
    video_files.sort()
    print(f"✅ Found {len(video_files)} video clips")
    
    # Show first few files as examples
    print("📋 Example video files:")
    for i, video_file in enumerate(video_files[:5]):
        file_size = video_file.stat().st_size / (1024*1024)  # MB
        print(f"   {i+1}. {video_file.name} ({file_size:.1f} MB)")
    
    if len(video_files) > 5:
        print(f"   ... and {len(video_files) - 5} more files")
    
    return video_files

def find_latest_song():
    """Find the most recent song file in the songs directory"""
    print("🎵 Searching for latest song...")
    
    if not SONGS_DIR.exists():
        raise FileNotFoundError(f"Songs directory not found: {SONGS_DIR}")
    
    # Look for audio files
    audio_extensions = ["*.mp3", "*.wav", "*.m4a", "*.flac"]
    audio_files = []
    
    for ext in audio_extensions:
        audio_files.extend(SONGS_DIR.glob(ext))
    
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {SONGS_DIR}")
    
    # Sort by modification time, newest first
    audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_song = audio_files[0]
    
    file_size = latest_song.stat().st_size / (1024*1024)  # MB
    print(f"✅ Found latest song: {latest_song.name} ({file_size:.1f} MB)")
    print(f"   Modified: {datetime.fromtimestamp(latest_song.stat().st_mtime)}")
    
    return latest_song

def create_output_directory(music_folder):
    """Create the output directory for compiled video"""
    output_dir = music_folder / "all_videos" / OUTPUT_FOLDER_NAME
    
    if output_dir.exists():
        print(f"📁 Output directory already exists: {output_dir}")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created output directory: {output_dir}")
    
    return output_dir

def test_discovery():
    """Test the discovery logic"""
    print("="*80)
    print(" 🧪 TESTING BEAT SYNC DISCOVERY LOGIC 🧪 ".center(80, "="))
    print("="*80)
    print()
    
    try:
        # Step 1: Find latest music run folder
        music_folder = find_latest_music_run_folder()
        print()
        
        # Step 2: Find video clips in the date subfolder
        video_files = find_video_clips_in_music_folder(music_folder)
        print()
        
        # Step 3: Find latest song
        song_path = find_latest_song()
        print()
        
        # Step 4: Create output directory (test)
        output_dir = create_output_directory(music_folder)
        print()
        
        # Summary
        print("="*80)
        print(" 🎉 DISCOVERY TEST SUCCESSFUL! 🎉 ".center(80, "="))
        print("="*80)
        print(f"✅ Music Folder: {music_folder.name}")
        print(f"✅ Video Files: {len(video_files)} clips found")
        print(f"✅ Song File: {song_path.name}")
        print(f"✅ Output Directory: {output_dir}")
        print()
        print("📋 Ready for beat sync compilation!")
        print("   Run: python music_video_beat_sync_compiler.py")
        print("   (Make sure dependencies are installed first)")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_discovery()
    if not success:
        print("\n💥 Discovery test failed!")
    
    print("\nPress Enter to exit...")
    input()