# api_server_v5.py (Handles Start Image Injection)
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
logger.info("Initializing API Server v5...")

# --- Configuration Loading ---
CONFIG_FILE = "config_with_faceswap.json" # Still uses the same config file
try:
    script_dir = Path(__file__).resolve().parent
    config_path_obj = script_dir / CONFIG_FILE
    if not config_path_obj.is_file(): logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
    with open(config_path_obj, "r", encoding='utf-8') as f: config = json.load(f) # Specify encoding
    logger.info(f"Config loaded successfully from '{CONFIG_FILE}'.")
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

COMFYUI_TIMEOUT = 300 # Timeout for waiting for ComfyUI response to the /prompt request

# --- Validation ---
if not BASE_WORKFLOW_IMAGE_PATH.is_file(): logger.critical(f"CRITICAL: Image workflow not found: '{BASE_WORKFLOW_IMAGE_PATH}'"); sys.exit(1)
if not BASE_WORKFLOW_VIDEO_PATH.is_file(): logger.critical(f"CRITICAL: Video workflow not found: '{BASE_WORKFLOW_VIDEO_PATH}'"); sys.exit(1)
if not SOURCE_FACES_PATH_CONFIG.is_dir(): logger.warning(f"Source faces dir not found: {SOURCE_FACES_PATH_CONFIG}")

logger.info(f"ComfyUI Prompt URL: {COMFYUI_PROMPT_URL}")
logger.info(f"Image Workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
logger.info(f"Video Workflow: {BASE_WORKFLOW_VIDEO_PATH.name}")
logger.info(f"Source Faces Dir (API Server sees): {SOURCE_FACES_PATH_CONFIG}")
logger.info(f"Source Faces Subfolder (for ComfyUI LoadImage node): {SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}")
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
    logger.info("Base workflows loaded successfully.")
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
app = FastAPI(title="ComfyUI Generation API v5")

# --- Request Model (Consistent with v4) ---
class GenerationRequest(BaseModel):
    prompt: str
    face: str | None = Field(None, description="Filename of the face image (e.g., 'face1.png') located in the source_faces directory.")
    output_subfolder: str = Field(..., description="Relative path within ComfyUI's output directory (e.g., 'Run_20231028_120000/all_images').")
    filename_prefix_text: str = Field(..., description="Prefix for the output filename (e.g., '001_swapped').")
    video_start_image_path: str | None = Field(None, description="Relative path for ComfyUI LoadImage node, inside ComfyUI's input dir (e.g., 'temp_video_starts/start_001.png').")

# --- Core Workflow Preparation Function ---
def prepare_and_submit_workflow(
    base_workflow: dict,
    workflow_type: str, # "Image" or "Video"
    request: GenerationRequest,
    client_id: str
):
    """Prepares a workflow by injecting inputs and submits it to ComfyUI."""
    results = {"status": "pending", "error": None, "prompt_id": None, "response": None}
    wf_name_log = f"{workflow_type} Workflow"
    wf = copy.deepcopy(base_workflow) # Deep copy to avoid modifying the original loaded workflow

    try:
        # --- Find Nodes ---
        logger.info(f"[{client_id}] Finding nodes for {wf_name_log}...")
        prompt_node_id = find_node_id_by_title(wf, PROMPT_NODE_TITLE, wf_name_log)
        face_node_id = find_node_id_by_title(wf, FACE_NODE_TITLE, wf_name_log) # May be None if not used/found
        seed_node_id = find_node_id_by_title(wf, SEED_NODE_TITLE, wf_name_log)
        output_prefix_node_id = find_node_id_by_title(wf, OUTPUT_PREFIX_NODE_TITLE, wf_name_log)
        video_start_node_id = None
        if workflow_type == "Video":
             video_start_node_id = find_node_id_by_title(wf, VIDEO_START_IMAGE_NODE_TITLE, wf_name_log)

        # --- Validate Nodes ---
        if not prompt_node_id: raise ValueError(f"Could not find Prompt node '{PROMPT_NODE_TITLE}'.")
        # Face node is optional in the workflow, but required if a face is provided in request
        if request.face and not face_node_id:
            logger.warning(f"Face provided ('{request.face}') but node '{FACE_NODE_TITLE}' not found in {wf_name_log}. Face swapping may not occur.")
            # Decide if this should be a hard error: raise ValueError(f"Face provided ('{request.face}') but node '{FACE_NODE_TITLE}' not found.")
        if not seed_node_id: raise ValueError(f"Could not find Seed node '{SEED_NODE_TITLE}'.")
        if not output_prefix_node_id: raise ValueError(f"Could not find Output Prefix node '{OUTPUT_PREFIX_NODE_TITLE}'.")
        # Validate video start image node only if needed and provided
        if workflow_type == "Video" and request.video_start_image_path and not video_start_node_id:
             raise ValueError(f"Video start image provided ('{request.video_start_image_path}') but LoadImage node '{VIDEO_START_IMAGE_NODE_TITLE}' not found.")

        # --- Modify Inputs ---
        # Prompt
        if prompt_node_id:
            prompt_input_key = "text" # Default for standard ClipTextEncode
            node_class = wf[prompt_node_id].get("class_type")
            # Add specific class types if your prompt node is different
            if node_class == "CLIPTextEncode (Prompt Simplified)": prompt_input_key = "text"
            elif node_class == "WanVideoTextEncode": prompt_input_key = "positive_prompt"
            # Add more conditions if needed
            logger.info(f"[{client_id}] Injecting prompt into Node {prompt_node_id} ('{node_class}', key: '{prompt_input_key}')")
            wf[prompt_node_id]["inputs"][prompt_input_key] = request.prompt
        else:
             # This case was already checked, but defensive coding
             logger.error(f"[{client_id}] Prompt node '{PROMPT_NODE_TITLE}' ID not found after check, skipping injection.")


        # Face (LoadImage node)
        if face_node_id and request.face:
            # Construct the path *relative* to ComfyUI's input directory
            face_path_str_for_comfyui = (Path(SOURCE_FACES_SUBFOLDER_FOR_COMFYUI) / request.face).as_posix() # Use forward slashes
            logger.info(f"[{client_id}] Injecting face path '{face_path_str_for_comfyui}' into Node {face_node_id} (LoadImage)")
            wf[face_node_id]["inputs"]["image"] = face_path_str_for_comfyui
        elif request.face:
             # Warning already logged if node not found
             pass
        else:
             logger.info(f"[{client_id}] No face provided in request. Skipping face injection.")
             # Optional: Ensure the face input is cleared if no face is given?
             # if face_node_id and wf[face_node_id]["inputs"].get("image"):
             #     wf[face_node_id]["inputs"]["image"] = "" # Or handle default/empty state

        # Seed
        if seed_node_id:
            seed_input_key = "seed" # Default for KSampler etc.
            seed_node_class = wf[seed_node_id].get("class_type")
            # Add specific class types if your seed node is different
            if seed_node_class == "RandomNoise": seed_input_key = "noise_seed"
            elif seed_node_class == "SetNodeSeed": seed_input_key = "seed"
            elif seed_node_class == "Seed": seed_input_key = "seed"
            # Add more conditions as needed
            random_seed = random.randint(0, 2**32 - 1)
            logger.info(f"[{client_id}] Injecting random seed {random_seed} into Node {seed_node_id} ('{seed_node_class}', key: '{seed_input_key}')")
            wf[seed_node_id]["inputs"][seed_input_key] = random_seed
        else:
             logger.error(f"[{client_id}] Seed node '{SEED_NODE_TITLE}' ID not found after check, skipping injection.")


        # Video Start Image (LoadImage node)
        if workflow_type == "Video" and video_start_node_id and request.video_start_image_path:
            # Path provided should already be relative to ComfyUI input folder
            start_image_path_str = request.video_start_image_path.replace("\\", "/") # Ensure forward slashes
            logger.info(f"[{client_id}] Injecting video start image path '{start_image_path_str}' into Node {video_start_node_id} (LoadImage)")
            wf[video_start_node_id]["inputs"]["image"] = start_image_path_str
        elif workflow_type == "Video" and request.video_start_image_path:
             # Error already raised if node not found
              pass
        elif workflow_type == "Video":
             logger.info(f"[{client_id}] No video start image provided in request. Using default image defined in workflow.")


        # Output Path and Prefix (using FileNamePrefix node)
        if output_prefix_node_id:
            prefix_node_class = wf[output_prefix_node_id].get("class_type")
            if prefix_node_class == "FileNamePrefix":
                # ComfyUI expects forward slashes for paths
                clean_subfolder = request.output_subfolder.replace("\\", "/")
                logger.info(f"[{client_id}] Injecting custom_directory '{clean_subfolder}' into Node {output_prefix_node_id}")
                wf[output_prefix_node_id]["inputs"]["custom_directory"] = clean_subfolder
                logger.info(f"[{client_id}] Injecting custom_text '{request.filename_prefix_text}' into Node {output_prefix_node_id}")
                wf[output_prefix_node_id]["inputs"]["custom_text"] = request.filename_prefix_text
            else:
                # If your output node isn't FileNamePrefix, adapt this logic
                raise ValueError(f"Output node '{OUTPUT_PREFIX_NODE_TITLE}' (ID: {output_prefix_node_id}) is not 'FileNamePrefix' class type (it's '{prefix_node_class}'). Cannot set output path/prefix.")
        else:
             logger.error(f"[{client_id}] Output Prefix node '{OUTPUT_PREFIX_NODE_TITLE}' ID not found after check, skipping injection.")


        # --- Submit ---
        payload = {"prompt": wf, "client_id": client_id}
        logger.info(f"[{client_id}] Submitting {wf_name_log} workflow to ComfyUI ({COMFYUI_PROMPT_URL})...")
        logger.debug(f"[{client_id}] Payload (prompt section size: {len(json.dumps(wf))} bytes): {json.dumps(payload, indent=2)}")

        response = requests.post(COMFYUI_PROMPT_URL, json=payload, timeout=COMFYUI_TIMEOUT)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        results["status"] = "submitted"
        results["response"] = response.json()
        results["prompt_id"] = results["response"].get("prompt_id")
        logger.info(f"✅ [{client_id}] {wf_name_log} Job Submitted (HTTP {response.status_code}, Prompt ID: {results['prompt_id']})")

    except requests.exceptions.Timeout:
        results["status"] = "error_timeout"
        results["error"] = f"Error submitting to ComfyUI: Request timed out after {COMFYUI_TIMEOUT} seconds."
        logger.error(f"❌ [{client_id}] {results['error']}")
    except requests.exceptions.RequestException as e:
        results["status"] = "error_connection"
        results["error"] = f"Error connecting to ComfyUI: {e}"
        logger.error(f"❌ [{client_id}] {results['error']}")
        # Log response if available
        if e.response is not None:
            logger.error(f"   Response Status Code: {e.response.status_code}")
            try: logger.error(f"   Response Body: {e.response.text[:1000]}...") # Log first 1k chars
            except Exception: logger.error("   Response body could not be read.")
    except ValueError as e: # Catch workflow preparation errors (missing nodes etc.)
        results["status"] = "error_workflow_prep"
        results["error"] = f"Error preparing workflow {wf_name_log}: {e}"
        logger.error(f"❌ [{client_id}] {results['error']}")
    except Exception as e:
        results["status"] = "error_unknown"
        results["error"] = f"Unexpected error during {wf_name_log}: {e}"
        logger.error(f"❌ [{client_id}] {results['error']}", exc_info=True)

    return results

# --- API Endpoints ---
@app.post("/generate_image", summary="Generate Image")
async def generate_image(request: GenerationRequest):
    """
    Triggers the ComfyUI image workflow.
    Requires prompt, output_subfolder, filename_prefix_text.
    Optional: face (filename).
    Ignores video_start_image_path.
    """
    client_id = str(uuid.uuid4())
    logger.info(f"\n--- [{client_id}] Received IMAGE request ---")
    logger.info(f"[{client_id}] Prompt: '{request.prompt[:80]}...'")
    logger.info(f"[{client_id}] Face: '{request.face or 'None'}'")
    logger.info(f"[{client_id}] Output Subfolder: '{request.output_subfolder}'")
    logger.info(f"[{client_id}] Filename Prefix: '{request.filename_prefix_text}'")
    if request.video_start_image_path:
        logger.warning(f"[{client_id}] `video_start_image_path` provided but will be ignored for image generation.")

    # Check if face file exists locally *before* submitting to ComfyUI
    if request.face:
        path_to_check_existence = SOURCE_FACES_PATH_CONFIG / request.face
        if not path_to_check_existence.is_file():
             logger.error(f"[{client_id}] Source face file not found at: {path_to_check_existence}")
             raise HTTPException(status_code=404, detail=f"Source face file '{request.face}' not found on API server in '{SOURCE_FACES_PATH_CONFIG}'.")
        else:
             logger.info(f"[{client_id}] Source face file '{request.face}' confirmed exists locally.")

    result = prepare_and_submit_workflow(base_image_workflow, "Image", request, client_id)

    if result["status"] != "submitted":
        # Log the error that occurred within prepare_and_submit_workflow
        logger.error(f"[{client_id}] Failed to submit image job. Status: {result['status']}, Error: {result['error']}")
        # Return a 502 Bad Gateway, indicating this server failed to get a valid response from upstream (ComfyUI)
        raise HTTPException(status_code=502, detail={"message": "Failed to submit image job to ComfyUI", "details": result["error"], "status": result["status"]})

    return result

@app.post("/generate_video", summary="Generate Video")
async def generate_video(request: GenerationRequest):
    """
    Triggers the ComfyUI video workflow.
    Requires prompt, output_subfolder, filename_prefix_text.
    Optional: face (filename), video_start_image_path (relative path in ComfyUI input).
    """
    client_id = str(uuid.uuid4())
    logger.info(f"\n--- [{client_id}] Received VIDEO request ---")
    logger.info(f"[{client_id}] Prompt: '{request.prompt[:80]}...'")
    logger.info(f"[{client_id}] Face: '{request.face or 'None'}'")
    logger.info(f"[{client_id}] Output Subfolder: '{request.output_subfolder}'")
    logger.info(f"[{client_id}] Filename Prefix: '{request.filename_prefix_text}'")
    logger.info(f"[{client_id}] Video Start Image: '{request.video_start_image_path or 'Default (from workflow)'}'")

    # Check face file existence
    if request.face:
        path_to_check_existence = SOURCE_FACES_PATH_CONFIG / request.face
        if not path_to_check_existence.is_file():
             logger.error(f"[{client_id}] Source face file not found at: {path_to_check_existence}")
             raise HTTPException(status_code=404, detail=f"Source face file '{request.face}' not found on API server in '{SOURCE_FACES_PATH_CONFIG}'.")
        else:
             logger.info(f"[{client_id}] Source face file '{request.face}' confirmed exists locally.")

    # Note: We don't validate video_start_image_path existence here.
    # The API server trusts the main script placed it correctly inside ComfyUI's input folder.

    result = prepare_and_submit_workflow(base_video_workflow, "Video", request, client_id)

    if result["status"] != "submitted":
        logger.error(f"[{client_id}] Failed to submit video job. Status: {result['status']}, Error: {result['error']}")
        raise HTTPException(status_code=502, detail={"message": "Failed to submit video job to ComfyUI", "details": result["error"], "status": result["status"]})

    return result

# --- Server Start ---
if __name__ == "__main__":
    logger.info("\n" + "="*40)
    logger.info("--- API Server v5 Pre-run Check ---")
    logger.info(f"Using Config: {config_path_obj}")
    logger.info(f"ComfyUI API URL: {COMFYUI_BASE_URL}")
    logger.info(f"Image Workflow File: {BASE_WORKFLOW_IMAGE_PATH.name}")
    logger.info(f"Video Workflow File: {BASE_WORKFLOW_VIDEO_PATH.name}")
    logger.info(f"Source Faces Directory: {SOURCE_FACES_PATH_CONFIG}")
    logger.info(f"ComfyUI Face Subfolder Name: '{SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}'")
    logger.info(f"--- Required Node Titles ---")
    logger.info(f"   - '{PROMPT_NODE_TITLE}' (Both Workflows)")
    logger.info(f"   - '{FACE_NODE_TITLE}' (Both, if using faces)")
    logger.info(f"   - '{SEED_NODE_TITLE}' (Both)")
    logger.info(f"   - '{OUTPUT_PREFIX_NODE_TITLE}' (Both, class: FileNamePrefix)")
    logger.info(f"   - '{IMAGE_OUTPUT_SAVE_NODE_TITLE}' (Image Workflow, any SaveImage/SaveWebp node)")
    logger.info(f"   - '{VIDEO_START_IMAGE_NODE_TITLE}' (Video Workflow, class: LoadImage)")
    logger.info("--- Verifications ---")
    logger.info(f"   - Image Workflow Exists: {'OK' if BASE_WORKFLOW_IMAGE_PATH.is_file() else 'FAIL'}")
    logger.info(f"   - Video Workflow Exists: {'OK' if BASE_WORKFLOW_VIDEO_PATH.is_file() else 'FAIL'}")
    logger.info(f"   - Source Faces Dir Exists: {'OK' if SOURCE_FACES_PATH_CONFIG.is_dir() else 'WARNING (Not Found)'}")
    logger.info(f"⚠️ Ensure ComfyUI input subfolder exists for faces: ComfyUI_Root/input/{SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}/")
    logger.info("="*40 + "\n")

    if not BASE_WORKFLOW_IMAGE_PATH.is_file() or not BASE_WORKFLOW_VIDEO_PATH.is_file():
        logger.critical("CRITICAL: One or both base workflow files not found. Exiting.")
        sys.exit(1)

    logger.info("--- Starting FastAPI Server (v5) ---")
    # Recommended: Use host="0.0.0.0" to be accessible on the network
    # Use port 8000 as defined in the main script's config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")