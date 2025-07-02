#!/usr/bin/env python3
"""
beat_sync_character_separated.py

Modified version of beat_sync_single.py that processes videos by character.
Creates separate compilation videos for each character, ensuring no character mixing.

Usage:
    python beat_sync_character_separated.py

The script will:
1. Find the latest run folder
2. Detect character folders in phase3_videos
3. For each character + audio combination, create a separate compilation
4. Output: character_1_song1.mp4, character_2_song1.mp4, etc.
"""

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
    concatenate_videoclips
)
from tqdm import tqdm
from pathlib import Path

# --- Configuration ---
BASE_DANCERS_DIR = r"H:\dancers_content"
RUN_PREFIX = "Run_"
INSTAGRAM_AUDIO_DIR = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\instagram_audio"

# --- Settings ---
TARGET_CLIP_DURATION = 5.0
ENABLE_DYNAMIC_SPEED = True
BASE_VIDEO_SPEED_FACTOR = 1.5
FAST_BEAT_THRESHOLD = 0.4
SLOW_BEAT_THRESHOLD = 0.8
FAST_BEAT_SPEED_MULTIPLIER = 1.25
NORMAL_BEAT_SPEED_MULTIPLIER = 1.0
SLOW_BEAT_SPEED_MULTIPLIER = 0.8
MIN_EFFECTIVE_SPEED = 0.75
MAX_EFFECTIVE_SPEED = 3.0
USE_EVERY_NTH_BEAT = 1
APPLY_RANDOM_EFFECTS = True
EFFECT_PROBABILITY = 0.35
CROSSFADE_DURATION = 0.15
SHUFFLE_VIDEO_FILES = True
OUTPUT_FPS = 24
OUTPUT_PRESET = "medium"
OUTPUT_BITRATE = "5000k"

ENABLE_YOYO_EFFECT = True
YOYO_PROBABILITY = 0.40
MIN_YOYO_SOURCE_DURATION_PER_HALF = 0.5
MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP = 0.2

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

def find_character_folders(latest_run_folder_path):
    """Find all character folders in phase3_videos (character-aware structure)"""
    phase3_videos_dir = None
    
    # Look for phase3_videos directory
    for item in os.listdir(latest_run_folder_path):
        item_path = os.path.join(latest_run_folder_path, item)
        if os.path.isdir(item_path) and "phase3_videos" in item:
            phase3_videos_dir = item_path
            break
    
    if not phase3_videos_dir:
        raise FileNotFoundError(f"No phase3_videos folder found in {latest_run_folder_path}")
    
    # NEW CHARACTER-AWARE STRUCTURE: Look for character folders directly in phase3_videos
    character_folders = {}
    for item in os.listdir(phase3_videos_dir):
        item_path = os.path.join(phase3_videos_dir, item)
        if os.path.isdir(item_path) and item.startswith("character_"):
            character_id = item.replace("character_", "")
            
            # Find the date subdirectory within this character folder
            date_subdirs = [os.path.join(item_path, name) for name in os.listdir(item_path) 
                           if os.path.isdir(os.path.join(item_path, name))]
            
            if date_subdirs:
                # Use the latest date folder for this character
                character_date_dir = max(date_subdirs, key=lambda p: os.path.getmtime(p))
                character_folders[character_id] = character_date_dir
                print(f"✅ Found character_{character_id}: {character_date_dir}")
            else:
                print(f"⚠️ Warning: No date folder found in character_{character_id}")
    
    if not character_folders:
        raise FileNotFoundError(f"No character folders found in {phase3_videos_dir}. Expected character-aware structure: phase3_videos/character_X/date/")
    
    print(f"📁 Total characters found: {len(character_folders)}")
    return character_folders

def get_video_files(folder_path):
    extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm")
    files = []
    for ext in extensions: 
        files.extend(glob.glob(os.path.join(folder_path, ext)))
    if not files: 
        raise ValueError(f"No video files found in {folder_path} with extensions {extensions}")
    files.sort()
    if SHUFFLE_VIDEO_FILES: 
        random.shuffle(files)
        print(f"Shuffled video file order for {os.path.basename(folder_path)}.")
    return files

def detect_beats(audio_path, tightness_param=100):
    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path)
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)
    actual_tempo_for_print = 0.0
    if isinstance(tempo, np.ndarray):
        if tempo.size == 1: 
            actual_tempo_for_print = tempo.item()
        elif tempo.size > 0: 
            actual_tempo_for_print = tempo[0]
            print(f"Info: Multi-tempo {tempo}, using first.")
        else: 
            print("Info: Librosa empty tempo array.")
    elif isinstance(tempo, (int, float)): 
        actual_tempo_for_print = tempo
    else: 
        print(f"Info: Non-numeric tempo: {tempo} type: {type(tempo)}.")
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"Detected {len(beat_times)} beats. Tempo: {actual_tempo_for_print:.2f} BPM")
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
        print("Adjusted beat list to include time 0.0")
    return beat_times

def apply_random_vfx(clip):
    effects_pool = [
        {"name": "mirror_x", "func": lambda c: c.fx(vfx.mirror_x)},
        {"name": "blackwhite", "func": lambda c: c.fx(vfx.blackwhite, RGB=[1,1,1], preserve_luminosity=True)},
        {"name": "lum_contrast_inc", "func": lambda c: c.fx(vfx.lum_contrast, lum=0, contrast=0.2)},
        {"name": "gamma_brighten", "func": lambda c: c.fx(vfx.gamma_corr, gamma=1.2)},
    ]
    if not effects_pool: 
        print("Warning: No effects in effects_pool.")
        return clip
    chosen_effect_dict = random.choice(effects_pool)
    return chosen_effect_dict["func"](clip)

def create_beat_synced_segment(beat_start_time, segment_duration_on_timeline, video_file_paths, loaded_source_clips, clip_selector_idx, video_segments):
    """Create a beat-synced video segment"""
    current_speed_factor = BASE_VIDEO_SPEED_FACTOR
    if ENABLE_DYNAMIC_SPEED:
        if segment_duration_on_timeline <= FAST_BEAT_THRESHOLD:
            current_speed_factor *= FAST_BEAT_SPEED_MULTIPLIER
        elif segment_duration_on_timeline >= SLOW_BEAT_THRESHOLD:
            current_speed_factor *= SLOW_BEAT_SPEED_MULTIPLIER
        current_speed_factor = max(MIN_EFFECTIVE_SPEED, min(current_speed_factor, MAX_EFFECTIVE_SPEED))
    
    source_video_path = video_file_paths[clip_selector_idx % len(video_file_paths)]
    
    try:
        if source_video_path not in loaded_source_clips:
            loaded_source_clips[source_video_path] = VideoFileClip(source_video_path, audio=False, verbose=False)
        source_clip_instance = loaded_source_clips[source_video_path]
        
        active_clip_content = None
        attempt_yoyo = False
        
        if ENABLE_YOYO_EFFECT and random.random() < YOYO_PROBABILITY and source_clip_instance.duration > (MIN_YOYO_SOURCE_DURATION_PER_HALF * 2):
            source_duration_for_one_yoyo_half = (segment_duration_on_timeline / 2.0) * current_speed_factor
            actual_source_to_take_for_yoyo_half = min(source_clip_instance.duration / 2.0, TARGET_CLIP_DURATION, source_duration_for_one_yoyo_half)
            
            if actual_source_to_take_for_yoyo_half >= MIN_YOYO_SOURCE_DURATION_PER_HALF:
                attempt_yoyo = True
                segment_material_forward = source_clip_instance.subclip(0, actual_source_to_take_for_yoyo_half)
                sped_up_forward = segment_material_forward.fx(vfx.speedx, current_speed_factor)
                
                if sped_up_forward.duration is not None and sped_up_forward.duration > 0.01:
                    sped_up_reversed = sped_up_forward.fx(vfx.time_mirror)
                    active_clip_content = concatenate_videoclips([sped_up_forward, sped_up_reversed], method="compose")
                else:
                    attempt_yoyo = False
        
        if not attempt_yoyo:
            source_duration_for_normal_clip = segment_duration_on_timeline * current_speed_factor
            duration_to_take_from_original = min(source_clip_instance.duration, TARGET_CLIP_DURATION, source_duration_for_normal_clip)
            duration_to_take_from_original = max(duration_to_take_from_original, MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP if source_clip_instance.duration > MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP else 0)
            
            if duration_to_take_from_original < 0.05: return None
            
            segment_material = source_clip_instance.subclip(0, duration_to_take_from_original)
            active_clip_content = segment_material.fx(vfx.speedx, current_speed_factor)
        
        if active_clip_content is None or active_clip_content.duration is None or active_clip_content.duration < 0.01: return None
        
        if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
            active_clip_content = apply_random_vfx(active_clip_content)
        
        segment_to_place_on_timeline = active_clip_content
        
        if CROSSFADE_DURATION > 0 and video_segments:
            current_clip_actual_duration = active_clip_content.duration
            safe_crossfade = min(CROSSFADE_DURATION, current_clip_actual_duration / 2.0 if current_clip_actual_duration else CROSSFADE_DURATION, segment_duration_on_timeline / 2.0)
            if safe_crossfade > 0.01:
                segment_to_place_on_timeline = segment_to_place_on_timeline.crossfadein(safe_crossfade)
        
        final_processed_segment = segment_to_place_on_timeline.set_start(beat_start_time).set_duration(segment_duration_on_timeline)
        return final_processed_segment
        
    except Exception as e:
        print(f"Warning: Could not create beat segment: {e}")
        return None

# --- Character-Specific Processing Function ---
def process_audio_for_character(audio_file_path, character_id, character_folder, loaded_source_clips, output_dir, start_clip_index=0):
    """
    Process a single audio file for a specific character.
    """
    
    audio_filename = os.path.basename(audio_file_path)
    audio_name = os.path.splitext(audio_filename)[0]
    
    print(f"\n🎵 Processing: {audio_filename} for Character {character_id}")
    
    try:
        # Get character-specific video files
        video_file_paths = get_video_files(character_folder)
        print(f"Found {len(video_file_paths)} videos for character {character_id}")
        
        if not video_file_paths:
            print(f"❌ No video files found for character {character_id}")
            return None, start_clip_index
        
        with AudioFileClip(audio_file_path) as temp_audio:
            total_duration = temp_audio.duration
        
        print(f"Audio duration: {total_duration:.1f}s")
        
        sync_section_duration = 3.0
        if total_duration < (sync_section_duration * 2):
            print(f"❌ Audio too short for {sync_section_duration}s start + {sync_section_duration}s end processing")
            return None, start_clip_index
        
        beat_times = detect_beats(audio_file_path)
        if len(beat_times) < 2:
            print("❌ Not enough beats detected")
            return None, start_clip_index
        
        start_beats = beat_times[beat_times <= sync_section_duration]
        if len(start_beats) == 0: start_beats = np.array([0.0, sync_section_duration])
        elif start_beats[-1] < sync_section_duration: start_beats = np.append(start_beats, sync_section_duration)
        
        end_start_time = total_duration - sync_section_duration
        end_beats = beat_times[beat_times >= end_start_time]
        if len(end_beats) == 0: end_beats = np.array([end_start_time, total_duration])
        elif end_beats[0] > end_start_time: end_beats = np.insert(end_beats, 0, end_start_time)
        if end_beats[-1] < total_duration: end_beats = np.append(end_beats, total_duration)
        
        print(f"Start beats (0-{sync_section_duration}s): {len(start_beats)} beats")
        print(f"End beats ({end_start_time:.1f}-{total_duration:.1f}s): {len(end_beats)} beats")
        
        video_segments = []
        clip_selector_idx = start_clip_index
        
        # PART 1: Beat-synced start (0 to sync_section_duration)
        print(f"Creating beat-synced start segments (0-{sync_section_duration}s)...")
        for i in range(len(start_beats) - 1):
            segment_duration = start_beats[i+1] - start_beats[i]
            if segment_duration <= 0.01: continue
            segment = create_beat_synced_segment(start_beats[i], segment_duration, video_file_paths, loaded_source_clips, clip_selector_idx, video_segments)
            if segment: video_segments.append(segment)
            clip_selector_idx += 1
        
        # PART 2: Continuous random videos in middle (gapless)
        middle_start = sync_section_duration
        middle_end = total_duration - sync_section_duration
        
        if middle_end > middle_start:
            print(f"Creating continuous middle segments ({middle_start:.1f}s-{middle_end:.1f}s)...")
            current_time = middle_start
            while current_time < middle_end - 0.05: 
                remaining_time = middle_end - current_time
                target_segment_duration = min(random.uniform(3.0, 7.0), remaining_time)
                
                source_video_path = video_file_paths[clip_selector_idx % len(video_file_paths)]
                
                try:
                    if source_video_path not in loaded_source_clips:
                        loaded_source_clips[source_video_path] = VideoFileClip(source_video_path, audio=False, verbose=False)
                    source_clip = loaded_source_clips[source_video_path]
                    
                    source_duration_needed = target_segment_duration * BASE_VIDEO_SPEED_FACTOR
                    source_duration_to_take = min(source_clip.duration, source_duration_needed)
                    
                    if source_duration_to_take >= 0.2:
                        segment_material = source_clip.subclip(0, source_duration_to_take)
                        sped_up_segment = segment_material.fx(vfx.speedx, BASE_VIDEO_SPEED_FACTOR)
                        actual_clip_duration = sped_up_segment.duration

                        if current_time + actual_clip_duration > middle_end:
                            actual_clip_duration = middle_end - current_time
                            sped_up_segment = sped_up_segment.set_duration(actual_clip_duration)
                        
                        if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
                            sped_up_segment = apply_random_vfx(sped_up_segment)
                        
                        if CROSSFADE_DURATION > 0 and any(s.start >= middle_start for s in video_segments):
                            safe_crossfade = min(CROSSFADE_DURATION, actual_clip_duration / 2.0)
                            if safe_crossfade > 0.01:
                                sped_up_segment = sped_up_segment.crossfadein(safe_crossfade)
                        
                        final_segment = sped_up_segment.set_start(current_time)
                        video_segments.append(final_segment)
                        
                        current_time += final_segment.duration
                    else:
                        print(f"  Skipping unusable short source clip: {os.path.basename(source_video_path)}")

                except Exception as e:
                    print(f"Warning: Could not create middle segment for {os.path.basename(source_video_path)}: {e}")
                
                clip_selector_idx += 1

        # PART 3: Beat-synced end
        print(f"Creating beat-synced end segments ({end_start_time:.1f}s-{total_duration:.1f}s)...")
        for i in range(len(end_beats) - 1):
            segment_duration = end_beats[i+1] - end_beats[i]
            if segment_duration <= 0.01: continue
            segment = create_beat_synced_segment(end_beats[i], segment_duration, video_file_paths, loaded_source_clips, clip_selector_idx, video_segments)
            if segment: video_segments.append(segment)
            clip_selector_idx += 1
        
        if not video_segments:
            print("❌ No video segments created")
            return None, start_clip_index
        
        print("Compositing video clips...")
        target_resolution = (1280, 720) 
        if loaded_source_clips:
            first_cached_path = next(iter(loaded_source_clips))
            if hasattr(loaded_source_clips[first_cached_path], 'size') and loaded_source_clips[first_cached_path].size:
                target_resolution = loaded_source_clips[first_cached_path].size
        
        final_composition = CompositeVideoClip(video_segments, size=target_resolution, bg_color=(0,0,0)).set_duration(total_duration)
        
        with AudioFileClip(audio_file_path) as audio_for_final_render:
            audio_clip_for_final = audio_for_final_render.subclip(0, total_duration)
            final_composition = final_composition.set_audio(audio_clip_for_final)
            
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"character_{character_id}_{audio_name}_{timestamp_str}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"Rendering final video to: {output_path}")
            try:
                temp_audio_path = os.path.join(output_dir, f"temp-audio_{character_id}_{timestamp_str}.m4a")
                final_composition.write_videofile(
                    output_path, codec="libx264", audio_codec="aac", temp_audiofile=temp_audio_path, 
                    remove_temp=True, preset=OUTPUT_PRESET, fps=OUTPUT_FPS, 
                    threads=os.cpu_count() or 2, bitrate=OUTPUT_BITRATE
                )
                print(f"✅ Video rendering complete: {output_filename}")
                return output_path, clip_selector_idx
            except Exception as e_render:
                print(f"ERROR during video rendering: {e_render}")
                return None, start_clip_index
            finally:
                if 'audio_clip_for_final' in locals() and hasattr(audio_clip_for_final, 'close'):
                    audio_clip_for_final.close()
                if hasattr(final_composition, 'close'):
                    final_composition.close()
            
    except Exception as e:
        print(f"ERROR processing {audio_filename} for character {character_id}: {e}")
        import traceback
        traceback.print_exc()
        return None, start_clip_index

# --- Main Logic ---
if __name__ == "__main__":
    loaded_source_clips = {}
    
    try:
        latest_run_folder_path = find_latest_run_folder(BASE_DANCERS_DIR, RUN_PREFIX)
        print(f"👉 Latest run folder detected: {latest_run_folder_path}")
        
        character_folders = find_character_folders(latest_run_folder_path)
        print(f"👉 Found {len(character_folders)} characters: {list(character_folders.keys())}")

        ALL_VIDEOS_CONTAINER_DIR = os.path.join(latest_run_folder_path, "all_videos")
        TARGET_COMPILED_DIR_FOR_UPSCALER = os.path.join(ALL_VIDEOS_CONTAINER_DIR, "compiled_character_separated")
        os.makedirs(TARGET_COMPILED_DIR_FOR_UPSCALER, exist_ok=True)
        print(f"Created/found target compiled directory: {TARGET_COMPILED_DIR_FOR_UPSCALER}")

        print(f"📁 Audio source: {INSTAGRAM_AUDIO_DIR}")
        print(f"📁 Output: {TARGET_COMPILED_DIR_FOR_UPSCALER}")

        audio_files = glob.glob(os.path.join(INSTAGRAM_AUDIO_DIR, "*.mp4")) + glob.glob(os.path.join(INSTAGRAM_AUDIO_DIR, "*.mp3"))
        if not audio_files:
            raise ValueError(f"No audio files (.mp4, .mp3) found in {INSTAGRAM_AUDIO_DIR}")
        audio_files.sort()
        print(f"Found {len(audio_files)} audio files")

        # Process each character × audio combination
        successful_renders = 0
        total_combinations = len(character_folders) * len(audio_files)
        
        print(f"\n🎬 Starting character-separated compilation generation...")
        print(f"📊 Total combinations: {total_combinations} ({len(character_folders)} characters × {len(audio_files)} songs)")
        
        for character_id, character_folder in character_folders.items():
            print(f"\n{'='*80}")
            print(f"🎭 Processing Character {character_id}")
            print(f"📁 Character folder: {character_folder}")
            
            character_video_offset = 0  # Separate offset per character
            
            for audio_file in tqdm(audio_files, desc=f"Character {character_id} Audio Files"):
                
                result_path, next_start_index = process_audio_for_character(
                    audio_file, 
                    character_id,
                    character_folder,
                    loaded_source_clips, 
                    TARGET_COMPILED_DIR_FOR_UPSCALER,
                    start_clip_index=character_video_offset 
                )
                
                if result_path:
                    successful_renders += 1
                    character_video_offset = next_start_index
                    print(f"✅ Successfully created: {os.path.basename(result_path)}")

        print(f"\n🎉 Complete! Successfully rendered {successful_renders}/{total_combinations} character-specific videos")
        print(f"📊 Results:")
        print(f"   - {len(character_folders)} characters processed")
        print(f"   - {len(audio_files)} songs processed") 
        print(f"   - {successful_renders} total compilation videos generated")
        print(f"📁 All outputs saved in: {TARGET_COMPILED_DIR_FOR_UPSCALER}")

    except Exception as e:
        print(f"\n\nFATAL ERROR: An unhandled exception occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Finalizing: Closing all cached source video files...")
        for clip_path, clip_obj in loaded_source_clips.items():
            try: 
                if hasattr(clip_obj, 'close'):
                    clip_obj.close()
            except Exception as e_close: 
                print(f"Warning: Error closing {os.path.basename(clip_path)}: {e_close}")
        loaded_source_clips.clear()
        print("Script execution finished.")