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
COMFYUI_OUTPUT_DIR_BASE = Path(r"H:/dancers_content")  # Base directory containing Run_* folders
VIDEO_PARENT_SUBFOLDER = "all_videos"
COMPILED_SUBFOLDER = "compiled"
UPSCALE_SUBFOLDER = "4k_upscaled"
UPSCALED_COMPILED_SUBFOLDER = "compiled"

TOPAZ_INSTALL_DIR = Path(r"C:\Program Files\Topaz Labs LLC\Topaz Video AI")
TOPAZ_MODEL_DIR = Path(r"C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models")
TOPAZ_FFMPEG_EXE = TOPAZ_INSTALL_DIR / "ffmpeg.exe"
TOPAZ_TIMEOUT = 7200  # 2 hours per video

TARGET_BITRATE_KBPS = "15000k"
MAX_BITRATE_KBPS = "25000k"
AUDIO_BITRATE_KBPS = "192k"

TOPAZ_FILTER_COMPLEX = (
    "tvai_fi=model=chr-2:slowmo=1:rdt=0.01:fps=30:device=0:vram=1:instances=1,"
    "tvai_up=model=prob-4:scale=2:preblur=-0.334523:noise=0.05:details=0.2:halo=0.0573913:blur=0.14:compression=0.535133:blend=0.2:device=0:vram=1:instances=1,"
    "tvai_up=model=amq-13:scale=0:w=3840:h=2160:blend=0.2:device=0:vram=1:instances=1,"
    "scale=w=3840:h=2160:flags=lanczos:threads=0:force_original_aspect_ratio=decrease,"
    "pad=3840:2160:-1:-1:color=black"
)

TOPAZ_ENCODER_SETTINGS = (
    f"-c:v h264_nvenc -profile:v high -pix_fmt yuv420p -g 30 "
    f"-preset p6 -tune hq "
    f"-rc vbr -cq 22 "
    f"-b:v {TARGET_BITRATE_KBPS} -maxrate {MAX_BITRATE_KBPS} -bufsize {int(float(MAX_BITRATE_KBPS[:-1])*1.5)}k "
    f"-rc-lookahead 20 -spatial_aq 1 -aq-strength 15 "
    f"-c:a aac -b:a {AUDIO_BITRATE_KBPS} -ac 2 "
    f"-map_metadata 0 -map_metadata:s:v 0:s:v "
    f"-movflags frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr -bf 2"
)

MAX_CONCURRENT_UPSCALES = 1

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
    label = f"4K Upscale Task {task_id}"
    logger.info(f"  ⬆️ Starting {label}: '{input_video_path.name}' -> '{output_video_path.name}'")
    start = time.time()
    env_vars = os.environ.copy()
    env_vars["TVAI_MODEL_DIR"] = str(TOPAZ_MODEL_DIR.resolve())
    env_vars["CUDA_VISIBLE_DEVICES"] = "0"

    command = (
        f'"{str(TOPAZ_FFMPEG_EXE)}" -y -hide_banner -hwaccel auto -i "{str(input_video_path)}" '
        f'-sws_flags spline+accurate_rnd+full_chroma_int -filter_complex "{TOPAZ_FILTER_COMPLEX}" '
        f'{TOPAZ_ENCODER_SETTINGS} "{str(output_video_path)}"'
    )

    result = None
    stderr_snippet = "[No STDERR captured]"

    try:
        logger.debug(f"    Executing command for {label}: {command}")
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, encoding='utf-8',
            errors='replace', cwd=str(TOPAZ_INSTALL_DIR), env=env_vars, timeout=TOPAZ_TIMEOUT
        )
        end = time.time()
        success = (result.returncode == 0 and output_video_path.exists() and output_video_path.stat().st_size > 10240)

        if result and result.stderr:
            stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-20:])

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
            if output_video_path.exists() and output_video_path.stat().st_size <= 10240:
                try:
                    output_video_path.unlink()
                    logger.warning(f"       Removed small/invalid output file: {output_video_path.name}")
                except Exception as rm_err:
                    logger.error(f"       Failed to remove small/invalid output file: {rm_err}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"    ❌ {label} timed out after {TOPAZ_TIMEOUT} seconds for {input_video_path.name}.")
        if output_video_path.exists():
            try:
                output_video_path.unlink()
                logger.warning(f"       Removed potentially incomplete output file due to timeout: {output_video_path.name}")
            except Exception as rm_err:
                logger.error(f"       Failed to remove timed-out output file: {rm_err}")
        return False
    except Exception as e:
        logger.error(f"    ❌ Python error during {label} for {input_video_path.name}: {e}", exc_info=True)
        if result and result.stderr:
            stderr_snippet = '\n'.join(result.stderr.strip().splitlines()[-20:])
            logger.error(f"       STDERR Snippet:\n{stderr_snippet}")
        return False

# ==============================================================================
#  Main Script Logic
# ==============================================================================
if __name__ == "__main__":
    logger.info("=" * 50); logger.info(f"Starting Parallel 4K Upscaling Script: {datetime.now()}"); logger.info("=" * 50)

    if not COMFYUI_OUTPUT_DIR_BASE.is_dir():
        logger.critical(f"CRITICAL: Base ComfyUI output directory not found: {COMFYUI_OUTPUT_DIR_BASE}. Exiting.")
        sys.exit(1)
    if not TOPAZ_FFMPEG_EXE.is_file():
        logger.critical(f"CRITICAL: Topaz FFmpeg not found: {TOPAZ_FFMPEG_EXE}. Exiting.")
        sys.exit(1)
    if not TOPAZ_MODEL_DIR.is_dir():
        logger.warning(f"WARNING: Topaz Model Directory not found: {TOPAZ_MODEL_DIR}.")

    # --- Find the latest 'Run_*' folder ---
    try:
        run_folders = sorted(
            [d for d in COMFYUI_OUTPUT_DIR_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
            key=lambda x: x.stat().st_mtime, reverse=True
        )
        if not run_folders:
            logger.critical(f"CRITICAL: No 'Run_*' folders found in '{COMFYUI_OUTPUT_DIR_BASE}'. Exiting.")
            sys.exit(1)
        latest_run_folder = run_folders[0]
        logger.info(f"Found latest run folder: {latest_run_folder}")
    except Exception as e:
        logger.critical(f"CRITICAL: Error finding latest run folder: {e}", exc_info=True)
        sys.exit(1)

    # --- Locate the compiled folder containing videos ---
    video_source_compiled_dir = latest_run_folder / VIDEO_PARENT_SUBFOLDER / COMPILED_SUBFOLDER
    upscaled_output_parent_dir = latest_run_folder / UPSCALE_SUBFOLDER / UPSCALED_COMPILED_SUBFOLDER
    upscaled_output_parent_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"4K upscaled videos will be saved to: {upscaled_output_parent_dir}")

    if not video_source_compiled_dir.is_dir():
        logger.error(f"Compiled video source folder not found: {video_source_compiled_dir}. Nothing to process. Exiting.")
        sys.exit(0)

    # --- Find videos to process ---
    video_files = sorted(list(video_source_compiled_dir.glob("*.mp4")))
    if not video_files:
        logger.warning(f"No video files (*.mp4) found in '{video_source_compiled_dir}'. Exiting.")
        sys.exit(0)
    logger.info(f"Found {len(video_files)} MP4 videos to process in 'compiled'.")

    # --- Prepare tasks for parallel execution ---
    tasks = []
    for i, video_path in enumerate(video_files):
        base_name = video_path.stem
        upscaled_filename = f"{base_name}_upscaled{video_path.suffix}"
        upscaled_output_path = upscaled_output_parent_dir / upscaled_filename
        task_id = f"{i+1:03d}"

        if upscaled_output_path.exists() and upscaled_output_path.stat().st_size > 10240:
            logger.info(f"  ⏭️ Skipping Task {task_id}: Output file already exists and seems valid: '{upscaled_output_path.name}'")
            continue

        tasks.append((task_id, video_path, upscaled_output_path))

    if not tasks:
        logger.info("All videos seem to be already processed or no videos found. Exiting.")
        sys.exit(0)

    logger.info(f"\n--- Starting Topaz 4K Video Upscaling from compiled ({len(tasks)} tasks, {MAX_CONCURRENT_UPSCALES} parallel) ---")
    successful_upscales = 0
    failed_upscales = 0

    # --- Execute tasks in parallel ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPSCALES) as executor:
        future_to_task = {
            executor.submit(upscale_video_topaz, task_id, vid_path, out_path): (task_id, vid_path.name)
            for task_id, vid_path, out_path in tasks
        }

        for future in tqdm(concurrent.futures.as_completed(future_to_task), total=len(tasks), desc="Upscaling 4K Videos"):
            task_id, video_name = future_to_task[future]
            try:
                success = future.result()
                if success:
                    successful_upscales += 1
                else:
                    failed_upscales += 1
                    logger.warning(f"Upscaling task {task_id} reported failure for: {video_name}")
            except Exception as exc:
                failed_upscales += 1
                logger.error(f"Task {task_id} for '{video_name}' generated an unexpected exception: {exc}", exc_info=True)

    logger.info(f"\n--- Finished 4K Upscaling ({successful_upscales} successful, {failed_upscales} failed) ---")
    logger.info(f"Upscaled 4K videos saved in: {upscaled_output_parent_dir}")
    logger.info("=" * 50)
