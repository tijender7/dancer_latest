#!/usr/bin/env python3
"""
Test script to verify image discovery is working
"""

import os
import glob
from datetime import datetime
from pathlib import Path

def find_latest_music_run_folder():
    """Find the most recent Run_*_music_images folder WITH approved images"""
    print("🔍 Searching for latest music run folder with approved images...")
    
    # Look in multiple possible locations
    script_dir = Path(__file__).resolve().parent
    search_paths = [
        script_dir / "output_runs_music",  # Local output_runs_music folder
        Path("H:/dancers_content"),  # H:/dancers_content
        script_dir.parent / "output" / "dancer" / "output_runs_music"  # Alternative path
    ]
    
    music_folders = []
    for search_path in search_paths:
        if search_path.exists():
            pattern = str(search_path / "Run_*_music_images")
            found_folders = glob.glob(pattern)
            music_folders.extend(found_folders)
            if found_folders:
                print(f"   🔍 Found {len(found_folders)} folders in: {search_path}")
        else:
            print(f"   ❌ Path doesn't exist: {search_path}")
    
    if not music_folders:
        print("❌ No Run_*_music_images folders found in any of these locations:")
        for path in search_paths:
            print(f"   - {path} (exists: {path.exists()})")
        return None
    
    # Sort by modification time, newest first
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    
    # Find the most recent folder that has approved images
    for folder_path in music_folders:
        folder = Path(folder_path)
        approved_dir = folder / "approved_images_for_video"
        
        if approved_dir.exists():
            # Check if it has any approved images
            image_extensions = ["*.png", "*.jpg", "*.jpeg"]
            has_images = False
            for ext in image_extensions:
                if list(approved_dir.glob(ext)):
                    has_images = True
                    break
            
            if has_images:
                print(f"✅ Found latest music run with approved images: {folder.name}")
                print(f"   Full path: {folder}")
                print(f"   Modified: {datetime.fromtimestamp(folder.stat().st_mtime)}")
                return folder
    
    # If no folder with approved images found, use the latest one anyway
    latest_folder = Path(music_folders[0])
    print(f"⚠️ No folders with approved images found, using latest: {latest_folder.name}")
    print(f"   Full path: {latest_folder}")
    print(f"   Modified: {datetime.fromtimestamp(latest_folder.stat().st_mtime)}")
    
    return latest_folder

def find_approved_images(music_folder):
    """Find approved images from the Telegram approval process"""
    print(f"\n🖼️ Searching for approved images in: {music_folder.name}")
    
    # Check for approved images folder
    approved_dir = music_folder / "approved_images_for_video"
    if not approved_dir.exists():
        print(f"❌ approved_images_for_video directory not found in {music_folder}")
        return []
    
    # Get all approved image files
    image_extensions = ["*.png", "*.jpg", "*.jpeg"]
    approved_images = []
    
    for ext in image_extensions:
        approved_images.extend(approved_dir.glob(ext))
    
    if not approved_images:
        print(f"❌ No approved images found in {approved_dir}")
        return []
    
    # Sort by filename for consistent ordering
    approved_images.sort()
    
    print(f"✅ Found {len(approved_images)} approved images")
    for i, img in enumerate(approved_images[:10], 1):  # Show first 10
        print(f"   {i}. {img.name}")
    if len(approved_images) > 10:
        print(f"   ... and {len(approved_images) - 10} more")
    
    return approved_images

def select_four_images(approved_images):
    """Select exactly 4 images for the 4-segment video"""
    print(f"\n🎯 Selecting 4 images from {len(approved_images)} approved images...")
    
    if len(approved_images) == 0:
        print("❌ No approved images available")
        return []
    elif len(approved_images) == 1:
        # Use the same image 4 times
        selected = [approved_images[0]] * 4
        print("   ⚠️ Only 1 image available - using it for all 4 segments")
    elif len(approved_images) == 2:
        # Use each image twice
        selected = [approved_images[0], approved_images[1], approved_images[0], approved_images[1]]
        print("   📋 2 images available - using each twice")
    elif len(approved_images) == 3:
        # Use first image twice, others once
        selected = [approved_images[0], approved_images[1], approved_images[2], approved_images[0]]
        print("   📋 3 images available - using first image twice")
    else:
        # Select 4 evenly spaced images from the collection
        # Simple spacing without numpy
        step = len(approved_images) // 4
        indices = [0, step, step*2, step*3]
        # Ensure we don't exceed the list bounds
        indices = [min(i, len(approved_images) - 1) for i in indices]
        selected = [approved_images[i] for i in indices]
        print(f"   📋 Selected 4 images from {len(approved_images)} available:")
    
    for i, img in enumerate(selected, 1):
        print(f"   Segment {i}: {img.name}")
    
    return selected

def main():
    print("="*60)
    print(" 🔍 IMAGE DISCOVERY TEST ".center(60, "="))
    print("="*60)
    
    # Test finding music run folder
    music_folder = find_latest_music_run_folder()
    if not music_folder:
        return
    
    # Test finding approved images
    approved_images = find_approved_images(music_folder)
    if not approved_images:
        return
    
    # Test image selection
    selected_images = select_four_images(approved_images)
    
    print("\n" + "="*60)
    print("✅ IMAGE DISCOVERY TEST COMPLETE!")
    print("="*60)
    print(f"📁 Latest run: {music_folder.name}")
    print(f"🖼️ Approved images: {len(approved_images)}")
    print(f"🎯 Selected for video: {len(selected_images)}")
    print("="*60)

if __name__ == "__main__":
    main()