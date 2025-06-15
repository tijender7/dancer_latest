# upscale_4k_parallel.py
import os
import subprocess
import time
import logging
import sys
import concurrent.futures
from datetime import datetime
from pathlib import Path
try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

# ==============================================================================
#  CONFIGURATION - 4K VERSION
# ==============================================================================

# --- Paths ---
COMFYUI_OUTPUT_DIR_BASE = Path(r"H:/dancers_content") # Base directory containing Run_* folders
VIDEO_PARENT_SUBFOLDER = "all_videos"                 # Subfolder within Run_* containing date folders
UPSCALE_SUBFOLDER = "4k_upscaled"                     # Subfolder within Run_* to save 4K upscaled videos

# --- Topaz Specific Configuration ---
TOPAZ_INSTALL_DIR = Path(r"C:\Program Files\Topaz Labs LLC\Topaz Video AI")
TOPAZ_MODEL_DIR = Path(r"C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models")
TOPAZ_FFMPEG_EXE = TOPAZ_INSTALL_DIR / "ffmpeg.exe"
TOPAZ_TIMEOUT = 7200 # Timeout per video in seconds (2 hours)

# --- 4K Target Filters & Settings ---
TARGET_BITRATE_KBPS = "15000k" # Target avg bitrate for 4K (e.g., 15 Mbps). Adjust if needed.
MAX_BITRATE_KBPS = "25000k"    # Max peak bitrate for 4K (e.g., 25 Mbps). Adjust if needed.
AUDIO_BITRATE_KBPS = "192k"    # Audio bitrate (e.g., 192 kbps AAC).

# Filter complex targeting 4K output
TOPAZ_FILTER_COMPLEX = (
    "tvai_fi=model=chr-2:slowmo=1:rdt=0.01:fps=30:device=0:vram=1:instances=1," # Frame interpolation to 30fps
    "tvai_up=model=prob-4:scale=2:preblur=-0.334523:noise=0.05:details=0.2:halo=0.0573913:blur=0.14:compression=0.535133:blend=0.2:device=0:vram=1:instances=1," # First upscale pass (e.g., 2x)
    "tvai_up=model=amq-13:scale=0:w=3840:h=2160:blend=0.2:device=0:vram=1:instances=1," # Second upscale pass to target 4K
    "scale=w=3840:h=2160:flags=lanczos:threads=0:force_original_aspect_ratio=decrease," # Ensure final scale is 4K, keep aspect ratio
    "pad=3840:2160:-1:-1:color=black" # Pad if needed to strictly meet 3840x2160
)

# Encoder settings using VBR for bitrate control, including audio
TOPAZ_ENCODER_SETTINGS = (
    f"-c:v h264_nvenc -profile:v high -pix_fmt yuv420p -g 30 " # H.264 NVENC settings
    f"-preset p6 -tune hq " # Preset p6 (very slow/better quality) or p7 (slowest/best)
    f"-rc vbr -cq 22 " # Rate Control: Variable Bitrate, CQ level 22 (adjust 20-24 as needed)
    f"-b:v {TARGET_BITRATE_KBPS} -maxrate {MAX_BITRATE_KBPS} -bufsize {int(float(MAX_BITRATE_KBPS[:-1])*1.5)}k " # <<< BITRATE CONTROL
    f"-rc-lookahead 20 -spatial_aq 1 -aq-strength 15 " # Quality enhancements
    f"-c:a aac -b:a {AUDIO_BITRATE_KBPS} -ac 2 " # <<< AUDIO ENCODING (AAC, Stereo)
    f"-map_metadata 0 -map_metadata:s:v 0:s:v " # Keep metadata
    f"-movflags frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr -bf 2" # MP4 container flags, 2 B-Frames
)

# --- Parallel Processing Settings ---
MAX_CONCURRENT_UPSCALES = 1 # Adjust based on GPU VRAM and capability (start low!)

# ==============================================================================
#  Logging Setup
# ==============================================================================
script_dir = Path(__file__).resolve().parent
log_directory = script_dir / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"upscale_4k_parallel_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8'); file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.INFO)
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler); logger.addHandler(console_handler)

# ==============================================================================
#  Topaz Upscaling Function
# ==============================================================================
def upscale_video_topaz(task_id, input_video_path: Path, output_video_path: Path):
    """Runs the Topaz FFmpeg command. Returns True on success, False on failure."""
    label = f"4K Upscale Task {task_id}"
    logger.info(f"  ⬆️ Starting {label}: '{input_video_path.name}' -> '{output_video_path.name}'")

    start = time.time()
    env_vars = os.environ.copy()
    env_vars["TVAI_MODEL_DIR"] = str(TOPAZ_MODEL_DIR.resolve())
    env_vars["CUDA_VISIBLE_DEVICES"] = "0" # Or specify GPU if needed

    # Construct the FFmpeg command using defined settings
    command = ( f'"{str(TOPAZ_FFMPEG_EXE)}" -y -hide_banner -hwaccel auto -i "{str(input_video_path)}" '
                f'-sws_flags spline+accurate_rnd+full_chroma_int -filter_complex "{TOPAZ_FILTER_COMPLEX}" '
                f'{TOPAZ_ENCODER_SETTINGS} "{str(output_video_path)}"' )

    result = None
    stderr_snippet = "[No STDERR captured]" # Default snippet

    try:
        logger.debug(f"    Executing command for {label}: {command}")
        result = subprocess.run( command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(TOPAZ_INSTALL_DIR), env=env_vars, timeout=TOPAZ_TIMEOUT )
        end = time.time()
        # Check success: return code 0 AND output file exists AND is reasonably sized (e.g., > 10KB)
        success = (result.returncode == 0 and output_video_path.exists() and output_video_path.stat().st_size > 10240)

        if result and result.stderr:
             stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-20:]) # Last 20 lines

        if success:
            logger.info(f"    ✅ {label} finished successfully in {round(end - start, 2)}s. Output size: {output_video_path.stat().st_size / (1024*1024):.2f} MB")
            return True
        else:
            logger.error(f"    ❌ {label} failed.")
            logger.error(f"       Input: {input_video_path.name}")
            if result:
                 logger.error(f"       FFmpeg Exit Code: {result.returncode}")
                 logger.error(f"       STDERR Snippet:\n{stderr_snippet}")
            else:
                 logger.error("       FFmpeg process likely did not start or finish properly.")
            if not output_video_path.exists():
                 logger.error(f"       Output file not found: {output_video_path}")
            elif output_video_path.stat().st_size <= 10240:
                 logger.error(f"       Output file invalid or too small: {output_video_path} ({output_video_path.stat().st_size} bytes)")
            # Attempt to clean up failed/small output file
            if output_video_path.exists() and output_video_path.stat().st_size <= 10240:
                try:
                    output_video_path.unlink()
                    logger.warning(f"       Removed small/invalid output file: {output_video_path.name}")
                except Exception as rm_err:
                    logger.error(f"       Failed to remove small/invalid output file: {rm_err}")
            return False

    except subprocess.TimeoutExpired:
         logger.error(f"    ❌ {label} timed out after {TOPAZ_TIMEOUT} seconds for {input_video_path.name}.")
         # Clean up potentially incomplete file on timeout
         if output_video_path.exists():
             try: output_video_path.unlink(); logger.warning(f"       Removed potentially incomplete output file due to timeout: {output_video_path.name}")
             except Exception as rm_err: logger.error(f"       Failed to remove timed-out output file: {rm_err}")
         return False
    except Exception as e:
        logger.error(f"    ❌ Python error during {label} for {input_video_path.name}: {e}", exc_info=True)
        if result and result.stderr: # Log stderr even on Python error if available
             stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-20:])
             logger.error(f"       STDERR Snippet:\n{stderr_snippet}")
        return False

# ==============================================================================
#  Main Script Logic
# ==============================================================================
if __name__ == "__main__":
    logger.info("=" * 50); logger.info(f"Starting Parallel 4K Upscaling Script: {datetime.now()}"); logger.info("=" * 50)

    # --- Pre-checks ---
    if not COMFYUI_OUTPUT_DIR_BASE.is_dir(): logger.critical(f"CRITICAL: Base ComfyUI output directory not found: {COMFYUI_OUTPUT_DIR_BASE}. Exiting."); sys.exit(1)
    if not TOPAZ_FFMPEG_EXE.is_file(): logger.critical(f"CRITICAL: Topaz FFmpeg not found: {TOPAZ_FFMPEG_EXE}. Exiting."); sys.exit(1)
    if not TOPAZ_MODEL_DIR.is_dir(): logger.warning(f"WARNING: Topaz Model Directory not found: {TOPAZ_MODEL_DIR}.") # Non-critical if models are cached elsewhere

    # --- Find the latest 'Run_*' folder ---
    try:
        run_folders = sorted( [d for d in COMFYUI_OUTPUT_DIR_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")], key=lambda x: x.stat().st_mtime, reverse=True )
        if not run_folders: logger.critical(f"CRITICAL: No 'Run_*' folders found in '{COMFYUI_OUTPUT_DIR_BASE}'. Exiting."); sys.exit(1)
        latest_run_folder = run_folders[0]; logger.info(f"Found latest run folder: {latest_run_folder}")
    except Exception as e: logger.critical(f"CRITICAL: Error finding latest run folder: {e}", exc_info=True); sys.exit(1)

    # --- Define source and destination paths ---
    video_source_parent_dir = latest_run_folder / VIDEO_PARENT_SUBFOLDER
    upscaled_output_parent_dir = latest_run_folder / UPSCALE_SUBFOLDER # Uses the configured subfolder name

    if not video_source_parent_dir.is_dir():
        logger.error(f"Video source parent folder '{VIDEO_PARENT_SUBFOLDER}' not found in '{latest_run_folder}'. Nothing to process. Exiting."); sys.exit(0)

    # --- Find the Date Subfolder (assuming only one) ---
    try:
        # Look for exactly one subfolder that looks like a date (e.g., "202504")
        date_folders = [d for d in video_source_parent_dir.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) >= 6] # Flexible date length check
        if not date_folders:
            logger.error(f"No date-like subfolder found inside '{video_source_parent_dir}'. Nothing to process. Exiting."); sys.exit(0)
        elif len(date_folders) > 1:
            logger.warning(f"Multiple date-like subfolders found in '{video_source_parent_dir}'. Using the most recently modified one: {date_folders[-1].name}")
            videos_to_upscale_dir = sorted(date_folders, key=lambda x: x.stat().st_mtime)[-1] # Pick latest modified
        else:
            videos_to_upscale_dir = date_folders[0]

        logger.info(f"Found video source date folder: {videos_to_upscale_dir}")

        # Create the corresponding output directory (e.g., Run_.../4k_upscaled/202504)
        upscaled_output_dir = upscaled_output_parent_dir / videos_to_upscale_dir.name
        upscaled_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"4K Upscaled videos will be saved to: {upscaled_output_dir}")

    except Exception as e: logger.critical(f"CRITICAL: Error accessing subfolders within '{video_source_parent_dir}': {e}", exc_info=True); sys.exit(1)

    # --- Find videos to process ---
    video_files = sorted(list(videos_to_upscale_dir.glob("*.mp4"))) # Only look for .mp4 files
    if not video_files: logger.warning(f"No video files (*.mp4) found in '{videos_to_upscale_dir}'. Exiting."); sys.exit(0)
    logger.info(f"Found {len(video_files)} MP4 videos to process in '{videos_to_upscale_dir.name}'.")

    # --- Prepare tasks for parallel execution ---
    tasks = []
    for i, video_path in enumerate(video_files):
        base_name = video_path.stem
        # Append a suffix like '_topaz_4k' to avoid overwriting if run multiple times? (Optional)
        # Example: upscaled_filename = f"{base_name}_topaz_4k{video_path.suffix}"
        upscaled_filename = f"{base_name}_upscaled{video_path.suffix}" # Original naming convention
        upscaled_output_path = upscaled_output_dir / upscaled_filename
        task_id = f"{i+1:03d}"

        # --- Check if output already exists ---
        if upscaled_output_path.exists() and upscaled_output_path.stat().st_size > 10240:
            logger.info(f"  ⏭️ Skipping Task {task_id}: Output file already exists and seems valid: '{upscaled_output_path.name}'")
            continue # Skip adding this task

        tasks.append((task_id, video_path, upscaled_output_path))

    if not tasks:
        logger.info("All videos seem to be already processed or no videos found. Exiting.")
        sys.exit(0)

    logger.info(f"\n--- Starting Topaz 4K Video Upscaling ({len(tasks)} tasks, {MAX_CONCURRENT_UPSCALES} parallel) ---")
    successful_upscales = 0
    failed_upscales = 0

    # --- Execute tasks in parallel ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPSCALES) as executor:
        # Store future alongside its task details for better error reporting
        future_to_task = {executor.submit(upscale_video_topaz, task_id, vid_path, out_path): (task_id, vid_path.name) for task_id, vid_path, out_path in tasks}

        # Process completed futures using tqdm progress bar
        for future in tqdm(concurrent.futures.as_completed(future_to_task), total=len(tasks), desc="Upscaling 4K Videos"):
            task_id, video_name = future_to_task[future]
            try:
                success = future.result() # Get result (True/False) from upscale_video_topaz
                if success:
                    successful_upscales += 1
                else:
                    failed_upscales += 1
                    # Error already logged within the function, but can add a summary warning
                    logger.warning(f"Upscaling task {task_id} reported failure for: {video_name}")
            except Exception as exc:
                failed_upscales += 1
                logger.error(f"Task {task_id} for '{video_name}' generated an unexpected exception: {exc}", exc_info=True)

    # --- Final Summary ---
    logger.info(f"\n--- Finished 4K Upscaling ({successful_upscales} successful, {failed_upscales} failed) ---")
    logger.info(f"Upscaled 4K videos saved in: {upscaled_output_dir}")
    logger.info("=" * 50)