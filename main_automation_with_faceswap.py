# main_automation_v6.py (Handles Batches & Fixes Image Serving)
import os
import json
import random
import requests
import time
import shutil
import logging
import sys
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote # For safe image URLs

# --- Third-party Imports ---
from dotenv import load_dotenv

# --- Import Flask ---
try:
    from flask import Flask, request, render_template_string, send_from_directory, jsonify, url_for
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

# --- Load environment variables (.env) ---
load_dotenv()  # Looking for TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

print("DEBUG: Script execution started (v6).")

# --- Constants ---
# (Keep constants the same as v5)
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAY = 3
OLLAMA_TIMEOUT = 180
REQUEST_TIMEOUT = 60
POLLING_INTERVAL = 10
POLLING_TIMEOUT_IMAGE = 1800
POLLING_TIMEOUT_VIDEO = 3600
APPROVAL_SERVER_PORT = 5005
APPROVAL_FILENAME = "approved_images.json" # Changed filename to reflect content
APPROVED_IMAGES_SUBFOLDER = "approved_images_for_video" # Changed subfolder name
BATCH_SEPARATOR = "__batch__" # Separator for checkbox value

# --- !! CONFIGURABLE PATHS !! ---
SCRIPT_DIR = Path(__file__).resolve().parent
# !!! USER MUST SET THESE CORRECTLY !!!
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input") # <<< USER MUST SET
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content") # <<< USER MUST SET
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"
# !!! END USER SETTINGS !!!

# --- Telegram Approval Paths & Env Vars ---
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"
TELEGRAM_APPROVALS_JSON = TELEGRAM_APPROVALS_DIR / "telegram_approvals.json"
TOKEN_MAP_JSON = TELEGRAM_APPROVALS_DIR / "token_map.json"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env. Telegram approval will fail if chosen.")

print(f"DEBUG: Script directory: {SCRIPT_DIR}")
print(f"DEBUG: Assumed ComfyUI Input Base: {COMFYUI_INPUT_DIR_BASE}")
print(f"DEBUG: Assumed ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")

# --- Logging Setup ---
# (Keep logging setup the same as v5)
print("DEBUG: Setting up logging...")
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_v6_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8'); file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.INFO) # Default to INFO
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler); logger.addHandler(console_handler)
print("DEBUG: Logging setup complete.")
logger.info("Starting Automation v6 Run")

# --- Helper Function (Find by Title) ---
# (Keep same function from v5)
def find_node_id_by_title(workflow, title, wf_name="workflow"):
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("_meta", {}).get("title") == title:
            logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

# --- Configuration Loading ---
# (Keep same function from v5)
def load_config(config_path="config_with_faceswap.json"):
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

# === 🔥 ENHANCED PROMPT GENERATION SYSTEM (IDENTICAL TO WITHOUT_FACESWAP) ===

# Dictionary to hold modular prompt components for high variety + VIRAL CONTENT
PROMPT_ELEMENTS = {
    "locations": [
        # Traditional Cultural Locations
        "a vibrant Bollywood dance festival in Mumbai with colorful decorations and cheering crowds",
        "a luxurious rooftop party overlooking the Gateway of India in Mumbai with city lights",
        "a traditional Indian wedding celebration with marigold flowers, fairy lights, and excited guests",
        "a high-energy Punjabi bhangra competition in a decorated mandap with loud music",
        "a glamorous Indian fashion show with runway lights, cameras, and applauding audience",
        "a festive Holi celebration with colorful powder, traditional music, and dancing people",
        "an exclusive pool party at a luxury resort in Goa with palm trees and sunset views",
        "a vibrant Navratri garba dance festival with ornate decorations and spinning dancers",
        "a modern Indian nightclub with neon lights, DJ booth, and energetic crowd",
        "a beachside party in Kerala during sunset with coconut palms and crashing waves",
        "a royal palace courtyard in Rajasthan converted into a dance venue with torches",
        "a contemporary Indian cultural festival with modern and traditional fusion elements",
        
        # 🔥 VIRAL UNIFORM THEMES - Maximum Appeal
        "a busy Indian police station with official desks, computers, and uniformed officers in background",
        "a modern Indian hospital emergency room with medical equipment, beds, and staff bustling around",
        "an upscale Indian corporate office with glass desks, computers, and professional atmosphere",
        "a prestigious Indian college campus with students, books, and academic buildings",
        "a high-end Indian restaurant kitchen with professional equipment, chefs, and busy service",
        "an exclusive Indian gym with modern equipment, mirrors, and fitness enthusiasts",
        "a luxurious Indian spa with massage tables, aromatherapy, and relaxation atmosphere",
        "an Indian courtroom with judge's bench, law books, and formal legal atmosphere",
        "a modern Indian television news studio with cameras, lights, and broadcasting equipment",
        "an Indian military training facility with equipment, flags, and disciplined environment",
        "a professional Indian photography studio with lighting equipment, cameras, and backdrops",
        "an Indian airline cabin with seats, overhead bins, and flight attendant service area"
    ],
    
    "attires": [
        # Traditional Revealing Outfits - ENHANCED FOR APPROPRIATE COVERAGE
        "a fitted, deep V-neck choli blouse with push-up design showing massive cleavage but covering nipples, paired with a short lehenga skirt that shows her midriff and curves",
        "a sequined saree blouse with plunging neckline that creates dramatic cleavage while keeping nipples covered, with saree draped very low on hips showing maximum skin",
        "a mini ghagra with intricate embroidery and a backless, halter-style choli with deep side cuts that shows underboob but keeps nipples covered",
        "a modern fusion outfit: tiny denim shorts with a cropped, traditional mirror-work halter top that shows maximum cleavage and entire midriff while covering nipples",
        "a sheer dupatta draped over a push-up style bikini top with coverage, and ultra-short sharara pants that show her curves",
        
        # 🔥 VIRAL UNIFORM VARIATIONS - Maximum Appeal with Appropriate Coverage
        "a provocative flight attendant costume: an ultra-tight, plunging V-neck airline blouse with buttons strategically placed to show maximum cleavage while covering nipples, and a micro mini skirt",
        "a seductive office secretary look: a business shirt with deep neckline tied under the chest to create maximum cleavage display while keeping nipples covered, with a tiny pencil skirt",
        "a college student outfit: a school tie with a tight, low-cut tank top that shows massive cleavage but covers nipples, and an ultra-short plaid skirt",
        "a tempting chef costume: a white chef's hat with a halter-style apron top that shows maximum cleavage and side boob while covering nipples, with tiny chef shorts",
        "a fitness instructor outfit: a push-up sports bra with deep neckline that shows massive cleavage but covers nipples, and micro athletic shorts",
        "a courtroom professional look: a lawyer's blazer worn open over a deep V-neck camisole that shows maximum cleavage while covering nipples, with a tiny pencil skirt",
        "a medical professional outfit: a white halter-style scrub top with deep neckline and red cross detail that shows maximum cleavage but covers nipples, with a tiny white skirt",
        "a modified Indian police uniform: an extremely tight, deep V-neck police shirt that shows massive cleavage while covering nipples, with a tiny police cap and micro shorts",
        "a news anchor look: a professional blazer worn open over a plunging neckline camisole that creates maximum cleavage display while covering nipples, with a tiny skirt",
        "a military inspired uniform: a deep V-neck camouflage halter top with dog tags that shows maximum cleavage but covers nipples, and tiny camo shorts"
    ],
    
    "dance_actions": [
        "performing energetic bhangra moves with dramatic shoulder shaking and hip movements that make her chest bounce",
        "executing graceful classical Indian dance poses that emphasize her curves and chest movements",
        "doing seductive Bollywood-style hip sways and chest pops while moving sensually toward the camera",
        "performing traditional garba spins modified with modern, sensual body movements and breast bouncing",
        "dancing with powerful Punjabi moves that showcase her bouncing chest and swaying hips",
        "executing fluid, snake-like movements inspired by classical Indian dance that highlight her curves",
        "doing contemporary fusion dance that combines traditional mudras with modern, sexy movements",
        "performing rhythmic thumri-inspired moves with graceful arm movements and dramatic body rolls that emphasize her figure"
    ],
    
    "camera_shots": [
        "a dynamic low-angle shot emphasizing her powerful dance moves, dominant presence, and bursting cleavage",
        "an intimate close-up focusing on her expressive Indian features, bouncing chest, and sensual expressions",
        "a cinematic medium shot that captures her full dance movements and revealing outfit against the backdrop",
        "a dramatic side-angle shot highlighting the curves of her silhouette, exposed skin, and hip movements",
        "a slow-motion full-body shot that emphasizes every bounce, sway, and curve of her voluptuous figure",
        "a follow-shot from behind focusing on her hip movements, exposed back, and the flow of her minimal outfit"
    ],
    
    "lighting": [
        "bathed in warm, golden Indian sunset light creating an ethereal glow around her exposed skin",
        "dramatically lit by colorful festival lights and diyas creating vibrant shadows on her curves",
        "illuminated by soft, romantic moonlight mixed with traditional oil lamps highlighting her figure",
        "backlit by bright Bollywood-style stage lights creating a star-like silhouette of her voluptuous body",
        "under the warm glow of traditional Indian lanterns and fairy lights that accentuate her skin",
        "in bright, high-key professional lighting that showcases every detail of her revealing outfit and curves"
    ]
}

def generate_prompts_ollama(model, num_prompts, ollama_api_url):
    """
    🔥 ENHANCED: Generates prompts using ONE consistent theme AND attire per run.
    All prompts in this run will use the SAME location/theme AND outfit but vary other elements for diversity.
    """
    logger.info(f"🚀 Generating {num_prompts} prompts with ONE CONSISTENT THEME + ATTIRE (Model: {model})...")
    
    # 🔥 STEP 1: SELECT ONE THEME AND ONE ATTIRE FOR THE ENTIRE RUN!
    selected_location = random.choice(PROMPT_ELEMENTS["locations"])
    selected_attire = random.choice(PROMPT_ELEMENTS["attires"])
    
    # 🔥 LOG THE SELECTED THEME AND ATTIRE PROMINENTLY
    logger.info("=" * 100)
    logger.info(f"🎭 SELECTED THEME FOR THIS ENTIRE RUN:")
    logger.info(f"    LOCATION: {selected_location}")
    logger.info("=" * 100)
    logger.info(f"👗 SELECTED ATTIRE FOR THIS ENTIRE RUN:")
    logger.info(f"    OUTFIT: {selected_attire}")
    logger.info("=" * 100)
    
    print("=" * 100)
    print(f"🎭 THIS RUN'S CONSISTENT THEME:")
    print(f"    LOCATION: {selected_location}")
    print(f"👗 THIS RUN'S CONSISTENT ATTIRE:")
    print(f"    OUTFIT: {selected_attire}")
    print("=" * 100)
    
    generated_prompt_list = []

    for i in range(num_prompts):
        # 🔥 STEP 2: USE THE SAME LOCATION AND ATTIRE FOR ALL PROMPTS IN THIS RUN!
        location = selected_location  # FIXED THEME - NO RANDOM SELECTION HERE!
        attire = selected_attire      # FIXED ATTIRE - NO RANDOM SELECTION HERE!
        
        # 🔥 STEP 3: VARY OTHER ELEMENTS FOR DIVERSITY WITHIN THE SAME THEME + ATTIRE
        dance_action = random.choice(PROMPT_ELEMENTS["dance_actions"])
        camera_shot = random.choice(PROMPT_ELEMENTS["camera_shots"])
        lighting = random.choice(PROMPT_ELEMENTS["lighting"])

        # Create a rich, detailed description for Ollama to synthesize
        dynamic_scene_description = (
            f"The main subject is a gorgeous, stunning Indian woman with extremely voluptuous curves, very large natural breasts with dramatic cleavage, "
            f"and an incredibly sexy, confident presence. She has beautiful Indian features, long dark hair, and radiant skin. "
            f"She is wearing {attire} that shows maximum skin while being extremely revealing but tastefully covered (nipples covered, no nudity). "
            f"She is at {location}. "  # 🔥 SAME LOCATION FOR ALL PROMPTS!
            f"The lighting is {lighting}. "
            f"She is {dance_action}. "
            f"The camera is capturing this with {camera_shot}. "
            f"The atmosphere is high-energy, sensual, and culturally rich. Her outfit reveals her curves, massive cleavage, midriff, "
            f"and hips in an artistic but maximally revealing way while maintaining appropriate coverage. She is the absolute focus with incredible sex appeal and viral potential."
        )

        # The instruction for Ollama guides it to use our detailed scene
        formatted_prompt = (
            f"""Synthesize the following scene details into ONE single-line, highly-detailed, and evocative cinematic prompt for AI video generation.
            The final prompt must be a masterpiece of visual description focusing on a stunning Indian woman with maximum sex appeal.
            Strictly adhere to all details provided. Do not add commentary or extra text.
            IMPORTANT: The main subject must be a beautiful Indian woman with extremely voluptuous curves, large breasts with dramatic cleavage, and revealing/provocative clothing that covers nipples (no nudity, no exposed nipples, tastefully covered).
            The dance must be energetic Indian dance styles with chest bouncing, hip movements, and sensual body movements.
            Emphasize her Indian heritage, cultural elements, and maximum skin showing in a tasteful but extremely revealing way with appropriate coverage.
            Make it viral-worthy with high sex appeal while maintaining artistic quality and appropriate coverage standards.
            Respond ONLY with a valid JSON object in the format: {{"prompts": ["<your synthesized prompt here>"]}}

            Scene Details to Synthesize:
            ---
            {dynamic_scene_description}
            ---
            """
        )
        
        logger.info(f"\n🧠 Requesting Prompt [{i+1}/{num_prompts}] | CONSISTENT THEME + ATTIRE")
        logger.debug(f"   Theme: {selected_location[:60]}...")
        logger.debug(f"   Attire: {selected_attire[:60]}...")
        logger.debug(f"   Variation elements: {dance_action[:40]}... | {camera_shot[:30]}... | {lighting[:30]}...")
        
        ollama_success = False
        last_error = None

        for attempt in range(OLLAMA_MAX_RETRIES):
            logger.debug(f"   Ollama Attempt {attempt+1}/{OLLAMA_MAX_RETRIES}...")
            try:
                response = requests.post(ollama_api_url, json={"model": model, "prompt": formatted_prompt, "stream": False}, timeout=OLLAMA_TIMEOUT)
                response.raise_for_status()
                response_json = response.json()
                generated_text = response_json.get("response", "").strip()
                
                try:
                    start_index = generated_text.find('{')
                    end_index = generated_text.rfind('}')
                    if start_index != -1 and end_index != -1 and start_index < end_index:
                        json_str = generated_text[start_index:end_index+1]
                        parsed = json.loads(json_str)
                        if "prompts" in parsed and isinstance(parsed["prompts"], list) and parsed["prompts"]:
                            prompt_text = parsed["prompts"][0].strip()
                            if prompt_text:
                                logger.info(f"   ✅ Clean Prompt Extracted:\n      '{prompt_text}'")
                                generated_prompt_list.append({
                                    "index": i + 1, 
                                    "run_theme": selected_location,  # 🔥 CONSISTENT THEME TRACKING
                                    "run_attire": selected_attire,   # 🔥 CONSISTENT ATTIRE TRACKING
                                    "dance_action": dance_action,
                                    "camera_shot": camera_shot,
                                    "lighting": lighting,
                                    "generated_prompt": prompt_text
                                })
                                ollama_success = True
                                break
                            else:
                                last_error = ValueError("Empty prompt string in JSON.")
                        else:
                            last_error = ValueError("Invalid JSON structure ('prompts' missing/empty).")
                    else:
                        last_error = ValueError("JSON brackets not found or invalid in Ollama response.")
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
            
            if not ollama_success and attempt < OLLAMA_MAX_RETRIES - 1:
                logger.info(f"      Retrying Ollama in {OLLAMA_RETRY_DELAY}s...")
                time.sleep(OLLAMA_RETRY_DELAY)
            elif not ollama_success:
                logger.error(f"   ❌ Failed to generate prompt [{i+1}] after {OLLAMA_MAX_RETRIES} attempts. Last error: {last_error}")
                generated_prompt_list.append({
                    "index": i + 1, 
                    "run_theme": selected_location,
                    "run_attire": selected_attire,
                    "error": str(last_error)
                })

    successful_count = sum(1 for p in generated_prompt_list if 'error' not in p)
    logger.info(f"✅ Finished generating {successful_count}/{num_prompts} prompts with CONSISTENT THEME + ATTIRE.")
    return generated_prompt_list

# --- Prompt Logging ---
# (Keep same function from v5)
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
# (Keep same function from v5)
def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None, output_subfolder: str, filename_prefix: str, video_start_image: str | None = None):
    # ... (same as v5) ...
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
            if e.response is not None:
                 response = e.response
                 logger.warning(f"      Status Code: {e.response.status_code}")
                 try:
                     error_detail = json.dumps(e.response.json(), indent=2)
                 except json.JSONDecodeError:
                     error_detail = e.response.text[:500]
                 logger.warning(f"      Response Body: {error_detail}...")
            else:
                 logger.warning("      No response object received.")
        except json.JSONDecodeError as e:
             logger.error(f"  ❌ Error decoding JSON response from API server (Attempt {attempt}): {e}")
             if response is not None: logger.debug(f"     Raw Response Text: {response.text[:500]}...")
             else: logger.debug("     No response object available for raw text logging.")
        except Exception as e:
            logger.error(f"  ❌ Unexpected error calling API (Attempt {attempt}): {e}", exc_info=True)

        if attempt < MAX_API_RETRIES:
            logger.info(f"      Retrying in {API_RETRY_DELAY} seconds...")
            time.sleep(API_RETRY_DELAY)
        else:
            logger.error(f"  ❌ {log_prefix} failed after {MAX_API_RETRIES} attempts.")
            return None

    return None

# --- Function to Poll ComfyUI History ---
# (Keep same function from v5)
def check_comfyui_job_status(comfyui_base_url: str, prompt_id: str):
    # ... (same as v5) ...
    if not prompt_id:
        logger.debug("Skipping history check: prompt_id is None or empty.")
        return None
    history_url = f"{comfyui_base_url}/history/{prompt_id}"
    logger.debug(f"Polling ComfyUI: {history_url}")
    try:
        response = requests.get(history_url, timeout=10) # Short timeout for polling
        response.raise_for_status()
        history_data = response.json()
        if prompt_id in history_data:
            logger.debug(f"History found for prompt_id {prompt_id}.")
            return history_data[prompt_id]
        else:
            logger.debug(f"Prompt_id {prompt_id} not found in history response (running/pending).")
            return None
    except requests.exceptions.Timeout:
        logger.warning(f"Polling /history timed out for {prompt_id}.")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error polling /history/{prompt_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Error decoding history JSON for {prompt_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error polling history for {prompt_id}: {e}", exc_info=True)
        return None

# --- Function to Extract Output Filenames from History (Handles Batches) ---
def get_output_filenames_from_history(history_entry: dict, output_node_id: str):
    """
    Parses history data to find ALL filenames from a specific Save node.
    Returns a list of Path objects (relative paths).
    """
    output_paths = []
    if not history_entry or 'outputs' not in history_entry:
        logger.warning(f"History entry invalid or missing 'outputs' key for node {output_node_id}.")
        logger.debug(f"Invalid history entry data: {json.dumps(history_entry, indent=2)}")
        return output_paths # Return empty list

    if output_node_id in history_entry['outputs']:
        node_output = history_entry['outputs'][output_node_id]
        logger.debug(f"Outputs found for node {output_node_id}: {json.dumps(node_output, indent=2)}")

        # Check common output structures (SaveImage, SaveImageWEBP, VHS_SaveVideo, etc.)
        # Process 'images' first
        if 'images' in node_output and isinstance(node_output['images'], list):
            for image_info in node_output['images']: # Iterate through all images in the list
                if isinstance(image_info, dict) and \
                   'filename' in image_info and \
                   'subfolder' in image_info and \
                   'type' in image_info and image_info['type'] == 'output':
                    subfolder = image_info['subfolder']
                    filename = image_info['filename']
                    relative_path = Path(subfolder) / filename if subfolder else Path(filename)
                    output_paths.append(relative_path)
                    logger.debug(f"Extracted relative image path from history: {relative_path}")
                else:
                    logger.warning(f"Image info dict for node {output_node_id} missing required keys or type is not 'output'. Image Info: {image_info}")

        # Check for 'gifs' (used by some animated nodes like AnimateDiffCombine)
        elif 'gifs' in node_output and isinstance(node_output['gifs'], list):
             for gif_info in node_output['gifs']:
                if isinstance(gif_info, dict) and \
                   'filename' in gif_info and \
                   'subfolder' in gif_info and \
                   'type' in gif_info and gif_info['type'] == 'output':
                    subfolder = gif_info['subfolder']
                    filename = gif_info['filename']
                    relative_path = Path(subfolder) / filename if subfolder else Path(filename)
                    output_paths.append(relative_path)
                    logger.debug(f"Extracted relative gif path from history: {relative_path}")
                else:
                    logger.warning(f"Gif info dict for node {output_node_id} missing required keys or type is not 'output'. Gif Info: {gif_info}")

        # Add checks for other potential outputs if needed (e.g., 'videos')

        if not output_paths:
             logger.warning(f"Node {output_node_id} output found, but no recognized output key ('images', 'gifs') found or list is empty.")
             logger.debug(f"Node output details: {node_output}")

    else:
         logger.warning(f"Node ID {output_node_id} not found in history entry outputs.")
         logger.debug(f"Available output node IDs in history: {list(history_entry['outputs'].keys())}")

    if not output_paths:
        logger.warning(f"Could not find any valid image/gif outputs for node {output_node_id} in history entry.")

    return output_paths # Return list (possibly empty)


# --- Flask Approval Server (Modified for Batches) ---
approval_app = Flask(__name__)
approval_data = {
    "run_details_for_approval": [], # Will store items with generated_image_paths
    "comfyui_output_base": None,
    "approval_file_path": None,
    "shutdown_event": None,
}

@approval_app.route('/')
def index():
    """Renders the approval page, handling batches."""
    global approval_data
    items_html = ""
    if not approval_data["run_details_for_approval"]:
        items_html = "<p>No successfully generated images found to approve.</p>"
    else:
        for item in approval_data["run_details_for_approval"]:
            item_index = item['index']
            image_paths = item.get('generated_image_paths', []) # Get the list of paths

            if not image_paths:
                items_html += f"""
                <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top; width: 256px; height: 100px; background-color: #eee;">
                    <p><b>Index: {item_index}</b></p>
                    <p style="color: red;">Error: No image paths found</p>
                </div>
                """
                continue # Skip to next item

            items_html += f'<fieldset style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top;">'
            items_html += f'<legend><b>Index: {item_index}</b> (Prompt: {item["prompt"][:40]}...)</legend>'

            for batch_idx, img_path in enumerate(image_paths):
                img_src_url = None
                display_filename = "N/A"
                checkbox_value = f"{item_index}{BATCH_SEPARATOR}{batch_idx}" # Combine original index and batch index

                if img_path and isinstance(img_path, Path) and img_path.is_file():
                    try:
                        # Create URL-safe relative path for the /images/ route
                        relative_path_for_url = img_path.relative_to(approval_data["comfyui_output_base"]).as_posix()
                        # URL encode the path to handle special characters in filenames/folders
                        img_src_url = url_for('serve_image', filename=relative_path_for_url) # Use url_for for safety
                        display_filename = img_path.name
                    except ValueError:
                        logger.warning(f"Image path {img_path} is not relative to base {approval_data['comfyui_output_base']}. Cannot display.")
                        img_src_url = None
                        display_filename = f"Error: Path Issue ({img_path.name})"
                    except Exception as e:
                         logger.error(f"Error creating relative path URL for {img_path}: {e}")
                         img_src_url = None
                         display_filename = f"Error: Path URL ({img_path.name})"
                else:
                    logger.warning(f"Item {item_index}, Batch {batch_idx} has invalid or missing image path: {img_path}")
                    display_filename = f"Error: Missing/Invalid Path (Index {item_index}, Batch {batch_idx})"


                if img_src_url:
                    items_html += f"""
                    <div style="border: 1px solid #eee; margin: 5px; padding: 5px; display: inline-block; vertical-align: top;">
                        <p style="font-size: 0.8em; margin: 0 0 5px 0;">Batch Idx: {batch_idx}<br>({display_filename})</p>
                        <img src="{img_src_url}" alt="Generated Image {item_index}_{batch_idx}" style="max-width: 200px; max-height: 200px; display: block; margin-bottom: 5px;">
                        <input type="checkbox" name="approved_item" value="{checkbox_value}" id="img_{checkbox_value}">
                        <label for="img_{checkbox_value}" style="font-size: 0.9em;">Approve</label>
                    </div>
                    """
                else:
                     items_html += f"""
                    <div style="border: 1px solid #eee; margin: 5px; padding: 5px; display: inline-block; vertical-align: top; width: 200px; height: 250px; background-color: #f8f8f8;">
                        <p style="font-size: 0.8em; margin: 0 0 5px 0;">Batch Idx: {batch_idx}</p>
                        <p style="color: red; font-size: 0.8em;">{display_filename}</p>
                        <p>(Cannot display image)</p>
                    </div>
                    """
            items_html += '</fieldset>'


    # Simple HTML structure
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Approval (v6)</title>
        <style> body {{ font-family: sans-serif; }} fieldset {{ min-width: 220px; }} </style>
    </head>
    <body>
        <h1>Approve Images for Video Generation</h1>
        <p>Select the specific images you want to use as starting frames for video generation.</p>
        <form action="/submit" method="post">
            {items_html}
            <div style="clear: both; margin-top: 20px;">
                <button type="submit">Submit Approvals</button>
            </div>
        </form>
    </body>
    </html>
    """
    return render_template_string(html_content)

# FIX: Corrected image serving route
@approval_app.route('/images/<path:filename>')
def serve_image(filename):
    """Serves images from the ComfyUI output directory."""
    global approval_data
    logger.debug(f"Serving image request for relative path: {filename}")
    # filename is expected to be the relative path *within* the comfyui_output_base
    # send_from_directory handles path safety
    try:
        # Ensure the base path exists
        if not approval_data["comfyui_output_base"] or not approval_data["comfyui_output_base"].is_dir():
            logger.error(f"ComfyUI Output Base directory is not set or doesn't exist: {approval_data['comfyui_output_base']}")
            return "Configuration Error: Output directory not found", 500

        logger.debug(f"Attempting to send '{filename}' from directory '{approval_data['comfyui_output_base']}'")
        return send_from_directory(approval_data["comfyui_output_base"], filename)
    except FileNotFoundError:
        # Construct the full path attempted for better logging
        full_attempted_path = approval_data["comfyui_output_base"] / filename
        logger.error(f"File not found for serving: {full_attempted_path}")
        return "File Not Found", 404
    except Exception as e:
         # Log the full path attempted as well
         full_attempted_path = approval_data["comfyui_output_base"] / filename
         logger.error(f"Error serving file {full_attempted_path}: {e}", exc_info=True)
         return "Server Error", 500


@approval_app.route('/submit', methods=['POST'])
def submit_approval():
    """Handles the form submission, saves approved image details, and triggers shutdown."""
    global approval_data
    approved_items_values = request.form.getlist('approved_item') # Get list like ["1__batch__0", "2__batch__3"]

    approved_details_list = []
    original_indices_approved = set()

    for value in approved_items_values:
        try:
            parts = value.split(BATCH_SEPARATOR)
            if len(parts) == 2:
                original_idx = int(parts[0])
                batch_img_idx = int(parts[1])

                # Find the corresponding run_details item and image path
                found = False
                for item in approval_data["run_details_for_approval"]:
                    if item['index'] == original_idx:
                        if 0 <= batch_img_idx < len(item.get('generated_image_paths', [])):
                            img_path = item['generated_image_paths'][batch_img_idx]
                            approved_details_list.append({
                                "original_index": original_idx,
                                "batch_image_index": batch_img_idx,
                                "approved_image_path": str(img_path.resolve()), # Store absolute path as string
                                "prompt": item['prompt'], # Include for reference
                                "face_filename": item['face_filename'], # Include for video stage
                                "base_image_prefix": item['image_prefix'] # Base prefix before batch num
                            })
                            original_indices_approved.add(original_idx)
                            found = True
                            break # Found the image for this batch index
                        else:
                             logger.warning(f"Received invalid batch index {batch_img_idx} for original index {original_idx}. Skipping.")
                             break # Stop searching for this original index
                if not found:
                     logger.warning(f"Could not find original run detail item for index {original_idx} from value '{value}'. Skipping.")

            else:
                 logger.warning(f"Received invalid checkbox value format: {value}. Skipping.")
        except ValueError:
            logger.warning(f"Received non-integer index value in: {value}. Skipping.")
        except Exception as e:
            logger.error(f"Error processing approved value '{value}': {e}", exc_info=True)

    logger.info(f"Received approval for {len(approved_details_list)} specific images.")
    logger.info(f"Original indices involved: {sorted(list(original_indices_approved))}")

    # Save to file
    try:
        # Save the list of approved image details directly
        with open(approval_data["approval_file_path"], 'w', encoding='utf-8') as f:
            json.dump({"approved_images": approved_details_list}, f, indent=2, ensure_ascii=False)
        logger.info(f"Approved image details saved to: {approval_data['approval_file_path']}")
        # Trigger shutdown
        if approval_data["shutdown_event"]:
            logger.info("Signaling main thread to shut down approval server.")
            approval_data["shutdown_event"].set()
        else:
             logger.error("Shutdown event not set in approval_data!")
        return "Approvals submitted successfully! You can close this window."
    except Exception as e:
        logger.error(f"Failed to save approval file: {e}", exc_info=True)
        return "Error saving approvals. Please check logs.", 500

def run_approval_server(run_details_list, comfy_output_base_path, file_path, shutdown_event_obj):
    """Starts the Flask server in a separate thread."""
    global approval_data
    # Filter for items that have at least one valid image path
    approval_data["run_details_for_approval"] = [
        item for item in run_details_list
        if item.get('generated_image_paths') and isinstance(item['generated_image_paths'], list) and item['generated_image_paths']
    ]
    approval_data["comfyui_output_base"] = comfy_output_base_path
    approval_data["approval_file_path"] = file_path
    approval_data["shutdown_event"] = shutdown_event_obj

    logger.info(f"Starting approval server on http://0.0.0.0:{APPROVAL_SERVER_PORT}")
    try:
        approval_app.run(host='0.0.0.0', port=APPROVAL_SERVER_PORT, debug=False)
    except Exception as e:
         logger.error(f"Failed to start approval server: {e}", exc_info=True)
         if approval_data["shutdown_event"]:
             approval_data["shutdown_event"].set()

# --- Main Execution Logic ---
if __name__ == "__main__":
    print("DEBUG: Entering main execution block.")
    logger.info("=" * 50); logger.info(f"Starting Automation v6 Run: {datetime.now()}"); logger.info("=" * 50)

    config = load_config("config_with_faceswap.json")
    if not config: print("DEBUG: Config loading failed. Exiting."); sys.exit(1)
    print("DEBUG: Config loaded successfully in main.")

    API_SERVER_URL = config['api_server_url']
    COMFYUI_BASE_URL = config['comfyui_api_url']

    # --- Verify User-Set Paths ---
    if not COMFYUI_INPUT_DIR_BASE.is_dir():
        logger.critical(f"CRITICAL: Configured ComfyUI input directory does not exist: {COMFYUI_INPUT_DIR_BASE}"); sys.exit(1)
    if not COMFYUI_OUTPUT_DIR_BASE.is_dir():
        logger.error(f"CRITICAL WARNING: Configured ComfyUI output directory does not exist: {COMFYUI_OUTPUT_DIR_BASE}")
        logger.error("Image approval UI WILL FAIL to display images!")
        # Consider exiting: sys.exit(1)

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
        logger.critical(f"Failed to create temp video start directory: {e}", exc_info=True); sys.exit(1)

    # 1. Generate Prompts
    # (Keep prompt gen call)
    print("DEBUG: Starting prompt generation...")
    prompts_data = generate_prompts_ollama(config["ollama_model"], config["num_prompts"], config.get("ollama_api_url", "http://localhost:11434/api/generate"))
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
    if source_faces_dir.is_dir():
        try:
            face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
            logger.info(f"Found {len(face_files)} face images in {source_faces_dir}.")
        except Exception as e: logger.error(f"Error scanning source faces directory {source_faces_dir}: {e}", exc_info=True)
    else: logger.warning(f"Source faces directory not found: {source_faces_dir}")
    if not face_files: logger.warning("No valid face images found. Face swap will be skipped.")
    print(f"DEBUG: Found {len(face_files)} face files.")

    # 3. Create Script Output Directory
    print("DEBUG: Defining main run folder name...")
    script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_output_base = config['output_folder']
    main_run_folder_path = script_output_base / f"Run_{script_run_timestamp}"
    try:
        main_run_folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created script run output directory: {main_run_folder_path}")
    except Exception as e: logger.critical(f"Failed to create script output directory: {e}", exc_info=True); sys.exit(1)

    # --- Store details for tracking ---
    run_details = [] # List of dictionaries tracking each original prompt/index

    # --- Find Image Save Node ID ---
    image_save_node_id = None
    image_save_node_title = "API_Image_Output_SaveNode" # Must match title in JSON
    try:
        img_workflow_path_from_config = (SCRIPT_DIR / config["base_workflow_image"]).resolve()
        logger.debug(f"Checking for Save Node '{image_save_node_title}' in: {img_workflow_path_from_config}")
        if not img_workflow_path_from_config.is_file(): logger.error(f"Image workflow path from config not found: {img_workflow_path_from_config}")
        else:
             with open(img_workflow_path_from_config, "r", encoding="utf-8") as f: temp_img_wf = json.load(f)
             image_save_node_id = find_node_id_by_title(temp_img_wf, image_save_node_title, img_workflow_path_from_config.name)
             if not image_save_node_id: logger.error(f"Could not find node titled '{image_save_node_title}'. Polling will fail.")
             else: logger.info(f"Found Image Save Node '{image_save_node_title}' with ID: {image_save_node_id}")
    except Exception as e: logger.error(f"Error finding SaveImage node ID: {e}", exc_info=True)

    # ====================================================
    # 🔹 STAGE 1: Submit Image Generation Jobs
    # ====================================================
    logger.info(f"\n--- STAGE 1: Submitting Image Generation for {len(valid_prompts)} Prompts ---")
    image_progress_bar = tqdm(valid_prompts, desc="Submitting Images")
    submitted_image_jobs = 0
    comfyui_image_output_subfolder = f"Run_{script_run_timestamp}/all_images"

    for item_index, item in enumerate(image_progress_bar):
        idx = item["index"]
        prompt = item["generated_prompt"]
        selected_face_path = None
        face_filename_only = None
        if face_files:
            selected_face_path = face_files[item_index % len(face_files)]
            face_filename_only = selected_face_path.name
            logger.info(f"Selected face for Index {idx}: {face_filename_only}")
        else: logger.info(f"No face selected for Index {idx}.")

        image_filename_prefix = f"{idx:03d}_{'swapped' if face_filename_only else 'raw'}" # Base prefix

        image_progress_bar.set_description(f"Image Req {idx}/{len(valid_prompts)}")
        logger.info(f"\n🖼️ Preparing Image Request [{idx}/{len(valid_prompts)}]")

        comfy_image_prompt_id = trigger_generation(
            API_SERVER_URL, "generate_image", prompt, face_filename_only,
            comfyui_image_output_subfolder, image_filename_prefix
        )

        run_details.append({
            'index': idx,
            'prompt': prompt,
            'background': item.get('background', 'N/A'),
            'face_filename': face_filename_only,
            'image_prefix': image_filename_prefix, # Base prefix
            'image_prompt_id': comfy_image_prompt_id,
            'image_job_status': 'submitted' if comfy_image_prompt_id else 'failed',
            'generated_image_paths': [], # Initialize as empty list
            'video_jobs': [] # Will store details for each video generated from this index
        })

        if comfy_image_prompt_id: submitted_image_jobs += 1
        else: logger.error(f"Failed API call for Image {idx}. Check API Server logs.")
        time.sleep(0.5)

    logger.info(f"--- STAGE 1: {submitted_image_jobs}/{len(valid_prompts)} Image Generation Requests Submitted ---")

    # ========================================================
    # 🔹 STAGE 1.5: Wait for Image Jobs to Complete (Polling - Modified for Batches)
    # ========================================================
    if not image_save_node_id:
        logger.error("Cannot poll images: Image Save Node ID not found. Skipping polling, approval, video gen.")
    elif submitted_image_jobs == 0:
         logger.warning("No image jobs submitted. Skipping polling.")
    else:
        logger.info(f"\n--- STAGE 1.5: Waiting for {submitted_image_jobs} Image Jobs to Complete (Polling /history) ---")
        jobs_to_poll = [d for d in run_details if d['image_prompt_id']]
        polling_progress = tqdm(total=len(jobs_to_poll), desc="Polling Images")
        completed_image_jobs_count = 0

        for details in jobs_to_poll:
            idx = details['index']
            prompt_id = details['image_prompt_id']
            logger.info(f"   Polling for Image Job {idx} (Prompt ID: {prompt_id})...")
            start_time = datetime.now()
            job_done = False
            while datetime.now() - start_time < timedelta(seconds=POLLING_TIMEOUT_IMAGE):
                history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
                if history_data:
                    logger.info(f"   ✅ Image Job {idx} completed (History found).")
                    details['image_job_status'] = 'completed_history_found'
                    relative_output_paths = get_output_filenames_from_history(history_data, image_save_node_id) # Get list

                    if relative_output_paths:
                        found_files_count = 0
                        details['generated_image_paths'] = [] # Reset/init list
                        for rel_path in relative_output_paths:
                            full_output_path = (COMFYUI_OUTPUT_DIR_BASE / rel_path).resolve()
                            details['generated_image_paths'].append(full_output_path) # Add Path object
                            if full_output_path.is_file():
                                logger.info(f"      Found output file ({len(details['generated_image_paths'])}/{len(relative_output_paths)}): {full_output_path}")
                                found_files_count += 1
                            else:
                                 logger.warning(f"      WARNING: History reported file {full_output_path}, but it doesn't exist on disk!")

                        if found_files_count == len(relative_output_paths):
                             details['image_job_status'] = 'completed_all_files_found'
                             logger.info(f"      All {found_files_count} expected files found.")
                        elif found_files_count > 0:
                             details['image_job_status'] = 'completed_some_files_missing'
                             logger.warning(f"      Only {found_files_count}/{len(relative_output_paths)} expected files found.")
                        else:
                             details['image_job_status'] = 'completed_all_files_missing'
                             logger.error(f"      ERROR: History reported {len(relative_output_paths)} files, but none exist on disk!")
                    else:
                        logger.error(f"      Image Job {idx} finished, but could not find any output filenames in history for node {image_save_node_id}!")
                        details['image_job_status'] = 'completed_no_output_found'

                    job_done = True
                    completed_image_jobs_count += 1
                    break # Exit polling loop for this job
                else: # Still waiting
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    polling_progress.set_description(f"Polling ImgJob {idx} ({int(elapsed_time)}s)")
                    time.sleep(POLLING_INTERVAL)

            if not job_done:
                 logger.error(f"   ❌ Polling timed out for Image Job {idx} (Prompt ID: {prompt_id}) after {POLLING_TIMEOUT_IMAGE} seconds.")
                 details['image_job_status'] = 'polling_timeout'
            polling_progress.update(1)

        polling_progress.close()
        logger.info(f"--- STAGE 1.5: Finished Polling Image Jobs ({completed_image_jobs_count}/{len(jobs_to_poll)} completed within timeout) ---")

    # ====================================================
    # STAGE 1.7: Image Approval (Web UI & Telegram in Parallel)
    # ====================================================
    logger.info(f"\n--- STAGE 1.7: Image Approval (Web UI & Telegram) - Faceswap Version ---")

    # Collect only those run_details that have at least one image path
    run_details_for_approval = [
        d for d in run_details
        if d.get('image_job_status') in ('completed_all_files_found', 'completed_some_files_missing')
        and d.get('generated_image_paths')
    ]

    # Flatten all generated image paths (absolute) into a list for Telegram
    all_generated_image_paths: list[str] = []
    for item in run_details_for_approval:
        for img_path in item['generated_image_paths']:
            all_generated_image_paths.append(str(img_path))

    # Prepare paths
    approval_file_path = main_run_folder_path / APPROVAL_FILENAME
    
    if not approval_file_path.parent.exists():
        approval_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Launch both UIs
    def start_flask_approval():
        shutdown_event = threading.Event()
        try:
            run_approval_server(
                run_details_for_approval,
                COMFYUI_OUTPUT_DIR_BASE,
                approval_file_path,
                shutdown_event
            )
        except Exception as e:
            logger.error(f"Flask approval server encountered an error: {e}", exc_info=True)

    def start_telegram_approval():
        # Clear any existing approval state files (but do not delete image files)
        if TELEGRAM_APPROVALS_JSON.exists():
            TELEGRAM_APPROVALS_JSON.unlink()
        if TOKEN_MAP_JSON.exists():
            TOKEN_MAP_JSON.unlink()

        # Ensure directory exists
        if not TELEGRAM_APPROVALS_DIR.exists():
            TELEGRAM_APPROVALS_DIR.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                [sys.executable, str(SEND_TELEGRAM_SCRIPT)] + all_generated_image_paths,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Telegram approval process failed: {e}")
        except Exception as e:
            logger.error(f"Failed to start Telegram approval script: {e}", exc_info=True)

    flask_thread = threading.Thread(target=start_flask_approval, daemon=True)
    telegram_thread = threading.Thread(target=start_telegram_approval, daemon=True)
    flask_thread.start()
    telegram_thread.start()

    print("=" * 100)
    print(f"🎭 FACESWAP VERSION: Face-swapped images with dynamic prompts")
    print("🟢 You can approve/reject images via browser (http://localhost:5005) OR on Telegram.")
    print("   📝 IMPORTANT: Script will proceed to video generation after ALL images are reviewed on Telegram.")
    print("   📝 OR submit your selections in the web browser to proceed immediately.")
    print("=" * 100)

    # Enhanced approval waiting - Wait for ALL images to be reviewed
    approved_image_details: list[dict] = []
    while True:
        # Check Web UI approvals (Web UI automatically completes on submit)
        if approval_file_path.exists():
            try:
                with open(approval_file_path, "r", encoding="utf-8") as f:
                    approval_result = json.load(f)
                    approved_image_details = approval_result.get("approved_images", [])
                if approved_image_details:
                    logger.info(f"[Main] Loaded {len(approved_image_details)} approved image details from Web UI.")
                    print("[Main] Web UI approvals submitted, proceeding to video generation...")
                    break
            except Exception as e:
                logger.error(f"Error reading web approval file {approval_file_path}: {e}")

        # 🔥 Check Telegram approvals - Wait for ALL images to have status
        if TELEGRAM_APPROVALS_JSON.exists():
            try:
                with open(TELEGRAM_APPROVALS_JSON, "r", encoding="utf-8") as f:
                    telegram_result = json.load(f)
                
                # Check if ALL sent images have been reviewed (have status)
                total_images_sent = len(all_generated_image_paths)
                images_with_status = sum(1 for info in telegram_result.values() 
                                       if isinstance(info, dict) and info.get("status") is not None)
                
                if images_with_status == total_images_sent and total_images_sent > 0:
                    # All images reviewed! Count approvals and rejections
                    approved_paths = [path for path, info in telegram_result.items() 
                                    if isinstance(info, dict) and info.get("status") == "approve"]
                    rejected_paths = [path for path, info in telegram_result.items() 
                                    if isinstance(info, dict) and info.get("status") == "reject"]
                    
                    logger.info(f"[Main] All Telegram images reviewed! {len(approved_paths)} approved, {len(rejected_paths)} rejected")
                    print(f"[Main] ✅ All Telegram images reviewed! {len(approved_paths)} approved, {len(rejected_paths)} rejected")
                    
                    # Build approved_image_details in the same format as Web UI
                    temp_approved_list: list[dict] = []
                    for img_path_str in approved_paths:
                        img_path_obj = Path(img_path_str)
                        # Find corresponding run_details entry
                        for item in run_details_for_approval:
                            if img_path_obj in item['generated_image_paths']:
                                orig_index = item['index']
                                batch_index = item['generated_image_paths'].index(img_path_obj)
                                temp_approved_list.append({
                                    "original_index": orig_index,
                                    "batch_image_index": batch_index,
                                    "approved_image_path": str(img_path_obj.resolve()),
                                    "prompt": item['prompt'],
                                    "face_filename": item['face_filename'],
                                    "base_image_prefix": item['image_prefix']
                                })
                                break
                    
                    approved_image_details = temp_approved_list
                    logger.info(f"[Main] Final result: {len(approved_image_details)} images approved for video generation.")
                    print(f"[Main] Proceeding to video generation with {len(approved_image_details)} approved images...")
                    break
                else:
                    # Still waiting for more reviews
                    if total_images_sent > 0:
                        logger.debug(f"[Main] Telegram progress: {images_with_status}/{total_images_sent} images reviewed")
                        
            except Exception as e:
                logger.error(f"Error reading Telegram approval file {TELEGRAM_APPROVALS_JSON}: {e}")

        time.sleep(2)

    # Copy approved images to a dedicated folder
    approved_images_folder_path = main_run_folder_path / APPROVED_IMAGES_SUBFOLDER
    try:
        approved_images_folder_path.mkdir(exist_ok=True)
        logger.info(f"Created/ensured approved images folder: {approved_images_folder_path}")
    except Exception as e:
        logger.error(f"Failed to create approved images folder: {e}", exc_info=True)

    copied_count = 0
    for idx, approved_info in enumerate(approved_image_details):
        try:
            source_img_path = Path(approved_info['approved_image_path'])
            orig_idx = approved_info['original_index']
            batch_idx = approved_info['batch_image_index']
            dest_filename = f"approved_{orig_idx:03d}_batch{batch_idx}_{source_img_path.name}"
            dest_img_path = approved_images_folder_path / dest_filename
            shutil.copyfile(source_img_path, dest_img_path)
            logger.info(f"  ({idx+1}/{len(approved_image_details)}) Copied '{source_img_path.name}' -> '{dest_img_path.name}'")
            copied_count += 1
        except Exception as e:
            logger.error(
                f"    Failed to copy approved image {idx+1} (Index {approved_info.get('original_index', 'N/A')}, "
                f"Batch {approved_info.get('batch_image_index', 'N/A')}): {e}"
            )
    logger.info(f"Finished copying {copied_count}/{len(approved_image_details)} approved images.")

    # ====================================================
    # 🔹 STAGE 2: Submit Video Generation Jobs (for approved images)
    # ====================================================
    if not approved_image_details:
        logger.info("\n--- STAGE 2: No specific images approved for video generation. Skipping video submission. ---")
    else:
        logger.info(f"\n--- STAGE 2: Submitting Video Generation for {len(approved_image_details)} Approved Images ---")
        video_progress_bar = tqdm(approved_image_details, desc="Submitting Videos")
        items_successfully_submitted_video = 0
        all_submitted_video_jobs = [] # Store details of submitted video jobs

        comfyui_video_output_subfolder = f"Run_{script_run_timestamp}/all_videos"

        for approved_idx, approved_info in enumerate(approved_image_details):
            orig_index = approved_info['original_index']
            batch_index = approved_info['batch_image_index']
            prompt = approved_info['prompt']
            face_filename_only = approved_info['face_filename'] # Use face associated with original prompt
            approved_image_path = Path(approved_info['approved_image_path']) # Use the specific approved image path

            # Create a unique video prefix for this specific approved image
            video_filename_prefix = f"{orig_index:03d}_batch{batch_index}_video_{'swapped' if face_filename_only else 'raw'}"

            video_progress_bar.set_description(f"Video Req {approved_idx+1}/{len(approved_image_details)} (OrigIdx {orig_index})")
            logger.info(f"\n🎬 Preparing Video Request [{approved_idx+1}/{len(approved_image_details)}] (Original Index: {orig_index}, Batch Index: {batch_index})")
            logger.info(f"   Using image: {approved_image_path}")

            # --- Copy Approved Image to Temp Dir ---
            temp_start_image_comfy_path_str = None
            if approved_image_path.is_file():
                try:
                    temp_start_filename = f"start_{orig_index:03d}_batch{batch_index}_{datetime.now().strftime('%H%M%S%f')}{approved_image_path.suffix}"
                    temp_dest_path = temp_start_image_dir / temp_start_filename
                    shutil.copyfile(approved_image_path, temp_dest_path)
                    temp_start_image_comfy_path = Path(TEMP_VIDEO_START_SUBDIR) / temp_start_filename
                    temp_start_image_comfy_path_str = temp_start_image_comfy_path.as_posix()
                    logger.info(f"   Copied '{approved_image_path.name}' -> Comfy Input as '{temp_start_image_comfy_path_str}'")
                except Exception as copy_e:
                    logger.error(f"   Failed to copy image '{approved_image_path}' to temp dir: {copy_e}. Video might use default start.", exc_info=True)
                    temp_start_image_comfy_path_str = None
            else:
                logger.warning(f"   Approved image file not found: '{approved_image_path}'. Video might use default start.")
                temp_start_image_comfy_path_str = None

            # Call API Server - Video Endpoint
            comfy_video_prompt_id = trigger_generation(
                API_SERVER_URL, "generate_video", prompt, face_filename_only,
                comfyui_video_output_subfolder, video_filename_prefix,
                video_start_image=temp_start_image_comfy_path_str
            )

            # Store details about this specific video job submission
            video_job_info = {
                "original_index": orig_index,
                "batch_image_index": batch_index,
                "video_prefix": video_filename_prefix,
                "video_prompt_id": comfy_video_prompt_id,
                "video_job_status": 'submitted' if comfy_video_prompt_id else 'failed',
                "approved_image_used": str(approved_image_path)
            }
            all_submitted_video_jobs.append(video_job_info)

            # Also update the original run_details entry (optional but can be useful)
            for detail in run_details:
                 if detail['index'] == orig_index:
                      detail['video_jobs'].append(video_job_info)
                      break

            if comfy_video_prompt_id:
                 items_successfully_submitted_video += 1
            else:
                 logger.error(f"Failed API call for Video (OrigIdx {orig_index}, Batch {batch_index}). Check API Server logs.")
            time.sleep(0.5)

        logger.info(f"--- STAGE 2: {items_successfully_submitted_video}/{len(approved_image_details)} Video Generation Requests Submitted ---")

    # ========================================================
    # 🔹 STAGE 2.5: Wait for Video Jobs to Complete (Optional Polling)
    # ========================================================
    video_ids_to_poll = [job['video_prompt_id'] for job in all_submitted_video_jobs if job['video_prompt_id']]
    if video_ids_to_poll:
        logger.info(f"\n--- STAGE 2.5: Waiting for {len(video_ids_to_poll)} Video Jobs to Complete (Polling /history) ---")
        video_polling_progress = tqdm(total=len(video_ids_to_poll), desc="Polling Videos")
        start_poll_time_video = datetime.now()
        overall_video_timeout = POLLING_TIMEOUT_VIDEO * len(video_ids_to_poll)
        active_video_poll_ids = set(video_ids_to_poll)
        completed_video_count = 0

        while active_video_poll_ids and (datetime.now() - start_poll_time_video < timedelta(seconds=overall_video_timeout)):
            completed_in_pass = set()
            for prompt_id in list(active_video_poll_ids):
                 history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
                 if history_data:
                     logger.info(f"   ✅ Video job with Prompt ID {prompt_id} confirmed complete.")
                     # Update status in all_submitted_video_jobs
                     for job in all_submitted_video_jobs:
                          if job['video_prompt_id'] == prompt_id:
                               job['video_job_status'] = 'completed'
                               break
                     # Also update in run_details if needed (more complex search)
                     # ...
                     completed_in_pass.add(prompt_id)
                     completed_video_count = len(video_ids_to_poll) - len(active_video_poll_ids) + len(completed_in_pass)
                     video_polling_progress.n = completed_video_count
                     video_polling_progress.refresh()

            active_video_poll_ids -= completed_in_pass

            if not active_video_poll_ids:
                 logger.info("   ✅ All submitted video jobs appear complete.")
                 break

            elapsed_time_total = (datetime.now() - start_poll_time_video).total_seconds()
            video_polling_progress.set_description(f"Polling Videos ({completed_video_count}/{len(video_ids_to_poll)} done | {int(elapsed_time_total)}s)")
            time.sleep(POLLING_INTERVAL * 2)

        video_polling_progress.close()
        remaining_ids = len(active_video_poll_ids)
        if remaining_ids > 0:
             logger.warning(f"--- STAGE 2.5: Video polling finished, but {remaining_ids}/{len(video_ids_to_poll)} jobs did not return history within timeout. ---")
             # Mark remaining as timeout
             for job in all_submitted_video_jobs:
                  if job['video_prompt_id'] in active_video_poll_ids:
                       job['video_job_status'] = 'polling_timeout'
        else:
             logger.info(f"--- STAGE 2.5: Finished Polling Videos ---")
    else:
         logger.info("\n--- STAGE 2.5: No successful video submissions to poll. ---")

    # ====================================================
    # 🔹 STAGE 3: Cleanup Temp Files
    # ====================================================
    # (Keep cleanup logic the same as v5)
    logger.info(f"\n--- STAGE 3: Cleaning up temporary start images... ---")
    try:
        if temp_start_image_dir.exists():
            logger.info(f"Attempting to remove temp directory: {temp_start_image_dir}")
            shutil.rmtree(temp_start_image_dir)
            if not temp_start_image_dir.exists(): logger.info(f"Successfully removed temp start image directory.")
            else: logger.warning(f"shutil.rmtree completed but directory still exists: {temp_start_image_dir}")
        else: logger.info("Temp start image directory did not exist (or already cleaned).")
    except PermissionError: logger.error(f"Error during temp image cleanup: Permission denied trying to remove {temp_start_image_dir}.")
    except Exception as e: logger.error(f"Error during final temp image cleanup: {e}", exc_info=True)

    # ====================================================
    # 🔹 STAGE 4: Final Summary (Updated)
    # ====================================================
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Automation v6 Run Summary:")
    logger.info(f"   Run Folder (Logs, Approvals): {main_run_folder_path}")
    logger.info(f"   ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")
    logger.info(f"   ComfyUI Run Subfolders: Run_{script_run_timestamp}/all_images, Run_{script_run_timestamp}/all_videos")
    logger.info(f"   Total Prompts Generated: {len(prompts_data)}")
    logger.info(f"   Valid Prompts for Processing: {len(valid_prompts)}")
    logger.info(f"   Image Jobs Submitted: {submitted_image_jobs}")
    image_jobs_completed_files_found = sum(1 for d in run_details if 'files_found' in d.get('image_job_status',''))
    logger.info(f"   Image Jobs Completed (Files Found): {image_jobs_completed_files_found}")
    total_images_generated = sum(len(d.get('generated_image_paths',[])) for d in run_details)
    logger.info(f"   Total Images Generated (Across Batches): {total_images_generated}")
    logger.info(f"   Specific Images Approved for Video: {len(approved_image_details)}")
    logger.info(f"   Video Jobs Submitted: {len(all_submitted_video_jobs)}")
    videos_completed = sum(1 for job in all_submitted_video_jobs if job.get('video_job_status') == 'completed')
    logger.info(f"   Video Jobs Confirmed Complete (via Polling): {videos_completed}")

    # Save final run details (includes nested video jobs)
    final_details_path = main_run_folder_path / f"run_{script_run_timestamp}_details_v6.json"
    try:
        serializable_details = []
        for item in run_details:
            new_item = item.copy()
            # Convert Path objects in generated_image_paths to strings
            if 'generated_image_paths' in new_item and isinstance(new_item['generated_image_paths'], list):
                new_item['generated_image_paths'] = [str(p) for p in new_item['generated_image_paths']]
            # Convert Path objects within video_jobs (if any were stored)
            if 'video_jobs' in new_item and isinstance(new_item['video_jobs'], list):
                 for vj in new_item['video_jobs']:
                      if 'approved_image_used' in vj and isinstance(vj['approved_image_used'], Path):
                           vj['approved_image_used'] = str(vj['approved_image_used'])
            serializable_details.append(new_item)

        with open(final_details_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_details, f, indent=2, ensure_ascii=False)
        logger.info(f"   Final run details saved to: {final_details_path}")
    except Exception as e:
        logger.error(f"   Failed to save final run details: {e}")

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Automation v6 Run Script Finished! {datetime.now()}")
    logger.info("=" * 50)
    print("DEBUG: Script finished.")