#!/usr/bin/env python3
"""
Quick test script to generate videos from the approved images
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_URL = "http://127.0.0.1:8006"
APPROVED_IMAGES = [
    "H:/dancers_content/250621/250621150249_00001_.png",
    "H:/dancers_content/250621/250621150249_00004_.png", 
    "H:/dancers_content/250621/250621150249_00005_.png",
    "H:/dancers_content/250621/250621150249_00007_.png",
    "H:/dancers_content/250621/250621150249_00008_.png"
]

def test_api_connection():
    """Test basic API connection"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        print(f"✅ API connection test: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def test_video_endpoint():
    """Test the video generation endpoint"""
    test_payload = {
        "prompt": "test video generation",
        "segment_id": 1,
        "face": None,
        "output_subfolder": "test_videos",
        "filename_prefix_text": "test",
        "video_start_image_path": "temp_video_starts/test.png"
    }
    
    try:
        response = requests.post(f"{API_URL}/generate_video", json=test_payload, timeout=10)
        print(f"✅ Video endpoint test: {response.status_code}")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Video endpoint failed: {e}")
        return False

def generate_videos_for_approved_images():
    """Generate videos for the approved images"""
    for i, img_path in enumerate(APPROVED_IMAGES, 1):
        img_name = Path(img_path).name
        print(f"\n🎬 Generating video {i}/{len(APPROVED_IMAGES)}: {img_name}")
        
        # Copy image to temp directory first
        temp_filename = f"start_test_{i:03d}_{int(time.time())}.png"
        
        payload = {
            "prompt": f"newfantasycore, divine being with mystical energy, video from {img_name}",
            "segment_id": i,
            "face": None,
            "output_subfolder": "test_videos_manual",
            "filename_prefix_text": f"manual_test_{i:03d}",
            "video_start_image_path": f"temp_video_starts/{temp_filename}"
        }
        
        try:
            response = requests.post(f"{API_URL}/generate_video", json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Video {i} submitted: {result.get('prompt_id', 'No ID')}")
            else:
                print(f"❌ Video {i} failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Video {i} error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    print("🧪 Testing Video Generation API")
    print("=" * 50)
    
    if test_api_connection():
        if test_video_endpoint():
            print("\n✅ API is working! Generating videos for approved images...")
            generate_videos_for_approved_images()
        else:
            print("\n❌ Video endpoint not working")
    else:
        print("\n❌ Cannot connect to API server")
        print("Make sure the API server is running: python api_server_v5_music.py")