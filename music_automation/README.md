# Music Automation System

## Overview

A comprehensive Music-Based Image & Video Generation Automation system that analyzes music files to generate themed images and videos featuring Lord Shiva and Hindu deity content. The system uses AI-powered music analysis to create contextually relevant visual content synchronized with musical segments.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- ComfyUI running on port 8188
- GPU with 8GB+ VRAM
- Required Python packages (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md))

### Installation
```bash
# Clone/navigate to music automation directory
cd music_automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install fastapi uvicorn flask tqdm requests pillow python-dotenv
pip install librosa numpy moviepy opencv-python
pip install google-generativeai openai-whisper

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys and settings
```

### Usage
```bash
# Full automation pipeline
python run_music_automation.py --mode automation

# Audio analysis only
python run_music_automation.py --mode audio-only

# Video generation only
python run_music_automation.py --mode video-only

# Beat sync compilation only
python run_music_automation.py --mode beat-sync

# Test mode (limited processing)
python run_music_automation.py --mode automation --test

# Run test suite
python run_music_automation.py --mode test
```

## 📁 Directory Structure

```
music_automation/
├── core/                    # Core automation scripts
│   ├── main_automation_music.py       # Main automation logic
│   ├── api_server_v5_music.py         # FastAPI server
│   ├── run_pipeline_music.py          # Pipeline orchestrator
│   └── music_pipeline_all_in_one.py   # All-in-one pipeline
├── audio_processing/        # Audio analysis & processing
│   ├── audio_to_prompts_generator.py  # Music analysis system
│   ├── quick_audio_capture.py         # Audio capture utility
│   └── test_whisper_transcription.py  # Whisper testing
├── video_compilation/       # Video compilation tools
│   ├── music_video_beat_sync_compiler.py  # Beat sync compiler
│   ├── music_video_fast_compiler.py       # Fast compiler
│   ├── music_video_image_compiler.py      # Image compiler
│   └── music_upscale.py                   # Video upscaling
├── beat_sync/              # Beat synchronization
│   ├── beat_sync_single.py            # Single beat sync
│   ├── test_beat_sync_discovery.py    # Beat sync testing
│   └── run_beat_sync_compiler.bat     # Batch runner
├── karaoke/                # Karaoke features
│   ├── test_word_level_karaoke.py     # Word-level karaoke
│   └── test_karaoke_fix.py            # Karaoke fixes
├── config/                 # Configuration files
│   ├── config_music.json              # Main configuration
│   └── base_workflows/                # ComfyUI workflows
│       └── API_flux_without_faceswap_music.json
├── debug_tools/            # Debugging & testing
│   ├── debug_music_pipeline.py       # Pipeline debugging
│   ├── test_approval_format.py       # Approval testing
│   └── test_*.py                     # Various tests
├── docs/                   # Documentation
│   ├── MUSIC_AUTOMATION_DOCUMENTATION.md  # Main docs
│   ├── README_BEAT_SYNC_COMPILER.md       # Beat sync docs
│   ├── README_KARAOKE_FEATURES.md         # Karaoke docs
│   └── AUTOMATION_DEVELOPMENT_LEARNINGS.md # Dev learnings
├── assets/                 # Assets & media
│   └── music.mp3                      # Sample music file
├── run_music_automation.py # Main entry point
├── DEPLOYMENT_GUIDE.md     # Deployment instructions
├── TESTING_GUIDE.md        # Testing procedures
└── README.md               # This file
```

## 🎵 Workflow Overview

### 1. Audio Analysis (5-10 minutes)
- Analyze music file with Google Gemini AI
- Generate timestamped prompts based on musical segments
- Create structured output folder

### 2. Image Generation (10-30 minutes)
- Generate Lord Shiva themed images based on prompts
- Send images to Telegram for user approval
- Process approval decisions

### 3. Video Generation (20-60 minutes)
- Convert approved images to videos using WanVideo
- Apply deity-specific enhancements
- Generate motion and effects

### 4. Beat Sync Compilation (5-15 minutes)
- Compile videos with beat synchronization
- Add karaoke subtitles (optional)
- Create final music video output

## 🔧 Configuration

### Environment Variables (.env)
```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
GOOGLE_API_KEY=your_google_api_key

# Optional
PYTHONIOENCODING=utf-8
COMFYUI_PATH=D:/Comfy_UI_V20/ComfyUI
OUTPUT_BASE_PATH=H:/dancers_content
```

### Main Configuration (config/config_music.json)
```json
{
    "comfyui_api_url": "http://127.0.0.1:8188",
    "api_server_url": "http://127.0.0.1:8006",
    "base_workflow_image": "config/base_workflows/API_flux_without_faceswap_music.json",
    "output_folder": "output_runs_music"
}
```

## 🧪 Testing

### Component Testing
```bash
# Test audio processing
cd audio_processing && python test_whisper_transcription.py

# Test beat sync discovery
cd beat_sync && python test_beat_sync_discovery.py

# Test API endpoints
cd debug_tools && python test_api_debug.py
```

### Integration Testing
```bash
# Run full test suite
python run_music_automation.py --mode test

# Test minimal pipeline
python run_music_automation.py --mode automation --test
```

## 📊 Features

### Core Features
- ✅ **Music Analysis**: AI-powered audio analysis with temporal segmentation
- ✅ **Image Generation**: Lord Shiva themed image creation
- ✅ **Video Generation**: I2V (Image-to-Video) processing with WanVideo
- ✅ **Telegram Integration**: Real-time approval system
- ✅ **Beat Synchronization**: Music-synchronized video compilation

### Advanced Features
- ✅ **Karaoke Subtitles**: Word-level synchronized subtitles with Hinglish support
- ✅ **Visual Effects**: Random effects pool with crossfade transitions
- ✅ **Auto-Discovery**: Automatic file and folder discovery
- ✅ **Error Handling**: Comprehensive error management and recovery
- ✅ **Performance Monitoring**: Real-time progress tracking and logging

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Complete deployment instructions
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)**: Comprehensive testing procedures
- **[docs/MUSIC_AUTOMATION_DOCUMENTATION.md](docs/MUSIC_AUTOMATION_DOCUMENTATION.md)**: Detailed system documentation
- **[docs/README_BEAT_SYNC_COMPILER.md](docs/README_BEAT_SYNC_COMPILER.md)**: Beat sync compiler guide
- **[docs/README_KARAOKE_FEATURES.md](docs/README_KARAOKE_FEATURES.md)**: Karaoke features documentation
- **[docs/AUTOMATION_DEVELOPMENT_LEARNINGS.md](docs/AUTOMATION_DEVELOPMENT_LEARNINGS.md)**: Development best practices

## 🚨 Troubleshooting

### Common Issues

1. **ComfyUI Connection Failed**
   ```bash
   cd D:/Comfy_UI_V20/ComfyUI
   python main.py --listen --port 8188
   ```

2. **Unicode Encoding Errors**
   ```bash
   export PYTHONIOENCODING=utf-8
   ```

3. **Port Already in Use**
   ```bash
   # Windows
   netstat -ano | findstr :8006
   taskkill /PID <process_id> /F
   
   # Linux
   lsof -ti:8006 | xargs kill -9
   ```

4. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

For more troubleshooting, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting).

## 🔄 Development

### Contributing
1. Review [docs/AUTOMATION_DEVELOPMENT_LEARNINGS.md](docs/AUTOMATION_DEVELOPMENT_LEARNINGS.md)
2. Follow existing code patterns and conventions
3. Test changes with `python run_music_automation.py --mode test`
4. Update documentation as needed

### Code Standards
- No emoji characters in logging statements
- Consistent API endpoint naming
- Proper error handling and input validation
- Comprehensive logging with appropriate levels

## 📈 Performance Metrics

### Expected Performance
- **Audio Analysis**: 5-10 minutes per song
- **Image Generation**: 30-60 seconds per image
- **Video Generation**: 2-5 minutes per video
- **Beat Sync Compilation**: 5-15 minutes
- **Overall Success Rate**: >90%

### System Requirements
- **GPU Memory**: 8GB+ VRAM recommended
- **RAM**: 16GB+ for large model loading
- **Storage**: 50GB+ for models and output
- **CPU**: Multi-core for parallel processing

## 📞 Support

For issues, questions, or contributions:
1. Check the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) and [TESTING_GUIDE.md](TESTING_GUIDE.md)
2. Review the comprehensive documentation in the `docs/` folder
3. Run diagnostic tests with `python run_music_automation.py --mode test`
4. Check log files in the `logs/` directory

## 🎯 Success Stories

The system has successfully generated:
- ✅ High-quality Lord Shiva themed images with deity-specific enhancements
- ✅ Motion videos with mystical effects and divine characteristics
- ✅ Beat-synchronized music videos with professional transitions
- ✅ Karaoke-style videos with Hinglish subtitle support
- ✅ Automated approval workflows via Telegram integration

---

**Version**: 1.0  
**Last Updated**: June 23, 2025  
**Compatibility**: Python 3.11+, ComfyUI, WanVideo Models

*A comprehensive automation system for creating divine music videos with AI-powered analysis and generation.*