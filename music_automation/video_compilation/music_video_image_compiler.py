#!/usr/bin/env python3
"""
Music Video Image Compiler with Beat Synchronization
==================================================

This script creates a music video using 4 approved images instead of video clips:
1. Finds the latest Run_*_music_images folder with approved images from Telegram
2. Selects 4 approved images from the approved_images_for_video folder
3. Creates a 4-segment video where each image displays for 25% of the song duration
4. Applies beat-synchronized visual effects (zoom, dribble, smooth transitions)
5. Each image gets dynamic effects timed to the music beats during its segment

Workflow Integration:
- Works with existing: run_pipeline_music.py → Telegram approval → this compiler
- Input: approved_images_for_video/ folder (populated by Telegram approval)
- Output: Beat-synced video with image transitions

Author: Claude Code Assistant  
Date: 2025-06-22
"""

import os
import glob
import random
import shutil
from datetime import datetime
from pathlib import Path

# Try to import optional dependencies
try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
    print("✅ librosa imported - beat detection enabled")
except ImportError:
    LIBROSA_AVAILABLE = False
    print("⚠️ librosa not available - using simple timing instead")
    print("   Install with: pip install librosa")

try:
    # Fix PIL compatibility issue first
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
        print("🔧 Fixed PIL.Image.ANTIALIAS compatibility")
    
    from moviepy.editor import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        CompositeVideoClip,
        vfx,
        concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
    print("✅ moviepy imported successfully")
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("⚠️ moviepy not available")
    print("   Install with: pip install moviepy")

try:
    import cv2
    CV2_AVAILABLE = True
    print("✅ opencv imported for smooth zoom")
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ opencv not available - using fallback zoom")
    print("   Install with: pip install opencv-python")

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Create simple fallback
    def tqdm(iterable, desc="Processing"):
        return iterable

# --- Configuration ---
DANCERS_CONTENT_BASE = Path("H:/dancers_content")
SONGS_DIR = Path("D:/Comfy_UI_V20/ComfyUI/output/dancer/songs")
OUTPUT_FOLDER_NAME = "music_video_compiled"

# --- Beat Sync Settings ---
TARGET_IMAGES = 6  # Now 6 images for 6 segments
ENABLE_BEAT_EFFECTS = False  # Disable all beat effects - no flickering/dribbling
CROSSFADE_DURATION = 0.5  # Smooth transitions only
OUTPUT_FPS = 24
OUTPUT_PRESET = "medium"
OUTPUT_BITRATE = "5000k"

# --- Image Effect Settings ---
ZOOM_INTENSITY = 1.4  # Zoom level for face focus
SMOOTH_ZOOM_CYCLES = 1.5  # Slower zoom cycles for smoother motion
# Face focus point - where all zoom effects converge (center-top for face)
FACE_FOCUS_X = 0.5  # Center horizontally
FACE_FOCUS_Y = 0.3  # Upper third vertically (face area)

def find_latest_music_run_folder():
    """Find the most recent Run_*_music_images folder WITH approved images"""
    print("🔍 Searching for latest music run folder with approved images...")
    
    # Look in multiple possible locations
    script_dir = Path(__file__).resolve().parent
    search_paths = [
        script_dir / "output_runs_music",  # Local output_runs_music folder
        DANCERS_CONTENT_BASE,  # H:/dancers_content
        script_dir.parent / "output" / "dancer" / "output_runs_music"  # Alternative path
    ]
    
    music_folders = []
    for search_path in search_paths:
        if search_path.exists():
            pattern = str(search_path / "Run_*_music_images")
            found_folders = glob.glob(pattern)
            music_folders.extend(found_folders)
            if found_folders:
                print(f"   🔍 Found {len(found_folders)} folders in: {search_path}")
    
    if not music_folders:
        print("❌ No Run_*_music_images folders found in any of these locations:")
        for path in search_paths:
            print(f"   - {path} (exists: {path.exists()})")
        raise FileNotFoundError("No Run_*_music_images folders found")
    
    # Sort by modification time, newest first
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    
    # Find the most recent folder that has approved images
    for folder_path in music_folders:
        folder = Path(folder_path)
        approved_dir = folder / "approved_images_for_video"
        
        if approved_dir.exists():
            # Check if it has any approved images
            image_extensions = ["*.png", "*.jpg", "*.jpeg"]
            has_images = False
            for ext in image_extensions:
                if list(approved_dir.glob(ext)):
                    has_images = True
                    break
            
            if has_images:
                print(f"✅ Found latest music run with approved images: {folder.name}")
                print(f"   Full path: {folder}")
                print(f"   Modified: {datetime.fromtimestamp(folder.stat().st_mtime)}")
                return folder
    
    # If no folder with approved images found, use the latest one anyway
    latest_folder = Path(music_folders[0])
    print(f"⚠️ No folders with approved images found, using latest: {latest_folder.name}")
    print(f"   Full path: {latest_folder}")
    print(f"   Modified: {datetime.fromtimestamp(latest_folder.stat().st_mtime)}")
    
    return latest_folder

def find_approved_images(music_folder):
    """Find approved images from the Telegram approval process"""
    print(f"🖼️ Searching for approved images in: {music_folder.name}")
    
    # Check for approved images folder
    approved_dir = music_folder / "approved_images_for_video"
    if not approved_dir.exists():
        raise FileNotFoundError(f"approved_images_for_video directory not found in {music_folder}")
    
    # Get all approved image files
    image_extensions = ["*.png", "*.jpg", "*.jpeg"]
    approved_images = []
    
    for ext in image_extensions:
        approved_images.extend(approved_dir.glob(ext))
    
    if not approved_images:
        raise FileNotFoundError(f"No approved images found in {approved_dir}")
    
    # Sort by filename for consistent ordering
    approved_images.sort()
    
    print(f"✅ Found {len(approved_images)} approved images")
    for i, img in enumerate(approved_images[:10], 1):  # Show first 10
        print(f"   {i}. {img.name}")
    if len(approved_images) > 10:
        print(f"   ... and {len(approved_images) - 10} more")
    
    return approved_images

def select_six_images(approved_images):
    """Select exactly 6 images for the 6-segment video"""
    print(f"🎯 Selecting 6 images from {len(approved_images)} approved images...")
    
    if len(approved_images) == 0:
        raise ValueError("No approved images available")
    elif len(approved_images) == 1:
        # Use the same image 6 times
        selected = [approved_images[0]] * 6
        print("   ⚠️ Only 1 image available - using it for all 6 segments")
    elif len(approved_images) == 2:
        # Use each image 3 times alternating
        selected = [approved_images[0], approved_images[1], approved_images[0], 
                   approved_images[1], approved_images[0], approved_images[1]]
        print("   📋 2 images available - using each 3 times")
    elif len(approved_images) == 3:
        # Use each image twice
        selected = [approved_images[0], approved_images[1], approved_images[2], 
                   approved_images[0], approved_images[1], approved_images[2]]
        print("   📋 3 images available - using each twice")
    elif len(approved_images) < 6:
        # Repeat images to fill 6 segments
        selected = []
        for i in range(6):
            selected.append(approved_images[i % len(approved_images)])
        print(f"   📋 {len(approved_images)} images available - repeating to fill 6 segments")
    else:
        # Select 6 evenly spaced images from the collection
        if LIBROSA_AVAILABLE:
            # Use numpy if available
            indices = np.linspace(0, len(approved_images) - 1, 6, dtype=int)
        else:
            # Simple spacing without numpy
            step = len(approved_images) // 6
            indices = [0, step, step*2, step*3, step*4, step*5]
            # Ensure we don't exceed the list bounds
            indices = [min(i, len(approved_images) - 1) for i in indices]
        selected = [approved_images[i] for i in indices]
        print(f"   📋 Selected 6 images from {len(approved_images)} available:")
    
    for i, img in enumerate(selected, 1):
        print(f"   Segment {i}: {img.name}")
    
    return selected

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

def detect_beats(audio_path):
    """Detect beats in the audio file using librosa (or simple timing if unavailable)"""
    print(f"🥁 Analyzing beats in: {audio_path.name}")
    
    if not LIBROSA_AVAILABLE:
        print("   ⚠️ Using simple timing (no beat detection)")
        # Create simple beat timing - assume 120 BPM
        with AudioFileClip(str(audio_path)) as temp_audio:
            duration = temp_audio.duration
        
        beat_interval = 60.0 / 120.0  # 120 BPM = 0.5s per beat
        beat_times = []
        t = 0.0
        while t < duration:
            beat_times.append(t)
            t += beat_interval
        
        beat_times = np.array(beat_times) if LIBROSA_AVAILABLE else beat_times
        tempo = 120.0
        
        print(f"✅ Generated {len(beat_times)} beats at 120 BPM")
        return beat_times, tempo
    
    # Use librosa for proper beat detection
    y, sr = librosa.load(str(audio_path))
    
    # Detect beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=100, trim=False)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    # Ensure beat at time 0
    if len(beat_times) == 0 or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
    
    # Handle tempo formatting (might be array or scalar)
    if isinstance(tempo, np.ndarray):
        if tempo.size == 1:
            tempo_value = tempo.item()
        elif tempo.size > 0:
            tempo_value = tempo[0]
        else:
            tempo_value = 120.0  # fallback
    else:
        tempo_value = float(tempo)
    
    print(f"✅ Detected {len(beat_times)} beats")
    print(f"   Tempo: {tempo_value:.1f} BPM")
    print(f"   Average beat interval: {np.mean(np.diff(beat_times)):.2f}s")
    
    return beat_times, tempo_value

def create_output_directory(music_folder):
    """Create the output directory for compiled video"""
    # Always use H:\dancers_content path for output, regardless of where we found the images
    music_folder_name = music_folder.name
    h_drive_base = Path("H:/dancers_content")
    
    if h_drive_base.exists():
        # Use H:\dancers_content if it exists
        output_base = h_drive_base / music_folder_name
        if output_base.exists():
            output_dir = output_base / "all_videos" / OUTPUT_FOLDER_NAME
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created output directory: {output_dir}")
            return output_dir
    
    # Fallback to the found music folder location
    output_dir = music_folder / "all_videos" / OUTPUT_FOLDER_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Created output directory: {output_dir}")
    return output_dir

def create_smooth_face_zoom_effects(image_clip, segment_index, segment_duration):
    """Apply combined multi-directional zoom that focuses on face (center-top)"""
    print(f"   🎨 Applying combined zoom (left+right+bottom → face) for segment {segment_index + 1}")
    
    import math
    
    if CV2_AVAILABLE:
        # Create combined multi-directional zoom animation with OpenCV
        def combined_face_zoom_transform(get_frame, t):
            frame = get_frame(t)
            
            # Calculate smooth zoom factor using sinusoidal function
            cycle_progress = (t / segment_duration) * SMOOTH_ZOOM_CYCLES * 2 * 3.14159
            zoom_factor = 1.0 + (ZOOM_INTENSITY - 1.0) * (0.5 + 0.5 * math.sin(cycle_progress))
            
            import cv2
            h, w = frame.shape[:2]
            
            if zoom_factor > 1.0:  # Zooming in towards face
                new_h, new_w = int(h * zoom_factor), int(w * zoom_factor)
                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                
                # Calculate where the face should be in the enlarged image
                face_pixel_x = int(FACE_FOCUS_X * new_w)
                face_pixel_y = int(FACE_FOCUS_Y * new_h)
                
                # Calculate zoom progress (0 = zoomed out, 1 = fully zoomed in on face)
                zoom_progress = (zoom_factor - 1.0) / (ZOOM_INTENSITY - 1.0)  # 0 to 1
                
                # COMBINED ZOOM EFFECT:
                # Start position combines all directions (left + right + bottom)
                # When zoomed out (zoom_progress = 0): show wider view from combined perspective
                # When zoomed in (zoom_progress = 1): focused on face (center-top)
                
                # Horizontal positioning: blend from wider view toward face center (left+right effect)
                # When zoomed out: show more of left+right (centered but wider)
                # When zoomed in: focus on face horizontally
                face_target_x = face_pixel_x - w//2  # Face centered horizontally
                wider_view_x = int(new_w//2 - w//2)  # Centered but showing wider view when zoomed out
                start_x = int(wider_view_x * (1 - zoom_progress) + face_target_x * zoom_progress)
                
                # Vertical positioning: blend from bottom toward face (bottom effect)  
                # When zoom_progress = 0: start from bottom area (show more bottom content)
                # When zoom_progress = 1: focus on face area (upper portion)
                bottom_start_y = new_h - h  # Bottom position when zoomed out
                face_target_y = face_pixel_y - h//2  # Face position when zoomed in
                start_y = int(bottom_start_y * (1 - zoom_progress) + face_target_y * zoom_progress)
                
                # Ensure crop bounds are valid
                start_x = max(0, min(start_x, new_w - w))
                start_y = max(0, min(start_y, new_h - h))
                
                cropped = resized[start_y:start_y + h, start_x:start_x + w]
                return cropped
                
            else:  # Zooming out from face
                new_h, new_w = int(h * zoom_factor), int(w * zoom_factor)
                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                
                # Center the smaller image when zooming out
                pad_y, pad_x = (h - new_h) // 2, (w - new_w) // 2
                padded = cv2.copyMakeBorder(resized, pad_y, h - new_h - pad_y, 
                                           pad_x, w - new_w - pad_x, cv2.BORDER_CONSTANT, value=[0,0,0])
                return padded
        
        final_clip = image_clip.fl(combined_face_zoom_transform, apply_to=['mask']).set_duration(segment_duration)
        
    else:
        # Fallback: Use MoviePy's resize (simpler but still smooth)
        def zoom_resize_func(t):
            cycle_progress = (t / segment_duration) * SMOOTH_ZOOM_CYCLES * 2 * 3.14159
            zoom_factor = 1.0 + (ZOOM_INTENSITY - 1.0) * (0.5 + 0.5 * math.sin(cycle_progress))
            return zoom_factor
        
        final_clip = image_clip.resize(zoom_resize_func).set_duration(segment_duration)
    
    print(f"   🎯 Applied combined zoom → face focus ({FACE_FOCUS_X:.1f}, {FACE_FOCUS_Y:.1f})")
    return final_clip

def create_image_based_compilation(song_path, selected_images, output_dir):
    """Create compilation video using 6 approved images with smooth face-focused zoom"""
    print(f"\n🎬 Creating 6-segment image compilation with smooth zoom...")
    print(f"🎵 Song: {song_path.name}")
    print(f"🖼️ Images: {len(selected_images)} selected")
    
    # Get audio duration
    with AudioFileClip(str(song_path)) as temp_audio:
        total_duration = temp_audio.duration
    
    print(f"⏱️ Audio duration: {total_duration:.1f}s")
    
    # Calculate segment duration (1/6 each = ~16.67% each)
    segment_duration = total_duration / 6
    print(f"📊 Segment duration: {segment_duration:.1f}s each (~{100/6:.1f}% per image)")
    
    # Create image segments
    image_segments = []
    
    try:
        for i, image_path in enumerate(selected_images):
            segment_start = i * segment_duration
            print(f"\n📹 Processing segment {i+1}/6: {image_path.name}")
            print(f"   Time: {segment_start:.1f}s - {segment_start + segment_duration:.1f}s")
            
            # Load image as clip
            image_clip = ImageClip(str(image_path))
            
            # Apply smooth face-focused zoom (NO beat effects, NO flickering)
            processed_clip = create_smooth_face_zoom_effects(
                image_clip, i, segment_duration
            )
            
            # Set timing
            final_clip = processed_clip.set_start(segment_start).set_duration(segment_duration)
            
            # Add smooth crossfade transitions (except first segment)
            if i > 0 and CROSSFADE_DURATION > 0:
                final_clip = final_clip.crossfadein(CROSSFADE_DURATION)
            
            image_segments.append(final_clip)
            print(f"   ✅ Segment {i+1} prepared")
        
        print(f"\n🎬 Compositing {len(image_segments)} image segments...")
        
        # Determine output resolution (use first image's resolution)
        with ImageClip(str(selected_images[0])) as temp_clip:
            target_resolution = temp_clip.size
        
        print(f"📐 Output resolution: {target_resolution[0]}x{target_resolution[1]}")
        
        # Create final composition
        final_composition = CompositeVideoClip(image_segments, size=target_resolution).set_duration(total_duration)
        
        # Add audio
        with AudioFileClip(str(song_path)) as audio_for_final_render:
            audio_clip = audio_for_final_render.subclip(0, total_duration)
            final_composition = final_composition.set_audio(audio_clip)
            
            # Generate output filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            song_name = song_path.stem
            output_filename = f"6segment_face_zoom_{song_name}_{timestamp_str}.mp4"
            output_path = output_dir / output_filename
            
            print(f"\n🎬 Rendering final video to: {output_path}")
            
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
                print(f"✅ Video rendering complete: {output_filename}")
                return output_path
                
            except Exception as e_render:
                print(f"❌ ERROR during video rendering: {e_render}")
                return None
            finally:
                if 'audio_clip' in locals() and hasattr(audio_clip, 'close'):
                    audio_clip.close()
                if hasattr(final_composition, 'close'):
                    final_composition.close()
                    
    except Exception as e:
        print(f"❌ ERROR during image processing: {e}")
        return None

def main():
    """Main execution function"""
    print("="*80)
    print(" 🖼️ MUSIC VIDEO IMAGE COMPILER 🖼️ ".center(80, "="))
    print("="*80)
    print("🎨 6-Image Smooth Face-Focused Video Compilation")
    print("📱 Uses approved images from Telegram workflow")
    print("🎯 Face-focused zoom with smooth transitions - NO flickering")
    print("="*80)
    print()
    
    # Check dependencies
    if not MOVIEPY_AVAILABLE:
        print("❌ ERROR: MoviePy is required for video processing")
        print("   Install with: pip install moviepy")
        return False
    
    try:
        # Step 1: Find latest music run folder
        music_folder = find_latest_music_run_folder()
        
        # Step 2: Find approved images from Telegram approval process
        approved_images = find_approved_images(music_folder)
        
        # Step 3: Select exactly 6 images for 6 segments
        selected_images = select_six_images(approved_images)
        
        # Step 4: Find latest song
        song_path = find_latest_song()
        
        # Step 5: Create output directory
        output_dir = create_output_directory(music_folder)
        
        # Step 6: Create image-based compilation with beat sync
        output_path = create_image_based_compilation(song_path, selected_images, output_dir)
        
        if output_path:
            print("\n" + "="*80)
            print(" 🎉 FACE-FOCUSED COMPILATION COMPLETE! 🎉 ".center(80, "="))
            print("="*80)
            print(f"✅ Output saved to: {output_path}")
            print(f"🎵 Song used: {song_path.name}")
            print(f"🖼️ Images processed: {len(selected_images)} (6 segments)")
            print(f"🎯 Smooth face-focused zoom applied - NO flickering")
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
        print("\n🎉 Face-focused music video compilation completed successfully!")
        print("🖼️ 6 images with smooth face-focused zoom - NO flickering!")
    else:
        print("\n💥 Image compilation failed!")
    
    input("\nPress Enter to exit...")