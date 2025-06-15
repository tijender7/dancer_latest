# main_automation_v3.py (Image Only - Enhanced Debug Prints)
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
# Ensure tqdm is importable after checking with pip show
try:
    from tqdm import tqdm
    print("DEBUG: tqdm imported successfully.")
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

print("DEBUG: Script execution started.") # <<< ADDED

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5  # seconds
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAY = 3
OLLAMA_TIMEOUT = 180
REQUEST_TIMEOUT = 60

# --- !! CONFIGURABLE PATHS !! ---
SCRIPT_DIR = Path(__file__).resolve().parent
print(f"DEBUG: Script directory: {SCRIPT_DIR}") # <<< ADDED

# --- Logging Setup ---
print("DEBUG: Setting up logging...") # <<< ADDED
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_v3_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Change to DEBUG for more verbose file logs if needed
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
print("DEBUG: Logging setup complete.") # <<< ADDED


# --- Configuration Loading ---
def load_config(config_path="config2.json"): # Using updated config name
    print(f"DEBUG: Entering load_config for '{config_path}'") # <<< ADDED
    config_path_obj = SCRIPT_DIR / config_path
    try:
        if not config_path_obj.is_file():
            print(f"DEBUG: CRITICAL - Config file not found: {config_path_obj}") # <<< ADDED
            logger.critical(f"CRITICAL: Config file not found: {config_path_obj}")
            sys.exit(1)
        print(f"DEBUG: Config file exists: {config_path_obj}") # <<< ADDED

        with open(config_path_obj, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"DEBUG: JSON loaded from {config_path_obj}") # <<< ADDED

        # Validate and resolve paths
        if 'api_server_url' not in config: raise KeyError("api_server_url")
        if 'base_workflow_image' not in config: raise KeyError("base_workflow_image")
        if 'source_faces_path' not in config: raise KeyError("source_faces_path")
        if 'output_folder' not in config: raise KeyError("output_folder")
        print("DEBUG: Required keys found in config.") # <<< ADDED

        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve()
        print(f"DEBUG: Resolved source_faces_path: {config['source_faces_path']}") # <<< ADDED
        print(f"DEBUG: Resolved output_folder: {config['output_folder']}") # <<< ADDED

        if not config['source_faces_path'].is_dir():
             logger.warning(f"Source faces dir not found: {config['source_faces_path']}") # Keep as warning
             print(f"DEBUG: Warning - Source faces dir not found: {config['source_faces_path']}") # <<< ADDED
        config['output_folder'].mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Output folder ensured: {config['output_folder']}") # <<< ADDED

        logger.info(f"Config loaded successfully from {config_path_obj}")
        print(f"DEBUG: Config load successful.") # <<< ADDED
        return config

    except FileNotFoundError: # Should be caught by is_file() check now but keep for safety
         print(f"DEBUG: CRITICAL - Caught FileNotFoundError for: {config_path_obj}") # <<< ADDED
         logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
    except json.JSONDecodeError as e:
         print(f"DEBUG: CRITICAL - Invalid JSON in '{config_path}': {e}") # <<< ADDED
         logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)
    except KeyError as e: # Catch missing key specifically
        print(f"DEBUG: CRITICAL - Missing required key {e} in '{config_path}'") # <<< ADDED
        logger.critical(f"CRITICAL: Missing required key {e} in config '{config_path}'"); sys.exit(1)
    except Exception as e:
         print(f"DEBUG: CRITICAL - Unexpected error in load_config: {e}") # <<< ADDED
         logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)

# --- Folder Creation for Run ---
def create_run_folder(output_root, background):
    # (Keep function as is)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_background = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in background)[:50]
    run_folder = output_root / f"{safe_background}_{timestamp}"
    try: run_folder.mkdir(parents=True, exist_ok=True); logger.debug(f"Ensured run folder exists: {run_folder}"); return run_folder
    except OSError as e: logger.error(f"Failed to create run folder {run_folder}: {e}"); return None

# --- Ollama Prompt Generation ---
def generate_prompts_ollama(model, num_prompts, ollama_api_url):
    # (Keep function as is - it already logs well)
    logger.info(f"🚀 Generating {num_prompts} prompts via Ollama (Model: {model}, URL: {ollama_api_url})...")
    backgrounds = [ "dance bar", "club", "beach", "steampunk airship deck", "desert landscape", "art deco speakeasy bar", "in big party hall", "open park in night ", "minimalist Japanese zen garden", "post-apocalyptic overgrown city" ]
    generated_prompt_list = []
    for i in range(num_prompts):
        background = random.choice(backgrounds)
        base_scene_idea = f"A striking, confident female dancer in a unique, thematic outfit, big burst, some time showing hips so mention them in prompt performing expressive movements on/in a {background}. She is the clear focal point, dynamic pose, showing big boobs outbursting , close or medium shot. Background elements are present but artistically blurred or secondary. Mood should be dramatic and cinematic."
        formatted_prompt = f"""Generate ONE single-line, highly detailed cinematic prompt for AI image/video. Focus on visual elements: lighting, camera angle/shot type (e.g., low angle close-up, dynamic wide shot), mood, character details (attire, expression), and specific environmental details. NO commentary. Respond ONLY with a valid JSON object: {{"prompts": ["<your prompt here>"]}}\n\nScene Desc:\n{base_scene_idea}"""
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
                    else: last_error = ValueError("JSON brackets not found or invalid.")
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
# (Keep trigger_generation function as is - make sure indentation is correct)
def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None, output_subfolder: str | None):
    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"; payload = {"prompt": prompt, "face": face_filename or "", "output_subfolder": output_subfolder}; log_prefix = f"API Call -> {endpoint}"
    logger.info(f"  ➡️ {log_prefix}: Preparing request..."); logger.info(f"     URL: {full_url}"); logger.info(f"     Prompt (start): '{prompt[:70]}...'"); logger.info(f"     Face Filename: '{face_filename or 'None'}'"); logger.info(f"     Output Subfolder: '{output_subfolder or 'None (Workflow Default)'}'"); logger.debug(f"    Payload Sent: {json.dumps(payload, indent=2)}")
    for attempt in range(1, MAX_API_RETRIES + 1):
        logger.info(f"  🚀 {log_prefix} (Attempt {attempt}/{MAX_API_RETRIES})")
        response = None
        try:
            response = requests.post(full_url, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status(); response_data = response.json()
            logger.info(f"  ✅ {log_prefix} submitted successfully (HTTP {response.status_code})"); api_status = response_data.get('status', 'N/A'); api_error = response_data.get('error', None); comfy_prompt_id = response_data.get('prompt_id', 'N/A')
            logger.info(f"     API Server Status: '{api_status}'"); logger.info(f"     ComfyUI Prompt ID: '{comfy_prompt_id}'");
            if api_error: logger.warning(f"     API Server reported error: {api_error}")
            return True
        except requests.exceptions.Timeout: logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): Request timed out after {REQUEST_TIMEOUT} seconds.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): {e}");
            # Indented block:
            if e.response is not None:
                response = e.response
                logger.warning(f"      Status Code: {e.response.status_code}");
                try:
                    logger.warning(f"      Response Body: {json.dumps(e.response.json(), indent=2)}")
                except json.JSONDecodeError: # Correctly indent except
                    logger.warning(f"      Response Body (non-JSON): {e.response.text[:500]}...")
                except Exception as inner_log_e: logger.error(f"      Error trying to log response body: {inner_log_e}")
        except json.JSONDecodeError as e:
             logger.error(f"  ❌ Error decoding JSON response from API server (Attempt {attempt}): {e}");
             if response is not None: logger.debug(f"     Raw Response: {response.text[:500]}...")
             else: logger.debug("     No response object available for raw text logging.")
        except Exception as e: logger.error(f"  ❌ Unexpected error calling API (Attempt {attempt}): {e}", exc_info=True)
        # Correctly indented retry logic:
        if attempt < MAX_API_RETRIES: logger.info(f"      Retrying in {API_RETRY_DELAY} seconds..."); time.sleep(API_RETRY_DELAY)
        else: logger.error(f"  ❌ {log_prefix} failed after {MAX_API_RETRIES} attempts."); return False
    return False


# --- Main Execution Logic (Image Only) ---
if __name__ == "__main__":
    print("DEBUG: Entering main execution block.") # <<< ADDED
    logger.info("=" * 50); logger.info(f"Starting Automation v3 (Image Only) Run: {datetime.now()}"); logger.info("=" * 50)

    config = load_config("config3.json"); # Make sure correct config file name
    if not config:
         print("DEBUG: Config loading returned None or False. Exiting.") # <<< ADDED
         sys.exit(1)
    print("DEBUG: Config loaded successfully in main.") # <<< ADDED
    API_SERVER_URL = config['api_server_url']
    print(f"DEBUG: API Server URL: {API_SERVER_URL}") # <<< ADDED

    # 1. Generate Prompts
    print("DEBUG: Starting prompt generation...") # <<< ADDED
    prompts_data = generate_prompts_ollama( config["ollama_model"], config["num_prompts"], config.get("ollama_api_url", "http://localhost:11434/api/generate") )
    print(f"DEBUG: Prompt generation finished. Got {len(prompts_data)} results.") # <<< ADDED
    save_prompts_log(prompts_data)
    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts: logger.critical("No valid prompts were generated by Ollama. Exiting."); print("DEBUG: No valid prompts found. Exiting."); sys.exit(1) # <<< ADDED
    logger.info(f"Proceeding with {len(valid_prompts)} valid prompts.")
    print(f"DEBUG: Proceeding with {len(valid_prompts)} valid prompts.") # <<< ADDED


    # 2. Prepare Faces List
    print("DEBUG: Preparing faces list...") # <<< ADDED
    face_files = []; source_faces_dir = config['source_faces_path']
    if source_faces_dir.is_dir():
        face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
        logger.info(f"Found {len(face_files)} face images in {source_faces_dir}")
    if not face_files: logger.warning("No valid face images found. Face swap will be skipped.")
    print(f"DEBUG: Found {len(face_files)} face files.") # <<< ADDED

    # 3. Create Root Output Directory
    print("DEBUG: Creating root output directory...") # <<< ADDED
    script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_output_root = config['output_folder'] / f"AutomationRun_ImageOnly_{script_run_timestamp}"
    script_output_root.mkdir(parents=True, exist_ok=True)
    logger.info(f"Script main output directory: {script_output_root}")
    print(f"DEBUG: Script main output directory: {script_output_root}") # <<< ADDED

    # ====================================================
    # 🔹 Generate Images
    # ====================================================
    logger.info(f"\n--- Submitting Image Generation for {len(valid_prompts)} Prompts ---")
    print(f"DEBUG: Starting image submission loop for {len(valid_prompts)} prompts.") # <<< ADDED
    image_progress_bar = tqdm(valid_prompts, desc="Submitting Images")
    for item_index, item in enumerate(image_progress_bar): # Use enumerate for clearer indexing
        print(f"DEBUG: Processing item index {item_index}") # <<< ADDED
        idx = item["index"]
        background = item.get("background", f"prompt_{idx}")
        prompt = item["generated_prompt"]
        selected_face_path = random.choice(face_files) if face_files else None
        face_filename_only = selected_face_path.name if selected_face_path else None

        # Create subfolder name
        run_subfolder_name = f"{idx:03d}_{''.join(c if c.isalnum() or c in ['-','_'] else '_' for c in background)[:30]}_{datetime.now().strftime('%H%M%S%f')}"
        image_output_subfolder = f"{run_subfolder_name}/images"

        image_progress_bar.set_description(f"Image Req {idx}/{len(valid_prompts)}")
        logger.info(f"\n🖼️ Preparing Image Request [{idx}/{len(valid_prompts)}] | Request Subfolder: '{image_output_subfolder}'")
        print(f"DEBUG: Calling trigger_generation for image {idx}...") # <<< ADDED

        # Call API Server - Image Endpoint ONLY
        success = trigger_generation(API_SERVER_URL, "generate_image", prompt, face_filename_only, image_output_subfolder)
        print(f"DEBUG: trigger_generation for image {idx} returned: {success}") # <<< ADDED
        if not success: logger.error(f"Failed API call for Image {idx}.")
        time.sleep(0.5)

    logger.info(f"--- All Image Generation Requests Submitted ---")
    logger.info(f"--- NOTE: ComfyUI is likely still processing these in the background. ---")
    print("DEBUG: Finished image submission loop.") # <<< ADDED

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation v3 (Image Only) Run Script Finished! {datetime.now()}")
    logger.info(f"   Check ComfyUI console for processing status.")
    logger.info(f"   Outputs *should* be located within base directory: {config['output_folder']}")
    logger.info(f"   (Actual location depends on ComfyUI's base output and the FileNamePrefix node setup)")
    logger.info("=" * 50)
    print("DEBUG: Script finished.") # <<< ADDED