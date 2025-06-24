#!/usr/bin/env python3
"""
Full Video Pipeline Debug - Test complete workflow
"""

import json
import requests
import shutil
import time
import subprocess
import signal
import os
from pathlib import Path
from datetime import datetime

# Configuration
API_URL = "http://127.0.0.1:8006"
COMFYUI_INPUT_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
TEMP_DIR = COMFYUI_INPUT_BASE / "temp_video_starts"
APPROVED_IMAGE = "H:/dancers_content/250621/250621163629_00019_.png"
TEST_PROMPT = "newfantasycore, athletic divine being with glowing amber eyes, ripped physique, mystical energy surrounding the figure, majestic and attractive, Photorealistic image of Lord Shiva in serene meditation"

def start_api_server():
    """Start the API server"""
    print("🚀 Starting API server...")
    try:
        # Start API server in background
        process = subprocess.Popen(
            ["python3", "api_server_v5_music.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if it's running
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ API server started successfully")
            return process
        else:
            print(f"❌ API server health check failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None

def setup_test_image():
    """Copy test image to temp directory"""
    print("📁 Setting up test image...")
    
    # Create temp directory
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy approved image to temp directory
    source_path = Path(APPROVED_IMAGE)
    if not source_path.exists():
        print(f"❌ Source image not found: {source_path}")
        return None
    
    timestamp = datetime.now().strftime('%H%M%S%f')
    temp_filename = f"debug_test_{timestamp}.png"
    dest_path = TEMP_DIR / temp_filename
    
    shutil.copy2(source_path, dest_path)
    print(f"✅ Copied image: {source_path.name} → {temp_filename}")
    
    # Return the relative path for ComfyUI
    relative_path = f"temp_video_starts/{temp_filename}"
    return relative_path, dest_path

def test_video_generation_with_debug(image_path):
    """Test video generation with detailed logging"""
    print("🎬 Testing video generation...")
    
    payload = {
        "prompt": TEST_PROMPT,
        "segment_id": 999,
        "face": None,
        "output_subfolder": "debug_video_test",
        "filename_prefix_text": "debug_test",
        "video_start_image_path": image_path
    }
    
    print(f"📦 Request payload:")
    for key, value in payload.items():
        if key == "prompt":
            print(f"   - {key}: {value[:50]}...")
        else:
            print(f"   - {key}: {value}")
    
    try:
        print("📤 Sending video generation request...")
        response = requests.post(f"{API_URL}/generate_video", json=payload, timeout=60)
        
        print(f"📤 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get('prompt_id')
            print(f"✅ Video generation submitted!")
            print(f"🆔 Prompt ID: {prompt_id}")
            return prompt_id
        else:
            print(f"❌ Video generation failed: {response.status_code}")
            print(f"❌ Error details: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Video generation request failed: {e}")
        return None

def check_image_file_exists(image_path, dest_path):
    """Verify the image file exists"""
    print(f"📋 Checking image file existence...")
    print(f"   - Relative path: {image_path}")
    print(f"   - Full path: {dest_path}")
    print(f"   - File exists: {dest_path.exists()}")
    if dest_path.exists():
        file_size = dest_path.stat().st_size
        print(f"   - File size: {file_size} bytes")
        if file_size > 0:
            print("✅ Image file is valid")
            return True
        else:
            print("❌ Image file is empty")
            return False
    else:
        print("❌ Image file not found")
        return False

def main():
    """Main debug function"""
    print("🧪 FULL VIDEO PIPELINE DEBUG")
    print("=" * 60)
    
    api_process = None
    image_path = None
    dest_path = None
    
    try:
        # Step 1: Start API server
        api_process = start_api_server()
        if not api_process:
            print("❌ Cannot proceed - API server failed to start")
            return
        
        # Step 2: Setup test image
        result = setup_test_image()
        if not result:
            print("❌ Cannot proceed - image setup failed")
            return
        
        image_path, dest_path = result
        
        # Step 3: Verify image file
        if not check_image_file_exists(image_path, dest_path):
            print("❌ Cannot proceed - image file invalid")
            return
        
        # Step 4: Test video generation
        prompt_id = test_video_generation_with_debug(image_path)
        
        if prompt_id:
            print("\n✅ Video generation request successful!")
            print("🔍 Check ComfyUI queue: http://127.0.0.1:8188/")
            print("📁 Check ComfyUI output for results")
        else:
            print("\n❌ Video generation request failed!")
        
        print("\n=== DEBUG COMPLETE ===")
        
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted")
    
    finally:
        # Cleanup
        if api_process:
            print("🛑 Stopping API server...")
            api_process.terminate()
            api_process.wait(timeout=5)
        
        if dest_path and dest_path.exists():
            try:
                dest_path.unlink()
                print(f"🧹 Cleaned up test file: {dest_path.name}")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    main()