# Music Automation Deployment Guide

## Overview

This comprehensive guide provides step-by-step instructions for deploying and executing the Music-Based Image & Video Generation Automation system. The system generates Lord Shiva themed visual content synchronized with musical analysis.

## 🏗️ System Architecture

```
music_automation/
├── core/                    # Core automation scripts
│   ├── main_automation_music.py       # Main automation logic
│   ├── api_server_v5_music.py         # FastAPI server
│   ├── run_pipeline_music.py          # Pipeline orchestrator
│   ├── music_pipeline_all_in_one.py   # All-in-one pipeline
│   └── logs/                          # Core logs
├── audio_processing/        # Audio analysis & processing
│   ├── audio_to_prompts_generator.py  # Music analysis
│   ├── quick_audio_capture.py         # Audio capture
│   └── test_whisper_transcription.py  # Whisper testing
├── video_compilation/       # Video compilation tools
│   ├── music_video_beat_sync_compiler.py  # Beat sync compiler
│   ├── music_video_fast_compiler.py       # Fast compiler
│   ├── music_video_image_compiler.py      # Image compiler
│   ├── music_upscale.py                   # Video upscaling
│   └── logs/                              # Compilation logs
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
├── logs/                   # Main log directory
├── output_runs_music/      # Generated content output
│   └── Run_YYYYMMDD_HHMMSS_music_images/
├── run_music_automation.py # Main entry point
├── setup_environment.py   # Environment setup
├── validate_setup.py      # Setup validation
├── DEPLOYMENT_GUIDE.md    # This file
├── README.md              # Main documentation
└── TESTING_GUIDE.md       # Testing procedures
```

## 📋 Prerequisites

### System Requirements

- **Operating System**: Windows 10/11 or Linux (Ubuntu 20.04+)
- **Python Version**: 3.11 or higher
- **GPU**: NVIDIA GPU with 8GB+ VRAM (required for ComfyUI)
- **RAM**: 16GB+ recommended
- **Storage**: 50GB+ free space (for models and generated content)
- **Internet**: Stable connection for model downloads and API calls

### Required Software

1. **Python 3.11+**
   ```bash
   # Windows - Download from python.org
   # Linux
   sudo apt update
   sudo apt install python3.11 python3.11-pip python3.11-venv
   ```

2. **Git** (for cloning repositories)
   ```bash
   # Windows - Download from git-scm.com
   # Linux
   sudo apt install git
   ```

3. **ComfyUI** (AI image/video generation)
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   pip install -r requirements.txt
   ```

## 🔧 Environment Setup

### 1. Create Python Virtual Environment

```bash
# Navigate to music automation folder
cd music_automation

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. Install Python Dependencies

```bash
# Core dependencies
pip install fastapi uvicorn flask tqdm requests pillow python-dotenv

# Audio processing dependencies
pip install librosa numpy

# Video processing dependencies
pip install moviepy opencv-python

# AI dependencies
pip install google-generativeai openai-whisper

# Optional: For better performance
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. Environment Variables

Create a `.env` file in the `music_automation` root directory:

```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Google AI Configuration
GOOGLE_API_KEY=your_google_gemini_api_key_here

# System Configuration
PYTHONIOENCODING=utf-8
COMFYUI_PATH=D:/Comfy_UI_V20/ComfyUI
OUTPUT_BASE_PATH=H:/dancers_content

# Optional: Custom ports
MUSIC_API_PORT=8006
COMFYUI_PORT=8188
```

### 4. Directory Structure Setup

```bash
# Create required output directories
mkdir -p H:/dancers_content
mkdir -p D:/Comfy_UI_V20/ComfyUI/output/dancer/songs
mkdir -p music_automation/logs
mkdir -p music_automation/output_runs_music
mkdir -p D:/Comfy_UI_V20/ComfyUI/input/temp_video_starts

# Verify structure exists
ls -la music_automation/
ls -la H:/dancers_content/
```

## 🤖 ComfyUI Setup

### 1. Download Required Models

**WanVideo Models** (for video generation):
```bash
cd D:/Comfly_UI_V20/ComfyUI/models/checkpoints
# Download the following models:
# - Wan2_1-I2V-14B-480P_fp8_e5m2.safetensors
# - Wan2_1_VAE_bf16.safetensors
# - umt5-xxl-enc-bf16.safetensors
```

**Flux Models** (for image generation):
```bash
# Download Flux models to ComfyUI/models/unet
# Download VAE models to ComfyUI/models/vae
# Download text encoders to ComfyUI/models/clip
```

### 2. Start ComfyUI

```bash
cd D:/Comfy_UI_V20/ComfyUI
python main.py --listen --port 8188
```

Verify ComfyUI is running by visiting: http://127.0.0.1:8188

## 🎵 Music Content Setup

### 1. Prepare Music Files

```bash
# Copy your music files to the songs directory
cp your_music.mp3 D:/Comfy_UI_V20/ComfyUI/output/dancer/songs/

# Supported formats: MP3, WAV, FLAC, M4A
```

### 2. Source Faces (Optional)

```bash
# If using face swap features
mkdir -p music_automation/source_faces
# Copy face images to this directory
```

## 🚀 Deployment Steps

### Step 1: Configuration Validation

```bash
# Navigate to music automation directory
cd music_automation

# Validate configuration
python -c "
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Check environment variables
required_vars = ['TELEGRAM_BOT_TOKEN', 'GOOGLE_API_KEY']
for var in required_vars:
    if not os.getenv(var):
        print(f'❌ Missing environment variable: {var}')
    else:
        print(f'✅ {var} configured')

# Check paths
paths = [
    'D:/Comfy_UI_V20/ComfyUI',
    'H:/dancers_content',
    'config/config_music.json',
    'config/base_workflows'
]

for path in paths:
    if Path(path).exists():
        print(f'✅ Path exists: {path}')
    else:
        print(f'❌ Path missing: {path}')
"
```

### Step 2: Start Core Services

```bash
# Terminal 1: Start ComfyUI (if not already running)
cd D:/Comfy_UI_V20/ComfyUI
python main.py --listen --port 8188

# Terminal 2: Start Music API Server
cd music_automation
python core/api_server_v5_music.py

# Verify API server is running
curl http://127.0.0.1:8006/health
```

### Step 3: Generate Audio Analysis

```bash
# Generate prompts from music
cd music_automation
python audio_processing/audio_to_prompts_generator.py

# This creates: H:/dancers_content/Run_YYYYMMDD_HHMMSS_music/
```

### Step 4: Execute Main Automation

```bash
# Run complete automation pipeline
cd music_automation
python core/run_pipeline_music.py

# Monitor logs
tail -f logs/automation_music_pipeline_*.log
```

## 📱 Telegram Integration

### Setup Telegram Bot

1. **Create Bot**:
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Save the bot token

2. **Get Chat ID**:
   - Add bot to your chat/group
   - Send a message to the bot
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find your chat_id in the response

3. **Configure Environment**:
   ```env
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxyz
   TELEGRAM_CHAT_ID=-1001234567890
   ```

## 🔄 Automation Workflow

### Complete Execution Flow

1. **Audio Analysis** (5-10 minutes)
   - Analyze music file with Google Gemini AI
   - Generate timestamped prompts based on musical segments
   - Create structured output folder: `H:/dancers_content/Run_YYYYMMDD_HHMMSS_music_images/`

2. **Image Generation** (10-30 minutes)
   - Generate Lord Shiva themed images based on prompts
   - Send images to Telegram for user approval
   - Wait for user approval decisions via Telegram bot

3. **Video Generation** (20-60 minutes)
   - Process approved images to generate videos
   - Use WanVideo models for image-to-video conversion
   - Apply deity-specific enhancements and effects

4. **Beat Sync Compilation** (5-15 minutes)
   - Compile videos with beat synchronization
   - Add karaoke subtitles with Hinglish support (optional)
   - Create final music video output

### Execution Methods

#### Method 1: Single Command (Recommended)
```bash
# Navigate to music automation directory
cd music_automation

# Run complete automation pipeline
python run_music_automation.py --mode automation

# Monitor progress
tail -f logs/automation_music_pipeline_*.log
```

#### Method 2: Step-by-Step Manual Execution
```bash
# Step 1: Audio Analysis (5-10 minutes)
cd music_automation
python audio_processing/audio_to_prompts_generator.py

# Step 2: Main Automation Pipeline (30-60 minutes)
python core/main_automation_music.py

# Step 3: Beat Sync Compilation (5-15 minutes)  
python video_compilation/music_video_beat_sync_compiler.py
```

#### Method 3: Component-Specific Execution
```bash
# Audio analysis only
python run_music_automation.py --mode audio-only

# Video generation only (after images approved)
python run_music_automation.py --mode video-only

# Beat sync compilation only
python run_music_automation.py --mode beat-sync

# Test mode (limited processing)
python run_music_automation.py --mode automation --test
```

#### Method 4: Alternative Core Scripts
```bash
# All-in-one pipeline
python core/music_pipeline_all_in_one.py

# Pipeline orchestrator  
python core/run_pipeline_music.py

# Approval-only mode
python approval_only.py
```

## 🧪 Testing & Validation

### Component Testing

```bash
# Test audio processing
cd music_automation/audio_processing
python test_whisper_transcription.py

# Test beat sync discovery
cd ../beat_sync
python test_beat_sync_discovery.py

# Test video compilation
cd ../video_compilation
python music_video_beat_sync_compiler.py

# Test API endpoints
cd ../debug_tools
python test_api_debug.py
```

### Integration Testing

```bash
# Test complete pipeline with minimal setup
cd music_automation
python debug_tools/debug_music_pipeline.py

# Validate configuration
python debug_tools/test_approval_format.py

# Test image discovery
python debug_tools/test_image_discovery.py
```

## 📊 Monitoring & Logging

### Log Files Location

```
music_automation/logs/
├── automation_music_pipeline_YYYYMMDD_HHMMSS.log
├── api_server_debug.log
├── api_server_stdout.log
└── api_server_stderr.log
```

### Real-time Monitoring

```bash
# Monitor main pipeline
tail -f music_automation/logs/automation_music_pipeline_*.log

# Monitor API server
tail -f music_automation/logs/api_server_debug.log

# Monitor ComfyUI queue
# Visit: http://127.0.0.1:8188
```

### Performance Metrics

```bash
# Check processing times
grep "Processing time\|Generation time" music_automation/logs/*.log

# Check error rates
grep "ERROR\|CRITICAL" music_automation/logs/*.log

# Check success rates
grep "SUCCESS\|COMPLETED" music_automation/logs/*.log
```

## 🚨 Troubleshooting

### Common Issues

#### 1. ComfyUI Connection Failed
```bash
# Error: Connection refused to 127.0.0.1:8188
# Solution:
cd D:/Comfy_UI_V20/ComfyUI
python main.py --listen --port 8188

# Verify ComfyUI is running
curl http://127.0.0.1:8188
```

#### 2. Unicode Encoding Errors
```bash
# Error: UnicodeEncodeError
# Solution: Set environment variable
export PYTHONIOENCODING=utf-8
# Windows CMD:
set PYTHONIOENCODING=utf-8
```

#### 3. Port Already in Use
```bash
# Error: Port 8006 already in use
# Solution: Kill existing process
# Windows:
netstat -ano | findstr :8006
taskkill /PID <process_id> /F

# Linux:
lsof -ti:8006 | xargs kill -9
```

#### 4. Missing Dependencies
```bash
# Error: ModuleNotFoundError
# Solution: Install missing packages
pip install fastapi uvicorn flask tqdm google-generativeai
pip install librosa numpy moviepy opencv-python
pip install openai-whisper
```

#### 5. Telegram Bot Not Working
```bash
# Check bot token and chat ID
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Bot Token:', os.getenv('TELEGRAM_BOT_TOKEN')[:10] + '...')
print('Chat ID:', os.getenv('TELEGRAM_CHAT_ID'))
"

# Test bot connection
curl -X GET "https://api.telegram.org/bot<TOKEN>/getMe"
```

#### 6. Black Video Generation
```bash
# Common causes and solutions:
# 1. Check WanVideo models are loaded in ComfyUI
# 2. Verify image paths are correct
# 3. Check GPU memory availability
# 4. Test workflow manually in ComfyUI interface

# Debug video generation
cd music_automation/debug_tools
python test_isolated_video_generation.py
```

### Debug Commands

```bash
# System diagnostics
python -c "
import sys, torch, cv2, librosa
print('Python:', sys.version)
print('PyTorch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
print('OpenCV:', cv2.__version__)
print('Librosa:', librosa.__version__)
"

# Check disk space
df -h  # Linux
dir   # Windows

# Check GPU memory
nvidia-smi

# Check network connectivity
ping google.com
curl -I https://api.telegram.org
```

## 🔐 Security Considerations

### API Security
- All APIs run on localhost only
- No external network exposure
- Use strong API keys and tokens
- Regularly rotate credentials

### File Security
- Generated content stored locally
- No external uploads
- Temporary files cleaned automatically
- Backup important configurations

### Privacy
- Audio processing done locally
- No external audio uploads
- Telegram integration optional
- All AI processing local (except Gemini API)

## 📈 Performance Optimization

### System Optimization

```bash
# GPU optimization
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Memory optimization
export PYTORCH_CUDA_ALLOC_CONF=garbage_collection_threshold:0.6,max_split_size_mb:128
```

### Processing Optimization

```python
# In config files, adjust:
{
    "batch_size": 1,           # Reduce for less VRAM usage
    "timeout_seconds": 300,    # Increase for slower systems
    "max_retries": 3,          # Increase for unstable systems
    "polling_interval": 5      # Adjust for responsiveness
}
```

## 📦 Backup & Recovery

### Configuration Backup

```bash
# Backup configuration files
cp -r music_automation/config music_automation/config_backup_$(date +%Y%m%d)

# Backup environment file
cp .env .env.backup
```

### Generated Content Backup

```bash
# Backup generated content
tar -czf music_output_backup_$(date +%Y%m%d).tar.gz H:/dancers_content/
```

### System Recovery

```bash
# Reset to clean state
cd music_automation
rm -rf logs/*
rm -rf temp_video_starts/*
rm -rf output_runs_music/*

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 🎯 Success Metrics

### Expected Performance
- **Audio Analysis**: 5-10 minutes per song
- **Image Generation**: 30-60 seconds per image
- **Video Generation**: 2-5 minutes per video
- **Beat Sync Compilation**: 5-15 minutes per compilation
- **Overall Success Rate**: >90% completion rate

### Quality Indicators
- **Audio Analysis Accuracy**: Meaningful segment prompts
- **Image Quality**: Recognizable Lord Shiva imagery
- **Video Quality**: Non-black videos with motion
- **Karaoke Accuracy**: Synchronized subtitles
- **Beat Sync Quality**: Music-synchronized video segments

## 🔄 Maintenance

### Regular Maintenance Tasks

**Daily**:
- Check log files for errors
- Monitor disk space usage
- Verify API server health

**Weekly**:
- Clean temporary files
- Archive old generated content
- Review performance metrics

**Monthly**:
- Update Python dependencies
- Update ComfyUI models
- Review and rotate API keys
- Backup configuration files

### Update Procedures

```bash
# Update Python dependencies
pip list --outdated
pip install --upgrade package_name

# Update ComfyUI
cd D:/Comfy_UI_V20/ComfyUI
git pull origin master
pip install -r requirements.txt

# Update music automation
cd music_automation
git pull origin main  # If using version control
```

## 📞 Support & Resources

### Documentation
- [Main Documentation](docs/MUSIC_AUTOMATION_DOCUMENTATION.md)
- [Beat Sync Guide](docs/README_BEAT_SYNC_COMPILER.md)
- [Karaoke Features](docs/README_KARAOKE_FEATURES.md)
- [Development Learnings](docs/AUTOMATION_DEVELOPMENT_LEARNINGS.md)

### Testing Resources
- [Testing Guide](TESTING_GUIDE.md)
- [Debug Tools](debug_tools/)
- [Component Tests](debug_tools/test_*.py)

### External Resources
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Google Gemini API](https://ai.google.dev/)
- [OpenAI Whisper](https://github.com/openai/whisper)

---

**Deployment Checklist**:

- [ ] System requirements met
- [ ] Python 3.11+ installed
- [ ] ComfyUI installed and running
- [ ] All models downloaded
- [ ] Environment variables configured
- [ ] Directory structure created
- [ ] Dependencies installed
- [ ] Configuration files updated
- [ ] Telegram bot configured
- [ ] API servers started
- [ ] Test execution completed
- [ ] Monitoring setup complete

*Last Updated: June 23, 2025*
*Version: 1.0*