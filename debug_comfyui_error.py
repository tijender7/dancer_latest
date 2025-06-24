#!/usr/bin/env python3
"""
Debug ComfyUI 400 error by getting detailed response
"""

import requests
import json

def get_comfyui_error_details():
    """Send a video workflow to ComfyUI and capture detailed error"""
    
    # Load the video workflow
    try:
        with open("base_workflows/api_wanvideo_without_faceswap.json", "r") as f:
            workflow = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
        return
    
    # Modify the workflow with minimal required fields
    workflow["341"]["inputs"]["image"] = "temp_video_starts/test.png"
    workflow["161"]["inputs"]["text"] = "test prompt"
    workflow["403"]["inputs"]["custom_directory"] = "debug_test"
    workflow["403"]["inputs"]["custom_text"] = "debug_test"
    
    # Create the payload exactly like the API server does
    client_id = "debug-test-123"
    payload = {
        "prompt": workflow,
        "client_id": client_id
    }
    
    print("🔍 Sending workflow to ComfyUI for debugging...")
    print(f"📦 Payload size: {len(json.dumps(payload))} characters")
    
    try:
        response = requests.post("http://127.0.0.1:8188/prompt", json=payload, timeout=30)
        
        print(f"📤 Status Code: {response.status_code}")
        print(f"📤 Response Headers: {dict(response.headers)}")
        print(f"📤 Response Text: {response.text}")
        
        if response.status_code == 400:
            print("\n🔍 This is the 400 error we're getting!")
            try:
                error_data = response.json()
                print(f"📤 Parsed Error: {json.dumps(error_data, indent=2)}")
            except:
                print("📤 Could not parse response as JSON")
        
    except Exception as e:
        print(f"❌ Request failed: {e}")

def check_comfyui_object_info():
    """Check what nodes are available in ComfyUI"""
    print("\n🔍 Checking ComfyUI available nodes...")
    try:
        response = requests.get("http://127.0.0.1:8188/object_info", timeout=10)
        if response.status_code == 200:
            object_info = response.json()
            
            # Check for video-related nodes
            video_nodes = [key for key in object_info.keys() if 'video' in key.lower() or 'wan' in key.lower()]
            print(f"📋 Found {len(video_nodes)} video-related nodes:")
            for node in video_nodes[:10]:  # Show first 10
                print(f"   - {node}")
            
            if len(video_nodes) > 10:
                print(f"   ... and {len(video_nodes) - 10} more")
                
            # Check specific nodes from our workflow
            required_nodes = ["LoadWanVideoT5TextEncoder", "WanVideoModelLoader", "WanVideoSampler"]
            print(f"\n🔍 Checking required nodes:")
            for node in required_nodes:
                if node in object_info:
                    print(f"   ✅ {node} - Available")
                else:
                    print(f"   ❌ {node} - Missing!")
                    
        else:
            print(f"❌ Failed to get object info: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Object info request failed: {e}")

if __name__ == "__main__":
    print("🧪 ComfyUI Error Debug Tool")
    print("=" * 50)
    
    check_comfyui_object_info()
    print("\n" + "=" * 50)
    get_comfyui_error_details()
    print("=" * 50)