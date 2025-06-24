#!/usr/bin/env python
"""
Test script to debug the Music API Server
"""
import requests
import json
import time

def test_api_server():
    """Test the music API server endpoints"""
    base_url = "http://127.0.0.1:8005"
    
    print("🧪 Testing Music API Server...")
    
    # Test 1: Health check
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
        return False
    
    # Test 2: Status endpoint
    print("\n2. Testing status endpoint...")
    try:
        response = requests.get(f"{base_url}/status", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    # Test 3: Simple image generation request
    print("\n3. Testing image generation endpoint...")
    test_request = {
        "prompt": "A beautiful sunset over mountains, photorealistic, 16:9 aspect ratio",
        "segment_id": 999,
        "face": None,
        "output_subfolder": "test_output/all_images",
        "filename_prefix_text": "test_image",
        "video_start_image_path": None
    }
    
    try:
        print(f"   Sending request: {json.dumps(test_request, indent=2)}")
        response = requests.post(f"{base_url}/generate/image", json=test_request, timeout=30)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    return True

def test_comfyui():
    """Test ComfyUI accessibility"""
    print("\n🧪 Testing ComfyUI connectivity...")
    
    try:
        response = requests.get("http://127.0.0.1:8188/", timeout=10)
        print(f"   ComfyUI Status: {response.status_code}")
        if response.status_code == 200:
            print("   ComfyUI is accessible ✅")
        else:
            print(f"   ComfyUI error: {response.text}")
    except Exception as e:
        print(f"   ComfyUI failed: {e}")
        return False
    
    # Test ComfyUI API endpoint
    try:
        response = requests.get("http://127.0.0.1:8188/queue", timeout=10)
        print(f"   ComfyUI Queue Status: {response.status_code}")
        if response.status_code == 200:
            queue_data = response.json()
            print(f"   Queue info: Running={len(queue_data.get('queue_running', []))}, Pending={len(queue_data.get('queue_pending', []))}")
        else:
            print(f"   Queue error: {response.text}")
    except Exception as e:
        print(f"   Queue check failed: {e}")
    
    return True

if __name__ == "__main__":
    print("🚀 API Server Debug Test")
    print("=" * 50)
    
    # Test ComfyUI first
    test_comfyui()
    
    # Test API server
    test_api_server()
    
    print("\n" + "=" * 50)
    print("✅ Debug test completed")