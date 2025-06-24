#!/usr/bin/env python3
"""
Test Video Generation API and create detailed logs
"""

import requests
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
log_file = f"video_api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://127.0.0.1:8006"
COMFYUI_INPUT_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
TEMP_DIR = COMFYUI_INPUT_BASE / "temp_video_starts"
APPROVED_IMAGES = [
    "H:/dancers_content/250621/250621150249_00001_.png",
    "H:/dancers_content/250621/250621150249_00004_.png", 
    "H:/dancers_content/250621/250621150249_00005_.png",
    "H:/dancers_content/250621/250621150249_00007_.png",
    "H:/dancers_content/250621/250621150249_00008_.png"
]

def test_api_connection():
    """Test basic API connection"""
    logger.info("🧪 Testing API connection...")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        logger.info(f"✅ API Status: {response.status_code}")
        logger.info(f"Response: {response.text}")
        return True
    except Exception as e:
        logger.error(f"❌ API connection failed: {e}")
        return False

def setup_temp_directory():
    """Create temp directory for video start images"""
    logger.info("📁 Setting up temp directory...")
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Temp directory ready: {TEMP_DIR}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create temp directory: {e}")
        return False

def copy_test_image():
    """Copy one approved image to temp directory"""
    logger.info("📸 Copying test image...")
    try:
        source_path = Path(APPROVED_IMAGES[0])
        dest_path = TEMP_DIR / "test_video_start.png"
        
        if source_path.exists():
            import shutil
            shutil.copy2(source_path, dest_path)
            logger.info(f"✅ Copied: {source_path.name} → {dest_path}")
            return str(dest_path.relative_to(COMFYUI_INPUT_BASE)).replace("\\", "/")
        else:
            logger.error(f"❌ Source image not found: {source_path}")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to copy image: {e}")
        return None

def test_video_generation(image_path):
    """Test video generation with real image"""
    logger.info("🎬 Testing video generation...")
    
    payload = {
        "prompt": "newfantasycore, athletic divine being with glowing amber eyes, ripped physique, mystical energy surrounding the figure, majestic and attractive, Photorealistic image of Lord Shiva in serene meditation",
        "segment_id": 1,
        "face": None,
        "output_subfolder": "api_test_videos",
        "filename_prefix_text": "api_test",
        "video_start_image_path": image_path
    }
    
    logger.info(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/generate_video", json=payload, timeout=60)
        logger.info(f"📤 Response Status: {response.status_code}")
        logger.info(f"📤 Response Headers: {dict(response.headers)}")
        logger.info(f"📤 Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get('prompt_id')
            logger.info(f"✅ Video generation submitted successfully!")
            logger.info(f"🆔 Prompt ID: {prompt_id}")
            return prompt_id
        else:
            logger.error(f"❌ Video generation failed: {response.status_code}")
            logger.error(f"Error details: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Video generation request failed: {e}")
        return None

def check_comfyui_queue(prompt_id):
    """Check ComfyUI queue status"""
    if not prompt_id:
        return
        
    logger.info("🔍 Checking ComfyUI queue status...")
    try:
        response = requests.get("http://127.0.0.1:8188/queue", timeout=10)
        if response.status_code == 200:
            queue_data = response.json()
            logger.info(f"📊 Queue Status: {json.dumps(queue_data, indent=2)}")
            
            # Check if our prompt is in the queue
            running = queue_data.get('queue_running', [])
            pending = queue_data.get('queue_pending', [])
            
            found_in_running = any(item[1] == prompt_id for item in running)
            found_in_pending = any(item[1] == prompt_id for item in pending)
            
            if found_in_running:
                logger.info(f"✅ Prompt {prompt_id} is currently running")
            elif found_in_pending:
                logger.info(f"⏳ Prompt {prompt_id} is pending in queue")
            else:
                logger.info(f"❓ Prompt {prompt_id} not found in queue (may have completed or failed)")
        else:
            logger.error(f"❌ Failed to check queue: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Queue check failed: {e}")

def main():
    """Main test function"""
    logger.info("🎬 Starting Video API Test")
    logger.info("=" * 60)
    
    # Test 1: API Connection
    if not test_api_connection():
        logger.error("❌ Cannot proceed - API server not responding")
        return
    
    # Test 2: Setup temp directory
    if not setup_temp_directory():
        logger.error("❌ Cannot proceed - temp directory setup failed")
        return
    
    # Test 3: Copy test image
    image_path = copy_test_image()
    if not image_path:
        logger.error("❌ Cannot proceed - image copy failed")
        return
    
    # Test 4: Generate video
    prompt_id = test_video_generation(image_path)
    
    # Test 5: Check queue status
    check_comfyui_queue(prompt_id)
    
    logger.info("=" * 60)
    logger.info(f"🎉 Test completed! Check log file: {log_file}")
    logger.info("📁 If video generation was successful, check ComfyUI output folder for results")
    
    # Cleanup
    try:
        cleanup_path = TEMP_DIR / "test_video_start.png"
        if cleanup_path.exists():
            cleanup_path.unlink()
            logger.info("🧹 Cleaned up test image")
    except Exception as e:
        logger.warning(f"⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    main()