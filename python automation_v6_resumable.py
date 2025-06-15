#!/usr/bin/env python
"""Sequentially run the dancer automation pipeline with parallel approval (Web UI and Telegram).

This script is now MODIFIED to be resumable from specific stages.
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
import argparse  # NEW: For better command-line argument parsing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

try:
    from flask import Flask, request, render_template_string, send_from_directory, url_for
except ImportError:
    print("ERROR: Flask library not found. Please install it: pip install Flask")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

load_dotenv()

# --- (All your constants and helper functions from the original script remain here unchanged) ---
# --- For brevity, I'll skip pasting them again. Just imagine all your functions like ---
# --- find_node_id_by_title, load_config, generate_prompts_ollama, save_prompts_log, ---
# --- trigger_generation, check_comfyui_job_status, get_output_filenames_from_history, ---
# --- and the entire Flask app section are here, exactly as you wrote them. ---

# [PASTE ALL YOUR ORIGINAL FUNCTIONS AND CONSTANTS HERE, FROM LINE 39 to LINE 920]
# ...
# I will assume all functions like `load_config`, `generate_prompts_ollama`, etc. exist.
# The following code starts *after* your last function definition.

# --- MODIFIED: Main Execution Logic with Stages ---

# NEW: Define the stages of the pipeline
STAGES = [
    "prompts", 
    "images", 
    "approval", 
    "videos", 
    "cleanup", 
    "summary"
]

def reconstruct_state_for_resume(resume_run_folder: Path, config: dict):
    """
    NEW: Loads state from a previous run to allow resuming.
    """
    logger.info(f"--- RESUMING RUN: Attempting to load state from {resume_run_folder} ---")
    if not resume_run_folder.is_dir():
        logger.critical(f"Resume folder not found: {resume_run_folder}")
        sys.exit(1)

    # Find the final details JSON file from the previous run
    details_file = next(resume_run_folder.glob("*_details_v6.json"), None)
    if not details_file:
        logger.critical(f"Could not find a '..._details_v6.json' file in {resume_run_folder} to resume from.")
        sys.exit(1)

    logger.info(f"Found details file: {details_file}")
    with open(details_file, 'r', encoding='utf-8') as f:
        run_details = json.load(f)

    # Convert paths back to Path objects
    for item in run_details:
        if 'generated_image_paths' in item:
            item['generated_image_paths'] = [Path(p) for p in item.get('generated_image_paths', [])]
        if 'video_jobs' in item:
            for vj in item['video_jobs']:
                if 'approved_image_used' in vj:
                    vj['approved_image_used'] = Path(vj['approved_image_used'])
    
    logger.info(f"Successfully loaded and reconstructed state for {len(run_details)} items.")
    
    # Also need the temp_start_image_dir path for cleanup
    temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    
    return run_details, resume_run_folder, temp_start_image_dir


def stage_1_generate_prompts(config):
    # This is the code from your original script for generating prompts
    logger.info("\n--- STAGE 1: Generating Prompts ---")
    prompts_data = generate_prompts_ollama(
        config["ollama_model"],
        config["num_prompts"],
        config.get("ollama_api_url", "http://localhost:11434/api/generate")
    )
    save_prompts_log(prompts_data)
    valid_prompts = [p for p in prompts_data if "generated_prompt" in p and p["generated_prompt"]]
    if not valid_prompts:
        logger.critical("No valid prompts generated. Stopping.")
        sys.exit(1)
    logger.info(f"Proceeding with {len(valid_prompts)} valid prompts.")
    return valid_prompts

def stage_2_generate_images(config, valid_prompts, main_run_folder_path):
    # This is the code from your original script for generating images and polling
    face_files = []
    source_faces_dir = config['source_faces_path']
    if source_faces_dir.is_dir():
        face_files = sorted([f for f in source_faces_dir.glob("*.*") if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
    
    run_details: list[dict] = []
    image_save_node_id = # ... [Find image save node logic here]
    # ... [All your image submission and polling logic goes here] ...
    # It should return the populated `run_details` list.
    logger.info("--- STAGE 2: Finished Image Generation and Polling ---")
    return run_details # This list now contains all info about generated images

def stage_3_wait_for_approval(run_details, main_run_folder_path, comfyui_output_base_path):
    # This is your approval logic (both Flask and Telegram)
    logger.info("\n--- STAGE 3: Waiting for Image Approval ---")
    # ... [All your parallel approval logic (Flask+Telegram threads) and the while loop to wait for the JSON file] ...
    # The function should return the list of `approved_image_details`
    approved_image_details = [] # This would be populated by your logic
    logger.info(f"--- STAGE 3: Approval received for {len(approved_image_details)} images. ---")
    
    # Copying approved images is part of this stage
    approved_images_folder_path = main_run_folder_path / APPROVED_IMAGES_SUBFOLDER
    # ... [Logic to copy files] ...
    
    return approved_image_details, approved_images_folder_path

def stage_4_generate_videos(config, approved_image_details, main_run_folder_path):
    # This is your video generation logic
    logger.info("\n--- STAGE 4: Generating Videos ---")
    if not approved_image_details:
        logger.info("No approved images. Skipping video generation.")
        return [], None
        
    temp_start_image_dir = COMFYUI_INPUT_DIR_BASE / TEMP_VIDEO_START_SUBDIR
    temp_start_image_dir.mkdir(parents=True, exist_ok=True)
    
    all_submitted_video_jobs = []
    # ... [All your video submission and polling logic goes here] ...
    # It should return the list of submitted jobs and the temp dir path
    logger.info("--- STAGE 4: Finished Video Generation and Polling ---")
    return all_submitted_video_jobs, temp_start_image_dir
    
def stage_5_cleanup(temp_start_image_dir):
    # This is your cleanup logic
    logger.info("\n--- STAGE 5: Cleaning up temporary files ---")
    if temp_start_image_dir and temp_start_image_dir.exists():
        try:
            shutil.rmtree(temp_start_image_dir)
            logger.info(f"Successfully removed temp directory: {temp_start_image_dir}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    else:
        logger.info("Temp directory does not exist or was not specified. Nothing to clean.")

def stage_6_summary(run_details, main_run_folder_path):
    # This is your final summary and log saving
    logger.info("\n--- STAGE 6: Final Summary ---")
    # ... [All your summary logging logic here] ...
    # ... [Logic to save the final `run_details` to a JSON file] ...
    logger.info("="*50)
    logger.info(f"🎉 Automation v6 Resumable Run Finished! {datetime.now()}")
    logger.info("="*50)

if __name__ == "__main__":
    # NEW: Argument parsing for resuming runs
    parser = argparse.ArgumentParser(description="Run the dancer automation pipeline, with resumable stages.")
    parser.add_argument(
        "--start-from", 
        type=str, 
        choices=STAGES, 
        default="prompts", 
        help="The stage to start execution from."
    )
    parser.add_argument(
        "--resume-run", 
        type=str, 
        default=None, 
        help="The name of the run folder (e.g., 'Run_20231027_123456') to resume."
    )
    args = parser.parse_args()

    # --- Initial Setup ---
    logger.info("=" * 50)
    logger.info(f"Starting Automation v6 (Resumable) Run: {datetime.now()}")
    logger.info(f"Command line args: --start-from {args.start_from}, --resume-run {args.resume_run}")
    logger.info("=" * 50)
    
    config = load_config("config4_without_faceswap.json")
    if not config:
        sys.exit(1)
        
    API_SERVER_URL = config['api_server_url']
    COMFYUI_BASE_URL = config['comfyui_api_url']
    # Verify paths...

    # --- State Initialization ---
    # MODIFIED: Logic to either start fresh or resume
    run_details = []
    main_run_folder_path = None
    temp_start_image_dir = None
    approved_image_details = []
    all_submitted_video_jobs = []

    if args.resume_run:
        if args.start_from == "prompts":
            logger.warning("Ignoring --resume-run because --start-from is 'prompts'. Starting a fresh run.")
            args.resume_run = None # Force a new run
        else:
            script_output_base = config['output_folder']
            resume_folder_path = script_output_base / args.resume_run
            run_details, main_run_folder_path, temp_start_image_dir = reconstruct_state_for_resume(resume_folder_path, config)
    
    if not args.resume_run:
        # This is a fresh run
        script_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_output_base = config['output_folder']
        main_run_folder_path = script_output_base / f"Run_{script_run_timestamp}"
        main_run_folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created new script run output directory: {main_run_folder_path}")

    # --- Main Execution Loop ---
    # MODIFIED: Sequentially run stages based on the start point
    
    start_index = STAGES.index(args.start_from)

    # Note: For a real implementation, you'd replace the print statements below
    # with calls to the stage functions defined above. This is a structural example.
    
    for i, stage_name in enumerate(STAGES):
        if i < start_index:
            logger.info(f"--- SKIPPING Stage: {stage_name.upper()} ---")
            continue

        logger.info(f"\n>>> EXECUTING Stage: {stage_name.upper()} <<<")

        if stage_name == "prompts":
            # This stage produces valid_prompts for the next one
            valid_prompts = stage_1_generate_prompts(config)
        
        elif stage_name == "images":
            # This stage needs valid_prompts, produces run_details
            run_details = stage_2_generate_images(config, valid_prompts, main_run_folder_path)

        elif stage_name == "approval":
            # This stage needs run_details, produces approved_image_details
            approved_image_details, _ = stage_3_wait_for_approval(run_details, main_run_folder_path, COMFYUI_OUTPUT_DIR_BASE)

        elif stage_name == "videos":
            # This stage needs approved_image_details
            # If we resumed, we need to re-run the approval-check part to load the JSON
            if args.resume_run and not approved_image_details:
                 logger.info("Resuming: Re-checking for approval files...")
                 approved_image_details, _ = stage_3_wait_for_approval(run_details, main_run_folder_path, COMFYUI_OUTPUT_DIR_BASE)
            
            all_submitted_video_jobs, temp_start_image_dir = stage_4_generate_videos(config, approved_image_details, main_run_folder_path)

        elif stage_name == "cleanup":
            stage_5_cleanup(temp_start_image_dir)

        elif stage_name == "summary":
            # Always save the latest state
            stage_6_summary(run_details, main_run_folder_path)

    print("DEBUG: Script finished.")