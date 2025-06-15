# main_automation_v5.py (Added Image Approval Step via Flask)
import os
import json
import random
import requests
import time
import shutil
import logging
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

# --- Import Flask ---
# Installation required: pip install Flask
try:
    from flask import Flask, request, render_template_string, send_from_directory, jsonify
    print("DEBUG: Flask imported successfully.")
except ImportError:
    print("ERROR: Flask library not found. Please install it: pip install Flask")
    sys.exit(1)

# --- Import TQDM ---
try:
    from tqdm import tqdm
    print("DEBUG: tqdm imported successfully.")
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

print("DEBUG: Script execution started (v5).")

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAY = 3
OLLAMA_TIMEOUT = 180
REQUEST_TIMEOUT = 60 # Timeout for API calls to our *own* API server
POLLING_INTERVAL = 10 # Check ComfyUI history every 10 seconds
POLLING_TIMEOUT_IMAGE = 1800 # 30 minutes per image
POLLING_TIMEOUT_VIDEO = 3600 # 60 minutes per video
APPROVAL_SERVER_PORT = 5005 # Port for the temporary approval web server
APPROVAL_FILENAME = "approved_indices.json"
APPROVED_IMAGES_SUBFOLDER = "approved_images" # Subfolder within run output for copies

# --- !! CONFIGURABLE PATHS !! ---
SCRIPT_DIR = Path(__file__).resolve().parent
# !!! USER MUST SET THESE CORRECTLY !!!
# Base Input directory FOR COMFYUI (where face folders, temp starts go)
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input") # <<< USER MUST SET
# Base Output directory WHERE COMFYUI SAVES FILES
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content") # <<< USER MUST SET
# Subdirectory *within* COMFYUI_INPUT_DIR_BASE for temporary start images
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"
# !!! END USER SETTINGS !!!

print(f"DEBUG: Script directory: {SCRIPT_DIR}")
print(f"DEBUG: Assumed ComfyUI Input Base: {COMFYUI_INPUT_DIR_BASE}")
print(f"DEBUG: Assumed ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")

# --- Logging Setup ---
print("DEBUG: Setting up logging...")
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_v5_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8'); file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.INFO) # Default to INFO, set DEBUG for more detail
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler); logger.addHandler(console_handler)
print("DEBUG: Logging setup complete.")
logger.info("Starting Automation v5 Run")

# --- Helper Function (Find by Title) ---
# (Keep same function from v4)
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("_meta", {}).get("title") == title:
            logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

# --- Configuration Loading ---
# (Keep same function, ensures config4.json is used)
def load_config(config_path="config4.json"):
    print(f"DEBUG: Entering load_config for '{config_path}'")
    config_path_obj = SCRIPT_DIR / config_path
    try:
        if not config_path_obj.is_file(): logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
        print(f"DEBUG: Config file exists: {config_path_obj}")
        with open(config_path_obj, 'r', encoding='utf-8') as f: config = json.load(f)
        print(f"DEBUG: JSON loaded from {config_path_obj}")
        required = ['api_server_url', 'base_workflow_image', 'base_workflow_video', 'source_faces_path', 'output_folder', 'comfyui_api_url', 'ollama_model', 'num_prompts']
        for key in required:
            if key not in config: raise KeyError(f"Missing required key '{key}'")
        print("DEBUG: Required keys found in config.")
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve()
        print(f"DEBUG: Resolved source_faces_path: {config['source_faces_path']}")
        print(f"DEBUG: Resolved output_folder: {config['output_folder']}")
        if not config['source_faces_path'].is_dir(): logger.warning(f"Source faces dir not found: {config['source_faces_path']}")
        config['output_folder'].mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Output folder ensured: {config['output_folder']}")
        config['comfyui_api_url'] = config['comfyui_api_url'].rstrip('/')
        config['api_server_url'] = config['api_server_url'].rstrip('/')
        logger.info(f"Config loaded successfully from {config_path_obj}")
        print(f"DEBUG: Config load successful.")
        return config
    except FileNotFoundError: logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
    except json.JSONDecodeError as e: logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)
    except KeyError as e: logger.critical(f"CRITICAL: {e} in config '{config_path}'"); sys.exit(1)
    except Exception as e: logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)

# --- Ollama Prompt Generation ---
# (Keep same generate_prompts_ollama function from v4)
def generate_prompts_ollama(model, num_prompts, ollama_api_url):
    logger.info(f"🚀 Generating {num_prompts} prompts via Ollama (Model: {model}, URL: {ollama_api_url})...")
    backgrounds = [ "bollywood dance floor", "dance floor white light", "indian festival ground" ]
    generated_prompt_list = []
    for i in range(num_prompts):
        background = random.choice(backgrounds)
        base_scene_idea = (f"A gorgeous, confident female dancer with revealing, facing camera, short clothing (like a small blouse top and super  large natural bust and ass revealing indian saree with hot pants) and very noticeable curves,  large natural bust out, small visible nipple " f"dancing energetically as the main focus in/at {background}. " f"Camera is medium shot or close-up on her. Other attractive people and dancers are visible partying " f"in the background but slightly blurred or less detailed. Focus on a vibrant, sexy, high-energy, " f"cinematic party atmosphere. indian festival ground")
        formatted_prompt = f"""Generate ONE single-line, in the prompt include  large natural bust popping out hard, highly detailed cinematic prompt for AI image/video. Focus on visual elements: dynamic lighting, camera angle/shot type (e.g., low angle close-up, dynamic medium shot), mood (energetic, celebratory, sexy), specific details about the main dancer's attire (short, revealing), expression (confident, playful),  large natural bust and the specific party environment ({background}). Include details about background dancers/partygoers. NO commentary. Respond ONLY with a valid JSON object: {{"prompts": ["<your prompt here>"]}}\n\nScene Desc:\n{base_scene_idea}"""
        logger.info(f"\n🧠 Requesting Prompt [{i+1}/{num_prompts}] | Theme: {background}")
        ollama_success = False; last_error = None
        for attempt in range(OLLAMA_MAX_RETRIES):
            logger.debug(f"   Ollama Attempt {attempt+1}/{OLLAMA_MAX_RETRIES}...")
            try:
                response = requests.post(ollama_api_url, json={"model": model, "prompt": formatted_prompt, "stream": False}, timeout=OLLAMA_TIMEOUT)
                response.raise_for_status(); response_json = response.json(); generated_text = response_json.get("response", "").strip()
                try:
                    start_index = generated_text.find('{'); end_index = generated_text.rfind('}')
                    if start_index != -1 and end_index != -1 and start_index < end_index:
                        json_str = generated_text[start_index:end_index+1]; parsed = json.loads(json_str)
                        if "prompts" in parsed and isinstance(parsed["prompts"], list) and parsed["prompts"]:
                            prompt_text = parsed["prompts"][0].strip()
                            if prompt_text: logger.info(f"   ✅ Clean Prompt Extracted:\n      '{prompt_text}'"); generated_prompt_list.append({"index": i + 1, "background": background, "generated_prompt": prompt_text}); ollama_success = True; break
                            else: last_error = ValueError("Empty prompt string in JSON.")
                        else: last_error = ValueError("Invalid JSON structure ('prompts' missing/empty).")
                    else: last_error = ValueError("JSON brackets not found or invalid in Ollama response.")
                except json.JSONDecodeError as json_e: last_error = json_e; logger.warning(f"   ❌ Could not decode JSON from Ollama response (Attempt {attempt+1}): {json_e}"); logger.debug(f"      Ollama raw response: {generated_text}")
            except requests.exceptions.RequestException as e: last_error = e; logger.warning(f"   ❌ Error connecting to Ollama (Attempt {attempt+1}): {e}")
            except Exception as e: last_error = e; logger.warning(f"   ❌ Unexpected error processing Ollama (Attempt {attempt+1}): {e}")
            if not ollama_success and attempt < OLLAMA_MAX_RETRIES - 1: logger.info(f"      Retrying Ollama in {OLLAMA_RETRY_DELAY}s..."); time.sleep(OLLAMA_RETRY_DELAY)
            elif not ollama_success: logger.error(f"   ❌ Failed to generate prompt [{i+1}] after {OLLAMA_MAX_RETRIES} attempts. Last error: {last_error}"); generated_prompt_list.append({"index": i + 1, "background": background, "error": str(last_error)})
    successful_count = sum(1 for p in generated_prompt_list if 'error' not in p); logger.info(f"✅ Finished generating {successful_count}/{num_prompts} prompts.")
    return generated_prompt_list

# --- Prompt Logging ---
# (Keep save_prompts_log function as is from v4)
def save_prompts_log(prompt_list):
     if not prompt_list: logger.warning("No prompts generated to save."); return
     timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
     log_folder = SCRIPT_DIR / "logs" # Already created
     json_path = log_folder / f"generated_prompts_{timestamp_str}.json"
     txt_path = log_folder / f"generated_prompts_{timestamp_str}.txt"
     try:
         with open(json_path, "w", encoding="utf-8") as f: json.dump(prompt_list, f, indent=2, ensure_ascii=False)
         logger.info(f"📝 Full prompt data saved to: {json_path}")
     except Exception as e: logger.error(f"Failed to save prompts JSON: {e}")
     try:
         with open(txt_path, "w", encoding="utf-8") as f:
             f.write(f"Generated Prompts - {timestamp_str}\n" + "="*30 + "\n\n")
             for item in prompt_list:
                  prompt_text = item.get("generated_prompt"); error_text = item.get("error")
                  f.write(f"{item['index']:02d}. [Background: {item.get('background','N/A')}]\n");
                  if prompt_text: f.write(f"   Prompt: {prompt_text}\n\n")
                  elif error_text: f.write(f"   Error: {error_text}\n\n")
                  else: f.write("   Status: Unknown (No prompt or error)\n\n")
         logger.info(f"📝 Clean prompts saved to: {txt_path}")
     except Exception as e: logger.error(f"Failed to save prompts TXT: {e}")

# --- Function to Call API Server ---
# (Keep trigger_generation function as is from v4)
def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None, output_subfolder: str, filename_prefix: str, video_start_image: str | None = None):
    """Sends a request to the intermediate API server (api_server_v5.py)."""
    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
    payload = {
        "prompt": prompt,
        "face": face_filename or "", # Send empty string if None
        "output_subfolder": output_subfolder,
        "filename_prefix_text": filename_prefix
    }
    # Add video start image path only if it's for the video endpoint and provided
    if endpoint == "generate_video" and video_start_image:
        payload["video_start_image_path"] = video_start_image

    log_prefix = f"API Call -> {endpoint}"
    logger.info(f"  ➡️ {log_prefix}: Preparing request...")
    logger.info(f"     URL: {full_url}")
    logger.info(f"     Prompt (start): '{prompt[:70]}...'")
    logger.info(f"     Face Filename: '{face_filename or 'None'}'")
    logger.info(f"     Output Subfolder: '{output_subfolder}'")
    logger.info(f"     Filename Prefix: '{filename_prefix}'")
    if video_start_image:
        logger.info(f"     Video Start Image: '{video_start_image}'")
    logger.debug(f"    Payload Sent: {json.dumps(payload, indent=2)}")

    for attempt in range(1, MAX_API_RETRIES + 1):
        logger.info(f"  🚀 {log_prefix} (Attempt {attempt}/{MAX_API_RETRIES})")
        response = None
        try:
            response = requests.post(full_url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            response_data = response.json()

            logger.info(f"  ✅ {log_prefix} submitted successfully (HTTP {response.status_code})")
            api_status = response_data.get('status', 'N/A')
            api_error = response_data.get('error', None)
            comfy_prompt_id = response_data.get('prompt_id', 'N/A')

            logger.info(f"     API Server Status: '{api_status}'")
            logger.info(f"     ComfyUI Prompt ID: '{comfy_prompt_id}'")
            if api_error:
                logger.warning(f"     API Server reported error: {api_error}")

            # Return prompt_id ONLY if status is 'submitted' and we got an ID
            if api_status == 'submitted' and comfy_prompt_id and comfy_prompt_id != 'N/A':
                return comfy_prompt_id
            else:
                 logger.error(f"     API submission failed or prompt_id missing. Status: {api_status}, ID: {comfy_prompt_id}")
                 return None # Indicate failure

        except requests.exceptions.Timeout:
            logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): Request timed out after {REQUEST_TIMEOUT} seconds.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): {e}")
            # Try to log response details if available
            if e.response is not None:
                 response = e.response # Keep response object for logging
                 logger.warning(f"      Status Code: {e.response.status_code}")
                 try:
                     # Try parsing JSON, fallback to text
                     error_detail = json.dumps(e.response.json(), indent=2)
                 except json.JSONDecodeError:
                     error_detail = e.response.text[:500] # Log first 500 chars
                 logger.warning(f"      Response Body: {error_detail}...")
            else:
                 logger.warning("      No response object received.")
        except json.JSONDecodeError as e:
             # This happens if the API server returns non-JSON response on success (shouldn't happen)
             logger.error(f"  ❌ Error decoding JSON response from API server (Attempt {attempt}): {e}")
             if response is not None:
                 logger.debug(f"     Raw Response Text: {response.text[:500]}...")
             else:
                 logger.debug("     No response object available for raw text logging.")
        except Exception as e:
            logger.error(f"  ❌ Unexpected error calling API (Attempt {attempt}): {e}", exc_info=True)

        # Retry logic
        if attempt < MAX_API_RETRIES:
            logger.info(f"      Retrying in {API_RETRY_DELAY} seconds...")
            time.sleep(API_RETRY_DELAY)
        else:
            logger.error(f"  ❌ {log_prefix} failed after {MAX_API_RETRIES} attempts.")
            return None # Explicitly return None after all retries fail

    return None # Should not be reached ideally, but safety return


# --- Function to Poll ComfyUI History ---
# (Keep check_comfyui_job_status function as is from v4)
def check_comfyui_job_status(comfyui_base_url: str, prompt_id: str):
    """Polls the ComfyUI /history endpoint for a specific prompt ID."""
    if not prompt_id:
        logger.debug("Skipping history check: prompt_id is None or empty.")
        return None
    history_url = f"{comfyui_base_url}/history/{prompt_id}"
    logger.debug(f"Polling ComfyUI: {history_url}")
    try:
        response = requests.get(history_url, timeout=10) # Short timeout for polling
        response.raise_for_status()
        history_data = response.json()
        # History returns an object where keys are prompt_ids
        if prompt_id in history_data:
            logger.debug(f"History found for prompt_id {prompt_id}.")
            return history_data[prompt_id] # Return the specific entry for this ID
        else:
            # This usually means the job is still running or queued
            logger.debug(f"Prompt_id {prompt_id} not found in history response (running/pending).")
            return None
    except requests.exceptions.Timeout:
        logger.warning(f"Polling /history timed out for {prompt_id}.")
        return None
    except requests.exceptions.RequestException as e:
        # Handle cases like 404 if history is pruned quickly, or connection errors
        logger.warning(f"Error polling /history/{prompt_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Error decoding history JSON for {prompt_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error polling history for {prompt_id}: {e}", exc_info=True)
        return None

# --- Function to Extract Output Filename from History ---
# (Keep get_output_filename_from_history function as is from v4)
def get_output_filename_from_history(history_entry: dict, output_node_id: str):
    """Parses history data to find the filename from a specific Save node."""
    if not history_entry or 'outputs' not in history_entry:
        logger.warning(f"History entry invalid or missing 'outputs' key for node {output_node_id}.")
        logger.debug(f"Invalid history entry data: {json.dumps(history_entry, indent=2)}")
        return None

    if output_node_id in history_entry['outputs']:
        node_output = history_entry['outputs'][output_node_id]
        logger.debug(f"Outputs found for node {output_node_id}: {json.dumps(node_output, indent=2)}")

        # Check common output structures (SaveImage, SaveImageWEBP, VHS_SaveVideo, etc.)
        # Prioritize 'images' for standard image saves
        if 'images' in node_output and isinstance(node_output['images'], list) and len(node_output['images']) > 0:
            image_info = node_output['images'][0]
            if isinstance(image_info, dict) and \
               'filename' in image_info and \
               'subfolder' in image_info and \
               'type' in image_info and image_info['type'] == 'output':
                # Construct relative path: subfolder might be empty
                subfolder = image_info['subfolder']
                filename = image_info['filename']
                relative_path = Path(subfolder) / filename if subfolder else Path(filename)
                logger.debug(f"Extracted relative image path from history: {relative_path}")
                return relative_path
            else:
                 logger.warning(f"Image info dict for node {output_node_id} missing required keys or type is not 'output'. Image Info: {image_info}")

        # Check for 'gifs' (used by some animated nodes like AnimateDiffCombine)
        elif 'gifs' in node_output and isinstance(node_output['gifs'], list) and len(node_output['gifs']) > 0:
            gif_info = node_output['gifs'][0]
            if isinstance(gif_info, dict) and \
               'filename' in gif_info and \
               'subfolder' in gif_info and \
               'type' in gif_info and gif_info['type'] == 'output':
                subfolder = gif_info['subfolder']
                filename = gif_info['filename']
                relative_path = Path(subfolder) / filename if subfolder else Path(filename)
                logger.debug(f"Extracted relative gif path from history: {relative_path}")
                return relative_path # Return gif path if found
            else:
                 logger.warning(f"Gif info dict for node {output_node_id} missing required keys or type is not 'output'. Gif Info: {gif_info}")

        # Add checks for other potential outputs if needed (e.g., 'videos')
        # elif 'videos' in node_output ...

        else:
             logger.warning(f"Node {output_node_id} output found, but no recognized output key ('images', 'gifs') found or list is empty.")
             logger.debug(f"Node output details: {node_output}")

    else:
         logger.warning(f"Node ID {output_node_id} not found in history entry outputs.")
         logger.debug(f"Available output node IDs in history: {list(history_entry['outputs'].keys())}")

    logger.warning(f"Could not find valid image/gif output for node {output_node_id} in history entry.")
    return None


# --- Flask Approval Server ---
approval_app = Flask(__name__)
approval_data = {
    "images_to_approve": [],
    "comfyui_output_base": None,
    "approval_file_path": None,
    "shutdown_event": None,
}

@approval_app.route('/')
def index():
    """Renders the approval page."""
    global approval_data
    images_html = ""
    if not approval_data["images_to_approve"]:
        images_html = "<p>No successfully generated images found to approve.</p>"
    else:
        for item in approval_data["images_to_approve"]:
            img_path = item.get('generated_image_path') # This is the *absolute* path
            item_index = item.get('index')
            img_src_url = None
            display_filename = "N/A"

            if img_path and isinstance(img_path, Path) and img_path.is_file():
                # Generate a URL safe relative path for the /images/ route
                try:
                    relative_path_for_url = img_path.relative_to(approval_data["comfyui_output_base"]).as_posix()
                    img_src_url = f"/images/{relative_path_for_url}"
                    display_filename = img_path.name
                except ValueError:
                    # This happens if the image path is not within the configured base output dir
                    logger.warning(f"Image path {img_path} is not relative to base {approval_data['comfyui_output_base']}. Cannot display.")
                    img_src_url = None # Or a placeholder image URL
                    display_filename = f"Error: Path Issue ({img_path.name})"
                except Exception as e:
                     logger.error(f"Error creating relative path for {img_path}: {e}")
                     img_src_url = None
                     display_filename = f"Error: Path Creation ({img_path.name})"
            else:
                logger.warning(f"Item {item_index} has invalid or missing image path: {img_path}")
                display_filename = f"Error: Missing Path (Index {item_index})"


            if img_src_url:
                images_html += f"""
                <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top;">
                    <p><b>Index: {item_index}</b> ({display_filename})</p>
                    <img src="{img_src_url}" alt="Generated Image {item_index}" style="max-width: 256px; max-height: 256px; display: block; margin-bottom: 5px;">
                    <input type="checkbox" name="approved_index" value="{item_index}" id="img_{item_index}">
                    <label for="img_{item_index}">Approve for Video</label>
                </div>
                """
            else:
                 images_html += f"""
                <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top; width: 256px; height: 300px; background-color: #eee;">
                    <p><b>Index: {item_index}</b></p>
                    <p style="color: red;">{display_filename}</p>
                    <p>(Cannot display image)</p>
                </div>
                """


    # Simple HTML structure
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Approval</title>
        <style> body {{ font-family: sans-serif; }} </style>
    </head>
    <body>
        <h1>Approve Images for Video Generation</h1>
        <p>Select the images you want to use as starting frames for video generation.</p>
        <form action="/submit" method="post">
            {images_html}
            <div style="clear: both; margin-top: 20px;">
                <button type="submit">Submit Approvals</button>
            </div>
        </form>
    </body>
    </html>
    """
    return render_template_string(html_content)

@approval_app.route('/images/<path:filename>')
def serve_image(filename):
    """Serves images from the ComfyUI output directory."""
    global approval_data
    logger.debug(f"Serving image request: {filename} from base: {approval_data['comfyui_output_base']}")
    # Ensure the requested path doesn't try to escape the base directory (basic security)
    safe_path = Path(filename).resolve()
    base_path = approval_data["comfyui_output_base"].resolve()
    if not str(safe_path).startswith(str(base_path)):
         logger.warning(f"Attempt to access file outside base directory denied: {filename}")
         return "Access Denied", 403
    # send_from_directory needs the directory and the filename separately
    try:
        directory = safe_path.parent
        name = safe_path.name
        return send_from_directory(directory, name)
    except FileNotFoundError:
        logger.error(f"File not found for serving: {safe_path}")
        return "File Not Found", 404
    except Exception as e:
         logger.error(f"Error serving file {safe_path}: {e}", exc_info=True)
         return "Server Error", 500


@approval_app.route('/submit', methods=['POST'])
def submit_approval():
    """Handles the form submission, saves approved indices, and triggers shutdown."""
    global approval_data
    approved_indices = request.form.getlist('approved_index')
    # Convert to integers
    approved_indices_int = []
    for idx_str in approved_indices:
        try:
            approved_indices_int.append(int(idx_str))
        except ValueError:
            logger.warning(f"Received invalid index value: {idx_str}. Skipping.")

    logger.info(f"Received approval for indices: {approved_indices_int}")

    # Save to file
    try:
        with open(approval_data["approval_file_path"], 'w', encoding='utf-8') as f:
            json.dump({"approved_indices": approved_indices_int}, f, indent=2)
        logger.info(f"Approved indices saved to: {approval_data['approval_file_path']}")
        # Trigger shutdown
        if approval_data["shutdown_event"]:
            logger.info("Signaling main thread to shut down approval server.")
            approval_data["shutdown_event"].set() # Signal the main thread
        else:
             logger.error("Shutdown event not set in approval_data!")
        return "Approvals submitted successfully! You can close this window."
    except Exception as e:
        logger.error(f"Failed to save approval file: {e}", exc_info=True)
        # Don't trigger shutdown if save failed
        return "Error saving approvals. Please check logs.", 500

def run_approval_server(images_list, comfy_output_base_path, file_path, shutdown_event_obj):
    """Starts the Flask server in a separate thread."""
    global approval_data
    approval_data["images_to_approve"] = images_list
    approval_data["comfyui_output_base"] = comfy_output_base_path
    approval_data["approval_file_path"] = file_path
    approval_data["shutdown_event"] = shutdown_event_obj

    # Disable Flask's default logging or redirect it if desired
    # log = logging.getLogger('werkzeug')
    # log.setLevel(logging.ERROR) # Suppress normal Flask request logs

    logger.info(f"Starting approval server on http://0.0.0.0:{APPROVAL_SERVER_PORT}")
    try:
        # Use 'quiet=True' if using newer Flask versions to suppress startup message
        approval_app.run(host='0.0.0.0', port=APPROVAL_SERVER_PORT, debug=False) # debug=False is important
    except Exception as e:
         logger.error(f"Failed to start approval server: {e}", exc_info=True)
         # Ensure event is set even on failure to unblock main thread
         if approval_data["shutdown_event"]:
             approval_data["shutdown_event"].set()

# --- Main Execution Logic ---
if __name__ == "__main__":
    print("DEBUG: Entering main execution block.")
    logger.info("=" * 50); logger.info(f"Starting Automation v5 Run: {datetime.now()}"); logger.info("=" * 50)

    config = load_config("config4.json")
    if not config: print("DEBUG: Config loading failed. Exiting."); sys.exit(1)
    print("DEBUG: Config loaded successfully in main.")

    API_SERVER_URL = config['api_server_url']
    COMFYUI_BASE_URL = config['comfyui_api_url'] # Base URL for polling ComfyUI history

    # --- Verify User-Set Paths ---
    if not COMFYUI_INPUT_DIR_BASE.is_dir():
        logger.critical(f"CRITICAL: Configured ComfyUI input directory does not exist: {COMFYUI_INPUT_DIR_BASE}")
        sys.exit(1)
    if not COMFYUI_OUTPUT_DIR_BASE.is_dir():
        # Don't exit, but warn heavily, as image serving will fail
        logger.error(f"CRITICAL WARNING: Configured ComfyUI output directory does not exist: {COMFYUI_OUTPUT_DIR_BASE}")
        logger.error("Image approval UI will likely fail to display images!")
        # sys.exit(1) # Optional: make this fatal

    logger.info(f"Using API Server: {API_SERVER_URL}")
    logger.info(f"Using ComfyUI API: {COMFYUI_BASE_URL}")
    logger.info(f"ComfyUI Input Base: {COMFYUI_INPUT_DIR_BASE}")
    logger.info(f"ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")

    # --- Setup Temp Dir for Video Start Images ---
    temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    try:
        temp_start_image_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured temporary directory for video start images: {temp_start_image_dir}")
    except Exception as e:
        logger.critical(f"Failed to create temp video start directory: {e}", exc_info=True)
        sys.exit(1)

    # 1. Generate Prompts
    # (Keep prompt gen call)
    print("DEBUG: Starting prompt generation...")
    prompts_data = generate_prompts_ollama(
        config["ollama_model"],
        config["num_prompts"],
        config.get("ollama_api_url", "http://localhost:11434/api/generate")
    )
    print(f"DEBUG: Prompt generation finished. Got {len(prompts_data)} results.")
    save_prompts_log(prompts_data) # Log prompts regardless of validity
    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts:
        logger.critical("No valid prompts generated by Ollama. Exiting.")
        print("DEBUG: No valid prompts found. Exiting.")
        sys.exit(1)
    logger.info(f"Proceeding with {len(valid_prompts)} valid prompts.")
    print(f"DEBUG: Proceeding with {len(valid_prompts)} valid prompts.")

    # 2. Prepare Faces List
    # (Keep face list prep)
    print("DEBUG: Preparing faces list...")
    face_files = []; source_faces_dir = config['source_faces_path']
    if source_faces_dir.is_dir():
        try:
            face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
            logger.info(f"Found {len(face_files)} face images in {source_faces_dir}.")
        except Exception as e:
             logger.error(f"Error scanning source faces directory {source_faces_dir}: {e}", exc_info=True)
    else:
         logger.warning(f"Source faces directory not found: {source_faces_dir}")

    if not face_files: logger.warning("No valid face images found. Face swap will be skipped if attempted.")
    print(f"DEBUG: Found {len(face_files)} face files.")

    # 3. Create ONE Root Output Directory name (in the script's output folder)
    print("DEBUG: Defining main run folder name...")
    script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # This is the output folder for *this script's* logs, approval file etc.
    script_output_base = config['output_folder']
    main_run_folder_path = script_output_base / f"Run_{script_run_timestamp}"
    try:
        main_run_folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created script run output directory: {main_run_folder_path}")
    except Exception as e:
        logger.critical(f"Failed to create script output directory: {e}", exc_info=True)
        sys.exit(1)

    # --- Store details for tracking ---
    run_details = [] # List of dictionaries tracking each item

    # --- Need the Node ID of the SaveImage node in the IMAGE workflow ---
    # This is CRUCIAL for finding the output path later
    image_save_node_id = None
    image_save_node_title = "API_Image_Output_SaveNode" # Must match title in JSON
    try:
        img_workflow_path_from_config = (SCRIPT_DIR / config["base_workflow_image"]).resolve()
        logger.debug(f"Checking for Save Node '{image_save_node_title}' in: {img_workflow_path_from_config}")
        if not img_workflow_path_from_config.is_file():
             logger.error(f"Image workflow path from config not found: {img_workflow_path_from_config}")
        else:
             with open(img_workflow_path_from_config, "r", encoding="utf-8") as f:
                 temp_img_wf = json.load(f)
             image_save_node_id = find_node_id_by_title(temp_img_wf, image_save_node_title, img_workflow_path_from_config.name)
             if not image_save_node_id:
                 logger.error(f"Could not find node titled '{image_save_node_title}' in image workflow '{img_workflow_path_from_config.name}'!")
                 logger.error("Polling for image outputs will likely fail.")
                 # Decide if this is fatal: sys.exit(1)
             else:
                 logger.info(f"Found Image Save Node '{image_save_node_title}' with ID: {image_save_node_id}")
    except Exception as e:
        logger.error(f"Error finding SaveImage node ID in image workflow: {e}", exc_info=True)
        # Decide if this is fatal: sys.exit(1)

    # ====================================================
    # 🔹 STAGE 1: Submit Image Generation Jobs
    # ====================================================
    logger.info(f"\n--- STAGE 1: Submitting Image Generation for {len(valid_prompts)} Prompts ---")
    print(f"DEBUG: Starting image submission loop for {len(valid_prompts)} prompts.")
    image_progress_bar = tqdm(valid_prompts, desc="Submitting Images")
    submitted_image_jobs = 0
    # Define the subfolder structure ONCE based on the run timestamp
    comfyui_image_output_subfolder = f"Run_{script_run_timestamp}/all_images" # Relative path for ComfyUI

    for item_index, item in enumerate(image_progress_bar):
        print(f"DEBUG: Processing item index {item_index}")
        idx = item["index"] # The original 1-based index from prompt generation
        prompt = item["generated_prompt"]

        # Select face deterministically based on index for reproducibility, or randomly
        selected_face_path = None
        face_filename_only = None
        if face_files:
            # Example: Cycle through faces
            selected_face_path = face_files[item_index % len(face_files)]
            # Example: Random choice
            # selected_face_path = random.choice(face_files)
            face_filename_only = selected_face_path.name
            logger.info(f"Selected face for Index {idx}: {face_filename_only}")
        else:
             logger.info(f"No face selected for Index {idx}.")


        # Filename prefix for ComfyUI output node
        image_filename_prefix = f"{idx:03d}_{'swapped' if face_filename_only else 'raw'}"

        image_progress_bar.set_description(f"Image Req {idx}/{len(valid_prompts)}")
        logger.info(f"\n🖼️ Preparing Image Request [{idx}/{len(valid_prompts)}]")
        print(f"DEBUG: Calling trigger_generation for image {idx}...")

        comfy_image_prompt_id = trigger_generation(
            API_SERVER_URL,
            "generate_image",
            prompt,
            face_filename_only, # Pass only the filename
            comfyui_image_output_subfolder, # Relative path for ComfyUI's output
            image_filename_prefix
        )
        print(f"DEBUG: trigger_generation for image {idx} returned prompt_id: {comfy_image_prompt_id}")

        # Store details for this item
        run_details.append({
            'index': idx, # Original index
            'prompt': prompt,
            'background': item.get('background', 'N/A'),
            'face_filename': face_filename_only, # Store filename used
            'image_prefix': image_filename_prefix,
            'video_prefix': f"{idx:03d}_video_{'swapped' if face_filename_only else 'raw'}", # Define video prefix here too
            'image_prompt_id': comfy_image_prompt_id, # Store ComfyUI ID for polling
            'image_job_status': 'submitted' if comfy_image_prompt_id else 'failed',
            'generated_image_path': None, # Full path after polling
            'temp_start_image_comfy_path': None, # Relative path for video start later
            'is_approved_for_video': False # Approval status
        })

        if comfy_image_prompt_id:
            submitted_image_jobs += 1
        else:
            logger.error(f"Failed API call for Image {idx}. Check API Server logs.")
        time.sleep(0.5) # Small delay between API calls

    logger.info(f"--- STAGE 1: {submitted_image_jobs}/{len(valid_prompts)} Image Generation Requests Submitted ---")

    # ========================================================
    # 🔹 STAGE 1.5: Wait for Image Jobs to Complete (Polling)
    # ========================================================
    if not image_save_node_id:
        logger.error("Cannot proceed to image polling stage: Image Save Node ID ('API_Image_Output_SaveNode') not found or identified in workflow JSON.")
        logger.error("Skipping image polling, approval, and video generation.")
        # Optionally exit here if polling is critical: sys.exit(1)
    elif submitted_image_jobs == 0:
         logger.warning("No image jobs were successfully submitted. Skipping polling.")
    else:
        logger.info(f"\n--- STAGE 1.5: Waiting for {submitted_image_jobs} Image Jobs to Complete (Polling /history) ---")
        # Filter details for jobs that were actually submitted
        jobs_to_poll = [d for d in run_details if d['image_prompt_id']]
        polling_progress = tqdm(total=len(jobs_to_poll), desc="Polling Images")
        completed_image_jobs = 0

        for details in jobs_to_poll:
            idx = details['index']
            prompt_id = details['image_prompt_id']
            logger.info(f"   Polling for Image {idx} (Prompt ID: {prompt_id})...")
            start_time = datetime.now()
            job_done = False
            while datetime.now() - start_time < timedelta(seconds=POLLING_TIMEOUT_IMAGE):
                history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
                if history_data:
                    logger.info(f"   ✅ Image {idx} completed (History found).")
                    details['image_job_status'] = 'completed'
                    relative_output_path = get_output_filename_from_history(history_data, image_save_node_id)
                    if relative_output_path:
                        # Construct FULL path using the configured base output dir
                        full_output_path = (COMFYUI_OUTPUT_DIR_BASE / relative_output_path).resolve()
                        details['generated_image_path'] = full_output_path # Store Path object
                        logger.info(f"      Found output file: {full_output_path}")
                        # Verify file exists (optional but good)
                        if not full_output_path.is_file():
                             logger.warning(f"      WARNING: History reported file {full_output_path}, but it doesn't exist on disk!")
                             details['image_job_status'] = 'completed_file_missing'
                        else:
                             details['image_job_status'] = 'completed_file_found'

                    else:
                        logger.error(f"      Image {idx} finished, but could not find output filename in history for node {image_save_node_id}!")
                        details['image_job_status'] = 'completed_no_output_found'
                    job_done = True
                    completed_image_jobs += 1
                    break # Exit polling loop for this job
                else:
                    # Still waiting
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    polling_progress.set_description(f"Polling Img {idx} ({int(elapsed_time)}s)")
                    time.sleep(POLLING_INTERVAL)

            if not job_done:
                 logger.error(f"   ❌ Polling timed out for Image {idx} (Prompt ID: {prompt_id}) after {POLLING_TIMEOUT_IMAGE} seconds.")
                 details['image_job_status'] = 'polling_timeout'
            polling_progress.update(1)

        polling_progress.close()
        logger.info(f"--- STAGE 1.5: Finished Polling Images ({completed_image_jobs}/{len(jobs_to_poll)} completed within timeout) ---")

    # ========================================================
    # 🔹 STAGE 1.7: Image Approval Step
    # ========================================================
    logger.info(f"\n--- STAGE 1.7: Image Approval ---")
    # Filter for images that completed successfully AND have a valid file path
    images_to_approve = [
        d for d in run_details
        if d.get('image_job_status') == 'completed_file_found' and \
           d.get('generated_image_path') and \
           isinstance(d.get('generated_image_path'), Path) and \
           d.get('generated_image_path').is_file()
    ]

    approved_indices_list = []
    if not images_to_approve:
        logger.warning("No successfully generated images found to approve. Skipping video generation.")
    elif not COMFYUI_OUTPUT_DIR_BASE.is_dir():
        logger.error(f"ComfyUI Output Base Dir ({COMFYUI_OUTPUT_DIR_BASE}) not found. Cannot start approval server.")
        logger.error("Skipping approval and video generation.")
    else:
        logger.info(f"Found {len(images_to_approve)} images eligible for approval.")
        approval_file_path = main_run_folder_path / APPROVAL_FILENAME
        approved_images_folder_path = main_run_folder_path / APPROVED_IMAGES_SUBFOLDER
        try:
            approved_images_folder_path.mkdir(exist_ok=True)
            logger.info(f"Created/ensured approved images folder: {approved_images_folder_path}")
        except Exception as e:
            logger.error(f"Failed to create approved images folder: {e}. Skipping approval.", exc_info=True)
            images_to_approve = [] # Prevent server start

        if images_to_approve:
            shutdown_event = threading.Event()
            approval_thread = threading.Thread(
                target=run_approval_server,
                args=(images_to_approve, COMFYUI_OUTPUT_DIR_BASE, approval_file_path, shutdown_event),
                daemon=True # Allows main thread to exit even if this fails badly
            )

            logger.info("Starting approval web server thread...")
            approval_thread.start()

            # Wait for server to start and print URL (add a small delay)
            time.sleep(2)
            logger.info("="*60)
            logger.info(f"➡️ Please open your web browser and go to: http://localhost:{APPROVAL_SERVER_PORT}")
            logger.info(f"➡️ OR (if accessing from another device on network): http://<YOUR_PC_IP_ADDRESS>:{APPROVAL_SERVER_PORT}")
            logger.info("➡️ Select the images to generate videos for and click 'Submit Approvals'.")
            logger.info("➡️ The script will resume automatically after you submit.")
            logger.info("="*60)

            # Wait until the shutdown event is set by the /submit route
            shutdown_event.wait() # Blocks here until event.set() is called
            logger.info("Approval server shutdown signal received. Proceeding...")

            # Check if the approval file was created
            if approval_file_path.is_file():
                try:
                    with open(approval_file_path, 'r', encoding='utf-8') as f:
                        approval_result = json.load(f)
                        approved_indices_list = approval_result.get("approved_indices", [])
                        logger.info(f"Successfully loaded {len(approved_indices_list)} approved indices from {approval_file_path}")
                except Exception as e:
                    logger.error(f"Error reading approval file {approval_file_path}: {e}. Assuming no approvals.", exc_info=True)
                    approved_indices_list = []
            else:
                logger.warning(f"Approval file ({approval_file_path}) not found. Assuming no images were approved.")
                approved_indices_list = []

            # Update run_details and copy approved images
            if approved_indices_list:
                logger.info("Processing approved images...")
                for details in run_details:
                    if details['index'] in approved_indices_list:
                        details['is_approved_for_video'] = True
                        logger.info(f"  - Marking index {details['index']} as approved.")
                        # Copy the image to the dedicated approved folder
                        try:
                            source_img_path = details['generated_image_path']
                            # Create a potentially clearer filename for the copy
                            dest_filename = f"approved_{details['image_prefix']}{source_img_path.suffix}"
                            dest_img_path = approved_images_folder_path / dest_filename
                            shutil.copyfile(source_img_path, dest_img_path)
                            logger.info(f"    Copied '{source_img_path.name}' -> '{dest_img_path.name}'")
                        except Exception as e:
                            logger.error(f"    Failed to copy approved image for index {details['index']}: {e}")
            else:
                 logger.info("No images were approved via the web UI.")

    # Filter run_details for the next stage
    details_for_video = [d for d in run_details if d['is_approved_for_video']]

    # ====================================================
    # 🔹 STAGE 2: Submit Video Generation Jobs (for approved images)
    # ====================================================
    if not details_for_video:
        logger.info("\n--- STAGE 2: No images approved for video generation. Skipping video submission. ---")
    else:
        logger.info(f"\n--- STAGE 2: Submitting Video Generation for {len(details_for_video)} Approved Images ---")
        print(f"DEBUG: Starting video submission loop for {len(details_for_video)} approved items.")
        video_progress_bar = tqdm(details_for_video, desc="Submitting Videos")
        items_successfully_submitted_video = 0
        all_video_prompt_ids = {} # Store video prompt IDs mapped to original index

        # Define the video output subfolder structure ONCE
        comfyui_video_output_subfolder = f"Run_{script_run_timestamp}/all_videos" # Relative path for ComfyUI

        for details in video_progress_bar:
            idx = details["index"]
            prompt = details["prompt"]
            # CRITICAL: Use the SAME face file that was used for the approved image
            face_filename_only = details["face_filename"]
            video_filename_prefix = details["video_prefix"]
            # The full path to the image GENERATED in stage 1.5
            generated_image_path = details["generated_image_path"]

            video_progress_bar.set_description(f"Video Req {idx}/{len(details_for_video)}")
            logger.info(f"\n🎬 Preparing Video Request [{idx}/{len(details_for_video)}]")
            print(f"DEBUG: Processing video for index {idx}, using image: {generated_image_path}")

            # --- Copy Generated Image to be Video Start Frame ---
            temp_start_image_comfy_path_str = None # Relative path for ComfyUI LoadImage node
            if generated_image_path and generated_image_path.is_file():
                try:
                    # Create a unique name for the temp file
                    temp_start_filename = f"start_{idx:03d}_{datetime.now().strftime('%H%M%S%f')}{generated_image_path.suffix}"
                    temp_dest_path = temp_start_image_dir / temp_start_filename
                    shutil.copyfile(generated_image_path, temp_dest_path)
                    # Construct the path ComfyUI needs (relative to its input dir)
                    temp_start_image_comfy_path = Path(TEMP_VIDEO_START_SUBDIR) / temp_start_filename
                    temp_start_image_comfy_path_str = temp_start_image_comfy_path.as_posix() # Use forward slashes
                    details['temp_start_image_comfy_path'] = temp_start_image_comfy_path_str # Store for potential cleanup info
                    logger.info(f"   Copied '{generated_image_path.name}' -> Comfy Input as '{temp_start_image_comfy_path_str}'")
                except Exception as copy_e:
                    logger.error(f"   Failed to copy image '{generated_image_path}' to temp dir '{temp_start_image_dir}': {copy_e}. Video might use default start frame.", exc_info=True)
                    temp_start_image_comfy_path_str = None # Ensure it's None if copy failed
            else:
                # This shouldn't happen if filtering worked, but safety check
                logger.warning(f"   Approved image file not found or path invalid: '{generated_image_path}'. Video might use default start frame.")
                temp_start_image_comfy_path_str = None

            # Call API Server - Video Endpoint
            print(f"DEBUG: Calling trigger_generation for video {idx}...")
            comfy_video_prompt_id = trigger_generation(
                API_SERVER_URL,
                "generate_video",
                prompt,
                face_filename_only, # Use the original face filename
                comfyui_video_output_subfolder, # Relative path for ComfyUI video output
                video_filename_prefix,
                video_start_image=temp_start_image_comfy_path_str # Pass the RELATIVE path for ComfyUI LoadImage
            )
            print(f"DEBUG: trigger_generation for video {idx} returned prompt_id: {comfy_video_prompt_id}")

            details['video_prompt_id'] = comfy_video_prompt_id # Store video prompt ID
            if comfy_video_prompt_id:
                 items_successfully_submitted_video += 1
                 all_video_prompt_ids[idx] = comfy_video_prompt_id # Store ID mapped to original index
                 details['video_job_status'] = 'submitted'
            else:
                 logger.error(f"Failed API call for Video {idx}. Check API Server logs.")
                 details['video_job_status'] = 'failed'
            time.sleep(0.5) # Small delay

        logger.info(f"--- STAGE 2: {items_successfully_submitted_video}/{len(details_for_video)} Video Generation Requests Submitted ---")
        print("DEBUG: Finished video submission loop.")

    # ========================================================
    # 🔹 STAGE 2.5: Wait for Video Jobs to Complete (Optional Polling)
    # ========================================================
    # Only poll if videos were submitted
    video_ids_to_poll = list(all_video_prompt_ids.values())
    if video_ids_to_poll:
        logger.info(f"\n--- STAGE 2.5: Waiting for {len(video_ids_to_poll)} Video Jobs to Complete (Polling /history) ---")
        # Note: This simple polling just checks if *any* history exists. It doesn't track individual completion.
        # A more robust approach would track completion status per ID.
        video_polling_progress = tqdm(total=len(video_ids_to_poll), desc="Polling Videos")
        completed_videos = 0
        start_poll_time_video = datetime.now()
        overall_video_timeout = POLLING_TIMEOUT_VIDEO * len(video_ids_to_poll) # Generous overall timeout

        # Keep polling until all submitted video jobs are found in history or overall timeout
        # More robust: Track which IDs are done
        active_video_poll_ids = set(video_ids_to_poll)
        while active_video_poll_ids and (datetime.now() - start_poll_time_video < timedelta(seconds=overall_video_timeout)):
            completed_in_pass = set()
            for prompt_id in list(active_video_poll_ids): # Iterate copy
                 history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
                 if history_data:
                     logger.info(f"   ✅ Video job with Prompt ID {prompt_id} confirmed complete.")
                     # Find the original index this prompt_id belongs to
                     original_idx = next((idx for idx, pid in all_video_prompt_ids.items() if pid == prompt_id), None)
                     if original_idx:
                          # Update status in run_details
                          for detail in details_for_video:
                              if detail['index'] == original_idx:
                                  detail['video_job_status'] = 'completed'
                                  break
                     completed_in_pass.add(prompt_id)
                     completed_videos = len(video_ids_to_poll) - len(active_video_poll_ids) + len(completed_in_pass)
                     video_polling_progress.n = completed_videos
                     video_polling_progress.refresh()


            active_video_poll_ids -= completed_in_pass # Remove completed IDs

            if not active_video_poll_ids:
                 logger.info("   ✅ All submitted video jobs appear complete.")
                 break # Exit polling loop

            # Update progress bar description
            elapsed_time_total = (datetime.now() - start_poll_time_video).total_seconds()
            video_polling_progress.set_description(f"Polling Videos ({completed_videos}/{len(video_ids_to_poll)} done | {int(elapsed_time_total)}s)")
            # Wait before next polling cycle
            time.sleep(POLLING_INTERVAL * 2) # Poll videos less frequently

        video_polling_progress.close()
        remaining_ids = len(active_video_poll_ids)
        if remaining_ids > 0:
             logger.warning(f"--- STAGE 2.5: Video polling finished, but {remaining_ids}/{len(video_ids_to_poll)} jobs did not return history within timeout ({overall_video_timeout}s). They might still be running or failed in ComfyUI. ---")
             # Mark remaining as timeout
             for detail in details_for_video:
                  if detail.get('video_prompt_id') in active_video_poll_ids:
                       detail['video_job_status'] = 'polling_timeout'
        else:
             logger.info(f"--- STAGE 2.5: Finished Polling Videos ---")
    else:
         logger.info("\n--- STAGE 2.5: No successful video submissions to poll. ---")


    # ====================================================
    # 🔹 STAGE 3: Cleanup Temp Files
    # ====================================================
    logger.info(f"\n--- STAGE 3: Cleaning up temporary start images... ---")
    try:
        if temp_start_image_dir.exists():
            logger.info(f"Attempting to remove temp directory: {temp_start_image_dir}")
            shutil.rmtree(temp_start_image_dir)
            # Double check removal
            if not temp_start_image_dir.exists():
                logger.info(f"Successfully removed temp start image directory.")
            else:
                 logger.warning(f"shutil.rmtree completed but directory still exists: {temp_start_image_dir}")
        else:
             logger.info("Temp start image directory did not exist (or already cleaned).")
    except PermissionError:
         logger.error(f"Error during temp image cleanup: Permission denied trying to remove {temp_start_image_dir}. Files might be locked.")
    except Exception as e:
        logger.error(f"Error during final temp image cleanup: {e}", exc_info=True)


    # ====================================================
    # 🔹 STAGE 4: Final Summary (Optional)
    # ====================================================
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Automation v5 Run Summary:")
    logger.info(f"   Run Folder (Logs, Approvals): {main_run_folder_path}")
    logger.info(f"   ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")
    logger.info(f"   ComfyUI Run Subfolders: Run_{script_run_timestamp}/all_images, Run_{script_run_timestamp}/all_videos")
    logger.info(f"   Total Prompts Generated: {len(prompts_data)}")
    logger.info(f"   Valid Prompts for Processing: {len(valid_prompts)}")
    logger.info(f"   Image Jobs Submitted: {submitted_image_jobs}")
    completed_files_found = sum(1 for d in run_details if d.get('image_job_status') == 'completed_file_found')
    logger.info(f"   Image Jobs Completed (File Found): {completed_files_found}")
    logger.info(f"   Images Approved for Video: {len(details_for_video)}")
    videos_submitted = sum(1 for d in details_for_video if d.get('video_job_status') == 'submitted' or d.get('video_job_status') == 'completed' or d.get('video_job_status') == 'polling_timeout')
    logger.info(f"   Video Jobs Submitted: {videos_submitted}") # Count submitted/completed/timeout
    videos_completed = sum(1 for d in details_for_video if d.get('video_job_status') == 'completed')
    logger.info(f"   Video Jobs Confirmed Complete (via Polling): {videos_completed}")

    # Save final run details to JSON
    final_details_path = main_run_folder_path / f"run_{script_run_timestamp}_details.json"
    try:
        # Convert Path objects to strings for JSON serialization
        serializable_details = []
        for item in run_details:
            new_item = item.copy()
            if isinstance(new_item.get('generated_image_path'), Path):
                new_item['generated_image_path'] = str(new_item['generated_image_path'])
            serializable_details.append(new_item)

        with open(final_details_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_details, f, indent=2, ensure_ascii=False)
        logger.info(f"   Final run details saved to: {final_details_path}")
    except Exception as e:
        logger.error(f"   Failed to save final run details: {e}")

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation v5 Run Script Finished! {datetime.now()}")
    logger.info(f"   Check ComfyUI console/outputs and the run summary above for status.")
    logger.info("=" * 50)
    print("DEBUG: Script finished.")