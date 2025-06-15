#!/usr/bin/env python
"""Generate videos from previously approved images (via Telegram or Web UI)."""

from __future__ import annotations

import json
import sys
import time
import shutil
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Constants ---
MAX_API_RETRIES = 3
API_RETRY_DELAY = 5
REQUEST_TIMEOUT = 60
POLLING_INTERVAL = 10
POLLING_TIMEOUT_VIDEO = 3600

# --- Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_INPUT_DIR_BASE = Path("D:/Comfy_UI_V20/ComfyUI/input")
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content")
TEMP_VIDEO_START_SUBDIR = "temp_video_starts"

# --- Telegram Approval Paths ---
TELEGRAM_APPROVALS_DIR = SCRIPT_DIR / "telegram_approvals"
TELEGRAM_APPROVALS_JSON = TELEGRAM_APPROVALS_DIR / "telegram_approvals.json"

# --- Web UI Approval Path (alternative) ---
WEB_APPROVAL_JSON = None  # Will be set via command line if needed

# --- Logging Setup ---
log_directory = SCRIPT_DIR / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"video_generation_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def load_config(config_path="config4_without_faceswap.json"):
    """Load and validate configuration file."""
    config_path_obj = SCRIPT_DIR / config_path
    try:
        with open(config_path_obj, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required keys
        required_keys = ['api_server_url', 'comfyui_api_url']
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required key '{key}' in config")
        
        config['api_server_url'] = config['api_server_url'].rstrip('/')
        config['comfyui_api_url'] = config['comfyui_api_url'].rstrip('/')
        
        logger.info(f"Config loaded successfully from {config_path_obj}")
        return config
    except Exception as e:
        logger.critical(f"Error loading config: {e}")
        sys.exit(1)

def trigger_generation(api_url: str, endpoint: str, prompt: str, face_filename: str | None,
                      output_subfolder: str, filename_prefix: str,
                      video_start_image: str | None = None):
    """Send request to intermediate API server to generate video."""
    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
    payload = {
        "prompt": prompt,
        "face": face_filename or "",
        "output_subfolder": output_subfolder,
        "filename_prefix_text": filename_prefix
    }
    if endpoint == "generate_video" and video_start_image:
        payload["video_start_image_path"] = video_start_image

    logger.info(f"  ➡️ API Call -> {endpoint}: Preparing request...")
    logger.info(f"     URL: {full_url}")
    logger.info(f"     Prompt: '{prompt[:70]}...'")
    logger.info(f"     Face: '{face_filename or 'None'}'")
    logger.info(f"     Output Subfolder: '{output_subfolder}'")
    logger.info(f"     Filename Prefix: '{filename_prefix}'")
    if video_start_image:
        logger.info(f"     Video Start Image: '{video_start_image}'")

    for attempt in range(1, MAX_API_RETRIES + 1):
        logger.info(f"  🚀 API Call (Attempt {attempt}/{MAX_API_RETRIES})")
        try:
            response = requests.post(full_url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response_data = response.json()

            logger.info(f"  ✅ API call submitted successfully (HTTP {response.status_code})")
            api_status = response_data.get('status', 'N/A')
            comfy_prompt_id = response_data.get('prompt_id', 'N/A')

            if api_status == 'submitted' and comfy_prompt_id and comfy_prompt_id != 'N/A':
                return comfy_prompt_id
            else:
                logger.error(f"API submission failed. Status: {api_status}, ID: {comfy_prompt_id}")
                return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ API Error (Attempt {attempt}): {e}")
            if attempt < MAX_API_RETRIES:
                time.sleep(API_RETRY_DELAY)
            else:
                logger.error(f"  ❌ API call failed after {MAX_API_RETRIES} attempts.")
                return None
        except Exception as e:
            logger.error(f"  ❌ Unexpected error: {e}", exc_info=True)
            return None

    return None

def check_comfyui_job_status(comfyui_base_url: str, prompt_id: str):
    """Poll ComfyUI /history endpoint for job status."""
    if not prompt_id:
        return None
    
    history_url = f"{comfyui_base_url}/history/{prompt_id}"
    try:
        response = requests.get(history_url, timeout=10)
        response.raise_for_status()
        history_data = response.json()
        
        if prompt_id in history_data:
            logger.debug(f"History found for prompt_id {prompt_id}")
            return history_data[prompt_id]
        else:
            logger.debug(f"Prompt_id {prompt_id} not found in history (still running)")
            return None
    except Exception as e:
        logger.warning(f"Error polling history for {prompt_id}: {e}")
        return None

def load_telegram_approvals():
    """Load and parse Telegram approval data."""
    if not TELEGRAM_APPROVALS_JSON.exists():
        logger.error(f"Telegram approvals file not found: {TELEGRAM_APPROVALS_JSON}")
        return []
    
    try:
        with open(TELEGRAM_APPROVALS_JSON, "r", encoding="utf-8") as f:
            telegram_result = json.load(f)
        
        approved_details = []
        for img_path_str, info in telegram_result.items():
            if info.get("status") == "approve":
                img_path = Path(img_path_str)
                
                # Extract metadata from filename if possible
                # Expected format: 001_swapped_00001_.png
                filename_parts = img_path.stem.split('_')
                try:
                    orig_index = int(filename_parts[0]) if filename_parts else 0
                except ValueError:
                    orig_index = len(approved_details) + 1
                
                approved_details.append({
                    "approved_image_path": str(img_path),
                    "original_index": orig_index,
                    "batch_image_index": 0,  # Default to 0 if not in filename
                    "prompt": info.get("prompt", ""),
                    "face_filename": "swapped" in img_path.stem,
                    "token": info.get("token", "")
                })
        
        return approved_details
    
    except Exception as e:
        logger.error(f"Error loading Telegram approvals: {e}", exc_info=True)
        return []

def load_web_approvals(approval_file_path):
    """Load Web UI approval data."""
    if not Path(approval_file_path).exists():
        logger.error(f"Web approval file not found: {approval_file_path}")
        return []
    
    try:
        with open(approval_file_path, 'r', encoding='utf-8') as f:
            approval_data = json.load(f)
        return approval_data.get("approved_images", [])
    except Exception as e:
        logger.error(f"Error loading web approvals: {e}", exc_info=True)
        return []

def main():
    """Main execution logic for video generation from approved images."""
    logger.info("=" * 50)
    logger.info("Starting Video Generation from Approved Images")
    logger.info("=" * 50)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Generate videos from approved images")
    parser.add_argument('--source', choices=['telegram', 'web'], default='telegram',
                       help='Source of approved images')
    parser.add_argument('--web-approval-file', type=str,
                       help='Path to web UI approval JSON file')
    parser.add_argument('--output-suffix', type=str, default='',
                       help='Suffix for output folder name')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    API_SERVER_URL = config['api_server_url']
    COMFYUI_BASE_URL = config['comfyui_api_url']
    
    # Verify paths exist
    if not COMFYUI_INPUT_DIR_BASE.is_dir():
        logger.critical(f"ComfyUI input directory not found: {COMFYUI_INPUT_DIR_BASE}")
        sys.exit(1)
    
    # Setup temp directory for video start images
    temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    try:
        temp_start_image_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temp directory: {temp_start_image_dir}")
    except Exception as e:
        logger.critical(f"Failed to create temp directory: {e}")
        sys.exit(1)
    
    # Load approved images based on source
    if args.source == 'telegram':
        approved_image_details = load_telegram_approvals()
    else:
        if not args.web_approval_file:
            logger.error("Web approval file path required when using --source web")
            sys.exit(1)
        approved_image_details = load_web_approvals(args.web_approval_file)
    
    if not approved_image_details:
        logger.error("No approved images found!")
        sys.exit(1)
    
    logger.info(f"Found {len(approved_image_details)} approved images")
    
    # Generate timestamp for this run
    script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_suffix = f"_{args.output_suffix}" if args.output_suffix else ""
    comfyui_video_output_subfolder = f"VideoRun_{script_run_timestamp}{run_suffix}/videos"
    
    # Create output directory for logs
    output_base = SCRIPT_DIR / "video_generation_runs" / f"run_{script_run_timestamp}{run_suffix}"
    output_base.mkdir(parents=True, exist_ok=True)
    
    # ====================================================
    # STAGE 1: Submit Video Generation Jobs
    # ====================================================
    logger.info(f"\n--- STAGE 1: Submitting {len(approved_image_details)} Video Generation Jobs ---")
    
    all_submitted_video_jobs = []
    video_progress_bar = tqdm(approved_image_details, desc="Submitting Videos")
    successful_submissions = 0
    
    for idx, approved_info in enumerate(video_progress_bar):
        approved_image_path = Path(approved_info['approved_image_path'])
        
        if not approved_image_path.exists():
            logger.warning(f"Approved image not found: {approved_image_path}")
            continue
        
        # Extract metadata
        orig_index = approved_info.get('original_index', idx + 1)
        batch_index = approved_info.get('batch_image_index', 0)
        prompt = approved_info.get('prompt', '')
        face_filename = approved_info.get('face_filename')
        
        # Generate video filename
        video_filename_prefix = f"{orig_index:03d}_batch{batch_index}_video"
        if isinstance(face_filename, bool):
            video_filename_prefix += "_swapped" if face_filename else "_raw"
        elif face_filename:
            video_filename_prefix += f"_{Path(face_filename).stem}"
        
        video_progress_bar.set_description(
            f"Video {idx+1}/{len(approved_image_details)} (Idx {orig_index})"
        )
        
        logger.info(f"\n🎬 Video Request [{idx+1}/{len(approved_image_details)}]")
        logger.info(f"   Original Index: {orig_index}, Batch: {batch_index}")
        logger.info(f"   Using image: {approved_image_path.name}")
        
        # Copy image to temp directory
        temp_start_image_comfy_path_str = None
        try:
            temp_filename = f"start_{orig_index:03d}_b{batch_index}_{datetime.now():%H%M%S%f}{approved_image_path.suffix}"
            temp_dest_path = temp_start_image_dir / temp_filename
            shutil.copyfile(approved_image_path, temp_dest_path)
            
            # Create relative path for ComfyUI
            temp_start_image_comfy_path = Path(TEMP_VIDEO_START_SUBDIR) / temp_filename
            temp_start_image_comfy_path_str = temp_start_image_comfy_path.as_posix()
            
            logger.info(f"   Copied to ComfyUI input: {temp_start_image_comfy_path_str}")
        except Exception as e:
            logger.error(f"   Failed to copy image: {e}")
            continue
        
        # Submit video generation
        comfy_video_prompt_id = trigger_generation(
            API_SERVER_URL, 
            "generate_video", 
            prompt or "A beautiful video", 
            face_filename if isinstance(face_filename, str) else None,
            comfyui_video_output_subfolder, 
            video_filename_prefix,
            video_start_image=temp_start_image_comfy_path_str
        )
        
        if comfy_video_prompt_id:
            all_submitted_video_jobs.append({
                "index": idx + 1,
                "original_index": orig_index,
                "batch_index": batch_index,
                "video_prompt_id": comfy_video_prompt_id,
                "video_prefix": video_filename_prefix,
                "video_job_status": "submitted",
                "approved_image_used": str(approved_image_path),
                "temp_image_path": str(temp_dest_path)
            })
            successful_submissions += 1
        else:
            logger.error(f"   Failed to submit video job {idx+1}")
        
        time.sleep(0.5)  # Small delay between submissions
    
    video_progress_bar.close()
    logger.info(f"\n--- STAGE 1 Complete: {successful_submissions}/{len(approved_image_details)} videos submitted ---")
    
    # ====================================================
    # STAGE 2: Poll for Video Completion
    # ====================================================
    if not all_submitted_video_jobs:
        logger.warning("No video jobs to poll. Exiting.")
        return
    
    logger.info(f"\n--- STAGE 2: Polling {len(all_submitted_video_jobs)} Video Jobs ---")
    
    video_ids_to_poll = [job['video_prompt_id'] for job in all_submitted_video_jobs]
    video_polling_progress = tqdm(total=len(video_ids_to_poll), desc="Polling Videos")
    
    start_poll_time = datetime.now()
    overall_timeout = POLLING_TIMEOUT_VIDEO * len(video_ids_to_poll)
    active_poll_ids = set(video_ids_to_poll)
    completed_count = 0
    
    while active_poll_ids and (datetime.now() - start_poll_time < timedelta(seconds=overall_timeout)):
        completed_in_pass = set()
        
        for prompt_id in list(active_poll_ids):
            history_data = check_comfyui_job_status(COMFYUI_BASE_URL, prompt_id)
            if history_data:
                logger.info(f"   ✅ Video job {prompt_id} completed")
                
                # Update job status
                for job in all_submitted_video_jobs:
                    if job['video_prompt_id'] == prompt_id:
                        job['video_job_status'] = 'completed'
                        break
                
                completed_in_pass.add(prompt_id)
        
        # Update progress
        active_poll_ids -= completed_in_pass
        completed_count = len(video_ids_to_poll) - len(active_poll_ids)
        video_polling_progress.n = completed_count
        video_polling_progress.refresh()
        
        if not active_poll_ids:
            logger.info("   ✅ All video jobs completed!")
            break
        
        # Update description with time elapsed
        elapsed = (datetime.now() - start_poll_time).total_seconds()
        video_polling_progress.set_description(
            f"Polling ({completed_count}/{len(video_ids_to_poll)} done, {int(elapsed)}s)"
        )
        
        time.sleep(POLLING_INTERVAL * 2)  # Longer interval for video polling
    
    video_polling_progress.close()
    
    # Mark remaining jobs as timeout
    for job in all_submitted_video_jobs:
        if job['video_prompt_id'] in active_poll_ids:
            job['video_job_status'] = 'polling_timeout'
    
    completed_final = sum(1 for job in all_submitted_video_jobs if job['video_job_status'] == 'completed')
    timeout_count = len(active_poll_ids)
    
    logger.info(f"\n--- STAGE 2 Complete: {completed_final} completed, {timeout_count} timed out ---")
    
    # ====================================================
    # STAGE 3: Cleanup Temporary Files
    # ====================================================
    logger.info(f"\n--- STAGE 3: Cleaning up temporary files ---")
    
    cleanup_success = 0
    cleanup_failed = 0
    
    # Delete individual temp files first
    for job in all_submitted_video_jobs:
        if 'temp_image_path' in job:
            temp_path = Path(job['temp_image_path'])
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    cleanup_success += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {temp_path}: {e}")
                    cleanup_failed += 1
    
    # Try to remove the temp directory
    try:
        if temp_start_image_dir.exists():
            remaining_files = list(temp_start_image_dir.iterdir())
            if remaining_files:
                logger.warning(f"Temp directory still has {len(remaining_files)} files")
            else:
                temp_start_image_dir.rmdir()
                logger.info("Removed empty temp directory")
    except Exception as e:
        logger.error(f"Failed to remove temp directory: {e}")
    
    logger.info(f"Cleanup complete: {cleanup_success} files deleted, {cleanup_failed} failed")
    
    # ====================================================
    # STAGE 4: Save Results and Summary
    # ====================================================
    logger.info(f"\n--- STAGE 4: Saving results ---")
    
    # Save job details
    results_file = output_base / "video_generation_results.json"
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": script_run_timestamp,
                "source": args.source,
                "total_approved_images": len(approved_image_details),
                "total_submitted": successful_submissions,
                "total_completed": completed_final,
                "total_timeout": timeout_count,
                "comfyui_output_subfolder": comfyui_video_output_subfolder,
                "jobs": all_submitted_video_jobs
            }, f, indent=2)
        logger.info(f"Results saved to: {results_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
    
    # Print summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Video Generation Summary:")
    logger.info(f"   Source: {args.source}")
    logger.info(f"   Approved Images Found: {len(approved_image_details)}")
    logger.info(f"   Videos Submitted: {successful_submissions}")
    logger.info(f"   Videos Completed: {completed_final}")
    logger.info(f"   Videos Timed Out: {timeout_count}")
    logger.info(f"   Output Location: {COMFYUI_OUTPUT_DIR_BASE / comfyui_video_output_subfolder}")
    logger.info(f"   Results File: {results_file}")
    logger.info("=" * 50)
    logger.info("🎉 Video generation complete!")

if __name__ == "__main__":
    main()