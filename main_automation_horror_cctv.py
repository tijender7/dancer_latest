#!/usr/bin/env python
"""Horror CCTV Dancer Automation Pipeline - Horror CCTV Security Footage Content Generation

This script generates horror-themed CCTV security footage using the Horror CCTV LoRA.
Features:
- Abandoned buildings, dark corridors, security camera perspectives
- Monochrome low-quality CCTV footage aesthetic
- Horror monsters and creatures in surveillance footage
- No face swap functionality
- Automatic <lora:horror_cctv_flux:1> trigger word injection

HORROR CCTV v1: ABANDONED LOCATIONS + SURVEILLANCE AESTHETIC + HORROR CREATURES
"""

from __future__ import annotations

import os
import sys
import json
import random
import requests
import shutil
import subprocess
import threading
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote  # For safe image URLs

# --- Third-party Imports ---
from dotenv import load_dotenv

# --- Import Flask for Web UI Approval ---
try:
    from flask import Flask, request, render_template_string, send_from_directory, url_for
    print("DEBUG: Flask imported successfully.")
except ImportError:
    print("ERROR: Flask library not found. Please install it: pip install Flask")
    sys.exit(1)

# --- Import tqdm for progress bars ---
try:
    from tqdm import tqdm
    print("DEBUG: tqdm imported successfully.")
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

# --- Load environment variables (.env) ---
load_dotenv()  # Looking for TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# === UNICODE FIX FOR HORROR CCTV AUTOMATION ===
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

print("DEBUG: Horror CCTV Automation Script execution started.")

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAY = 3
OLLAMA_TIMEOUT = 180
REQUEST_TIMEOUT = 60
POLLING_INTERVAL = 10
POLLING_TIMEOUT_IMAGE = 1800
POLLING_TIMEOUT_VIDEO = 3600

APPROVAL_SERVER_PORT = 5007
APPROVAL_FILENAME = "approved_images.json"              # For Web UI approval file
APPROVED_IMAGES_SUBFOLDER = "approved_images_for_video"  # Where to copy approved images

BATCH_SEPARATOR = "__batch__"  # Separator for checkbox values in Web UI

# Horror CCTV LoRA trigger word
HORROR_CCTV_TRIGGER = "<lora:horror_cctv_flux:1>"

# --- Configurable Paths (User Must Confirm) ---
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")  # <<< USER MUST SET
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content")            # <<< USER MUST SET
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"                   # Subfolder under COMFYUI_INPUT_DIR_BASE

# --- Telegram Approval Paths & Env Vars ---
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"
TELEGRAM_APPROVALS_JSON = TELEGRAM_APPROVALS_DIR / "telegram_approvals.json"
TOKEN_MAP_JSON = TELEGRAM_APPROVALS_DIR / "token_map.json"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env. Telegram approval will fail if chosen.")

def safe_log_message(message):
    """Sanitize Unicode characters for safe logging and printing."""
    if isinstance(message, str):
        replacements = {
            '🎬': '[MOVIE]', '🔤': '[TEXT]', '🟢': '[GREEN]', '📝': '[MEMO]',
            '✅': '[OK]', '❌': '[ERROR]', '⚠️': '[WARN]', '🧹': '[CLEAN]',
            '⏹️': '[STOP]', '🔥': '[FIRE]', '🚀': '[ROCKET]', '📊': '[CHART]',
            '🛑': '[STOP_SIGN]', '💪': '[MUSCLE]', '🏋️': '[WEIGHT]', '📋': '[CLIPBOARD]'
        }
        safe_message = message
        for unicode_char, replacement in replacements.items():
            safe_message = safe_message.replace(unicode_char, replacement)
        return safe_message
    return str(message)

print(f"DEBUG: Script directory: {SCRIPT_DIR}")
print(f"DEBUG: Assumed ComfyUI Input Base: {COMFYUI_INPUT_DIR_BASE}")
print(f"DEBUG: Assumed ComfyUI Output Base: {COMFYUI_OUTPUT_DIR_BASE}")

# --- Logging Setup ---
print("DEBUG: Setting up logging...")
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

log_file = log_directory / f"horror_cctv_automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Horror CCTV Automation Script started")

# --- Configuration Loading ---
def load_config():
    config_path = SCRIPT_DIR / "config_horror_cctv.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config: {e}")
        sys.exit(1)

# --- Horror CCTV Content Elements ---
def get_horror_cctv_prompts():
    """Generate horror CCTV-themed prompts focusing on surveillance footage aesthetics"""
    
    # Horror creatures/entities for CCTV footage
    horror_entities = [
        "shadowy figure", "tall pale creature", "crawling entity", "hooded figure",
        "spider-like monster", "faceless humanoid", "skeletal creature", "ghostly apparition",
        "distorted human shape", "tentacled beast", "lurking predator", "nightmare entity",
        "demonic silhouette", "twisted monster", "eldritch horror", "supernatural being"
    ]
    
    # CCTV/surveillance specific environments
    locations = [
        "abandoned hospital corridor", "empty office building hallway", "deserted subway tunnel",
        "dark parking garage", "derelict warehouse floor", "vacant shopping mall",
        "forgotten basement levels", "industrial facility corridors", "abandoned school hallway",
        "empty apartment building stairwell", "desolate hotel corridor", "underground maintenance tunnel",
        "vacant factory floor", "abandoned prison cell block", "empty airport terminal",
        "deserted retail store", "forgotten archive room", "vacant laboratory corridor"
    ]
    
    # CCTV camera angles and perspectives
    camera_angles = [
        "overhead security camera view", "corner mounted camera angle", "hallway surveillance perspective",
        "ceiling camera looking down", "wall mounted security cam", "high angle security footage",
        "infrared night vision camera", "grainy surveillance feed", "low resolution security cam",
        "wide angle security camera", "fish-eye security lens view", "motion activated camera"
    ]
    
    # CCTV visual qualities
    visual_qualities = [
        "monochrome security footage", "grainy black and white", "low quality surveillance video",
        "pixelated CCTV feed", "distorted security camera", "static interference",
        "timestamp overlay visible", "scan lines across image", "poor lighting conditions",
        "motion blur from camera", "digital noise and artifacts", "infrared lighting effects"
    ]
    
    # Horror actions suitable for CCTV
    actions = [
        "slowly moving through frame", "appearing from shadows", "stalking down corridor",
        "suddenly entering frame", "lurking in dark corner", "creeping along wall",
        "emerging from doorway", "hiding behind pillar", "moving unnaturally",
        "gliding across floor", "climbing on walls", "vanishing into darkness",
        "watching the camera", "approaching surveillance device", "standing motionless"
    ]
    
    entity = random.choice(horror_entities)
    location = random.choice(locations)
    angle = random.choice(camera_angles)
    visual = random.choice(visual_qualities)
    action = random.choice(actions)
    
    # Create CCTV-style prompt
    prompt_templates = [
        f"{visual}, {angle} capturing {entity} {action} in {location}",
        f"Security camera footage: {entity} {action} through {location}, {visual}",
        f"{angle} shows {entity} {action} in {location}, {visual} with poor lighting",
        f"Surveillance feed: {entity} detected {action} in {location}, {visual}",
        f"{visual} from {angle}, {entity} {action} across {location}"
    ]
    
    base_prompt = random.choice(prompt_templates)
    
    # Add CCTV enhancement details
    enhancements = [
        "security camera timestamp visible", "motion detection activated", "night vision mode",
        "emergency lighting only", "flickering fluorescent lights", "complete darkness except infrared",
        "strobing alarm lights", "broken lighting fixture", "emergency exit signs glowing",
        "shadows creating hiding spots", "dust particles in air", "water dripping sounds implied"
    ]
    
    enhancement = random.choice(enhancements)
    final_prompt = f"{base_prompt}, {enhancement}, horror atmosphere, creepy surveillance footage"
    
    return final_prompt

def generate_horror_cctv_prompt_ollama(config):
    """Generate horror CCTV prompt using Ollama with specific CCTV surveillance themes"""
    
    # Horror CCTV specific context for Ollama
    context = """Generate a creative horror prompt for CCTV security camera footage. Focus on:
- Monochrome, low-quality surveillance camera aesthetic
- Horror creatures/monsters in abandoned buildings
- Security camera perspectives (overhead, corner-mounted, hallway views)
- Grainy, pixelated, black and white footage
- Abandoned locations like hospitals, offices, warehouses, tunnels
- Creepy surveillance atmosphere with poor lighting
- Horror entities moving through frame, stalking, lurking
- CCTV-specific visual elements: timestamps, scan lines, motion detection

Create a detailed prompt describing horror CCTV footage."""

    ollama_prompt = f"""You are an expert in creating horror-themed CCTV security footage descriptions. 

{context}

Generate 1 detailed prompt (2-3 sentences) for horror CCTV surveillance footage featuring a monster or horror entity in an abandoned building. Focus on the security camera perspective, monochrome aesthetic, and creepy surveillance atmosphere.

Format: Direct prompt only, no explanations."""

    try:
        # API call to Ollama
        for attempt in range(OLLAMA_MAX_RETRIES):
            try:
                payload = {
                    "model": config["ollama_model"],
                    "prompt": ollama_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.9,
                        "top_p": 0.9,
                        "max_tokens": 200
                    }
                }
                
                response = requests.post(
                    config["ollama_api_url"],
                    json=payload,
                    timeout=OLLAMA_TIMEOUT
                )
                response.raise_for_status()
                
                result = response.json()
                if "response" in result:
                    generated_prompt = result["response"].strip()
                    # Clean up the prompt
                    generated_prompt = generated_prompt.replace('"', '').replace('\n', ' ')
                    if generated_prompt:
                        logger.info(f"Ollama generated horror CCTV prompt: {generated_prompt[:100]}...")
                        return generated_prompt
                        
            except requests.exceptions.RequestException as e:
                logger.warning(f"Ollama attempt {attempt + 1} failed: {e}")
                if attempt < OLLAMA_MAX_RETRIES - 1:
                    time.sleep(OLLAMA_RETRY_DELAY)
                    
    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
    
    # Fallback to predefined horror CCTV prompts
    logger.info("Using fallback horror CCTV prompt generation")
    return get_horror_cctv_prompts()

# --- Generation Functions ---
def generate_prompts(config):
    """Generate horror CCTV prompts using Ollama or fallback method"""
    logger.info("Generating horror CCTV prompts...")
    
    prompts = []
    num_prompts = config.get("num_prompts", 1)
    
    for i in range(num_prompts):
        logger.info(f"Generating prompt {i+1}/{num_prompts}...")
        
        if "ollama_api_url" in config and config["ollama_api_url"]:
            prompt = generate_horror_cctv_prompt_ollama(config)
        else:
            prompt = get_horror_cctv_prompts()
            
        prompts.append(prompt)
        time.sleep(1)  # Small delay between generations
    
    logger.info(f"Generated {len(prompts)} horror CCTV prompts")
    return prompts

def create_run_folder():
    """Create timestamped folder following Run_TIMESTAMP_HorrorCCTV pattern"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"Run_{timestamp}_HorrorCCTV"
    run_folder = COMFYUI_OUTPUT_DIR_BASE / folder_name
    
    try:
        run_folder.mkdir(parents=True, exist_ok=True)
        
        # Create subfolders
        subfolders = ["all_images", "all_videos", "approved_images_for_video"]
        for subfolder in subfolders:
            (run_folder / subfolder).mkdir(exist_ok=True)
            
        logger.info(f"Created horror CCTV run folder: {run_folder}")
        return run_folder
        
    except Exception as e:
        logger.error(f"Failed to create run folder: {e}")
        raise

def call_api(api_url, endpoint, data, timeout=REQUEST_TIMEOUT):
    """Make API call with retry logic"""
    url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    for attempt in range(MAX_API_RETRIES):
        try:
            logger.debug(f"API call attempt {attempt + 1}: {url}")
            response = requests.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"API attempt {attempt + 1} failed: {e}")
            if attempt < MAX_API_RETRIES - 1:
                time.sleep(API_RETRY_DELAY)
            else:
                raise

def generate_images(config, prompts, run_folder):
    """Generate horror CCTV images using the API server"""
    logger.info("Starting horror CCTV image generation...")
    
    api_url = config["api_server_url"]
    images_folder = run_folder / "all_images"
    prompt_ids = []
    
    for i, prompt in enumerate(prompts):
        logger.info(f"Submitting horror CCTV image {i+1}/{len(prompts)}")
        
        # Prepare API request
        request_data = {
            "prompt": prompt,
            "face": None,  # No face swap for horror CCTV
            "output_subfolder": f"{run_folder.name}/all_images",
            "filename_prefix_text": f"{i+1:03d}_horror_cctv"
        }
        
        try:
            response = call_api(api_url, "generate_image", request_data)
            prompt_id = response.get("prompt_id")
            
            if prompt_id:
                prompt_ids.append(prompt_id)
                logger.info(f"Horror CCTV image {i+1} submitted: {prompt_id}")
            else:
                logger.error(f"No prompt_id in response for image {i+1}")
                
        except Exception as e:
            logger.error(f"Failed to submit horror CCTV image {i+1}: {e}")
    
    logger.info(f"Submitted {len(prompt_ids)} horror CCTV images for generation")
    return prompt_ids

def wait_for_images(prompt_ids, images_folder):
    """Wait for horror CCTV images to be generated"""
    logger.info("Waiting for horror CCTV images to be generated...")
    
    start_time = time.time()
    generated_images = []
    
    with tqdm(total=len(prompt_ids), desc="Horror CCTV Images") as pbar:
        while time.time() - start_time < POLLING_TIMEOUT_IMAGE:
            current_images = []
            
            if images_folder.exists():
                current_images = [f for f in images_folder.iterdir() 
                                if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg']]
            
            if len(current_images) >= len(prompt_ids):
                generated_images = sorted(current_images)
                logger.info(f"All {len(generated_images)} horror CCTV images generated")
                break
                
            pbar.n = len(current_images)
            pbar.refresh()
            time.sleep(POLLING_INTERVAL)
    
    if not generated_images:
        logger.error("No horror CCTV images were generated within timeout")
        return []
    
    return generated_images

# Old create_web_approval_ui function removed - replaced with automatic dual approval system

def copy_approved_images(approved_images, run_folder):
    """Copy approved horror CCTV images to video subfolder"""
    if not approved_images:
        logger.warning("No horror CCTV images approved for video generation")
        return []
    
    approved_folder = run_folder / APPROVED_IMAGES_SUBFOLDER
    approved_folder.mkdir(exist_ok=True)
    
    copied_images = []
    for img_path in approved_images:
        if img_path.exists():
            dest_path = approved_folder / img_path.name
            shutil.copy2(img_path, dest_path)
            copied_images.append(dest_path)
            logger.info(f"Copied approved horror CCTV image: {img_path.name}")
    
    logger.info(f"Copied {len(copied_images)} approved horror CCTV images for video generation")
    return copied_images

# --- Flask App for Web-based Image Approval ---
approval_app = Flask(__name__)
approval_data = {
    "run_details_for_approval": [],  # Will store items with generated_image_paths
    "comfyui_output_base": None,
    "approval_file_path": None,
    "shutdown_event": None,
}

@approval_app.route('/')
def index():
    """Renders the horror CCTV approval page."""
    global approval_data
    items_html = ""
    
    if not approval_data["run_details_for_approval"]:
        items_html = "<p>No successfully generated horror CCTV images found to approve.</p>"
    else:
        for item in approval_data["run_details_for_approval"]:
            item_index = item['index']
            image_paths = item.get('generated_image_paths', [])

            if not image_paths:
                items_html += f"""
                <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block;
                            vertical-align: top; width: 256px; height: 100px; background-color: #eee;">
                    <p><b>Index: {item_index}</b></p>
                    <p style="color: red;">Error: No image paths found</p>
                </div>
                """
                continue

            items_html += f'<fieldset style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top;">'
            items_html += f'<legend><b>Index: {item_index}</b> (Prompt: {item["prompt"][:40]}...)</legend>'

            for batch_idx, img_path in enumerate(image_paths):
                img_src_url = None
                display_filename = "N/A"
                checkbox_value = f"{item_index}{BATCH_SEPARATOR}{batch_idx}"

                if img_path and isinstance(img_path, Path) and img_path.is_file():
                    try:
                        relative_path_for_url = img_path.relative_to(approval_data["comfyui_output_base"]).as_posix()
                        img_src_url = url_for('serve_image', filename=relative_path_for_url)
                        display_filename = img_path.name
                    except ValueError:
                        logger.warning(
                            f"Image path {img_path} is not relative to base {approval_data['comfyui_output_base']}. Cannot display."
                        )
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
                    <div style="border: 1px solid #eee; margin: 5px; padding: 5px;
                                display: inline-block; vertical-align: top;">
                        <p style="font-size: 0.8em; margin: 0 0 5px 0;">Batch Idx: {batch_idx}<br>({display_filename})</p>
                        <img src="{img_src_url}" alt="Generated Image {item_index}_{batch_idx}"
                             style="max-width: 200px; max-height: 200px; display: block; margin-bottom: 5px;">
                        <input type="checkbox" name="approved_item" value="{checkbox_value}" id="img_{checkbox_value}">
                        <label for="img_{checkbox_value}" style="font-size: 0.9em;">Approve</label>
                    </div>
                    """
                else:
                    items_html += f"""
                    <div style="border: 1px solid #eee; margin: 5px; padding: 5px;
                                display: inline-block; vertical-align: top; width: 200px; height: 250px;
                                background-color: #f8f8f8;">
                        <p style="font-size: 0.8em; margin: 0 0 5px 0;">Batch Idx: {batch_idx}</p>
                        <p style="color: red; font-size: 0.8em;">{display_filename}</p>
                        <p>(Cannot display image)</p>
                    </div>
                    """
            items_html += '</fieldset>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Horror CCTV Image Approval</title>
        <style> 
            body {{ font-family: sans-serif; background: linear-gradient(135deg, #1a1a1a 0%, #333333 100%); }} 
            .header {{ 
                background: linear-gradient(135deg, #ff4444 0%, #cc2222 100%);
                color: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 8px;
                text-align: center;
            }}
            .content {{ background: white; padding: 20px; border-radius: 8px; margin: 20px; }}
            fieldset {{ min-width: 220px; }} 
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 Horror CCTV Image Approval 🎬</h1>
            <h2>Security Footage Content Generation</h2>
            <p>Trigger Word: {HORROR_CCTV_TRIGGER}</p>
        </div>
        <div class="content">
            <p>Select the specific horror CCTV images you want to use as starting frames for video generation.</p>
            <form action="/submit" method="post">
                {items_html}
                <div style="clear: both; margin-top: 20px;">
                    <button type="submit" style="background: #ff4444; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px;">Submit Horror CCTV Approvals</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content)

@approval_app.route('/images/<path:filename>')
def serve_image(filename):
    """Serves images from the ComfyUI output directory."""
    global approval_data
    logger.debug(f"Serving image request for relative path: {filename}")
    try:
        if not approval_data["comfyui_output_base"] or not approval_data["comfyui_output_base"].is_dir():
            logger.error(f"ComfyUI Output Base directory is not set or doesn't exist: {approval_data['comfyui_output_base']}")
            return "Configuration Error: Output directory not found", 500

        logger.debug(f"Attempting to send '{filename}' from directory '{approval_data['comfyui_output_base']}'")
        return send_from_directory(approval_data["comfyui_output_base"], filename)
    except FileNotFoundError:
        full_attempted_path = approval_data["comfyui_output_base"] / filename
        logger.error(f"File not found for serving: {full_attempted_path}")
        return "File Not Found", 404
    except Exception as e:
        full_attempted_path = approval_data["comfyui_output_base"] / filename
        logger.error(f"Error serving file {full_attempted_path}: {e}", exc_info=True)
        return "Server Error", 500

@approval_app.route('/submit', methods=['POST'])
def submit_approval():
    """Handles the form submission, saves approved image details, and triggers shutdown."""
    global approval_data
    approved_items_values = request.form.getlist('approved_item')

    approved_details_list = []
    original_indices_approved = set()

    for value in approved_items_values:
        try:
            parts = value.split(BATCH_SEPARATOR)
            if len(parts) == 2:
                original_idx = int(parts[0])
                batch_img_idx = int(parts[1])

                found = False
                for item in approval_data["run_details_for_approval"]:
                    if item['index'] == original_idx:
                        paths = item.get('generated_image_paths', [])
                        if 0 <= batch_img_idx < len(paths):
                            img_path = paths[batch_img_idx]
                            approved_details_list.append({
                                "original_index": original_idx,
                                "batch_image_index": batch_img_idx,
                                "approved_image_path": str(img_path.resolve()),
                                "prompt": item['prompt'],
                                "face_filename": item['face_filename'],
                                "base_image_prefix": item['image_prefix'],
                                "trigger_word": HORROR_CCTV_TRIGGER
                            })
                            original_indices_approved.add(original_idx)
                            found = True
                            break
                        else:
                            logger.warning(f"Received invalid batch index {batch_img_idx} for original index {original_idx}. Skipping.")
                            break
                if not found:
                    logger.warning(f"Could not find run detail item for index {original_idx} from '{value}'. Skipping.")
            else:
                logger.warning(f"Received invalid checkbox value format: {value}. Skipping.")
        except ValueError:
            logger.warning(f"Non-integer index in: {value}. Skipping.")
        except Exception as e:
            logger.error(f"Error processing approved value '{value}': {e}", exc_info=True)

    logger.info(f"Received approval for {len(approved_details_list)} specific horror CCTV images.")
    logger.info(f"Original indices involved: {sorted(list(original_indices_approved))}")

    try:
        with open(approval_data["approval_file_path"], 'w', encoding='utf-8') as f:
            json.dump({
                "approved_images": approved_details_list,
                "trigger_word": HORROR_CCTV_TRIGGER,
                "automation_type": "horror_cctv",
                "approval_timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"Approved horror CCTV image details saved to: {approval_data['approval_file_path']}")
        if approval_data["shutdown_event"]:
            logger.info("Signaling main thread to shut down approval server.")
            approval_data["shutdown_event"].set()
        else:
            logger.error("Shutdown event not set in approval_data!")
        return "Horror CCTV approvals submitted successfully! You can close this window."
    except Exception as e:
        logger.error(f"Failed to save approval file: {e}", exc_info=True)
        return "Error saving approvals. Please check logs.", 500

def run_approval_server(run_details_list, comfy_output_base_path, file_path, shutdown_event_obj):
    """Starts the Flask server in a separate thread."""
    global approval_data
    approval_data["run_details_for_approval"] = [
        item for item in run_details_list
        if item.get('generated_image_paths') and isinstance(item['generated_image_paths'], list) and item['generated_image_paths']
    ]
    approval_data["comfyui_output_base"] = comfy_output_base_path
    approval_data["approval_file_path"] = file_path
    approval_data["shutdown_event"] = shutdown_event_obj

    logger.info(f"Starting horror CCTV approval server on http://0.0.0.0:{APPROVAL_SERVER_PORT}")
    try:
        approval_app.run(host='0.0.0.0', port=APPROVAL_SERVER_PORT, debug=False)
    except Exception as e:
        logger.error(f"Failed to start approval server: {e}", exc_info=True)
        if approval_data["shutdown_event"]:
            approval_data["shutdown_event"].set()

def handle_image_approval(generated_images, run_folder):
    """Handle horror CCTV image approval using automatic dual launch (Web UI & Telegram)"""
    if not generated_images:
        logger.error("No horror CCTV images to approve")
        return []
    
    logger.info(f"\n--- Horror CCTV Image Approval (Web UI & Telegram) ---")

    # Convert generated_images to run_details format for compatibility
    run_details_for_approval = []
    all_generated_image_paths = []
    
    for i, img_path in enumerate(generated_images):
        item_data = {
            'index': i + 1,
            'prompt': f"Horror CCTV prompt {i + 1}",  # Placeholder since we don't have full prompt data
            'generated_image_paths': [img_path],
            'face_filename': None,  # No face swap for horror CCTV
            'image_prefix': f"{i+1:03d}_horror_cctv"
        }
        run_details_for_approval.append(item_data)
        all_generated_image_paths.append(str(img_path))

    # Prepare paths
    approval_file_path = run_folder / APPROVAL_FILENAME
    
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
    print(safe_log_message("🎬 HORROR CCTV AUTOMATION - APPROVAL PHASE"))
    print(safe_log_message(f"🔤 Trigger Word: {HORROR_CCTV_TRIGGER}"))
    print(safe_log_message("🟢 You can approve/reject horror CCTV images via browser (http://localhost:5007) OR on Telegram."))
    print(safe_log_message("   📝 IMPORTANT: Script will proceed to video generation after ALL images are reviewed on Telegram."))
    print(safe_log_message("   📝 OR submit your selections in the web browser to proceed immediately."))
    print("=" * 100)

    # Enhanced approval waiting - Wait for ALL images to be reviewed
    approved_image_details = []
    while True:
        # Check Web UI approvals (Web UI automatically completes on submit)
        if approval_file_path.exists():
            try:
                with open(approval_file_path, "r", encoding="utf-8") as f:
                    approval_result = json.load(f)
                    approved_image_details = approval_result.get("approved_images", [])
                if approved_image_details:
                    logger.info(f"[Main] Loaded {len(approved_image_details)} approved horror CCTV image details from Web UI.")
                    print("[Main] Horror CCTV Web UI approvals submitted, proceeding to video generation...")
                    break
            except Exception as e:
                logger.error(f"Error reading web approval file {approval_file_path}: {e}")

        # Check Telegram approvals - Wait for ALL images to have status
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
                    
                    logger.info(f"[Main] All Telegram horror CCTV images reviewed! {len(approved_paths)} approved, {len(rejected_paths)} rejected")
                    print(f"[Main] ✅ All Telegram horror CCTV images reviewed! {len(approved_paths)} approved, {len(rejected_paths)} rejected")
                    
                    # Build approved_image_details in the same format as Web UI
                    temp_approved_list = []
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
                                    "base_image_prefix": item['image_prefix'],
                                    "trigger_word": HORROR_CCTV_TRIGGER
                                })
                                break
                    
                    approved_image_details = temp_approved_list
                    logger.info(f"[Main] Final result: {len(approved_image_details)} horror CCTV images approved for video generation.")
                    print(f"[Main] Proceeding to video generation with {len(approved_image_details)} approved horror CCTV images...")
                    break
                else:
                    # Still waiting for more reviews
                    if total_images_sent > 0:
                        logger.debug(f"[Main] Telegram progress: {images_with_status}/{total_images_sent} horror CCTV images reviewed")
                        
            except Exception as e:
                logger.error(f"Error reading Telegram approval file {TELEGRAM_APPROVALS_JSON}: {e}")

        time.sleep(2)

    # Convert approved_image_details back to simple Path list format for compatibility
    approved_images = []
    for item in approved_image_details:
        approved_images.append(Path(item['approved_image_path']))
    
    return approved_images

def generate_videos(config, approved_images, run_folder):
    """Generate horror CCTV videos from approved images"""
    if not approved_images:
        logger.warning("No approved horror CCTV images for video generation")
        return []
    
    logger.info(f"Starting horror CCTV video generation for {len(approved_images)} images...")
    
    api_url = config["api_server_url"]
    videos_folder = run_folder / "all_videos"
    prompt_ids = []
    
    # Copy approved images to ComfyUI input directory for video start images
    temp_start_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    temp_start_dir.mkdir(exist_ok=True)
    
    for i, img_path in enumerate(approved_images):
        logger.info(f"Submitting horror CCTV video {i+1}/{len(approved_images)}")
        
        # Copy image to ComfyUI input for video start
        start_img_name = f"horror_cctv_start_{i+1:03d}_{img_path.stem}.png"
        start_img_path = temp_start_dir / start_img_name
        shutil.copy2(img_path, start_img_path)
        
        # Generate horror CCTV video prompt
        video_prompt = generate_horror_cctv_prompt_ollama(config)
        
        # Prepare API request
        request_data = {
            "prompt": video_prompt,
            "face": None,  # No face swap for horror CCTV
            "output_subfolder": f"{run_folder.name}/all_videos", 
            "filename_prefix_text": f"{i+1:03d}_horror_cctv_video",
            "video_start_image_path": f"{TEMP_VIDEO_START_SUBDIR}/{start_img_name}"
        }
        
        try:
            response = call_api(api_url, "generate_video", request_data)
            prompt_id = response.get("prompt_id")
            
            if prompt_id:
                prompt_ids.append(prompt_id)
                logger.info(f"Horror CCTV video {i+1} submitted: {prompt_id}")
            else:
                logger.error(f"No prompt_id in response for video {i+1}")
                
        except Exception as e:
            logger.error(f"Failed to submit horror CCTV video {i+1}: {e}")
    
    logger.info(f"Submitted {len(prompt_ids)} horror CCTV videos for generation")
    return prompt_ids

def wait_for_videos(prompt_ids, videos_folder):
    """Wait for horror CCTV videos to be generated"""
    logger.info("Waiting for horror CCTV videos to be generated...")
    
    start_time = time.time()
    generated_videos = []
    
    with tqdm(total=len(prompt_ids), desc="Horror CCTV Videos") as pbar:
        while time.time() - start_time < POLLING_TIMEOUT_VIDEO:
            current_videos = []
            
            if videos_folder.exists():
                current_videos = [f for f in videos_folder.iterdir() 
                                if f.is_file() and f.suffix.lower() in ['.mp4', '.avi', '.mov']]
            
            if len(current_videos) >= len(prompt_ids):
                generated_videos = sorted(current_videos)
                logger.info(f"All {len(generated_videos)} horror CCTV videos generated")
                break
                
            pbar.n = len(current_videos)
            pbar.refresh()
            time.sleep(POLLING_INTERVAL)
    
    if not generated_videos:
        logger.error("No horror CCTV videos were generated within timeout")
        return []
    
    return generated_videos

def run_horror_cctv_automation():
    """Main horror CCTV automation pipeline"""
    logger.info("="*60)
    logger.info("HORROR CCTV AUTOMATION PIPELINE STARTED")
    logger.info("="*60)
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Horror CCTV configuration loaded successfully")
        
        # Create run folder
        run_folder = create_run_folder()
        
        # Generate horror CCTV prompts
        prompts = generate_prompts(config)
        
        # Generate horror CCTV images
        prompt_ids = generate_images(config, prompts, run_folder)
        
        if not prompt_ids:
            logger.error("No horror CCTV images submitted for generation")
            return
        
        # Wait for images
        images_folder = run_folder / "all_images"
        generated_images = wait_for_images(prompt_ids, images_folder)
        
        if not generated_images:
            logger.error("No horror CCTV images were generated")
            return
        
        # Handle image approval
        approved_images = handle_image_approval(generated_images, run_folder)
        
        if approved_images:
            # Copy approved images
            copied_images = copy_approved_images(approved_images, run_folder)
            
            # Generate videos from approved images
            video_prompt_ids = generate_videos(config, copied_images, run_folder)
            
            if video_prompt_ids:
                # Wait for videos
                videos_folder = run_folder / "all_videos"
                generated_videos = wait_for_videos(video_prompt_ids, videos_folder)
                
                if generated_videos:
                    logger.info("Horror CCTV automation completed successfully!")
                    logger.info(f"Generated {len(generated_videos)} horror CCTV videos")
                    logger.info(f"Output folder: {run_folder}")
                else:
                    logger.error("Horror CCTV video generation failed")
            else:
                logger.error("No horror CCTV videos submitted for generation")
        else:
            logger.warning("No horror CCTV images approved, skipping video generation")
        
    except Exception as e:
        logger.error(f"Horror CCTV automation failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        run_horror_cctv_automation()
    except KeyboardInterrupt:
        logger.info("Horror CCTV automation interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in horror CCTV automation: {e}", exc_info=True)
        sys.exit(1)