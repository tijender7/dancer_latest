#!/usr/bin/env python
"""
All-In-One Music-Based Image & Video Generation Pipeline

This single script handles everything:
1. Validates system requirements (ComfyUI, dependencies, config files)
2. Finds latest music analysis and loads prompts
3. Starts API server in background
4. Generates images for all music segments
5. Provides Telegram approval interface
6. Prepares approved images for video generation
7. Handles cleanup and error recovery

Usage: python music_pipeline_all_in_one.py

Author: Claude Code Assistant
Date: 2025-06-19
"""

from __future__ import annotations

import os
import sys
import json
import random
import requests
import shutil
import subprocess
import threading
import time
import logging
import glob
import uuid
import copy
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

# --- Import FastAPI for API Server ---
try:
    from fastapi import FastAPI, HTTPException, Body
    from pydantic import BaseModel, Field
    import uvicorn
    print("DEBUG: FastAPI imported successfully.")
except ImportError:
    print("ERROR: FastAPI library not found. Please install it: pip install fastapi uvicorn")
    sys.exit(1)

# --- Load environment variables (.env) ---
load_dotenv()

print("DEBUG: All-In-One Music Pipeline execution started.")

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
REQUEST_TIMEOUT = 60
POLLING_INTERVAL = 10
POLLING_TIMEOUT_IMAGE = 1800
POLLING_TIMEOUT_VIDEO = 3600

APPROVAL_SERVER_PORT = 5006  # Different port for music pipeline
APPROVAL_FILENAME = "approved_images.json"
APPROVED_IMAGES_SUBFOLDER = "approved_images_for_video"

# API Server Constants
API_SERVER_PORT = 8005
COMFYUI_TIMEOUT = 300

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
log_file = log_directory / f"music_pipeline_all_in_one_{datetime.now():%Y%m%d_%H%M%S}.log"
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
logger.info("🎵 Starting All-In-One Music Pipeline")

# --- Global Variables for API Server ---
api_server_process = None
api_app = None
config = None

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def check_dependencies():
    """Check if required Python packages are installed"""
    logger.info("Checking Python dependencies...")
    
    package_mappings = {
        "requests": "requests",
        "fastapi": "fastapi", 
        "uvicorn": "uvicorn",
        "flask": "flask",
        "tqdm": "tqdm",
        "google.generativeai": "google-generativeai"
    }
    
    missing_packages = []
    for import_name, pip_name in package_mappings.items():
        try:
            __import__(import_name)
            logger.info(f"  ✅ {pip_name}: OK")
        except ImportError:
            missing_packages.append(pip_name)
            logger.error(f"  ❌ {pip_name}: MISSING")
    
    if missing_packages:
        logger.error("Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        logger.error("Install with: pip install " + " ".join(missing_packages))
        return False
    
    logger.info("All required dependencies found")
    return True

def check_comfyui_running():
    """Check if ComfyUI is running and accessible"""
    logger.info("Checking if ComfyUI is running...")
    
    try:
        response = requests.get("http://127.0.0.1:8188/", timeout=10)
        if response.status_code == 200:
            logger.info("✅ ComfyUI is running and accessible")
            return True
        else:
            logger.error(f"❌ ComfyUI returned status: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"❌ ComfyUI is not accessible: {e}")
        return False

def check_config_files():
    """Check if required configuration files exist"""
    logger.info("Checking configuration files...")
    
    required_files = [
        "config_music.json",
        "base_workflows/API_flux_and_reactor_without_faceswap.json",
        "base_workflows/api_wanvideo_without_faceswap.json"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = SCRIPT_DIR / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        logger.error("Missing required files:")
        for file_name in missing_files:
            logger.error(f"   - {file_name}")
        return False
    
    logger.info("✅ All required configuration files found")
    return True

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

def load_config(config_path="config_music.json"):
    """Load and validate music pipeline configuration"""
    global config
    
    logger.info(f"Loading music config from '{config_path}'")
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
        
        logger.info(f"✅ Music config loaded successfully from {config_path_obj}")
        return config
        
    except Exception as e:
        logger.critical(f"CRITICAL error loading config '{config_path}': {e}", exc_info=True)
        sys.exit(1)

# =============================================================================
# MUSIC ANALYSIS FUNCTIONS
# =============================================================================

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

# =============================================================================
# EMBEDDED API SERVER
# =============================================================================

# --- Request Model ---
class MusicGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Primary prompt from music analysis")
    segment_id: int = Field(..., description="Segment number from music timeline")
    face: str | None = Field(None, description="Optional face image filename")
    output_subfolder: str = Field(..., description="Output subfolder path")
    filename_prefix_text: str = Field(..., description="Output filename prefix")
    video_start_image_path: str | None = Field(None, description="Start image for video generation")

# --- Helper Function (Find by Title) ---
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    """Finds the first node ID in a workflow dict matching the given _meta.title."""
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict):
             node_meta = node_data.get("_meta", {})
             if isinstance(node_meta, dict) and node_meta.get("title") == title:
                logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
                return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

def create_api_server():
    """Create and configure the FastAPI server"""
    global api_app, config
    
    # Load workflows
    try:
        BASE_WORKFLOW_IMAGE_PATH = (SCRIPT_DIR / config.get("base_workflow_image", "")).resolve()
        BASE_WORKFLOW_VIDEO_PATH = (SCRIPT_DIR / config.get("base_workflow_video", "")).resolve()
        SOURCE_FACES_PATH_CONFIG = (SCRIPT_DIR / config.get("source_faces_path", "source_faces")).resolve()
        SOURCE_FACES_SUBFOLDER_FOR_COMFYUI = SOURCE_FACES_PATH_CONFIG.name
        
        with open(BASE_WORKFLOW_IMAGE_PATH, "r", encoding="utf-8") as f: 
            base_image_workflow = json.load(f)
        with open(BASE_WORKFLOW_VIDEO_PATH, "r", encoding="utf-8") as f: 
            base_video_workflow = json.load(f)
        
        logger.info("✅ Base workflows loaded for API server")
        
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to load workflows for API server: {e}", exc_info=True)
        return None
    
    # Expected Node Titles
    PROMPT_NODE_TITLE = "API_Prompt_Input"
    FACE_NODE_TITLE = "API_Face_Input"
    SEED_NODE_TITLE = "API_Seed_Input"
    OUTPUT_PREFIX_NODE_TITLE = "API_Output_Prefix"
    IMAGE_OUTPUT_SAVE_NODE_TITLE = "API_Image_Output_SaveNode"
    VIDEO_START_IMAGE_NODE_TITLE = "API_Video_Start_Image"
    
    COMFYUI_BASE_URL = config.get("comfyui_api_url", "http://127.0.0.1:8188").rstrip('/')
    COMFYUI_PROMPT_URL = f"{COMFYUI_BASE_URL}/prompt"
    
    # --- Core Workflow Preparation Function ---
    def prepare_and_submit_workflow(
        base_workflow: dict,
        workflow_type: str,
        request: MusicGenerationRequest,
        client_id: str
    ):
        """Prepares a workflow by injecting music-based inputs and submits it to ComfyUI."""
        results = {"status": "pending", "error": None, "prompt_id": None, "response": None}
        wf_name_log = f"{workflow_type} Workflow"
        wf = copy.deepcopy(base_workflow)

        try:
            # --- Find Nodes ---
            logger.info(f"[{client_id}] Finding nodes for {wf_name_log} (Segment {request.segment_id})...")
            prompt_node_id = find_node_id_by_title(wf, PROMPT_NODE_TITLE, wf_name_log)
            face_node_id = find_node_id_by_title(wf, FACE_NODE_TITLE, wf_name_log)
            seed_node_id = find_node_id_by_title(wf, SEED_NODE_TITLE, wf_name_log)
            output_prefix_node_id = find_node_id_by_title(wf, OUTPUT_PREFIX_NODE_TITLE, wf_name_log)
            video_start_node_id = None
            if workflow_type == "Video":
                 video_start_node_id = find_node_id_by_title(wf, VIDEO_START_IMAGE_NODE_TITLE, wf_name_log)

            # --- Validate Nodes ---
            if not prompt_node_id: 
                raise ValueError(f"Could not find Prompt node '{PROMPT_NODE_TITLE}'.")
            if request.face and not face_node_id:
                logger.warning(f"Face provided ('{request.face}') but node '{FACE_NODE_TITLE}' not found in {wf_name_log}.")
            if not seed_node_id: 
                raise ValueError(f"Could not find Seed node '{SEED_NODE_TITLE}'.")
            if not output_prefix_node_id: 
                raise ValueError(f"Could not find Output Prefix node '{OUTPUT_PREFIX_NODE_TITLE}'.")
            if workflow_type == "Video" and request.video_start_image_path and not video_start_node_id:
                 raise ValueError(f"Video start image provided but LoadImage node '{VIDEO_START_IMAGE_NODE_TITLE}' not found.")

            # --- Inject Music Prompt ---
            if prompt_node_id:
                prompt_input_key = "text"
                node_class = wf[prompt_node_id].get("class_type")
                if node_class == "CLIPTextEncode (Prompt Simplified)": 
                    prompt_input_key = "text"
                elif node_class == "WanVideoTextEncode": 
                    prompt_input_key = "positive_prompt"
                
                logger.info(f"[{client_id}] Injecting music prompt for segment {request.segment_id} into Node {prompt_node_id}")
                wf[prompt_node_id]["inputs"][prompt_input_key] = request.prompt

            # --- Inject Face (Optional) ---
            if face_node_id and request.face:
                face_path_str_for_comfyui = (Path(SOURCE_FACES_SUBFOLDER_FOR_COMFYUI) / request.face).as_posix()
                logger.info(f"[{client_id}] Injecting face path '{face_path_str_for_comfyui}' into Node {face_node_id}")
                wf[face_node_id]["inputs"]["image"] = face_path_str_for_comfyui
            else:
                logger.info(f"[{client_id}] No face provided for segment {request.segment_id}")

            # --- Generate Random Seed ---
            if seed_node_id:
                seed_input_key = "seed"
                seed_node_class = wf[seed_node_id].get("class_type")
                if seed_node_class == "RandomNoise": 
                    seed_input_key = "noise_seed"
                elif seed_node_class in ["SetNodeSeed", "Seed"]: 
                    seed_input_key = "seed"
                
                random_seed = random.randint(0, 2**32 - 1)
                logger.info(f"[{client_id}] Injecting random seed {random_seed} for segment {request.segment_id}")
                wf[seed_node_id]["inputs"][seed_input_key] = random_seed

            # --- Inject Video Start Image (For Video Workflow) ---
            if workflow_type == "Video" and video_start_node_id and request.video_start_image_path:
                start_image_path_str = request.video_start_image_path.replace("\\", "/")
                logger.info(f"[{client_id}] Injecting video start image '{start_image_path_str}' for segment {request.segment_id}")
                wf[video_start_node_id]["inputs"]["image"] = start_image_path_str
            elif workflow_type == "Video":
                logger.info(f"[{client_id}] No video start image provided for segment {request.segment_id}")

            # --- Set Output Path and Prefix (using FileNamePrefix node) ---
            if output_prefix_node_id:
                prefix_node_class = wf[output_prefix_node_id].get("class_type")
                if prefix_node_class == "FileNamePrefix":
                    # ComfyUI expects forward slashes for paths
                    clean_subfolder = request.output_subfolder.replace("\\", "/")
                    filename_prefix = f"{request.filename_prefix_text}_segment_{request.segment_id:03d}"
                    
                    logger.info(f"[{client_id}] Injecting custom_directory '{clean_subfolder}' into Node {output_prefix_node_id}")
                    wf[output_prefix_node_id]["inputs"]["custom_directory"] = clean_subfolder
                    logger.info(f"[{client_id}] Injecting custom_text '{filename_prefix}' into Node {output_prefix_node_id}")
                    wf[output_prefix_node_id]["inputs"]["custom_text"] = filename_prefix
                else:
                    # Fallback for other output node types
                    output_folder_path = request.output_subfolder
                    filename_prefix = f"{request.filename_prefix_text}_segment_{request.segment_id:03d}"
                    logger.info(f"[{client_id}] Setting output text for {prefix_node_class}: '{output_folder_path}/{filename_prefix}'")
                    wf[output_prefix_node_id]["inputs"]["text"] = f"{output_folder_path}/{filename_prefix}"
            else:
                logger.error(f"[{client_id}] Output Prefix node '{OUTPUT_PREFIX_NODE_TITLE}' ID not found, skipping output path injection.")

            # --- Submit to ComfyUI ---
            submit_payload = {"prompt": wf, "client_id": client_id}
            logger.info(f"[{client_id}] Submitting {workflow_type} workflow to ComfyUI for segment {request.segment_id}...")
            
            response = requests.post(COMFYUI_PROMPT_URL, json=submit_payload, timeout=COMFYUI_TIMEOUT)
            response.raise_for_status()
            response_data = response.json()
            
            prompt_id = response_data.get("prompt_id")
            if prompt_id:
                logger.info(f"[{client_id}] ✅ Workflow submitted successfully! Prompt ID: {prompt_id} (Segment {request.segment_id})")
                results.update({"status": "submitted", "prompt_id": prompt_id, "response": response_data})
            else:
                logger.error(f"[{client_id}] ❌ No prompt_id in ComfyUI response for segment {request.segment_id}")
                results.update({"status": "error", "error": "No prompt_id in ComfyUI response", "response": response_data})

        except requests.exceptions.Timeout:
            error_msg = f"ComfyUI request timeout after {COMFYUI_TIMEOUT}s for segment {request.segment_id}"
            logger.error(f"[{client_id}] {error_msg}")
            results.update({"status": "error", "error": error_msg})
        except requests.exceptions.RequestException as e:
            error_msg = f"ComfyUI request failed for segment {request.segment_id}: {str(e)}"
            logger.error(f"[{client_id}] {error_msg}")
            results.update({"status": "error", "error": error_msg})
        except Exception as e:
            error_msg = f"Workflow preparation failed for segment {request.segment_id}: {str(e)}"
            logger.error(f"[{client_id}] {error_msg}", exc_info=True)
            results.update({"status": "error", "error": error_msg})

        return results
    
    # --- Create FastAPI App ---
    api_app = FastAPI(title="ComfyUI Music Generation API v5", description="API for music-based image generation")
    
    # --- API Endpoints ---
    @api_app.get("/")
    async def root():
        """Health check endpoint"""
        return {
            "message": "ComfyUI Music Generation API v5",
            "status": "running",
            "config": {
                "comfyui_url": COMFYUI_BASE_URL,
                "port": API_SERVER_PORT,
                "workflows": {
                    "image": Path(config.get("base_workflow_image", "")).name,
                    "video": Path(config.get("base_workflow_video", "")).name
                }
            }
        }

    @api_app.post("/generate/image")
    async def generate_image(request: MusicGenerationRequest):
        """Generate image from music segment prompt"""
        client_id = str(uuid.uuid4())
        logger.info(f"[{client_id}] 🎵 Image generation request for segment {request.segment_id}")
        
        try:
            results = prepare_and_submit_workflow(base_image_workflow, "Image", request, client_id)
            
            if results["status"] == "submitted":
                return {
                    "status": "submitted",  # Match working pattern
                    "message": f"Image generation started for segment {request.segment_id}",
                    "prompt_id": results["prompt_id"],
                    "client_id": client_id,
                    "segment_id": request.segment_id
                }
            else:
                raise HTTPException(status_code=500, detail=results["error"])
                
        except Exception as e:
            logger.error(f"[{client_id}] Image generation failed for segment {request.segment_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @api_app.post("/generate/video")
    async def generate_video(request: MusicGenerationRequest):
        """Generate video from music segment prompt"""
        client_id = str(uuid.uuid4())
        logger.info(f"[{client_id}] 🎬 Video generation request for segment {request.segment_id}")
        
        try:
            results = prepare_and_submit_workflow(base_video_workflow, "Video", request, client_id)
            
            if results["status"] == "submitted":
                return {
                    "status": "submitted",  # Match working pattern
                    "message": f"Video generation started for segment {request.segment_id}",
                    "prompt_id": results["prompt_id"],
                    "client_id": client_id,
                    "segment_id": request.segment_id
                }
            else:
                raise HTTPException(status_code=500, detail=results["error"])
                
        except Exception as e:
            logger.error(f"[{client_id}] Video generation failed for segment {request.segment_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @api_app.get("/status")
    async def get_status():
        """Get API server status and configuration"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "comfyui_api_url": COMFYUI_BASE_URL,
                "port": API_SERVER_PORT,
                "workflow_image": Path(config.get("base_workflow_image", "")).name,
                "workflow_video": Path(config.get("base_workflow_video", "")).name,
                "source_faces_dir": str(SOURCE_FACES_PATH_CONFIG),
                "node_titles": {
                    "prompt": PROMPT_NODE_TITLE,
                    "face": FACE_NODE_TITLE,
                    "seed": SEED_NODE_TITLE,
                    "output_prefix": OUTPUT_PREFIX_NODE_TITLE,
                    "video_start": VIDEO_START_IMAGE_NODE_TITLE
                }
            }
        }
    
    return api_app

def start_embedded_api_server():
    """Start the embedded API server in a background thread"""
    global api_server_process
    
    logger.info(f"🚀 Starting embedded API server on port {API_SERVER_PORT}...")
    
    try:
        api_app = create_api_server()
        if not api_app:
            logger.error("❌ Failed to create API server")
            return None
        
        # Start server in background thread
        def run_server():
            uvicorn.run(api_app, host="127.0.0.1", port=API_SERVER_PORT, log_level="error")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(5)
        
        # Test if server is running
        max_retries = 6
        for retry in range(max_retries):
            try:
                response = requests.get(f"http://127.0.0.1:{API_SERVER_PORT}/", timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Embedded API Server started successfully")
                    return server_thread
                else:
                    logger.warning(f"⚠️ API Server returned status: {response.status_code}, retrying...")
            except requests.RequestException as e:
                logger.warning(f"⚠️ Retry {retry+1}/{max_retries}: {e}")
                if retry == max_retries - 1:
                    logger.error(f"❌ Failed to connect to API Server after {max_retries} retries")
                    return None
            
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"❌ Failed to start embedded API Server: {e}")
        return None

# =============================================================================
# IMAGE GENERATION FUNCTIONS
# =============================================================================

def generate_images_from_music(config, prompts, output_run_dir, all_images_dir):
    """Generate images for each music segment prompt"""
    logger.info(f"🎨 Starting image generation for {len(prompts)} music segments")
    
    # Prepare for ComfyUI path generation
    output_subfolder_for_comfyui = f"{output_run_dir.name}/all_images"
    
    generation_requests = []
    
    for i, prompt_info in enumerate(prompts, 1):
        segment_id = prompt_info["segment_id"]
        prompt_text = prompt_info["primary_prompt"]
        
        logger.info(f"📝 Processing segment {segment_id}/{len(prompts)}: {prompt_info['start_time']}-{prompt_info['end_time']}")
        
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
                
                response = requests.post(
                    f"http://127.0.0.1:{API_SERVER_PORT}/generate/image",
                    json=request_data,
                    timeout=REQUEST_TIMEOUT
                )
                
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
        time.sleep(2)
    
    logger.info(f"📊 Generation Summary:")
    logger.info(f"   Total segments: {len(prompts)}")
    logger.info(f"   Successful requests: {len(generation_requests)}")
    logger.info(f"   Failed requests: {len(prompts) - len(generation_requests)}")
    
    return generation_requests

# =============================================================================
# PROGRESS TRACKING FUNCTIONS
# =============================================================================

def check_comfyui_job_status(comfyui_base_url, prompt_id):
    """Check status of a single job using ComfyUI history API (working pattern)"""
    try:
        history_url = f"{comfyui_base_url}/history/{prompt_id}"
        history_response = requests.get(history_url, timeout=10)
        
        if history_response.status_code == 200:
            history_data = history_response.json()
            return {"status": "completed", "history_data": history_data}
        elif history_response.status_code == 404:
            # Job not in history - check if it's in queue
            queue_response = requests.get(f"{comfyui_base_url}/queue", timeout=10)
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                
                # Check running queue
                for job in queue_data.get("queue_running", []):
                    if job[1] == prompt_id:  # job format: [number, prompt_id, prompt_data]
                        return {"status": "running"}
                
                # Check pending queue
                for job in queue_data.get("queue_pending", []):
                    if job[1] == prompt_id:
                        return {"status": "pending"}
                
                # Not found anywhere - assume pending
                return {"status": "pending"}
            else:
                return {"status": "unknown"}
        else:
            return {"status": "unknown"}
            
    except Exception as e:
        logger.debug(f"Error checking status for {prompt_id}: {e}")
        return {"status": "unknown"}

def get_output_filenames_from_history(history_data):
    """Extract output filenames from ComfyUI history (working pattern)"""
    try:
        if not history_data:
            return []
        
        output_filenames = []
        outputs = history_data.get("outputs", {})
        
        for node_id, node_outputs in outputs.items():
            if isinstance(node_outputs, dict):
                # Look for image outputs
                for output_type, output_list in node_outputs.items():
                    if isinstance(output_list, list):
                        for output_item in output_list:
                            if isinstance(output_item, dict):
                                # Check for filename or similar keys
                                if "filename" in output_item:
                                    output_filenames.append(output_item["filename"])
                                elif "name" in output_item:
                                    output_filenames.append(output_item["name"])
        
        return output_filenames
    except Exception as e:
        logger.debug(f"Error extracting filenames from history: {e}")
        return []

def wait_for_image_generation_with_tracking(all_images_dir, generation_requests):
    """Wait for all images to be generated using working automation pattern with smart timeout"""
    logger.info(f"⏳ Tracking image generation progress (using working pattern)...")
    logger.info(f"   Total jobs: {len(generation_requests)}")
    logger.info(f"   Expected images: {len(generation_requests) * 4}")  # 4 images per segment
    logger.info(f"   Output directory: {all_images_dir}")
    
    comfyui_base_url = "http://127.0.0.1:8188"
    comfyui_output_base = Path("H:/dancers_content")  # ComfyUI's actual output directory
    
    # Smart timeout logic: Reset when progress is made
    PROGRESS_TIMEOUT = 600  # 10 minutes without ANY progress = timeout
    last_progress_time = time.time()
    total_start_time = time.time()
    
    # Track job details with history data
    job_details = {}
    for req in generation_requests:
        job_details[req["prompt_id"]] = {
            "segment_id": req["segment_id"],
            "status": "pending",
            "history_data": None,
            "output_files": []
        }
    
    with tqdm(total=len(generation_requests), desc="Processing Jobs", unit="job") as pbar:
        last_completed = 0
        
        while True:
            current_time = time.time()
            time_since_progress = current_time - last_progress_time
            total_elapsed = current_time - total_start_time
            completed_count = 0
            running_count = 0
            pending_count = 0
            failed_count = 0
            progress_made = False
            
            # Check each job individually using working pattern
            for prompt_id, details in job_details.items():
                if details["status"] != "completed":
                    job_status = check_comfyui_job_status(comfyui_base_url, prompt_id)
                    
                    # Detect progress (status change)
                    if job_status["status"] != details["status"]:
                        progress_made = True
                        logger.info(f"🔄 Job {prompt_id} status changed: {details['status']} → {job_status['status']}")
                    
                    details["status"] = job_status["status"]
                    
                    if job_status["status"] == "completed" and "history_data" in job_status:
                        details["history_data"] = job_status["history_data"]
                        # Extract output filenames from history
                        output_filenames = get_output_filenames_from_history(job_status["history_data"])
                        details["output_files"] = output_filenames
                        logger.info(f"✅ Job {prompt_id} completed, output files: {output_filenames}")
                        progress_made = True  # Completion is definite progress
                
                # Count statuses
                if details["status"] == "completed":
                    completed_count += 1
                elif details["status"] == "running":
                    running_count += 1
                elif details["status"] == "pending":
                    pending_count += 1
                else:
                    failed_count += 1
            
            # Reset timeout if progress was made
            if progress_made or completed_count > last_completed:
                last_progress_time = current_time
                if completed_count > last_completed:
                    logger.info(f"📈 Progress made! Timeout reset. New jobs completed: {completed_count - last_completed}")
            
            # Update progress bar
            if completed_count > last_completed:
                pbar.update(completed_count - last_completed)
                last_completed = completed_count
            
            # Update progress bar description with timeout info
            remaining_timeout = max(0, PROGRESS_TIMEOUT - time_since_progress)
            pbar.set_description(f"Jobs - Done: {completed_count}, Running: {running_count}, Pending: {pending_count}, Failed: {failed_count} | Timeout: {remaining_timeout:.0f}s")
            
            logger.info(f"📊 Job Status - Completed: {completed_count}/{len(generation_requests)}, Running: {running_count}, Pending: {pending_count}, Failed: {failed_count}")
            logger.info(f"⏱️ Time since last progress: {time_since_progress:.1f}s / {PROGRESS_TIMEOUT}s, Total elapsed: {total_elapsed/60:.1f}min")
            
            # Check timeout condition
            if time_since_progress > PROGRESS_TIMEOUT:
                logger.warning(f"⚠️ Timeout reached: No progress for {PROGRESS_TIMEOUT}s ({PROGRESS_TIMEOUT/60:.1f} minutes)")
                logger.warning(f"   Final status - Completed: {completed_count}, Still Running: {running_count}")
                break
            
            # Check if all jobs are done (completed or failed)
            if completed_count + failed_count >= len(generation_requests):
                logger.info(f"✅ All jobs processed! Completed: {completed_count}, Failed: {failed_count}")
                
                # Use working pattern: find files based on ComfyUI history data
                found_files = []
                for prompt_id, details in job_details.items():
                    if details["status"] == "completed" and details["output_files"]:
                        for filename in details["output_files"]:
                            # Build actual file path in ComfyUI output directory
                            file_path = comfyui_output_base / filename
                            if file_path.exists():
                                found_files.append(file_path)
                                logger.info(f"Found output file: {file_path}")
                            else:
                                logger.warning(f"History reported file {file_path}, but it doesn't exist on disk!")
                
                logger.info(f"📁 Found {len(found_files)} generated images using history data")
                
                # Copy found files to expected directory for approval workflow
                if found_files:
                    logger.info("📋 Copying images to expected directory for approval...")
                    all_images_dir.mkdir(parents=True, exist_ok=True)
                    
                    for file_path in found_files:
                        try:
                            dest_path = all_images_dir / file_path.name
                            shutil.copy2(file_path, dest_path)
                            logger.debug(f"Copied {file_path.name} to approval directory")
                        except Exception as e:
                            logger.warning(f"Failed to copy {file_path.name}: {e}")
                    
                    # Recount images in approval directory
                    image_files = list(all_images_dir.glob("*.png")) + list(all_images_dir.glob("*.jpg"))
                    actual_count = len(image_files)
                    logger.info(f"📁 Images ready for approval: {actual_count}")
                else:
                    actual_count = 0
                    logger.warning("⚠️ No images found even with history-based tracking!")
                
                pbar.close()
                return actual_count > 0  # Return True if we got at least some images
            
            # If some jobs failed but others are still running/pending, continue
            if failed_count > 0:
                logger.warning(f"⚠️ {failed_count} jobs failed, but continuing with remaining jobs...")
            
            time.sleep(POLLING_INTERVAL)
    
    # Handle timeout case - process any completed jobs we have
    logger.info(f"🕐 Processing timeout case. Completed jobs: {completed_count}")
    
    # Use working pattern: find files based on ComfyUI history data (even for partial completion)
    found_files = []
    for prompt_id, details in job_details.items():
        if details["status"] == "completed" and details["output_files"]:
            for filename in details["output_files"]:
                # Build actual file path in ComfyUI output directory
                file_path = comfyui_output_base / filename
                if file_path.exists():
                    found_files.append(file_path)
                    logger.info(f"Found output file: {file_path}")
                else:
                    logger.warning(f"History reported file {file_path}, but it doesn't exist on disk!")
    
    logger.info(f"📁 Found {len(found_files)} generated images using history data")
    
    # Copy found files to expected directory for approval workflow
    if found_files:
        logger.info("📋 Copying images to expected directory for approval...")
        all_images_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in found_files:
            try:
                dest_path = all_images_dir / file_path.name
                shutil.copy2(file_path, dest_path)
                logger.debug(f"Copied {file_path.name} to approval directory")
            except Exception as e:
                logger.warning(f"Failed to copy {file_path.name}: {e}")
        
        # Recount images in approval directory
        image_files = list(all_images_dir.glob("*.png")) + list(all_images_dir.glob("*.jpg"))
        actual_count = len(image_files)
        logger.info(f"📁 Images ready for approval: {actual_count}")
        
        # Return True if we have at least some images, even if not all completed
        if actual_count > 0:
            logger.info(f"✅ Proceeding with {actual_count} images (partial completion due to timeout)")
            pbar.close()
            return True
    
    logger.warning("⚠️ No usable images found even with timeout handling!")
    pbar.close()
    return False

# =============================================================================
# TELEGRAM APPROVAL FUNCTIONS
# =============================================================================

def start_telegram_approval(all_images_dir):
    """Start Telegram approval process for generated images"""
    logger.info("📱 Starting Telegram approval process...")
    
    if not SEND_TELEGRAM_SCRIPT.exists():
        logger.error(f"❌ Telegram script not found: {SEND_TELEGRAM_SCRIPT}")
        return False
    
    try:
        # Prepare telegram script arguments
        args = [
            sys.executable, str(SEND_TELEGRAM_SCRIPT),
            "--images_dir", str(all_images_dir),
            "--output_file", str(TELEGRAM_APPROVALS_JSON)
        ]
        
        # Start telegram approval process
        process = subprocess.Popen(args, cwd=str(SCRIPT_DIR))
        
        logger.info("✅ Telegram approval process started")
        logger.info(f"   Check your Telegram bot for approval messages")
        logger.info(f"   Approvals will be saved to: {TELEGRAM_APPROVALS_JSON}")
        
        return process
        
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram approval: {e}")
        return False

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

# =============================================================================
# MAIN EXECUTION FUNCTIONS
# =============================================================================

def print_banner():
    """Print startup banner"""
    print("\n" + "="*80)
    print("🎵 ALL-IN-ONE MUSIC-BASED IMAGE & VIDEO GENERATION PIPELINE")
    print("="*80)
    print("This pipeline will:")
    print("1. 🔍 Validate system requirements")
    print("2. 📝 Load music prompts from latest analysis")
    print("3. 🚀 Start embedded API server")
    print("4. 🎨 Generate images for each music segment")
    print("5. 📱 Provide Telegram approval interface")
    print("6. 🎬 Prepare for video generation")
    print("="*80)
    print()

def print_summary(success: bool, output_run_dir=None, approved_count=0, total_images=0):
    """Print completion summary"""
    print("\n" + "="*80)
    if success:
        print("🎉 ALL-IN-ONE MUSIC PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("✅ What was accomplished:")
        print("   • System requirements validated")
        print("   • API server started and configured")
        print("   • Images generated for all music segments")
        print("   • Telegram approval process completed")
        print("   • Approved images prepared for video generation")
        print()
        if output_run_dir:
            print("📁 Results:")
            print(f"   Output Directory: {output_run_dir}")
            print(f"   Total Images Generated: {total_images}")
            print(f"   Approved Images: {approved_count}")
        print()
        print("🎬 Next steps:")
        print("   • Review approved images in the output folder")
        print("   • Run video generation if desired")
        print("   • Upload content to social media")
    else:
        print("💥 ALL-IN-ONE MUSIC PIPELINE FAILED!")
        print("="*80)
        print("❌ Please check the logs above for error details")
        print("📝 Common issues:")
        print("   • ComfyUI not running (start with: python main.py)")
        print("   • No music prompts available (run: python audio_to_prompts_generator.py)")
        print("   • Missing dependencies (install with pip)")
        print("   • Configuration file issues")
    print("="*80)

def main():
    """Main execution flow for all-in-one music pipeline"""
    print_banner()
    
    logger.info("🎵 Starting All-In-One Music-Based Image Generation Pipeline")
    logger.info("=" * 80)
    
    try:
        # Step 1: Validate dependencies
        if not check_dependencies():
            print_summary(False)
            return False
        
        # Step 2: Check configuration files
        if not check_config_files():
            print_summary(False)
            return False
        
        # Step 3: Load configuration
        config = load_config()
        
        # Step 4: Check ComfyUI
        if not check_comfyui_running():
            logger.error("Please start ComfyUI first:")
            logger.error("   1. Navigate to ComfyUI directory")
            logger.error("   2. Run: python main.py")
            logger.error("   3. Wait for 'Starting server' message")
            logger.error("   4. Then run this script again")
            print_summary(False)
            return False
        
        # Step 5: Find latest music run
        music_folder = find_latest_music_run()
        if not music_folder:
            logger.error("❌ No music run folder found. Run audio_to_prompts_generator.py first!")
            print_summary(False)
            return False
        
        # Step 6: Load music prompts
        prompts, metadata = load_music_prompts(music_folder)
        if not prompts:
            logger.error("❌ Failed to load music prompts")
            print_summary(False)
            return False
        
        # Step 7: Create output directory
        output_run_dir, all_images_dir = create_output_run_directory(config, music_folder)
        
        # Step 8: Start embedded API server
        api_server_thread = start_embedded_api_server()
        if not api_server_thread:
            logger.error("❌ Failed to start embedded API server")
            print_summary(False)
            return False
        
        try:
            # Step 9: Generate images
            generation_requests = generate_images_from_music(config, prompts, output_run_dir, all_images_dir)
            
            if not generation_requests:
                logger.error("❌ No images were submitted for generation")
                print_summary(False)
                return False
            
            # Step 10: Wait for generation completion with prompt ID tracking
            generation_success = wait_for_image_generation_with_tracking(all_images_dir, generation_requests)
            
            if generation_success:
                # Count total generated images
                total_images = len(list(all_images_dir.glob("*.png")) + list(all_images_dir.glob("*.jpg")))
                
                # Step 11: Start Telegram approval
                telegram_process = start_telegram_approval(all_images_dir)
                
                if telegram_process:
                    # Step 12: Wait for approvals
                    approvals = wait_for_approvals()
                    
                    # Step 13: Copy approved images
                    approved_images_dir = output_run_dir / APPROVED_IMAGES_SUBFOLDER
                    approved_count = copy_approved_images(all_images_dir, approved_images_dir, approvals)
                    
                    logger.info("=" * 80)
                    logger.info("🎉 ALL-IN-ONE MUSIC PIPELINE COMPLETED SUCCESSFULLY!")
                    logger.info("=" * 80)
                    logger.info(f"📁 Output Directory: {output_run_dir}")
                    logger.info(f"🎵 Music Source: {music_folder.name}")
                    logger.info(f"🎨 Total Images Generated: {total_images}")
                    logger.info(f"✅ Approved Images: {approved_count}")
                    logger.info(f"📝 Log File: {log_file}")
                    logger.info("=" * 80)
                    
                    print_summary(True, output_run_dir, approved_count, total_images)
                    return True
                else:
                    logger.error("❌ Failed to start Telegram approval")
                    print_summary(False)
                    return False
            else:
                logger.error("❌ Image generation incomplete")
                print_summary(False)
                return False
                
        finally:
            # Cleanup: API server will auto-cleanup since it's in daemon thread
            logger.info("🧹 Cleanup complete (API server will stop automatically)")
        
    except KeyboardInterrupt:
        logger.info("⚠️ Pipeline interrupted by user")
        print_summary(False)
        return False
    except Exception as e:
        logger.error(f"❌ Pipeline failed with error: {e}", exc_info=True)
        print_summary(False)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 All-in-one music pipeline completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 All-in-one music pipeline failed!")
        sys.exit(1)