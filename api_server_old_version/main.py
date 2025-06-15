import os
import json
import random
import requests
import time
import shutil
import logging
import sys
from datetime import datetime
from pathlib import Path
from tqdm import tqdm # For progress bar, ensure it's installed: pip install tqdm

# --- Constants ---
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between ComfyUI API retries
OLLAMA_RETRY_DELAY = 3 # seconds between Ollama retries
OLLAMA_TIMEOUT = 180 # Increased timeout for Ollama
COMFYUI_TIMEOUT = 300 # seconds for ComfyUI API call

# --- !! CONFIGURABLE PATHS !! ---
# Define ComfyUI base directory relative to the script or use absolute
# Adjust these paths if your structure is different!
SCRIPT_DIR = Path(__file__).resolve().parent # Directory where main.py lives
COMFYUI_BASE_DIR = Path("D:/Comfy_UI_V20/ComfyUI") # Path to the main ComfyUI directory
COMFYUI_INPUT_DIR = COMFYUI_BASE_DIR / "input"
COMFYUI_OUTPUT_DIR_NODE = "output" # Default ComfyUI output dir for SaveImage nodes
TEMP_FACE_SUBDIR = "temp_faces_automation" # Subdirectory within ComfyUI's input folder for temp faces

# --- Logging Setup ---
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Use INFO, change to DEBUG for excessive detail
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
else:
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# --- Configuration Loading ---
def load_config(config_path="config.json"):
    config_path_obj = SCRIPT_DIR / config_path
    try:
        if not config_path_obj.is_file():
            logger.critical(f"CRITICAL: Config file not found: {config_path_obj}")
            sys.exit(1)
        with open(config_path_obj, 'r', encoding='utf-8') as f: config = json.load(f)
        logger.info(f"Config loaded from {config_path_obj}")

        # Resolve paths relative to the script directory for robustness
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve() # Where this script saves organized output
        config['base_workflow_image'] = (SCRIPT_DIR / config['base_workflow_image']).resolve()
        config['base_workflow_video'] = (SCRIPT_DIR / config['base_workflow_video']).resolve()

        # Validation
        if not config['source_faces_path'].is_dir(): logger.warning(f"Source faces dir not found: {config['source_faces_path']}")
        if not config['base_workflow_image'].is_file(): logger.error(f"Image workflow not found: {config['base_workflow_image']}")
        if not config['base_workflow_video'].is_file(): logger.error(f"Video workflow not found: {config['base_workflow_video']}")
        config['output_folder'].mkdir(parents=True, exist_ok=True) # Ensure script's output folder exists
        if not COMFYUI_INPUT_DIR.is_dir(): logger.error(f"ComfyUI input directory not found: {COMFYUI_INPUT_DIR}. Cannot copy faces.")

        return config
    except Exception as e:
        logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True)
        sys.exit(1)

# --- Folder Creation ---
def create_output_folders(output_root, background):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_background = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in background)
    run_folder = output_root / f"{safe_background}_{timestamp}"
    # Subfolders are determined by the FileNamePrefix node's custom_directory now
    # We only create the main run folder here.
    try:
        run_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created base output directory for run: {run_folder}")
        return run_folder
    except OSError as e:
        logger.error(f"Failed to create base output directory {run_folder}: {e}")
        return None

# --- Ollama Prompt Generation ---
def generate_prompts_ollama(model, num_prompts, ollama_api_url="http://localhost:11434/api/generate"):
    logger.info(f"🚀 Generating {num_prompts} prompts via Ollama (Model: {model})...")
    backgrounds = ["night club dance floor", "lush enchanted garden", "futuristic neon stage", "sun-drenched tropical beach", "grungy urban alleyway", "opulent ballroom", "serene mountain top"]
    generated_prompt_list = []
    for i in range(num_prompts):
        background = random.choice(backgrounds)
        base_scene_idea = ( f"A stunning young woman with a short, revealing dress and noticeable curves, dancing energetically in/on a {background}. She is the main focus, close to the camera. Other dancers are visible but less distinct in the background. Capture a vibrant, dynamic, cinematic atmosphere." )
        formatted_prompt = f"""You are an expert AI Prompt Engineer. Rewrite the following scene description into ONE single-line, highly detailed, and evocative cinematic prompt suitable for AI image/video generation. Focus on visual elements: lighting, camera angle, composition, mood, style, and specific details about the subject and environment. ⚠️ IMPORTANT: Your response MUST be ONLY a valid JSON object in the following exact format. Do NOT include any explanations, apologies, commentary, markdown formatting, or any text outside the JSON structure.\n\n{{ "prompts": ["<your single-line cinematic prompt here>"] }}\n\nScene Description:\n{base_scene_idea}"""
        logger.info(f"\n🧠 Requesting Prompt [{i+1}/{num_prompts}] | Background: {background}")
        for attempt in range(MAX_RETRIES):
            logger.debug(f"   Ollama Attempt {attempt+1}/{MAX_RETRIES}...")
            try:
                response = requests.post(ollama_api_url, json={"model": model, "prompt": formatted_prompt, "stream": True}, stream=True, timeout=OLLAMA_TIMEOUT)
                response.raise_for_status()
                full_output_text = ""
                print("   Ollama generating: ", end="")
                for line in response.iter_lines():
                    if line:
                        try: chunk = json.loads(line.decode("utf-8")); token = chunk.get("response", ""); print(token, end="", flush=True); full_output_text += token
                        except: pass # Ignore potential non-JSON lines/errors during streaming
                print() # Newline after streaming finishes
                # Attempt to find and parse the JSON within the potentially messy output
                start_index = full_output_text.find('{')
                end_index = full_output_text.rfind('}') + 1
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_str = full_output_text[start_index:end_index]
                    parsed = json.loads(json_str)
                    if "prompts" in parsed and isinstance(parsed["prompts"], list) and len(parsed["prompts"]) > 0:
                        prompt_text = parsed["prompts"][0].strip()
                        if prompt_text:
                            logger.info(f"   ✅ Clean Prompt Extracted: {prompt_text}")
                            generated_prompt_list.append({"index": i + 1, "background": background, "base_scene_idea": base_scene_idea, "generated_prompt": prompt_text})
                            break # Success, exit retry loop
                        else:
                            raise ValueError("Empty prompt string found in JSON")
                    else:
                        raise ValueError("Invalid JSON structure ('prompts' key missing or not a list)")
                else:
                    raise ValueError("JSON boundaries '{}' not found in Ollama response")
            except json.JSONDecodeError as json_e:
                logger.warning(f"   ❌ Error decoding JSON from Ollama (Attempt {attempt+1}): {json_e}")
                logger.debug(f"      Full Ollama response text: {full_output_text}")
            except Exception as e:
                logger.warning(f"   ❌ Error processing Ollama (Attempt {attempt+1}): {e}")

            # If loop didn't break (meaning error occurred)
            if attempt < MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)
                logger.info(f"      Retrying Ollama...")
            else:
                logger.error(f"   ❌ Failed to generate prompt [{i+1}] after {MAX_RETRIES} attempts.")
                generated_prompt_list.append({"index": i + 1, "background": background, "error": str(e)}) # Log error for this prompt
    logger.info(f"✅ Finished generating {len([p for p in generated_prompt_list if 'error' not in p])} prompts successfully.")
    return generated_prompt_list


# --- Prompt Logging ---
def save_prompts_log(prompt_list):
    if not prompt_list: logger.warning("No prompts generated to save."); return
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_folder = SCRIPT_DIR / "logs"
    json_path = log_folder / f"generated_prompts_{timestamp_str}.json"
    txt_path = log_folder / f"generated_prompts_{timestamp_str}.txt"
    try: # Save JSON
        with open(json_path, "w", encoding="utf-8") as f: json.dump(prompt_list, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Full prompt data saved to: {json_path}")
    except Exception as e: logger.error(f"Failed to save prompts JSON: {e}")
    try: # Save TXT
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Generated Prompts - {timestamp_str}\n" + "="*30 + "\n\n")
            for item in prompt_list:
                 prompt_text = item.get("generated_prompt"); error_text = item.get("error")
                 f.write(f"{item['index']:02d}. [Background: {item['background']}]\n");
                 if prompt_text: f.write(f"   Prompt: {prompt_text}\n\n")
                 elif error_text: f.write(f"   Error: {error_text}\n\n")
                 else: f.write("   Status: Unknown (No prompt or error)\n\n") # Should not happen
        logger.info(f"📝 Clean prompts saved to: {txt_path}")
    except Exception as e: logger.error(f"Failed to save prompts TXT: {e}")

# --- ComfyUI Interaction (Updated Version) ---
def run_comfyui(prompt, face_path: Path, base_workflow_path: Path, run_output_dir: Path, mode, idx, comfyui_api_url, script_output_root_path: Path):
    """Loads, prepares, copies face, sends workflow, handles paths, and cleans up."""
    prepared_workflow_json = None
    log_folder = SCRIPT_DIR / "logs"
    temp_face_comfy_relative_path = None
    temp_face_dest_abs = None

    try:
        # --- 0. Prepare Temp Face ---
        if face_path and face_path.is_file():
            try:
                temp_face_dir_abs = COMFYUI_INPUT_DIR / TEMP_FACE_SUBDIR
                temp_face_dir_abs.mkdir(parents=True, exist_ok=True)
                # Use a more unique name to avoid potential collisions if runs are very fast
                unique_face_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{face_path.name}"
                temp_face_dest_abs = temp_face_dir_abs / unique_face_name
                shutil.copyfile(face_path, temp_face_dest_abs)
                # Ensure forward slashes for ComfyUI path, relative to input dir
                temp_face_comfy_relative_path = f"{TEMP_FACE_SUBDIR}/{unique_face_name}".replace("\\", "/")
                logger.info(f"[{idx}] Copied face '{face_path.name}' -> Comfy Input: '{temp_face_comfy_relative_path}'")
            except Exception as copy_e:
                 logger.error(f"[{idx}] Failed to copy face image: {copy_e}", exc_info=True)
                 # Don't raise immediately, allow generation without face swap if copy fails
                 temp_face_comfy_relative_path = None
                 face_path = None # Ensure we don't try to use it later
                 logger.warning(f"[{idx}] Proceeding without face swap due to copy error.")
        elif face_path: # Log if path was provided but invalid
             logger.error(f"[{idx}] Invalid face path provided: {face_path}. Skipping face swap.")
             temp_face_comfy_relative_path = None
             face_path = None
        else: # No face path provided
            logger.info(f"[{idx}] No face path provided for {mode}. Skipping face swap.")
            temp_face_comfy_relative_path = None # Ensure it's None

        # --- 1. Load Base Workflow ---
        logger.debug(f"[{idx}] Loading base workflow: {base_workflow_path.name}")
        if not base_workflow_path.is_file(): raise FileNotFoundError(f"Workflow not found: {base_workflow_path}")
        with open(base_workflow_path, "r", encoding="utf-8") as f: workflow = json.load(f)

        # --- 2. Find Required Nodes ---
        text_node_id, face_node_id, output_node_id = None, None, None
        output_node_ids = {} # Store different prefix nodes if they exist (mainly for image workflow)
        face_node_target_title = "Load Face Image" # <<< Title given to the specific LoadImage node for faces

        logger.debug(f"[{idx}] Searching for nodes in {base_workflow_path.name}...")
        for node_id, node_data in workflow.items():
            ct = node_data.get("class_type")
            meta_title = node_data.get("_meta", {}).get("title", "")

            # Find Text Node
            if ct == "Text Multiline" and not text_node_id:
                text_node_id = node_id
                logger.debug(f"[{idx}] Found Text node: {text_node_id} (Title: '{meta_title}')")

            # --- MODIFIED FACE NODE FINDING ---
            # Prioritize finding the node with the specific title
            if ct == "LoadImage" and meta_title == face_node_target_title and not face_node_id:
                face_node_id = node_id
                logger.debug(f"[{idx}] Found specific Face LoadImage node by title '{face_node_target_title}': {face_node_id}")
            # --- END MODIFIED FACE NODE FINDING ---

            # Find FileNamePrefix Node(s)
            if ct == "FileNamePrefix":
                if "Swapped" in meta_title and "swapped" not in output_node_ids:
                    output_node_ids["swapped"] = node_id
                    logger.debug(f"[{idx}] Found Output FileNamePrefix (Swapped): {node_id} (Title: '{meta_title}')")
                elif "raw" not in output_node_ids and "Raw" in meta_title: # Check title more reliably
                     output_node_ids["raw"] = node_id
                     logger.debug(f"[{idx}] Found Output FileNamePrefix (Raw): {node_id} (Title: '{meta_title}')")
                # General fallback if specific titles aren't found or needed (like in video)
                if not output_node_id:
                     output_node_id = node_id # Store the first one found as a fallback
                     logger.debug(f"[{idx}] Found generic FileNamePrefix node: {node_id} (Title: '{meta_title}')")

        # --- Fallback for Face Node (If specific title not found but face exists) ---
        if temp_face_comfy_relative_path and not face_node_id:
            logger.warning(f"[{idx}] Specific face node '{face_node_target_title}' not found in {base_workflow_path.name}. Searching for *first* LoadImage as fallback.")
            for node_id, node_data in workflow.items():
                if node_data.get("class_type") == "LoadImage":
                    face_node_id = node_id
                    logger.warning(f"[{idx}] Using first found LoadImage node as fallback: {face_node_id} (Title: '{node_data.get('_meta', {}).get('title', '')}')")
                    break # Use the first one found

        # --- Select the correct Output Node based on mode and findings ---
        # This logic primarily helps the IMAGE workflow distinguish saves. Video might just use the fallback.
        if "Image Gen" in mode: # Check if it's the image workflow
            if "swapped" in output_node_ids: # Prefer the specifically named swapped node if available
                 output_node_id = output_node_ids["swapped"]
                 logger.debug(f"[{idx}] Selected 'swapped' output node for Image Gen: {output_node_id}")
            # If not swapping or swapped node not found, try to find 'raw' for the image workflow
            elif "raw" in output_node_ids:
                 output_node_id = output_node_ids["raw"]
                 logger.debug(f"[{idx}] Selected 'raw' output node for Image Gen: {output_node_id}")
            # Else use the fallback (first found FileNamePrefix)
            else:
                logger.debug(f"[{idx}] Using fallback output node for Image Gen: {output_node_id}")
        elif "Video Gen" in mode: # For video, usually just one output prefix is controlled
            # Use the first FileNamePrefix found during the initial loop (stored in output_node_id)
             logger.debug(f"[{idx}] Using first found/fallback output node for Video Gen: {output_node_id}")
        # If mode is unclear or no specific nodes found, stick with the fallback
        else:
             logger.debug(f"[{idx}] Using fallback output node for mode '{mode}': {output_node_id}")


        # --- 3. Validate Nodes Found ---
        if not text_node_id: raise ValueError(f"Missing 'Text Multiline' node in {base_workflow_path.name}")
        # Only raise error if face swap was intended but node is missing
        if temp_face_comfy_relative_path and not face_node_id:
            raise ValueError(f"Face path provided, but failed to find suitable 'LoadImage' node (tried title '{face_node_target_title}' and fallback) in {base_workflow_path.name}")
        if not output_node_id: raise ValueError(f"Missing 'FileNamePrefix' node in {base_workflow_path.name}")

        # --- 4. Inject Data ---
        logger.debug(f"[{idx}] Injecting prompt into Text Node {text_node_id}")
        workflow[text_node_id]["inputs"]["text"] = prompt

        injected_face_path_value = "NOT_APPLICABLE"
        if face_node_id and temp_face_comfy_relative_path:
            workflow[face_node_id]["inputs"]["image"] = temp_face_comfy_relative_path
            # Some LoadImage nodes might need type set explicitly if using API format
            # workflow[face_node_id]["inputs"]["type"] = "input"
            injected_face_path_value = temp_face_comfy_relative_path
            logger.debug(f"[{idx}] Injected face path '{injected_face_path_value}' into Face Node {face_node_id}")
        elif face_node_id:
             logger.warning(f"[{idx}] Face LoadImage node ({face_node_id}) exists, but no face available or copy failed for {mode}.")
             # Log the existing value in the node for debugging
             injected_face_path_value = workflow[face_node_id]["inputs"].get("image", "DEFAULT_OR_MISSING")
             logger.debug(f"[{idx}] Face Node {face_node_id} existing image value: '{injected_face_path_value}'")


        # Calculate relative path for ComfyUI FileNamePrefix custom_directory
        # The path should be relative TO the ComfyUI output directory BASE
        # Example: If script output is D:\proj\output\run_1 and ComfyUI output is D:\ComfyUI\output
        # And we want ComfyUI to save to D:\ComfyUI\output\run_1\raw_images
        # The custom_directory should be '..\..\proj\output\run_1\raw_images' relative to Comfy output
        # OR simpler: use an absolute path for custom_directory if supported, OR use path relative to script output root

        # Let's try making it relative to the *script's* overall output folder structure
        # Assumes ComfyUI is configured to save files where specified relative paths work from its base output dir
        # Or that FileNamePrefix node handles this intelligently.
        # Simplification: Use the run_output_dir name directly, assuming ComfyUI output structure matches.
        # This relies on FileNamePrefix node properly handling the path relative to ComfyUI's base output.
        # Example: If run_output_dir is 'cool_run_123', ComfyUI saves to '<ComfyUI_Output>/cool_run_123/...'
        try:
            # Get the final directory name created by create_output_folders
            run_folder_name = run_output_dir.name
            # Determine subpath based on mode (this is a heuristic, depends on workflow node connections)
            sub_path = ""
            if "Image Gen" in mode:
                if output_node_id in output_node_ids.get("swapped", ""): sub_path = "faceswapped_images"
                elif output_node_id in output_node_ids.get("raw", ""): sub_path = "raw_images"
                else: sub_path = "images" # Default if unsure
            elif "Video Gen" in mode:
                 # Assume video workflow saves to a video subfolder if using the injected prefix
                 sub_path = "faceswapped_videos" if face_node_id and temp_face_comfy_relative_path else "raw_videos"
            else:
                 sub_path = "unknown_output"

            # Combine the run folder name and the determined sub-path
            comfy_custom_dir = f"{run_folder_name}/{sub_path}".replace("\\", "/")
            logger.debug(f"[{idx}] Determined ComfyUI custom_directory target: '{comfy_custom_dir}' (based on run folder '{run_folder_name}' and sub-path '{sub_path}')")

        except Exception as path_e:
            logger.warning(f"Error calculating custom directory path: {path_e}. Using fallback.")
            comfy_custom_dir = run_output_dir.name # Fallback to just the run folder name

        logger.debug(f"[{idx}] Injecting custom_directory '{comfy_custom_dir}' into Output Node {output_node_id}")
        workflow[output_node_id]["inputs"]["custom_directory"] = comfy_custom_dir

        # Set prefix text based on whether face swap happened (useful for organizing files)
        prefix_text = workflow[output_node_id]["inputs"].get("custom_text", "") # Get existing prefix if any
        if face_node_id and temp_face_comfy_relative_path:
             if "swapped" not in prefix_text.lower() : prefix_text = f"swapped_{prefix_text}"
        else:
             if "raw" not in prefix_text.lower() : prefix_text = f"raw_{prefix_text}"

        # Clean up potential double underscores or trailing underscores
        prefix_text = prefix_text.replace("__", "_").strip("_")
        workflow[output_node_id]["inputs"]["custom_text"] = prefix_text
        logger.debug(f"[{idx}] Setting custom_text in Output Node {output_node_id} to: '{prefix_text}'")

        prepared_workflow_json = {"prompt": workflow}

        # --- 5. Send to ComfyUI API ---
        api_call_successful = False
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"  🚀 Sending to ComfyUI -> {mode} [{idx}] (Attempt {attempt}/{MAX_RETRIES})")
            try:
                # Log payload size for debugging large workflows
                payload_size = len(json.dumps(prepared_workflow_json))
                logger.debug(f"      Payload size: {payload_size / 1024:.2f} KB")
                if payload_size > 5 * 1024 * 1024: # Warn if > 5MB
                    logger.warning(f"      Payload size is large ({payload_size / 1024:.2f} KB). This might cause issues.")

                response = requests.post(comfyui_api_url, json=prepared_workflow_json, timeout=COMFYUI_TIMEOUT)
                response.raise_for_status()
                logger.info(f"  ✅ {mode} [{idx}] workflow sent successfully (HTTP {response.status_code}).")
                api_call_successful = True
                break # Exit retry loop on success
            except requests.exceptions.Timeout:
                logger.warning(f"  ⚠️ ComfyUI API Error ({mode} [{idx}], Attempt {attempt}): Request timed out after {COMFYUI_TIMEOUT} seconds.")
            except requests.exceptions.RequestException as e:
                logger.warning(f"  ⚠️ ComfyUI API Error ({mode} [{idx}], Attempt {attempt}): {e}")
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                     status_code = e.response.status_code
                     logger.warning(f"      Received HTTP {status_code} from ComfyUI.")
                     # Log response body for common errors like 400 or 500
                     if status_code in [400, 500]:
                         error_payload_file = log_folder / f"failed_payload_{mode}_{idx}_attempt_{attempt}_{datetime.now():%Y%m%d%H%M%S}.json"
                         logger.error(f"      🔥 ComfyUI HTTP {status_code}. Saving payload to: {error_payload_file}")
                         try:
                             with open(error_payload_file, "w", encoding="utf-8") as f_err: json.dump(prepared_workflow_json, f_err, indent=2)
                         except Exception as log_e: logger.error(f"      Failed to save error payload: {log_e}")
                         try:
                             error_details = e.response.json()
                             logger.error(f"      ComfyUI Response Body (JSON): {json.dumps(error_details, indent=2)}")
                         except json.JSONDecodeError:
                             logger.error(f"      ComfyUI Response Body (non-JSON): {e.response.text[:1500]}...") # Limit log size
            # Retry logic
            if attempt < MAX_RETRIES:
                logger.info(f"      Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"  ❌ {mode} [{idx}] failed after {MAX_RETRIES} attempts.")

        return api_call_successful # Return True if any attempt succeeded

    except FileNotFoundError as e: logger.error(f"❌ Workflow file error for {mode} [{idx}]: {e}"); return False
    except ValueError as e: logger.error(f"❌ Workflow prep error for {mode} [{idx}]: {e}"); return False
    except Exception as e: logger.error(f"❌ Unexpected error during ComfyUI run for {mode} [{idx}]: {e}", exc_info=True); return False
    finally:
        # --- 6. Clean Up Temp Face ---
        if temp_face_comfy_relative_path and temp_face_dest_abs and temp_face_dest_abs.is_file():
             try:
                 logger.debug(f"[{idx}] Cleaning up temp face: {temp_face_dest_abs}")
                 os.remove(temp_face_dest_abs)
             except OSError as rm_e:
                 logger.warning(f"[{idx}] Could not delete temp face file {temp_face_dest_abs}: {rm_e}")

# --- Main Execution Logic ---
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info(f"Starting Automation Run: {datetime.now()}")
    logger.info("=" * 50)

    config = load_config()
    if not config:
        logger.critical("Exiting due to configuration loading failure.")
        sys.exit(1)

    prompts_data = generate_prompts_ollama( config["ollama_model"], config["num_prompts"], config.get("ollama_api_url", "http://localhost:11434/api/generate") )
    save_prompts_log(prompts_data)

    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts:
        logger.error("No valid prompts were generated by Ollama. Exiting.")
        sys.exit(1)
    logger.info(f"Successfully generated {len(valid_prompts)} valid prompts.")


    face_files = []
    source_faces_dir = config['source_faces_path']
    if source_faces_dir.is_dir():
        face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')]) # Sort for consistency
        logger.info(f"Found {len(face_files)} face images in {source_faces_dir}")
    if not face_files:
        logger.warning("No valid face images found in specified directory. Face swap will be skipped for all runs.")

    total_prompts_to_process = len(valid_prompts)
    logger.info(f"\n--- Starting Image/Video Generation for {total_prompts_to_process} Prompts ---")
    script_output_root_abs = config['output_folder'].resolve()

    # Use tqdm for progress bar over valid prompts
    for idx, item in enumerate(tqdm(valid_prompts, desc="Processing Prompts"), 1):
        background = item.get("background", "unknown_background")
        prompt = item["generated_prompt"] # We know this exists from filtering

        # Select face sequentially or randomly - let's use random for now
        selected_face = random.choice(face_files) if face_files else None
        face_log_name = selected_face.name if selected_face else "None (Swap Skipped)"

        # Log start of processing for this item
        tqdm.write 
        logger.info(f"\n🎬 Processing [{idx}/{total_prompts_to_process}] | Background: '{background}' | Face: '{face_log_name}'")
        logger.debug(f"   Prompt: {prompt}")

        # Create the specific output directory for this run/prompt
        output_dir_for_run = create_output_folders(script_output_root_abs, background)
        if not output_dir_for_run:
            logger.error(f"Failed to create output directory for prompt {idx} (background: {background}). Skipping this prompt.")
            continue # Skip to the next prompt
        logger.info(f"   📂 Base Output Dir for this Run: {output_dir_for_run}")


        # --- Execute Image Workflow ---
        logger.info(f"--- Running IMAGE Workflow for Prompt {idx} ---")
        image_workflow_path = config.get('base_workflow_image')
        if image_workflow_path and image_workflow_path.is_file():
            # Pass the base output directory for the run
            success = run_comfyui(prompt, selected_face, image_workflow_path, output_dir_for_run, f"Image Gen", idx, config['comfyui_api_url'], script_output_root_abs)
            if not success:
                logger.error(f"Image generation failed for prompt {idx}.")
            # Add a small delay perhaps?
            # time.sleep(2)
        elif image_workflow_path:
            logger.error(f"Skipping Image generation - Workflow file missing: {image_workflow_path}")
        else:
             logger.warning("Skipping Image generation - 'base_workflow_image' not defined in config.")


        # --- Execute Video Workflow ---
        logger.info(f"--- Running VIDEO Workflow for Prompt {idx} ---")
        video_workflow_path = config.get('base_workflow_video')
        if video_workflow_path and video_workflow_path.is_file():
             # Pass the base output directory for the run
             success = run_comfyui(prompt, selected_face, video_workflow_path, output_dir_for_run, f"Video Gen", idx, config['comfyui_api_url'], script_output_root_abs)
             if not success:
                 logger.error(f"Video generation failed for prompt {idx}.")
             # Add a small delay perhaps?
             # time.sleep(2)
        elif video_workflow_path:
             logger.error(f"Skipping Video generation - Workflow file missing: {video_workflow_path}")
        else:
             logger.warning("Skipping Video generation - 'base_workflow_video' not defined in config.")


        logger.info(f"--- Finished Processing Prompt {idx} ---")
        # Optional: add a longer pause between prompts if needed
        # time.sleep(5)


    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation Run Completed! {datetime.now()}")
    logger.info("=" * 50)