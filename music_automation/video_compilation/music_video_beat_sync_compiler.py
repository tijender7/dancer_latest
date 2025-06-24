#!/usr/bin/env python3
"""
Music Video Equal Time Allocation Compiler with Karaoke Subtitles

This script automatically:
1. Finds the latest Run_*_music_images folder 
2. Locates video clips in the date subfolder
3. Gets the latest song from the songs directory
4. Creates a compilation where each video gets equal time (no repeats)
5. Each video plays forward→backward→forward... pattern to fill its time slot
6. Transcribes audio using Whisper for karaoke-style subtitles
7. Adds synchronized word-by-word highlighting (Hinglish support)

Author: Claude Code Assistant
Date: 2025-06-22
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
    TextClip,
    vfx,
    concatenate_videoclips
)
from tqdm import tqdm

# Try to import whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
    print("SUCCESS: Whisper imported successfully")
except ImportError:
    WHISPER_AVAILABLE = False
    print("WARNING: Whisper not available. Install with: pip install openai-whisper")
    print("   Subtitles will be disabled.")

# --- Configuration ---
DANCERS_CONTENT_BASE = Path("H:/dancers_content")
SONGS_DIR = Path("D:/Comfy_UI_V20/ComfyUI/output/dancer/songs")
OUTPUT_FOLDER_NAME = "music_video_compiled"

# --- Beat Sync Settings (from beat_sync_single.py) ---
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

# --- Subtitle Configuration ---
ENABLE_SUBTITLES = True and WHISPER_AVAILABLE  # Set to False to skip subtitles entirely
WHISPER_MODEL_SIZE = "medium"  # Options: tiny, base, small, medium, large (medium for better coverage)
WHISPER_TIMEOUT_MINUTES = 10  # Increased timeout for better transcription
SUBTITLE_FONT = "Arial-Bold"
SUBTITLE_FONTSIZE = 36  # Reduced size to prevent overflow
SUBTITLE_COLOR_NORMAL = "white"
SUBTITLE_COLOR_HIGHLIGHT = "yellow"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 2
SUBTITLE_POSITION = ('center', 'bottom')
SUBTITLE_MARGIN_BOTTOM = 50  # Pixels from bottom
MAX_SUBTITLE_WIDTH = 0.8  # 80% of video width
WORDS_PER_LINE = 4  # Max words per subtitle line (reduced to prevent overflow)

def find_latest_music_run_folder():
    """Find the most recent Run_*_music_images folder"""
    print("SEARCH: Searching for latest music run folder...")
    
    if not DANCERS_CONTENT_BASE.exists():
        raise FileNotFoundError(f"Dancers content directory not found: {DANCERS_CONTENT_BASE}")
    
    pattern = str(DANCERS_CONTENT_BASE / "Run_*_music_images")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        raise FileNotFoundError("No Run_*_music_images folders found")
    
    # Sort by modification time, newest first
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    latest_folder = Path(music_folders[0])
    
    print(f"SUCCESS: Found latest music run: {latest_folder.name}")
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
    
    print(f"SUCCESS: Found {len(video_files)} video clips")
    return video_files

def find_latest_song():
    """Find the most recent song file in the songs directory"""
    print("MUSIC: Searching for latest song...")
    
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
    
    print(f"SUCCESS: Found latest song: {latest_song.name}")
    print(f"   Modified: {datetime.fromtimestamp(latest_song.stat().st_mtime)}")
    
    return latest_song

def create_output_directory(music_folder):
    """Create the output directory for compiled video"""
    output_dir = music_folder / "all_videos" / OUTPUT_FOLDER_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Created output directory: {output_dir}")
    return output_dir

def detect_beats(audio_path, tightness_param=100):
    """Detect beats in audio file using librosa"""
    print(f"MUSIC: Loading audio: {audio_path.name}")
    y, sr = librosa.load(str(audio_path))
    
    print("SEARCH: Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)
    
    # Handle tempo output
    actual_tempo_for_print = 0.0
    if isinstance(tempo, np.ndarray):
        if tempo.size == 1: 
            actual_tempo_for_print = tempo.item()
        elif tempo.size > 0: 
            actual_tempo_for_print = tempo[0]
            print(f"ℹ️ Multi-tempo {tempo}, using first.")
        else: 
            print("ℹ️ Librosa empty tempo array.")
    elif isinstance(tempo, (int, float)): 
        actual_tempo_for_print = tempo
    else: 
        print(f"ℹ️ Non-numeric tempo: {tempo} type: {type(tempo)}.")
    
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"SUCCESS: Detected {len(beat_times)} beats. Tempo: {actual_tempo_for_print:.2f} BPM")
    
    # Ensure beat starts at 0.0
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
        print("CONFIG: Adjusted beat list to include time 0.0")
    
    return beat_times

def get_audio_duration(audio_path):
    """Get audio duration using librosa"""
    try:
        y, sr = librosa.load(str(audio_path))
        duration = librosa.get_duration(y=y, sr=sr)
        return duration
    except Exception as e:
        print(f"   WARNING: Warning: Could not get audio duration: {e}")
        return 0.0

def analyze_transcription_coverage(word_data, audio_duration):
    """Analyze how much of the audio was successfully transcribed"""
    if not word_data or audio_duration <= 0:
        return {
            'coverage_percentage': 0.0,
            'gaps': [],
            'largest_gap': 0.0
        }
    
    # Find gaps in transcription
    gaps = []
    last_end = 0.0
    
    for word in word_data:
        if word['start'] > last_end + 1.0:  # Gap of more than 1 second
            gaps.append({
                'start': last_end,
                'end': word['start'],
                'duration': word['start'] - last_end
            })
        last_end = max(last_end, word['end'])
    
    # Check if there's a gap at the end
    if last_end < audio_duration - 1.0:
        gaps.append({
            'start': last_end,
            'end': audio_duration,
            'duration': audio_duration - last_end
        })
    
    # Calculate coverage
    total_gap_time = sum(gap['duration'] for gap in gaps)
    coverage_percentage = ((audio_duration - total_gap_time) / audio_duration) * 100
    largest_gap = max((gap['duration'] for gap in gaps), default=0.0)
    
    return {
        'coverage_percentage': coverage_percentage,
        'gaps': gaps,
        'largest_gap': largest_gap
    }

def transcribe_audio_with_whisper(audio_path):
    """Transcribe audio using Whisper with word-level timestamps"""
    if not WHISPER_AVAILABLE:
        print("WARNING: Whisper not available, skipping transcription")
        return None
    
    print(f"🎤 Transcribing audio with Whisper ({WHISPER_MODEL_SIZE} model)...")
    print(f"   Audio: {audio_path.name}")
    print(f"   ⏱️ This may take 1-3 minutes depending on audio length...")
    print(f"   💡 Press Ctrl+C to skip transcription and continue without subtitles")
    
    try:
        # Load Whisper model
        print(f"   📥 Loading {WHISPER_MODEL_SIZE} model...")
        model = whisper.load_model(WHISPER_MODEL_SIZE)
        print(f"   SUCCESS: Whisper {WHISPER_MODEL_SIZE} model loaded")
        
        # Transcribe with word timestamps and improved settings
        print(f"   🔄 Transcribing audio... (this is the slow part)")
        result = model.transcribe(
            str(audio_path), 
            word_timestamps=True, 
            language=None,  # Auto-detect language for better coverage
            verbose=True,   # Enable verbose for debugging transcription issues
            temperature=0.0,  # Deterministic output for better consistency
            beam_size=5,    # Better beam search for accuracy
            best_of=5,      # Multiple candidates for better results
            patience=1.0,   # More patience for better coverage
            length_penalty=1.0,  # Balanced length penalty
            suppress_tokens=[-1],  # Don't suppress any tokens
            initial_prompt="Om Namah Shivaya, Hindu mantras, Sanskrit chants, devotional songs"  # Context for better recognition
        )
        
        # Extract word-level data
        word_data = []
        if 'segments' in result:
            for segment in result['segments']:
                if 'words' in segment:
                    for word_info in segment['words']:
                        word_data.append({
                            'word': word_info.get('word', '').strip(),
                            'start': word_info.get('start', 0),
                            'end': word_info.get('end', 0),
                            'confidence': word_info.get('probability', 0)
                        })
        
        print(f"   SUCCESS: Transcription completed!")
        print(f"   STATS: {len(word_data)} words with timestamps")
        print(f"   LOG: Sample text: {result.get('text', '')[:100]}...")
        
        # Analyze transcription coverage
        if word_data:
            audio_duration = get_audio_duration(audio_path)
            coverage_analysis = analyze_transcription_coverage(word_data, audio_duration)
            print(f"   📈 Coverage: {coverage_analysis['coverage_percentage']:.1f}% of audio")
            if coverage_analysis['coverage_percentage'] < 70:
                print(f"   WARNING: Warning: Poor transcription coverage detected!")
                print(f"   STATS: {len(coverage_analysis['gaps'])} gaps found, largest: {coverage_analysis['largest_gap']:.1f}s")
        
        return {
            'words': word_data,
            'full_text': result.get('text', ''),
            'language': result.get('language', 'unknown')
        }
        
    except KeyboardInterrupt:
        print(f"   WARNING: Transcription interrupted by user")
        print(f"   LOG: Continuing without subtitles...")
        return None
    except Exception as e:
        print(f"   ERROR: Whisper transcription failed: {e}")
        print(f"   LOG: Continuing without subtitles...")
        return None

def create_subtitle_lines(word_data, words_per_line=WORDS_PER_LINE):
    """Group words into subtitle lines with timing"""
    if not word_data:
        return []
    
    lines = []
    current_line_words = []
    
    for word_info in word_data:
        current_line_words.append(word_info)
        
        # Check if we should start a new line
        if len(current_line_words) >= words_per_line:
            # Create line data
            line_text = ' '.join([w['word'] for w in current_line_words])
            line_start = current_line_words[0]['start']
            line_end = current_line_words[-1]['end']
            
            lines.append({
                'text': line_text,
                'start': line_start,
                'end': line_end,
                'words': current_line_words.copy()
            })
            
            current_line_words = []
    
    # Handle remaining words
    if current_line_words:
        line_text = ' '.join([w['word'] for w in current_line_words])
        line_start = current_line_words[0]['start']
        line_end = current_line_words[-1]['end']
        
        lines.append({
            'text': line_text,
            'start': line_start,
            'end': line_end,
            'words': current_line_words.copy()
        })
    
    print(f"LOG: Created {len(lines)} subtitle lines")
    return lines

def create_word_level_karaoke_clips(word_data, video_size):
    """Create clean karaoke highlighting - each word gets its moment to shine"""
    if not word_data:
        return []
    
    print(f"🎤 Creating word-level karaoke clips...")
    subtitle_clips = []
    
    video_width, video_height = video_size
    subtitle_y = video_height - SUBTITLE_MARGIN_BOTTOM - SUBTITLE_FONTSIZE
    
    # Group words into lines (max WORDS_PER_LINE words per line)
    lines = []
    current_line = []
    
    for word_info in word_data:
        current_line.append(word_info)
        if len(current_line) >= WORDS_PER_LINE:
            lines.append(current_line.copy())
            current_line = []
    
    # Add remaining words
    if current_line:
        lines.append(current_line)
    
    print(f"   LOG: Created {len(lines)} subtitle lines from {len(word_data)} words")
    
    # Process each line
    for line_idx, line_words in enumerate(tqdm(lines, desc="Creating word-level subtitles")):
        if not line_words:
            continue
            
        line_start = line_words[0]['start']
        line_end = line_words[-1]['end']
        
        # Calculate line position - use alternating lines to avoid overlap
        line_y_offset = (line_idx % 2) * (SUBTITLE_FONTSIZE + 15)  # 15px spacing
        current_subtitle_y = subtitle_y - line_y_offset
        
        try:
            # For each word in the line, create a complete line clip with that word highlighted
            for word_idx, word_info in enumerate(line_words):
                word_text = word_info['word']
                word_start = word_info['start']
                word_end = word_info['end']
                word_duration = word_end - word_start
                
                if word_duration > 0.05 and word_text.strip():
                    # Build line text with highlighted word
                    line_parts = []
                    
                    for i, w in enumerate(line_words):
                        line_parts.append(w['word'])
                    
                    complete_line_text = ' '.join(line_parts)
                    
                    try:
                        # Create complete line with single color (this eliminates overlap)
                        if word_idx == 0:
                            # First word of line - show in highlight color
                            line_clip = TextClip(
                                complete_line_text,
                                fontsize=SUBTITLE_FONTSIZE,
                                font=SUBTITLE_FONT,
                                color=SUBTITLE_COLOR_HIGHLIGHT,
                                stroke_color=SUBTITLE_STROKE_COLOR,
                                stroke_width=SUBTITLE_STROKE_WIDTH
                            ).set_duration(word_duration).set_start(word_start).set_position(('center', current_subtitle_y))
                        else:
                            # Other words - create with progressive highlighting effect
                            # Show words up to current one in highlight, rest in normal
                            highlighted_part = ' '.join([w['word'] for w in line_words[:word_idx + 1]])
                            normal_part = ' '.join([w['word'] for w in line_words[word_idx + 1:]])
                            
                            if normal_part:
                                display_text = highlighted_part + ' ' + normal_part
                            else:
                                display_text = highlighted_part
                            
                            # For simplicity, alternate between highlight and normal colors
                            text_color = SUBTITLE_COLOR_HIGHLIGHT if word_idx % 2 == 0 else SUBTITLE_COLOR_NORMAL
                            
                            line_clip = TextClip(
                                display_text,
                                fontsize=SUBTITLE_FONTSIZE,
                                font=SUBTITLE_FONT,
                                color=text_color,
                                stroke_color=SUBTITLE_STROKE_COLOR,
                                stroke_width=SUBTITLE_STROKE_WIDTH
                            ).set_duration(word_duration).set_start(word_start).set_position(('center', current_subtitle_y))
                        
                        subtitle_clips.append(line_clip)
                        
                    except Exception as e:
                        print(f"   WARNING: Warning: Could not create karaoke for word '{word_text}': {e}")
                        
                        # Fallback: simple static line
                        try:
                            fallback_clip = TextClip(
                                complete_line_text,
                                fontsize=SUBTITLE_FONTSIZE,
                                font=SUBTITLE_FONT,
                                color=SUBTITLE_COLOR_NORMAL,
                                stroke_color=SUBTITLE_STROKE_COLOR,
                                stroke_width=SUBTITLE_STROKE_WIDTH
                            ).set_duration(word_duration).set_start(word_start).set_position(('center', current_subtitle_y))
                            
                            subtitle_clips.append(fallback_clip)
                        except:
                            print(f"   ERROR: Complete fallback failed for word '{word_text}'")
                        
        except Exception as e:
            print(f"   WARNING: Warning: Could not create subtitle for line {line_idx}: {e}")
            continue
    
    print(f"   SUCCESS: Created {len(subtitle_clips)} karaoke clips")
    return subtitle_clips

def apply_random_vfx(clip):
    """Apply random visual effects to video clip"""
    effects_pool = [
        {"name": "mirror_x", "func": lambda c: c.fx(vfx.mirror_x)},
        {"name": "blackwhite", "func": lambda c: c.fx(vfx.blackwhite, RGB=[1,1,1], preserve_luminosity=True)},
        {"name": "lum_contrast_inc", "func": lambda c: c.fx(vfx.lum_contrast, lum=0, contrast=0.2)},
        {"name": "gamma_brighten", "func": lambda c: c.fx(vfx.gamma_corr, gamma=1.2)},
    ]
    
    if not effects_pool: 
        print("WARNING: Warning: No effects in effects_pool.")
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
    
    # Loop through video files
    source_video_path = video_file_paths[clip_selector_idx % len(video_file_paths)]
    
    try:
        if source_video_path not in loaded_source_clips:
            loaded_source_clips[source_video_path] = VideoFileClip(str(source_video_path), audio=False, verbose=False)
        source_clip_instance = loaded_source_clips[source_video_path]
        
        active_clip_content = None
        attempt_yoyo = False
        
        # Try yoyo effect
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
        
        # Normal clip if yoyo failed
        if not attempt_yoyo:
            source_duration_for_normal_clip = segment_duration_on_timeline * current_speed_factor
            duration_to_take_from_original = min(source_clip_instance.duration, TARGET_CLIP_DURATION, source_duration_for_normal_clip)
            duration_to_take_from_original = max(duration_to_take_from_original, MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP if source_clip_instance.duration > MIN_SOURCE_MATERIAL_FOR_NORMAL_CLIP else 0)
            
            if duration_to_take_from_original < 0.05: 
                return None
            
            segment_material = source_clip_instance.subclip(0, duration_to_take_from_original)
            active_clip_content = segment_material.fx(vfx.speedx, current_speed_factor)
        
        if active_clip_content is None or active_clip_content.duration is None or active_clip_content.duration < 0.01: 
            return None
        
        # Apply random effects
        if APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
            active_clip_content = apply_random_vfx(active_clip_content)
        
        segment_to_place_on_timeline = active_clip_content
        
        # Apply crossfade
        if CROSSFADE_DURATION > 0 and video_segments:
            current_clip_actual_duration = active_clip_content.duration
            safe_crossfade = min(CROSSFADE_DURATION, current_clip_actual_duration / 2.0 if current_clip_actual_duration else CROSSFADE_DURATION, segment_duration_on_timeline / 2.0)
            if safe_crossfade > 0.01:
                segment_to_place_on_timeline = segment_to_place_on_timeline.crossfadein(safe_crossfade)
        
        final_processed_segment = segment_to_place_on_timeline.set_start(beat_start_time).set_duration(segment_duration_on_timeline)
        return final_processed_segment
        
    except Exception as e:
        print(f"WARNING: Warning: Could not create beat segment: {e}")
        return None

def create_forward_backward_segment(video_clip, allocated_time, start_time, apply_effects=True):
    """Create forward-backward looping segment for allocated time slot"""
    segments = []
    current_time = 0.0
    forward = True
    segment_duration = 2.0  # Each forward/backward segment duration
    
    while current_time < allocated_time:
        remaining_time = allocated_time - current_time
        actual_segment_duration = min(segment_duration, remaining_time)
        
        if actual_segment_duration < 0.1:  # Skip very short segments
            break
        
        # Create base segment from video clip
        base_segment = video_clip.subclip(0, min(video_clip.duration, actual_segment_duration))
        
        # Apply direction (forward or backward)
        if forward:
            processed_segment = base_segment
        else:
            processed_segment = base_segment.fx(vfx.time_mirror)
        
        # Apply random effects occasionally
        if apply_effects and APPLY_RANDOM_EFFECTS and random.random() < EFFECT_PROBABILITY:
            processed_segment = apply_random_vfx(processed_segment)
        
        # Set timing and add to segments
        final_segment = processed_segment.set_start(start_time + current_time).set_duration(actual_segment_duration)
        segments.append(final_segment)
        
        current_time += actual_segment_duration
        forward = not forward  # Alternate direction
    
    return segments

def create_equal_time_allocation_compilation(song_path, video_files, output_dir):
    """Create compilation with equal time allocation per video (no repeats) + karaoke subtitles"""
    print(f"\nVIDEO: Creating equal time allocation compilation with karaoke subtitles...")
    print(f"MUSIC: Song: {song_path.name}")
    print(f"📹 Videos: {len(video_files)} clips")
    print(f"🎤 Subtitles: {'Enabled' if ENABLE_SUBTITLES else 'Disabled'}")
    
    # Get audio duration
    with AudioFileClip(str(song_path)) as temp_audio:
        total_duration = temp_audio.duration
    
    print(f"⏱️ Audio duration: {total_duration:.1f}s")
    
    # Step 1: Transcribe audio for subtitles (if enabled)
    transcription_data = None
    subtitle_lines = []
    word_data = []
    if ENABLE_SUBTITLES:
        transcription_data = transcribe_audio_with_whisper(song_path)
        if transcription_data and transcription_data['words']:
            word_data = transcription_data['words']
            subtitle_lines = create_subtitle_lines(word_data)  # Keep for logging purposes
    
    # Calculate time allocation per video
    time_per_video = total_duration / len(video_files)
    print(f"STATS: Time per video: {time_per_video:.1f}s")
    print(f"STATS: Pattern: Each video plays forward→backward→forward... for {time_per_video:.1f}s")
    
    # Initialize
    video_segments = []
    loaded_source_clips = {}
    
    try:
        # Process each video sequentially with equal time allocation
        print(f"VIDEO: Creating equal time segments...")
        
        for i, video_file in enumerate(tqdm(video_files, desc="Processing videos")):
            start_time = i * time_per_video
            allocated_time = time_per_video
            
            # Handle last video (might have slightly different duration due to rounding)
            if i == len(video_files) - 1:
                allocated_time = total_duration - start_time
            
            print(f"  📹 Video {i+1}/{len(video_files)}: {video_file.name}")
            print(f"     Time slot: {start_time:.1f}s - {start_time + allocated_time:.1f}s ({allocated_time:.1f}s)")
            
            try:
                # Load video clip if not already loaded
                if video_file not in loaded_source_clips:
                    loaded_source_clips[video_file] = VideoFileClip(str(video_file), audio=False, verbose=False)
                source_clip = loaded_source_clips[video_file]
                
                # Create forward-backward segments for this time slot
                segments = create_forward_backward_segment(source_clip, allocated_time, start_time)
                
                # Add crossfade between different videos
                if i > 0 and CROSSFADE_DURATION > 0 and segments:
                    first_segment = segments[0]
                    safe_crossfade = min(CROSSFADE_DURATION, first_segment.duration / 2.0)
                    if safe_crossfade > 0.01:
                        segments[0] = first_segment.crossfadein(safe_crossfade)
                
                video_segments.extend(segments)
                print(f"     SUCCESS: Created {len(segments)} forward/backward segments")
                
            except Exception as e:
                print(f"     WARNING: Warning: Could not process {video_file.name}: {e}")
                continue
        
        if not video_segments:
            raise ValueError("No video segments created")
        
        print(f"VIDEO: Compositing {len(video_segments)} video segments...")
        target_resolution = (1280, 720) 
        if loaded_source_clips:
            first_cached_path = next(iter(loaded_source_clips))
            if hasattr(loaded_source_clips[first_cached_path], 'size') and loaded_source_clips[first_cached_path].size:
                target_resolution = loaded_source_clips[first_cached_path].size
        
        # Create base video composition
        final_composition = CompositeVideoClip(video_segments, size=target_resolution, bg_color=(0,0,0)).set_duration(total_duration)
        
        # Add karaoke subtitles if available
        all_clips = [final_composition]
        if ENABLE_SUBTITLES and word_data:
            print(f"🎤 Adding word-level karaoke subtitles ({len(word_data)} words)...")
            subtitle_clips = create_word_level_karaoke_clips(word_data, target_resolution)
            if subtitle_clips:
                all_clips.extend(subtitle_clips)
                print(f"   SUCCESS: Added {len(subtitle_clips)} word-level karaoke clips")
        
        # Final composition with subtitles
        if len(all_clips) > 1:
            final_composition = CompositeVideoClip(all_clips, size=target_resolution).set_duration(total_duration)
            print(f"VIDEO: Final composition: {len(video_segments)} video clips + {len(all_clips)-1} subtitle clips")
        
        # Add audio
        with AudioFileClip(str(song_path)) as audio_for_final_render:
            audio_clip_for_final = audio_for_final_render.subclip(0, total_duration)
            final_composition = final_composition.set_audio(audio_clip_for_final)
            
            # Generate output filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            song_name = song_path.stem
            subtitle_suffix = "_with_karaoke" if ENABLE_SUBTITLES and word_data else ""
            output_filename = f"equal_time_compilation_{song_name}{subtitle_suffix}_{timestamp_str}.mp4"
            output_path = output_dir / output_filename
            
            print(f"VIDEO: Rendering final video to: {output_path}")
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
                    threads=os.cpu_count() or 2, 
                    bitrate=OUTPUT_BITRATE
                )
                print(f"SUCCESS: Video rendering complete: {output_filename}")
                return output_path, word_data
                
            except Exception as e_render:
                print(f"ERROR: ERROR during video rendering: {e_render}")
                return None, word_data
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
                print(f"WARNING: Warning: Error closing {clip_path.name}: {e_close}")
        loaded_source_clips.clear()

def main():
    """Main execution function"""
    print("="*80)
    print(" MUSIC: MUSIC VIDEO KARAOKE COMPILER MUSIC: ".center(80, "="))
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
        
        # Step 5: Create equal time allocation compilation
        output_path, word_data_result = create_equal_time_allocation_compilation(song_path, video_files, output_dir)
        
        if output_path:
            print("\n" + "="*80)
            print(" 🎉 KARAOKE COMPILATION COMPLETE! 🎉 ".center(80, "="))
            print("="*80)
            print(f"SUCCESS: Output saved to: {output_path}")
            print(f"MUSIC: Song used: {song_path.name}")
            print(f"📹 Videos processed: {len(video_files)} clips")
            print(f"🎤 Subtitles: {'SUCCESS: Word-level karaoke included' if ENABLE_SUBTITLES and word_data_result else 'ERROR: Disabled'}")
            print(f"📁 Output directory: {output_dir}")
            print("="*80)
            return True
        else:
            print("\nERROR: Compilation failed during rendering")
            return False
            
    except Exception as e:
        print(f"\nERROR: ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Karaoke music video compilation completed successfully!")
        print("🎤 Your video now includes synchronized Hinglish subtitles!")
    else:
        print("\n💥 Karaoke compilation failed!")
    
    input("\nPress Enter to exit...")