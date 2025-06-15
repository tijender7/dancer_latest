import os
import glob
import librosa
import numpy as np
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)
from tqdm import tqdm  # For progress bars

# --- Configuration ---
AUDIO_FILE_PATH = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\music.mp3"
VIDEO_CLIPS_FOLDER = r"H:\dancers_content\Run_20250603_141231\all_videos\250603"
OUTPUT_VIDEO_PATH = r"H:\dancers_content\Run_20250602_145116\all_videos\cpmpiled\output_beat_synced_video.mp4"
TARGET_CLIP_DURATION = 5.0
BEAT_AGGRESSION = 1.1  # (Not used directly; kept for future tweaks)
USE_EVERY_NTH_BEAT = 1  # Use all beats (set >1 to subsample)

# --- Helper Functions ---
def get_video_files(folder_path):
    """Gets a sorted list of video files from a folder."""
    extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv")
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(folder_path, ext)))
    files.sort()
    if not files:
        raise ValueError(f"No video files found in {folder_path}")
    return files

def detect_beats(audio_path, tightness_param=100):
    """Detects beat timestamps in an audio file."""
    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path)
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)

    # Handle if librosa returns an array for tempo
    actual_tempo_for_print = 0.0
    if isinstance(tempo, np.ndarray):
        if tempo.size == 1:
            actual_tempo_for_print = tempo.item()
        elif tempo.size > 0:
            actual_tempo_for_print = tempo[0]
            print(f"Info: Multiple tempos detected by librosa: {tempo}. Using first ({actual_tempo_for_print:.2f} BPM).")
        else:
            print("Info: librosa.beat.beat_track returned an empty array for tempo.")
    elif isinstance(tempo, (int, float)):
        actual_tempo_for_print = tempo
    else:
        print(f"Info: Non-numeric tempo returned: {tempo} (type: {type(tempo)}).")

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"Detected {len(beat_times)} beats. Tempo: {actual_tempo_for_print:.2f} BPM")

    # Ensure a beat at time 0.0
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
        print("Adjusted beats to include time 0.0")

    return beat_times

# --- Main Logic ---
if __name__ == "__main__":
    # Ensure output directory exists
    output_dir = os.path.dirname(OUTPUT_VIDEO_PATH)
    if output_dir and not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)

    # Validate inputs
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"ERROR: Audio file not found at {AUDIO_FILE_PATH}")
        exit()
    if not os.path.isdir(VIDEO_CLIPS_FOLDER):
        print(f"ERROR: Video clips folder not found at {VIDEO_CLIPS_FOLDER}")
        exit()

    # 1. Detect Beats
    beat_times = detect_beats(AUDIO_FILE_PATH)  # default tightness=100
    if USE_EVERY_NTH_BEAT > 1:
        beat_times = beat_times[::USE_EVERY_NTH_BEAT]
        print(f"Using every {USE_EVERY_NTH_BEAT}th beat → {len(beat_times)} beats selected.")

    if len(beat_times) < 2:
        print("ERROR: Not enough beats detected. Try adjusting parameters or check the audio.")
        exit()

    # 2. Get Video Clips
    video_file_paths = get_video_files(VIDEO_CLIPS_FOLDER)
    print(f"Found {len(video_file_paths)} video clips.")
    if not video_file_paths:
        exit()

    # 3. Synchronize and Prepare Video Segments (with 1.5× speed)
    video_segments = []
    clip_idx = 0

    print("Preparing video segments (sped-up at 1.5×)...")
    for i in tqdm(range(len(beat_times))):
        beat_start_time = beat_times[i]

        if i < len(beat_times) - 1:
            beat_end_time = beat_times[i + 1]
        else:
            # Last beat → extend to end of the audio
            with AudioFileClip(AUDIO_FILE_PATH) as temp_audio_for_duration:
                beat_end_time = temp_audio_for_duration.duration
            if beat_end_time <= beat_start_time:
                # Fallback small segment
                beat_end_time = beat_start_time + (TARGET_CLIP_DURATION / 2)

        segment_duration_on_timeline = beat_end_time - beat_start_time
        if segment_duration_on_timeline <= 0.01:
            print(f"Skipping very short segment at beat {i + 1} (duration: {segment_duration_on_timeline:.3f}s)")
            continue

        source_video_path = video_file_paths[clip_idx % len(video_file_paths)]
        source_clip_object = None
        try:
            # Load the video & speed it up
            source_clip_object = VideoFileClip(source_video_path)
            source_clip_object = source_clip_object.fx(vfx.speedx, 1.5)

            # Extract up to TARGET_CLIP_DURATION seconds from the *sped-up* clip
            segment_to_add = source_clip_object.subclip(
                0, min(source_clip_object.duration, TARGET_CLIP_DURATION)
            )
            segment_to_add = segment_to_add.set_start(beat_start_time)
            segment_to_add = segment_to_add.set_duration(segment_duration_on_timeline)

            video_segments.append(segment_to_add)
            # NOTE: Do NOT close source_clip_object here; segment_to_add depends on its reader
        except Exception as e:
            print(f"Warning: Could not load/process {source_video_path}. Skipping. Error: {e}")
            if source_clip_object:
                source_clip_object.close()
        finally:
            clip_idx += 1

    if not video_segments:
        print("ERROR: No video segments created. Check beat detection or video files.")
        exit()

    # 4. Composite Video + Attach Original Audio
    print("Compositing video clips...")
    final_duration = 0.0

    # Compute the maximum end time from segments
    valid_ends = [seg.end for seg in video_segments if seg.end is not None]
    if valid_ends:
        final_duration = max(valid_ends)
    elif beat_times.size > 0:
        final_duration = beat_times[-1]

    with AudioFileClip(AUDIO_FILE_PATH) as original_audio:
        final_duration = max(final_duration, original_audio.duration)

        # Determine a target resolution (use resolution of first valid segment or first clip)
        target_resolution = None
        for seg in video_segments:
            if hasattr(seg, 'size') and seg.size:
                target_resolution = seg.size
                break

        if target_resolution is None and video_file_paths:
            try:
                with VideoFileClip(video_file_paths[0]) as temp_clip:
                    target_resolution = temp_clip.size
            except Exception as e:
                print(f"Could not get resolution from clips: {e}. Defaulting to 1920×1080.")
                target_resolution = (1920, 1080)
        elif target_resolution is None:
            print("Could not determine resolution. Defaulting to 1920×1080.")
            target_resolution = (1920, 1080)

        print(f"Using target resolution: {target_resolution}")

        # Resize segments if needed
        resized_segments = []
        for seg_idx, seg in enumerate(video_segments):
            if not (hasattr(seg, 'get_frame') and hasattr(seg, 'set_position')):
                print(f"Warning: Item at video_segments[{seg_idx}] is not a valid clip. Skipping.")
                continue
            if hasattr(seg, 'reader') and seg.reader is None:
                print(f"Warning: Segment {seg_idx} has a None reader before resizing. Skipping.")
                continue

            if hasattr(seg, 'size') and seg.size and seg.size != target_resolution:
                try:
                    resized_segments.append(seg.resize(target_resolution))
                except Exception as e:
                    filename_attr = getattr(seg, 'filename', 'unknown')
                    print(f"Warning: Could not resize segment from {filename_attr}. Error: {e}. Skipping.")
            else:
                resized_segments.append(seg)

        if not resized_segments:
            print("ERROR: No valid video segments to composite after resizing. Exiting.")
            exit()

        # Create the composite clip
        final_composition = CompositeVideoClip(resized_segments, size=target_resolution)
        final_composition = final_composition.set_duration(final_duration)

        # Re-open audio for final composition
        with AudioFileClip(AUDIO_FILE_PATH) as audio_for_final:
            audio_clip_for_final = audio_for_final.subclip(0, final_duration)
            final_composition = final_composition.set_audio(audio_clip_for_final)

            # 5. Render out the final video
            print(f"Rendering final video to: {OUTPUT_VIDEO_PATH}")
            try:
                final_composition.write_videofile(
                    OUTPUT_VIDEO_PATH,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True,
                    preset="medium",
                    fps=24,  # Hardcoded, but can be made configurable if needed
                    threads=os.cpu_count() or 2
                )
                print("✅ Video rendering complete!")
            except Exception as e:
                print(f"ERROR during video rendering: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Clean up/close all opened clip readers to release resources
                print("Closing video segment resources...")
                all_clips_to_close = set()
                for seg_list in (video_segments, resized_segments):
                    for seg_obj in seg_list:
                        if hasattr(seg_obj, 'close'):
                            all_clips_to_close.add(seg_obj)
                for seg_obj in all_clips_to_close:
                    try:
                        seg_obj.close()
                    except Exception:
                        pass

                if 'audio_clip_for_final' in locals() and hasattr(audio_clip_for_final, 'close'):
                    audio_clip_for_final.close()

                print("Resource cleanup finished.")
