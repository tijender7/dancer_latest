#!/usr/bin/env python3
"""
Simple Video Generation Test
"""

import requests
import json
from pathlib import Path

def test_video_generation():
    """Test video generation with a simple request"""
    print("🎬 Testing video generation...")
    
    # Test with a minimal payload first
    payload = {
        "prompt": "test video generation",
        "segment_id": 1,
        "face": None,
        "output_subfolder": "simple_test",
        "filename_prefix_text": "simple_test",
        "video_start_image_path": "temp_video_starts/test.png"  # File doesn't need to exist for this test
    }
    
    try:
        print(f"📦 Sending payload: {json.dumps(payload, indent=2)}")
        response = requests.post("http://127.0.0.1:8006/generate_video", json=payload, timeout=30)
        
        print(f"📤 Status Code: {response.status_code}")
        print(f"📤 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Video generation API is working!")
            return True
        else:
            print(f"❌ Video generation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Simple Video API Test")
    print("=" * 40)
    test_video_generation()
    print("=" * 40)
    print("Test completed!")