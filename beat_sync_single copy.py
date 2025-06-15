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
    vfx,
    concatenate_videoclips # <--- ADDED FOR YO-YO
)
from tqdm import tqdm

# --- Configuration ---

# 1. Base directory for "Run_YYYYMMDD_HHMMSS" folders:
BASE_DANCERS_DIR = r"H:\dancers_content"
RUN_PREFIX = "Run_"

# 2. Audio file path:
AUDIO_FILE_PATH = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\music.mp3"

# 3. How long each video segment (from original source, before speed-up) should be, in seconds:
#    This now acts more as a *maximum preferred* source duration to take, especially for normal clips.
TARGET_CLIP_DURATION = 5.0

# 4. Speed Variation Configuration
ENABLE_DYNAMIC_SPEED = True
BASE_VIDEO_SPEED_FACTOR = 1.5   # Base speed for segments
FAST_BEAT_THRESHOLD = 0.4
SLOW_BEAT_THRESHOLD = 0.8
FAST_BEAT_SPEED_MULTIPLIER = 1.25
NORMAL_BEAT_SPEED_MULTIPLIER = 1.0
SLOW_BEAT_SPEED_MULTIPLIER = 0.8
MIN_EFFECTIVE_SPEED = 0.75
MAX_EFFECTIVE_SPEED = 3.0

# 5. Subsample beats (1 means use every beat):
USE_EVERY_NTH_BEAT = 1

# 6. Visual Enhancements Configuration
APPLY_RANDOM_EFFECTS = True
EFFECT_PROBABILITY = 0.35
CROSSFADE_DURATION = 0.15
SHUFFLE_VIDEO_FILES = True

# 7. Output Video Configuration
OUTPUT_FPS = 24
OUTPUT_PRESET = "medium"
OUTPUT_BITRATE = "5000k"

# --- NEW: 8. Yo-Yo (Forward then Reverse) Effect Configuration ---
ENABLE_YOYO_EFFECT = True
YOYO_PROBABILITY = 0.40           # Probability of applying yo-yo if conditions are met
# Minimum original source duration (before speedup) for EACH HALF of the yo-yo.
# e.g., if 0.5, needs 0.5s for forward, 0.5s for reverse from source.
MIN_YOYO_SOURCE_DURATION_PER_HALF = 0.5
# If a yo-yo is made, its content (forward part + reverse part) will be stretched/shrunk
# by the final set_duration call to fit the beat segment duration.

# Minimum source material to take for a normal (non-yo-yo) segment.
# If calculated need is less, we might skip or take this minimum.
MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP = 0.2 # seconds

# --- Helper Functions ---
# ... (find_latest_run_folder, find_video_clips_folder, get_video_files, detect_beats, apply_random_vfx remain unchanged) ...
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
        # ... (Initial setup: latest_run_folder, VIDEO_CLIPS_FOLDER, output paths, audio/video checks - unchanged) ...
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

            # --- Dynamic Speed Calculation (unchanged) ---
            current_speed_factor = BASE_VIDEO_SPEED_FACTOR 
            if ENABLE_DYNAMIC_SPEED:
                if segment_duration_on_timeline <= FAST_BEAT_THRESHOLD:
                    current_speed_factor = BASE_VIDEO_SPEED_FACTOR * FAST_BEAT_SPEED_MULTIPLIER
                elif segment_duration_on_timeline >= SLOW_BEAT_THRESHOLD:
                    current_speed_factor = BASE_VIDEO_SPEED_FACTOR * SLOW_BEAT_SPEED_MULTIPLIER
                current_speed_factor = max(MIN_EFFECTIVE_SPEED, min(current_speed_factor, MAX_EFFECTIVE_SPEED))
                # if abs(current_speed_factor - BASE_VIDEO_SPEED_FACTOR) > 0.01:
                # print(f" Beat {i+1} ({segment_duration_on_timeline:.2f}s) -> DynSpeed: {current_speed_factor:.2f}x")

            # --- MODIFIED SEGMENT CREATION LOGIC ---
            source_video_path = video_file_paths[clip_selector_idx % len(video_file_paths)]
            # This will hold the raw sped-up content (normal or yo-yo) BEFORE final timeline fitting and crossfade
            active_clip_content = None 
            attempt_yoyo = False

            try:
                if source_video_path not in loaded_source_clips:
                    loaded_source_clips[source_video_path] = VideoFileClip(source_video_path, audio=False, verbose=False)
                source_clip_instance = loaded_source_clips[source_video_path]

                # --- Decide if attempting Yo-Yo ---
                if ENABLE_YOYO_EFFECT and random.random() < YOYO_PROBABILITY and source_clip_instance.duration > (MIN_YOYO_SOURCE_DURATION_PER_HALF * 2): # Basic check
                    # Source duration needed for ONE HALF of the yo-yo to fill HALF the timeline slot after speedup
                    source_duration_for_one_yoyo_half = (segment_duration_on_timeline / 2.0) * current_speed_factor
                    
                    # Actual source to take for one half, capped by available duration, preferred max, and calculated need
                    actual_source_to_take_for_yoyo_half = min(
                        source_clip_instance.duration / 2.0, # Max available for one half if taking from start
                        TARGET_CLIP_DURATION, # Overall preference for max source intake
                        source_duration_for_one_yoyo_half
                    )

                    if actual_source_to_take_for_yoyo_half >= MIN_YOYO_SOURCE_DURATION_PER_HALF:
                        attempt_yoyo = True
                        
                        segment_material_forward = source_clip_instance.subclip(0, actual_source_to_take_for_yoyo_half)
                        sped_up_forward = segment_material_forward.fx(vfx.speedx, current_speed_factor)
                        
                        if sped_up_forward.duration is not None and sped_up_forward.duration > 0.01:
                            sped_up_reversed = sped_up_forward.fx(vfx.time_mirror)
                            active_clip_content = concatenate_videoclips(
                                [sped_up_forward, sped_up_reversed],
                                method="compose" 
                            )
                            # print(f"  Beat {i+1}: YoYo! SrcHalf:{actual_source_to_take_for_yoyo_half:.2f}s -> ClipDur:{active_clip_content.duration:.2f}s")
                        else:
                            # print(f"  Beat {i+1}: YoYo forward part too short ({sped_up_forward.duration}), skipping yo-yo.")
                            attempt_yoyo = False # Fallback to normal
                    # else:
                        # print(f"  Beat {i+1}: YoYo skipped, not enough source for half ({actual_source_to_take_for_yoyo_half:.2f}s < {MIN_YOYO_SOURCE_DURATION_PER_HALF}s)")


                # --- Normal segment processing (if not doing yo-yo or yo-yo failed) ---
                if not attempt_yoyo:
                    # Source duration needed to fill the ENTIRE timeline slot after speedup
                    source_duration_for_normal_clip = segment_duration_on_timeline * current_speed_factor
                    
                    duration_to_take_from_original = min(
                        source_clip_instance.duration,
                        TARGET_CLIP_DURATION, # Max preferred source duration
                        source_duration_for_normal_clip
                    )
                    # Ensure we take at least a minimum, if possible, and it's not less than the calculated need.
                    duration_to_take_from_original = max(duration_to_take_from_original, MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP if source_clip_instance.duration > MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP else 0)


                    if duration_to_take_from_original < 0.05: # Stricter check than 0.1 if we're taking so little
                        # print(f"  Beat {i+1}: Normal clip source too short ({duration_to_take_from_original:.2f}s). Skipping this source for beat.")
                        clip_selector_idx += 1 # Advance to next clip for *next* beat. This beat gets skipped for this source.
                        continue 
                    
                    segment_material = source_clip_instance.subclip(0, duration_to_take_from_original)
                    active_clip_content = segment_material.fx(vfx.speedx, current_speed_factor)
                    # print(f"  Beat {i+1}: Normal. Src:{duration_to_take_from_original:.2f}s -> ClipDur:{active_clip_content.duration:.2f}s")

                # --- Common post-processing for EITHER yo-yo or normal clip ---
                if active_clip_content is None or active_clip_content.duration is None or active_clip_content.duration < 0.01:
                    # print(f"  Beat {i+1}: active_clip_content invalid after creation. Skipping.")
                    clip_selector_idx += 1 
                    continue

                # Apply random visual effects
                if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
                    try:
                        active_clip_content = apply_random_vfx(active_clip_content)
                    except Exception as fx_exc:
                        print(f"Warning: Failed VFX on clip from {os.path.basename(source_video_path)}: {fx_exc}")
                
                # This will be the clip that gets start time and duration set for the timeline
                segment_to_place_on_timeline = active_clip_content 
                
                # Apply crossfade-in if there are previous segments
                if CROSSFADE_DURATION > 0 and video_segments:
                    # Calculate safe crossfade based on the current clip's actual duration
                    # AND the target duration it will have on the timeline.
                    current_clip_actual_duration = active_clip_content.duration
                    
                    safe_crossfade = min(CROSSFADE_DURATION,
                                         current_clip_actual_duration / 2.0 if current_clip_actual_duration else CROSSFADE_DURATION,
                                         segment_duration_on_timeline / 2.0) # Cannot crossfade longer than half the timeline slot
                    
                    if safe_crossfade > 0.01:
                        segment_to_place_on_timeline = segment_to_place_on_timeline.crossfadein(safe_crossfade)
                
                # Set start time and force duration to fit the beat segment precisely
                final_processed_segment = segment_to_place_on_timeline.set_start(beat_start_time)
                final_processed_segment = final_processed_segment.set_duration(segment_duration_on_timeline)
                
                video_segments.append(final_processed_segment)

            except Exception as e:
                print(f"Warning: Could not load/process {os.path.basename(source_video_path)} for beat {i+1}. Error: {e}")
                # import traceback; traceback.print_exc() # Uncomment for deep debugging
            finally:
                # Always advance to next source video for the next beat segment,
                # regardless of success/failure for the current beat.
                clip_selector_idx += 1
        # --- END OF MODIFIED SEGMENT CREATION ---

        if not video_segments: raise RuntimeError("No video segments created.")

        # ... (Compositing, audio attachment, rendering - unchanged) ...
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