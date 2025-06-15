# main_automation_v4.py (Added Video Polling & Fixed Cleanup)
import os
import json
import random
import requests
import time
import shutil
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
try:
    from tqdm import tqdm
    print("DEBUG: tqdm imported successfully.")
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

print("DEBUG: Script execution started.")

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAY = 3
OLLAMA_TIMEOUT = 180
REQUEST_TIMEOUT = 60
POLLING_INTERVAL = 10 # Check history every 10 seconds
POLLING_TIMEOUT_IMAGE = 1800 # 30 minutes per image
POLLING_TIMEOUT_VIDEO = 3600 # 60 minutes per video (adjust as needed)

# --- !! CONFIGURABLE PATHS !! ---
SCRIPT_DIR = Path(__file__).resolve().parent
# !!! USER MUST SET THESE CORRECTLY !!!
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"
# !!! END USER SETTINGS !!!

print(f"DEBUG: Script directory: {SCRIPT_DIR}")

# --- Logging Setup ---
# (Keep same logging setup)
print("DEBUG: Setting up logging...")
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_v4_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8'); file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.DEBUG)
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler); logger.addHandler(console_handler)
print("DEBUG: Logging setup complete.")

# --- Helper Function (Find by Title) ---
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    # (Keep same function)
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("_meta", {}).get("title") == title:
            logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

# --- Configuration Loading ---
def load_config(config_path="config4.json"):
    # (Keep same function, ensures config4.json is used)
    print(f"DEBUG: Entering load_config for '{config_path}'")
    config_path_obj = SCRIPT_DIR / config_path
    try:
        if not config_path_obj.is_file(): logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
        print(f"DEBUG: Config file exists: {config_path_obj}")
        with open(config_path_obj, 'r', encoding='utf-8') as f: config = json.load(f)
        print(f"DEBUG: JSON loaded from {config_path_obj}")
        required = ['api_server_url', 'base_workflow_image', 'base_workflow_video', 'source_faces_path', 'output_folder', 'comfyui_api_url']
        for key in required:
            if key not in config: raise KeyError(key)
        print("DEBUG: Required keys found in config.")
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve()
        print(f"DEBUG: Resolved source_faces_path: {config['source_faces_path']}")
        print(f"DEBUG: Resolved output_folder: {config['output_folder']}")
        if not config['source_faces_path'].is_dir(): logger.warning(f"Source faces dir not found: {config['source_faces_path']}")
        config['output_folder'].mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Output folder ensured: {config['output_folder']}")
        config['comfyui_api_url'] = config['comfyui_api_url'].rstrip('/')
        logger.info(f"Config loaded successfully from {config_path_obj}")
        print(f"DEBUG: Config load successful.")
        return config
    except FileNotFoundError: logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
    except json.JSONDecodeError as e: logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)
    except KeyError as e: logger.critical(f"CRITICAL: Missing required key {e} in config '{config_path}'"); sys.exit(1)
    except Exception as e: logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)

# --- Ollama Prompt Generation ---
# (Keep same generate_prompts_ollama function)
def generate_prompts_ollama(model, num_prompts, ollama_api_url):
    logger.info(f"🚀 Generating {num_prompts} prompts via Ollama (Model: {model}, URL: {ollama_api_url})...")
    backgrounds = [ "bollywood dance floor in a club", "bollywood dance floor in a disco light" ]
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
# (Keep save_prompts_log function as is)
def save_prompts_log(prompt_list):
     if not prompt_list: logger.warning("No prompts generated to save."); return
     timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
     log_folder = SCRIPT_DIR / "logs"
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
# (Keep trigger_generation function as is)
def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None, output_subfolder: str | None, filename_prefix: str, video_start_image: str | None = None):
    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"; payload = {"prompt": prompt, "face": face_filename or "", "output_subfolder": output_subfolder, "filename_prefix_text": filename_prefix}
    if endpoint == "generate_video" and video_start_image: payload["video_start_image_path"] = video_start_image
    log_prefix = f"API Call -> {endpoint}"; logger.info(f"  ➡️ {log_prefix}: Preparing request..."); logger.info(f"     URL: {full_url}"); logger.info(f"     Prompt (start): '{prompt[:70]}...'"); logger.info(f"     Face Filename: '{face_filename or 'None'}'"); logger.info(f"     Output Subfolder: '{output_subfolder or 'None'}'"); logger.info(f"     Filename Prefix: '{filename_prefix}'");
    if video_start_image: logger.info(f"     Video Start Image: '{video_start_image}'")
    logger.debug(f"    Payload Sent: {json.dumps(payload, indent=2)}")
    for attempt in range(1, MAX_API_RETRIES + 1):
        logger.info(f"  🚀 {log_prefix} (Attempt {attempt}/{MAX_API_RETRIES})"); response = None
        try:
            response = requests.post(full_url, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status(); response_data = response.json()
            logger.info(f"  ✅ {log_prefix} submitted successfully (HTTP {response.status_code})"); api_status = response_data.get('status', 'N/A'); api_error = response_data.get('error', None); comfy_prompt_id = response_data.get('prompt_id', 'N/A')
            logger.info(f"     API Server Status: '{api_status}'"); logger.info(f"     ComfyUI Prompt ID: '{comfy_prompt_id}'");
            if api_error: logger.warning(f"     API Server reported error: {api_error}")
            return comfy_prompt_id if api_status == 'submitted' else None
        except requests.exceptions.Timeout: logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): Request timed out after {REQUEST_TIMEOUT} seconds.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): {e}");
            if e.response is not None: response = e.response; logger.warning(f"      Status Code: {e.response.status_code}");
            try: logger.warning(f"      Response Body: {json.dumps(e.response.json(), indent=2)}")
            except json.JSONDecodeError: logger.warning(f"      Response Body (non-JSON): {e.response.text[:500]}...")
            except Exception as inner_log_e: logger.error(f"      Error trying to log response body: {inner_log_e}")
        except json.JSONDecodeError as e:
             logger.error(f"  ❌ Error decoding JSON response from API server (Attempt {attempt}): {e}");
             if response is not None: logger.debug(f"     Raw Response: {response.text[:500]}...")
             else: logger.debug("     No response object available for raw text logging.")
        except Exception as e: logger.error(f"  ❌ Unexpected error calling API (Attempt {attempt}): {e}", exc_info=True)
        if attempt < MAX_API_RETRIES: logger.info(f"      Retrying in {API_RETRY_DELAY} seconds..."); time.sleep(API_RETRY_DELAY)
        else: logger.error(f"  ❌ {log_prefix} failed after {MAX_API_RETRIES} attempts."); return None
    return None

# --- Function to Poll ComfyUI History ---
# (Keep check_comfyui_job_status function as is)
def check_comfyui_job_status(comfyui_base_url: str, prompt_id: str):
    history_url = f"{comfyui_base_url}/history/{prompt_id}"; logger.debug(f"Polling: {history_url}")
    try:
        response = requests.get(history_url, timeout=10); response.raise_for_status(); history_data = response.json()
        if prompt_id in history_data: logger.debug(f"History found for prompt_id {prompt_id}."); return history_data[prompt_id]
        else: logger.debug(f"Prompt_id {prompt_id} not found in history response (running/pending)."); return None
    except requests.exceptions.Timeout: logger.warning(f"Polling /history timed out for {prompt_id}."); return None
    except requests.exceptions.RequestException as e: logger.warning(f"Error polling /history/{prompt_id}: {e}"); return None
    except json.JSONDecodeError as e: logger.warning(f"Error decoding history JSON for {prompt_id}: {e}"); return None


# --- Function to Extract Output Filename from History ---
# (Keep get_output_filename_from_history function as is)
# --- Function to Extract Output Filename from History ---
def get_output_filename_from_history(history_entry: dict, output_node_id: str):
    """Parses history data to find the filename from a specific SaveImage node."""
    if not history_entry or 'outputs' not in history_entry:
        logger.warning(f"History entry invalid or missing 'outputs' key for node {output_node_id}.")
        logger.debug(f"Invalid history entry data: {json.dumps(history_entry, indent=2)}") # Log full entry on error
        return None

    if output_node_id in history_entry['outputs']:
        node_output = history_entry['outputs'][output_node_id]
        # Log the specific node output data we are checking
        logger.debug(f"Outputs found for node {output_node_id}: {json.dumps(node_output, indent=2)}")
        if 'images' in node_output and isinstance(node_output['images'], list) and len(node_output['images']) > 0:
             image_info = node_output['images'][0]
             if 'filename' in image_info and 'subfolder' in image_info and 'type' in image_info and image_info['type'] == 'output':
                 relative_path = Path(image_info['subfolder']) / image_info['filename']
                 logger.debug(f"Extracted relative path from history: {relative_path}")
                 return relative_path
             else:
                 logger.warning(f"Image info dict for node {output_node_id} missing required keys or type is not 'output'. Image Info: {image_info}")
        else:
             logger.warning(f"Node {output_node_id} output found, but 'images' key is missing, not a list, or empty.")
    else:
         logger.warning(f"Node ID {output_node_id} not found in history entry outputs.")
         # Log all available output node IDs for comparison
         logger.debug(f"Available output node IDs in history: {list(history_entry['outputs'].keys())}")

    logger.warning(f"Could not find valid image output for node {output_node_id} in history entry.")
    return None


# --- Main Execution Logic ---
if __name__ == "__main__":
    print("DEBUG: Entering main execution block.")
    logger.info("=" * 50); logger.info(f"Starting Automation v4 Run: {datetime.now()}"); logger.info("=" * 50)

    config = load_config("config4.json");
    if not config: print("DEBUG: Config loading failed. Exiting."); sys.exit(1)
    print("DEBUG: Config loaded successfully in main.")
    API_SERVER_URL = config['api_server_url']
    COMFYUI_BASE_URL = config['comfyui_api_url'] # Base URL for polling
    print(f"DEBUG: API Server URL: {API_SERVER_URL}")
    print(f"DEBUG: ComfyUI Base URL: {COMFYUI_BASE_URL}")

    # --- Determine ComfyUI Base Output Directory (CRUCIAL) ---
    COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content") # <<< USER MUST SET THIS CORRECTLY
    logger.info(f"Assuming ComfyUI base output directory: {COMFYUI_OUTPUT_DIR_BASE}")
    if not COMFYUI_OUTPUT_DIR_BASE.is_dir(): logger.error(f"Configured ComfyUI output directory does not exist: {COMFYUI_OUTPUT_DIR_BASE}")

    # --- Setup Temp Dir for Video Start Images ---
    if not COMFYUI_INPUT_DIR_BASE.is_dir(): logger.critical(f"ComfyUI input dir not found! Path: {COMFYUI_INPUT_DIR_BASE}"); sys.exit(1)
    temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    temp_start_image_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using temporary directory for video start images: {temp_start_image_dir}")

    # 1. Generate Prompts
    # (Keep prompt gen)
    print("DEBUG: Starting prompt generation...")
    prompts_data = generate_prompts_ollama( config["ollama_model"], config["num_prompts"], config.get("ollama_api_url", "http://localhost:11434/api/generate") )
    print(f"DEBUG: Prompt generation finished. Got {len(prompts_data)} results.")
    save_prompts_log(prompts_data)
    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts: logger.critical("No valid prompts generated."); print("DEBUG: No valid prompts found."); sys.exit(1)
    logger.info(f"Proceeding with {len(valid_prompts)} valid prompts.")
    print(f"DEBUG: Proceeding with {len(valid_prompts)} valid prompts.")

    # 2. Prepare Faces List
    # (Keep face list prep)
    print("DEBUG: Preparing faces list...")
    face_files = []; source_faces_dir = config['source_faces_path']
    if source_faces_dir.is_dir(): face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
    logger.info(f"Found {len(face_files)} face images.")
    if not face_files: logger.warning("No valid face images found. Face swap will be skipped.")
    print(f"DEBUG: Found {len(face_files)} face files.")

    # 3. Create ONE Root Output Directory name
    print("DEBUG: Defining main run folder name...")
    script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_parent_folder = config['output_folder']
    main_run_folder_name = f"Run_{script_run_timestamp}"
    logger.info(f"Run Identifier (used for subfolders): {main_run_folder_name}")
    logger.info(f"Script output log parent directory: {run_parent_folder}")
    print(f"DEBUG: Run Identifier: {main_run_folder_name}")

    # --- Store details for tracking ---
    run_details = []

    # --- Need the Node ID of the SaveImage node in the IMAGE workflow ---
    image_save_node_id = None
    image_save_node_title = "API_Image_Output_SaveNode"
    try:
        img_workflow_path_from_config = (SCRIPT_DIR / config["base_workflow_image"]).resolve()
        logger.debug(f"Checking for Save Node in: {img_workflow_path_from_config}")
        if not img_workflow_path_from_config.is_file(): logger.error(f"Image workflow path from config not found: {img_workflow_path_from_config}")
        else:
             with open(img_workflow_path_from_config, "r", encoding="utf-8") as f: temp_img_wf = json.load(f)
             image_save_node_id = find_node_id_by_title(temp_img_wf, image_save_node_title, img_workflow_path_from_config.name) # Call defined function
             if not image_save_node_id: logger.error(f"Could not find node titled '{image_save_node_title}' in image workflow '{img_workflow_path_from_config.name}'! Cannot track output files.")
             else: logger.info(f"Found Image Save Node '{image_save_node_title}' with ID: {image_save_node_id}")
    except Exception as e: logger.error(f"Error finding SaveImage node ID in image workflow: {e}", exc_info=True)


    # ====================================================
    # 🔹 STAGE 1: Submit Image Generation Jobs
    # ====================================================
    logger.info(f"\n--- STAGE 1: Submitting Image Generation for {len(valid_prompts)} Prompts ---")
    print(f"DEBUG: Starting image submission loop for {len(valid_prompts)} prompts.")
    image_progress_bar = tqdm(valid_prompts, desc="Submitting Images")
    for item_index, item in enumerate(image_progress_bar):
        print(f"DEBUG: Processing item index {item_index}")
        idx = item["index"]
        prompt = item["generated_prompt"]
        selected_face_path = random.choice(face_files) if face_files else None
        face_filename_only = selected_face_path.name if selected_face_path else None

        image_output_subfolder = f"{main_run_folder_name}/all_images"
        image_filename_prefix = f"{idx:03d}_{'swapped' if face_filename_only else 'raw'}"

        image_progress_bar.set_description(f"Image Req {idx}/{len(valid_prompts)}")
        logger.info(f"\n🖼️ Preparing Image Request [{idx}/{len(valid_prompts)}]")
        print(f"DEBUG: Calling trigger_generation for image {idx}...")

        comfy_prompt_id = trigger_generation(
            API_SERVER_URL, "generate_image", prompt, face_filename_only,
            image_output_subfolder, image_filename_prefix
        )
        print(f"DEBUG: trigger_generation for image {idx} returned prompt_id: {comfy_prompt_id}")

        run_details.append({
            'index': idx, 'prompt': prompt, 'face_filename': face_filename_only,
            'image_prefix': image_filename_prefix,
            'video_prefix': f"{idx:03d}_video_{'swapped' if face_filename_only else 'raw'}",
            'image_prompt_id': comfy_prompt_id,
            'generated_image_path': None,
            'temp_start_image_comfy_path': None,
            'image_job_submitted': bool(comfy_prompt_id)
        })

        if not comfy_prompt_id: logger.error(f"Failed API call for Image {idx}.")
        time.sleep(0.5)

    logger.info(f"--- STAGE 1: All Image Generation Requests Submitted ---")


    # ========================================================
    # 🔹 STAGE 1.5: Wait for Image Jobs to Complete (Polling)
    # ========================================================
    if not image_save_node_id:
        logger.error("Cannot proceed to polling stage: Image Save Node ID ('API_Image_Output_SaveNode') not found in workflow JSON. Check title.")
    else:
        logger.info(f"\n--- STAGE 1.5: Waiting for Image Jobs to Complete (Polling /history) ---")
        polling_progress = tqdm(total=len(run_details), desc="Polling Images")
        for details in run_details:
            idx = details['index']
            prompt_id = details['image_prompt_id']
            if not prompt_id:
                logger.warning(f"Polling skipped for Image {idx}: No prompt_id (submission likely failed).")
                polling_progress.update(1)
                continue

            logger.info(f"   Polling for Image {idx} (Prompt ID: {prompt_id})...")
            start_time = datetime.now()
            job_done = False
            while datetime.now() - start_time < timedelta(seconds=POLLING_TIMEOUT_IMAGE): # Use image timeout
                history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
                if history_data:
                    logger.info(f"   ✅ Image {idx} completed.")
                    relative_output_path = get_output_filename_from_history(history_data, image_save_node_id)
                    if relative_output_path:
                        full_output_path = COMFYUI_OUTPUT_DIR_BASE / relative_output_path
                        details['generated_image_path'] = full_output_path
                        logger.info(f"      Found output file: {full_output_path}")
                    else:
                        logger.error(f"      Image {idx} finished, but could not find output filename in history for node {image_save_node_id}!")
                    job_done = True
                    break
                else:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    polling_progress.set_description(f"Polling Img {idx} ({int(elapsed_time)}s)")
                    time.sleep(POLLING_INTERVAL)

            if not job_done:
                 logger.error(f"   ❌ Polling timed out for Image {idx} (Prompt ID: {prompt_id}) after {POLLING_TIMEOUT_IMAGE} seconds.")
            polling_progress.update(1)
        polling_progress.close()
        logger.info(f"--- STAGE 1.5: Finished Polling Images ---")


    # ====================================================
    # 🔹 STAGE 2: Submit Video Generation Jobs
    # ====================================================
    logger.info(f"\n--- STAGE 2: Submitting Video Generation ---")
    print(f"DEBUG: Starting video submission loop for {len(run_details)} items.")
    video_progress_bar = tqdm(run_details, desc="Submitting Videos")
    items_to_process_video = 0
    items_successfully_submitted_video = 0
    all_video_prompt_ids = [] # Store video prompt IDs for final polling

    for details in video_progress_bar:
        idx = details["index"]
        if not details['image_prompt_id'] or not details['generated_image_path']:
            logger.warning(f"Skipping video for index {idx}: Image submission failed or output path not found.")
            continue

        items_to_process_video += 1
        prompt = details["prompt"]
        face_filename_only = details["face_filename"]
        video_filename_prefix = details["video_prefix"]
        generated_image_path = details["generated_image_path"] # Full path from polling

        video_output_subfolder = f"{main_run_folder_name}/all_videos"
        video_progress_bar.set_description(f"Video Req {idx}/{len(run_details)}")
        logger.info(f"\n🎬 Preparing Video Request [{idx}/{len(run_details)}]")
        print(f"DEBUG: Calling trigger_generation for video {idx}...")

        # --- Copy Generated Image to be Video Start Frame ---
        temp_start_image_comfy_path_str = None
        if generated_image_path and generated_image_path.is_file():
            try:
                temp_start_filename = f"start_{idx:03d}_{datetime.now().strftime('%H%M%S%f')}{generated_image_path.suffix}"
                temp_dest_path = temp_start_image_dir / temp_start_filename
                shutil.copyfile(generated_image_path, temp_dest_path)
                temp_start_image_comfy_path_str = (Path(TEMP_VIDEO_START_SUBDIR) / temp_start_filename).as_posix()
                details['temp_start_image_comfy_path'] = temp_start_image_comfy_path_str # Store for cleanup
                logger.info(f"   Copied '{generated_image_path.name}' -> Comfy Input as '{temp_start_image_comfy_path_str}'")
            except Exception as copy_e:
                logger.error(f"   Failed to copy image '{generated_image_path}' to temp dir: {copy_e}. Video will use default start.")
                temp_start_image_comfy_path_str = None
        else:
            logger.warning(f"   Generated image file not found or path invalid: '{generated_image_path}'. Video will use default start.")
            temp_start_image_comfy_path_str = None

        # Call API Server - Video Endpoint
        comfy_video_prompt_id = trigger_generation(
            API_SERVER_URL,
            "generate_video",
            prompt,
            face_filename_only,
            video_output_subfolder,
            video_filename_prefix,
            video_start_image=temp_start_image_comfy_path_str # Pass the temp path
        )
        print(f"DEBUG: trigger_generation for video {idx} returned prompt_id: {comfy_video_prompt_id}")

        if comfy_video_prompt_id:
             items_successfully_submitted_video += 1
             all_video_prompt_ids.append(comfy_video_prompt_id) # Store ID for final wait
        else:
             logger.error(f"Failed API call for Video {idx}.")
        time.sleep(0.5)

    logger.info(f"--- STAGE 2: {items_successfully_submitted_video}/{items_to_process_video} Video Generation Requests Submitted ---")
    print("DEBUG: Finished video submission loop.")

    # ========================================================
    # 🔹 STAGE 2.5: Wait for Video Jobs to Complete (Optional but Recommended)
    # ========================================================
    if all_video_prompt_ids:
        logger.info(f"\n--- STAGE 2.5: Waiting for {len(all_video_prompt_ids)} Video Jobs to Complete (Polling /history) ---")
        video_polling_progress = tqdm(total=len(all_video_prompt_ids), desc="Polling Videos")
        completed_videos = 0
        start_poll_time_video = datetime.now()
        # Keep polling until all submitted video jobs are found in history or overall timeout
        while completed_videos < len(all_video_prompt_ids) and \
              datetime.now() - start_poll_time_video < timedelta(seconds=POLLING_TIMEOUT_VIDEO * len(all_video_prompt_ids)): # Overall timeout

            all_done = True # Assume done until proven otherwise
            for prompt_id in all_video_prompt_ids:
                 # Check only if we haven't confirmed this one yet
                 # (Requires tracking completion status per ID, simplified here: check all each time)
                 history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
                 if not history_data:
                     all_done = False # At least one job is not finished
                     break # No need to check others in this pass

            if all_done:
                 logger.info("   ✅ All submitted video jobs appear complete.")
                 # Update progress bar fully if loop finishes early
                 video_polling_progress.n = len(all_video_prompt_ids)
                 video_polling_progress.refresh()
                 break # Exit polling loop

            # Update progress bar based on current completed count (more accurate way needed)
            # video_polling_progress.n = completed_videos
            # video_polling_progress.refresh()

            elapsed_time_total = (datetime.now() - start_poll_time_video).total_seconds()
            video_polling_progress.set_description(f"Polling Videos ({int(elapsed_time_total)}s)")
            time.sleep(POLLING_INTERVAL * 2) # Poll videos less frequently

        video_polling_progress.close()
        if completed_videos < len(all_video_prompt_ids):
             logger.warning(f"--- STAGE 2.5: Video polling finished, but only {completed_videos}/{len(all_video_prompt_ids)} jobs confirmed complete (may have timed out or some failed in ComfyUI). ---")
        else:
             logger.info(f"--- STAGE 2.5: Finished Polling Videos ---")
    else:
         logger.info("--- STAGE 2.5: No successful video submissions to poll. ---")


    # ====================================================
    # 🔹 STAGE 3: Cleanup Temp Files
    # ====================================================
    # Now this runs *after* polling for video completion (or timeout)
    logger.info(f"\n--- STAGE 3: Cleaning up temporary start images... ---")
    try:
        if temp_start_image_dir.exists():
            shutil.rmtree(temp_start_image_dir)
            logger.info(f"Removed temp start image directory: {temp_start_image_dir}")
        else:
             logger.info("Temp start image directory did not exist (or already cleaned).")
    except Exception as e:
        logger.error(f"Error during final temp image cleanup: {e}")


    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation v4 Run Script Finished! {datetime.now()}")
    logger.info(f"   Check ComfyUI console for final processing status.")
    # Use the path constructed earlier
    final_output_location = COMFYUI_OUTPUT_DIR_BASE / main_run_folder_name
    logger.info(f"   Outputs located in: {final_output_location}")
    logger.info("=" * 50)
    print("DEBUG: Script finished.")