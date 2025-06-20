# api_server_v5_music.py (Music-Based Image Generation API Server)
import os
import json
import requests
import uuid
import copy
import random
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import uvicorn
from pathlib import Path
import logging
import sys
import time

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if logger.hasHandlers(): 
    logger.handlers.clear()
logger.addHandler(console_handler)
logger.info("Initializing Music API Server v5...")

# --- Configuration Loading ---
CONFIG_FILE = "config_music.json"
try:
    script_dir = Path(__file__).resolve().parent
    config_path_obj = script_dir / CONFIG_FILE
    if not config_path_obj.is_file(): 
        logger.critical(f"CRITICAL: Config file not found: {config_path_obj}")
        sys.exit(1)
    with open(config_path_obj, "r", encoding='utf-8') as f: 
        config = json.load(f)
    logger.info(f"Config loaded successfully from '{CONFIG_FILE}'.")
except Exception as e: 
    logger.critical(f"CRITICAL: Failed to load config '{CONFIG_FILE}': {e}", exc_info=True)
    sys.exit(1)

# --- Constants ---
COMFYUI_BASE_URL = config.get("comfyui_api_url", "http://127.0.0.1:8188").rstrip('/')
COMFYUI_PROMPT_URL = f"{COMFYUI_BASE_URL}/prompt"
BASE_WORKFLOW_IMAGE_PATH = (script_dir / config.get("base_workflow_image", "")).resolve()
BASE_WORKFLOW_VIDEO_PATH = (script_dir / config.get("base_workflow_video", "")).resolve()
SOURCE_FACES_PATH_CONFIG = (script_dir / config.get("source_faces_path", "source_faces")).resolve()
SOURCE_FACES_SUBFOLDER_FOR_COMFYUI = SOURCE_FACES_PATH_CONFIG.name

# Expected Node Titles (Match workflow files' _meta.title)
PROMPT_NODE_TITLE = "API_Prompt_Input"
FACE_NODE_TITLE = "API_Face_Input"
SEED_NODE_TITLE = "API_Seed_Input"
OUTPUT_PREFIX_NODE_TITLE = "API_Output_Prefix"
IMAGE_OUTPUT_SAVE_NODE_TITLE = "API_Image_Output_SaveNode"
VIDEO_START_IMAGE_NODE_TITLE = "API_Video_Start_Image"

COMFYUI_TIMEOUT = 300

# --- Validation ---
if not BASE_WORKFLOW_IMAGE_PATH.is_file(): 
    logger.critical(f"CRITICAL: Image workflow not found: '{BASE_WORKFLOW_IMAGE_PATH}'")
    sys.exit(1)
if not BASE_WORKFLOW_VIDEO_PATH.is_file(): 
    logger.critical(f"CRITICAL: Video workflow not found: '{BASE_WORKFLOW_VIDEO_PATH}'")
    sys.exit(1)
if not SOURCE_FACES_PATH_CONFIG.is_dir(): 
    logger.warning(f"Source faces dir not found: {SOURCE_FACES_PATH_CONFIG}")

logger.info(f"Music API Server Configuration:")
logger.info(f"  ComfyUI Prompt URL: {COMFYUI_PROMPT_URL}")
logger.info(f"  Image Workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
logger.info(f"  Video Workflow: {BASE_WORKFLOW_VIDEO_PATH.name}")
logger.info(f"  Source Faces Dir: {SOURCE_FACES_PATH_CONFIG}")
logger.info(f"  API Server Port: 8005 (Music Pipeline)")

# --- Load Base Workflows ---
try:
    with open(BASE_WORKFLOW_IMAGE_PATH, "r", encoding="utf-8") as f: 
        base_image_workflow = json.load(f)
    with open(BASE_WORKFLOW_VIDEO_PATH, "r", encoding="utf-8") as f: 
        base_video_workflow = json.load(f)
    logger.info("Base workflows loaded successfully.")
except Exception as e: 
    logger.critical(f"CRITICAL: Failed to load workflows: {e}", exc_info=True)
    sys.exit(1)

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

# --- FastAPI App ---
app = FastAPI(title="ComfyUI Music Generation API v5", description="API for music-based image generation")

# --- Request Model ---
class MusicGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Primary prompt from music analysis")
    segment_id: int = Field(..., description="Segment number from music timeline")
    face: str | None = Field(None, description="Optional face image filename")
    output_subfolder: str = Field(..., description="Output subfolder path")
    filename_prefix_text: str = Field(..., description="Output filename prefix")
    video_start_image_path: str | None = Field(None, description="Start image for video generation")

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
        logger.info(f"[{client_id}] Workflow has {len(wf)} nodes")
        
        logger.info(f"[{client_id}] Looking for prompt node: '{PROMPT_NODE_TITLE}'")
        prompt_node_id = find_node_id_by_title(wf, PROMPT_NODE_TITLE, wf_name_log)
        logger.info(f"[{client_id}] Prompt node result: {prompt_node_id}")
        
        logger.info(f"[{client_id}] Looking for face node: '{FACE_NODE_TITLE}'")
        face_node_id = find_node_id_by_title(wf, FACE_NODE_TITLE, wf_name_log)
        logger.info(f"[{client_id}] Face node result: {face_node_id}")
        
        logger.info(f"[{client_id}] Looking for seed node: '{SEED_NODE_TITLE}'")
        seed_node_id = find_node_id_by_title(wf, SEED_NODE_TITLE, wf_name_log)
        logger.info(f"[{client_id}] Seed node result: {seed_node_id}")
        
        logger.info(f"[{client_id}] Looking for output prefix node: '{OUTPUT_PREFIX_NODE_TITLE}'")
        output_prefix_node_id = find_node_id_by_title(wf, OUTPUT_PREFIX_NODE_TITLE, wf_name_log)
        logger.info(f"[{client_id}] Output prefix node result: {output_prefix_node_id}")
        
        video_start_node_id = None
        if workflow_type == "Video":
             logger.info(f"[{client_id}] Looking for video start node: '{VIDEO_START_IMAGE_NODE_TITLE}'")
             video_start_node_id = find_node_id_by_title(wf, VIDEO_START_IMAGE_NODE_TITLE, wf_name_log)
             logger.info(f"[{client_id}] Video start node result: {video_start_node_id}")
        
        logger.info(f"[{client_id}] Node IDs found: prompt={prompt_node_id}, face={face_node_id}, seed={seed_node_id}, output={output_prefix_node_id}")

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
        logger.info(f"[{client_id}] ComfyUI URL: {COMFYUI_PROMPT_URL}")
        logger.info(f"[{client_id}] Payload size: {len(str(submit_payload))} characters")
        
        logger.info(f"[{client_id}] Sending POST request to ComfyUI...")
        response = requests.post(COMFYUI_PROMPT_URL, json=submit_payload, timeout=COMFYUI_TIMEOUT)
        logger.info(f"[{client_id}] ComfyUI response status: {response.status_code}")
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"[{client_id}] ComfyUI response data: {response_data}")
        
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

# --- API Endpoints ---
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "ComfyUI Music Generation API v5",
        "status": "running",
        "config": {
            "comfyui_url": COMFYUI_BASE_URL,
            "port": 8006,
            "workflows": {
                "image": BASE_WORKFLOW_IMAGE_PATH.name,
                "video": BASE_WORKFLOW_VIDEO_PATH.name
            }
        }
    }

@app.post("/generate/image")
async def generate_image(request: MusicGenerationRequest):
    """Generate image from music segment prompt"""
    client_id = str(uuid.uuid4())
    logger.info(f"[{client_id}] 🎵 Image generation request for segment {request.segment_id}")
    logger.info(f"[{client_id}] Request details: prompt_length={len(request.prompt)}, output_subfolder='{request.output_subfolder}'")
    
    try:
        logger.info(f"[{client_id}] Starting workflow preparation...")
        results = prepare_and_submit_workflow(base_image_workflow, "Image", request, client_id)
        logger.info(f"[{client_id}] Workflow preparation complete. Status: {results['status']}")
        
        if results["status"] == "submitted":
            response_data = {
                "status": "submitted",
                "message": f"Image generation started for segment {request.segment_id}",
                "prompt_id": results["prompt_id"],
                "client_id": client_id,
                "segment_id": request.segment_id
            }
            logger.info(f"[{client_id}] ✅ Returning success response: {response_data}")
            return response_data
        else:
            error_msg = results.get("error", "Unknown workflow error")
            logger.error(f"[{client_id}] ❌ Workflow failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = f"Image generation failed for segment {request.segment_id}: {str(e)}"
        logger.error(f"[{client_id}] ❌ Unexpected error: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/generate/video")
async def generate_video(request: MusicGenerationRequest):
    """Generate video from music segment prompt"""
    client_id = str(uuid.uuid4())
    logger.info(f"[{client_id}] 🎬 Video generation request for segment {request.segment_id}")
    
    try:
        results = prepare_and_submit_workflow(base_video_workflow, "Video", request, client_id)
        
        if results["status"] == "submitted":
            return {
                "status": "submitted",
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

@app.get("/status")
async def get_status():
    """Get API server status and configuration"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "comfyui_api_url": COMFYUI_BASE_URL,
            "port": 8006,
            "workflow_image": BASE_WORKFLOW_IMAGE_PATH.name,
            "workflow_video": BASE_WORKFLOW_VIDEO_PATH.name,
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

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("🎵 Starting Music API Server on port 8006...")
    logger.info("🔍 Debug mode enabled - detailed logging active")
    logger.info("📁 Log file: Check console output for debugging")
    
    # Add file logging for debugging
    import logging
    file_handler = logging.FileHandler('api_server_debug.log', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    
    logger.info("📝 Debug log file created: api_server_debug.log")
    
    uvicorn.run(app, host="127.0.0.1", port=8006, log_level="info")