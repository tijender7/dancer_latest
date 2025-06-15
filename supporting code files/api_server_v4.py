# api_server_v4.py (Handles Start Image Injection)
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

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
console_handler = logging.StreamHandler(sys.stdout) # Log to stdout for visibility
console_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Use INFO, DEBUG for more detail
if logger.hasHandlers(): logger.handlers.clear() # Avoid duplicate handlers
logger.addHandler(console_handler)

# --- Configuration Loading ---
CONFIG_FILE = "config4.json"
try:
    script_dir = Path(__file__).resolve().parent
    config_path_obj = script_dir / CONFIG_FILE
    if not config_path_obj.is_file(): logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
    with open(config_path_obj, "r") as f: config = json.load(f)
    logger.info(f"Config loaded successfully from '{CONFIG_FILE}'.")
except Exception as e: logger.critical(f"CRITICAL: Failed to load config '{CONFIG_FILE}': {e}", exc_info=True); sys.exit(1)

# --- Constants ---
COMFYUI_BASE_URL = config.get("comfyui_api_url", "http://127.0.0.1:8188").rstrip('/') # Store base URL
COMFYUI_PROMPT_URL = f"{COMFYUI_BASE_URL}/prompt" # Construct prompt URL
BASE_WORKFLOW_IMAGE_PATH = (script_dir / config.get("base_workflow_image", "")).resolve()
BASE_WORKFLOW_VIDEO_PATH = (script_dir / config.get("base_workflow_video", "")).resolve()
SOURCE_FACES_PATH_CONFIG = (script_dir / config.get("source_faces_path", "source_faces")).resolve()
SOURCE_FACES_SUBFOLDER_FOR_COMFYUI = SOURCE_FACES_PATH_CONFIG.name

# Expected Node Titles
PROMPT_NODE_TITLE = "API_Prompt_Input"
FACE_NODE_TITLE = "API_Face_Input"
SEED_NODE_TITLE = "API_Seed_Input"
OUTPUT_PREFIX_NODE_TITLE = "API_Output_Prefix"
IMAGE_OUTPUT_SAVE_NODE_TITLE = "API_Image_Output_SaveNode" # For finding image output path
VIDEO_START_IMAGE_NODE_TITLE = "API_Video_Start_Image"   # For injecting start image

COMFYUI_TIMEOUT = 300

# --- Validation ---
if not BASE_WORKFLOW_IMAGE_PATH.is_file(): logger.critical(f"CRITICAL: Image workflow not found: '{BASE_WORKFLOW_IMAGE_PATH}'"); exit(1)
if not BASE_WORKFLOW_VIDEO_PATH.is_file(): logger.critical(f"CRITICAL: Video workflow not found: '{BASE_WORKFLOW_VIDEO_PATH}'"); exit(1)
if not SOURCE_FACES_PATH_CONFIG.is_dir(): logger.warning(f"Source faces dir not found: {SOURCE_FACES_PATH_CONFIG}")

logger.info(f"ComfyUI Prompt URL: {COMFYUI_PROMPT_URL}")
logger.info(f"Image Workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
logger.info(f"Video Workflow: {BASE_WORKFLOW_VIDEO_PATH.name}")
logger.info(f"Source Faces Subfolder (for ComfyUI): {SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}")
logger.info(f"-> Required Titles: '{PROMPT_NODE_TITLE}', '{FACE_NODE_TITLE}', '{SEED_NODE_TITLE}', '{OUTPUT_PREFIX_NODE_TITLE}'")
logger.info(f"-> Required Title (Image WF): '{IMAGE_OUTPUT_SAVE_NODE_TITLE}'")
logger.info(f"-> Required Title (Video WF): '{VIDEO_START_IMAGE_NODE_TITLE}'")


# --- Load Base Workflows ---
try:
    with open(BASE_WORKFLOW_IMAGE_PATH, "r", encoding="utf-8") as f: base_image_workflow = json.load(f)
    with open(BASE_WORKFLOW_VIDEO_PATH, "r", encoding="utf-8") as f: base_video_workflow = json.load(f)
    logger.info("Base workflows loaded successfully.")
except Exception as e: logger.critical(f"CRITICAL: Failed to load workflows: {e}", exc_info=True); exit(1)

# --- Helper Function (Find by Title) ---
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("_meta", {}).get("title") == title:
            logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

# --- FastAPI App ---
app = FastAPI(title="ComfyUI Generation API v4")

# --- Request Model (Added prefix text & start image) ---
class GenerationRequest(BaseModel):
    prompt: str
    face: str | None = None # Face is optional
    output_subfolder: str
    filename_prefix_text: str
    video_start_image_path: str | None = None # Relative path for ComfyUI LoadImage (e.g., temp_starts/...)

# --- Core Workflow Preparation Function ---
def prepare_and_submit_workflow(
    base_workflow: dict,
    workflow_type: str,
    request: GenerationRequest,
    client_id: str
):
    """Prepares and submits a single workflow, randomizing seed and setting inputs."""
    results = {"status": "pending", "error": None, "prompt_id": None, "response": None}
    wf_name_log = f"{workflow_type} Workflow"
    wf = copy.deepcopy(base_workflow) # Start with a fresh copy

    try:
        # --- Find Nodes ---
        logger.info(f"Finding nodes for {wf_name_log}...")
        prompt_node_id = find_node_id_by_title(wf, PROMPT_NODE_TITLE, wf_name_log)
        face_node_id = find_node_id_by_title(wf, FACE_NODE_TITLE, wf_name_log)
        seed_node_id = find_node_id_by_title(wf, SEED_NODE_TITLE, wf_name_log)
        output_prefix_node_id = find_node_id_by_title(wf, OUTPUT_PREFIX_NODE_TITLE, wf_name_log)
        # Find video-specific node only if processing video
        video_start_node_id = None
        if workflow_type == "Video":
             video_start_node_id = find_node_id_by_title(wf, VIDEO_START_IMAGE_NODE_TITLE, wf_name_log)

        # --- Validate Nodes ---
        if not prompt_node_id: raise ValueError(f"Could not find Prompt node '{PROMPT_NODE_TITLE}'.")
        if request.face and not face_node_id: raise ValueError(f"Face provided ('{request.face}') but node '{FACE_NODE_TITLE}' not found.")
        if not seed_node_id: raise ValueError(f"Could not find Seed node '{SEED_NODE_TITLE}'.")
        if not output_prefix_node_id: raise ValueError(f"Could not find Output Prefix node '{OUTPUT_PREFIX_NODE_TITLE}'.")
        # Validate video start image node only if needed
        if workflow_type == "Video" and request.video_start_image_path and not video_start_node_id:
             raise ValueError(f"Video start image provided ('{request.video_start_image_path}') but node '{VIDEO_START_IMAGE_NODE_TITLE}' not found.")

        # --- Modify Inputs ---
        # Prompt
        prompt_input_key = "text"
        if wf[prompt_node_id].get("class_type") == "WanVideoTextEncode": prompt_input_key = "positive_prompt"
        logger.info(f"Injecting prompt into Node {prompt_node_id} (key: {prompt_input_key})")
        wf[prompt_node_id]["inputs"][prompt_input_key] = request.prompt

        # Face
        if face_node_id and request.face:
            face_path_str_for_comfyui = (Path(SOURCE_FACES_SUBFOLDER_FOR_COMFYUI) / request.face).as_posix()
            logger.info(f"Injecting face '{face_path_str_for_comfyui}' into Node {face_node_id}")
            wf[face_node_id]["inputs"]["image"] = face_path_str_for_comfyui
        elif request.face: logger.warning(f"Face '{request.face}' provided but node '{FACE_NODE_TITLE}' not found. Skipping injection.")
        else: logger.info("No face provided. Skipping injection.")

        # Seed
        seed_input_key = "seed"; seed_node_class = wf[seed_node_id].get("class_type")
        if seed_node_class == "RandomNoise": seed_input_key = "noise_seed"
        random_seed = random.randint(0, 2**32 - 1)
        logger.info(f"Injecting random seed {random_seed} into Node {seed_node_id} (key: {seed_input_key})")
        wf[seed_node_id]["inputs"][seed_input_key] = random_seed

        # Video Start Image (only for Video workflow)
        if workflow_type == "Video" and video_start_node_id and request.video_start_image_path:
            start_image_path_str = request.video_start_image_path.replace("\\", "/") # Ensure forward slashes
            logger.info(f"Injecting video start image '{start_image_path_str}' into Node {video_start_node_id}")
            wf[video_start_node_id]["inputs"]["image"] = start_image_path_str
        elif workflow_type == "Video" and request.video_start_image_path:
            logger.warning(f"Video start image provided ('{request.video_start_image_path}') but node '{VIDEO_START_IMAGE_NODE_TITLE}' not found. Using default.")
        elif workflow_type == "Video":
             logger.info("No video start image provided. Using default image from workflow.")


        # Output Path and Prefix
        prefix_node_class = wf[output_prefix_node_id].get("class_type")
        if prefix_node_class == "FileNamePrefix":
            clean_subfolder = request.output_subfolder.replace("\\", "/")
            logger.info(f"Injecting custom_directory '{clean_subfolder}' into Node {output_prefix_node_id}")
            wf[output_prefix_node_id]["inputs"]["custom_directory"] = clean_subfolder
            logger.info(f"Injecting custom_text '{request.filename_prefix_text}' into Node {output_prefix_node_id}")
            wf[output_prefix_node_id]["inputs"]["custom_text"] = request.filename_prefix_text
        else: raise ValueError(f"Output node '{OUTPUT_PREFIX_NODE_TITLE}' is not 'FileNamePrefix'.")

        # --- Submit ---
        payload = {"prompt": wf, "client_id": client_id}
        logger.info(f"Submitting {wf_name_log} workflow to ComfyUI ({COMFYUI_PROMPT_URL})...")
        response = requests.post(COMFYUI_PROMPT_URL, json=payload, timeout=COMFYUI_TIMEOUT)
        response.raise_for_status()
        results["status"] = "submitted"; results["response"] = response.json(); results["prompt_id"] = results["response"].get("prompt_id")
        logger.info(f"✅ {wf_name_log} Job Submitted (Prompt ID: {results['prompt_id']})")

    # Error Handling remains the same
    except requests.exceptions.RequestException as e: results["status"] = "error_connection"; results["error"] = f"Error connecting to ComfyUI: {e}"; logger.error(results["error"])
    except ValueError as e: results["status"] = "error_workflow_prep"; results["error"] = f"Error preparing workflow {wf_name_log}: {e}"; logger.error(results["error"])
    except Exception as e: results["status"] = "error_unknown"; results["error"] = f"Unexpected error during {wf_name_log}: {e}"; logger.error(results["error"], exc_info=True)
    return results

# --- API Endpoints ---
@app.post("/generate_image", summary="Generate Image")
async def generate_image(request: GenerationRequest):
    """Triggers the ComfyUI image workflow."""
    client_id = str(uuid.uuid4())
    logger.info(f"\n--- Received IMAGE request (Client ID: {client_id}) ---")
    logger.info(f"Req Details: Face='{request.face or 'None'}', Output='{request.output_subfolder}', Prefix='{request.filename_prefix_text}'")
    if request.video_start_image_path: logger.warning("`video_start_image_path` provided but ignored for image generation.")

    if request.face:
        path_to_check_existence = SOURCE_FACES_PATH_CONFIG / request.face
        if not path_to_check_existence.is_file(): raise HTTPException(status_code=404, detail=f"Source face file '{request.face}' not found.")
    result = prepare_and_submit_workflow(base_image_workflow, "Image", request, client_id)
    if result["status"] != "submitted": raise HTTPException(status_code=502, detail={"message": "Failed to submit image job", "details": result["error"]})
    return result

@app.post("/generate_video", summary="Generate Video")
async def generate_video(request: GenerationRequest):
    """Triggers the ComfyUI video workflow."""
    client_id = str(uuid.uuid4())
    logger.info(f"\n--- Received VIDEO request (Client ID: {client_id}) ---")
    logger.info(f"Req Details: Face='{request.face or 'None'}', Output='{request.output_subfolder}', Prefix='{request.filename_prefix_text}', StartImg='{request.video_start_image_path or 'Default'}'")

    if request.face:
        path_to_check_existence = SOURCE_FACES_PATH_CONFIG / request.face
        if not path_to_check_existence.is_file(): raise HTTPException(status_code=404, detail=f"Source face file '{request.face}' not found.")
    # No need to validate start image path here - server assumes it exists inside ComfyUI input
    result = prepare_and_submit_workflow(base_video_workflow, "Video", request, client_id)
    if result["status"] != "submitted": raise HTTPException(status_code=502, detail={"message": "Failed to submit video job", "details": result["error"]})
    return result

# --- Server Start ---
if __name__ == "__main__":
    logger.info("\n--- API Server v4 Pre-run Check ---")
    # ... (keep pre-run checks, ensure they mention the new required titles) ...
    logger.info(f"⚠️ Ensure ComfyUI input subfolder exists: ComfyUI_Root/input/{SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}/")
    logger.info(f"⚠️ Ensure nodes in BOTH workflows have correct titles set:")
    logger.info(f"   Prompt Input Node Title : '{PROMPT_NODE_TITLE}'")
    logger.info(f"   Face Input Node Title   : '{FACE_NODE_TITLE}'")
    logger.info(f"   Seed Input Node Title   : '{SEED_NODE_TITLE}'")
    logger.info(f"   Output Prefix Node Title: '{OUTPUT_PREFIX_NODE_TITLE}' (REQUIRED in both workflows)")
    logger.info(f"   Image Output Save Node  : '{IMAGE_OUTPUT_SAVE_NODE_TITLE}' (REQUIRED in Image WF)")
    logger.info(f"   Video Start Image Node  : '{VIDEO_START_IMAGE_NODE_TITLE}' (REQUIRED in Video WF)")
    logger.info("--- Starting API Server v4 ---")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")