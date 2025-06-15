import os
import glob
import librosa
import numpy as np
import random
from datetime import datetime
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    vfx
)
from tqdm import tqdm

# --- Configuration ---

# 1. Base directory for "Run_YYYYMMDD_HHMMSS" folders:
BASE_DANCERS_DIR = r"H:\dancers_content"
RUN_PREFIX = "Run_"

# 2. Audio file path:
AUDIO_FILE_PATH = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\music.mp3"

# 3. How long each video segment (from original source, before speed-up) should be, in seconds:
TARGET_CLIP_DURATION = 5.0

# 4. Speed Variation Configuration
ENABLE_DYNAMIC_SPEED = True
BASE_VIDEO_SPEED_FACTOR = 1.5   # Base speed for segments
# Beat interval durations (in seconds) to categorize speed changes
FAST_BEAT_THRESHOLD = 0.4       # Segments shorter than this are "fast"
SLOW_BEAT_THRESHOLD = 0.8       # Segments longer than this are "slow"
# Speed multipliers relative to BASE_VIDEO_SPEED_FACTOR
FAST_BEAT_SPEED_MULTIPLIER = 1.25 # Speed up fast segments more
NORMAL_BEAT_SPEED_MULTIPLIER = 1.0  # Default for medium-length segments
SLOW_BEAT_SPEED_MULTIPLIER = 0.8    # Speed up slow segments less (or normal if desired)
MIN_EFFECTIVE_SPEED = 0.75          # Minimum allowed speed factor after dynamic adjustment
MAX_EFFECTIVE_SPEED = 3.0           # Maximum allowed speed factor

# 5. Subsample beats (1 means use every beat):
USE_EVERY_NTH_BEAT = 1

# 6. Visual Enhancements Configuration
APPLY_RANDOM_EFFECTS = True
EFFECT_PROBABILITY = 0.35
CROSSFADE_DURATION = 0.15
SHUFFLE_VIDEO_FILES = True # Shuffles the initial list of video files

# 7. Output Video Configuration
OUTPUT_FPS = 24
OUTPUT_PRESET = "medium"
OUTPUT_BITRATE = "5000k"

# --- Helper Functions ---

def find_latest_run_folder(base_dir, prefix):
    all_entries = os.listdir(base_dir)
    run_folders = []
    for entry in all_entries:
        full_path = os.path.join(base_dir, entry)
        if os.path.isdir(full_path) and entry.startswith(prefix):
            run_folders.append(full_path)
    if not run_folders:
        raise FileNotFoundError(f"No folders starting with '{prefix}' found under {base_dir}")
    return max(run_folders, key=lambda p: os.path.getmtime(p))

def find_video_clips_folder(latest_run_folder_path):
    all_videos_dir = os.path.join(latest_run_folder_path, "all_videos")
    if not os.path.isdir(all_videos_dir):
        raise FileNotFoundError(f"'all_videos' not found in {latest_run_folder_path}")
    subdirs = [
        os.path.join(all_videos_dir, name)
        for name in os.listdir(all_videos_dir)
        if os.path.isdir(os.path.join(all_videos_dir, name))
    ]
    if not subdirs:
        raise FileNotFoundError(f"No subfolder found under {all_videos_dir} to contain videos.")
    excluded_subfolder_names = ["compiled", "compiled_beatsync", "compiled_beatsync_ref", "1080p_upscaled"]
    valid_source_subdirs = [sd for sd in subdirs if os.path.basename(sd) not in excluded_subfolder_names]
    if not valid_source_subdirs:
        raise FileNotFoundError(
            f"No valid source subfolder found under {all_videos_dir}. "
            f"Checked: {subdirs}, Excluded known output names: {excluded_subfolder_names}. "
            "Ensure source videos are in a dedicated subfolder not named like an output folder."
        )
    if len(valid_source_subdirs) == 1: return valid_source_subdirs[0]
    else: return max(valid_source_subdirs, key=lambda p: os.path.getmtime(p))

def get_video_files(folder_path):
    extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm")
    files = []
    for ext in extensions: files.extend(glob.glob(os.path.join(folder_path, ext)))
    if not files: raise ValueError(f"No video files found in {folder_path} with extensions {extensions}")
    files.sort()
    if SHUFFLE_VIDEO_FILES: random.shuffle(files); print("Shuffled video file order.")
    return files

def detect_beats(audio_path, tightness_param=100):
    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path)
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)
    actual_tempo_for_print = 0.0
    if isinstance(tempo, np.ndarray):
        if tempo.size == 1: actual_tempo_for_print = tempo.item()
        elif tempo.size > 0: actual_tempo_for_print = tempo[0]; print(f"Info: Multi-tempo {tempo}, using first.")
        else: print("Info: Librosa empty tempo array.")
    elif isinstance(tempo, (int, float)): actual_tempo_for_print = tempo
    else: print(f"Info: Non-numeric tempo: {tempo} type: {type(tempo)}.")
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"Detected {len(beat_times)} beats. Tempo: {actual_tempo_for_print:.2f} BPM")
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0); print("Adjusted beat list to include time 0.0")
    return beat_times

def apply_random_vfx(clip):
    effects_pool = [
        {"name": "mirror_x", "func": lambda c: c.fx(vfx.mirror_x)},
        {"name": "blackwhite", "func": lambda c: c.fx(vfx.blackwhite, RGB=[1,1,1], preserve_luminosity=True)},
        {"name": "lum_contrast_inc", "func": lambda c: c.fx(vfx.lum_contrast, lum=0, contrast=0.2)},
        {"name": "gamma_brighten", "func": lambda c: c.fx(vfx.gamma_corr, gamma=1.2)},
    ]
    if not effects_pool: print("Warning: No effects in effects_pool."); return clip
    chosen_effect_dict = random.choice(effects_pool)
    return chosen_effect_dict["func"](clip)

# --- Main Logic ---
if __name__ == "__main__":
    loaded_source_clips = {}
    OUTPUT_VIDEO_PATH = ""
    TARGET_COMPILED_DIR_FOR_UPSCALER = ""

    try:
        latest_run_folder_path = find_latest_run_folder(BASE_DANCERS_DIR, RUN_PREFIX)
        print(f"👉 Latest run folder detected: {latest_run_folder_path}")
        VIDEO_CLIPS_FOLDER = find_video_clips_folder(latest_run_folder_path)
        print(f"👉 Video clips source folder: {VIDEO_CLIPS_FOLDER}")

        ALL_VIDEOS_CONTAINER_DIR = os.path.join(latest_run_folder_path, "all_videos")
        TARGET_COMPILED_DIR_FOR_UPSCALER = os.path.join(ALL_VIDEOS_CONTAINER_DIR, "compiled")
        if not os.path.exists(TARGET_COMPILED_DIR_FOR_UPSCALER):
            os.makedirs(TARGET_COMPILED_DIR_FOR_UPSCALER, exist_ok=True)
            print(f"Created target compiled directory: {TARGET_COMPILED_DIR_FOR_UPSCALER}")
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder_basename = os.path.basename(latest_run_folder_path).replace(RUN_PREFIX, "")
        output_filename = f"beatsync_{run_folder_basename}_{timestamp_str}.mp4"
        OUTPUT_VIDEO_PATH = os.path.join(TARGET_COMPILED_DIR_FOR_UPSCALER, output_filename)
        print(f"✅ Beat-synced video will be saved to: {OUTPUT_VIDEO_PATH}\n")

        if not os.path.exists(AUDIO_FILE_PATH): raise FileNotFoundError(f"Audio file not found: {AUDIO_FILE_PATH}")
        if not os.path.isdir(VIDEO_CLIPS_FOLDER): raise FileNotFoundError(f"Video clips folder not found: {VIDEO_CLIPS_FOLDER}")

        beat_times = detect_beats(AUDIO_FILE_PATH)
        if USE_EVERY_NTH_BEAT > 1:
            beat_times = beat_times[::USE_EVERY_NTH_BEAT]
            print(f"Using every {USE_EVERY_NTH_BEAT}th beat → {len(beat_times)} beats selected.")
        if len(beat_times) < 2: raise ValueError("Not enough beats detected.")

        video_file_paths = get_video_files(VIDEO_CLIPS_FOLDER)
        print(f"Found {len(video_file_paths)} video clips for processing.")
        if not video_file_paths: raise ValueError("No video files available.")

        video_segments = []
        clip_selector_idx = 0
        print("Preparing video segments...")
        for i in tqdm(range(len(beat_times)), desc="Processing Beats"):
            beat_start_time = beat_times[i]
            if i < len(beat_times) - 1: beat_end_time = beat_times[i + 1]
            else:
                with AudioFileClip(AUDIO_FILE_PATH) as temp_audio: beat_end_time = temp_audio.duration
                if beat_end_time <= beat_start_time: beat_end_time = beat_start_time + (TARGET_CLIP_DURATION / BASE_VIDEO_SPEED_FACTOR) / 2
            
            segment_duration_on_timeline = beat_end_time - beat_start_time
            if segment_duration_on_timeline <= 0.01: continue

            # --- Dynamic Speed Calculation ---
            current_speed_factor = BASE_VIDEO_SPEED_FACTOR 
            if ENABLE_DYNAMIC_SPEED:
                if segment_duration_on_timeline <= FAST_BEAT_THRESHOLD:
                    current_speed_factor = BASE_VIDEO_SPEED_FACTOR * FAST_BEAT_SPEED_MULTIPLIER
                elif segment_duration_on_timeline >= SLOW_BEAT_THRESHOLD:
                    current_speed_factor = BASE_VIDEO_SPEED_FACTOR * SLOW_BEAT_SPEED_MULTIPLIER
                # else: it remains BASE_VIDEO_SPEED_FACTOR * NORMAL_BEAT_SPEED_MULTIPLIER (which is * 1.0)
                
                current_speed_factor = max(MIN_EFFECTIVE_SPEED, min(current_speed_factor, MAX_EFFECTIVE_SPEED))
                if abs(current_speed_factor - BASE_VIDEO_SPEED_FACTOR) > 0.01 : # Only print if changed
                     # print(f" Beat {i+1} ({segment_duration_on_timeline:.2f}s) -> DynSpeed: {current_speed_factor:.2f}x") # DEBUG
                     pass
            # --- End Dynamic Speed ---

            source_video_path = video_file_paths[clip_selector_idx % len(video_file_paths)]
            processed_segment_for_timeline = None
            try:
                if source_video_path not in loaded_source_clips:
                    loaded_source_clips[source_video_path] = VideoFileClip(source_video_path, audio=False, verbose=False)
                source_clip_instance = loaded_source_clips[source_video_path]

                duration_to_take_from_original = min(source_clip_instance.duration, TARGET_CLIP_DURATION)
                if duration_to_take_from_original < 0.1:
                    clip_selector_idx += 1; continue

                segment_material = source_clip_instance.subclip(0, duration_to_take_from_original)
                sped_up_segment = segment_material.fx(vfx.speedx, current_speed_factor) # USE DYNAMIC SPEED

                if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
                    try: sped_up_segment = apply_random_vfx(sped_up_segment)
                    except Exception as fx_exc: print(f"Warning: Failed VFX: {fx_exc}")
                
                if CROSSFADE_DURATION > 0 and video_segments:
                    processed_duration = sped_up_segment.duration if sped_up_segment.duration is not None else (TARGET_CLIP_DURATION / current_speed_factor)
                    safe_crossfade = min(CROSSFADE_DURATION, 
                                         processed_duration / 2.0 if processed_duration > 0 else CROSSFADE_DURATION, 
                                         segment_duration_on_timeline / 2.0)
                    if safe_crossfade > 0.01: sped_up_segment = sped_up_segment.crossfadein(safe_crossfade)
                
                processed_segment_for_timeline = sped_up_segment.set_start(beat_start_time)
                processed_segment_for_timeline = processed_segment_for_timeline.set_duration(segment_duration_on_timeline)
                video_segments.append(processed_segment_for_timeline)
            except Exception as e:
                print(f"Warning: Could not load/process {source_video_path}. Skipping. Error: {e}")
            finally:
                clip_selector_idx += 1

        if not video_segments: raise RuntimeError("No video segments created.")

        print("Compositing video clips...")
        final_duration = 0.0
        valid_ends = [seg.end for seg in video_segments if seg.end is not None]
        if valid_ends: final_duration = max(valid_ends)
        elif beat_times.size > 0: final_duration = beat_times[-1]

        with AudioFileClip(AUDIO_FILE_PATH) as original_audio:
            final_duration = max(final_duration, original_audio.duration)
            target_resolution = None
            if loaded_source_clips:
                first_cached_path = next(iter(loaded_source_clips))
                if hasattr(loaded_source_clips[first_cached_path], 'size') and loaded_source_clips[first_cached_path].size:
                    target_resolution = loaded_source_clips[first_cached_path].size
            if target_resolution is None and video_file_paths:
                try:
                    with VideoFileClip(video_file_paths[0], audio=False) as temp_clip: target_resolution = temp_clip.size
                except Exception: pass
            if target_resolution is None: target_resolution = (1280, 720); print("Defaulting resolution 1280x720")
            print(f"Using target resolution: {target_resolution[0]}x{target_resolution[1]}")

            final_composition = CompositeVideoClip(video_segments, size=target_resolution, bg_color=(0,0,0))
            final_composition = final_composition.set_duration(final_duration)

            with AudioFileClip(AUDIO_FILE_PATH) as audio_for_final_render:
                audio_clip_for_final = audio_for_final_render.subclip(0, final_duration)
                final_composition = final_composition.set_audio(audio_clip_for_final)
                print(f"Rendering final video to: {OUTPUT_VIDEO_PATH}")
                try:
                    if not TARGET_COMPILED_DIR_FOR_UPSCALER or not os.path.isdir(TARGET_COMPILED_DIR_FOR_UPSCALER):
                        raise ValueError(f"TARGET_COMPILED_DIR_FOR_UPSCALER not valid: {TARGET_COMPILED_DIR_FOR_UPSCALER}")
                    temp_audio_filename = f"temp-audio_{timestamp_str}.m4a"
                    temp_audio_path = os.path.join(TARGET_COMPILED_DIR_FOR_UPSCALER, temp_audio_filename)
                    final_composition.write_videofile(
                        OUTPUT_VIDEO_PATH, codec="libx264", audio_codec="aac",
                        temp_audiofile=temp_audio_path, remove_temp=True,
                        preset=OUTPUT_PRESET, fps=OUTPUT_FPS, threads=os.cpu_count() or 2, bitrate=OUTPUT_BITRATE
                    )
                    print("✅ Video rendering complete!")
                except Exception as e_render:
                    print(f"ERROR during video rendering: {e_render}"); import traceback; traceback.print_exc()
                finally:
                    if 'audio_clip_for_final' in locals() and hasattr(audio_clip_for_final, 'close'): audio_clip_for_final.close()
        if hasattr(final_composition, 'close'): final_composition.close()
    except (FileNotFoundError, ValueError, RuntimeError) as e: print(f"ERROR: {e}")
    except Exception as e_outer:
        print(f"An unexpected critical error occurred: {e_outer}"); import traceback; traceback.print_exc()
    finally:
        print("\n🔒 Finalizing: Closing all cached source video files...")
        for clip_path, clip_obj in loaded_source_clips.items():
            try: clip_obj.close()
            except Exception as e_close: print(f"Warning: Error closing {os.path.basename(clip_path)}: {e_close}")
        loaded_source_clips.clear()
        print("Script execution finished.")