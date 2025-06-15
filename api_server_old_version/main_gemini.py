import os
import json
import random
import requests
import time
import shutil
import logging
import sys
import uuid # For generating client ID
import websocket # For WebSocket communication
from datetime import datetime
from pathlib import Path
from tqdm import tqdm # For progress bar

# --- Constants ---
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between ComfyUI API retries
OLLAMA_RETRY_DELAY = 3 # seconds between Ollama retries
OLLAMA_TIMEOUT = 180 # Increased timeout for Ollama
COMFYUI_TIMEOUT = 600 # Increased timeout for ComfyUI API call AND execution monitoring (seconds)
WS_TIMEOUT = 60 # Timeout for individual websocket receive calls (seconds)

# --- !! CONFIGURABLE PATHS !! ---
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_BASE_DIR = Path("D:/Comfy_UI_V20/ComfyUI") # Adjust if needed
COMFYUI_INPUT_DIR = COMFYUI_BASE_DIR / "input"
COMFYUI_OUTPUT_DIR_NODE = "output" # Default ComfyUI output dir
TEMP_FACE_SUBDIR = "temp_faces_automation"

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
    # Prevent duplicate handlers if script is reloaded in some environments
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

        # Resolve paths
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve()
        config['base_workflow_image'] = (SCRIPT_DIR / config['base_workflow_image']).resolve()
        config['base_workflow_video'] = (SCRIPT_DIR / config['base_workflow_video']).resolve()

        # Extract ComfyUI host/port for WebSocket
        api_url = config.get('comfyui_api_url', 'http://127.0.0.1:8188/prompt')
        # Basic parsing, assumes http://host:port/something format
        try:
            base_url = api_url.split('/prompt')[0]
            if base_url.startswith("http://"):
                host_port = base_url[len("http://"):]
            elif base_url.startswith("https://"):
                 host_port = base_url[len("https://"):] # Though WS might differ (wss://)
                 logger.warning("HTTPS detected, ensure WebSocket uses 'wss://' if needed.")
            else:
                 host_port = base_url

            if ':' in host_port:
                 config['comfyui_host'] = host_port.split(':')[0]
                 config['comfyui_port'] = int(host_port.split(':')[1])
            else:
                 config['comfyui_host'] = host_port
                 config['comfyui_port'] = 80 # Default HTTP port? Unlikely for ComfyUI.
                 logger.warning(f"Could not reliably determine port from API URL '{api_url}'. Assuming default WebSocket port needed.")
            logger.info(f"ComfyUI Host: {config['comfyui_host']}, Port: {config['comfyui_port']}")
        except Exception as parse_e:
            logger.error(f"Failed to parse ComfyUI host/port from API URL '{api_url}': {parse_e}. Using defaults.")
            config['comfyui_host'] = '127.0.0.1'
            config['comfyui_port'] = 8188

        # Validation
        if not config['source_faces_path'].is_dir(): logger.warning(f"Source faces dir not found: {config['source_faces_path']}")
        if not config['base_workflow_image'].is_file(): logger.error(f"Image workflow not found: {config['base_workflow_image']}")
        if not config['base_workflow_video'].is_file(): logger.error(f"Video workflow not found: {config['base_workflow_video']}")
        config['output_folder'].mkdir(parents=True, exist_ok=True)
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
    try:
        run_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created base output directory for run: {run_folder}")
        return run_folder
    except OSError as e:
        logger.error(f"Failed to create base output directory {run_folder}: {e}")
        return None

# --- Ollama Prompt Generation ---
def generate_prompts_ollama(model, num_prompts, ollama_api_url="http://localhost:11434/api/generate"):
    # (This function remains the same as the previous corrected version)
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
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            token = chunk.get("response", "")
                            print(token, end="", flush=True)
                            full_output_text += token
                        except json.JSONDecodeError:
                            # Ignore non-JSON lines which might occur in streaming
                            logger.debug(f"      Ignoring non-JSON line from Ollama stream: {line.decode('utf-8', errors='ignore')}")
                            pass
                        except Exception as stream_e:
                            logger.warning(f"      Error processing Ollama stream chunk: {stream_e}")
                print() # Newline after streaming finishes

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
                            break # Success
                        else:
                            raise ValueError("Empty prompt string found in JSON")
                    else:
                        raise ValueError("Invalid JSON structure ('prompts' key missing or not a list)")
                else:
                    # Handle case where Ollama might not return JSON (e.g., error message)
                    logger.warning(f"   ⚠️ Ollama response did not contain valid JSON boundaries. Response text: {full_output_text[:500]}...")
                    raise ValueError("JSON boundaries '{}' not found in Ollama response")

            except json.JSONDecodeError as json_e:
                logger.warning(f"   ❌ Error decoding JSON from Ollama (Attempt {attempt+1}): {json_e}")
                logger.debug(f"      Full Ollama response text: {full_output_text}")
                error_reason = str(json_e)
            except Exception as e:
                logger.warning(f"   ❌ Error processing Ollama (Attempt {attempt+1}): {e}")
                error_reason = str(e)

            # Retry logic
            if attempt < MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)
                logger.info(f"      Retrying Ollama...")
            else:
                logger.error(f"   ❌ Failed to generate prompt [{i+1}] after {MAX_RETRIES} attempts.")
                generated_prompt_list.append({"index": i + 1, "background": background, "error": error_reason})
                break # Exit retry loop after max attempts

    success_count = len([p for p in generated_prompt_list if 'error' not in p])
    logger.info(f"✅ Finished generating {success_count} prompts successfully.")
    return generated_prompt_list

# --- Prompt Logging ---
def save_prompts_log(prompt_list):
    # (This function remains the same as the previous corrected version)
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


# --- ComfyUI Interaction (WebSocket Version) ---
def run_comfyui(prompt, face_path: Path, base_workflow_path: Path, run_output_dir: Path, mode, idx, config, script_output_root_path: Path):
    """Loads, prepares, copies face, sends workflow via HTTP, monitors via WebSocket, and cleans up."""
    prepared_workflow_json = None
    log_folder = SCRIPT_DIR / "logs"
    temp_face_comfy_relative_path = None
    temp_face_dest_abs = None
    ws = None # WebSocket connection object
    prompt_id = None # Store the submitted prompt ID
    client_id = str(uuid.uuid4()) # Unique ID for WebSocket client
    execution_successful = False # Track if ComfyUI execution finished without errors

    comfyui_api_url = config['comfyui_api_url']
    comfyui_host = config['comfyui_host']
    comfyui_port = config['comfyui_port']
    ws_url = f"ws://{comfyui_host}:{comfyui_port}/ws?clientId={client_id}"

    try:
        # --- 0. Prepare Temp Face ---
        # (Same logic as previous version)
        if face_path and face_path.is_file():
            try:
                temp_face_dir_abs = COMFYUI_INPUT_DIR / TEMP_FACE_SUBDIR
                temp_face_dir_abs.mkdir(parents=True, exist_ok=True)
                unique_face_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{face_path.name}"
                temp_face_dest_abs = temp_face_dir_abs / unique_face_name
                shutil.copyfile(face_path, temp_face_dest_abs)
                temp_face_comfy_relative_path = f"{TEMP_FACE_SUBDIR}/{unique_face_name}".replace("\\", "/")
                logger.info(f"[{idx}] Copied face '{face_path.name}' -> Comfy Input: '{temp_face_comfy_relative_path}'")
            except Exception as copy_e:
                 logger.error(f"[{idx}] Failed to copy face image: {copy_e}", exc_info=True)
                 temp_face_comfy_relative_path = None
                 face_path = None
                 logger.warning(f"[{idx}] Proceeding without face swap due to copy error.")
        elif face_path:
             logger.error(f"[{idx}] Invalid face path provided: {face_path}. Skipping face swap.")
             temp_face_comfy_relative_path = None
             face_path = None
        else:
            logger.info(f"[{idx}] No face path provided for {mode}. Skipping face swap.")
            temp_face_comfy_relative_path = None

        # --- 1. Load Base Workflow ---
        logger.debug(f"[{idx}] Loading base workflow: {base_workflow_path.name}")
        if not base_workflow_path.is_file(): raise FileNotFoundError(f"Workflow not found: {base_workflow_path}")
        with open(base_workflow_path, "r", encoding="utf-8") as f: workflow = json.load(f)

        # --- 2. Find Required Nodes ---
        # (Same logic as previous version, including fallback)
        text_node_id, face_node_id, output_node_id = None, None, None
        output_node_ids = {}
        face_node_target_title = "Load Face Image"
        logger.debug(f"[{idx}] Searching for nodes in {base_workflow_path.name}...")
        for node_id, node_data in workflow.items():
            ct = node_data.get("class_type")
            meta_title = node_data.get("_meta", {}).get("title", "")
            if ct == "Text Multiline" and not text_node_id:
                text_node_id = node_id
                logger.debug(f"[{idx}] Found Text node: {node_id} (Title: '{meta_title}')")
            if ct == "LoadImage" and meta_title == face_node_target_title and not face_node_id:
                face_node_id = node_id
                logger.debug(f"[{idx}] Found specific Face LoadImage node by title '{face_node_target_title}': {face_node_id}")
            if ct == "FileNamePrefix":
                if "Swapped" in meta_title and "swapped" not in output_node_ids:
                    output_node_ids["swapped"] = node_id
                    logger.debug(f"[{idx}] Found Output FileNamePrefix (Swapped): {node_id} (Title: '{meta_title}')")
                elif "raw" not in output_node_ids and "Raw" in meta_title:
                     output_node_ids["raw"] = node_id
                     logger.debug(f"[{idx}] Found Output FileNamePrefix (Raw): {node_id} (Title: '{meta_title}')")
                if not output_node_id:
                     output_node_id = node_id
                     logger.debug(f"[{idx}] Found generic FileNamePrefix node: {node_id} (Title: '{meta_title}')")
        if temp_face_comfy_relative_path and not face_node_id:
            logger.warning(f"[{idx}] Specific face node '{face_node_target_title}' not found. Searching for first LoadImage as fallback.")
            for node_id, node_data in workflow.items():
                if node_data.get("class_type") == "LoadImage":
                    face_node_id = node_id
                    logger.warning(f"[{idx}] Using first found LoadImage node as fallback: {face_node_id} (Title: '{node_data.get('_meta', {}).get('title', '')}')")
                    break
        if "Image Gen" in mode:
            if "swapped" in output_node_ids: output_node_id = output_node_ids["swapped"]
            elif "raw" in output_node_ids: output_node_id = output_node_ids["raw"]
        elif "Video Gen" in mode: pass # Use fallback (first found)
        logger.debug(f"[{idx}] Using Output Node ID {output_node_id} for mode {mode}")

        # --- 3. Validate Nodes Found ---
        if not text_node_id: raise ValueError(f"Missing 'Text Multiline' node in {base_workflow_path.name}")
        if temp_face_comfy_relative_path and not face_node_id:
            raise ValueError(f"Face path provided, but failed to find suitable 'LoadImage' node (tried title '{face_node_target_title}' and fallback) in {base_workflow_path.name}")
        if not output_node_id: raise ValueError(f"Missing 'FileNamePrefix' node in {base_workflow_path.name}")

        # --- 4. Inject Data ---
        # (Same logic as previous version)
        logger.debug(f"[{idx}] Injecting prompt into Text Node {text_node_id}")
        workflow[text_node_id]["inputs"]["text"] = prompt
        if face_node_id and temp_face_comfy_relative_path:
            workflow[face_node_id]["inputs"]["image"] = temp_face_comfy_relative_path
            logger.debug(f"[{idx}] Injected face path '{temp_face_comfy_relative_path}' into Face Node {face_node_id}")
        elif face_node_id:
             logger.warning(f"[{idx}] Face LoadImage node ({face_node_id}) exists, but no face available for {mode}.")
        try:
            run_folder_name = run_output_dir.name
            sub_path = ""
            if "Image Gen" in mode:
                if output_node_id == output_node_ids.get("swapped"): sub_path = "faceswapped_images"
                elif output_node_id == output_node_ids.get("raw"): sub_path = "raw_images"
                else: sub_path = "images"
            elif "Video Gen" in mode:
                 sub_path = "faceswapped_videos" if face_node_id and temp_face_comfy_relative_path else "raw_videos"
            else: sub_path = "unknown_output"
            comfy_custom_dir = f"{run_folder_name}/{sub_path}".replace("\\", "/")
        except Exception as path_e:
            logger.warning(f"Error calculating custom directory path: {path_e}. Using fallback.")
            comfy_custom_dir = run_output_dir.name
        logger.debug(f"[{idx}] Injecting custom_directory '{comfy_custom_dir}' into Output Node {output_node_id}")
        workflow[output_node_id]["inputs"]["custom_directory"] = comfy_custom_dir
        prefix_text = workflow[output_node_id]["inputs"].get("custom_text", "")
        if face_node_id and temp_face_comfy_relative_path:
             if "swapped" not in prefix_text.lower() : prefix_text = f"swapped_{prefix_text}"
        else:
             if "raw" not in prefix_text.lower() : prefix_text = f"raw_{prefix_text}"
        prefix_text = prefix_text.replace("__", "_").strip("_")
        workflow[output_node_id]["inputs"]["custom_text"] = prefix_text
        logger.debug(f"[{idx}] Setting custom_text in Output Node {output_node_id} to: '{prefix_text}'")

        # Add client_id to the payload for ComfyUI
        prepared_workflow_json = {"prompt": workflow, "client_id": client_id}

        # --- 5. Send to ComfyUI API (HTTP Post) ---
        api_call_successful = False
        prompt_response = None
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"  🚀 Sending to ComfyUI -> {mode} [{idx}] (Attempt {attempt}/{MAX_RETRIES})")
            try:
                response = requests.post(comfyui_api_url, json=prepared_workflow_json, timeout=COMFYUI_TIMEOUT/10) # Shorter timeout for just the POST
                response.raise_for_status()
                prompt_response = response.json()
                prompt_id = prompt_response.get('prompt_id')
                if not prompt_id:
                    raise ValueError("ComfyUI API response did not contain 'prompt_id'")
                logger.info(f"  ✅ {mode} [{idx}] workflow sent successfully (HTTP {response.status_code}). Prompt ID: {prompt_id}")
                api_call_successful = True
                break # Exit retry loop on success
            except requests.exceptions.Timeout:
                logger.warning(f"  ⚠️ ComfyUI API Error ({mode} [{idx}], Attempt {attempt}): HTTP POST request timed out.")
            except requests.exceptions.RequestException as e:
                # (Error logging same as previous version)
                logger.warning(f"  ⚠️ ComfyUI API Error ({mode} [{idx}], Attempt {attempt}): {e}")
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                     status_code = e.response.status_code
                     logger.warning(f"      Received HTTP {status_code} from ComfyUI.")
                     if status_code in [400, 500]:
                         error_payload_file = log_folder / f"failed_payload_{mode}_{idx}_attempt_{attempt}_{datetime.now():%Y%m%d%H%M%S}.json"
                         logger.error(f"      🔥 ComfyUI HTTP {status_code}. Saving payload to: {error_payload_file}")
                         try:
                             # Save without client_id for easier debugging in UI
                             debug_payload = prepared_workflow_json.copy()
                             debug_payload.pop("client_id", None)
                             with open(error_payload_file, "w", encoding="utf-8") as f_err: json.dump({"prompt": debug_payload.get("prompt")}, f_err, indent=2)
                         except Exception as log_e: logger.error(f"      Failed to save error payload: {log_e}")
                         try:
                             error_details = e.response.json(); logger.error(f"      ComfyUI Response Body (JSON): {json.dumps(error_details, indent=2)}")
                         except json.JSONDecodeError: logger.error(f"      ComfyUI Response Body (non-JSON): {e.response.text[:1500]}...")
            except ValueError as e:
                 logger.error(f"  ❌ Error processing ComfyUI response ({mode} [{idx}], Attempt {attempt}): {e}")


            if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY); logger.info(f"      Retrying...")
            else: logger.error(f"  ❌ {mode} [{idx}] failed to submit prompt after {MAX_RETRIES} attempts.")

        if not api_call_successful or not prompt_id:
            return False # Cannot proceed without successful submission and prompt_id

        # --- 6. Monitor Execution via WebSocket ---
        logger.info(f"  👂 Monitoring ComfyUI execution via WebSocket for Prompt ID: {prompt_id}")
        execution_finished = False
        execution_error = False
        start_time = time.time()

        try:
            ws = websocket.create_connection(ws_url)
            logger.debug(f"      WebSocket connection established to {ws_url}")

            while True:
                # Check for overall timeout
                if time.time() - start_time > COMFYUI_TIMEOUT:
                    logger.error(f"  ❌ Timeout waiting for ComfyUI execution to finish for Prompt ID {prompt_id} (>{COMFYUI_TIMEOUT}s).")
                    execution_error = True # Treat timeout as an error
                    break

                try:
                    # Set a timeout for receiving data to prevent indefinite blocking
                    ws.settimeout(WS_TIMEOUT)
                    message_str = ws.recv()
                    if not message_str:
                        # Connection might be closing or idle, check overall timeout again
                        logger.debug("      Received empty message or timeout from WebSocket.")
                        continue

                    message = json.loads(message_str)
                    logger.debug(f"      WS Received: {message}") # Log raw messages at debug level

                    if message.get('type') == 'status':
                        status_data = message.get('data', {})
                        queue_remaining = status_data.get('status', {}).get('exec_info', {}).get('queue_remaining', '?')
                        logger.debug(f"      WS Status: Queue Remaining = {queue_remaining}")

                    elif message.get('type') == 'execution_start':
                        if message.get('data', {}).get('prompt_id') == prompt_id:
                            logger.info(f"      WS: Execution started for Prompt ID {prompt_id}.")

                    elif message.get('type') == 'progress':
                        progress_data = message.get('data', {})
                        if progress_data.get('prompt_id') == prompt_id: # Check if progress is for our prompt
                            value = progress_data.get('value', '?')
                            max_val = progress_data.get('max', '?')
                            logger.debug(f"      WS Progress for {prompt_id}: {value}/{max_val}")
                            # Optionally update tqdm bar here if needed (more complex)

                    elif message.get('type') == 'executed':
                        exec_data = message.get('data', {})
                        if exec_data.get('prompt_id') == prompt_id:
                            logger.info(f"  ✅ WS: Execution finished successfully for Prompt ID {prompt_id}.")
                            execution_finished = True
                            execution_successful = True # Mark as successful
                            break # Exit the monitoring loop

                    elif message.get('type') == 'execution_error' or message.get('type') == 'execution_interrupted':
                         error_data = message.get('data', {})
                         if error_data.get('prompt_id') == prompt_id:
                             logger.error(f"  ❌ WS: Execution failed or interrupted for Prompt ID {prompt_id}.")
                             logger.error(f"      Error Details: {json.dumps(error_data, indent=2)}")
                             execution_finished = True
                             execution_error = True
                             break # Exit the monitoring loop

                except websocket.WebSocketTimeoutException:
                    logger.debug(f"      WebSocket recv timed out after {WS_TIMEOUT}s, continuing wait...")
                    continue # Continue waiting, rely on overall timeout
                except json.JSONDecodeError as json_e:
                    logger.warning(f"      Error decoding WebSocket message: {json_e}. Message: '{message_str}'")
                except websocket.WebSocketConnectionClosedException:
                    logger.error("  ❌ WebSocket connection closed unexpectedly.")
                    execution_error = True
                    break
                except Exception as ws_e:
                    logger.error(f"  ❌ Unexpected WebSocket error: {ws_e}", exc_info=True)
                    execution_error = True
                    break

            # End of WebSocket loop

        except Exception as ws_conn_e:
            logger.error(f"  ❌ Failed to establish WebSocket connection to {ws_url}: {ws_conn_e}")
            execution_error = True # Cannot monitor, assume failure for cleanup logic
        finally:
            if ws and ws.connected:
                try:
                    ws.close()
                    logger.debug("      WebSocket connection closed.")
                except Exception as ws_close_e:
                     logger.warning(f"      Error closing WebSocket: {ws_close_e}")

        # Return based on whether execution was monitored and successful
        return execution_successful

    # --- Outer Exception Handling and Cleanup ---
    except FileNotFoundError as e: logger.error(f"❌ Workflow file error for {mode} [{idx}]: {e}"); return False
    except ValueError as e: logger.error(f"❌ Workflow prep error for {mode} [{idx}]: {e}"); return False
    except Exception as e: logger.error(f"❌ Unexpected error during ComfyUI run setup for {mode} [{idx}]: {e}", exc_info=True); return False
    finally:
        # --- 7. Clean Up Temp Face ---
        # Only delete if the workflow execution was monitored and seemed successful OR if there was an error preventing monitoring/execution
        # Basically, delete unless we timed out waiting for execution AND the file still exists (meaning ComfyUI might still need it)
        should_delete = False
        if execution_successful:
            logger.debug(f"[{idx}] Execution successful, proceeding with temp file cleanup.")
            should_delete = True
        elif execution_error: # Includes WS errors, timeouts, execution errors
             logger.debug(f"[{idx}] Execution/Monitoring error occurred, proceeding with temp file cleanup.")
             should_delete = True
        # Add specific check if the only reason we stopped monitoring was timeout, in which case, maybe don't delete?
        # This is tricky. Let's stick to deleting on success or explicit error for now.

        if should_delete and temp_face_comfy_relative_path and temp_face_dest_abs and temp_face_dest_abs.is_file():
             time.sleep(1) # Small delay just in case filesystem is slow
             try:
                 logger.info(f"  🧹 Cleaning up temp face: {temp_face_dest_abs}")
                 os.remove(temp_face_dest_abs)
             except OSError as rm_e:
                 logger.warning(f"[{idx}] Could not delete temp face file {temp_face_dest_abs}: {rm_e}")
        elif temp_face_dest_abs and temp_face_dest_abs.is_file():
            logger.warning(f"[{idx}] Skipping temp face cleanup for {temp_face_dest_abs} as execution status was inconclusive (e.g., timeout without explicit finish/error signal). Please check manually.")


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
        face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
        logger.info(f"Found {len(face_files)} face images in {source_faces_dir}")
    if not face_files:
        logger.warning("No valid face images found. Face swap will be skipped.")

    total_prompts_to_process = len(valid_prompts)
    logger.info(f"\n--- Starting Image/Video Generation for {total_prompts_to_process} Prompts ---")
    script_output_root_abs = config['output_folder'].resolve()

    # Use tqdm for progress bar
    for idx, item in enumerate(tqdm(valid_prompts, desc="Processing Prompts"), 1):
        background = item.get("background", "unknown_background")
        prompt = item["generated_prompt"]

        selected_face = random.choice(face_files) if face_files else None
        face_log_name = selected_face.name if selected_face else "None (Swap Skipped)"

        # Log start of processing for this item
        logger.info(f"\n🎬 Processing [{idx}/{total_prompts_to_process}] | Background: '{background}' | Face: '{face_log_name}'")
        logger.debug(f"   Prompt: {prompt}")

        output_dir_for_run = create_output_folders(script_output_root_abs, background)
        if not output_dir_for_run:
            logger.error(f"Failed to create output directory for prompt {idx}. Skipping.")
            continue
        logger.info(f"   📂 Base Output Dir for this Run: {output_dir_for_run}")

        # --- Execute Image Workflow ---
        logger.info(f"--- Running IMAGE Workflow for Prompt {idx} ---")
        image_workflow_path = config.get('base_workflow_image')
        if image_workflow_path and image_workflow_path.is_file():
            success = run_comfyui(prompt, selected_face, image_workflow_path, output_dir_for_run, f"Image Gen", idx, config, script_output_root_abs)
            if not success:
                logger.error(f"Image generation failed or encountered errors during execution for prompt {idx}.")
        elif image_workflow_path:
            logger.error(f"Skipping Image generation - Workflow file missing: {image_workflow_path}")
        else:
             logger.warning("Skipping Image generation - 'base_workflow_image' not defined in config.")

        # --- Execute Video Workflow ---
        logger.info(f"--- Running VIDEO Workflow for Prompt {idx} ---")
        video_workflow_path = config.get('base_workflow_video')
        if video_workflow_path and video_workflow_path.is_file():
             success = run_comfyui(prompt, selected_face, video_workflow_path, output_dir_for_run, f"Video Gen", idx, config, script_output_root_abs)
             if not success:
                 logger.error(f"Video generation failed or encountered errors during execution for prompt {idx}.")
        elif video_workflow_path:
             logger.error(f"Skipping Video generation - Workflow file missing: {video_workflow_path}")
        else:
             logger.warning("Skipping Video generation - 'base_workflow_video' not defined in config.")

        logger.info(f"--- Finished Processing Prompt {idx} ---")
        # Optional: Add a small delay between prompts if ComfyUI needs recovery time
        # time.sleep(5)

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation Run Completed! {datetime.now()}")
    logger.info("=" * 50)