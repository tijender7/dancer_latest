import os
import subprocess
import time
import logging
import sys
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

# ==============================================================================
#  CONFIGURATION
# ==============================================================================
BASE_DIR = Path(r"H:/dancers_content")
VIDEO_PARENT = "all_videos"
INPUT_SUB = "music_video_compiled"
OUTPUT_SUB = "upscaled"

TOPAZ_DIR = Path(r"C:\Program Files\Topaz Labs LLC\Topaz Video AI")
MODEL_DIR = Path(r"C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models")
FFMPEG = TOPAZ_DIR / "ffmpeg.exe"
FFPROBE = TOPAZ_DIR / "ffprobe.exe"
TIMEOUT = 7200  # seconds

# bitrate + filter settings unchanged...
TARGET_K = "15000k"; MAX_K = "25000k"; AUDIO_K = "192k"
FILTER = (
    "tvai_fi=model=chr-2:slowmo=1:rdt=0.01:fps=30:device=0:vram=1:instances=1,"
    "tvai_up=model=prob-4:scale=2:preblur=-0.334523:noise=0.05:details=0.2:"
    "halo=0.0573913:blur=0.14:compression=0.535133:blend=0.2:device=0:vram=1:instances=1,"
    "tvai_up=model=amq-13:scale=0:w=3840:h=2160:blend=0.2:device=0:vram=1:instances=1,"
    "scale=w=3840:h=2160:flags=lanczos:threads=0"
    ":force_original_aspect_ratio=decrease,pad=3840:2160:-1:-1:color=black"
)
ENCODE = (
    f"-c:v h264_nvenc -profile:v high -pix_fmt yuv420p -g 30 -preset p6 -tune hq "
    f"-rc vbr -cq 22 -b:v {TARGET_K} -maxrate {MAX_K} "
    f"-bufsize {int(float(MAX_K[:-1])*1.5)}k -rc-lookahead 20 -spatial_aq 1 -aq-strength 15 "
    f"-c:a aac -b:a {AUDIO_K} -ac 2 -map_metadata 0 -map_metadata:s:v 0:s:v "
    f"-movflags frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr -bf 2"
)

# ==============================================================================
#  LOGGING
# ==============================================================================
logdir = Path(__file__).parent / "logs"
logdir.mkdir(exist_ok=True)
fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh = logging.FileHandler(logdir / f"upscale_{datetime.now():%Y%m%d_%H%M%S}.log", encoding='utf-8')
fh.setFormatter(fmt)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(); logger.setLevel(logging.INFO)
logger.handlers.clear(); logger.addHandler(fh); logger.addHandler(ch)


def get_duration(path: Path) -> float:
    """Use ffprobe to get video duration in seconds."""
    cmd = [
        str(FFPROBE), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except:
        return 0.0


def upscale_with_tqdm(src: Path, dst: Path) -> bool:
    dur = get_duration(src)
    bar = tqdm(total=dur, unit="s", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]")
    cmd = [
        str(FFMPEG), "-y", "-hide_banner",
        "-hwaccel", "auto",
        "-i", str(src),
        "-sws_flags", "spline+accurate_rnd+full_chroma_int",
        "-filter_complex", FILTER,
        *ENCODE.split(),
        "-nostats", "-progress", "pipe:1",
        str(dst)
    ]
    env = os.environ.copy()
    env["TVAI_MODEL_DIR"] = str(MODEL_DIR)
    env["CUDA_VISIBLE_DEVICES"] = "0"

    logger.info(f"Upscaling → {dst.name}")
    start = time.time()
    proc = subprocess.Popen(cmd, cwd=TOPAZ_DIR, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, bufsize=1)

    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                val = line.split("=", 1)[1]
                if val.isdigit():
                    sec = int(val) / 1_000_000
                    bar.update(sec - bar.n)
            elif line.startswith("progress=") and line.endswith("end"):
                break
        ret = proc.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ Timed out after {TIMEOUT}s")
        proc.kill()
        bar.close()
        return False
    except KeyboardInterrupt:
        logger.warning("🔌 Interrupted by user")
        proc.kill()
        bar.close()
        return False

    bar.close()
    elapsed = time.time() - start
    if ret == 0 and dst.exists() and dst.stat().st_size > 10_240:
        mb = dst.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Done in {elapsed:.1f}s — {mb:.1f}MB")
        return True
    else:
        logger.error(f"❌ Failed (exit {ret})")
        return False


if __name__ == "__main__":
    logger.info("=== Upscale Latest Music Video (tqdm) ===")

    # find latest run
    runs = sorted(
        [d for d in BASE_DIR.iterdir() if d.is_dir() and d.name.startswith("Run_") and "_music_images" in d.name],
        key=lambda d: d.stat().st_mtime, reverse=True
    )
    if not runs:
        logger.critical("No runs found"); sys.exit(1)
    latest = runs[0]; logger.info(f"Using: {latest.name}")

    inp = latest / VIDEO_PARENT / INPUT_SUB
    vids = list(inp.glob("*.mp4"))
    if not vids:
        logger.critical("No .mp4"); sys.exit(1)
    src = max(vids, key=lambda f: f.stat().st_mtime)
    logger.info(f"Selected: {src.name}")

    out = latest / VIDEO_PARENT / OUTPUT_SUB
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{src.stem}_upscaled{src.suffix}"
    logger.info(f"Output: {dst}")

    ok = upscale_with_tqdm(src, dst)
    sys.exit(0 if ok else 1)
