#!/usr/bin/env python
"""
Sequentially run the dancer automation pipeline with parallel approval (Web UI and Telegram).

This script is now MODIFIED to be fully resumable from specific stages using command-line arguments.
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
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

# --- Third-party Imports ---
from dotenv import load_dotenv

# --- Import Flask for Web UI Approval ---
try:
    from flask import Flask, request, render_template_string, send_from_directory, url_for
except ImportError:
    print("ERROR: Flask library not found. Please install it: pip install Flask")
    sys.exit(1)

# --- Import tqdm for progress bars ---
try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

# --- Load environment variables (.env) ---
load_dotenv()

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

APPROVAL_SERVER_PORT = 5005
APPROVAL_FILENAME = "approved_images.json"
APPROVED_IMAGES_SUBFOLDER = "approved_images_for_video"

BATCH_SEPARATOR = "__batch__"

# --- Configurable Paths (User Must Confirm) ---
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content")
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"

# --- Telegram Approval Paths & Env Vars ---
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR / "telegram_approvals"
SEND_TELEGRAM_SCRIPT = TELEGRAM_APPROVALS_DIR / "send_telegram_image_approvals.py"
TELEGRAM_APPROVALS_JSON = TELEGRAM_APPROVALS_DIR / "telegram_approvals.json"
TOKEN_MAP_JSON = TELEGRAM_APPROVALS_DIR / "token_map.json"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Logging Setup ---
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"automation_v6_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- All original helper functions (unchanged) ---

def find_node_id_by_title(workflow, title, wf_name="workflow"):
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("_meta", {}).get("title") == title:
            logger.debug(f"Found node by title '{title}' in {wf_name}: ID {node_id} (Class: {node_data.get('class_type', 'N/A')})")
            return node_id
    logger.warning(f"Node not found by title '{title}' in {wf_name}.")
    return None

def load_config(config_path="config4_without_faceswap.json"):
    config_path_obj = SCRIPT_DIR / config_path
    try:
        if not config_path_obj.is_file():
            logger.critical(f"CRITICAL: Config file not found: {config_path_obj}")
            sys.exit(1)
        with open(config_path_obj, 'r', encoding='utf-8') as f:
            config = json.load(f)
        required_keys = ['api_server_url', 'base_workflow_image', 'base_workflow_video', 'source_faces_path', 'output_folder', 'comfyui_api_url', 'ollama_model', 'num_prompts']
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required key '{key}' in config")
        config['source_faces_path'] = (SCRIPT_DIR / config['source_faces_path']).resolve()
        config['output_folder'] = (SCRIPT_DIR / config['output_folder']).resolve()
        config['output_folder'].mkdir(parents=True, exist_ok=True)
        config['comfyui_api_url'] = config['comfyui_api_url'].rstrip('/')
        config['api_server_url'] = config['api_server_url'].rstrip('/')
        logger.info(f"Config loaded successfully from {config_path_obj}")
        return config
    except Exception as e:
        logger.critical(f"CRITICAL error loading/validating config '{config_path}': {e}", exc_info=True)
        sys.exit(1)

def generate_prompts_ollama(model, num_prompts, ollama_api_url):
    logger.info(f"🚀 Generating {num_prompts} prompts via Ollama (Model: {model}, URL: {ollama_api_url})...")
    backgrounds = ["european beach", "united state beach party", "open air beach"]
    generated_prompt_list = []
    for i in range(num_prompts):
        background = random.choice(backgrounds)
        base_scene_idea = (f"A gorgeous, confident female dancer with revealing, facing camera, short clothing (like a small blouse top and super large natural bust and ass revealing indian saree with hot pants) and very noticeable curves, large natural bust out, small visible nipple dancing energetically as the main focus in/at {background}. Camera is medium shot or close-up on her. Other attractive people and dancers are visible partying in the background but slightly blurred or less detailed. Focus on a vibrant, sexy, high-energy, cinematic party atmosphere. indian festival ground")
        formatted_prompt = (f"""Generate ONE single-line highly detailed cinematic prompt for AI video creation. Strictly focus on a gorgeous, confident female dancer energetically dancing by walking forward rhythmically, dramatically shaking her chest and hips, with no spinning movements, highly detailed cinematic prompt for AI image/video. Focus on visual elements: dynamic lighting, camera angle/shot type (e.g., low angle close-up, dynamic medium shot), mood (energetic, celebratory, sexy), specific details about the main dancer's attire (short, revealing), expression (confident, playful), large natural bust and the specific party environment ({background}). Include details about background dancers/partygoers. NO commentary. Respond ONLY with a valid JSON object: {{"prompts": ["<your prompt here>"]}}\n\nScene Desc:\n{base_scene_idea}""")
        logger.info(f"\n🧠 Requesting Prompt [{i+1}/{num_prompts}] | Theme: {background}")
        ollama_success = False
        last_error = None
        for attempt in range(OLLAMA_MAX_RETRIES):
            logger.debug(f"   Ollama Attempt {attempt+1}/{OLLAMA_MAX_RETRIES}...")
            try:
                response = requests.post(ollama_api_url, json={"model": model, "prompt": formatted_prompt, "stream": False}, timeout=OLLAMA_TIMEOUT)
                response.raise_for_status()
                response_json = response.json()
                generated_text = response_json.get("response", "").strip()
                start_index, end_index = generated_text.find('{'), generated_text.rfind('}')
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_str = generated_text[start_index:end_index+1]
                    parsed = json.loads(json_str)
                    if "prompts" in parsed and isinstance(parsed["prompts"], list) and parsed["prompts"]:
                        prompt_text = parsed["prompts"][0].strip()
                        if prompt_text:
                            logger.info(f"   ✅ Clean Prompt Extracted:\n      '{prompt_text}'")
                            generated_prompt_list.append({"index": i + 1, "background": background, "generated_prompt": prompt_text})
                            ollama_success = True
                            break
                last_error = ValueError("Invalid JSON or structure in Ollama response.")
            except Exception as e:
                last_error = e
                logger.warning(f"   ❌ Error with Ollama (Attempt {attempt+1}): {e}")
            if not ollama_success and attempt < OLLAMA_MAX_RETRIES - 1:
                time.sleep(OLLAMA_RETRY_DELAY)
            elif not ollama_success:
                logger.error(f"   ❌ Failed to generate prompt [{i+1}] after {OLLAMA_MAX_RETRIES} attempts. Last error: {last_error}")
                generated_prompt_list.append({"index": i + 1, "background": background, "error": str(last_error)})
    successful_count = sum(1 for p in generated_prompt_list if 'error' not in p)
    logger.info(f"✅ Finished generating {successful_count}/{num_prompts} prompts.")
    return generated_prompt_list

def save_prompts_log(prompt_list, main_run_folder_path):
    if not prompt_list: return
    timestamp_str = main_run_folder_path.name.replace("Run_", "")
    log_folder = main_run_folder_path / "logs"
    log_folder.mkdir(exist_ok=True)
    json_path = log_folder / f"generated_prompts_{timestamp_str}.json"
    txt_path = log_folder / f"generated_prompts_{timestamp_str}.txt"
    try:
        with open(json_path, "w", encoding="utf-8") as f: json.dump(prompt_list, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Full prompt data saved to: {json_path}")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Generated Prompts - {timestamp_str}\n" + "=" * 30 + "\n\n")
            for item in prompt_list:
                # CORRECTED SYNTAX: Avoid nested f-strings
                prompt_text = item.get('generated_prompt', 'Error: ' + str(item.get("error")))
                f.write(f"{item.get('index', 'N/A'):02d}. Prompt: {prompt_text}\n\n")
        logger.info(f"📝 Clean prompts saved to: {txt_path}")
    except Exception as e:
        logger.error(f"Failed to save prompts logs: {e}")

def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None, output_subfolder: str, filename_prefix: str, video_start_image: str | None = None):
    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
    payload = {"prompt": prompt, "face": face_filename or "", "output_subfolder": output_subfolder, "filename_prefix_text": filename_prefix}
    if endpoint == "generate_video" and video_start_image: payload["video_start_image_path"] = video_start_image
    log_prefix = f"API Call -> {endpoint}"
    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            response = requests.post(full_url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('status') == 'submitted' and response_data.get('prompt_id'):
                logger.info(f"  ✅ {log_prefix} submitted successfully. ComfyUI Prompt ID: {response_data['prompt_id']}")
                return response_data['prompt_id']
            else:
                logger.error(f"API submission failed. Status: {response_data.get('status')}, Info: {response_data.get('error')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ {log_prefix} Error (Attempt {attempt}): {e}")
        if attempt < MAX_API_RETRIES: time.sleep(API_RETRY_DELAY)
    logger.error(f"  ❌ {log_prefix} failed after {MAX_API_RETRIES} attempts.")
    return None

def check_comfyui_job_status(comfyui_base_url: str, prompt_id: str):
    if not prompt_id: return None
    try:
        response = requests.get(f"{comfyui_base_url}/history/{prompt_id}", timeout=10)
        response.raise_for_status()
        history_data = response.json()
        if prompt_id in history_data: return history_data[prompt_id]
        return None
    except Exception as e:
        logger.warning(f"Error polling /history/{prompt_id}: {e}")
        return None

def get_output_filenames_from_history(history_entry: dict, output_node_id: str):
    output_paths = []
    if not history_entry or 'outputs' not in history_entry or output_node_id not in history_entry['outputs']:
        return output_paths
    node_output = history_entry['outputs'][output_node_id]
    output_key = 'images' if 'images' in node_output else 'gifs' if 'gifs' in node_output else None
    if output_key:
        for item_info in node_output[output_key]:
            if 'filename' in item_info and 'subfolder' in item_info:
                output_paths.append(Path(item_info['subfolder']) / item_info['filename'])
    if not output_paths:
        logger.warning(f"Could not find any valid image/gif outputs for node {output_node_id} in history entry.")
    return output_paths

# --- Flask App for Approval (Unchanged) ---
approval_app = Flask(__name__)
approval_data = {"run_details_for_approval": [], "comfyui_output_base": None, "approval_file_path": None, "shutdown_event": None}
@approval_app.route('/')
def index():
    global approval_data
    items_html = ""
    if not approval_data["run_details_for_approval"]: items_html = "<p>No successfully generated images found to approve.</p>"
    else:
        for item in approval_data["run_details_for_approval"]:
            item_index, image_paths = item['index'], item.get('generated_image_paths', [])
            if not image_paths: continue
            items_html += f'<fieldset style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top;">'
            items_html += f'<legend><b>Index: {item_index}</b> (Prompt: {item["prompt"][:40]}...)</legend>'
            for batch_idx, img_path in enumerate(image_paths):
                img_src_url, display_filename = None, "N/A"
                checkbox_value = f"{item_index}{BATCH_SEPARATOR}{batch_idx}"
                if img_path and img_path.is_file():
                    try:
                        relative_path_for_url = img_path.relative_to(approval_data["comfyui_output_base"]).as_posix()
                        img_src_url = url_for('serve_image', filename=relative_path_for_url)
                        display_filename = img_path.name
                    except ValueError: logger.warning(f"Image path {img_path} not relative to base. Cannot display.")
                if img_src_url:
                    items_html += f"""<div style="margin: 5px; padding: 5px; display: inline-block; vertical-align: top;"><p style="font-size: 0.8em; margin: 0 0 5px 0;">Batch Idx: {batch_idx}<br>({display_filename})</p><img src="{img_src_url}" alt="Generated Image {item_index}_{batch_idx}" style="max-width: 200px; max-height: 200px; display: block; margin-bottom: 5px;"><input type="checkbox" name="approved_item" value="{checkbox_value}" id="img_{checkbox_value}"><label for="img_{checkbox_value}" style="font-size: 0.9em;">Approve</label></div>"""
            items_html += '</fieldset>'
    return render_template_string(f'<!DOCTYPE html><html><head><title>Image Approval (v6)</title><style>body{{font-family: sans-serif;}}</style></head><body><h1>Approve Images for Video Generation</h1><form action="/submit" method="post">{items_html}<div style="clear: both; margin-top: 20px;"><button type="submit">Submit Approvals</button></div></form></body></html>')
@approval_app.route('/images/<path:filename>')
def serve_image(filename):
    global approval_data
    return send_from_directory(approval_data["comfyui_output_base"], filename)
@approval_app.route('/submit', methods=['POST'])
def submit_approval():
    global approval_data
    approved_values = request.form.getlist('approved_item')
    approved_details_list = []
    for value in approved_values:
        try:
            original_idx_str, batch_img_idx_str = value.split(BATCH_SEPARATOR)
            original_idx, batch_img_idx = int(original_idx_str), int(batch_img_idx_str)
            for item in approval_data["run_details_for_approval"]:
                if item['index'] == original_idx:
                    paths = item.get('generated_image_paths', [])
                    if 0 <= batch_img_idx < len(paths):
                        approved_details_list.append({"original_index": original_idx, "batch_image_index": batch_img_idx, "approved_image_path": str(paths[batch_img_idx].resolve()), "prompt": item['prompt'], "face_filename": item['face_filename'], "base_image_prefix": item['image_prefix']})
                    break
        except Exception as e: logger.warning(f"Error processing approved value '{value}': {e}")
    try:
        with open(approval_data["approval_file_path"], 'w', encoding='utf-8') as f: json.dump({"approved_images": approved_details_list}, f, indent=2)
        logger.info(f"Approved image details saved to: {approval_data['approval_file_path']}")
        if approval_data["shutdown_event"]: approval_data["shutdown_event"].set()
        return "Approvals submitted successfully! You can close this window."
    except Exception as e:
        logger.error(f"Failed to save approval file: {e}", exc_info=True)
        return "Error saving approvals.", 500
def run_approval_server(run_details_list, comfy_output_base_path, file_path, shutdown_event_obj):
    global approval_data
    approval_data["run_details_for_approval"] = [d for d in run_details_list if d.get('generated_image_paths')]
    approval_data["comfyui_output_base"] = comfy_output_base_path
    approval_data["approval_file_path"] = file_path
    approval_data["shutdown_event"] = shutdown_event_obj
    logger.info(f"Starting approval server on http://0.0.0.0:{APPROVAL_SERVER_PORT}")
    try:
        from werkzeug.serving import make_server
        class StoppableServer(threading.Thread):
            def __init__(self, app, host, port):
                threading.Thread.__init__(self)
                self.server = make_server(host, port, app, threaded=True)
                self.ctx = app.app_context()
                self.ctx.push()
            def run(self): self.server.serve_forever()
            def shutdown(self): self.server.shutdown()
        server = StoppableServer(approval_app, '0.0.0.0', APPROVAL_SERVER_PORT)
        server.start()
        shutdown_event_obj.wait()
        server.shutdown()
        logger.info("Approval server has been shut down.")
    except Exception as e:
        logger.error(f"Failed to start/run approval server: {e}", exc_info=True)
        if approval_data["shutdown_event"]: approval_data["shutdown_event"].set()

# --- Pipeline Stages as Functions ---

STAGES = ["prompts", "images", "approval", "videos", "cleanup", "summary"]

def reconstruct_state_for_resume(resume_run_folder: Path):
    logger.info(f"--- RESUMING RUN: Attempting to load state from {resume_run_folder} ---")
    if not resume_run_folder.is_dir():
        logger.critical(f"Resume folder not found: {resume_run_folder}"); sys.exit(1)
    details_file = next(resume_run_folder.glob("*_details_v6.json"), None)
    if not details_file:
        logger.critical(f"Could not find a '..._details_v6.json' file in {resume_run_folder} to resume from."); sys.exit(1)
    logger.info(f"Found details file: {details_file}")
    with open(details_file, 'r', encoding='utf-8') as f: run_details = json.load(f)
    for item in run_details:
        if 'generated_image_paths' in item: item['generated_image_paths'] = [Path(p) for p in item.get('generated_image_paths', [])]
        if 'video_jobs' in item:
            for vj in item.get('video_jobs', []):
                if 'approved_image_used' in vj and vj['approved_image_used']: vj['approved_image_used'] = Path(vj['approved_image_used'])
    logger.info(f"Successfully loaded and reconstructed state for {len(run_details)} items.")
    return run_details, resume_run_folder

def stage_1_generate_prompts(config, main_run_folder_path):
    logger.info("\n" + "="*20 + " STAGE 1: GENERATE PROMPTS " + "="*20)
    prompts_data = generate_prompts_ollama(config["ollama_model"], config["num_prompts"], config.get("ollama_api_url", "http://localhost:11434/api/generate"))
    save_prompts_log(prompts_data, main_run_folder_path)
    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts: logger.critical("No valid prompts generated. Stopping."); sys.exit(1)
    logger.info(f"Proceeding with {len(valid_prompts)} valid prompts.")
    return valid_prompts

def stage_2_generate_and_poll_images(config, valid_prompts, main_run_folder_path):
    logger.info("\n" + "="*20 + " STAGE 2: GENERATE & POLL IMAGES " + "="*20)
    run_details, face_files = [], []
    source_faces_path = config['source_faces_path']
    if source_faces_path.is_dir():
        face_files = sorted([f for f in source_faces_path.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
    else:
        logger.warning(f"Source faces dir not found: {source_faces_path}")
    if not face_files: logger.warning("No face images found; face swap will be skipped.")

    image_save_node_id = None
    try:
        img_wf_path = (SCRIPT_DIR / config["base_workflow_image"]).resolve()
        with open(img_wf_path, "r", encoding="utf-8") as f: temp_img_wf = json.load(f)
        image_save_node_id = find_node_id_by_title(temp_img_wf, "API_Image_Output_SaveNode", img_wf_path.name)
    except Exception as e: logger.error(f"Error finding SaveImage node ID: {e}", exc_info=True)
    if not image_save_node_id: logger.error("Could not find SaveImage node. Polling will fail.")
    
    comfyui_image_output_subfolder = f"{main_run_folder_path.name}/all_images"
    for item_index, item in enumerate(tqdm(valid_prompts, desc="Submitting Images")):
        idx, prompt = item["index"], item["generated_prompt"]
        face_path = face_files[item_index % len(face_files)] if face_files else None
        face_filename = face_path.name if face_path else None
        prefix = f"{idx:03d}_{'swapped' if face_filename else 'raw'}"
        prompt_id = trigger_generation(config['api_server_url'], "generate_image", prompt, face_filename, comfyui_image_output_subfolder, prefix)
        run_details.append({'index': idx, 'prompt': prompt, 'face_filename': face_filename, 'image_prefix': prefix, 'image_prompt_id': prompt_id, 'image_job_status': 'submitted' if prompt_id else 'failed', 'generated_image_paths': [], 'video_jobs': []})

    jobs_to_poll = [d for d in run_details if d['image_prompt_id']]
    if image_save_node_id and jobs_to_poll:
        logger.info(f"--- Polling for {len(jobs_to_poll)} Image Jobs ---")
        for details in tqdm(jobs_to_poll, desc="Polling Images"):
            start_time = time.time()
            while time.time() - start_time < POLLING_TIMEOUT_IMAGE:
                history = check_comfyui_job_status(config['comfyui_api_url'], details['image_prompt_id'])
                if history:
                    details['image_job_status'] = 'completed_history_found'
                    rel_paths = get_output_filenames_from_history(history, image_save_node_id)
                    details['generated_image_paths'] = [(COMFYUI_OUTPUT_DIR_BASE / p).resolve() for p in rel_paths]
                    if all(p.is_file() for p in details['generated_image_paths']): details['image_job_status'] = 'completed_all_files_found'
                    else: details['image_job_status'] = 'completed_some_files_missing'
                    break
                time.sleep(POLLING_INTERVAL)
            else: details['image_job_status'] = 'polling_timeout'
    return run_details

def stage_3_handle_approval(run_details, main_run_folder_path, config, wait_for_human=True):
    logger.info("\n" + "="*20 + " STAGE 3: HANDLE APPROVAL " + "="*20)
    approval_file_path = main_run_folder_path / APPROVAL_FILENAME
    run_details_for_approval = [d for d in run_details if d.get('generated_image_paths')]
    if not run_details_for_approval:
        logger.warning("No images were successfully generated. Skipping approval.")
        return []
    
    if wait_for_human:
        all_image_paths_str = [str(p) for item in run_details_for_approval for p in item['generated_image_paths']]
        
        def start_telegram_approval():
            if TELEGRAM_APPROVALS_JSON.exists(): TELEGRAM_APPROVALS_JSON.unlink()
            if TOKEN_MAP_JSON.exists(): TOKEN_MAP_JSON.unlink()
            TELEGRAM_APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
            try: subprocess.run([sys.executable, str(SEND_TELEGRAM_SCRIPT)] + all_image_paths_str, check=True)
            except Exception as e: logger.error(f"Telegram approval process failed: {e}", exc_info=True)

        shutdown_event = threading.Event()
        flask_thread = threading.Thread(target=run_approval_server, args=(run_details_for_approval, COMFYUI_OUTPUT_DIR_BASE, approval_file_path, shutdown_event), daemon=True)
        telegram_thread = threading.Thread(target=start_telegram_approval, daemon=True)
        
        flask_thread.start()
        telegram_thread.start()
        
        logger.info("=" * 60)
        logger.info(f"🟢 Approval UI is running. Web: http://localhost:{APPROVAL_SERVER_PORT} OR use Telegram.")
        logger.info("=" * 60)
    
    approved_image_details = []
    logger.info("Checking for approval files...")
    while True:
        if approval_file_path.exists() and approval_file_path.stat().st_size > 0:
            try:
                with open(approval_file_path, 'r', encoding='utf-8') as f: approved_image_details = json.load(f).get("approved_images", [])
                if approved_image_details: logger.info(f"Loaded {len(approved_image_details)} approvals from Web UI."); break
            except Exception as e: logger.error(f"Error reading web approval file: {e}")
        
        if TELEGRAM_APPROVALS_JSON.exists() and TELEGRAM_APPROVALS_JSON.stat().st_size > 0:
            try:
                with open(TELEGRAM_APPROVALS_JSON, "r", encoding="utf-8") as f: telegram_result = json.load(f)
                temp_list = []
                for img_path_str, info in telegram_result.items():
                    if info.get("status") == "approve":
                        img_path_obj = Path(img_path_str)
                        for item in run_details_for_approval:
                            if img_path_obj in item['generated_image_paths']:
                                batch_idx = item['generated_image_paths'].index(img_path_obj)
                                temp_list.append({"original_index": item['index'], "batch_image_index": batch_idx, "approved_image_path": str(img_path_obj.resolve()), "prompt": item['prompt'], "face_filename": item['face_filename'], "base_image_prefix": item['image_prefix']})
                                break
                if temp_list: approved_image_details = temp_list; logger.info(f"Loaded {len(approved_image_details)} approvals from Telegram."); break
            except Exception as e: logger.error(f"Error reading Telegram approval file: {e}")
        
        if not wait_for_human:
            logger.warning("No approval file found and not waiting for human. Proceeding with no approved images.")
            break
        time.sleep(2)

    if wait_for_human:
        shutdown_event.set()
    
    approved_images_folder_path = main_run_folder_path / APPROVED_IMAGES_SUBFOLDER
    approved_images_folder_path.mkdir(exist_ok=True)
    for info in approved_image_details:
        try:
            source_path = Path(info['approved_image_path'])
            dest_filename = f"approved_{info['original_index']:03d}_batch{info['batch_image_index']}_{source_path.name}"
            shutil.copyfile(source_path, approved_images_folder_path / dest_filename)
        except Exception as e: logger.error(f"Failed to copy approved image {source_path.name}: {e}")
    
    return approved_image_details

def stage_4_generate_and_poll_videos(config, run_details, approved_image_details, main_run_folder_path):
    logger.info("\n" + "="*20 + " STAGE 4: GENERATE & POLL VIDEOS " + "="*20)
    if not approved_image_details:
        logger.warning("No approved images found. Skipping video generation.")
        return run_details, None

    temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    temp_start_image_dir.mkdir(parents=True, exist_ok=True)
    
    comfyui_video_output_subfolder = f"{main_run_folder_path.name}/all_videos"
    for approved_info in tqdm(approved_image_details, desc="Submitting Videos"):
        orig_index, batch_index = approved_info['original_index'], approved_info['batch_image_index']
        start_image_path = Path(approved_info['approved_image_path'])
        
        temp_start_image_comfy_path_str = None
        try:
            temp_filename = f"start_{orig_index:03d}_batch{batch_index}_{datetime.now().strftime('%H%M%S%f')}{start_image_path.suffix}"
            shutil.copyfile(start_image_path, temp_start_image_dir / temp_filename)
            temp_start_image_comfy_path_str = (Path(TEMP_VIDEO_START_SUBDIR) / temp_filename).as_posix()
        except Exception as e: logger.error(f"Failed to copy start image: {e}")

        prefix = f"{orig_index:03d}_batch{batch_index}_video_{'swapped' if approved_info['face_filename'] else 'raw'}"
        prompt_id = trigger_generation(config['api_server_url'], "generate_video", approved_info['prompt'], approved_info['face_filename'], comfyui_video_output_subfolder, prefix, video_start_image=temp_start_image_comfy_path_str)
        
        video_job_info = {"original_index": orig_index, "batch_image_index": batch_index, "video_prompt_id": prompt_id, "video_job_status": 'submitted' if prompt_id else 'failed', "approved_image_used": str(start_image_path)}
        for detail in run_details:
            if detail['index'] == orig_index:
                if 'video_jobs' not in detail: detail['video_jobs'] = []
                detail['video_jobs'].append(video_job_info)
                break

    jobs_to_poll = [job for detail in run_details for job in detail.get('video_jobs', []) if job.get('video_prompt_id')]
    if jobs_to_poll:
        logger.info(f"--- Polling for {len(jobs_to_poll)} Video Jobs ---")
        for job in tqdm(jobs_to_poll, desc="Polling Videos"):
            start_time = time.time()
            while time.time() - start_time < POLLING_TIMEOUT_VIDEO:
                if check_comfyui_job_status(config['comfyui_api_url'], job['video_prompt_id']):
                    job['video_job_status'] = 'completed'
                    break
                time.sleep(POLLING_INTERVAL * 2)
            else: job['video_job_status'] = 'polling_timeout'
    return run_details, temp_start_image_dir

def stage_5_cleanup(temp_start_image_dir):
    logger.info("\n" + "="*20 + " STAGE 5: CLEANUP " + "="*20)
    if temp_start_image_dir and temp_start_image_dir.exists():
        try: shutil.rmtree(temp_start_image_dir); logger.info(f"Successfully removed temp directory: {temp_start_image_dir}")
        except Exception as e: logger.error(f"Error during cleanup: {e}", exc_info=True)
    else: logger.info("Temp directory does not exist or was not created. Nothing to clean.")

def stage_6_generate_summary(run_details, main_run_folder_path):
    logger.info("\n" + "="*20 + " STAGE 6: FINAL SUMMARY " + "="*20)
    final_details_path = main_run_folder_path / f"{main_run_folder_path.name}_details_v6.json"
    try:
        serializable_details = json.loads(json.dumps(run_details, default=lambda o: str(o) if isinstance(o, Path) else o))
        with open(final_details_path, 'w', encoding='utf-8') as f: json.dump(serializable_details, f, indent=2, ensure_ascii=False)
        logger.info(f"   Final run details saved to: {final_details_path}")
    except Exception as e: logger.error(f"   Failed to save final run details: {e}")
    images_found = sum(1 for d in run_details if 'files_found' in d.get('image_job_status', ''))
    approved_count = sum(len(d.get('video_jobs', [])) for d in run_details)
    videos_completed = sum(1 for d in run_details for vj in d.get('video_jobs', []) if vj.get('video_job_status') == 'completed')
    logger.info(f"Run Folder: {main_run_folder_path}")
    logger.info(f"Valid Prompts: {len(run_details)}")
    logger.info(f"Images Generated: {images_found}")
    logger.info(f"Images Approved: {approved_count}")
    logger.info(f"Videos Completed: {videos_completed}")

# --- Main Execution Logic ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the dancer automation pipeline, with resumable stages.")
    parser.add_argument("--start-from", type=str, choices=STAGES, default="prompts", help="The stage to start execution from.")
    parser.add_argument("--resume-run", type=str, default=None, help="The name of the run folder (e.g., 'Run_20231028_145530') to resume.")
    args = parser.parse_args()
    
    # If starting from a later stage, a resume folder is required.
    if args.start_from != 'prompts' and not args.resume_run:
        parser.error("--resume-run is required when using --start-from with any stage other than 'prompts'.")

    logger.info("=" * 60)
    logger.info(f"STARTING AUTOMATION V6 (Resumable) | Start Stage: {args.start_from.upper()}")
    if args.resume_run: logger.info(f"Resuming Run: {args.resume_run}")
    logger.info("=" * 60)

    config = load_config()

    # --- State Initialization ---
    run_details, main_run_folder_path = [], None
    valid_prompts, approved_image_details = [], []
    temp_start_image_dir = None
    
    if args.resume_run:
        run_details, main_run_folder_path = reconstruct_state_for_resume(config['output_folder'] / args.resume_run)
    else:
        script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        main_run_folder_path = config['output_folder'] / f"Run_{script_run_timestamp}"
        main_run_folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created new script run output directory: {main_run_folder_path}")

    # --- Execution Loop ---
    start_index = STAGES.index(args.start_from)
    for i, stage_name in enumerate(STAGES):
        if i < start_index:
            logger.info(f"--- SKIPPING Stage: {stage_name.upper()} ---")
            continue
        
        if stage_name == "prompts":
            valid_prompts = stage_1_generate_prompts(config, main_run_folder_path)
        
        elif stage_name == "images":
            run_details = stage_2_generate_and_poll_images(config, valid_prompts, main_run_folder_path)

        elif stage_name == "approval":
            approved_image_details = stage_3_handle_approval(run_details, main_run_folder_path, config, wait_for_human=True)

        elif stage_name == "videos":
            # If we started here, we need to load the approvals first without waiting for human input
            if start_index == STAGES.index("videos"):
                approved_image_details = stage_3_handle_approval(run_details, main_run_folder_path, config, wait_for_human=False)
            
            run_details, temp_start_image_dir = stage_4_generate_and_poll_videos(config, run_details, approved_image_details, main_run_folder_path)
            
        elif stage_name == "cleanup":
            if not temp_start_image_dir: temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
            stage_5_cleanup(temp_start_image_dir)
            
        elif stage_name == "summary":
            stage_6_generate_summary(run_details, main_run_folder_path)

    logger.info("\n" + "=" * 60)
    logger.info(f"🎉 Automation Run Script Finished! {datetime.now()}")
    logger.info("=" * 60)