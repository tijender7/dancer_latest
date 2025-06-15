import os
import json
import requests
import uuid
import copy
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import uvicorn
from pathlib import Path # Use pathlib for paths

# --- Configuration Loading ---
CONFIG_FILE = "config.json"
try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    print(f"✅ Configuration loaded successfully from '{CONFIG_FILE}'.")
except FileNotFoundError:
    print(f"❌ FATAL ERROR: Configuration file '{CONFIG_FILE}' not found!")
    exit(1)
except json.JSONDecodeError as e:
    print(f"❌ FATAL ERROR: Configuration file '{CONFIG_FILE}' is not valid JSON: {e}")
    exit(1)
except Exception as e:
    print(f"❌ FATAL ERROR: An unexpected error occurred loading config: {e}")
    exit(1)

# --- Constants from Config ---
COMFYUI_API_URL = config.get("comfyui_api_url", "http://127.0.0.1:8188/prompt")
# Use Path objects for consistency
BASE_WORKFLOW_IMAGE_PATH = Path(config.get("base_workflow_image", ""))
BASE_WORKFLOW_VIDEO_PATH = Path(config.get("base_workflow_video", ""))
# source_faces_path from config is relative to the script for existence check
SOURCE_FACES_PATH_CONFIG = Path(config.get("source_faces_path", "source_faces"))
# This is the SUBFOLDER name inside ComfyUI/input/ where faces are expected
SOURCE_FACES_SUBFOLDER_FOR_COMFYUI = SOURCE_FACES_PATH_CONFIG.name

# Node Titles to look for (SET THESE IN YOUR COMFYUI WORKFLOWS!)
# These titles should be unique within each workflow for their purpose.
PROMPT_NODE_TITLE = "API_Prompt_Input"
FACE_NODE_TITLE = "API_Face_Input"

# Check if required config keys are present and paths exist
required_keys = ["comfyui_api_url", "base_workflow_image", "base_workflow_video", "source_faces_path"]
if not all(key in config for key in required_keys):
    print(f"❌ FATAL ERROR: Missing one or more required keys in '{CONFIG_FILE}': {required_keys}")
    exit(1)
if not BASE_WORKFLOW_IMAGE_PATH.is_file():
     print(f"❌ FATAL ERROR: Base Image Workflow file not found: '{BASE_WORKFLOW_IMAGE_PATH}'")
     exit(1)
if not BASE_WORKFLOW_VIDEO_PATH.is_file():
     print(f"❌ FATAL ERROR: Base Video Workflow file not found: '{BASE_WORKFLOW_VIDEO_PATH}'")
     exit(1)

print(f"   ComfyUI API URL: {COMFYUI_API_URL}")
print(f"   Image Workflow: {BASE_WORKFLOW_IMAGE_PATH}")
print(f"   Video Workflow: {BASE_WORKFLOW_VIDEO_PATH}")
print(f"   Source Faces Path (for script check): {SOURCE_FACES_PATH_CONFIG}")
print(f"   Source Faces Subfolder (for ComfyUI): {SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}")
print(f"   Looking for Prompt Node Title: '{PROMPT_NODE_TITLE}'")
print(f"   Looking for Face Node Title: '{FACE_NODE_TITLE}'")


# --- Load Base Workflows ---
try:
    with open(BASE_WORKFLOW_IMAGE_PATH, "r", encoding="utf-8") as f:
        base_image_workflow = json.load(f)
    print(f"✅ Loaded Base Image Workflow: {BASE_WORKFLOW_IMAGE_PATH.name}")
except Exception as e:
    print(f"❌ FATAL ERROR: Failed to load Image Workflow '{BASE_WORKFLOW_IMAGE_PATH}': {e}")
    exit(1)

try:
    with open(BASE_WORKFLOW_VIDEO_PATH, "r", encoding="utf-8") as f:
        base_video_workflow = json.load(f)
    print(f"✅ Loaded Base Video Workflow: {BASE_WORKFLOW_VIDEO_PATH.name}")
except Exception as e:
    print(f"❌ FATAL ERROR: Failed to load Video Workflow '{BASE_WORKFLOW_VIDEO_PATH}': {e}")
    exit(1)

# --- Helper Function to Find Nodes by Title (Primary Method) ---
def find_node_id_by_title(workflow, title):
    """Finds the first node ID matching the given _meta.title."""
    for node_id, node_data in workflow.items():
        if node_data.get("_meta", {}).get("title") == title:
            print(f"   Found node by title '{title}': ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    print(f"   ⚠️  Node not found by title: '{title}'")
    return None

# --- FastAPI App ---
app = FastAPI(title="ComfyUI Generation API")

# --- Request Model ---
class GenerationRequest(BaseModel):
    prompt: str
    face: str

# --- API Endpoint ---
@app.post("/generate", summary="Generate Image and Video")
async def generate_image_and_video(request: GenerationRequest):
    """
    Receives a prompt and face filename. Triggers ComfyUI image and video
    workflows sequentially, injecting the prompt and face image path into
    nodes identified by specific titles ('API_Prompt_Input', 'API_Face_Input').

    - **prompt**: The text prompt for generation.
    - **face**: The filename (e.g., "my_face.png") of the source face image.
      This file **must** exist inside `ComfyUI/input/{SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}/`.
    """
    start_time = datetime.now()
    client_id = str(uuid.uuid4())
    prompt_text = request.prompt
    face_filename = request.face

    # --- Path Construction ---
    face_relative_path_for_comfyui = Path(SOURCE_FACES_SUBFOLDER_FOR_COMFYUI) / face_filename
    # Use as_posix() to ensure forward slashes for ComfyUI
    face_path_str_for_comfyui = face_relative_path_for_comfyui.as_posix()

    path_to_check_existence = SOURCE_FACES_PATH_CONFIG / face_filename

    print(f"\n{'='*10} Request Received ({start_time.strftime('%Y-%m-%d %H:%M:%S')}) {'='*10}")
    print(f"Client ID: {client_id}")
    print(f"Prompt: '{prompt_text}'")
    print(f"Face Filename: '{face_filename}'")
    print(f"Checking for source file at: '{path_to_check_existence}'")
    print(f"Path to be used in ComfyUI LoadImage nodes: '{face_path_str_for_comfyui}'")
    print("-" * 40)

    # --- Validate Face File Existence ---
    if not path_to_check_existence.is_file():
        error_msg = f"Source face file not found at '{path_to_check_existence}'. Ensure the file exists and the 'source_faces_path' in config.json is correct relative to the script's location."
        print(f"❌ ERROR: {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    else:
        print(f"✅ Source face file found by script at '{path_to_check_existence}'.")

    results = {
        "client_id": client_id,
        "request_details": {"prompt": prompt_text, "face": face_filename},
        "image_job": {"status": "pending", "error": None},
        "video_job": {"status": "pending", "error": None},
    }

    # ======================================
    # 🔹 1. Generate Image
    # ======================================
    print("\n🖼️ Preparing Image Generation...")
    try:
        img_wf = copy.deepcopy(base_image_workflow)

        # --- Find Nodes to Modify using TITLES ---
        print(f"   Finding nodes in Image Workflow ('{BASE_WORKFLOW_IMAGE_PATH.name}')...")
        prompt_node_id = find_node_id_by_title(img_wf, PROMPT_NODE_TITLE)
        face_node_id = find_node_id_by_title(img_wf, FACE_NODE_TITLE)

        if not prompt_node_id:
            # Add fallback logic here if needed, but relying on title is preferred
            raise ValueError(f"Could not find Image Prompt node with title '{PROMPT_NODE_TITLE}'. Please set the title in the ComfyUI workflow.")
        if not face_node_id:
            raise ValueError(f"Could not find Image Face node with title '{FACE_NODE_TITLE}'. Please set the title for the correct LoadImage node in the ComfyUI workflow.")

        # --- Modify Workflow Inputs ---
        # Determine the correct input key for the prompt node (usually 'text' for Text Multiline)
        prompt_input_key = "text" # Assume 'text' for Text Multiline or similar
        if img_wf[prompt_node_id].get("class_type") == "WanVideoTextEncode": # Example if workflow structure changes
             prompt_input_key = "positive_prompt"
        print(f"   Modifying Image Node {prompt_node_id} input '{prompt_input_key}' (Prompt)...")
        img_wf[prompt_node_id]["inputs"][prompt_input_key] = prompt_text

        # Face node is assumed to be LoadImage, which uses the 'image' key
        print(f"   Modifying Image Node {face_node_id} input 'image' (Face Image)...")
        img_wf[face_node_id]["inputs"]["image"] = face_path_str_for_comfyui

        payload = {"prompt": img_wf, "client_id": client_id}
        print(f"   Submitting Image workflow to ComfyUI ({COMFYUI_API_URL})...")
        response = requests.post(COMFYUI_API_URL, json=payload, timeout=60)

        if response.status_code == 200:
            results["image_job"]["status"] = "submitted"
            print(f"✅ Image Job Submitted Successfully to ComfyUI.")
        else:
            results["image_job"]["status"] = "failed_submission"
            error_detail = f"ComfyUI image request failed: {response.status_code} - {response.text}"
            results["image_job"]["error"] = error_detail
            print(f"❌ {error_detail}")

    except requests.exceptions.RequestException as e:
        results["image_job"]["status"] = "error_connection"
        error_detail = f"Error connecting to ComfyUI for image job: {e}"
        results["image_job"]["error"] = error_detail
        print(f"❌ {error_detail}")
    except Exception as e:
        results["image_job"]["status"] = "error_preparing"
        error_detail = f"Error preparing/sending image workflow: {e}"
        results["image_job"]["error"] = error_detail
        print(f"❌ {error_detail}")

    # ======================================
    # 🔹 2. Generate Video
    # ======================================
    print("\n🎬 Preparing Video Generation...")
    try:
        vid_wf = copy.deepcopy(base_video_workflow)

        # --- Find Nodes to Modify using TITLES ---
        print(f"   Finding nodes in Video Workflow ('{BASE_WORKFLOW_VIDEO_PATH.name}')...")
        prompt_node_id = find_node_id_by_title(vid_wf, PROMPT_NODE_TITLE)
        face_node_id = find_node_id_by_title(vid_wf, FACE_NODE_TITLE)

        if not prompt_node_id:
            raise ValueError(f"Could not find Video Prompt node with title '{PROMPT_NODE_TITLE}'. Please set the title in the ComfyUI workflow.")
        if not face_node_id:
            raise ValueError(f"Could not find Video Face node with title '{FACE_NODE_TITLE}'. Please set the title for the correct LoadImage node in the ComfyUI workflow.")

        # --- Modify Workflow Inputs ---
        # Determine the correct input key based on the found prompt node's class type
        prompt_input_key = "text" # Default assumption
        node_class_type = vid_wf[prompt_node_id].get("class_type")
        if node_class_type == "WanVideoTextEncode":
            prompt_input_key = "positive_prompt"
            print(f"   Detected '{node_class_type}', using '{prompt_input_key}' for prompt.")
        elif node_class_type != "Text Multiline": # Add other types if needed
            print(f"   ⚠️ WARNING: Prompt node {prompt_node_id} has unexpected class '{node_class_type}'. Assuming input key is '{prompt_input_key}'.")

        print(f"   Modifying Video Node {prompt_node_id} input '{prompt_input_key}' (Prompt)...")
        vid_wf[prompt_node_id]["inputs"][prompt_input_key] = prompt_text

        # Face node is assumed to be LoadImage, uses 'image' key
        print(f"   Modifying Video Node {face_node_id} input 'image' (Face Image)...")
        vid_wf[face_node_id]["inputs"]["image"] = face_path_str_for_comfyui

        payload = {"prompt": vid_wf, "client_id": client_id}
        print(f"   Submitting Video workflow to ComfyUI ({COMFYUI_API_URL})...")
        response = requests.post(COMFYUI_API_URL, json=payload, timeout=120)

        if response.status_code == 200:
            results["video_job"]["status"] = "submitted"
            print(f"✅ Video Job Submitted Successfully to ComfyUI.")
        else:
            results["video_job"]["status"] = "failed_submission"
            try:
                error_json = response.json()
                error_detail = f"ComfyUI video request failed: {response.status_code} - {json.dumps(error_json, indent=2)}"
            except json.JSONDecodeError:
                error_detail = f"ComfyUI video request failed: {response.status_code} - {response.text}"
            results["video_job"]["error"] = error_detail
            print(f"❌ {error_detail}")

    except requests.exceptions.RequestException as e:
        results["video_job"]["status"] = "error_connection"
        error_detail = f"Error connecting to ComfyUI for video job: {e}"
        results["video_job"]["error"] = error_detail
        print(f"❌ {error_detail}")
    except Exception as e:
        results["video_job"]["status"] = "error_preparing"
        error_detail = f"Error preparing/sending video workflow: {e}"
        results["video_job"]["error"] = error_detail
        print(f"❌ {error_detail}")

    # --- Return Combined Results ---
    end_time = datetime.now()
    duration = end_time - start_time
    print("-" * 40)
    print(f"Request finished for Client ID: {client_id} (Duration: {duration})")
    print(f"Final Status: Image={results['image_job']['status']}, Video={results['video_job']['status']}")
    print("=" * (32 + len(start_time.strftime('%Y-%m-%d %H:%M:%S'))))

    # Decide HTTP status (keeping 200 OK even on ComfyUI submission errors, errors are in body)
    return results

# --- Pre-Run Check and Server Start ---
if __name__ == "__main__":
    print("\n--- Pre-run Check ---")
    print(f"⚠️ IMPORTANT: Ensure source faces folder exists and is accessible by ComfyUI at:")
    print(f"   ComfyUI_Root/input/{SOURCE_FACES_SUBFOLDER_FOR_COMFYUI}/")
    print(f"⚠️ IMPORTANT: Ensure nodes in workflows have correct titles set:")
    print(f"   Prompt Input Node Title: '{PROMPT_NODE_TITLE}'")
    print(f"   Face Input Node Title  : '{FACE_NODE_TITLE}'")
    print("--- Starting Server ---")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")