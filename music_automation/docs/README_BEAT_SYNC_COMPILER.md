# Music Video Equal Time Allocation Compiler

## Overview
This automated script creates music videos by giving each video clip equal time allocation (no repeats) with forward-backward looping patterns to fill the assigned time slots.

## 🎯 What It Does

1. **Auto-Discovery**: Automatically finds the latest `Run_*_music_images` folder
2. **Video Collection**: Locates all video clips in the date subfolder (e.g., `250622`)
3. **Song Selection**: Gets the latest song from the songs directory
4. **Time Allocation**: Calculates equal time per video (music_duration ÷ number_of_videos)
5. **Forward-Backward Pattern**: Each video fills its time slot with:
   - Forward playback → Backward playback → Forward → Backward (loop until time filled)
   - 2-second segments alternating direction
   - Random visual effects (mirror, contrast, gamma, etc.)
   - Crossfade transitions between different videos
6. **Output**: Creates a seamless compilation with no video repetition

## 📁 Folder Structure

```
H:\dancers_content\
└── Run_20250622_131220_music_images\
    └── all_videos\
        ├── 250622\                    # Source video clips
        │   ├── video1.mp4
        │   ├── video2.mp4
        │   └── ...
        └── music_video_compiled\      # Output folder (created)
            └── equal_time_compilation_[song]_[timestamp].mp4

D:\Comfy_UI_V20\ComfyUI\output\dancer\songs\
└── ओम नमः शिवाय.mp3               # Source audio
```

## 📊 Time Allocation Example

**Scenario**: 60-second song with 5 video clips
- **Time per video**: 60 ÷ 5 = 12 seconds each
- **No video repetition**: Each video used exactly once

```
Video 1: 0s-12s   → Forward→Backward→Forward→Backward (6 segments × 2s each)
Video 2: 12s-24s  → Forward→Backward→Forward→Backward 
Video 3: 24s-36s  → Forward→Backward→Forward→Backward
Video 4: 36s-48s  → Forward→Backward→Forward→Backward  
Video 5: 48s-60s  → Forward→Backward→Forward→Backward
```

**Pattern within each 12-second slot**:
- 0-2s: Forward
- 2-4s: Backward  
- 4-6s: Forward
- 6-8s: Backward
- 8-10s: Forward
- 10-12s: Backward

## 🚀 Quick Start

### Option 1: Windows Batch Script (Recommended)
```bash
# Double-click or run:
run_beat_sync_compiler.bat
```
This will automatically install dependencies and run the compiler.

### Option 2: Manual Installation
```bash
# Install dependencies
pip install librosa numpy moviepy tqdm

# Run the compiler
python music_video_beat_sync_compiler.py
```

### Option 3: Test Discovery First
```bash
# Test folder/file discovery without dependencies
python test_beat_sync_discovery.py
```

## 📋 Files Included

- `music_video_beat_sync_compiler.py` - Main compilation script
- `test_beat_sync_discovery.py` - Test discovery logic (no heavy deps)
- `run_beat_sync_compiler.bat` - Windows batch installer/runner
- `INSTALL_DEPENDENCIES.txt` - Detailed installation instructions
- `README_BEAT_SYNC_COMPILER.md` - This documentation

## 🎛️ Configuration

The script includes customizable settings:

```python
# Beat Sync Settings
TARGET_CLIP_DURATION = 5.0
BASE_VIDEO_SPEED_FACTOR = 1.5
FAST_BEAT_THRESHOLD = 0.4
SLOW_BEAT_THRESHOLD = 0.8
EFFECT_PROBABILITY = 0.35
CROSSFADE_DURATION = 0.15
YOYO_PROBABILITY = 0.40
```

## 🎨 Features

### Beat Synchronization
- **Librosa Beat Detection**: Advanced audio analysis for precise beat timing
- **Dynamic Speed**: Automatically adjusts video speed based on beat intervals
- **Three-Section Processing**: Beat-synced start, continuous middle, beat-synced end

### Visual Effects
- **Random Effects Pool**: Mirror, black/white, contrast, gamma correction
- **Yoyo Effects**: Forward-reverse segments for dynamic visual appeal
- **Crossfade Transitions**: Smooth transitions between clips
- **Effect Probability**: Configurable chance of applying effects (35% default)

### Smart Processing
- **Auto-Discovery**: No hardcoded paths, finds latest folders automatically
- **Video Looping**: Automatically cycles through available video clips
- **Progress Tracking**: Visual progress bars with tqdm
- **Error Handling**: Robust error handling and cleanup
- **Memory Management**: Proper cleanup of video clips and audio

## 🔧 Technical Details

### Dependencies
- **librosa**: Audio analysis and beat detection
- **numpy**: Numerical operations for audio processing
- **moviepy**: Video editing and composition
- **tqdm**: Progress bars and user feedback

### Output Format
- **Codec**: H.264 (libx264)
- **Audio**: AAC
- **FPS**: 24
- **Preset**: Medium (balance of quality/speed)
- **Bitrate**: 5000k

### File Naming
Output files are named: `beat_synced_compilation_[song_name]_[timestamp].mp4`

Example: `beat_synced_compilation_ओम नमः शिवाय_20250622_143025.mp4`

## 📊 Recent Test Results

✅ **Discovery Test Successful**:
- Music Folder: `Run_20250622_131220_music_images`
- Video Files: 19 clips found
- Song File: `ओम नमः शिवाय.mp3` (3.2 MB)
- Output Directory: Created successfully

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Install missing dependencies with pip
2. **Path Not Found**: Verify folder structure matches expected format
3. **No Video Files**: Check that video files exist in date subfolder
4. **No Song Files**: Ensure songs directory contains audio files
5. **Permission Errors**: Run with appropriate file system permissions

### Debugging Steps

1. Run `test_beat_sync_discovery.py` to test folder discovery
2. Check the console output for specific error messages
3. Verify all required folders and files exist
4. Ensure Python and pip are properly installed

## 🎯 Expected Workflow

1. User runs music generation pipeline → Creates `Run_*_music_images` folder with videos
2. User adds songs to songs directory
3. User runs beat sync compiler → Creates synchronized compilation
4. Final video saved in `music_video_compiled` folder

## 📈 Performance

- **Processing Time**: Depends on video count and song length
- **Memory Usage**: Optimized with proper clip cleanup
- **Quality**: High-quality output with configurable settings
- **Progress Tracking**: Real-time progress updates during processing

---

*Created by Claude Code Assistant - A fully automated beat-synchronized music video compilation system*