# upscale_latest_run_v3_parallel.py (Adds Parallel Processing)
import os
import subprocess
import time
import logging
import sys
import concurrent.futures # Import concurrency library
from datetime import datetime
from pathlib import Path
try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

# ==============================================================================
#  CONFIGURATION
# ==============================================================================

# --- Paths ---
COMFYUI_OUTPUT_DIR_BASE = Path(r"H:/dancers_content")
VIDEO_PARENT_SUBFOLDER = "all_videos"
UPSCALE_SUBFOLDER = "Upscaled_Topaz"

# --- Topaz Specific Configuration ---
TOPAZ_INSTALL_DIR = Path(r"C:\Program Files\Topaz Labs LLC\Topaz Video AI")
TOPAZ_MODEL_DIR = Path(r"C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models")
TOPAZ_FFMPEG_EXE = TOPAZ_INSTALL_DIR / "ffmpeg.exe"
TOPAZ_FILTER_COMPLEX = (
    "tvai_fi=model=chr-2:slowmo=1:rdt=0.01:fps=30:device=0:vram=1:instances=1,"
    "tvai_up=model=prob-4:scale=2:preblur=-0.334523:noise=0.05:details=0.2:halo=0.0573913:blur=0.14:compression=0.535133:blend=0.2:device=0:vram=1:instances=1,"
    "tvai_up=model=amq-13:scale=0:w=3840:h=2160:blend=0.2:device=0:vram=1:instances=1,"
    "scale=w=3840:h=2160:flags=lanczos:threads=0:force_original_aspect_ratio=decrease,"
    "pad=3840:2160:-1:-1:color=black"
)
TOPAZ_ENCODER_SETTINGS = (
    "-c:v h264_nvenc -profile:v high -pix_fmt yuv420p -g 30 "
    "-preset p7 -tune hq -rc constqp -qp 18 -rc-lookahead 20 -spatial_aq 1 -aq-strength 15 "
    "-b:v 0 -an -map_metadata 0 -map_metadata:s:v 0:s:v "
    "-movflags frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr -bf 0"
)
TOPAZ_TIMEOUT = 7200 # Timeout per video

# --- !! PARALLEL PROCESSING SETTINGS !! ---
# Number of FFmpeg processes to run concurrently.
# Start low (1 or 2) and increase carefully while monitoring GPU VRAM/Usage.
# If GPU hits 100% or VRAM is full, increasing workers won't help.
MAX_CONCURRENT_UPSCALES = 1 # <<< ADJUST THIS BASED ON YOUR SYSTEM (e.g., 1, 2, 3)

# ==============================================================================
#  Logging Setup (Same as before)
# ==============================================================================
script_dir = Path(__file__).resolve().parent
log_directory = script_dir / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"upscale_parallel_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8'); file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.INFO)
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler); logger.addHandler(console_handler)

# ==============================================================================
#  Topaz Upscaling Function (Modified slightly for parallel logging)
# ==============================================================================
# upscale_latest_run_v3_parallel.py

# ... (Keep imports and configuration the same) ...

# ==============================================================================
#  Logging Setup (Same as before)
# ==============================================================================
# ... (Keep logging setup the same) ...

# ==============================================================================
#  Topaz Upscaling Function (CORRECTED f-string error)
# ==============================================================================
def upscale_video_topaz(task_id, input_video_path: Path, output_video_path: Path):
    """Runs the Topaz FFmpeg command. Returns True on success, False on failure."""
    label = f"Upscale Task {task_id}"
    logger.info(f"  ⬆️ Starting {label}: '{input_video_path.name}' -> '{output_video_path.name}'")

    start = time.time()
    env_vars = os.environ.copy()
    env_vars["TVAI_MODEL_DIR"] = str(TOPAZ_MODEL_DIR.resolve())

    command = ( f'"{str(TOPAZ_FFMPEG_EXE)}" -y -hide_banner -hwaccel auto -i "{str(input_video_path)}" '
                f'-sws_flags spline+accurate_rnd+full_chroma_int -filter_complex "{TOPAZ_FILTER_COMPLEX}" '
                f'{TOPAZ_ENCODER_SETTINGS} "{str(output_video_path)}"' )

    result = None
    stderr_snippet = "[No STDERR captured]" # Default snippet

    try:
        result = subprocess.run( command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(TOPAZ_INSTALL_DIR), env=env_vars, timeout=TOPAZ_TIMEOUT )
        end = time.time()
        success = (result.returncode == 0 and output_video_path.exists() and output_video_path.stat().st_size > 10240)

        # Prepare stderr snippet *before* the f-string if needed
        if result and result.stderr:
             stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-20:]) # Last 20 lines

        if success:
            logger.info(f"    ✅ {label} finished successfully in {round(end - start, 2)}s.")
            return True
        else:
            logger.error(f"    ❌ {label} failed.")
            logger.error(f"       Input: {input_video_path.name}")
            if result: # Check if result object exists
                 logger.error(f"       FFmpeg Exit Code: {result.returncode}")
                 logger.error(f"       STDERR Snippet:\n{stderr_snippet}") # Use the prepared snippet
            else:
                 logger.error("       FFmpeg process likely did not start or finish.")
            if not output_video_path.exists() or output_video_path.stat().st_size <= 10240:
                 logger.error(f"       Output file invalid or too small: {output_video_path}")
            return False

    except subprocess.TimeoutExpired:
         logger.error(f"    ❌ {label} timed out after {TOPAZ_TIMEOUT} seconds.")
         return False
    except Exception as e:
        logger.error(f"    ❌ Python error during {label} upscaling: {e}", exc_info=True)
        # Prepare snippet again in case result exists but exception happened later
        if result and result.stderr:
             stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-20:])
        logger.error(f"       STDERR Snippet:\n{stderr_snippet}") # Log snippet even on Python error
        return False

# ==============================================================================
#  Main Script Logic (Same as before)
# ==============================================================================
if __name__ == "__main__":
    # ... (Keep the rest of the main execution logic exactly the same) ...
    logger.info("=" * 50); logger.info(f"Starting Parallel Upscaling Script (v3): {datetime.now()}"); logger.info("=" * 50)

    # --- Pre-checks ---
    if not TOPAZ_FFMPEG_EXE.is_file(): logger.critical(f"CRITICAL: Topaz FFmpeg not found: {TOPAZ_FFMPEG_EXE}. Exiting."); sys.exit(1)
    if not TOPAZ_MODEL_DIR.is_dir(): logger.warning(f"WARNING: Topaz Model Directory not found: {TOPAZ_MODEL_DIR}.")

    # --- Find the latest 'Run_*' folder ---
    try:
        run_folders = sorted( [d for d in COMFYUI_OUTPUT_DIR_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")], key=os.path.getmtime, reverse=True )
        if not run_folders: logger.critical(f"CRITICAL: No 'Run_*' folders found in '{COMFYUI_OUTPUT_DIR_BASE}'."); sys.exit(1)
        latest_run_folder = run_folders[0]; logger.info(f"Found latest run folder: {latest_run_folder}")
    except Exception as e: logger.critical(f"CRITICAL: Error finding latest run folder: {e}", exc_info=True); sys.exit(1)

    # --- Define paths ---
    video_parent_dir = latest_run_folder / VIDEO_PARENT_SUBFOLDER
    upscaled_parent_dir = latest_run_folder / UPSCALE_SUBFOLDER
    if not video_parent_dir.is_dir(): logger.error(f"Video source parent folder '{VIDEO_PARENT_SUBFOLDER}' not found in '{latest_run_folder}'. Exiting."); sys.exit(0)

    # --- Find the Date Subfolder ---
    try:
        date_folders = [d for d in video_parent_dir.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 6]
        if not date_folders: logger.error(f"No date subfolder found inside '{video_parent_dir}'. Exiting."); sys.exit(0)
        videos_to_upscale_dir = date_folders[0]; logger.info(f"Found video source date folder: {videos_to_upscale_dir}")
        upscaled_output_dir = upscaled_parent_dir / videos_to_upscale_dir.name; upscaled_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upscaled videos will be saved to: {upscaled_output_dir}")
    except Exception as e: logger.error(f"Error accessing subfolders within '{video_parent_dir}': {e}", exc_info=True); sys.exit(1)

    # --- Find videos ---
    video_files = sorted(list(videos_to_upscale_dir.glob("*.mp4")))
    if not video_files: logger.warning(f"No video files (*.mp4) found in '{videos_to_upscale_dir}'. Exiting."); sys.exit(0)
    logger.info(f"Found {len(video_files)} videos to process in '{videos_to_upscale_dir.name}'.")

    # --- Start Parallel Upscaling ---
    logger.info(f"\n--- Starting Topaz Video Upscaling ({MAX_CONCURRENT_UPSCALES} parallel tasks) ---")
    successful_upscales = 0; failed_upscales = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPSCALES) as executor:
        future_to_video = {}
        for i, video_path in enumerate(video_files):
            base_name = video_path.stem; upscaled_filename = f"{base_name}_upscaled{video_path.suffix}"
            upscaled_output_path = upscaled_output_dir / upscaled_filename; task_id = f"{i+1:03d}"
            future = executor.submit(upscale_video_topaz, task_id, video_path, upscaled_output_path)
            future_to_video[future] = video_path.name

        for future in tqdm(concurrent.futures.as_completed(future_to_video), total=len(video_files), desc="Upscaling Videos"):
            video_name = future_to_video[future]
            try:
                success = future.result()
                if success: successful_upscales += 1
                else: failed_upscales += 1; logger.warning(f"Upscaling task failed for: {video_name}")
            except Exception as exc: failed_upscales += 1; logger.error(f"Task for '{video_name}' generated an exception: {exc}", exc_info=True)

    logger.info(f"\n--- Finished Upscaling ({successful_upscales} successful, {failed_upscales} failed) ---")
    logger.info(f"Upscaled videos saved in: {upscaled_output_dir}")
    logger.info("=" * 50)