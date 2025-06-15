import os
import glob
import librosa
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from tqdm import tqdm

# --- Configuration ---
AUDIO_FILE_PATH = r"D:\Comfy_UI_V20\ComfyUI\output\dancer\music.mp3"
VIDEO_CLIPS_FOLDER = r"H:\dancers_content\Run_20250602_145116\all_videos\250602"
OUTPUT_DIR = r"H:\dancers_content\Run_20250602_145116\all_videos\compiled"
TARGET_CLIP_DURATION = 5.0
NTH_BEATS_TO_COMPILE = [1, 2, 3, 4]  # Add more intervals as needed

# --- Helper Functions ---
def get_video_files(folder_path):
    extensions = ("*.mp4", "*.mov", "*.avi", "*.mkv")
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(folder_path, ext)))
    files.sort()
    if not files:
        raise ValueError(f"No video files found in {folder_path}")
    return files

def detect_beats(audio_path, tightness_param=100):
    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path)
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=tightness_param, trim=False)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if not beat_times.size or beat_times[0] > 0.1:
        beat_times = np.insert(beat_times, 0, 0.0)
    print(f"Detected {len(beat_times)} beats.")
    return beat_times

def compile_video_for_beats(beat_times, video_file_paths, output_path, audio_file_path, target_clip_duration):
    video_segments = []
    clip_idx = 0
    for i in tqdm(range(len(beat_times))):
        beat_start_time = beat_times[i]
        if i < len(beat_times) - 1:
            beat_end_time = beat_times[i+1]
        else:
            with AudioFileClip(audio_file_path) as temp_audio:
                beat_end_time = temp_audio.duration
            if beat_end_time <= beat_start_time:
                beat_end_time = beat_start_time + (target_clip_duration / 2)

        segment_duration_on_timeline = beat_end_time - beat_start_time
        if segment_duration_on_timeline <= 0.01:
            continue

        source_video_path = video_file_paths[clip_idx % len(video_file_paths)]
        try:
            source_clip_object = VideoFileClip(source_video_path)
            segment_to_add = source_clip_object.subclip(0, min(source_clip_object.duration, target_clip_duration))
            segment_to_add = segment_to_add.set_start(beat_start_time)
            segment_to_add = segment_to_add.set_duration(segment_duration_on_timeline)
            video_segments.append(segment_to_add)
        except Exception as e:
            print(f"Warning: Could not load/process video {source_video_path}: {e}")
        finally:
            clip_idx += 1

    if not video_segments:
        print("ERROR: No video segments created.")
        return

    # Determine target resolution
    target_resolution = None
    for seg in video_segments:
        if hasattr(seg, 'size') and seg.size:
            target_resolution = seg.size
            break
    if not target_resolution and video_file_paths:
        with VideoFileClip(video_file_paths[0]) as temp_clip:
            target_resolution = temp_clip.size
    if not target_resolution:
        target_resolution = (1920, 1080)

    # Resize segments if needed
    resized_segments = []
    for seg in video_segments:
        if hasattr(seg, 'size') and seg.size != target_resolution:
            try:
                resized_segments.append(seg.resize(target_resolution))
            except Exception:
                resized_segments.append(seg)
        else:
            resized_segments.append(seg)

    # Final duration
    with AudioFileClip(audio_file_path) as original_audio:
        final_duration = max([s.end for s in resized_segments if s.end], default=original_audio.duration)
        final_duration = max(final_duration, original_audio.duration)
        final_composition = CompositeVideoClip(resized_segments, size=target_resolution)
        final_composition = final_composition.set_duration(final_duration)
        final_composition = final_composition.set_audio(original_audio.subclip(0, final_duration))
        print(f"Rendering: {output_path}")
        final_composition.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            preset="medium",
            fps=24,
            threads=os.cpu_count() or 2
        )
        print("Done:", output_path)

# --- Main ---
if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"Audio file not found: {AUDIO_FILE_PATH}")
        exit()
    if not os.path.isdir(VIDEO_CLIPS_FOLDER):
        print(f"Video clips folder not found: {VIDEO_CLIPS_FOLDER}")
        exit()

    # Detect beats once
    all_beat_times = detect_beats(AUDIO_FILE_PATH)
    video_file_paths = get_video_files(VIDEO_CLIPS_FOLDER)

    for nth in NTH_BEATS_TO_COMPILE:
        beat_times = all_beat_times[::nth]
        print(f"\n--- Compiling video for every {nth}th beat ({len(beat_times)} segments) ---")
        output_path = os.path.join(OUTPUT_DIR, f"output_beat_synced_video_every_{nth}.mp4")
        compile_video_for_beats(
            beat_times=beat_times,
            video_file_paths=video_file_paths,
            output_path=output_path,
            audio_file_path=AUDIO_FILE_PATH,
            target_clip_duration=TARGET_CLIP_DURATION
        )
