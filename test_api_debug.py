#!/usr/bin/env python
"""
Simple test script to debug the API server issue.
This sends a single image generation request to isolate the problem.
"""

import requests
import json
import time

# API server details
API_URL = "http://127.0.0.1:8006"
TIMEOUT = 60

def test_health_check():
    """Test if API server is responding"""
    print("🏥 Testing API server health check...")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

def test_status_endpoint():
    """Test the status endpoint"""
    print("📊 Testing /status endpoint...")
    try:
        response = requests.get(f"{API_URL}/status", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except Exception as e:
        print(f"   ❌ Status check failed: {e}")
        return False

def test_image_generation():
    """Test a simple image generation request"""
    print("🎨 Testing image generation...")
    
    # Simple test request
    test_request = {
        "prompt": "simple test image of a flower",
        "segment_id": 999,
        "face": None,
        "output_subfolder": "test_debug",
        "filename_prefix_text": "debug_test",
        "video_start_image_path": None
    }
    
    print(f"   Request data: {test_request}")
    
    try:
        print("   Sending POST request...")
        response = requests.post(
            f"{API_URL}/generate/image", 
            json=test_request, 
            timeout=TIMEOUT
        )
        print(f"   Response status: {response.status_code}")
        print(f"   Response data: {response.json() if response.status_code == 200 else response.text}")
        return True
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out after {TIMEOUT}s")
        return False
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 API SERVER DEBUG TEST")
    print("=" * 60)
    
    # Test 1: Health check
    if not test_health_check():
        print("❌ Health check failed - API server not running")
        return
    
    print()
    
    # Test 2: Status endpoint
    if not test_status_endpoint():
        print("❌ Status endpoint failed")
        return
    
    print()
    
    # Test 3: Image generation
    print("⏳ Testing image generation (this may take a while)...")
    success = test_image_generation()
    
    print()
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Image generation test failed")
    print("=" * 60)

if __name__ == "__main__":
    main()