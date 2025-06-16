# Dancer Content Pipeline - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Dancer Content Pipeline to a new server. The pipeline is a sophisticated AI-powered content generation system that creates synchronized video content with automated approval workflows and social media integration.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Prerequisites](#prerequisites)
3. [Core Dependencies](#core-dependencies)
4. [Directory Structure](#directory-structure)
5. [Configuration Files](#configuration-files)
6. [Environment Variables](#environment-variables)
7. [External Services Setup](#external-services-setup)
8. [Installation Steps](#installation-steps)
9. [Pipeline Components](#pipeline-components)
10. [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware Requirements

**Minimum Specifications:**
- **CPU**: 8-core Intel/AMD processor (3.0GHz+)
- **RAM**: 32GB DDR4
- **GPU**: NVIDIA RTX 3080 or better (12GB+ VRAM)
- **Storage**: 2TB NVMe SSD
- **Network**: 100Mbps+ internet connection

**Recommended Specifications:**
- **CPU**: 16-core Intel/AMD processor (3.5GHz+)
- **RAM**: 64GB DDR4
- **GPU**: NVIDIA RTX 4090 (24GB VRAM)
- **Storage**: 4TB NVMe SSD
- **Network**: 1Gbps+ internet connection

### Operating System Support
- **Primary**: Windows 10/11 (64-bit)
- **Secondary**: Linux Ubuntu 20.04+ (with CUDA support)
- **Not Supported**: macOS (due to CUDA requirements)

## Prerequisites

### Core Software Dependencies

1. **Python 3.9-3.11**
   ```bash
   # Download from python.org or use conda
   python --version  # Should be 3.9.x to 3.11.x
   ```

2. **NVIDIA CUDA Toolkit 11.8+**
   ```bash
   # Download from developer.nvidia.com
   nvcc --version  # Verify installation
   nvidia-smi      # Check GPU status
   ```

3. **FFmpeg with NVENC Support**
   ```bash
   # Windows: Download from ffmpeg.org
   # Linux: sudo apt install ffmpeg
   ffmpeg -version  # Verify installation
   ```

4. **Git**
   ```bash
   git --version
   ```

## Core Dependencies

### AI/ML Platforms

#### 1. ComfyUI Installation
```bash
# Clone ComfyUI repository
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies
pip install -r requirements.txt

# Download required models (place in ComfyUI/models/)
# - FLUX models for image generation
# - Video generation models
# - Face recognition models
```

#### 2. Ollama Setup
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download required model
ollama pull gemma2:12b

# Verify installation
ollama list
```

#### 3. Topaz Video AI (Optional - for 4K upscaling)
```bash
# Download from topazlabs.com
# Install to: C:\Program Files\Topaz Labs LLC\Topaz Video AI\
# Required models: chr-2, prob-4, amq-13
```

### Python Environment Setup

```bash
# Create virtual environment
python -m venv dancer_env
source dancer_env/bin/activate  # Linux/Mac
# OR
dancer_env\Scripts\activate  # Windows

# Install requirements
pip install -r requirements.txt
```

## Directory Structure

### Required Directory Layout
```
/path/to/dancer/
├── api_server_v5_without_faceswap.py
├── main_automation_without_faceswap.py
├── run_pipeline.py
├── beat_sync_single.py
├── upscale_4k_parallel.py
├── crop_to_reels.py
├── youtube_metadata_generator.py
├── youtube_shorts_poster.py
├── requirements.txt
├── .env
├── config4_without_faceswap.json
├── base_workflows/
│   ├── API_flux_and_reactor_without_faceswap.json
│   └── api_wanvideo_without_faceswap.json
├── source_faces/
│   └── [face_image_files.jpg]
├── music/
│   └── [background_music.mp3]
├── instagram_audio/
│   └── [instagram_audio_files.mp4]
├── logs/
├── telegram_approvals/
├── output_runs_consolidated/
└── temp_video_starts/
```

### External Directory Dependencies
```
# ComfyUI directories (configurable paths)
H:/dancers_content/                    # Output base directory
D:/Comfy_UI_V20/ComfyUI/input/        # ComfyUI input directory
D:/Comfy_UI_V20/ComfyUI/output/       # ComfyUI output directory

# Topaz Video AI (Windows)
C:/Program Files/Topaz Labs LLC/Topaz Video AI/
C:/ProgramData/Topaz Labs LLC/Topaz Video AI/models/
```

## Configuration Files

### 1. Environment Variables (.env)
```bash
# Create .env file
cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Instagram Configuration (if using)
INSTA_USERNAME=your_instagram_username
INSTA_PASSWORD=your_instagram_password
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token

# YouTube API Configuration
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret

# OpenAI API (if using GPT features)
OPENAI_API_KEY=your_openai_api_key

# Paths Configuration
COMFYUI_INPUT_PATH=D:/Comfy_UI_V20/ComfyUI/input
COMFYUI_OUTPUT_PATH=H:/dancers_content
EOF
```

### 2. Main Configuration (config4_without_faceswap.json)
```json
{
  "comfyui_api_url": "http://127.0.0.1:8188",
  "base_workflow_image": "./base_workflows/API_flux_and_reactor_without_faceswap.json",
  "base_workflow_video": "./base_workflows/api_wanvideo_without_faceswap.json",
  "source_faces_path": "./source_faces",
  "output_folder": "H:/dancers_content",
  "ollama_model": "gemma2:12b",
  "ollama_url": "http://localhost:11434/api/generate",
  "generation_settings": {
    "batch_size": 10,
    "max_concurrent": 3,
    "timeout_seconds": 300
  },
  "approval_settings": {
    "web_ui_port": 5005,
    "require_telegram_approval": true,
    "auto_approve_threshold": 0.8
  }
}
```

### 3. ComfyUI Workflow Files
The workflow JSON files must contain specific node titles:
- `API_Prompt_Input` - Text prompt input
- `API_Face_Input` - Face image input
- `API_Seed_Input` - Seed for randomization
- `API_Output_Prefix` - Output filename prefix
- `API_Image_Output_SaveNode` - Image save node
- `API_Video_Start_Image` - Video start image (video workflow only)

## External Services Setup

### Required API Keys and Services

The pipeline requires several external API keys and services. Follow these detailed steps to obtain and configure each one:

### 1. Telegram Bot API Setup (Required for Mobile Approval)

#### Step 1: Create a Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Start a chat with BotFather
3. Send `/newbot` command
4. Choose a name for your bot (e.g., "Dancer Content Approval Bot")
5. Choose a unique username ending with "bot" (e.g., "dancer_approval_bot")
6. **Save the Bot Token** - You'll receive something like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

#### Step 2: Get Your Chat ID
1. Send a message to your newly created bot
2. Visit: `https://api.telegram.org/bot<YourBOTToken>/getUpdates`
3. Replace `<YourBOTToken>` with your actual bot token
4. Look for `"chat":{"id":` in the response
5. **Save the Chat ID** - It will be a number like: `123456789`

#### Step 3: Configure Bot Permissions
1. In BotFather, send `/setprivacy`
2. Select your bot
3. Choose "Disable" to allow the bot to read all messages
4. Send `/setcommands` to set up bot commands:
   ```
   approve - Approve the current image
   reject - Reject the current image
   status - Check approval status
   help - Show available commands
   ```

### 2. Google APIs Setup (Required for YouTube Upload)

#### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" or select existing project
3. Name your project (e.g., "Dancer Content Pipeline")
4. Note your **Project ID**

#### Step 2: Enable Required APIs
1. Go to "APIs & Services" > "Library"
2. Enable the following APIs:
   - **YouTube Data API v3**
   - **Google Drive API** (for backup storage)
   - **Google Sheets API** (for analytics tracking)

#### Step 3: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "+ CREATE CREDENTIALS" > "OAuth client ID"
3. Choose "Desktop application"
4. Name it "Dancer Pipeline Client"
5. **Download the JSON file** and rename it to `client_secret.json`
6. Place this file in your project root directory

#### Step 4: Set up OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in required fields:
   - App name: "Dancer Content Pipeline"
   - User support email: your email
   - Developer contact: your email
4. Add scopes:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/drive.file`

#### Step 5: Run Google OAuth Setup
```bash
# Run authentication script
python autenticate_google.py
# Follow browser prompts to authorize
# This creates token.json and youtube_token.pickle
```

### 3. Instagram Integration Setup (Optional)

#### Step 1: Create Meta Developer Account
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Log in with your Facebook account
3. Click "Get Started" and complete verification

#### Step 2: Create App
1. Click "Create App"
2. Choose "Consumer" app type
3. Enter app details:
   - App Name: "Dancer Content Pipeline"
   - Contact Email: your email

#### Step 3: Add Instagram Basic Display
1. In your app dashboard, click "Add Product"
2. Find "Instagram Basic Display" and click "Set Up"
3. Go to "Basic Display" > "Roles" > "Roles"
4. Add Instagram Testers (your Instagram account)

#### Step 4: Get Access Tokens
1. Generate User Token through Instagram Basic Display
2. **Save the Access Token** and **User ID**

### 4. AI Model APIs (Optional - for External LLMs)

#### OpenAI API (if using GPT models)
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create account and verify phone number
3. Go to "API Keys" section
4. Click "Create new secret key"
5. **Save the API Key** - starts with `sk-`

#### Anthropic API (if using Claude models)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create account and complete verification
3. Go to "API Keys" section
4. Click "Create Key"
5. **Save the API Key** - starts with `sk-ant-`

### 5. Environment Variables Configuration

**Create `.env` file in project root:**
```env
# === TELEGRAM CONFIGURATION (REQUIRED) ===
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# === GOOGLE APIS (REQUIRED FOR YOUTUBE) ===
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_PROJECT_ID=your-project-id

# === INSTAGRAM (OPTIONAL) ===
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_USER_ID=your_instagram_user_id
INSTAGRAM_APP_ID=your_meta_app_id
INSTAGRAM_APP_SECRET=your_meta_app_secret

# === EXTERNAL AI APIS (OPTIONAL) ===
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here

# === PIPELINE CONFIGURATION ===
PIPELINE_MODE=production
LOG_LEVEL=INFO
MAX_CONCURRENT_JOBS=3
AUTO_CLEANUP=true
```

### 6. API Connection Testing

**Test all API connections:**
```bash
# Test Telegram Bot
python -c "
import os
from dotenv import load_dotenv
import requests
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
if token:
    resp = requests.get(f'https://api.telegram.org/bot{token}/getMe')
    print('Telegram bot test:', resp.json())
else:
    print('TELEGRAM_BOT_TOKEN not found in .env')
"

# Test Google APIs (after OAuth setup)
python -c "
import os
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
print('Google API libraries available')
"

# Test Ollama
curl http://localhost:11434/api/generate -d '{"model":"gemma2:12b","prompt":"test"}'

# Test ComfyUI
curl http://localhost:8188/system_stats
```

## Installation Steps

### Step 1: Clone Repository
```bash
git clone <repository_url>
cd dancer
```

### Step 2: Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Create Directories
```bash
# Create required directories
mkdir -p logs telegram_approvals output_runs_consolidated temp_video_starts
mkdir -p source_faces music instagram_audio
```

### Step 4: Configure Services
```bash
# Start ComfyUI (in separate terminal)
cd /path/to/ComfyUI
python main.py --listen 127.0.0.1 --port 8188

# Start Ollama (in separate terminal)
ollama serve

# Verify services are running
curl http://127.0.0.1:8188/history  # ComfyUI
curl http://localhost:11434/api/tags  # Ollama
```

### Step 5: Add Content Assets
```bash
# Add face images to source_faces/
cp your_face_images.jpg source_faces/

# Add background music to music/
cp your_music_files.mp3 music/

# Add Instagram audio clips to instagram_audio/
cp your_audio_clips.mp4 instagram_audio/
```

### Step 6: Test Installation
```bash
# Test pipeline components
python api_server_v5_without_faceswap.py &  # Start API server
python -c "import requests; print(requests.get('http://127.0.0.1:8000/health').text)"

# Run complete pipeline
python run_pipeline.py
```

## Pipeline Components

### Component Overview

1. **API Server** (`api_server_v5_without_faceswap.py`)
   - **Port**: 8000
   - **Function**: Bridge between main automation and ComfyUI
   - **Endpoints**: `/generate_image`, `/generate_video`

2. **Main Automation** (`main_automation_without_faceswap.py`)
   - **Function**: Core content generation and approval workflow
   - **Dependencies**: Ollama, ComfyUI, Telegram Bot
   - **Output**: Approved images and videos

3. **Beat Synchronization** (`beat_sync_single.py`)
   - **Function**: Synchronize videos with music beats
   - **Dependencies**: librosa, moviepy, FFmpeg
   - **Input**: Videos and audio files
   - **Output**: Beat-synchronized videos

4. **4K Upscaling** (`upscale_4k_parallel.py`)
   - **Function**: AI-powered video upscaling to 4K
   - **Dependencies**: Topaz Video AI, NVIDIA GPU
   - **Hardware**: High-end GPU with 12GB+ VRAM

5. **Crop to Reels** (`crop_to_reels.py`)
   - **Function**: Convert videos to social media formats
   - **Output**: 9:16 aspect ratio videos for Instagram/TikTok

6. **Metadata Generation** (`youtube_metadata_generator.py`)
   - **Function**: AI-generated titles, descriptions, tags
   - **Dependencies**: OpenAI API or local AI models

7. **YouTube Upload** (`youtube_shorts_poster.py`)
   - **Function**: Automated YouTube Shorts upload
   - **Dependencies**: YouTube Data API v3, OAuth tokens

### Service Dependencies

**Always Running Services:**
- ComfyUI (port 8188)
- Ollama (port 11434)
- API Server (port 8000)

**On-Demand Services:**
- Flask Web UI (port 5005) - during approval phase
- Telegram Bot - for mobile approvals
- Topaz Video AI - during upscaling phase

## Port Configuration

```bash
# Required ports (ensure not blocked by firewall)
8188    # ComfyUI API
11434   # Ollama API  
8000    # Custom API Server
5005    # Flask Web UI (approval)
443     # HTTPS (YouTube, Telegram APIs)
80      # HTTP (redirects)
```

## Performance Optimization

### GPU Configuration
```bash
# Set environment variables for optimal GPU usage
export CUDA_VISIBLE_DEVICES=0
export TVAI_MODEL_DIR="C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models"

# Monitor GPU usage
nvidia-smi -l 1  # Continuous monitoring
```

### Memory Management
```python
# In config files, adjust batch sizes based on available RAM/VRAM
{
  "generation_settings": {
    "batch_size": 5,        # Reduce if out of memory
    "max_concurrent": 2     # Reduce for less VRAM
  }
}
```

## Troubleshooting

### Common Issues

#### 1. CUDA Out of Memory
```bash
# Solution: Reduce batch sizes in config
# Check GPU memory usage: nvidia-smi
# Restart ComfyUI to clear VRAM
```

#### 2. ComfyUI Connection Failed
```bash
# Check if ComfyUI is running
curl http://127.0.0.1:8188/history

# Check firewall/antivirus blocking ports
# Restart ComfyUI with correct parameters
python main.py --listen 127.0.0.1 --port 8188
```

#### 3. Ollama Model Not Found
```bash
# Check available models
ollama list

# Download required model
ollama pull gemma2:12b

# Verify model is working
ollama run gemma2:12b "test prompt"
```

#### 4. FFmpeg/Video Processing Errors
```bash
# Check FFmpeg installation
ffmpeg -version

# Check codec support
ffmpeg -codecs | grep h264

# Install additional codecs if needed
```

#### 5. Telegram Bot Not Responding
```bash
# Test bot token
curl https://api.telegram.org/bot<TOKEN>/getMe

# Check webhook/polling configuration
# Verify chat ID is correct
```

### Log Files

**Important Log Locations:**
```bash
./logs/                           # Application logs
./pipeline_log.txt               # Pipeline execution log
ComfyUI/comfyui.log             # ComfyUI logs
%TEMP%/ollama.log               # Ollama logs (Windows)
```

### Performance Monitoring

```bash
# System monitoring
htop                    # CPU/RAM usage
nvidia-smi -l 1        # GPU monitoring
df -h                   # Disk usage
netstat -tuln          # Port usage

# Application monitoring
tail -f logs/automation_*.log    # Real-time log monitoring
```

## Security Considerations

### API Keys and Tokens
- Store all sensitive credentials in `.env` file
- Never commit `.env` to version control
- Use environment variables in production
- Regularly rotate API keys

### Network Security
- Run services on localhost only in production
- Use reverse proxy (nginx) for external access
- Implement rate limiting for API endpoints
- Use HTTPS for all external communications

### File Permissions
```bash
# Set appropriate permissions
chmod 600 .env                    # Environment file
chmod 700 source_faces/           # Face images directory
chmod 755 *.py                    # Python scripts
```

## Maintenance

### Regular Tasks
1. **Daily**: Monitor log files for errors
2. **Weekly**: Clean up temporary files and old outputs
3. **Monthly**: Update Python dependencies
4. **Quarterly**: Update ComfyUI and Ollama models

### Backup Strategy
```bash
# Critical files to backup
.env                              # Environment configuration
config4_without_faceswap.json    # Main configuration
base_workflows/                   # ComfyUI workflows
source_faces/                     # Face images
client_secret.json               # Google OAuth
token.json                       # Authentication tokens
```

### Updates and Upgrades
```bash
# Update Python packages
pip install -r requirements.txt --upgrade

# Update ComfyUI
cd ComfyUI && git pull

# Update Ollama models
ollama pull gemma2:12b
```

## Production Deployment

### Systemd Services (Linux)
```bash
# Create service file: /etc/systemd/system/dancer-api.service
[Unit]
Description=Dancer API Server
After=network.target

[Service]
Type=simple
User=dancer
WorkingDirectory=/path/to/dancer
Environment=PATH=/path/to/dancer/venv/bin
ExecStart=/path/to/dancer/venv/bin/python api_server_v5_without_faceswap.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl enable dancer-api
sudo systemctl start dancer-api
```

### Process Management
```bash
# Use supervisor or PM2 for process management
# Install supervisor: sudo apt install supervisor

# Create config: /etc/supervisor/conf.d/dancer.conf
[program:dancer-api]
command=/path/to/dancer/venv/bin/python api_server_v5_without_faceswap.py
directory=/path/to/dancer
user=dancer
autostart=true
autorestart=true
```

## Support and Resources

### Documentation Links
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Ollama Documentation](https://ollama.ai/docs)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [YouTube API Documentation](https://developers.google.com/youtube/v3)

### Community Support
- ComfyUI Discord Community
- Ollama GitHub Issues
- Stack Overflow for Python/AI questions

---

**Last Updated**: 2025-06-15
**Version**: 1.0
**Tested On**: Windows 11, Ubuntu 22.04 LTS