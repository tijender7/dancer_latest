# run_topaz_gui_generated.py
import subprocess
import time
import os
from datetime import datetime

# ==============================================================================
#  CONFIGURATION
# ==============================================================================

# --- Paths ---
# NOTE: Using the ORIGINAL input file, not the previously generated output
input_path = r"H:\dancers_content\Run_20250414_070855\all_videos\250414\250414073229_001_video_swapped_00001.mp4"
topaz_dir = r"C:\Program Files\Topaz Labs LLC\Topaz Video AI"
model_dir = r"C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models" # Confirmed model location

# --- FFmpeg Executable ---
ffmpeg_exe = os.path.join(topaz_dir, "ffmpeg.exe")

# --- Output File ---
base_dir = os.path.dirname(input_path)
output_dir = os.path.join(base_dir, "topaz_outputs_script")
output_filename_base = os.path.splitext(os.path.basename(input_path))[0]
# New filename reflecting GUI generation approach
output_path = os.path.join(output_dir, f"{output_filename_base}_gui_generated_cli.mp4")

# ==============================================================================
#  PRE-RUN CHECKS (Same as before)
# ==============================================================================
print("-" * 60)
print(" Performing Pre-run Checks ".center(60, "-"))
print("-" * 60)
valid_setup = True
if not os.path.exists(input_path): print(f"❌ FATAL ERROR: Input video not found: {input_path}"); valid_setup = False
else: print(f"✅ Input video found: {input_path}")
if not os.path.exists(ffmpeg_exe): print(f"❌ FATAL ERROR: FFmpeg not found: {ffmpeg_exe}"); valid_setup = False
else: print(f"✅ FFmpeg executable found: {ffmpeg_exe}")
if not os.path.isdir(model_dir): print(f"⚠️ WARNING: Model directory not found: {model_dir}")
else: print(f"✅ Model directory check path: {model_dir}")
if not valid_setup: print("\nSetup errors found. Exiting."); exit(1)
print(f"[*] Output directory: {output_dir}"); os.makedirs(output_dir, exist_ok=True)
print(f"[*] Output file will be: {output_path}")
print("-" * 60)

# ==============================================================================
#  HELPER FUNCTION (Prints to Console - Same as before)
# ==============================================================================
def print_run_details(label, command_preview, start, end, stdout, stderr, returncode):
    print("-" * 60); print(f"--- Details for: {label} ---"); print(f"Timestamp: {datetime.now()}")
    print(f"Runtime: {round(end - start, 2)}s"); print(f"FFmpeg Exit Code: {returncode}")
    if returncode != 0 or not stderr:
        print("\n--- STDERR (Last 20 lines) ---")
        if stderr: print('\n'.join(stderr.strip().splitlines()[-20:]))
        else: print("[No STDERR output detected]")
    print("-" * 60)

def run_topaz_ffmpeg(label, command, output_file_path):
    print(f"\n🚀 Running Task: {label}")
    start = time.time(); env_vars = os.environ.copy(); env_vars["TVAI_MODEL_DIR"] = model_dir
    result = None
    try:
        result = subprocess.run( command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=topaz_dir, env=env_vars)
        end = time.time()
        success = (result.returncode == 0 and os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 1024)
        if success: print(f"✅ {label} finished successfully in {round(end - start, 2)}s.\n   Output: {output_file_path}")
        else:
            print(f"❌ {label} failed or produced an empty/invalid file.")
            print_run_details(label, command, start, end, result.stdout, result.stderr, result.returncode)
            if result.returncode != 0: print(f"   (FFmpeg exited with error code: {result.returncode})")
            if not os.path.exists(output_file_path): print(f"   (Output file was not created: {output_file_path})")
            elif os.path.exists(output_file_path) and os.path.getsize(output_file_path) <= 1024: print(f"   (Output file is too small/likely invalid: {output_file_path})")
    except FileNotFoundError: print(f"\n❌ FATAL ERROR: '{ffmpeg_exe}' not found."); print_run_details(label, command, start, time.time(), "", f"Python FileNotFoundError: {ffmpeg_exe}", -1)
    except Exception as e: end = time.time(); print(f"\n❌ PYTHON ERROR: {e}"); print_run_details(label, command, start, end, getattr(result, 'stdout', ""), f"Python Exception: {e}\n{getattr(result, 'stderr', '')}", getattr(result, 'returncode', -1))

# ==============================================================================
#  CONSTRUCT THE FFmpeg COMMAND (Based on GUI Ctrl+Shift+E)
# ==============================================================================

# --- Build the filter_complex string ---
# NOTE: Parameters derived from GUI command, mapped to variable names where possible
# Using f-string with line breaks for readability
filter_complex_chain = (
    "tvai_fi=model=chr-2:slowmo=1:rdt=0.01:fps=30:device=0:vram=1:instances=1," # Chronos V2 Fast, 30fps
    "tvai_up=model=prob-4:scale=2:preblur=-0.334523:noise=0.05:details=0.2:halo=0.0573913:blur=0.14:compression=0.535133:blend=0.2:device=0:vram=1:instances=1," # Proteus V4, 2x scale, detailed params
    "tvai_up=model=amq-13:scale=0:w=3840:h=2160:blend=0.2:device=0:vram=1:instances=1," # Artemis MQ V13, enhance at 4K
    "scale=w=3840:h=2160:flags=lanczos:threads=0:force_original_aspect_ratio=decrease," # FFmpeg scale to final 4K
    "pad=3840:2160:-1:-1:color=black" # Pad to 4K if needed
)

# --- Build the full command string ---
# Using the GUI's more detailed encoding options
command_to_run = (
    f'"{ffmpeg_exe}" -hide_banner -y ' # Added -y for overwrite, removed duplicate -hide_banner if present
    f'-i "{input_path}" '
    f'-sws_flags spline+accurate_rnd+full_chroma_int ' # GUI included scaling flags
    f'-filter_complex "{filter_complex_chain}" ' # Use filter_complex
    f'-c:v h264_nvenc -profile:v high -pix_fmt yuv420p -g 30 ' # Video codec options
    f'-preset p7 -tune hq -rc constqp -qp 18 -rc-lookahead 20 -spatial_aq 1 -aq-strength 15 ' # Detailed NVENC settings
    f'-b:v 0 ' # Bitrate 0 often used with constqp
    f'-an ' # No audio
    f'-map_metadata 0 -map_metadata:s:v 0:s:v ' # Map metadata
    f'-movflags frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr ' # MP4 flags
    f'-bf 0 ' # No B-frames (GUI choice)
    # f'-metadata "videoai=..." ' # Optional: Add descriptive metadata if desired
    f'"{output_path}"'
)

# ==============================================================================
#  EXECUTE THE COMMAND
# ==============================================================================
print("\n" + "=" * 60); print(" Starting Topaz Pipeline (GUI Generated Command) ".center(60, "=")); print("=" * 60)
print(f"Applying complex filter chain...")
# print(f"Full command preview:\n{command_to_run}") # Uncomment to see the exact command before running
print("-" * 60)

run_topaz_ffmpeg("GUI Generated Pipeline", command_to_run, output_path)

print("\n" + "=" * 60); print(" Script Finished ".center(60, "=")); print("=" * 60)
print(f"[*] Check console output above for status and errors.")
print(f"[*] If successful, output video is in: {output_dir}")
# ==============================================================================