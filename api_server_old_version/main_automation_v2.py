# main_automation_v2.py
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
from tqdm import tqdm

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5  # seconds
OLLAMA_RETRY_DELAY = 3
OLLAMA_TIMEOUT = 180
REQUEST_TIMEOUT = 30 # Timeout for requests TO the api_server_v2
MAX_RETRIES = 3
OLLAMA_MAX_RETRIES = 3

# --- !! CONFIGURABLE PATHS !! ---
SCRIPT_DIR = Path(__file__).resolve().parent
# Note: ComfyUI base paths are less relevant here, as API server handles workflows
# We mainly need the source faces path for listing files

# --- Logging Setup ---
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_v2_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.hasHandlers(): logger.handlers.clear(); logger.addHandler(file_handler); logger.addHandler(console_handler)


# --- Configuration Loading ---
def load_config(config_path="config2.json"):
    config_path_obj = SCRIPT_DIR / config_path
    try:
        if not config_path_obj.is_file(): logger.critical(f"CRITICAL: Config file not found: {config_path_obj}"); sys.exit(1)
        with open(config_path_obj, 'r', encoding='utf-8') as f: config = json.load(f)
        logger.info(f"Config loaded from {config_path_obj}")

        # Paths relative to script dir
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve() # Where this script creates run folders

        # Validation
        if 'api_server_url' not in config: logger.critical("CRITICAL: 'api_server_url' missing in config2.json"); sys.exit(1)
        if not config['source_faces_path'].is_dir(): logger.warning(f"Source faces dir not found: {config['source_faces_path']}")
        config['output_folder'].mkdir(parents=True, exist_ok=True)

        return config
    except Exception as e: logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True); sys.exit(1)

# --- Folder Creation for Run ---
def create_run_folder(output_root, background):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_background = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in background)[:50] # Limit length
    run_folder = output_root / f"{safe_background}_{timestamp}"
    try:
        run_folder.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured run folder exists: {run_folder}")
        return run_folder
    except OSError as e: logger.error(f"Failed to create run folder {run_folder}: {e}"); return None

# --- Ollama Prompt Generation (Same as before, slightly updated logging) ---
def generate_prompts_ollama(model, num_prompts, ollama_api_url):
    logger.info(f"🚀 Generating {num_prompts} prompts via Ollama (Model: {model}, URL: {ollama_api_url})...")
    # Enhanced list of backgrounds for variety
    backgrounds = [  "minimalist Japanese zen garden", "post-apocalyptic overgrown city" ]
    generated_prompt_list = []

    for i in range(num_prompts):
        background = random.choice(backgrounds)
        base_scene_idea = f"A striking, confident female dancer in a unique, thematic outfit, performing expressive movements on/in a {background}. She is the clear focal point, dynamic pose, close or medium shot. Background elements are present but artistically blurred or secondary. Mood should be dramatic and cinematic."
        formatted_prompt = f"""Generate ONE single-line, highly detailed cinematic prompt for AI image/video. Focus on visual elements: lighting, camera angle/shot type (e.g., low angle close-up, dynamic wide shot), mood, character details (attire, expression), and specific environmental details. NO commentary. Respond ONLY with a valid JSON object: {{"prompts": ["<your prompt here>"]}}\n\nScene Desc:\n{base_scene_idea}"""

        logger.info(f"\n🧠 Requesting Prompt [{i+1}/{num_prompts}] | Theme: {background}")
        ollama_success = False
        last_error = None
        # Use the correct constant here
        for attempt in range(OLLAMA_MAX_RETRIES): # <--- CORRECTED
            logger.debug(f"   Ollama Attempt {attempt+1}/{OLLAMA_MAX_RETRIES}...") # <--- Use constant here too for logging
            try:
                response = requests.post(ollama_api_url, json={"model": model, "prompt": formatted_prompt, "stream": False}, timeout=OLLAMA_TIMEOUT) # Stream false for simpler parsing
                response.raise_for_status()
                response_json = response.json()
                generated_text = response_json.get("response", "").strip()

                # Try to find JSON within the response if Ollama didn't format perfectly
                try:
                    start_index = generated_text.find('{')
                    end_index = generated_text.rfind('}')
                    if start_index != -1 and end_index != -1 and start_index < end_index:
                        json_str = generated_text[start_index:end_index+1]
                        parsed = json.loads(json_str)
                        if "prompts" in parsed and isinstance(parsed["prompts"], list) and parsed["prompts"]:
                            prompt_text = parsed["prompts"][0].strip()
                            if prompt_text:
                                logger.info(f"   ✅ Clean Prompt Extracted: {prompt_text}")
                                generated_prompt_list.append({"index": i + 1, "background": background, "generated_prompt": prompt_text})
                                ollama_success = True
                                break # Success
                            else: last_error = ValueError("Empty prompt string in JSON.")
                        else: last_error = ValueError("Invalid JSON structure ('prompts' missing/empty).")
                    else: last_error = ValueError("JSON brackets not found or invalid.")
                except json.JSONDecodeError as json_e:
                    last_error = json_e
                    logger.warning(f"   ❌ Could not decode JSON from Ollama response (Attempt {attempt+1}): {json_e}")
                    logger.debug(f"      Ollama raw response: {generated_text}")

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"   ❌ Error connecting to Ollama (Attempt {attempt+1}): {e}")
            except Exception as e:
                 last_error = e
                 logger.warning(f"   ❌ Unexpected error processing Ollama (Attempt {attempt+1}): {e}")

            # Use the correct constant here
            if not ollama_success and attempt < OLLAMA_MAX_RETRIES - 1: # <--- CORRECTED
                logger.info(f"      Retrying Ollama in {OLLAMA_RETRY_DELAY}s...")
                time.sleep(OLLAMA_RETRY_DELAY)
            elif not ollama_success:
                 # And here
                 logger.error(f"   ❌ Failed to generate prompt [{i+1}] after {OLLAMA_MAX_RETRIES} attempts. Last error: {last_error}") # <--- CORRECTED
                 generated_prompt_list.append({"index": i + 1, "background": background, "error": str(last_error)})

    successful_count = sum(1 for p in generated_prompt_list if 'error' not in p)
    logger.info(f"✅ Finished generating {successful_count}/{num_prompts} prompts.")
    return generated_prompt_list


# --- Prompt Logging (Same as before) ---
def save_prompts_log(prompt_list):
    # ... (keep the exact same function as in your original script) ...
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
def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None, output_subfolder: str | None):
    """Sends a request to the specified API server endpoint."""
    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
    payload = {"prompt": prompt, "face": face_filename or "", "output_subfolder": output_subfolder} # Send empty string if no face

    log_prefix = f"API Call -> {endpoint}"

    for attempt in range(1, MAX_API_RETRIES + 1):
        logger.info(f"  🚀 {log_prefix} (Attempt {attempt}/{MAX_API_RETRIES}) | Face: {face_filename or 'None'}")
        logger.debug(f"     URL: {full_url}")
        logger.debug(f"     Payload: {json.dumps(payload, indent=2)}")
        try:
            response = requests.post(full_url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status() # Check for HTTP errors
            logger.info(f"  ✅ {log_prefix} submitted successfully (HTTP {response.status_code})")
            # logger.debug(f"     Response: {response.text}") # Optionally log full response
            return True # Success
        except requests.exceptions.Timeout:
             logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): Request timed out after {REQUEST_TIMEOUT} seconds.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): {e}")
            if e.response is not None:
                logger.warning(f"      Status Code: {e.response.status_code}")
                try: logger.warning(f"      Response Body: {json.dumps(e.response.json(), indent=2)}")
                except: logger.warning(f"      Response Body (non-JSON): {e.response.text[:500]}...")
        except Exception as e:
             logger.error(f"  ❌ Unexpected error calling API (Attempt {attempt}): {e}", exc_info=True)

        # Retry logic
        if attempt < MAX_API_RETRIES: logger.info(f"      Retrying in {API_RETRY_DELAY} seconds..."); time.sleep(API_RETRY_DELAY)
        else: logger.error(f"  ❌ {log_prefix} failed after {MAX_API_RETRIES} attempts."); return False

    return False # Should not be reached if MAX_RETRIES > 0

# --- Main Execution Logic ---
if __name__ == "__main__":
    logger.info("=" * 50); logger.info(f"Starting Automation v2 Run: {datetime.now()}"); logger.info("=" * 50)
    config = load_config(); API_SERVER_URL = config['api_server_url']

    # 1. Generate Prompts
    prompts_data = generate_prompts_ollama( config["ollama_model"], config["num_prompts"], config.get("ollama_api_url", "http://localhost:11434/api/generate") )
    save_prompts_log(prompts_data)
    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts: logger.critical("No valid prompts were generated by Ollama. Exiting."); sys.exit(1)
    logger.info(f"Proceeding with {len(valid_prompts)} valid prompts.")

    # 2. Prepare Faces List
    face_files = []; source_faces_dir = config['source_faces_path']
    if source_faces_dir.is_dir():
        face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
        logger.info(f"Found {len(face_files)} face images in {source_faces_dir}")
    if not face_files: logger.warning("No valid face images found. Face swap will be skipped.")

    # 3. Create Root Output Directory for This Entire Script Run
    script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_output_root = config['output_folder'] / f"AutomationRun_{script_run_timestamp}"
    script_output_root.mkdir(parents=True, exist_ok=True)
    logger.info(f"Script main output directory: {script_output_root}")

    prompt_details_for_video = {} # Store details needed for the video loop

    # ====================================================
    # 🔹 STAGE 1: Generate All Images
    # ====================================================
    logger.info(f"\n--- STAGE 1: Generating Images for {len(valid_prompts)} Prompts ---")
    image_progress_bar = tqdm(valid_prompts, desc="Generating Images")
    for item in image_progress_bar:
        idx = item["index"]
        background = item.get("background", f"prompt_{idx}")
        prompt = item["generated_prompt"]
        selected_face_path = random.choice(face_files) if face_files else None
        face_filename_only = selected_face_path.name if selected_face_path else None

        # Create a unique subfolder for this specific prompt's outputs within the main script run folder
        # This name will also be passed to the API server to use in ComfyUI's FileNamePrefix
        run_subfolder_name = f"{idx:03d}_{''.join(c if c.isalnum() or c in ['-','_'] else '_' for c in background)[:30]}_{datetime.now().strftime('%H%M%S')}"
        current_run_output_dir = script_output_root / run_subfolder_name
        current_run_output_dir.mkdir(exist_ok=True) # Ensure it exists

        # Store details for the video stage
        prompt_details_for_video[idx] = {"prompt": prompt, "face_filename": face_filename_only, "run_subfolder_name": run_subfolder_name}

        # Define the subfolder structure for ComfyUI's output prefix
        image_output_subfolder = f"{run_subfolder_name}/images" # Relative path structure for ComfyUI

        image_progress_bar.set_description(f"Image {idx}/{len(valid_prompts)}")
        logger.info(f"\n🖼️ Processing Image [{idx}/{len(valid_prompts)}] | Subfolder: '{run_subfolder_name}' | Face: '{face_filename_only or 'None'}'")

        # Call API Server - Image Endpoint
        success = trigger_generation(API_SERVER_URL, "generate_image", prompt, face_filename_only, image_output_subfolder)
        if not success: logger.error(f"Failed API call for Image {idx}.")
        # Optional short delay between submissions
        # time.sleep(1)

    logger.info("--- STAGE 1: Image Generation Requests Submitted ---")

    # ====================================================
    # 🔹 STAGE 2: Generate All Videos
    # ====================================================
    logger.info(f"\n--- STAGE 2: Generating Videos for {len(valid_prompts)} Prompts ---")
    video_progress_bar = tqdm(valid_prompts, desc="Generating Videos") # Iterate over original valid prompts list
    for item in video_progress_bar:
        idx = item["index"]
        # Retrieve details stored during the image stage
        details = prompt_details_for_video.get(idx)
        if not details:
            logger.error(f"Could not find details for prompt index {idx}. Skipping video generation.")
            continue

        prompt = details["prompt"]
        face_filename_only = details["face_filename"]
        run_subfolder_name = details["run_subfolder_name"] # Use the same subfolder name

        # Define the subfolder structure for ComfyUI's output prefix for video
        video_output_subfolder = f"{run_subfolder_name}/videos" # Relative path structure for ComfyUI

        video_progress_bar.set_description(f"Video {idx}/{len(valid_prompts)}")
        logger.info(f"\n🎬 Processing Video [{idx}/{len(valid_prompts)}] | Subfolder: '{run_subfolder_name}' | Face: '{face_filename_only or 'None'}'")

        # Call API Server - Video Endpoint
        success = trigger_generation(API_SERVER_URL, "generate_video", prompt, face_filename_only, video_output_subfolder)
        if not success: logger.error(f"Failed API call for Video {idx}.")
        # Optional short delay between submissions
        # time.sleep(1)

    logger.info("--- STAGE 2: Video Generation Requests Submitted ---")

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation v2 Run Completed! {datetime.now()}")
    logger.info(f"   Outputs located within base directory: {script_output_root}")
    logger.info("=" * 50)