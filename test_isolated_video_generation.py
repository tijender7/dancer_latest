#!/usr/bin/env python3
"""
Isolated Video Generation Test - Test video generation with approved image
"""

import requests
import json
import shutil
import time
from pathlib import Path
from datetime import datetime

# Configuration
API_URL = "http://127.0.0.1:8006"
COMFYUI_INPUT_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
TEMP_DIR = COMFYUI_INPUT_BASE / "temp_video_starts"

# Use one of the approved images from the latest run
APPROVED_IMAGE = "H:/dancers_content/250621/250621163629_00019_.png"
TEST_PROMPT = "newfantasycore, athletic divine being with glowing amber eyes, ripped physique, mystical energy surrounding the figure, majestic and attractive, Photorealistic image of Lord Shiva in serene meditation with blue skin, crescent moon, and Ganges in hair, Mount Kailash background, serene mood, 16:9 aspect ratio, cinematic lighting, engaging composition perfect for YouTube thumbnail"

def setup_test_environment():
    """Setup test environment and copy approved image"""
    print("🔧 Setting up test environment...")
    
    # Create temp directory
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created temp directory: {TEMP_DIR}")
    
    # Copy approved image to temp directory
    source_path = Path(APPROVED_IMAGE)
    if not source_path.exists():
        print(f"❌ Source image not found: {source_path}")
        return None
    
    timestamp = datetime.now().strftime('%H%M%S%f')
    temp_filename = f"test_isolated_{timestamp}.png"
    dest_path = TEMP_DIR / temp_filename
    
    shutil.copy2(source_path, dest_path)
    print(f"✅ Copied image: {source_path.name} → {temp_filename}")
    
    # Return the relative path for ComfyUI
    relative_path = f"temp_video_starts/{temp_filename}"
    return relative_path

def test_api_health():
    """Test API server health"""
    print("🏥 Testing API server health...")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"✅ API Health: {response.status_code}")
        data = response.json()
        print(f"📝 API Response: {data['message']}")
        return True
    except Exception as e:
        print(f"❌ API Health failed: {e}")
        return False

def generate_test_video(image_path):
    """Generate a test video using the approved image"""
    print("🎬 Generating test video...")
    
    payload = {
        "prompt": TEST_PROMPT,
        "segment_id": 999,  # Use a unique segment ID for testing
        "face": None,
        "output_subfolder": "isolated_test_videos",
        "filename_prefix_text": "isolated_test",
        "video_start_image_path": image_path
    }
    
    print(f"📦 Request Payload:")
    print(f"   - Prompt: {TEST_PROMPT[:80]}...")
    print(f"   - Segment ID: {payload['segment_id']}")
    print(f"   - Image Path: {image_path}")
    print(f"   - Output: {payload['output_subfolder']}")
    
    try:
        print("📤 Sending video generation request...")
        response = requests.post(f"{API_URL}/generate_video", json=payload, timeout=60)
        
        print(f"📤 Response Status: {response.status_code}")
        print(f"📤 Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get('prompt_id')
            print(f"✅ Video generation submitted successfully!")
            print(f"🆔 Prompt ID: {prompt_id}")
            return prompt_id
        else:
            print(f"❌ Video generation failed: {response.status_code}")
            print(f"Error details: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Video generation request failed: {e}")
        return None

def check_comfyui_status(prompt_id):
    """Check ComfyUI queue and history for our prompt"""
    print(f"🔍 Checking ComfyUI status for prompt: {prompt_id}")
    
    try:
        # Check queue
        print("📋 Checking ComfyUI queue...")
        queue_response = requests.get("http://127.0.0.1:8188/queue", timeout=10)
        if queue_response.status_code == 200:
            queue_data = queue_response.json()
            
            running = queue_data.get('queue_running', [])
            pending = queue_data.get('queue_pending', [])
            
            print(f"🔄 Running jobs: {len(running)}")
            print(f"⏳ Pending jobs: {len(pending)}")
            
            # Check if our prompt is in the queue
            found_running = any(item[1] == prompt_id for item in running if len(item) > 1)
            found_pending = any(item[1] == prompt_id for item in pending if len(item) > 1)
            
            if found_running:
                print(f"✅ Our prompt {prompt_id} is currently RUNNING")
            elif found_pending:
                print(f"⏳ Our prompt {prompt_id} is PENDING in queue")
            else:
                print(f"❓ Our prompt {prompt_id} not found in queue (may have completed or failed)")
        
        # Check history
        print("📚 Checking ComfyUI history...")
        history_response = requests.get("http://127.0.0.1:8188/history", timeout=10)
        if history_response.status_code == 200:
            history_data = history_response.json()
            
            if prompt_id in history_data:
                print(f"✅ Found prompt {prompt_id} in history!")
                prompt_history = history_data[prompt_id]
                status = prompt_history.get('status', {})
                print(f"📊 Status: {status}")
                
                # Check for outputs
                outputs = prompt_history.get('outputs', {})
                if outputs:
                    print(f"📁 Outputs found: {len(outputs)} nodes")
                    for node_id, node_outputs in outputs.items():
                        if 'gifs' in node_outputs:
                            gifs = node_outputs['gifs']
                            print(f"🎬 Videos found in node {node_id}: {len(gifs)} files")
                            for gif in gifs:
                                print(f"   - {gif.get('filename', 'unknown')}")
                        if 'images' in node_outputs:
                            images = node_outputs['images']
                            print(f"🖼️ Images found in node {node_id}: {len(images)} files")
                else:
                    print("❌ No outputs found in history")
            else:
                print(f"❌ Prompt {prompt_id} not found in history")
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")

def monitor_video_generation(prompt_id, max_wait_minutes=15):
    """Monitor video generation progress"""
    if not prompt_id:
        return
    
    print(f"⏰ Monitoring video generation for {max_wait_minutes} minutes...")
    start_time = datetime.now()
    max_wait_seconds = max_wait_minutes * 60
    
    while (datetime.now() - start_time).total_seconds() < max_wait_seconds:
        check_comfyui_status(prompt_id)
        print(f"⏳ Waiting 30 seconds before next check...")
        print("-" * 50)
        time.sleep(30)
    
    print(f"⏰ Monitoring timeout reached ({max_wait_minutes} minutes)")
    print("🔍 Final status check:")
    check_comfyui_status(prompt_id)

def cleanup_test_files(image_path):
    """Clean up test files"""
    if image_path:
        try:
            test_file = TEMP_DIR / Path(image_path).name
            if test_file.exists():
                test_file.unlink()
                print(f"🧹 Cleaned up test file: {test_file}")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

def main():
    """Main test function"""
    print("🧪 ISOLATED VIDEO GENERATION TEST")
    print("=" * 60)
    print(f"Using approved image: {APPROVED_IMAGE}")
    print(f"Using prompt: {TEST_PROMPT[:100]}...")
    print("=" * 60)
    
    # Step 1: Test API
    if not test_api_health():
        print("❌ Cannot proceed - API server not available")
        return
    
    # Step 2: Setup environment
    image_path = setup_test_environment()
    if not image_path:
        print("❌ Cannot proceed - image setup failed")
        return
    
    try:
        # Step 3: Generate video
        prompt_id = generate_test_video(image_path)
        
        # Step 4: Monitor generation
        monitor_video_generation(prompt_id)
        
        print("=" * 60)
        print("🎉 Test completed!")
        print("📁 Check the following locations for results:")
        print(f"   - ComfyUI output folder: H:/dancers_content/isolated_test_videos/")
        print(f"   - ComfyUI queue: http://127.0.0.1:8188/ (web interface)")
        print("=" * 60)
        
    finally:
        # Always try to cleanup
        cleanup_test_files(image_path)

if __name__ == "__main__":
    main()