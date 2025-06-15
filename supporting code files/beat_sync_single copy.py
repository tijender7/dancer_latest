import os
import glob
import librosa
import numpy as np
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    vfx
)
from tqdm import tqdm  # For progress bars

# --- Configuration / Dynamic Path Discovery ---

# 1. Base directory where all "Run_YYYYMMDD_HHMMSS" folders live:
BASE_DANCERS_DIR = r"H:\dancers_content"
RUN_PREFIX = "Run_"

# 2. Audio path is still fixed:
AUDIO_FILE_PATH = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\music.mp3"

# 3. How long each video segment (before speed-up) should be, in seconds:
TARGET_CLIP_DURATION = 5.0

# 4. Speed multiplier for each video clip:
VIDEO_SPEED_FACTOR = 1.5

# 5. Subsample beats (1 means use every beat):
USE_EVERY_NTH_BEAT = 1


def find_latest_run_folder(base_dir, prefix):
    """
    Finds the most recently modified subfolder of 'base_dir' whose name starts with 'prefix'.
    Returns the full path to that folder, or raises an error if none found.
    """
    all_entries = os.listdir(base_dir)
    run_folders = []
    for entry in all_entries:
        full_path = os.path.join(base_dir, entry)
        if os.path.isdir(full_path) and entry.startswith(prefix):
            run_folders.append(full_path)

    if not run_folders:
        raise FileNotFoundError(f"No folders starting with '{prefix}' found under {base_dir}")

    # Choose the one with the latest modification time:
    latest = max(run_folders, key=lambda p: os.path.getmtime(p))
    return latest


def find_video_clips_folder(latest_run_folder):
    """
    Given a path like 'H:\dancers_content\Run_20250603_141231',
    this navigates into 'all_videos', then picks the single (or newest) subfolder inside it.
    Returns the full path to that subfolder containing the actual video files.
    """
    all_videos_dir = os.path.join(latest_run_folder, "all_videos")
    if not os.path.isdir(all_videos_dir):
        raise FileNotFoundError(f"'all_videos' not found in {latest_run_folder}")

    subdirs = [
        os.path.join(all_videos_dir, name)
        for name in os.listdir(all_videos_dir)
        if os.path.isdir(os.path.join(all_videos_dir, name))
    ]

    if not subdirs:
        raise FileNotFoundError(f"No subfolder found under {all_videos_dir} to contain videos.")

    # If there is exactly one, use it; otherwise pick the most recently modified one:
    if len(subdirs) == 1:
        return subdirs[0]
    else:
        return max(subdirs, key=lambda p: os.path.getmtime(p))


def detect_beats(audio_path, tightness_param=100):
    """
    Loads the audio and uses librosa.beat.beat_track to find beat timestamps.
    Returns a numpy array of beat times (in seconds), ensuring the first time is 0.0.
    """
    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path)
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)

    # Normalize tempo output (librosa sometimes returns an array)
    actual_tempo_for_print = 0.0
    if isinstance(tempo, np.ndarray):
        if tempo.size >= 1:
            actual_tempo_for_print = float(tempo[0])
            if tempo.size > 1:
                print(f"Info: Multiple tempos detected {tempo}, using {actual_tempo_for_print:.2f} BPM")
        else:
            print("Info: librosa returned empty tempo array.")
    elif isinstance(tempo, (int, float)):
        actual_tempo_for_print = float(tempo)
    else:
        print(f"Info: Unexpected tempo type: {type(tempo)}")

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"Detected {len(beat_times)} beats. Tempo: {actual_tempo_for_print:.2f} BPM")

    # Ensure there's a beat at time 0.0
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
        print("Adjusted beat list to include time 0.0")

    return beat_times


if __name__ == "__main__":
    # --- Step A: Dynamically determine where the video clips actually live ---

    try:
        latest_run = find_latest_run_folder(BASE_DANCERS_DIR, RUN_PREFIX)
        print(f"👉 Latest run folder detected: {latest_run}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        exit()

    try:
        VIDEO_CLIPS_FOLDER = find_video_clips_folder(latest_run)
        print(f"👉 Video clips folder: {VIDEO_CLIPS_FOLDER}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        exit()

    #  Create an output "compiled" folder inside all_videos:
    ALL_VIDEOS_DIR = os.path.join(latest_run, "all_videos")
    COMPILED_DIR = os.path.join(ALL_VIDEOS_DIR, "compiled")
    if not os.path.exists(COMPILED_DIR):
        print(f"Creating compiled folder: {COMPILED_DIR}")
        os.makedirs(COMPILED_DIR, exist_ok=True)

    OUTPUT_VIDEO_PATH = os.path.join(COMPILED_DIR, "output_beat_synced_video.mp4")
    print(f"✅ Final will be saved to: {OUTPUT_VIDEO_PATH}\n")

    # --- Step B: Validate audio and video folders exist ---
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"ERROR: Audio file not found at {AUDIO_FILE_PATH}")
        exit()
    if not os.path.isdir(VIDEO_CLIPS_FOLDER):
        print(f"ERROR: Video clips folder not found at {VIDEO_CLIPS_FOLDER}")
        exit()

    # --- Step C: Beat Detection ---
    beat_times = detect_beats(AUDIO_FILE_PATH)
    if USE_EVERY_NTH_BEAT > 1:
        beat_times = beat_times[::USE_EVERY_NTH_BEAT]
        print(f"Using every {USE_EVERY_NTH_BEAT}th beat → {len(beat_times)} beats retained.")

    if len(beat_times) < 2:
        print("ERROR: Not enough beats detected. Check audio or adjust parameters.")
        exit()

    # --- Step D: Gather all video files under that folder ---
    def get_video_files(folder_path):
        """Returns a sorted list of video file paths in folder_path."""
        extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv")
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(folder_path, ext)))
        files.sort()
        if not files:
            raise ValueError(f"No video files found in {folder_path}")
        return files

    try:
        video_file_paths = get_video_files(VIDEO_CLIPS_FOLDER)
        print(f"Found {len(video_file_paths)} video clip(s) in {VIDEO_CLIPS_FOLDER}.")
    except ValueError as e:
        print(f"ERROR: {e}")
        exit()

    # --- Step E: Build the sped-up, beat-aligned segments ---
    video_segments = []
    clip_idx = 0

    print("\n🔨 Preparing video segments (each sped to 1.5× speed)...")
    for i in tqdm(range(len(beat_times))):
        beat_start_time = float(beat_times[i])
        # Determine end of this beat interval
        if i < len(beat_times) - 1:
            beat_end_time = float(beat_times[i + 1])
        else:
            with AudioFileClip(AUDIO_FILE_PATH) as temp_audio_for_duration:
                beat_end_time = temp_audio_for_duration.duration
            if beat_end_time <= beat_start_time:
                beat_end_time = beat_start_time + (TARGET_CLIP_DURATION / 2)

        segment_duration_on_timeline = beat_end_time - beat_start_time
        if segment_duration_on_timeline <= 0.01:
            print(f"Skipping tiny segment at beat {i+1} (duration {segment_duration_on_timeline:.3f}s)")
            continue

        source_video_path = video_file_paths[clip_idx % len(video_file_paths)]
        source_clip = None
        try:
            source_clip = VideoFileClip(source_video_path)
            # Speed it up to 1.5×
            source_clip = source_clip.fx(vfx.speedx, VIDEO_SPEED_FACTOR)

            # Extract up to TARGET_CLIP_DURATION seconds from the sped-up clip:
            extracted = source_clip.subclip(
                0,
                min(source_clip.duration, TARGET_CLIP_DURATION)
            )
            # Place it at the correct timestamp on the timeline:
            extracted = extracted.set_start(beat_start_time)
            extracted = extracted.set_duration(segment_duration_on_timeline)

            video_segments.append(extracted)
            # (Do NOT close source_clip here; MoviePy needs its reader to remain open.)

        except Exception as exc:
            print(f"Warning: Failed to load/process '{source_video_path}'. Skipping. ({exc})")
            if source_clip:
                source_clip.close()
        finally:
            clip_idx += 1

    if not video_segments:
        print("ERROR: No video segments were successfully created. Exiting.")
        exit()

    # --- Step F: Composite all segments and attach the original audio ---
    print("\n🎬 Compositing video clips together...")
    # Determine final_duration from segments' end times
    valid_ends = [seg.end for seg in video_segments if seg.end is not None]
    final_duration = max(valid_ends) if valid_ends else beat_times[-1]

    with AudioFileClip(AUDIO_FILE_PATH) as original_audio:
        final_duration = max(final_duration, original_audio.duration)

        # Figure out a target resolution (width×height) from the first valid segment
        target_resolution = None
        for seg in video_segments:
            if hasattr(seg, 'size') and seg.size:
                target_resolution = seg.size
                break

        # If none of the segments had a valid .size, fallback to the first video file
        if target_resolution is None and video_file_paths:
            try:
                with VideoFileClip(video_file_paths[0]) as temp_clip:
                    target_resolution = temp_clip.size
            except Exception:
                target_resolution = (1920, 1080)
        elif target_resolution is None:
            target_resolution = (1920, 1080)

        print(f"Using target resolution: {target_resolution[0]}×{target_resolution[1]}")

        # Resize each segment if it doesn't match the target resolution
        resized_segments = []
        for idx, seg in enumerate(video_segments):
            if not (hasattr(seg, 'get_frame') and hasattr(seg, 'set_position')):
                print(f"Warning: Segment #{idx} isn't a valid clip. Skipping.")
                continue
            if hasattr(seg, 'reader') and seg.reader is None:
                print(f"Warning: Segment #{idx} has a None reader. Skipping.")
                continue

            if hasattr(seg, 'size') and seg.size and seg.size != target_resolution:
                try:
                    resized_segments.append(seg.resize(target_resolution))
                except Exception as resize_exc:
                    fname = getattr(seg, 'filename', 'unknown')
                    print(f"Warning: Could not resize segment from '{fname}'. {resize_exc}. Skipping.")
            else:
                resized_segments.append(seg)

        if not resized_segments:
            print("ERROR: After resizing, no segments remain. Exiting.")
            exit()

        # Build the CompositeVideoClip, set total duration
        final_composition = CompositeVideoClip(resized_segments, size=target_resolution)
        final_composition = final_composition.set_duration(final_duration)

        # Attach the original audio (trimmed to final_duration)
        with AudioFileClip(AUDIO_FILE_PATH) as audio_for_final:
            audio_clip_for_final = audio_for_final.subclip(0, final_duration)
            final_composition = final_composition.set_audio(audio_clip_for_final)

            # Render out to disk:
            print(f"\n🔊 Rendering final combined video to:\n   {OUTPUT_VIDEO_PATH}\n")
            try:
                final_composition.write_videofile(
                    OUTPUT_VIDEO_PATH,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True,
                    preset="medium",
                    fps=24,
                    threads=os.cpu_count() or 2
                )
                print("✅ Video rendering complete!")
            except Exception as render_exc:
                print(f"ERROR during rendering: {render_exc}")
                import traceback
                traceback.print_exc()
            finally:
                # Close all segment objects to free resources
                print("\n🔒 Cleaning up clipped resources...")
                clips_to_close = set()
                for seg_list in (video_segments, resized_segments):
                    for clip_obj in seg_list:
                        if hasattr(clip_obj, 'close'):
                            clips_to_close.add(clip_obj)
                for c in clips_to_close:
                    try:
                        c.close()
                    except:
                        pass

                if 'audio_clip_for_final' in locals() and hasattr(audio_clip_for_final, 'close'):
                    audio_clip_for_final.close()
                print("Resource cleanup done.")
