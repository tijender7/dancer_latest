# apply_ffmpeg_effects_v2.py
import os
import subprocess
from pathlib import Path
import time
import sys # Added for sys.exit

# ==============================================================
# Configuration
# ==============================================================
input_video_path_str = r"H:\dancers_content\Run_20250414_070855\Upscaled_Topaz\250414\250414094407_011_video_swapped_00001_upscaled.mp4"
ffmpeg_exe = "ffmpeg" # Assumes ffmpeg is in PATH

# --- Use Software Encoding for better filter compatibility ---
output_codec_options = "-c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p"

# --- Effects to Apply ---
effects_to_apply = {
    # Color & Tone
    "vintage": "curves=preset=vintage",
    "crossprocess": "curves=preset=cross_process",
    "grayscale": "format=pix_fmts=gray",
    "sepia": "sepia",
    "saturation_boost": "hue=s=1.7",
    "saturation_drain": "hue=s=0.3",
    "contrast_high": "eq=contrast=1.5:brightness=-0.05",
    "vignette_dark": "vignette=angle=PI/5:d=1",
    "vignette_light": "vignette=mode=backward:a=PI/6",
    # Stylization & Distortion
    "edge_canny": "edgedetect=mode=canny:low=0.1:high=0.3",
    "pixelize_med": "scale=iw/12:-1,scale=iw*12:ih*12:flags=neighbor",
    "noise_grain": "noise=alls=15:allf=t+u",
    "hflip": "hflip",
    # Blur & Sharpen
    "blur_motion_like": "gblur=sigma=3", # Simple blur often gives motion feel
    "sharpen_strong": "unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=1.8",
    # Time (Example - Run these carefully, check output duration)
    # "speed_2x": "setpts=0.5*PTS", # NOTE: Audio will be desynced without -filter_complex and atempo
    # "speed_halfx": "setpts=2.0*PTS", # NOTE: Audio will be desynced
    # Overlays
    "text_overlay": "drawtext=text='Music Video FX':fontcolor=white@0.8:fontsize=50:x=(w-text_w)/2:y=h-th-50:box=1:boxcolor=black@0.5:boxborderw=5"
    # Add frei0r examples if available
    # "glitch_frei0r": "frei0r=glitch0r:0.1",
    # "oldfilm_frei0r": "frei0r=oldfilm"
}
# ==============================================================
# Script Logic (Mostly same as before)
# ==============================================================
def run_ffmpeg_effect(input_path: Path, effect_name: str, filter_string: str, output_dir: Path):
    if not input_path.is_file(): print(f"❌ ERROR: Input file not found: {input_path}"); return False
    output_filename = f"{input_path.stem}_{effect_name}{input_path.suffix}"
    output_path = output_dir / output_filename
    label = f"Effect '{effect_name}'"
    command = [ ffmpeg_exe, "-y", "-i", str(input_path), "-vf", filter_string, *output_codec_options.split(), str(output_path) ]
    print("-" * 60); print(f"🚀 Applying {label}..."); print(f"   Output: {output_path}"); start = time.time(); success = False
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        end = time.time()
        if result.returncode == 0:
            if output_path.exists() and output_path.stat().st_size > 1024: print(f"✅ {label} completed successfully in {round(end - start, 2)}s."); success = True
            else: print(f"⚠️ {label} command ran (Code 0), but output file is missing or too small.")
        else: print(f"❌ {label} failed."); print(f"   FFmpeg Exit Code: {result.returncode}")
        if not success or result.returncode != 0:
             print("\n--- FFmpeg STDERR (Last 20 lines) ---")
             stderr_lines = result.stderr.strip().splitlines(); print('\n'.join(stderr_lines[-20:])); print("-" * 35)
    except FileNotFoundError: print(f"\n❌ FATAL ERROR: '{ffmpeg_exe}' not found."); return False
    except Exception as e: print(f"\n❌ PYTHON ERROR during {label}: {e}"); return False
    print("-" * 60)
    return success

# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 60); print(" Starting FFmpeg Effect Application v2 ".center(60, "=")); print("=" * 60)
    input_file = Path(input_video_path_str); output_directory = input_file.parent
    print(f"Input Video: {input_file}"); print(f"Output Directory: {output_directory}")
    if not input_file.is_file(): print(f"\n❌ Input video file does not exist. Exiting."); sys.exit(1)
    output_directory.mkdir(parents=True, exist_ok=True)
    total_effects = len(effects_to_apply); successful_effects = 0; failed_effects = []
    for name, vf_string in effects_to_apply.items():
        if not run_ffmpeg_effect(input_file, name, vf_string, output_directory): failed_effects.append(name)
        else: successful_effects += 1
    print("\n" + "=" * 60); print(" Processing Summary ".center(60, "=")); print("=" * 60)
    print(f"Total Effects Attempted: {total_effects}"); print(f"Successful: {successful_effects}"); print(f"Failed: {len(failed_effects)}")
    if failed_effects: print(f"Failed Effects: {', '.join(failed_effects)}")
    print(f"\nOutput files are located in: {output_directory}"); print("=" * 60)