#!/usr/bin/env python
"""
Debug script to test the exact API request that's hanging
"""
import requests
import json
import time
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_request():
    """Test the exact same request as the music pipeline"""
    api_url = "http://127.0.0.1:8005"
    
    # Test data that matches the music pipeline request
    request_data = {
        "prompt": "A majestic Lord Shiva in deep meditation, surrounded by cosmic energy, blue skin glowing with divine light, third eye radiating wisdom, sitting in lotus position on Mount Kailash with the Ganges flowing from his hair, photorealistic, 16:9 aspect ratio, cinematic lighting, ultra-detailed",
        "segment_id": 1,
        "face": None,
        "output_subfolder": "Run_20250619_193911_music_images/all_images",
        "filename_prefix_text": "music_segment",
        "video_start_image_path": None
    }
    
    print("🧪 Starting API Request Debug Test")
    print("="*60)
    
    # Step 1: Health check
    print("\n1. Testing health check...")
    try:
        health_response = requests.get(f"{api_url}/", timeout=10)
        print(f"   Status: {health_response.status_code}")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   Data: {json.dumps(health_data, indent=2)}")
        else:
            print(f"   Error: {health_response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
        return False
    
    # Step 2: Status check
    print("\n2. Testing status endpoint...")
    try:
        status_response = requests.get(f"{api_url}/status", timeout=10)
        print(f"   Status: {status_response.status_code}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"   Config: {json.dumps(status_data.get('config', {}), indent=2)}")
        else:
            print(f"   Error: {status_response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    # Step 3: The actual image generation request
    print("\n3. Testing image generation request...")
    print(f"   URL: {api_url}/generate/image")
    print(f"   Request data: {json.dumps(request_data, indent=2)}")
    
    try:
        print("   Sending request...")
        start_time = time.time()
        
        response = requests.post(
            f"{api_url}/generate/image",
            json=request_data,
            timeout=60  # Longer timeout for debugging
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   ✅ Response received after {duration:.2f} seconds")
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Parsed JSON: {json.dumps(result, indent=2)}")
        
        return True
        
    except requests.Timeout:
        print(f"   ❌ Request timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False

def test_comfyui_direct():
    """Test ComfyUI directly to ensure it's accessible"""
    print("\n4. Testing ComfyUI direct access...")
    
    try:
        # Test ComfyUI root
        response = requests.get("http://127.0.0.1:8188/", timeout=10)
        print(f"   ComfyUI root status: {response.status_code}")
        
        # Test ComfyUI queue
        queue_response = requests.get("http://127.0.0.1:8188/queue", timeout=10)
        print(f"   ComfyUI queue status: {queue_response.status_code}")
        if queue_response.status_code == 200:
            queue_data = queue_response.json()
            print(f"   Queue info: Running={len(queue_data.get('queue_running', []))}, Pending={len(queue_data.get('queue_pending', []))}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ ComfyUI test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 API Debug Test Starting...")
    
    # Test ComfyUI first
    comfyui_ok = test_comfyui_direct()
    
    # Test API server
    api_ok = test_api_request()
    
    print("\n" + "="*60)
    print("🏁 Debug Test Summary:")
    print(f"   ComfyUI accessibility: {'✅ OK' if comfyui_ok else '❌ FAILED'}")
    print(f"   API server test: {'✅ OK' if api_ok else '❌ FAILED'}")
    
    if not api_ok:
        print("\n💡 Troubleshooting suggestions:")
        print("   1. Check if the API server is actually running on port 8005")
        print("   2. Look for error messages in the API server logs")
        print("   3. Verify ComfyUI is accessible and responding")
        print("   4. Check for firewall or network issues")