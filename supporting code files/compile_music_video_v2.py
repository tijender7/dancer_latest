# compile_music_video_v3.py
import os
import subprocess
import random
import sys
import shutil
from pathlib import Path
from datetime import datetime
try:
    # Ensure moviepy is imported correctly
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
    # This specific import isn't directly used but good to keep for reference if needed later
    # from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
except ImportError:
    print("ERROR: moviepy library not found. Please install it: pip install moviepy")
    sys.exit(1)
try:
    from tqdm import tqdm
except ImportError:
    print("WARNING: tqdm library not found. Progress bars disabled. Install with: pip install tqdm")
    tqdm = lambda x, **kwargs: x # Dummy tqdm

# ==============================================================
# Configuration
# ==============================================================
RUNS_BASE_DIR_STR = r"H:\dancers_content"
MUSIC_FILE_PATH_STR = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\music.mp3"
UPSCALE_PARENT_FOLDER = "Upscaled_Topaz"
ffmpeg_exe = "ffmpeg"
ffprobe_exe = "ffprobe"
FINAL_VIDEO_BASENAME = f"Compiled_Music_Video_{datetime.now():%Y%m%d_%H%M%S}.mp4"
script_dir = Path(__file__).resolve().parent
temp_dir = script_dir / "temp_compiled_clips"
intermediate_codec_options = "-c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p -an"
# Using software encoding for final write for quality/compatibility by default
final_write_params = {"preset": "medium", "codec": "libx264", "audio_codec": "aac", "threads": 4, "logger": 'bar'}
# --- Allowed Effects List (v4 - Removed high contrast and problematic ones) ---
allowed_effects = [
    "curves=preset=vintage",
    "curves=preset=cross_process",
    # "sepia", # Removed (Filter not found)
    "hue=s=1.7", # Saturation Boost
    "hue=s=0.3", # Saturation Drain
    # "eq=contrast=1.5:brightness=-0.05", # Removed High Contrast
    "eq=saturation=1.3", # Simple Saturation Boost
    "eq=gamma=1.2", # Gamma Adjust (Brighter Mids)
    "vignette=angle=PI/5", # Dark Vignette (Simpler options)
    "vignette=mode=backward", # Light Vignette (Simpler options)
    "gblur=sigma=1.5", # Light Blur
    "gblur=sigma=5",   # Heavier Blur
    "unsharp=5:5:1.0", # Sharpen
    "hflip", # Horizontal Flip
    "noise=alls=10:allf=t+u", # Light Grain/Noise
    "scale=iw*1.05:ih*1.05,crop=iw/1.05:ih/1.05", # Slight zoom in crop
    "scale=iw*0.95:ih*0.95,pad=iw/0.95:ih/0.95:(ow-iw)/2:(oh-ih)/2", # Slight zoom out pad
    # "text_overlay": "...", # Removed (Font issues)
    "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0", # Channel Mixer Example
    "smartblur=lr=1.0:ls=0.5", # Smart Blur
    "format=pix_fmts=gray,hue=s=0", # Grayscale (keeping this one unless you specify otherwise)
]

# ==============================================================
# Helper Functions (Same as before)
# ==============================================================
def get_duration(filepath):
    command = [ ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(filepath) ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except FileNotFoundError: print(f"❌ FATAL ERROR: '{ffprobe_exe}' not found."); sys.exit(1)
    except Exception as e: print(f"❌ Error getting duration for {filepath.name}: {e}"); return None

def apply_ffmpeg_effect(input_path: Path, output_path: Path, filter_string: str):
    label = f"Effect '{filter_string[:30]}...'"
    command = [ ffmpeg_exe, "-y", "-i", str(input_path), "-vf", filter_string, *intermediate_codec_options.split(), str(output_path) ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            if output_path.exists() and output_path.stat().st_size > 1024: return True
            else: print(f"⚠️ {label} cmd OK, but output invalid: {output_path.name}\n   STDERR: {result.stderr.strip().splitlines()[-5:]}"); return False
        else: print(f"❌ {label} failed for {input_path.name}.\n   Code: {result.returncode}\n   STDERR: {result.stderr.strip().splitlines()[-15:]}"); return False
    except FileNotFoundError: print(f"❌ FATAL ERROR: '{ffmpeg_exe}' not found."); sys.exit(1)
    except Exception as e: print(f"❌ PYTHON ERROR during {label} for {input_path.name}: {e}"); return False

# ==============================================================
# Main Script Logic
# ==============================================================
if __name__ == "__main__":
    print("=" * 60); print(" Starting Music Video Compilation v3 ".center(60, "=")); print("=" * 60)

    runs_base_dir = Path(RUNS_BASE_DIR_STR)
    music_file_path = Path(MUSIC_FILE_PATH_STR)

    if not runs_base_dir.is_dir(): print(f"❌ ERROR: Runs base directory not found: {runs_base_dir}"); sys.exit(1)
    if not music_file_path.is_file(): print(f"❌ ERROR: Music file not found: {music_file_path}"); sys.exit(1)

    print(f"Searching for latest 'Run_*' folder in: {runs_base_dir}")
    try:
        run_folders = sorted( [d for d in runs_base_dir.iterdir() if d.is_dir() and d.name.startswith("Run_")], key=os.path.getmtime, reverse=True )
        if not run_folders: print(f"❌ ERROR: No 'Run_*' folders found in '{runs_base_dir}'."); sys.exit(1)
        latest_run_folder = run_folders[0]; print(f"Found latest run folder: {latest_run_folder}")
    except Exception as e: print(f"❌ ERROR finding latest run folder: {e}"); sys.exit(1)

    upscaled_parent_dir = latest_run_folder / UPSCALE_PARENT_FOLDER
    final_output_path = latest_run_folder / FINAL_VIDEO_BASENAME # Save in the root run folder

    if not upscaled_parent_dir.is_dir(): print(f"❌ ERROR: Upscaled parent folder '{UPSCALE_PARENT_FOLDER}' not found in '{latest_run_folder}'."); sys.exit(1)

    print(f"Searching for date subfolder inside: {upscaled_parent_dir}")
    try:
        date_folders = [d for d in upscaled_parent_dir.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 6]
        if not date_folders: print(f"❌ ERROR: No date subfolder found inside '{upscaled_parent_dir}'."); sys.exit(1)
        input_clips_dir = date_folders[0]; print(f"Found input clips source folder: {input_clips_dir}")
    except Exception as e: print(f"❌ ERROR accessing subfolders within '{upscaled_parent_dir}': {e}"); sys.exit(1)

    print(f"Music File: {music_file_path}")
    print(f"Final Video Output Path: {final_output_path}")
    print(f"Temporary files in: {temp_dir}")

    music_duration = get_duration(music_file_path)
    if music_duration is None: print(f"❌ ERROR: Could not determine music duration."); sys.exit(1)
    print(f"\nMusic Duration: {music_duration:.2f} seconds")

    print(f"\nFinding input video clips in: {input_clips_dir}")
    input_clips = sorted([p for p in input_clips_dir.glob("*.mp4") if p.is_file()])
    if not input_clips: print(f"❌ ERROR: No .mp4 video clips found in {input_clips_dir}"); sys.exit(1)
    print(f"Found {len(input_clips)} clips.")
    random.shuffle(input_clips)

    if temp_dir.exists(): print(f"\nCleaning up previous temp directory: {temp_dir}"); shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True); print(f"Created temp directory: {temp_dir}")

    print("\nApplying random effects to clips...")
    processed_clip_paths = []; total_processed_duration = 0.0; clips_needed = True
    clip_pool = list(input_clips)
    progress_bar = tqdm(total=int(music_duration), desc="Processing Clips", unit="s") if 'tqdm' in sys.modules else None

    while clips_needed:
        if not clip_pool: print("Looping clip pool..."); clip_pool = list(input_clips); random.shuffle(clip_pool)
        current_clip_path = clip_pool.pop(0); clip_duration = get_duration(current_clip_path)
        if clip_duration is None: print(f"⚠️ Skipping {current_clip_path.name}, no duration."); continue

        chosen_effect_filter = random.choice(allowed_effects)
        temp_output_filename = f"temp_{len(processed_clip_paths):04d}_{current_clip_path.stem}{current_clip_path.suffix}"
        temp_output_path = temp_dir / temp_output_filename

        if apply_ffmpeg_effect(current_clip_path, temp_output_path, chosen_effect_filter):
            processed_clip_paths.append(temp_output_path)
            duration_to_add = min(clip_duration, music_duration - total_processed_duration)
            if progress_bar:
                update_amount = duration_to_add if (total_processed_duration + duration_to_add) <= music_duration else (music_duration - total_processed_duration)
                if update_amount > 0: progress_bar.update(update_amount)
            total_processed_duration += duration_to_add
            if total_processed_duration >= music_duration: clips_needed = False; print("\nTarget duration reached.")
        else: print(f"⚠️ Failed effect on {current_clip_path.name}. Skipping.")
        if len(processed_clip_paths) > len(input_clips) * 3: print("⚠️ WARNING: Clip loop limit hit. Stopping."); clips_needed = False

    if progress_bar: progress_bar.close()

    if not processed_clip_paths: print("❌ ERROR: No clips processed. Exiting."); sys.exit(1)
    print(f"\nSuccessfully processed {len(processed_clip_paths)} clip segments.")

    # --- MoviePy Processing Block ---
    print("\nProcessing with MoviePy (Concatenate, Add Audio, Trim)...")
    # Initialize variables outside try block
    final_clips_list = []
    music_clip = None
    final_video_concat = None
    final_video_with_audio = None
    final_video_written = False # Flag to track if write succeeded

    try: # <<< START OF MOVIEPY TRY BLOCK
        print("Loading processed clips...")
        for temp_path in tqdm(processed_clip_paths, desc="Loading Clips"):
            try:
                clip = VideoFileClip(str(temp_path))
                final_clips_list.append(clip)
            except Exception as e:
                print(f"⚠️ Warning: Skipping {temp_path.name}, load failed: {e}")

        if not final_clips_list:
            print("❌ ERROR: Failed to load any processed clips. Cannot continue.")
            # No need to exit here, finally block will handle cleanup
        else:
            print("Concatenating clips...")
            # Ensure compose method uses temp dir for intermediate files if needed (less likely needed now)
            final_video_concat = concatenate_videoclips(final_clips_list, method="compose")
            print(f"Concatenated duration: {final_video_concat.duration:.2f}s")

            print("Adding music...")
            music_clip = AudioFileClip(str(music_file_path))
            # Set audio first
            final_video_with_audio = final_video_concat.set_audio(music_clip)

            # Trim to music duration if necessary
            if final_video_with_audio.duration > music_duration:
                print(f"Trimming final video from {final_video_with_audio.duration:.2f}s to {music_duration:.2f}s")
                # It's safer to assign the result of subclip back to the variable
                final_video_with_audio = final_video_with_audio.subclip(0, music_duration)
            else:
                 print("Video duration <= music duration. No trim needed.")
            print(f"Final duration set to: {final_video_with_audio.duration:.2f}s")


            print(f"\nWriting final video: {final_output_path}...")
            # Ensure the variable holding the final clip is used for writing
            final_video_with_audio.write_videofile(str(final_output_path), **final_write_params)
            final_video_written = True # Set flag on success
            print(f"\n✅ Final video saved!")

    except Exception as e: # <<< CORRESPONDING EXCEPT BLOCK
        print(f"❌ ERROR during MoviePy processing: {e}")
        # Log the exception for debugging
        import traceback
        traceback.print_exc()

    finally: # <<< CORRESPONDING FINALLY BLOCK (Correctly Indented)
        # --- Close & Cleanup ---
        print("\nClosing clips & cleaning up...")

        print("Closing loaded video clips...")
        for clip in final_clips_list: # Close clips from the list
            try:
                clip.close()
            except Exception: # Ignore errors on close
                pass

        if music_clip: # Check if music_clip was assigned
            print("Closing music clip...")
            try:
                music_clip.close()
            except Exception:
                 pass

        # Clean up temporary directory
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                print(f"Removed temp dir: {temp_dir}")
            except Exception as e:
                print(f"⚠️ Error removing temp dir {temp_dir}: {e}")
        else:
            print("Temporary directory already removed or not created.")

        # Final status message based on whether the video was written
        print("\n" + "=" * 60)
        if final_video_written:
            print(" Music Video Compilation Finished Successfully ".center(60, "="))
        else:
            print(" Music Video Compilation Finished with Errors ".center(60, "="))
            print("   Final video may not have been saved correctly.")
        print("=" * 60)