# upscale_latest_run_v2.py (Handles Date Subfolder)
import os
import subprocess
import time
import logging
import sys
from datetime import datetime
from pathlib import Path
try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm library not found. Please install it: pip install tqdm")
    sys.exit(1)

# ==============================================================================
#  CONFIGURATION (Same as before)
# ==============================================================================
COMFYUI_OUTPUT_DIR_BASE = Path(r"H:/dancers_content")
VIDEO_PARENT_SUBFOLDER = "all_videos" # Parent folder containing the date folder
UPSCALE_SUBFOLDER = "Upscaled_Topaz"
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
TOPAZ_TIMEOUT = 7200

# ==============================================================================
#  Logging Setup (Same as before)
# ==============================================================================
script_dir = Path(__file__).resolve().parent
log_directory = script_dir / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"upscale_run_{datetime.now():%Y%m%d_%H%M%S}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8'); file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.INFO)
if logger.hasHandlers(): logger.handlers.clear()
logger.addHandler(file_handler); logger.addHandler(console_handler)

# ==============================================================================
#  Topaz Upscaling Function (Same as before)
# ==============================================================================
def upscale_video_topaz(label, input_video_path: Path, output_video_path: Path):
    # (Keep the exact same function as before)
    logger.info(f"  ⬆️ {label}: Upscaling '{input_video_path.name}' -> '{output_video_path.name}'")
    if not input_video_path.is_file(): logger.error(f"    ❌ Input video not found: {input_video_path}"); return False
    if not TOPAZ_FFMPEG_EXE.is_file(): logger.error(f"    ❌ Topaz FFmpeg not found: {TOPAZ_FFMPEG_EXE}"); return False
    start = time.time(); env_vars = os.environ.copy(); env_vars["TVAI_MODEL_DIR"] = str(TOPAZ_MODEL_DIR.resolve())
    command = ( f'"{str(TOPAZ_FFMPEG_EXE)}" -y -hide_banner -hwaccel auto -i "{str(input_video_path)}" '
                f'-sws_flags spline+accurate_rnd+full_chroma_int -filter_complex "{TOPAZ_FILTER_COMPLEX}" '
                f'{TOPAZ_ENCODER_SETTINGS} "{str(output_video_path)}"' )
    result = None
    try:
        result = subprocess.run( command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(TOPAZ_INSTALL_DIR), env=env_vars, timeout=TOPAZ_TIMEOUT )
        end = time.time(); success = (result.returncode == 0 and output_video_path.exists() and output_video_path.stat().st_size > 10240)
        if success: logger.info(f"    ✅ Upscaling finished successfully in {round(end - start, 2)}s.") ; return True
        else:
            logger.error(f"    ❌ {label} Upscaling failed."); logger.error(f"       FFmpeg Exit Code: {result.returncode}")
            if not output_video_path.exists() or output_video_path.stat().st_size <= 10240: logger.error(f"       Output file invalid or too small: {output_video_path}")
            logger.error(f"       STDERR (Last 20 lines):\n" + '\n'.join(result.stderr.strip().splitlines()[-20:])); return False
    except subprocess.TimeoutExpired: logger.error(f"    ❌ {label} Upscaling timed out after {TOPAZ_TIMEOUT} seconds."); return False
    except Exception as e:
        logger.error(f"    ❌ Python error during {label} upscaling: {e}", exc_info=True)
        if result: logger.error(f"       STDERR (Last 20 lines):\n" + '\n'.join(result.stderr.strip().splitlines()[-20:]))
        return False

# ==============================================================================
#  Main Script Logic
# ==============================================================================
if __name__ == "__main__":
    logger.info("=" * 50); logger.info(f"Starting Separate Upscaling Script (v2 - Date Folder Aware): {datetime.now()}"); logger.info("=" * 50)

    # --- Find the latest 'Run_*' folder ---
    try:
        run_folders = sorted( [d for d in COMFYUI_OUTPUT_DIR_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")], key=os.path.getmtime, reverse=True )
        if not run_folders: logger.critical(f"CRITICAL: No 'Run_*' folders found in '{COMFYUI_OUTPUT_DIR_BASE}'."); sys.exit(1)
        latest_run_folder = run_folders[0]; logger.info(f"Found latest run folder: {latest_run_folder}")
    except Exception as e: logger.critical(f"CRITICAL: Error finding latest run folder: {e}", exc_info=True); sys.exit(1)

    # --- Define paths for this run ---
    video_parent_dir = latest_run_folder / VIDEO_PARENT_SUBFOLDER # Path to 'all_videos'
    upscaled_parent_dir = latest_run_folder / UPSCALE_SUBFOLDER   # Path to 'Upscaled_Topaz'

    if not video_parent_dir.is_dir():
        logger.error(f"Video source parent folder '{VIDEO_PARENT_SUBFOLDER}' not found inside '{latest_run_folder}'.")
        sys.exit(0)

    # --- Find the Date Subfolder within 'all_videos' ---
    try:
        date_folders = [d for d in video_parent_dir.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 6] # Find folders like '250414'
        if not date_folders:
            logger.error(f"No date subfolder (e.g., 'YYMMDD') found inside '{video_parent_dir}'. Cannot find videos.")
            # Optional: Check directly in 'all_videos' as a fallback?
            # videos_to_upscale_dir = video_parent_dir
            # logger.warning(f"Date folder not found, checking directly in {video_parent_dir}")
            # if not any(video_parent_dir.glob("*.mp4")): # Check if fallback has files
            #      sys.exit(0) # Exit if fallback is also empty
            sys.exit(0) # Exit if date folder required and not found

        # Assume the first found date folder is the correct one for this run
        videos_to_upscale_dir = date_folders[0]
        logger.info(f"Found video source date folder: {videos_to_upscale_dir}")
        # Create corresponding date folder in the output
        upscaled_output_dir = upscaled_parent_dir / videos_to_upscale_dir.name # e.g., .../Upscaled_Topaz/250414
        upscaled_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upscaled videos will be saved to: {upscaled_output_dir}")

    except Exception as e:
         logger.error(f"Error accessing subfolders within '{video_parent_dir}': {e}", exc_info=True)
         sys.exit(1)


    # --- Find videos to upscale within the date folder ---
    video_files = sorted(list(videos_to_upscale_dir.glob("*.mp4")))

    if not video_files:
        logger.warning(f"No video files (*.mp4) found in '{videos_to_upscale_dir}'. Nothing to upscale.")
        sys.exit(0)

    logger.info(f"Found {len(video_files)} videos to process in '{videos_to_upscale_dir.name}'.")

    # --- Start Upscaling ---
    logger.info("\n--- Starting Topaz Video Upscaling ---")
    upscaling_progress = tqdm(video_files, desc="Upscaling Videos")
    successful_upscales = 0; failed_upscales = 0

    for video_path in upscaling_progress:
        base_name = video_path.stem
        upscaled_filename = f"{base_name}_upscaled{video_path.suffix}"
        # Save to the date-specific upscale folder
        upscaled_output_path = upscaled_output_dir / upscaled_filename
        label = f"Upscale {video_path.name}"
        upscaling_progress.set_description(f"Upscaling {video_path.name[:20]}...")
        if upscale_video_topaz(label, video_path, upscaled_output_path): successful_upscales += 1
        else: failed_upscales += 1
        time.sleep(1) # Small pause

    upscaling_progress.close()
    logger.info(f"\n--- Finished Upscaling ({successful_upscales} successful, {failed_upscales} failed) ---")
    logger.info(f"Upscaled videos saved in: {upscaled_output_dir}") # Log the specific date folder
    logger.info("=" * 50)