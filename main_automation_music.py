#!/usr/bin/env python
"""
Music-Based Image & Video Generation Pipeline

This script automatically:
1. Finds the latest music analysis folder (Run_*_music)
2. Loads prompts from the generated prompts.json file
3. Generates images for each music segment using ComfyUI
4. Provides Telegram approval for generated images
5. Creates videos from approved images

Author: Claude Code Assistant
Date: 2025-06-19
"""

from __future__ import annotations

import os
import sys
import json
import requests
import shutil
import subprocess
import threading
import time
import logging
import glob
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

# --- Third-party Imports ---
from dotenv import load_dotenv

# --- Import Flask for Web UI Approval ---
try:
    from flask import Flask, request, render_template_string, send_from_directory, url_for
    print("DEBUG: Flask imported successfully.")
except ImportError:
    print("ERROR: Flask library not found. Please install it: pip install Flask")
    sys.exit(1)

# --- Import tqdm for progress bars ---
try:
    from tqdm import tqdm
    print("DEBUG: tqdm imported successfully.")
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

# --- Load environment variables (.env) ---
load_dotenv()

print("DEBUG: Music Pipeline execution started.")

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
REQUEST_TIMEOUT = 60
POLLING_INTERVAL = 10
POLLING_TIMEOUT_IMAGE = 600  # 10 minutes timeout for no activity
POLLING_TIMEOUT_VIDEO = 3600

APPROVAL_SERVER_PORT = 5006  # Different port for music pipeline
APPROVAL_FILENAME = "approved_images.json"
APPROVED_IMAGES_SUBFOLDER = "approved_images_for_video"

# --- Configurable Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content")
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"

# --- Telegram Approval Paths & Env Vars ---
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"
TELEGRAM_APPROVALS_JSON = TELEGRAM_APPROVALS_DIR / "telegram_approvals.json"
TOKEN_MAP_JSON = TELEGRAM_APPROVALS_DIR / "token_map.json"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env. Telegram approval will fail.")

print(f"DEBUG: Script directory: {SCRIPT_DIR}")
print(f"DEBUG: ComfyUI Input Base: {COMFYUI_INPUT_DIR_BASE}")
print(f"DEBUG: ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")

# --- Logging Setup ---
print("DEBUG: Setting up logging...")
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_music_pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
print("DEBUG: Logging setup complete.")
logger.info("🎵 Starting Music Pipeline Automation")

# --- Function: Load Config ---
def load_config(config_path="config_music.json"):
    """Load and validate music pipeline configuration"""
    print(f"DEBUG: Loading music config from '{config_path}'")
    config_path_obj = SCRIPT_DIR / config_path
    
    try:
        if not config_path_obj.is_file():
            logger.critical(f"CRITICAL: Config file not found: {config_path_obj}")
            sys.exit(1)
        
        with open(config_path_obj, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = [
            'api_server_url',
            'base_workflow_image',
            'base_workflow_video',
            'source_faces_path',
            'output_folder',
            'comfyui_api_url'
        ]
        
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required key '{key}' in config")
        
        # Resolve relative paths
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve()
        
        if not config['source_faces_path'].is_dir():
            logger.warning(f"Source faces dir not found: {config['source_faces_path']}")
        
        config['output_folder'].mkdir(parents=True, exist_ok=True)
        config['comfyui_api_url'] = config['comfyui_api_url'].rstrip('/')
        config['api_server_url'] = config['api_server_url'].rstrip('/')
        
        logger.info(f"Music config loaded successfully from {config_path_obj}")
        return config
        
    except Exception as e:
        logger.critical(f"CRITICAL error loading config '{config_path}': {e}", exc_info=True)
        sys.exit(1)

# --- Function: Find Latest Music Run ---
def find_latest_music_run():
    """Find the most recent Run_*_music folder"""
    logger.info("🔍 Searching for latest music run folder...")
    
    pattern = str(COMFYUI_OUTPUT_DIR_BASE / "Run_*_music")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        logger.error("❌ No music run folders found matching pattern: Run_*_music")
        return None
    
    # Sort by modification time, newest first
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    latest_folder = Path(music_folders[0])
    
    logger.info(f"✅ Found latest music run: {latest_folder.name}")
    logger.info(f"   Full path: {latest_folder}")
    logger.info(f"   Modified: {datetime.fromtimestamp(latest_folder.stat().st_mtime)}")
    
    return latest_folder

# --- Function: Load Music Prompts ---
def load_music_prompts(music_folder):
    """Load and parse prompts from the music analysis JSON file"""
    logger.info(f"📝 Loading music prompts from {music_folder.name}")
    
    prompts_file = music_folder / "prompts.json"
    if not prompts_file.exists():
        logger.error(f"❌ Prompts file not found: {prompts_file}")
        return None, None
    
    try:
        with open(prompts_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get("metadata", {})
        segments = data.get("segments", [])
        
        if not segments:
            logger.error("❌ No segments found in prompts.json")
            return None, None
        
        # Extract prompts dynamically
        prompts = []
        for segment in segments:
            segment_info = {
                "segment_id": segment.get("segment_id"),
                "start_time": segment.get("start_time"),
                "end_time": segment.get("end_time"),
                "primary_prompt": segment.get("primary_prompt"),
                "scene_type": segment.get("scene_type"),
                "energy_level": segment.get("energy_level"),
                "technical_specs": segment.get("technical_specs", {})
            }
            prompts.append(segment_info)
        
        logger.info(f"✅ Loaded {len(prompts)} music prompts successfully")
        logger.info(f"   Song: {metadata.get('song_file', 'Unknown')}")
        logger.info(f"   Duration: {metadata.get('total_duration', 'Unknown')}s")
        logger.info(f"   Generated: {metadata.get('generation_timestamp', 'Unknown')}")
        
        return prompts, metadata
        
    except Exception as e:
        logger.error(f"❌ Failed to load music prompts: {e}", exc_info=True)
        return None, None

# --- Function: Create Output Run Directory ---
def create_output_run_directory(config, music_folder):
    """Create a new output run directory based on the music folder"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    music_folder_name = music_folder.name.replace("Run_", "").replace("_music", "")
    run_name = f"Run_{timestamp}_music_images"
    
    output_run_dir = config['output_folder'] / run_name
    output_run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    all_images_dir = output_run_dir / "all_images"
    approved_images_dir = output_run_dir / APPROVED_IMAGES_SUBFOLDER
    all_images_dir.mkdir(exist_ok=True)
    approved_images_dir.mkdir(exist_ok=True)
    
    logger.info(f"📁 Created output directory: {output_run_dir}")
    return output_run_dir, all_images_dir

# --- Function: Check ComfyUI Queue Status ---
def check_comfyui_queue():
    """Check ComfyUI queue status for information only"""
    logger.info("Checking ComfyUI queue status...")
    
    try:
        response = requests.get("http://127.0.0.1:8188/queue", timeout=10)
        if response.status_code == 200:
            queue_data = response.json()
            running = len(queue_data.get('queue_running', []))
            pending = len(queue_data.get('queue_pending', []))
            
            logger.info(f"ComfyUI Queue - Running: {running}, Pending: {pending}")
            
            if running > 0 or pending > 0:
                logger.info("ComfyUI has active jobs. Our jobs will be queued automatically.")
            else:
                logger.info("ComfyUI queue is clear and ready")
                
            return True  # Always return True since we don't wait
        else:
            logger.error(f"Failed to check ComfyUI queue: {response.status_code}")
            return True  # Continue anyway
    except Exception as e:
        logger.error(f"Failed to check ComfyUI queue: {e}")
        return True  # Continue anyway


# --- Function: Start API Server ---
def start_api_server(config):
    """Start the music API server in background"""
    api_port = config['api_server_url'].split(':')[-1]
    logger.info(f"🚀 Starting Music API Server on port {api_port}...")
    
    api_script = SCRIPT_DIR / "api_server_v5_music.py"
    if not api_script.exists():
        logger.error(f"❌ API server script not found: {api_script}")
        return None
    
    try:
        # Create log files for API server output
        api_stdout_log = SCRIPT_DIR / "api_server_stdout.log"
        api_stderr_log = SCRIPT_DIR / "api_server_stderr.log"
        
        with open(api_stdout_log, 'w') as stdout_file, open(api_stderr_log, 'w') as stderr_file:
            process = subprocess.Popen(
                [sys.executable, str(api_script)],
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                cwd=str(SCRIPT_DIR)
            )
        
        logger.info(f"📝 API server stdout: {api_stdout_log}")
        logger.info(f"📝 API server stderr: {api_stderr_log}")
        
        # Wait a moment for server to start
        time.sleep(8)
        
        # Test if server is running (with longer wait time)
        max_retries = 6  # 30 seconds total
        for retry in range(max_retries):
            try:
                response = requests.get(f"{config['api_server_url']}/", timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Music API Server started successfully")
                    # Test the configuration endpoint too
                    try:
                        config_response = requests.get(f"{config['api_server_url']}/status", timeout=5)
                        if config_response.status_code == 200:
                            config_data = config_response.json()
                            logger.info(f"   API Server Config: {config_data.get('config', {}).get('comfyui_api_url', 'Unknown')}")
                    except:
                        pass  # Optional check
                    return process
                else:
                    logger.warning(f"⚠️ API Server returned status: {response.status_code}, retrying...")
            except requests.RequestException as e:
                logger.warning(f"⚠️ Retry {retry+1}/{max_retries}: {e}")
                if retry == max_retries - 1:
                    logger.error(f"❌ Failed to connect to API Server after {max_retries} retries")
                    # Check if process is still running
                    if process.poll() is None:
                        logger.error("   API Server process is still running but not responding")
                        logger.error("   This could indicate a configuration or startup issue")
                    else:
                        logger.error(f"   API Server process has exited with code: {process.returncode}")
                    process.terminate()
                    return None
            
            time.sleep(5)  # Wait 5 seconds between retries
            
    except Exception as e:
        logger.error(f"❌ Failed to start API Server: {e}")
        return None

# --- Function: Enhance Prompt for Fantasy Deity ---
def enhance_prompt_for_deity(original_prompt):
    """Enhance any prompt to focus on muscular fantasy deity with newfantasycore"""
    
    # Deity enhancement elements
    deity_features = [
        "extremely muscular deity", "ripped divine physique", "powerful muscular god", 
        "muscular divine warrior", "extremely buff deity", "athletic divine being"
    ]
    
    glowing_eyes = [
        "glowing golden eyes", "luminous blue eyes", "radiant silver eyes",
        "glowing amber eyes", "ethereal green eyes", "divine purple eyes"
    ]
    
    divine_elements = [
        "divine aura", "celestial energy", "ethereal light", "supernatural glow",
        "mystical energy surrounding the figure", "holy radiance", "godlike presence"
    ]
    
    muscular_descriptors = [
        "extremely well-defined muscles", "powerful muscular frame", "athletic build with visible muscle definition",
        "ripped physique", "imposing muscular stature", "perfectly sculpted body"
    ]
    
    import random
    
    # Select random elements
    deity = random.choice(deity_features)
    eyes = random.choice(glowing_eyes)
    divine = random.choice(divine_elements)
    muscles = random.choice(muscular_descriptors)
    
    # Create enhanced prompt while preserving original music-based context
    enhanced_prompt = f"newfantasycore, {deity} with {eyes}, {muscles}, {divine}, majestic and attractive, {original_prompt}"
    
    return enhanced_prompt

# --- Function: Generate Images from Music Prompts ---
def generate_images_from_music(config, prompts, output_run_dir, all_images_dir):
    """Generate images for each music segment prompt"""
    logger.info(f"🎨 Starting image generation for {len(prompts)} music segments")
    
    # Prepare for ComfyUI path generation
    output_subfolder_for_comfyui = f"{output_run_dir.name}/all_images"
    
    generation_requests = []
    
    for i, prompt_info in enumerate(prompts, 1):
        segment_id = prompt_info["segment_id"]
        original_prompt = prompt_info["primary_prompt"]
        
        # Enhance prompt for muscular deity characteristics
        prompt_text = enhance_prompt_for_deity(original_prompt)
        
        logger.info(f"📝 Processing segment {segment_id}/{len(prompts)}: {prompt_info['start_time']}-{prompt_info['end_time']}")
        logger.info(f"🎭 Original prompt: {original_prompt[:100]}...")
        logger.info(f"⚡ Enhanced prompt: {prompt_text[:100]}...")
        
        # Prepare request data
        request_data = {
            "prompt": prompt_text,
            "segment_id": segment_id,
            "face": None,  # No face for music-based generation
            "output_subfolder": output_subfolder_for_comfyui,
            "filename_prefix_text": f"music_segment",
            "video_start_image_path": None
        }
        
        # Send request to API server with retry mechanism
        submitted = False
        for attempt in range(1, MAX_API_RETRIES + 1):
            try:
                logger.info(f"📤 Sending generation request for segment {segment_id} (Attempt {attempt}/{MAX_API_RETRIES})...")
                logger.info(f"🔗 API URL: {config['api_server_url']}/generate/image")
                logger.info(f"📦 Request data: {request_data}")
                logger.info(f"⏰ Timeout: {REQUEST_TIMEOUT}s")
                
                # Test API server connectivity first
                logger.info(f"🧪 Testing API server health check...")
                try:
                    health_response = requests.get(f"{config['api_server_url']}/", timeout=5)
                    logger.info(f"🏥 Health check status: {health_response.status_code}")
                    if health_response.status_code == 200:
                        health_data = health_response.json()
                        logger.info(f"🏥 Health check data: {health_data}")
                    else:
                        logger.warning(f"⚠️ Health check failed: {health_response.text}")
                except Exception as health_e:
                    logger.error(f"❌ Health check failed: {health_e}")
                
                logger.info(f"🚀 Now sending POST request...")
                response = requests.post(
                    f"{config['api_server_url']}/generate/image",
                    json=request_data,
                    timeout=REQUEST_TIMEOUT
                )
                logger.info(f"✅ Received response: Status {response.status_code}")
                logger.info(f"📄 Response headers: {dict(response.headers)}")
                logger.info(f"📝 Response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                api_status = result.get('status', 'N/A')
                prompt_id = result.get('prompt_id', 'N/A')
                api_error = result.get('error', None)
                
                logger.info(f"   API Server Status: '{api_status}'")
                logger.info(f"   ComfyUI Prompt ID: '{prompt_id}'")
                if api_error:
                    logger.warning(f"   API Server reported error: {api_error}")
                
                if api_status == 'submitted' and prompt_id and prompt_id != 'N/A':
                    logger.info(f"✅ Segment {segment_id} submitted successfully! Prompt ID: {prompt_id}")
                    generation_requests.append({
                        "segment_id": segment_id,
                        "prompt_id": prompt_id,
                        "prompt_text": prompt_text[:100] + "...",
                        "start_time": prompt_info["start_time"],
                        "end_time": prompt_info["end_time"]
                    })
                    submitted = True
                    break
                else:
                    logger.error(f"❌ API submission failed for segment {segment_id}. Status: {api_status}, ID: {prompt_id}")
                    if api_error:
                        logger.error(f"   API Server reported error: {api_error}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Request timeout for segment {segment_id} (Attempt {attempt}): Request timed out after {REQUEST_TIMEOUT}s")
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Request error for segment {segment_id} (Attempt {attempt}): {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.warning(f"   Status Code: {e.response.status_code}")
                    try:
                        error_detail = e.response.json()
                        logger.warning(f"   Response Body: {error_detail}")
                    except:
                        logger.warning(f"   Response Text: {e.response.text[:500]}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error decoding JSON response for segment {segment_id} (Attempt {attempt}): {e}")
                if 'response' in locals():
                    logger.debug(f"   Raw Response Text: {response.text[:500]}")
            except Exception as e:
                logger.error(f"❌ Unexpected error for segment {segment_id} (Attempt {attempt}): {e}", exc_info=True)
            
            if attempt < MAX_API_RETRIES:
                logger.info(f"   Retrying in {API_RETRY_DELAY} seconds...")
                time.sleep(API_RETRY_DELAY)
        
        if not submitted:
            logger.error(f"❌ Failed to submit segment {segment_id} after {MAX_API_RETRIES} attempts")
        
        # Small delay between requests to avoid overwhelming the system
        time.sleep(3)
    
    logger.info(f"📊 Generation Summary:")
    logger.info(f"   Total segments: {len(prompts)}")
    logger.info(f"   Successful requests: {len(generation_requests)}")
    logger.info(f"   Failed requests: {len(prompts) - len(generation_requests)}")
    
    return generation_requests

# --- Function: Check ComfyUI Job Status (Based on Working Pattern) ---
def check_comfyui_job_status(comfyui_base_url: str, prompt_id: str):
    """Check status of a single job using ComfyUI /history endpoint (matches working pattern)"""
    if not prompt_id:
        logger.debug("Skipping history check: prompt_id is None or empty.")
        return None
        
    history_url = f"{comfyui_base_url}/history/{prompt_id}"
    logger.debug(f"Polling ComfyUI: {history_url}")
    
    try:
        response = requests.get(history_url, timeout=10)
        response.raise_for_status()
        history_data = response.json()
        
        if prompt_id in history_data:
            logger.debug(f"History found for prompt_id {prompt_id}.")
            return history_data[prompt_id]
        else:
            logger.debug(f"Prompt_id {prompt_id} not found in history response (running/pending).")
            return None
            
    except requests.exceptions.Timeout:
        logger.warning(f"Polling /history timed out for {prompt_id}.")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error polling /history/{prompt_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Error decoding history JSON for {prompt_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error polling history for {prompt_id}: {e}", exc_info=True)
        return None

# --- Function: Check Job Status via ComfyUI API (Updated for Individual Polling) ---
def check_job_status(prompt_ids, comfyui_base_url):
    """Check status of jobs using individual /history/{prompt_id} calls (working pattern)"""
    status = {
        "completed": [],
        "running": [],
        "pending": [],
        "failed": []
    }
    
    try:
        for prompt_id in prompt_ids:
            history_data = check_comfyui_job_status(comfyui_base_url, prompt_id)
            
            if history_data:
                # Job completed (found in history)
                status["completed"].append(prompt_id)
            else:
                # Job still running/pending (not in history yet)
                status["running"].append(prompt_id)
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Failed to check job status: {e}")
        return None

# --- Function: Wait for Image Generation Completion with Progress Tracking ---
def wait_for_image_generation_with_tracking(all_images_dir, generation_requests, comfyui_base_url):
    """Wait for all images to be generated using prompt ID tracking (based on working pattern)"""
    logger.info(f"⏳ Tracking image generation progress...")
    logger.info(f"   Total jobs: {len(generation_requests)}")
    logger.info(f"   Expected images: {len(generation_requests) * 4}")  # 4 images per segment
    logger.info(f"   Output directory: {all_images_dir}")
    
    prompt_ids = [req["prompt_id"] for req in generation_requests]
    start_time = time.time()
    last_progress_time = start_time  # Track when we last made progress
    
    with tqdm(total=len(generation_requests), desc="Processing Jobs", unit="job") as pbar:
        last_completed = 0
        
        while time.time() - last_progress_time < POLLING_TIMEOUT_IMAGE:
            # Check job status via ComfyUI APIs (using working pattern)
            status = check_job_status(prompt_ids, comfyui_base_url)
            
            if status:
                completed_count = len(status["completed"])
                running_count = len(status["running"])
                pending_count = len(status["pending"])
                failed_count = len(status["failed"])
                
                # Update progress bar and reset timeout on progress
                if completed_count > last_completed:
                    pbar.update(completed_count - last_completed)
                    last_completed = completed_count
                    last_progress_time = time.time()  # Reset timeout when progress is made
                    logger.info(f"🔄 Progress made! Timer reset. Jobs completed: {completed_count}/{len(generation_requests)}")
                
                # Update progress bar description
                pbar.set_description(f"Jobs - Done: {completed_count}, Running: {running_count}, Pending: {pending_count}, Failed: {failed_count}")
                
                logger.info(f"📊 Job Status - Completed: {completed_count}/{len(generation_requests)}, Running: {running_count}, Pending: {pending_count}, Failed: {failed_count}")
                
                # Check if all jobs are done (completed only, since we don't track failures in this pattern)
                if completed_count >= len(generation_requests):
                    # Collect actual generated images using ComfyUI history (working pattern)
                    collected_images = collect_generated_images_from_history(generation_requests, comfyui_base_url)
                    
                    logger.info(f"✅ All jobs completed! Completed: {completed_count}")
                    logger.info(f"📁 Generated images collected via history: {len(collected_images)}")
                    
                    pbar.close()
                    return len(collected_images) > 0  # Return True if we got at least some images
                
                # Log progress for any completed jobs
                if completed_count > 0:
                    logger.debug(f"📈 Progress: {completed_count}/{len(generation_requests)} jobs completed")
            
            time.sleep(POLLING_INTERVAL)
    
    # Timeout - check final status
    final_status = check_job_status(prompt_ids, comfyui_base_url)
    if final_status:
        completed = len(final_status["completed"])
        running = len(final_status["running"])
        total_elapsed = time.time() - start_time
        idle_time = time.time() - last_progress_time
        logger.warning(f"⚠️ Timeout reached after {idle_time:.0f}s of no activity (total time: {total_elapsed:.0f}s). Final status - Completed: {completed}, Still Running: {running}")
        
        # Collect actual generated images using ComfyUI history (working pattern)
        collected_images = collect_generated_images_from_history(generation_requests, comfyui_base_url)
        logger.info(f"📁 Generated images collected via history: {len(collected_images)}")
        
        return len(collected_images) > 0
    
    return False

# --- Function: Get Output Filenames from ComfyUI History (Working Pattern) ---
def get_output_filenames_from_history(history_entry, output_node_id):
    """Parse history data to find ALL filenames from a specific Save node. Returns list of Path objects."""
    output_paths = []
    if not history_entry or 'outputs' not in history_entry:
        logger.warning(f"History entry invalid or missing 'outputs' key for node {output_node_id}")
        return output_paths

    if output_node_id in history_entry['outputs']:
        node_output = history_entry['outputs'][output_node_id]
        logger.debug(f"Outputs found for node {output_node_id}")

        # Check for 'images'
        if 'images' in node_output and isinstance(node_output['images'], list):
            for image_info in node_output['images']:
                if (isinstance(image_info, dict) and 'filename' in image_info and 
                    'subfolder' in image_info and 'type' in image_info and image_info['type'] == 'output'):
                    subfolder = image_info['subfolder']
                    filename = image_info['filename']
                    relative_path = Path(subfolder) / filename if subfolder else Path(filename)
                    output_paths.append(relative_path)
                    logger.debug(f"Extracted relative image path: {relative_path}")
    
    return output_paths

# --- Function: Check ComfyUI Job Status via History ---
def check_comfyui_job_status(comfyui_base_url, prompt_id):
    """Check individual job status via /history/{prompt_id} endpoint"""
    if not prompt_id:
        return None
    
    history_url = f"{comfyui_base_url}/history/{prompt_id}"
    try:
        response = requests.get(history_url, timeout=10)
        response.raise_for_status()
        history_data = response.json()
        if prompt_id in history_data:
            return history_data[prompt_id]
        else:
            return None
    except Exception as e:
        logger.debug(f"Error checking history for {prompt_id}: {e}")
        return None

# --- Function: Collect Generated Images from History ---
def collect_generated_images_from_history(generation_requests, comfyui_base_url):
    """Collect actual generated images using ComfyUI history (working pattern)"""
    logger.info("🔍 Collecting generated images via ComfyUI history...")
    
    # Find the save node ID from the workflow
    save_node_id = "607"  # From the workflow file: "API_Image_Output_SaveNode"
    collected_images = []
    
    for req in generation_requests:
        prompt_id = req.get("prompt_id")
        segment_id = req.get("segment_id", "unknown")
        
        if not prompt_id:
            continue
            
        logger.info(f"📋 Checking history for segment {segment_id}, prompt_id: {prompt_id}")
        history_data = check_comfyui_job_status(comfyui_base_url, prompt_id)
        
        if history_data:
            relative_paths = get_output_filenames_from_history(history_data, save_node_id)
            logger.info(f"   Found {len(relative_paths)} output paths in history")
            
            for rel_path in relative_paths:
                full_path = (COMFYUI_OUTPUT_DIR_BASE / rel_path).resolve()
                if full_path.exists():
                    collected_images.append({
                        "segment_id": segment_id,
                        "prompt_id": prompt_id,
                        "image_path": full_path,
                        "relative_path": rel_path
                    })
                    logger.info(f"   ✅ Found: {full_path}")
                else:
                    logger.warning(f"   ❌ Missing: {full_path}")
        else:
            logger.info(f"   No history found for segment {segment_id}")
    
    logger.info(f"📊 Total images collected: {len(collected_images)}")
    return collected_images

# --- Function: Start Telegram Approval ---
def start_telegram_approval(collected_images):
    """Start Telegram approval process for generated images"""
    logger.info("📱 Starting Telegram approval process...")
    
    if not SEND_TELEGRAM_SCRIPT.exists():
        logger.error(f"❌ Telegram script not found: {SEND_TELEGRAM_SCRIPT}")
        return False
    
    if not collected_images:
        logger.error("❌ No images to send for approval")
        return False
    
    try:
        # Prepare telegram script arguments - pass individual image paths
        args = [sys.executable, str(SEND_TELEGRAM_SCRIPT)]
        
        # Add each image path as a separate argument
        for image_info in collected_images:
            image_path = image_info["image_path"]
            args.append(str(image_path))
            
        logger.info(f"📤 Sending {len(collected_images)} images for Telegram approval...")
        
        # Start telegram approval process
        process = subprocess.Popen(args, cwd=str(SCRIPT_DIR))
        
        logger.info("✅ Telegram approval process started")
        logger.info(f"   Check your Telegram bot for approval messages")
        logger.info(f"   Approvals will be saved to: {TELEGRAM_APPROVALS_JSON}")
        
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram approval: {e}")
        return False

# --- Function: Wait for Approvals ---
def wait_for_approvals():
    """Wait for user to approve images via Telegram"""
    logger.info("⏳ Waiting for Telegram approvals...")
    logger.info("   Use your Telegram bot to approve/reject images")
    logger.info("   Press Ctrl+C to skip approval and use all images")
    
    try:
        while True:
            if TELEGRAM_APPROVALS_JSON.exists():
                try:
                    with open(TELEGRAM_APPROVALS_JSON, 'r') as f:
                        approvals = json.load(f)
                    
                    approved_count = len([img for img in approvals.values() if img.get('approved', False)])
                    
                    if approved_count > 0:
                        logger.info(f"✅ Found {approved_count} approved images!")
                        return approvals
                        
                except json.JSONDecodeError:
                    pass  # File might be being written
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("⚠️ Approval skipped by user. Using all generated images.")
        return None

# --- Function: Copy Approved Images ---
def copy_approved_images(all_images_dir, approved_images_dir, approvals):
    """Copy approved images to the video generation folder"""
    if not approvals:
        # Use all images if no approvals
        logger.info("📋 No approvals found, copying all images...")
        image_files = list(all_images_dir.glob("*.png")) + list(all_images_dir.glob("*.jpg"))
        for img_file in image_files:
            shutil.copy2(img_file, approved_images_dir / img_file.name)
        logger.info(f"✅ Copied {len(image_files)} images for video generation")
        return len(image_files)
    
    # Copy only approved images
    approved_count = 0
    for img_name, img_data in approvals.items():
        if img_data.get('approved', False):
            src_path = all_images_dir / img_name
            if src_path.exists():
                shutil.copy2(src_path, approved_images_dir / img_name)
                approved_count += 1
    
    logger.info(f"✅ Copied {approved_count} approved images for video generation")
    return approved_count

# --- Main Function ---
def main():
    """Main execution flow for music pipeline"""
    logger.info("🎵 Starting Music-Based Image Generation Pipeline")
    logger.info("=" * 80)
    
    try:
        # Step 1: Load configuration
        config = load_config()
        
        # Step 2: Find latest music run
        music_folder = find_latest_music_run()
        if not music_folder:
            logger.error("❌ No music run folder found. Run audio_to_prompts_generator.py first!")
            return False
        
        # Step 3: Load music prompts
        prompts, metadata = load_music_prompts(music_folder)
        if not prompts:
            logger.error("❌ Failed to load music prompts")
            return False
        
        # Step 4: Create output directory
        output_run_dir, all_images_dir = create_output_run_directory(config, music_folder)
        
        # Step 5: Start API server
        api_process = start_api_server(config)
        if not api_process:
            logger.error("❌ Failed to start API server")
            return False
        
        try:
            # Step 5.5: Check ComfyUI queue status (for info only)
            check_comfyui_queue()
            
            # Step 6: Generate images
            generation_requests = generate_images_from_music(config, prompts, output_run_dir, all_images_dir)
            
            if not generation_requests:
                logger.error("❌ No images were submitted for generation")
                return False
            
            # Step 7: Wait for generation completion with prompt ID tracking
            generation_success = wait_for_image_generation_with_tracking(all_images_dir, generation_requests, config['comfyui_api_url'])

            if generation_success:
                # Step 8: Collect generated images and start Telegram approval
                collected_images = collect_generated_images_from_history(generation_requests, config['comfyui_api_url'])
                if not collected_images:
                    logger.error("❌ No generated images found to send for approval")
                    return False

                telegram_process = start_telegram_approval(collected_images)
                
                if telegram_process:
                    # Step 9: Wait for approvals
                    approvals = wait_for_approvals()
                    
                    # Step 10: Copy approved images
                    approved_images_dir = output_run_dir / APPROVED_IMAGES_SUBFOLDER
                    approved_count = copy_approved_images(all_images_dir, approved_images_dir, approvals)
                    
                    logger.info("=" * 80)
                    logger.info("🎉 MUSIC PIPELINE COMPLETED SUCCESSFULLY!")
                    logger.info("=" * 80)
                    logger.info(f"📁 Output Directory: {output_run_dir}")
                    logger.info(f"🎵 Music Source: {music_folder.name}")
                    logger.info(f"🎨 Total Images Generated: {len(list(all_images_dir.glob('*.png')))}")
                    logger.info(f"✅ Approved Images: {approved_count}")
                    logger.info(f"📝 Log File: {log_file}")
                    logger.info("=" * 80)
                    
                    return True
                else:
                    logger.error("❌ Failed to start Telegram approval")
                    return False
            else:
                logger.error("❌ Image generation incomplete")
                return False
                
        finally:
            # Cleanup: Stop API server
            if api_process:
                logger.info("🧹 Stopping API server...")
                api_process.terminate()
                time.sleep(2)
                if api_process.poll() is None:
                    api_process.kill()
                logger.info("✅ API server stopped")
        
    except KeyboardInterrupt:
        logger.info("⚠️ Pipeline interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Pipeline failed with error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Music pipeline completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Music pipeline failed!")
        sys.exit(1)