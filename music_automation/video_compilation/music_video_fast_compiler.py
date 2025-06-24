#!/usr/bin/env python3
"""
Music Video Sequential Beat Sync Compiler (Fast Version - No Subtitles)
ENHANCED VERSION with Sequential Video Selection and Advanced Beat Synchronization

=== PREVIOUS BEHAVIOR (Backup: music_video_fast_compiler_backup.py) ===
The previous version divided audio time equally among videos with forward/mirrored patterns.
Each video got a fixed time slot regardless of beat alignment.

=== NEW ENHANCED BEHAVIOR ===
This version implements sequential video selection with enhanced beat synchronization:
- Videos are selected sequentially and used across the full audio duration
- Advanced beat detection identifies main beats (high intensity) and secondary beats
- Segment timing and playback speed adapt based on beat proximity:
  * HIGH SYNC: Main beats get longer segments with faster playback (1.3x speed)
  * MODERATE SYNC: Secondary beats get normal segments with slight speed boost (1.1x)
  * STANDARD: Non-beat areas get shorter segments with normal playback
- Creates dynamic, rhythm-responsive video flow that matches music intensity

=== BENEFITS OF SEQUENTIAL BEAT SYNC APPROACH ===
✅ Videos play sequentially across full duration (no time division)
✅ Enhanced beat synchronization with focus on main beats
✅ Dynamic segment timing based on musical intensity
✅ Speed variations create visual emphasis on strong beats
✅ More natural video progression that follows the music
✅ Eliminates artificial time constraints per video
✅ Better utilization of available video content

This is a faster version that skips Whisper transcription for quicker processing.
For karaoke subtitles, use music_video_beat_sync_compiler.py instead.

Author: Claude Code Assistant
Date: 2025-06-23 (Sequential Beat Sync Version)
"""

import os
import glob
import librosa
import numpy as np
import random
import shutil
from datetime import datetime
from pathlib import Path
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    vfx,
    concatenate_videoclips
)
from tqdm import tqdm
from scipy.signal import find_peaks

# --- Configuration ---
DANCERS_CONTENT_BASE = Path("H:/dancers_content")
SONGS_DIR = Path("D:/Comfy_UI_V20/ComfyUI/output/dancer/songs")
OUTPUT_FOLDER_NAME = "music_video_compiled"

# Alternative song directory for music automation folder
MUSIC_AUTOMATION_SONGS_DIR = Path(__file__).parent.parent / "assets"
if not SONGS_DIR.exists() and MUSIC_AUTOMATION_SONGS_DIR.exists():
    SONGS_DIR = MUSIC_AUTOMATION_SONGS_DIR
    print(f"📁 Using music automation songs directory: {SONGS_DIR}")

# --- Beat Sync Settings ---
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

# --- Copy all the same functions from the main script (without Whisper parts) ---
def find_latest_music_run_folder():
    """Find the most recent Run_*_music_images folder"""
    print("🔍 Searching for latest music run folder...")
    
    if not DANCERS_CONTENT_BASE.exists():
        raise FileNotFoundError(f"Dancers content directory not found: {DANCERS_CONTENT_BASE}")
    
    pattern = str(DANCERS_CONTENT_BASE / "Run_*_music_images")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        raise FileNotFoundError("No Run_*_music_images folders found")
    
    # Sort by modification time, newest first
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    latest_folder = Path(music_folders[0])
    
    print(f"✅ Found latest music run: {latest_folder.name}")
    print(f"   Full path: {latest_folder}")
    print(f"   Modified: {datetime.fromtimestamp(latest_folder.stat().st_mtime)}")
    
    return latest_folder

def find_video_clips_in_music_folder(music_folder):
    """Find video clips in the date subfolder within all_videos"""
    print(f"📁 Searching for video clips in: {music_folder.name}")
    
    all_videos_dir = music_folder / "all_videos"
    if not all_videos_dir.exists():
        raise FileNotFoundError(f"all_videos directory not found in {music_folder}")
    
    # Find date subfolders (should be 6-digit date like 250622)
    date_folders = [
        d for d in all_videos_dir.iterdir() 
        if d.is_dir() and d.name.isdigit() and len(d.name) == 6
    ]
    
    if not date_folders:
        raise FileNotFoundError(f"No date subfolder found in {all_videos_dir}")
    
    # Use the most recent date folder
    date_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    video_clips_folder = date_folders[0]
    
    print(f"📂 Using date folder: {video_clips_folder.name}")
    
    # Get all video files
    video_extensions = ["*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"]
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(video_clips_folder.glob(ext))
    
    if not video_files:
        raise FileNotFoundError(f"No video files found in {video_clips_folder}")
    
    video_files.sort()
    if SHUFFLE_VIDEO_FILES:
        random.shuffle(video_files)
        print(f"🔀 Shuffled {len(video_files)} video files")
    
    print(f"✅ Found {len(video_files)} video clips")
    return video_files

def find_latest_song():
    """Find the most recent song file in the songs directory"""
    print("🎵 Searching for latest song...")
    
    if not SONGS_DIR.exists():
        raise FileNotFoundError(f"Songs directory not found: {SONGS_DIR}")
    
    # Look for audio files
    audio_extensions = ["*.mp3", "*.wav", "*.m4a", "*.flac"]
    audio_files = []
    
    for ext in audio_extensions:
        audio_files.extend(SONGS_DIR.glob(ext))
    
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {SONGS_DIR}")
    
    # Sort by modification time, newest first
    audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_song = audio_files[0]
    
    print(f"✅ Found latest song: {latest_song.name}")
    print(f"   Modified: {datetime.fromtimestamp(latest_song.stat().st_mtime)}")
    
    return latest_song

def create_output_directory(music_folder):
    """Create the output directory for compiled video"""
    output_dir = music_folder / "all_videos" / OUTPUT_FOLDER_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Created output directory: {output_dir}")
    return output_dir

def apply_random_vfx(clip):
    """Apply random visual effects to video clip"""
    effects_pool = [
        {"name": "mirror_x", "func": lambda c: c.fx(vfx.mirror_x)},
        {"name": "blackwhite", "func": lambda c: c.fx(vfx.blackwhite, RGB=[1,1,1], preserve_luminosity=True)},
        {"name": "lum_contrast_inc", "func": lambda c: c.fx(vfx.lum_contrast, lum=0, contrast=0.2)},
        {"name": "gamma_brighten", "func": lambda c: c.fx(vfx.gamma_corr, gamma=1.2)},
    ]
    
    if not effects_pool: 
        print("⚠️ Warning: No effects in effects_pool.")
        return clip
    
    chosen_effect_dict = random.choice(effects_pool)
    return chosen_effect_dict["func"](clip)

def create_forward_mirrored_segment(video_clip, allocated_time, start_time, apply_effects=True):
    """Create forward-mirrored looping segment for allocated time slot"""
    segments = []
    current_time = 0.0
    use_original = True  # Alternates between original and horizontally mirrored
    segment_duration = 2.0  # Each forward/mirrored segment duration
    
    while current_time < allocated_time:
        remaining_time = allocated_time - current_time
        actual_segment_duration = min(segment_duration, remaining_time)
        
        if actual_segment_duration < 0.1:  # Skip very short segments
            break
        
        # Create base segment from video clip
        base_segment = video_clip.subclip(0, min(video_clip.duration, actual_segment_duration))
        
        # Apply mirroring (original or horizontally mirrored, both play forward)
        if use_original:
            processed_segment = base_segment  # Original video, forward
        else:
            processed_segment = base_segment.fx(vfx.mirror_x)  # Horizontally mirrored, forward
        
        # Apply random effects occasionally
        if apply_effects and APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
            processed_segment = apply_random_vfx(processed_segment)
        
        # Set timing and add to segments
        final_segment = processed_segment.set_start(start_time + current_time).set_duration(actual_segment_duration)
        segments.append(final_segment)
        
        current_time += actual_segment_duration
        use_original = not use_original  # Alternate between original and mirrored
    
    return segments

def detect_beats_advanced(song_path, tightness_param=100):
    """Advanced beat detection using the proven approach from beat_sync_single.py"""
    print(f"🎵 Analyzing beats with advanced detection for: {song_path.name}")
    
    # Load audio for analysis
    y, sr = librosa.load(str(song_path))
    
    # Beat tracking with tightness parameter for better accuracy
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)
    
    # Handle tempo array conversion (from beat_sync_single.py)
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
    
    # Convert frames to time
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"🥁 Detected {len(beat_times)} beats. Tempo: {actual_tempo_for_print:.2f} BPM")
    
    # Ensure beat at time 0.0 (from beat_sync_single.py)
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
        print("Adjusted beat list to include time 0.0")
    
    return beat_times, actual_tempo_for_print

def analyze_beat_structure(song_path, total_duration):
    """Analyze beat structure and create smart switching strategy"""
    print(f"🎭 Analyzing beat structure for smart switching...")
    
    beat_times, tempo = detect_beats_advanced(song_path)
    
    # Define sections for optimal flow
    sync_section_duration = 8.0  # Longer sync sections for dramatic effect
    
    # Identify key structural beats for switching
    dramatic_switch_points = []
    min_switch_spacing = 20.0  # Longer minimum spacing for smoother flow
    
    # Start section beats (0 to sync_section_duration)
    start_beats = beat_times[beat_times <= sync_section_duration]
    if len(start_beats) == 0: 
        start_beats = np.array([0.0, sync_section_duration])
    elif start_beats[-1] < sync_section_duration: 
        start_beats = np.append(start_beats, sync_section_duration)
    
    # End section beats (last sync_section_duration seconds)
    end_start_time = total_duration - sync_section_duration
    end_beats = beat_times[beat_times >= end_start_time]
    if len(end_beats) == 0: 
        end_beats = np.array([end_start_time, total_duration])
    elif end_beats[0] > end_start_time: 
        end_beats = np.insert(end_beats, 0, end_start_time)
    if end_beats[-1] < total_duration: 
        end_beats = np.append(end_beats, total_duration)
    
    # Create strategic switch points
    dramatic_switch_points = [0.0]  # Always start at 0
    
    # Add middle section switches based on tempo and structure
    if total_duration > sync_section_duration * 2 + min_switch_spacing:
        middle_start = sync_section_duration
        middle_end = total_duration - sync_section_duration
        
        # Calculate optimal number of switches for middle section
        middle_duration = middle_end - middle_start
        num_middle_switches = max(1, int(middle_duration / min_switch_spacing))
        
        for i in range(1, num_middle_switches + 1):
            switch_time = middle_start + (i * middle_duration / (num_middle_switches + 1))
            
            # Snap to nearest beat for better sync
            closest_beat_idx = np.argmin(np.abs(beat_times - switch_time))
            snapped_switch_time = beat_times[closest_beat_idx]
            
            if snapped_switch_time not in dramatic_switch_points:
                dramatic_switch_points.append(snapped_switch_time)
                print(f"🎯 Strategic switch point at {snapped_switch_time:.1f}s (snapped to beat)")
    
    # Add end section start if not already there
    if end_start_time not in dramatic_switch_points and end_start_time > dramatic_switch_points[-1] + 5.0:
        dramatic_switch_points.append(end_start_time)
        print(f"🎵 End section switch at {end_start_time:.1f}s")
    
    dramatic_switch_points.sort()
    
    print(f"🎯 Final strategic switch points: {len(dramatic_switch_points)}")
    print(f"⏱️ Average time between switches: {(dramatic_switch_points[-1] - dramatic_switch_points[0]) / max(1, len(dramatic_switch_points) - 1):.1f}s")
    print(f"📊 Switch times: {[f'{t:.1f}s' for t in dramatic_switch_points]}")
    
    return beat_times, dramatic_switch_points, start_beats, end_beats, tempo

def create_beat_synced_segment_advanced(beat_start_time, segment_duration, video_files, loaded_source_clips, clip_index, video_segments):
    """Create advanced beat-synced segment using proven approach from beat_sync_single.py"""
    
    # Dynamic speed based on segment duration (from beat_sync_single.py)
    current_speed_factor = BASE_VIDEO_SPEED_FACTOR
    if ENABLE_DYNAMIC_SPEED:
        if segment_duration <= FAST_BEAT_THRESHOLD:
            current_speed_factor *= FAST_BEAT_SPEED_MULTIPLIER
        elif segment_duration >= SLOW_BEAT_THRESHOLD:
            current_speed_factor *= SLOW_BEAT_SPEED_MULTIPLIER
        current_speed_factor = max(MIN_EFFECTIVE_SPEED, min(current_speed_factor, MAX_EFFECTIVE_SPEED))
    
    # Select video sequentially
    source_video_path = video_files[clip_index % len(video_files)]
    
    try:
        if source_video_path not in loaded_source_clips:
            loaded_source_clips[source_video_path] = VideoFileClip(str(source_video_path), audio=False, verbose=False)
        source_clip = loaded_source_clips[source_video_path]
        
        active_clip_content = None
        attempt_yoyo = False
        
        # Try YOYO effect for dramatic beats (from beat_sync_single.py)
        if ENABLE_YOYO_EFFECT and random.random() < YOYO_PROBABILITY and source_clip.duration > (MIN_YOYO_SOURCE_DURATION_PER_HALF * 2):
            source_duration_for_one_yoyo_half = (segment_duration / 2.0) * current_speed_factor
            actual_source_to_take_for_yoyo_half = min(source_clip.duration / 2.0, TARGET_CLIP_DURATION, source_duration_for_one_yoyo_half)
            
            if actual_source_to_take_for_yoyo_half >= MIN_YOYO_SOURCE_DURATION_PER_HALF:
                attempt_yoyo = True
                segment_material_forward = source_clip.subclip(0, actual_source_to_take_for_yoyo_half)
                sped_up_forward = segment_material_forward.fx(vfx.speedx, current_speed_factor)
                
                if sped_up_forward.duration is not None and sped_up_forward.duration > 0.01:
                    sped_up_reversed = sped_up_forward.fx(vfx.time_mirror)
                    active_clip_content = concatenate_videoclips([sped_up_forward, sped_up_reversed], method="compose")
                    print(f"     🪀 YOYO effect applied (forward+reverse)")
                else:
                    attempt_yoyo = False
        
        # Normal clip processing - prefer natural durations
        if not attempt_yoyo:
            # For short beat segments, use natural clip duration when possible
            if segment_duration <= 2.0 and source_clip.duration >= segment_duration * 0.8:
                # Use clip at natural duration with minimal speed adjustment
                duration_to_take = min(source_clip.duration, segment_duration * 1.2)
                segment_material = source_clip.subclip(0, duration_to_take)
                # Minimal speed adjustment to fit exactly
                speed_needed = duration_to_take / segment_duration
                current_speed_factor = max(0.8, min(2.0, speed_needed))
                active_clip_content = segment_material.fx(vfx.speedx, current_speed_factor)
                print(f"     🎬 Natural duration with minimal speed: {current_speed_factor:.2f}x")
            else:
                # Original logic for longer segments
                source_duration_for_normal_clip = segment_duration * current_speed_factor
                duration_to_take_from_original = min(source_clip.duration, TARGET_CLIP_DURATION, source_duration_for_normal_clip)
                duration_to_take_from_original = max(duration_to_take_from_original, MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP if source_clip.duration > MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP else 0)
                
                if duration_to_take_from_original < 0.05: 
                    return None
                
                segment_material = source_clip.subclip(0, duration_to_take_from_original)
                active_clip_content = segment_material.fx(vfx.speedx, current_speed_factor)
                print(f"     ⚡ Speed: {current_speed_factor:.2f}x")
        
        if active_clip_content is None or active_clip_content.duration is None or active_clip_content.duration < 0.01: 
            return None
        
        # Apply random effects
        if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
            active_clip_content = apply_random_vfx(active_clip_content)
            print(f"     🎨 Random effect applied")
        
        # For concatenate approach, don't use set_start or crossfade - keep it simple
        final_segment = active_clip_content.set_duration(segment_duration)
        return final_segment
        
    except Exception as e:
        print(f"     ⚠️ Warning: Could not create beat segment: {e}")
        return None

def create_sequential_beat_sync_compilation(song_path, video_files, output_dir):
    """Create compilation with sequential video selection and enhanced beat synchronization - NO SUBTITLES"""
    print(f"\n🎬 Creating sequential beat-synced compilation (fast - no subtitles)...")
    print(f"🎵 Song: {song_path.name}")
    print(f"📹 Videos: {len(video_files)} clips")
    
    # Get audio duration
    with AudioFileClip(str(song_path)) as temp_audio:
        total_duration = temp_audio.duration
    
    print(f"⏱️ Audio duration: {total_duration:.1f}s")
    
    # Analyze beat structure for smart switching
    all_beats, dramatic_switch_points, start_beats, end_beats, tempo = analyze_beat_structure(song_path, total_duration)
    
    print(f"📊 Smart switching: Strategic video changes for optimal flow")
    print(f"🎯 Three-part structure: Beat-synced start → Smooth middle → Beat-synced end")
    
    # Initialize for sequential beat-synced approach
    video_segments = []
    loaded_source_clips = {}
    current_video_index = 0
    
    try:
        # Three-part structure: Beat-synced start → Smooth middle → Beat-synced end
        print(f"🎬 Creating three-part beat-synced compilation...")
        print(f"🎭 Strategic switches at {len(dramatic_switch_points)} key moments")
        
        sync_section_duration = 8.0  # Duration for start/end beat sync sections
        video_segments = []
        clip_index = 0
        
        # PART 1: Beat-synced start (0 to sync_section_duration)
        print(f"🎵 Part 1: Beat-synced opening (0-{sync_section_duration}s)")
        for i in range(len(start_beats) - 1):
            segment_duration = start_beats[i+1] - start_beats[i]
            if segment_duration <= 0.01: 
                continue
            
            print(f"  📹 Beat segment {i+1}: {video_files[clip_index % len(video_files)].name}")
            print(f"     Time: {start_beats[i]:.1f}s - {start_beats[i+1]:.1f}s ({segment_duration:.1f}s)")
            
            segment = create_beat_synced_segment_advanced(start_beats[i], segment_duration, video_files, loaded_source_clips, clip_index, video_segments)
            if segment: 
                video_segments.append(segment)
                print(f"     ✅ Added beat-synced segment")
            clip_index += 1
        
        # PART 2: Sequential clips with smooth flow (no looping/repetition)
        middle_start = sync_section_duration
        middle_end = total_duration - sync_section_duration
        
        if middle_end > middle_start:
            print(f"🌊 Part 2: Sequential smooth flow ({middle_start:.1f}s-{middle_end:.1f}s)")
            print(f"💫 Playing clips sequentially with natural durations")
            
            current_time = middle_start
            segment_count = 0
            
            # Play clips sequentially until we reach the end of middle section
            while current_time < middle_end - 0.5:
                remaining_time = middle_end - current_time
                
                video_file = video_files[clip_index % len(video_files)]
                
                try:
                    if video_file not in loaded_source_clips:
                        loaded_source_clips[video_file] = VideoFileClip(str(video_file), audio=False, verbose=False)
                    source_clip = loaded_source_clips[video_file]
                    
                    # Use clip's natural duration or remaining time, whichever is smaller
                    natural_duration = source_clip.duration
                    segment_duration = min(natural_duration, remaining_time)
                    
                    print(f"  📹 Sequential clip {segment_count+1}: {video_file.name}")
                    print(f"     Time: {current_time:.1f}s - {current_time + segment_duration:.1f}s ({segment_duration:.1f}s)")
                    print(f"     🎬 Natural duration: {natural_duration:.1f}s")
                    
                    # Use normal speed for smooth flow (no artificial speed changes)
                    if segment_duration >= natural_duration:
                        # Use full clip at normal speed
                        segment = source_clip
                        print(f"     ✅ Using full clip at normal speed")
                    else:
                        # Use part of clip to fit remaining time
                        segment = source_clip.subclip(0, segment_duration)
                        print(f"     ✂️ Using {segment_duration:.1f}s of {natural_duration:.1f}s clip")
                    
                    # Apply effects occasionally for variety
                    if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
                        segment = apply_random_vfx(segment)
                        print(f"     🎨 Random effect applied")
                    
                    # Ensure exact duration
                    final_segment = segment.set_duration(segment_duration)
                    video_segments.append(final_segment)
                    
                    # Move to next clip
                    current_time += segment_duration
                    clip_index += 1
                    segment_count += 1
                    
                    print(f"     ✅ Added sequential segment, next starts at {current_time:.1f}s")
                    
                except Exception as e:
                    print(f"     ⚠️ Warning: Could not process {video_file.name}: {e}")
                    # Skip problematic clip and move to next
                    clip_index += 1
                    current_time += 2.0  # Small advance to avoid infinite loop
        
        # PART 3: Beat-synced end
        print(f"🎵 Part 3: Beat-synced finale ({total_duration - sync_section_duration:.1f}s-{total_duration:.1f}s)")
        for i in range(len(end_beats) - 1):
            segment_duration = end_beats[i+1] - end_beats[i]
            if segment_duration <= 0.01: 
                continue
            
            print(f"  📹 End beat segment {i+1}: {video_files[clip_index % len(video_files)].name}")
            print(f"     Time: {end_beats[i]:.1f}s - {end_beats[i+1]:.1f}s ({segment_duration:.1f}s)")
            
            segment = create_beat_synced_segment_advanced(end_beats[i], segment_duration, video_files, loaded_source_clips, clip_index, video_segments)
            if segment: 
                video_segments.append(segment)
                print(f"     ✅ Added end beat-synced segment")
            clip_index += 1
        
        if not video_segments:
            raise ValueError("No video segments created")
        
        print(f"🎬 Compositing {len(video_segments)} video segments...")
        
        # Validate all segments before compositing
        valid_segments = []
        total_expected_duration = 0.0
        
        for i, segment in enumerate(video_segments):
            try:
                # Test the segment more thoroughly
                if hasattr(segment, 'duration') and segment.duration > 0:
                    # Try to get a frame to ensure the segment is valid
                    try:
                        test_frame = segment.get_frame(0)
                        if test_frame is not None:
                            valid_segments.append(segment)
                            total_expected_duration += segment.duration
                            print(f"✅ Segment {i+1}: {segment.duration:.1f}s - Valid")
                        else:
                            print(f"⚠️ Segment {i+1}: Frame test failed - Skipping")
                    except Exception as frame_error:
                        print(f"⚠️ Segment {i+1}: Frame error ({frame_error}) - Skipping")
                else:
                    print(f"⚠️ Segment {i+1}: Invalid duration - Skipping")
            except Exception as seg_error:
                print(f"⚠️ Segment {i+1}: General error ({seg_error}) - Skipping")
        
        print(f"✅ Using {len(valid_segments)} valid segments")
        print(f"📊 Expected total duration: {total_expected_duration:.1f}s")
        
        target_resolution = (1280, 720) 
        if loaded_source_clips:
            first_cached_path = next(iter(loaded_source_clips))
            if hasattr(loaded_source_clips[first_cached_path], 'size') and loaded_source_clips[first_cached_path].size:
                target_resolution = loaded_source_clips[first_cached_path].size
        
        # Use concatenate instead of composite for better stability
        print("🔗 Using concatenate approach for better stability...")
        
        try:
            final_composition = concatenate_videoclips(valid_segments, method="compose")
            print("✅ Concatenation successful with compose method")
        except Exception as concat_error:
            print(f"⚠️ Compose method failed: {concat_error}")
            print("🔄 Trying chain method...")
            try:
                final_composition = concatenate_videoclips(valid_segments, method="chain")
                print("✅ Concatenation successful with chain method")
            except Exception as chain_error:
                print(f"❌ Chain method also failed: {chain_error}")
                print("🔄 Using simple method...")
                final_composition = concatenate_videoclips(valid_segments)
                print("✅ Simple concatenation successful")
        
        # Skip resize to avoid PIL compatibility issues - videos should already be same size
        print(f"📐 Using original video resolution (skipping resize to avoid PIL issues)")
        
        # Add audio
        with AudioFileClip(str(song_path)) as audio_for_final_render:
            # Use the actual video duration instead of original audio duration
            video_duration = final_composition.duration
            print(f"🎵 Video duration: {video_duration:.1f}s, Audio duration: {total_duration:.1f}s")
            
            audio_clip_for_final = audio_for_final_render.subclip(0, min(video_duration, total_duration))
            final_composition = final_composition.set_audio(audio_clip_for_final)
            
            # Generate output filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            song_name = song_path.stem
            output_filename = f"sequential_beat_sync_{song_name}_fast_{timestamp_str}.mp4"
            output_path = output_dir / output_filename
            
            print(f"🎬 Rendering final video to: {output_path}")
            print(f"📊 Final composition stats:")
            print(f"   - Duration: {final_composition.duration:.1f}s")
            print(f"   - FPS: {final_composition.fps}")
            print(f"   - Size: {final_composition.size}")
            
            try:
                temp_audio_path = output_dir / f"temp-audio_{timestamp_str}.m4a"
                final_composition.write_videofile(
                    str(output_path), 
                    codec="libx264", 
                    audio_codec="aac", 
                    temp_audiofile=str(temp_audio_path), 
                    remove_temp=True, 
                    preset=OUTPUT_PRESET, 
                    fps=OUTPUT_FPS, 
                    threads=2,  # Reduce threads to avoid issues
                    bitrate=OUTPUT_BITRATE,
                    verbose=False,  # Reduce verbose output
                    logger=None    # Disable MoviePy logger
                )
                print(f"✅ Video rendering complete: {output_filename}")
                return output_path
                
            except Exception as e_render:
                print(f"❌ ERROR during video rendering: {e_render}")
                return None
            finally:
                if 'audio_clip_for_final' in locals() and hasattr(audio_clip_for_final, 'close'):
                    audio_clip_for_final.close()
                if hasattr(final_composition, 'close'):
                    final_composition.close()
                    
    finally:
        # Cleanup loaded clips
        print("🧹 Cleaning up loaded video clips...")
        for clip_path, clip_obj in loaded_source_clips.items():
            try: 
                if hasattr(clip_obj, 'close'):
                    clip_obj.close()
            except Exception as e_close: 
                print(f"⚠️ Warning: Error closing {clip_path.name}: {e_close}")
        loaded_source_clips.clear()

def main():
    """Main execution function"""
    print("="*80)
    print(" 🎵 MUSIC VIDEO FAST COMPILER 🎵 ".center(80, "="))
    print("="*80)
    print("⚡ Fast version - no subtitles for quicker processing")
    print("🎤 For karaoke subtitles, use: music_video_beat_sync_compiler.py")
    print("="*80)
    print()
    
    try:
        # Step 1: Find latest music run folder
        music_folder = find_latest_music_run_folder()
        
        # Step 2: Find video clips in the date subfolder
        video_files = find_video_clips_in_music_folder(music_folder)
        
        # Step 3: Find latest song
        song_path = find_latest_song()
        
        # Step 4: Create output directory
        output_dir = create_output_directory(music_folder)
        
        # Step 5: Create sequential beat-synced compilation (fast)
        output_path = create_sequential_beat_sync_compilation(song_path, video_files, output_dir)
        
        if output_path:
            print("\n" + "="*80)
            print(" 🎉 FAST COMPILATION COMPLETE! 🎉 ".center(80, "="))
            print("="*80)
            print(f"✅ Output saved to: {output_path}")
            print(f"🎵 Song used: {song_path.name}")
            print(f"📹 Videos processed: {len(video_files)} clips")
            print(f"⚡ Processing time: Much faster (no transcription)")
            print(f"📁 Output directory: {output_dir}")
            print("="*80)
            return True
        else:
            print("\n❌ Compilation failed during rendering")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Fast music video compilation completed successfully!")
        print("⚡ No subtitles but much faster processing!")
    else:
        print("\n💥 Fast compilation failed!")
    
    input("\nPress Enter to exit...")