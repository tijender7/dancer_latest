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
#  CONFIGURATION - REELS CROPPING
# ==============================================================================
DANCERS_CONTENT_BASE = Path(r"H:\dancers_content")  # Fixed base directory
UPSCALED_SUBFOLDER = "4k_upscaled"
COMPILED_SUBFOLDER = "compiled"
REELS_SUBFOLDER = "reels"

# Instagram Reels specs: 1080x1920 (9:16 aspect ratio)
REELS_WIDTH = 1080
REELS_HEIGHT = 1920

# FFmpeg cropping - center crop from 4K (3840x2160) to Reels (1080x1920)
# Formula: crop=w:h:x:y where x=(input_width-crop_width)/2, y=(input_height-crop_height)/2
CROP_FILTER = f"crop={REELS_WIDTH}:{REELS_HEIGHT}:(iw-{REELS_WIDTH})/2:(ih-{REELS_HEIGHT})/2"

# High quality encoding for Instagram
REELS_ENCODER_SETTINGS = (
    f"-c:v libx264 -profile:v high -pix_fmt yuv420p "
    f"-crf 18 -preset slow "
    f"-b:v 8000k -maxrate 12000k -bufsize 16000k "
    f"-g 30 -keyint_min 30 -sc_threshold 0 "
    f"-c:a aac -b:a 128k -ac 2 -ar 44100 "
    f"-movflags +faststart"
)

MAX_CONCURRENT_CROPS = 2
CROP_TIMEOUT = 300  # 5 minutes per video

# ==============================================================================
#  Logging Setup
# ==============================================================================
script_dir = Path(__file__).resolve().parent
log_directory = script_dir / "logs"
log_directory.mkdir(exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
log_file = log_directory / f"reels_cropper_{datetime.now():%Y%m%d_%H%M%S}.log"
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

# ==============================================================================
#  Reels Cropping Function
# ==============================================================================
def crop_video_to_reels(task_id, input_video_path: Path, output_video_path: Path):
    """Crop 4K video to Instagram Reels format (1080x1920) from center"""
    label = f"Reels Crop Task {task_id}"
    logger.info(f"  ✂️ Starting {label}: '{input_video_path.name}' -> '{output_video_path.name}'")
    start_time = time.time()

    command = (
        f'ffmpeg -y -hide_banner -i "{str(input_video_path)}" '
        f'-vf "{CROP_FILTER}" '
        f'{REELS_ENCODER_SETTINGS} '
        f'"{str(output_video_path)}"'
    )

    try:
        logger.debug(f"    Executing command for {label}: {command}")
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace', 
            timeout=CROP_TIMEOUT
        )
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Check if cropping was successful
        success = (
            result.returncode == 0 and 
            output_video_path.exists() and 
            output_video_path.stat().st_size > 10240
        )

        if success:
            file_size_mb = output_video_path.stat().st_size / (1024 * 1024)
            logger.info(f"    ✅ {label} completed successfully in {duration}s. Output size: {file_size_mb:.2f} MB")
            return True
        else:
            logger.error(f"    ❌ {label} failed.")
            logger.error(f"       Input: {input_video_path.name}")
            logger.error(f"       FFmpeg Exit Code: {result.returncode}")
            
            if result.stderr:
                stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-10:])
                logger.error(f"       STDERR Snippet:\n{stderr_snippet}")
            
            # Clean up failed output
            if output_video_path.exists() and output_video_path.stat().st_size <= 10240:
                try:
                    output_video_path.unlink()
                    logger.warning(f"       Removed invalid output file: {output_video_path.name}")
                except Exception as rm_err:
                    logger.error(f"       Failed to remove invalid output file: {rm_err}")
            
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"    ❌ {label} timed out after {CROP_TIMEOUT} seconds for {input_video_path.name}")
        if output_video_path.exists():
            try:
                output_video_path.unlink()
                logger.warning(f"       Removed incomplete output file due to timeout: {output_video_path.name}")
            except Exception as rm_err:
                logger.error(f"       Failed to remove timed-out output file: {rm_err}")
        return False
        
    except Exception as e:
        logger.error(f"    ❌ Python error during {label} for {input_video_path.name}: {e}", exc_info=True)
        return False

# ==============================================================================
#  Main Script Logic
# ==============================================================================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info(f"Starting Instagram Reels Cropper: {datetime.now()}")
    logger.info("=" * 60)

    # Verify base directory exists
    if not DANCERS_CONTENT_BASE.is_dir():
        logger.critical(f"CRITICAL: Base directory not found: {DANCERS_CONTENT_BASE}. Exiting.")
        sys.exit(1)

    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("✅ FFmpeg found and accessible")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.critical("CRITICAL: FFmpeg not found in PATH. Please install FFmpeg. Exiting.")
        sys.exit(1)

    # --- Find the latest 'Run_*' folder ---
    try:
        run_folders = sorted(
            [d for d in DANCERS_CONTENT_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime, 
            reverse=True
        )
        
        if not run_folders:
            logger.critical(f"CRITICAL: No 'Run_*' folders found in '{DANCERS_CONTENT_BASE}'. Exiting.")
            sys.exit(1)
            
        latest_run_folder = run_folders[0]
        logger.info(f"📁 Found latest run folder: {latest_run_folder.name}")
        
    except Exception as e:
        logger.critical(f"CRITICAL: Error finding latest run folder: {e}", exc_info=True)
        sys.exit(1)

    # --- Set up source and destination paths ---
    source_compiled_dir = latest_run_folder / UPSCALED_SUBFOLDER / COMPILED_SUBFOLDER
    reels_output_dir = source_compiled_dir / REELS_SUBFOLDER
    
    # Create reels folder
    reels_output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📱 Reels output directory: {reels_output_dir}")

    # Verify source directory exists
    if not source_compiled_dir.is_dir():
        logger.error(f"Source compiled folder not found: {source_compiled_dir}. Nothing to process. Exiting.")
        sys.exit(0)

    # --- Find videos to process ---
    video_files = sorted(list(source_compiled_dir.glob("*.mp4")))
    if not video_files:
        logger.warning(f"No MP4 videos found in '{source_compiled_dir}'. Exiting.")
        sys.exit(0)
        
    logger.info(f"🎬 Found {len(video_files)} MP4 videos to crop for Instagram Reels")

    # --- Prepare cropping tasks ---
    tasks = []
    for i, video_path in enumerate(video_files):
        base_name = video_path.stem
        reels_filename = f"{base_name}_reels{video_path.suffix}"
        reels_output_path = reels_output_dir / reels_filename
        task_id = f"{i+1:03d}"

        # Skip if already processed
        if reels_output_path.exists() and reels_output_path.stat().st_size > 10240:
            logger.info(f"  ⏭️ Skipping Task {task_id}: Reels version already exists: '{reels_output_path.name}'")
            continue

        tasks.append((task_id, video_path, reels_output_path))

    if not tasks:
        logger.info("✨ All videos already processed or no new videos found. Exiting.")
        sys.exit(0)

    logger.info(f"\n🚀 Starting Instagram Reels cropping ({len(tasks)} tasks, {MAX_CONCURRENT_CROPS} parallel)")
    logger.info(f"📐 Target resolution: {REELS_WIDTH}x{REELS_HEIGHT} (9:16 aspect ratio)")
    
    successful_crops = 0
    failed_crops = 0

    # --- Execute cropping tasks in parallel ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CROPS) as executor:
        future_to_task = {
            executor.submit(crop_video_to_reels, task_id, vid_path, out_path): (task_id, vid_path.name)
            for task_id, vid_path, out_path in tasks
        }

        for future in tqdm(concurrent.futures.as_completed(future_to_task), total=len(tasks), desc="Cropping to Reels"):
            task_id, video_name = future_to_task[future]
            try:
                success = future.result()
                if success:
                    successful_crops += 1
                else:
                    failed_crops += 1
                    logger.warning(f"⚠️ Cropping task {task_id} failed for: {video_name}")
            except Exception as exc:
                failed_crops += 1
                logger.error(f"💥 Task {task_id} for '{video_name}' generated an exception: {exc}", exc_info=True)

    # --- Final summary ---
    logger.info(f"\n🏁 Finished Instagram Reels cropping:")
    logger.info(f"   ✅ Successful: {successful_crops}")
    logger.info(f"   ❌ Failed: {failed_crops}")
    logger.info(f"   📱 Reels saved in: {reels_output_dir}")
    logger.info("=" * 60)