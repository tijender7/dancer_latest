# api_server_v5_muscle_mommy.py (Handles Muscle Mommy LoRA Workflow)
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
import time # Added for potential delays if needed

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
console_handler = logging.StreamHandler(sys.stdout) # Log to stdout for visibility
console_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Use INFO, DEBUG for more detail
if logger.hasHandlers(): logger.handlers.clear() # Avoid duplicate handlers
logger.addHandler(console_handler)
logger.info("Initializing Muscle Mommy API Server v5...")

# --- Configuration Loading ---
CONFIG_FILE = "config_muscle_mommy.json" # Uses muscle mommy config
try:
    script_dir = Path(__file__).resolve().parent
    config_path_obj = script_dir / CONFIG_FILE
    if not config_path_obj.is_file(): logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
    with open(config_path_obj, "r", encoding='utf-8') as f: config = json.load(f) # Specify encoding
    logger.info(f"Muscle Mommy config loaded successfully from '{CONFIG_FILE}'.")
except Exception as e: logger.critical(f"CRITICAL: Failed to load config '{CONFIG_FILE}': {e}", exc_info=True); sys.exit(1)

# --- Constants ---
COMFYUI_BASE_URL = config.get("comfyui_api_url", "http://127.0.0.1:8188").rstrip('/') # Store base URL
COMFYUI_PROMPT_URL = f"{COMFYUI_BASE_URL}/prompt" # Construct prompt URL
BASE_WORKFLOW_IMAGE_PATH = (script_dir / config.get("base_workflow_image", "")).resolve()
BASE_WORKFLOW_VIDEO_PATH = (script_dir / config.get("base_workflow_video", "")).resolve()
SOURCE_FACES_PATH_CONFIG = (script_dir / config.get("source_faces_path", "source_faces")).resolve()
SOURCE_FACES_SUBFOLDER_FOR_COMFYUI = SOURCE_FACES_PATH_CONFIG.name # Subfolder name within ComfyUI input

# Expected Node Titles (Ensure these EXACTLY match your workflow files' _meta.title)
PROMPT_NODE_TITLE = "API_Prompt_Input"
FACE_NODE_TITLE = "API_Face_Input"
SEED_NODE_TITLE = "API_Seed_Input"
OUTPUT_PREFIX_NODE_TITLE = "API_Output_Prefix"
IMAGE_OUTPUT_SAVE_NODE_TITLE = "API_Image_Output_SaveNode" # Used by main script, but good to define here too
VIDEO_START_IMAGE_NODE_TITLE = "API_Video_Start_Image"   # For injecting start image

# Muscle Mommy LoRA trigger word
MUSCLE_MOMMY_TRIGGER = "Muscl3-m0mmy"

COMFYUI_TIMEOUT = 300 # Timeout for waiting for ComfyUI response to the /prompt request

# --- Validation ---
if not BASE_WORKFLOW_IMAGE_PATH.is_file(): logger.critical(f"CRITICAL: Image workflow not found: '{BASE_WORKFLOW_IMAGE_PATH}'"); sys.exit(1)
if not BASE_WORKFLOW_VIDEO_PATH.is_file(): logger.critical(f"CRITICAL: Video workflow not found: '{BASE_WORKFLOW_VIDEO_PATH}'"); sys.exit(1)
if not SOURCE_FACES_PATH_CONFIG.is_dir(): logger.warning(f"Source faces dir not found: {SOURCE_FACES_PATH_CONFIG}")

logger.info(f"ComfyUI Prompt URL: {COMFYUI_PROMPT_URL}")
logger.info(f"Muscle Mommy Image Workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
logger.info(f"Video Workflow: {BASE_WORKFLOW_VIDEO_PATH.name}")
logger.info(f"Source Faces Dir (API Server sees): {SOURCE_FACES_PATH_CONFIG}")
logger.info(f"Source Faces Subfolder (for ComfyUI LoadImage node): {SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}")
logger.info(f"Muscle Mommy LoRA Trigger Word: {MUSCLE_MOMMY_TRIGGER}")
logger.info(f"-> Required Node Titles in Workflows:")
logger.info(f"   '{PROMPT_NODE_TITLE}' (Both)")
logger.info(f"   '{FACE_NODE_TITLE}' (Both, if using faces)")
logger.info(f"   '{SEED_NODE_TITLE}' (Both)")
logger.info(f"   '{OUTPUT_PREFIX_NODE_TITLE}' (Both, must be 'FileNamePrefix' class)")
logger.info(f"   '{IMAGE_OUTPUT_SAVE_NODE_TITLE}' (Image WF only)")
logger.info(f"   '{VIDEO_START_IMAGE_NODE_TITLE}' (Video WF only, must be 'LoadImage' class)")


# --- Load Base Workflows ---
try:
    with open(BASE_WORKFLOW_IMAGE_PATH, "r", encoding="utf-8") as f: base_image_workflow = json.load(f)
    with open(BASE_WORKFLOW_VIDEO_PATH, "r", encoding="utf-8") as f: base_video_workflow = json.load(f)
    logger.info("Muscle Mommy base workflows loaded successfully.")
except Exception as e: logger.critical(f"CRITICAL: Failed to load workflows: {e}", exc_info=True); sys.exit(1)

# --- Helper Function (Find by Title) ---
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    """Finds the first node ID in a workflow dict matching the given _meta.title."""
    for node_id, node_data in workflow.items():
        # Check if node_data is a dictionary and has the required keys
        if isinstance(node_data, dict):
             node_meta = node_data.get("_meta", {})
             if isinstance(node_meta, dict) and node_meta.get("title") == title:
                logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
                return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

# --- FastAPI App ---
app = FastAPI(title="Muscle Mommy ComfyUI Generation API v5")

# --- Request Model (Consistent with v4) ---
class GenerationRequest(BaseModel):
    prompt: str
    face: str | None = Field(None, description="Filename of the face image (e.g., 'face1.png') located in the source_faces directory.")
    output_subfolder: str = Field(..., description="Subfolder within ComfyUI output directory to save generated files")
    filename_prefix_text: str = Field(..., description="Text to include in the filename prefix (e.g. '001_swapped')")
    video_start_image_path: str | None = Field(None, description="Path to start image for video generation (relative to ComfyUI input directory)")

# --- Helper Function: Inject Muscle Mommy Trigger ---
def inject_muscle_mommy_trigger(prompt: str) -> str:
    """Ensures the Muscle Mommy trigger word is present in the prompt."""
    if MUSCLE_MOMMY_TRIGGER not in prompt:
        # Add trigger word at the beginning
        return f"{MUSCLE_MOMMY_TRIGGER}, {prompt}"
    return prompt

# --- Core Function: Generate Workflow (Enhanced for Muscle Mommy) ---
def prepare_workflow(
    prompt: str, 
    face: str | None, 
    output_subfolder: str, 
    filename_prefix_text: str, 
    is_video: bool = False, 
    video_start_image_path: str | None = None
) -> dict:
    """
    Prepares a workflow JSON with the given parameters for Muscle Mommy generation.
    
    Args:
        prompt: Text prompt for generation
        face: Filename of face image (not used in muscle mommy - no face swap)
        output_subfolder: Subfolder within ComfyUI output directory
        filename_prefix_text: Text for filename prefix
        is_video: Whether this is for video generation
        video_start_image_path: Path to start image for video (if applicable)
    
    Returns:
        dict: Prepared workflow JSON
    """
    # Choose the appropriate base workflow
    if is_video:
        workflow = copy.deepcopy(base_video_workflow)
        workflow_name = f"Video ({BASE_WORKFLOW_VIDEO_PATH.name})"
    else:
        workflow = copy.deepcopy(base_image_workflow)
        workflow_name = f"Image ({BASE_WORKFLOW_IMAGE_PATH.name})"
    
    logger.info(f"Preparing {workflow_name} workflow for Muscle Mommy generation...")
    
    # Inject Muscle Mommy trigger word into prompt
    enhanced_prompt = inject_muscle_mommy_trigger(prompt)
    if enhanced_prompt != prompt:
        logger.info(f"Enhanced prompt with trigger word: {MUSCLE_MOMMY_TRIGGER}")
    
    # Find required nodes
    prompt_node_id = find_node_id_by_title(workflow, PROMPT_NODE_TITLE, workflow_name)
    seed_node_id = find_node_id_by_title(workflow, SEED_NODE_TITLE, workflow_name)
    output_prefix_node_id = find_node_id_by_title(workflow, OUTPUT_PREFIX_NODE_TITLE, workflow_name)
    
    # Check if required nodes exist
    if not prompt_node_id:
        raise ValueError(f"'{PROMPT_NODE_TITLE}' node not found in {workflow_name}")
    if not seed_node_id:
        raise ValueError(f"'{SEED_NODE_TITLE}' node not found in {workflow_name}")
    if not output_prefix_node_id:
        raise ValueError(f"'{OUTPUT_PREFIX_NODE_TITLE}' node not found in {workflow_name}")
    
    # 1. Set prompt (with Muscle Mommy trigger)
    workflow[prompt_node_id]["inputs"]["text"] = enhanced_prompt
    logger.debug(f"Set prompt in node {prompt_node_id}: '{enhanced_prompt[:50]}...'")
    
    # 2. Set random seed
    random_seed = random.randint(1, 1000000000)
    workflow[seed_node_id]["inputs"]["noise_seed"] = random_seed
    logger.debug(f"Set random seed in node {seed_node_id}: {random_seed}")
    
    # 3. Set output prefix with subfolder
    workflow[output_prefix_node_id]["inputs"]["custom_directory"] = output_subfolder
    workflow[output_prefix_node_id]["inputs"]["custom_text"] = filename_prefix_text
    logger.debug(f"Set output prefix in node {output_prefix_node_id}: subfolder='{output_subfolder}', prefix='{filename_prefix_text}'")
    
    # 4. Handle video-specific start image injection
    if is_video and video_start_image_path:
        video_start_node_id = find_node_id_by_title(workflow, VIDEO_START_IMAGE_NODE_TITLE, workflow_name)
        if video_start_node_id:
            workflow[video_start_node_id]["inputs"]["image"] = video_start_image_path
            logger.debug(f"Set video start image in node {video_start_node_id}: '{video_start_image_path}'")
        else:
            logger.warning(f"'{VIDEO_START_IMAGE_NODE_TITLE}' node not found in {workflow_name} - video start image injection skipped")
    
    # Note: Face swap is skipped entirely for muscle mommy automation
    
    logger.info(f"Muscle Mommy workflow prepared successfully: {workflow_name}")
    return workflow

# --- Core Function: Submit to ComfyUI ---
def submit_to_comfyui(workflow: dict) -> str:
    """
    Submits a workflow to ComfyUI and returns the prompt ID.
    
    Args:
        workflow: Prepared workflow dictionary
        
    Returns:
        str: ComfyUI prompt ID
        
    Raises:
        HTTPException: If submission fails
    """
    payload = {"prompt": workflow}
    logger.debug(f"Submitting to ComfyUI: {COMFYUI_PROMPT_URL}")
    
    try:
        response = requests.post(COMFYUI_PROMPT_URL, json=payload, timeout=COMFYUI_TIMEOUT)
        response.raise_for_status()
        response_data = response.json()
        
        prompt_id = response_data.get("prompt_id")
        if not prompt_id:
            error_detail = response_data.get("error", "Unknown error")
            logger.error(f"ComfyUI submission failed: {error_detail}")
            raise HTTPException(status_code=500, detail=f"ComfyUI submission failed: {error_detail}")
        
        logger.info(f"Successfully submitted to ComfyUI. Prompt ID: {prompt_id}")
        return prompt_id
        
    except requests.exceptions.Timeout:
        logger.error(f"ComfyUI request timed out after {COMFYUI_TIMEOUT} seconds")
        raise HTTPException(status_code=504, detail="ComfyUI request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with ComfyUI: {e}")
        raise HTTPException(status_code=500, detail=f"Error communicating with ComfyUI: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during ComfyUI submission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

# --- API Endpoints ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Muscle Mommy API Server v5 is running",
        "trigger_word": MUSCLE_MOMMY_TRIGGER,
        "image_workflow": BASE_WORKFLOW_IMAGE_PATH.name,
        "video_workflow": BASE_WORKFLOW_VIDEO_PATH.name,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/generate_image")
async def generate_image(request: GenerationRequest):
    """
    Generate images using the Muscle Mommy workflow.
    
    The prompt will automatically have the Muscle Mommy trigger word added if not present.
    Face swap is not supported in this automation.
    """
    logger.info(f"Received image generation request")
    logger.info(f"  Prompt: '{request.prompt[:100]}...'")
    logger.info(f"  Output Subfolder: '{request.output_subfolder}'")
    logger.info(f"  Filename Prefix: '{request.filename_prefix_text}'")
    logger.info(f"  Face: '{request.face}' (ignored - no face swap in muscle mommy)")
    
    try:
        # Prepare workflow for image generation
        workflow = prepare_workflow(
            prompt=request.prompt,
            face=request.face,  # Ignored but passed for consistency
            output_subfolder=request.output_subfolder,
            filename_prefix_text=request.filename_prefix_text,
            is_video=False
        )
        
        # Submit to ComfyUI
        prompt_id = submit_to_comfyui(workflow)
        
        return {
            "status": "submitted",
            "prompt_id": prompt_id,
            "trigger_word_used": MUSCLE_MOMMY_TRIGGER,
            "enhanced_prompt": inject_muscle_mommy_trigger(request.prompt),
            "message": "Muscle Mommy image generation submitted to ComfyUI"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in image generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/generate_video")
async def generate_video(request: GenerationRequest):
    """
    Generate videos using the existing video workflow with Muscle Mommy trigger word.
    
    The prompt will automatically have the Muscle Mommy trigger word added if not present.
    Face swap is not supported in this automation.
    """
    logger.info(f"Received video generation request")
    logger.info(f"  Prompt: '{request.prompt[:100]}...'")
    logger.info(f"  Output Subfolder: '{request.output_subfolder}'")
    logger.info(f"  Filename Prefix: '{request.filename_prefix_text}'")
    logger.info(f"  Video Start Image: '{request.video_start_image_path}'")
    logger.info(f"  Face: '{request.face}' (ignored - no face swap in muscle mommy)")
    
    try:
        # Prepare workflow for video generation
        workflow = prepare_workflow(
            prompt=request.prompt,
            face=request.face,  # Ignored but passed for consistency
            output_subfolder=request.output_subfolder,
            filename_prefix_text=request.filename_prefix_text,
            is_video=True,
            video_start_image_path=request.video_start_image_path
        )
        
        # Submit to ComfyUI
        prompt_id = submit_to_comfyui(workflow)
        
        return {
            "status": "submitted",
            "prompt_id": prompt_id,
            "trigger_word_used": MUSCLE_MOMMY_TRIGGER,
            "enhanced_prompt": inject_muscle_mommy_trigger(request.prompt),
            "video_start_image": request.video_start_image_path,
            "message": "Muscle Mommy video generation submitted to ComfyUI"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in video generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

# --- Server Startup ---
if __name__ == "__main__":
    logger.info("Starting Muscle Mommy API Server v5...")
    logger.info(f"Trigger word: {MUSCLE_MOMMY_TRIGGER}")
    logger.info(f"Image workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
    logger.info(f"Video workflow: {BASE_WORKFLOW_VIDEO_PATH.name}")
    logger.info("Server will run on http://0.0.0.0:8001")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)