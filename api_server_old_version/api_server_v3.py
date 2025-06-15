# api_server_v3.py
import os
import json
import requests
import uuid
import copy
import random
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import logging

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    logger.addHandler(console_handler)

# --- Configuration Loading ---
CONFIG_FILE = "config3.json" # Ensure this points to your active config
try:
    script_dir = Path(__file__).resolve().parent
    config_path_obj = script_dir / CONFIG_FILE
    if not config_path_obj.is_file():
        logger.critical(f"CRITICAL: Config file not found: {config_path_obj}")
        exit(1)
    with open(config_path_obj, "r") as f: config = json.load(f)
    logger.info(f"Config loaded successfully from '{CONFIG_FILE}'.")
except Exception as e: logger.critical(f"CRITICAL: Failed to load config '{CONFIG_FILE}': {e}", exc_info=True); exit(1)

# --- Constants ---
COMFYUI_API_URL = config.get("comfyui_api_url", "http://127.0.0.1:8188/prompt")
BASE_WORKFLOW_IMAGE_PATH = (script_dir / config.get("base_workflow_image", "")).resolve()
SOURCE_FACES_PATH_CONFIG = (script_dir / config.get("source_faces_path", "source_faces")).resolve()
SOURCE_FACES_SUBFOLDER_FOR_COMFYUI = SOURCE_FACES_PATH_CONFIG.name

PROMPT_NODE_TITLE = "API_Prompt_Input"
FACE_NODE_TITLE = "API_Face_Input"
SEED_NODE_TITLE = "API_Seed_Input"
OUTPUT_PREFIX_NODE_TITLE = "API_Output_Prefix"

COMFYUI_TIMEOUT = 300

# --- Validation ---
if not BASE_WORKFLOW_IMAGE_PATH.is_file(): logger.critical(f"CRITICAL: Image workflow not found: '{BASE_WORKFLOW_IMAGE_PATH}'"); exit(1)
if not SOURCE_FACES_PATH_CONFIG.is_dir(): logger.warning(f"Source faces dir (for checking existence) not found: {SOURCE_FACES_PATH_CONFIG}")

logger.info(f"ComfyUI API URL: {COMFYUI_API_URL}")
logger.info(f"Image Workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
logger.info(f"Source Faces Subfolder (for ComfyUI): {SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}")
logger.info(f"Expected Prompt Node Title: '{PROMPT_NODE_TITLE}'")
logger.info(f"Expected Face Node Title: '{FACE_NODE_TITLE}'")
logger.info(f"Expected Seed Node Title: '{SEED_NODE_TITLE}'")
logger.info(f"Expected Output Prefix Node Title: '{OUTPUT_PREFIX_NODE_TITLE}'")

# --- Load Base Workflow ---
try:
    with open(BASE_WORKFLOW_IMAGE_PATH, "r", encoding="utf-8") as f:
        base_image_workflow = json.load(f)
    logger.info("Base image workflow loaded successfully.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to load Image Workflow: {e}", exc_info=True)
    exit(1)

# --- Helper Function (Find by Title) ---
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("_meta", {}).get("title") == title:
            logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

# --- FastAPI App ---
app = FastAPI(title="ComfyUI Image Generation API v3")

# --- Request Model ---
class GenerationRequest(BaseModel):
    prompt: str
    face: str
    output_subfolder: str | None = None

# --- Core Workflow Preparation Function ---
def prepare_and_submit_image_workflow(
    request: GenerationRequest,
    client_id: str
):
    """Prepares and submits the image workflow."""
    results = {"status": "pending", "error": None, "prompt_id": None, "response": None}
    WORKFLOW_NAME = "Image"

    try:
        wf = copy.deepcopy(base_image_workflow)

        # --- Find Nodes ---
        logger.info(f"Finding nodes for {WORKFLOW_NAME}...")
        prompt_node_id = find_node_id_by_title(wf, PROMPT_NODE_TITLE, WORKFLOW_NAME)
        face_node_id = find_node_id_by_title(wf, FACE_NODE_TITLE, WORKFLOW_NAME)
        seed_node_id = find_node_id_by_title(wf, SEED_NODE_TITLE, WORKFLOW_NAME)
        output_prefix_node_id = find_node_id_by_title(wf, OUTPUT_PREFIX_NODE_TITLE, WORKFLOW_NAME)

        # --- Validate Nodes ---
        if not prompt_node_id: raise ValueError(f"Could not find Prompt node '{PROMPT_NODE_TITLE}'.")
        # Face node is only required if a face filename was actually sent in the request
        if request.face and not face_node_id: raise ValueError(f"Face filename provided ('{request.face}') but could not find Face node '{FACE_NODE_TITLE}'.")
        if not face_node_id and request.face: logger.warning("Face provided but no face node found/titled. Skipping face injection.")
        if not seed_node_id: raise ValueError(f"Could not find Seed node '{SEED_NODE_TITLE}'.")
        if request.output_subfolder and not output_prefix_node_id: logger.warning(f"output_subfolder provided but node '{OUTPUT_PREFIX_NODE_TITLE}' not found.")

        # --- Modify Inputs ---
        # Prompt
        prompt_input_key = "text"
        logger.info(f"Injecting prompt into Node {prompt_node_id} (key: {prompt_input_key})")
        wf[prompt_node_id]["inputs"][prompt_input_key] = request.prompt

        # Face (Only if node found and face provided)
        if face_node_id and request.face:
            face_path_str_for_comfyui = (Path(SOURCE_FACES_SUBFOLDER_FOR_COMFYUI) / request.face).as_posix()
            logger.info(f"Injecting face '{face_path_str_for_comfyui}' into Node {face_node_id}")
            wf[face_node_id]["inputs"]["image"] = face_path_str_for_comfyui
        elif not request.face:
             logger.info("No face filename provided in request, skipping face injection.")

        # Seed
        seed_input_key = "noise_seed"
        seed_node_class = wf[seed_node_id].get("class_type")
        if seed_node_class not in ["RandomNoise"]:
             logger.warning(f"Seed node {seed_node_id} has unexpected class '{seed_node_class}'. Assuming input key is '{seed_input_key}'.")
        random_seed = random.randint(0, 2**32 - 1)
        logger.info(f"Injecting random seed {random_seed} into Node {seed_node_id} (key: {seed_input_key})")
        wf[seed_node_id]["inputs"][seed_input_key] = random_seed

        # Output Subfolder
        if output_prefix_node_id and request.output_subfolder:
            prefix_node_class = wf[output_prefix_node_id].get("class_type")
            if prefix_node_class == "FileNamePrefix":
                 clean_subfolder = request.output_subfolder.replace("\\", "/")
                 logger.info(f"Injecting custom_directory '{clean_subfolder}' into Node {output_prefix_node_id}")
                 wf[output_prefix_node_id]["inputs"]["custom_directory"] = clean_subfolder
                 prefix_text = "swapped" if face_node_id and request.face else "raw"
                 wf[output_prefix_node_id]["inputs"]["custom_text"] = prefix_text
                 logger.info(f"Setting custom_text to '{prefix_text}' in Node {output_prefix_node_id}")
            else: logger.warning(f"Node '{OUTPUT_PREFIX_NODE_TITLE}' is not 'FileNamePrefix'. Cannot set output path.")

        # --- Submit ---
        payload = {"prompt": wf, "client_id": client_id}
        logger.info(f"Submitting {WORKFLOW_NAME} workflow to ComfyUI...")
        response = requests.post(COMFYUI_API_URL, json=payload, timeout=COMFYUI_TIMEOUT)
        response.raise_for_status()
        results["status"] = "submitted"; results["response"] = response.json(); results["prompt_id"] = results["response"].get("prompt_id")
        logger.info(f"✅ {WORKFLOW_NAME} Job Submitted (Prompt ID: {results['prompt_id']})")

    except requests.exceptions.RequestException as e: results["status"] = "error_connection"; results["error"] = f"Error connecting to ComfyUI: {e}"; logger.error(results["error"])
    except ValueError as e: results["status"] = "error_workflow_prep"; results["error"] = f"Error preparing workflow {WORKFLOW_NAME}: {e}"; logger.error(results["error"])
    except Exception as e: results["status"] = "error_unknown"; results["error"] = f"Unexpected error during {WORKFLOW_NAME}: {e}"; logger.error(results["error"], exc_info=True)
    return results

# --- API Endpoint ---
@app.post("/generate_image", summary="Generate Image Only")
async def generate_image(request: GenerationRequest):
    """Triggers the ComfyUI image workflow."""
    client_id = str(uuid.uuid4())
    logger.info(f"\n--- Received IMAGE request (Client ID: {client_id}) ---")
    logger.info(f"Prompt: '{request.prompt[:70]}...' | Face: '{request.face or 'None'}' | Subfolder: '{request.output_subfolder or 'Default'}'")

    # --- Validate Face File Existence (Only if a face was provided) ---
    if request.face:
        path_to_check_existence = SOURCE_FACES_PATH_CONFIG / request.face
        if not path_to_check_existence.is_file():
            raise HTTPException(status_code=404, detail=f"Source face file '{request.face}' provided but not found at expected script path '{path_to_check_existence}'.")
        else:
             logger.debug(f"Validated face file exists: {path_to_check_existence}")
    else:
         logger.info("No face file provided in request.")

    result = prepare_and_submit_image_workflow(request, client_id)
    if result["status"] != "submitted":
        raise HTTPException(status_code=502, detail={"message": "Failed to submit image job to ComfyUI", "details": result["error"]})
    return result

# --- Server Start ---
if __name__ == "__main__":
    logger.info("\n--- API Server v3 (Image Only) Pre-run Check ---")
    logger.info(f"⚠️ Ensure ComfyUI input subfolder exists: ComfyUI_Root/input/{SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}/")
    logger.info(f"⚠️ Ensure nodes in IMAGE workflow ('{BASE_WORKFLOW_IMAGE_PATH.name}') have correct titles set:")
    logger.info(f"   Prompt Input Node Title : '{PROMPT_NODE_TITLE}'")
    logger.info(f"   Face Input Node Title   : '{FACE_NODE_TITLE}' (for LoadImage feeding ReActor)")
    logger.info(f"   Seed Input Node Title   : '{SEED_NODE_TITLE}' (for RandomNoise or Sampler)")
    logger.info(f"   Output Prefix Node Title: '{OUTPUT_PREFIX_NODE_TITLE}' (Optional, for FileNamePrefix)")
    logger.info("--- Starting API Server v3 (Image Only) ---")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")