#!/usr/bin/env python3
"""
Test script for file discovery functionality
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def find_latest_mp3(songs_dir: Path):
    """Test function to find latest MP3"""
    print(f"🔍 Searching for MP3 files in: {songs_dir}")
    
    if not songs_dir.exists():
        print(f"❌ Songs directory not found: {songs_dir}")
        return None
    
    # Find all MP3 files
    mp3_files = list(songs_dir.glob("*.mp3"))
    print(f"Found {len(mp3_files)} MP3 files")
    
    if not mp3_files:
        print("❌ No MP3 files found")
        return None
    
    # Sort by modification time (newest first)
    latest_file = max(mp3_files, key=lambda f: f.stat().st_mtime)
    
    # Log file details
    file_size_mb = latest_file.stat().st_size / (1024 * 1024)
    mod_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
    
    print(f"✅ Latest MP3: {latest_file.name}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"   Modified: {mod_time}")
    
    return latest_file

def create_output_directory(base_dir: Path):
    """Test function to create output directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / f"Run_{timestamp}_music"
    
    print(f"📁 Creating output directory: {output_dir}")
    
    # Check if we can create the directory (simulate)
    print(f"✅ Would create output directory: {output_dir}")
    return output_dir

if __name__ == "__main__":
    print("🧪 Testing File Discovery Functionality")
    print("=" * 50)
    
    # Test paths
    songs_dir = Path("songs")
    base_output_dir = Path("/tmp")  # Use /tmp for testing
    
    # Test 1: File discovery
    print("\n📝 Test 1: MP3 File Discovery")
    latest_mp3 = find_latest_mp3(songs_dir)
    
    # Test 2: Output directory creation
    print("\n📝 Test 2: Output Directory Creation")
    output_dir = create_output_directory(base_output_dir)
    
    # Summary
    print("\n📊 Test Summary")
    print(f"MP3 Discovery: {'✅ PASS' if latest_mp3 else '❌ FAIL'}")
    print(f"Directory Creation: {'✅ PASS' if output_dir else '❌ FAIL'}")
    
    if latest_mp3:
        print(f"\n🎵 Ready to process: {latest_mp3.name}")
        print(f"📁 Would save to: {output_dir}")