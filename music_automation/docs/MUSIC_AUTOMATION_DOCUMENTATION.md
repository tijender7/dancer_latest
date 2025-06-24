# Music-Based Image & Video Generation Automation

## Overview

The Music-Based Image & Video Generation Automation is a comprehensive system that analyzes music files to generate themed images and videos featuring Lord Shiva and Hindu deity content. The system uses AI-powered music analysis to create contextually relevant visual content synchronized with musical segments.

## System Architecture

### Core Components

1. **Audio Analysis Pipeline** (`audio_to_prompts_generator.py`)
2. **Music Automation Pipeline** (`main_automation_music.py`)
3. **API Server** (`api_server_v5_music.py`)
4. **Pipeline Orchestrator** (`run_pipeline_music.py`)
5. **ComfyUI Workflows** (Image & Video generation)
6. **Telegram Approval System**

## Prerequisites

### System Requirements

- **Python 3.11+**
- **ComfyUI** (running on port 8188)
- **GPU** with sufficient VRAM for AI model processing
- **Windows/Linux** compatible environment

### Required Python Packages

```bash
pip install fastapi uvicorn flask tqdm google-generativeai python-dotenv pillow requests
```

### ComfyUI Models Required

- **WanVideo Models**:
  - `Wan2_1-I2V-14B-480P_fp8_e5m2.safetensors`
  - `Wan2_1_VAE_bf16.safetensors`
  - `umt5-xxl-enc-bf16.safetensors`
  - Various LoRA files for enhancement

- **Flux Models** for image generation
- **Text Encoders** for prompt processing

### Environment Configuration

Create a `.env` file with:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
GOOGLE_API_KEY=your_google_api_key
```

## File Structure

```
ComfyUI/output/dancer/
├── main_automation_music.py          # Main automation logic
├── api_server_v5_music.py            # FastAPI server for ComfyUI integration
├── run_pipeline_music.py             # Pipeline orchestrator
├── audio_to_prompts_generator.py     # Music analysis system
├── config_music.json                 # Configuration file
├── base_workflows/
│   ├── API_flux_without_faceswap_music.json  # Image generation workflow
│   └── api_wanvideo_without_faceswap.json    # Video generation workflow
├── telegram_approvals/               # Telegram integration files
├── output_runs_music/               # Generated content output
└── logs/                           # System logs
```

## Configuration

### config_music.json

```json
{
    "ollama_model": "gemma3:12b",
    "ollama_api_url": "http://localhost:11434/api/generate",
    "num_prompts": "dynamic",
    "comfyui_api_url": "http://127.0.0.1:8188",
    "api_server_url": "http://127.0.0.1:8006",
    "base_workflow_image": "base_workflows/API_flux_without_faceswap_music.json",
    "base_workflow_video": "base_workflows/api_wanvideo_without_faceswap.json",
    "source_faces_path": "source_faces",
    "output_folder": "output_runs_music",
    "prompt_source": "latest_run_folder"
}
```

## Workflow Process

### Stage 1: Music Analysis
1. **Input**: Audio files (MP3, WAV, etc.)
2. **Processing**: AI analysis using Google's Gemini API
3. **Output**: Structured prompts with timestamps and themes
4. **Storage**: `H:/dancers_content/Run_YYYYMMDD_HHMMSS_music/`

### Stage 2: Image Generation
1. **Prompt Enhancement**: Deity-specific enhancements added
2. **ComfyUI Integration**: Flux-based image generation
3. **Batch Processing**: Multiple images per music segment
4. **Quality Control**: AI-generated variations

### Stage 3: Telegram Approval
1. **Image Delivery**: Generated images sent to Telegram
2. **User Review**: Manual approval/rejection via Telegram bot
3. **Status Tracking**: Real-time approval monitoring
4. **Decision Recording**: JSON-based approval storage

### Stage 4: Video Generation
1. **Approved Image Processing**: Copy to temp directory
2. **Prompt Enhancement**: Deity-specific visual elements
3. **WanVideo Processing**: I2V (Image-to-Video) generation
4. **Output**: MP4 videos with motion and effects

### Stage 5: Cleanup and Organization
1. **Temp File Cleanup**: Remove temporary processing files
2. **Output Organization**: Structure final results
3. **Log Management**: Comprehensive logging throughout

## Key Features

### Intelligent Music Analysis
- **Temporal Segmentation**: Divides music into meaningful segments
- **Thematic Recognition**: Identifies musical themes and moods
- **Cultural Context**: Hindu/Indian music pattern recognition
- **Prompt Generation**: Creates detailed visual descriptions

### Deity-Focused Content
- **Lord Shiva Themes**: Meditation, Nataraja, cosmic dance
- **Visual Enhancement**: Muscular, divine, ethereal characteristics
- **Cultural Authenticity**: Traditional Hindu iconography
- **Mood Adaptation**: Matches visual style to musical mood

### Advanced Video Generation
- **WanVideo Technology**: State-of-the-art I2V generation
- **Motion Synthesis**: Natural movement from static images
- **Effect Integration**: Mystical energy, divine light effects
- **Quality Optimization**: 832x480 resolution, 81 frames

### Telegram Integration
- **Real-time Approval**: Instant image review and approval
- **Batch Processing**: Handle multiple images efficiently
- **Status Monitoring**: Live progress tracking
- **User-Friendly Interface**: Simple approve/reject buttons

## API Endpoints

### Image Generation
```http
POST /generate/image
Content-Type: application/json

{
    "prompt": "Enhanced deity prompt...",
    "segment_id": 1,
    "face": null,
    "output_subfolder": "Run_YYYYMMDD_HHMMSS_music_images/all_images",
    "filename_prefix_text": "music_segment",
    "video_start_image_path": null
}
```

### Video Generation
```http
POST /generate_video
Content-Type: application/json

{
    "prompt": "Enhanced deity prompt...",
    "segment_id": 1,
    "face": null,
    "output_subfolder": "Run_YYYYMMDD_HHMMSS_music_images/all_videos",
    "filename_prefix_text": "video_segment",
    "video_start_image_path": "temp_video_starts/start_001_batch0_timestamp.png"
}
```

## Usage Instructions

### 1. Initial Setup
```bash
# Start ComfyUI
cd D:/Comfy_UI_V20/ComfyUI
python main.py

# Verify environment
python -c "import requests, fastapi, flask, tqdm; print('Dependencies OK')"
```

### 2. Music Analysis
```bash
# Generate prompts from music
python audio_to_prompts_generator.py

# Verify output
ls H:/dancers_content/Run_*_music/
```

### 3. Run Automation
```bash
# Execute complete pipeline
python run_pipeline_music.py

# Monitor logs
tail -f logs/automation_music_pipeline_*.log
```

### 4. Telegram Approval
1. Wait for images to appear in Telegram
2. Review each image for quality and relevance
3. Tap ✅ **Approve** or ❌ **Reject**
4. System proceeds automatically after all reviews

### 5. Monitor Progress
- **Console Output**: Real-time status updates
- **ComfyUI Interface**: http://127.0.0.1:8188 (queue monitoring)
- **Log Files**: Detailed execution logs
- **Output Folders**: Generated content storage

## Output Structure

```
output_runs_music/Run_YYYYMMDD_HHMMSS_music_images/
├── all_images/                    # Generated images
│   ├── music_segment_001_00001_.png
│   ├── music_segment_001_00002_.png
│   └── ...
├── approved_images_for_video/     # Approved images
│   ├── approved_001_batch0_*.png
│   └── ...
├── all_videos/                    # Generated videos
│   ├── 001_batch0_video_raw_*.mp4
│   └── ...
└── approval_data.json           # Approval decisions
```

## Troubleshooting

### Common Issues

#### 1. ComfyUI Not Running
```bash
# Error: Connection refused to 127.0.0.1:8188
# Solution: Start ComfyUI first
cd D:/Comfy_UI_V20/ComfyUI
python main.py
```

#### 2. API Server Port Conflicts
```bash
# Error: Port 8006 already in use
# Solution: Kill existing process or change port
netstat -ano | findstr :8006
taskkill /PID <process_id> /F
```

#### 3. Missing Dependencies
```bash
# Error: ModuleNotFoundError
# Solution: Install missing packages
pip install fastapi uvicorn flask tqdm google-generativeai
```

#### 4. Telegram Bot Issues
```bash
# Error: Telegram approval not working
# Solution: Check .env file
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

#### 5. Black Video Generation
- **Check ComfyUI models**: Ensure WanVideo models are loaded
- **Verify image paths**: Check temp directory for image files
- **Monitor ComfyUI logs**: Look for processing errors
- **GPU memory**: Ensure sufficient VRAM available

#### 6. Unicode Encoding Errors
```bash
# Error: UnicodeEncodeError in logs
# Solution: Set environment variable
set PYTHONIOENCODING=utf-8
```

### Performance Optimization

#### System Resources
- **GPU Memory**: 8GB+ VRAM recommended
- **CPU**: Multi-core for parallel processing
- **Storage**: SSD for faster I/O operations
- **RAM**: 16GB+ for large model loading

#### Processing Settings
- **Batch Size**: Adjust based on available GPU memory
- **Timeout Values**: Increase for slower systems
- **Polling Intervals**: Optimize for responsiveness vs. resource usage

## Advanced Configuration

### Custom Prompt Enhancement
Modify `enhance_prompt_for_deity()` function in `main_automation_music.py`:

```python
def enhance_prompt_for_deity(original_prompt: str) -> str:
    enhancements = [
        "newfantasycore, powerful muscular god with divine purple eyes...",
        "newfantasycore, extremely buff deity with radiant silver eyes...",
        "newfantasycore, athletic divine being with glowing amber eyes..."
    ]
    # Custom enhancement logic here
    return enhanced_prompt
```

### Workflow Customization
Edit ComfyUI workflow files in `base_workflows/`:
- **Image Workflow**: Modify generation parameters, models, samplers
- **Video Workflow**: Adjust video length, resolution, effects

### API Server Extensions
Extend `api_server_v5_music.py` for custom endpoints:
- **Health monitoring**: Add status endpoints
- **Model management**: Runtime model switching
- **Custom processing**: Additional image/video effects

## Monitoring and Logging

### Log Levels
- **INFO**: General operation status
- **WARNING**: Non-critical issues
- **ERROR**: Operation failures
- **DEBUG**: Detailed execution trace

### Log Files
- **Main Pipeline**: `logs/automation_music_pipeline_*.log`
- **API Server**: `api_server_debug.log`
- **System Output**: `api_server_stdout.log`
- **Error Output**: `api_server_stderr.log`

### Monitoring Commands
```bash
# Real-time log monitoring
tail -f logs/automation_music_pipeline_*.log

# Error checking
grep "ERROR" logs/automation_music_pipeline_*.log

# Performance monitoring
grep "Processing time\|Generation time" logs/*.log
```

## Security Considerations

### API Security
- **Local Network Only**: APIs bound to localhost
- **No Authentication**: Designed for local use only
- **File Access**: Limited to configured directories

### Data Privacy
- **Local Processing**: All AI processing done locally
- **No External Uploads**: Images/videos never leave system
- **Telegram Integration**: Only approved content sent

### File System Security
- **Sandboxed Execution**: Limited file system access
- **Temp File Cleanup**: Automatic cleanup of temporary files
- **Output Isolation**: Generated content in dedicated folders

## Contributing

### Development Setup
1. **Fork Repository**: Create development branch
2. **Install Dependencies**: Set up development environment
3. **Test Configuration**: Verify all components working
4. **Make Changes**: Implement improvements
5. **Test Thoroughly**: Ensure no regressions

### Code Standards
- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Comment complex logic
- **Error Handling**: Comprehensive exception handling
- **Logging**: Appropriate log levels and messages

## Support and Maintenance

### Regular Maintenance
- **Log Rotation**: Manage log file sizes
- **Model Updates**: Keep AI models current
- **Dependency Updates**: Update Python packages
- **Performance Monitoring**: Track system performance

### Backup Strategy
- **Configuration Files**: Backup all config files
- **Workflow Files**: Version control ComfyUI workflows
- **Generated Content**: Archive important outputs
- **System State**: Document current working configuration

## Current Challenges & Development Status

### 🔴 Active Issues

#### 1. Black Video Generation (CRITICAL)
**Status**: 🔄 **IN PROGRESS** - Multiple attempts, partial success

**Problem Description**:
- Video generation completes successfully (200 OK responses)
- ComfyUI processes workflows without errors
- Generated videos contain only black screens instead of Lord Shiva images
- Approved images are correctly copied to temp directory
- Image paths are properly injected into video workflows

**Testing History**:

##### Attempt 1: Architecture Comparison (❌ Failed)
- **Action**: Compared music automation with working `main_automation_without_faceswap.py`
- **Findings**: Different API servers, different request structures
- **Result**: No improvement in video quality

##### Attempt 2: API Server Standardization (❌ Failed)
- **Action**: Switched music automation to use working API server (port 8000)
- **Changes**: Updated config to use `api_server_v5_without_faceswap.py`
- **Result**: Connection issues, incompatible request formats

##### Attempt 3: Request Format Alignment (❌ Failed)
- **Action**: Modified trigger_generation to match working automation
- **Changes**: Removed segment_id, updated parameter structure
- **Result**: API calls successful but videos still black

##### Attempt 4: Workflow Investigation (❌ Failed)
- **Action**: Analyzed video workflow floating point precision
- **Changes**: Fixed `1.0000000000000002` to `1.0` in workflow parameters
- **Result**: No change in video output quality

##### Attempt 5: Image Injection Verification (✅ Partial Success)
- **Action**: Created isolated test script for video generation
- **Findings**: Image paths correctly injected, API responds properly
- **Result**: Videos generate but remain black - confirms API communication works

##### Attempt 6: API Compatibility Fix (⚠️ Ongoing)
- **Action**: Made music API server compatible with working request format
- **Changes**: Optional segment_id, improved error handling
- **Current Status**: 500 Server Errors due to None segment_id formatting

**Current Symptoms**:
```
API Call -> generate_video: Preparing request...
✅ generate_video submitted successfully (HTTP 200)
ComfyUI Prompt ID: 'd42aeddb-933e-4773-9e0f-e8d1c2758fd3'
Video job confirmed complete.
Result: Black video files generated
```

**Root Cause Hypothesis**:
1. **WanVideo Model Configuration**: Model parameters not optimized for input images
2. **ComfyUI LoadImage Processing**: Image loading/preprocessing issues
3. **Video Workflow Settings**: Incorrect noise_aug_strength or latent processing
4. **GPU Memory Issues**: Insufficient VRAM during video generation

#### 2. Unicode Encoding Issues (HIGH)
**Status**: 🔄 **IDENTIFIED** - Workaround needed

**Problem Description**:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3b5'
```

**Impact**: API server logging fails, but functionality continues

**Testing History**:
- **Root Cause**: Emoji characters in log messages on Windows systems
- **Workaround**: Set `PYTHONIOENCODING=utf-8` environment variable
- **Permanent Fix**: Replace emoji characters with text equivalents

#### 3. Port Conflict Management (MEDIUM)
**Status**: 🔄 **RECURRING** - Manual intervention required

**Problem Description**:
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8006)
```

**Impact**: Cannot start multiple API server instances

**Testing History**:
- **Cause**: Previous API server instances not properly terminated
- **Current Solution**: Manual process termination required
- **Improvement Needed**: Automatic port cleanup and detection

### 🟡 Partially Resolved Issues

#### 1. 422 Unprocessable Entity Errors (✅ RESOLVED)
**Previous Problem**: Video generation requests failing with 422 errors

**Solution Applied**:
- Fixed parameter order in trigger_generation function
- Updated segment_id handling in API requests
- Standardized request format across automations

**Result**: Video requests now accepted (200 OK), but output quality issue remains

#### 2. Image Generation & Approval (✅ WORKING)
**Status**: ✅ **FULLY FUNCTIONAL**

**Components Working**:
- Music analysis and prompt generation
- Image generation via ComfyUI
- Telegram approval system
- Image copying and organization

**Test Results**:
- ✅ 8 images generated successfully
- ✅ 4 images approved via Telegram
- ✅ Approval status tracking working
- ✅ Image file management working

### 🟢 Successful Components

#### 1. Music Analysis Pipeline (✅ STABLE)
- **Gemini AI Integration**: Working reliably
- **Prompt Enhancement**: Deity-specific enhancements applied
- **Temporal Segmentation**: Music divided into meaningful segments
- **Output Structure**: Consistent JSON format generated

#### 2. Telegram Integration (✅ STABLE)
- **Image Delivery**: All generated images sent successfully
- **User Interface**: Approve/Reject buttons working
- **Status Tracking**: Real-time approval monitoring
- **Cleanup**: Automatic message deletion after decisions

#### 3. File Management (✅ STABLE)
- **Directory Structure**: Proper organization maintained
- **Image Copying**: Approved images copied to video input
- **Temp File Handling**: Temporary files created and cleaned up
- **Output Organization**: Structured result storage

### 🔬 Diagnostic Testing Performed

#### Test 1: Isolated Video Generation
**Purpose**: Isolate video generation from broader pipeline
**Method**: Created standalone test script with known good image
**Result**: 
- ✅ API connection successful
- ✅ Image path injection confirmed
- ✅ ComfyUI processing completed
- ❌ Output video still black

#### Test 2: Workflow Parameter Analysis  
**Purpose**: Identify problematic workflow settings
**Method**: Analyzed video workflow JSON for parameter issues
**Result**:
- ✅ LoadImage node correctly configured
- ✅ Node connections verified
- ✅ Floating point precision fixed
- ❌ Root cause not in workflow structure

#### Test 3: API Server Comparison
**Purpose**: Compare working vs. music API server behavior
**Method**: Detailed comparison of request/response patterns
**Result**:
- ✅ Request structures now aligned
- ✅ Error handling improved
- ✅ Logging standardized
- ❌ Video quality issue persists across servers

#### Test 4: ComfyUI Direct Testing
**Purpose**: Test video workflow directly in ComfyUI interface
**Status**: 🔄 **PENDING** - Requires manual ComfyUI testing

**Next Steps**:
1. Load video workflow in ComfyUI web interface
2. Manually set LoadImage node with approved Shiva image
3. Execute workflow and examine output
4. Compare with API-generated results

### 🎯 Current Investigation Focus

#### Primary Hypothesis: WanVideo Model Configuration
**Theory**: WanVideo models not properly configured for input image characteristics

**Investigation Plan**:
1. **Model Verification**: Confirm all WanVideo models loaded correctly
2. **Parameter Tuning**: Adjust noise_aug_strength, latent_strength values
3. **Resolution Testing**: Test with different image sizes/aspect ratios
4. **Manual Workflow Testing**: Use ComfyUI interface for direct testing

#### Secondary Hypothesis: GPU Memory Issues
**Theory**: Insufficient VRAM causing incomplete video processing

**Investigation Plan**:
1. **Memory Monitoring**: Track GPU memory usage during video generation
2. **Batch Size Reduction**: Process fewer frames per video
3. **Model Offloading**: Ensure proper model offloading between processes

#### Tertiary Hypothesis: Image Preprocessing Issues
**Theory**: Input images not properly preprocessed for video generation

**Investigation Plan**:
1. **Image Format Verification**: Confirm PNG format compatibility
2. **Color Space Analysis**: Check RGB vs other color spaces
3. **Resolution Matching**: Ensure input images match expected dimensions

### 🚀 Immediate Next Steps

#### Priority 1: Direct ComfyUI Testing
1. **Manual Workflow Execution**: Test video workflow in ComfyUI web interface
2. **Parameter Adjustment**: Modify WanVideo settings based on results
3. **Model Verification**: Confirm all required models are loaded

#### Priority 2: Unicode Encoding Fix
1. **Remove Emoji Characters**: Replace with text equivalents in API server
2. **Environment Configuration**: Document proper encoding setup
3. **Cross-Platform Testing**: Ensure compatibility across systems

#### Priority 3: Error Handling Improvement
1. **Port Management**: Implement automatic port detection and cleanup
2. **Graceful Degradation**: Better handling of partial failures
3. **Recovery Mechanisms**: Automatic retry with different parameters

### 📊 Success Metrics

#### Current Success Rate
- **Music Analysis**: 100% ✅
- **Image Generation**: 100% ✅  
- **Telegram Approval**: 100% ✅
- **Video API Calls**: 100% ✅
- **Video File Generation**: 100% ✅
- **Video Content Quality**: 0% ❌

#### Target Goals
- **End-to-End Success**: 90%+
- **Video Quality**: Recognizable Lord Shiva imagery
- **Processing Speed**: <5 minutes per video
- **Error Rate**: <5% for all operations

### 🔧 Development Environment Notes

#### Working Configuration
- **ComfyUI**: Version unknown, working on Windows
- **Python**: 3.11+
- **GPU**: CUDA-compatible with WanVideo models
- **API Servers**: Multiple versions tested

#### Known Good Components
- **main_automation_without_faceswap.py**: Proven working video generation
- **api_server_v5_without_faceswap.py**: Successful video processing
- **Telegram Integration**: Reliable approval system
- **ComfyUI Workflows**: Image generation confirmed working

#### Testing Environment Limitations
- **Manual Testing Required**: ComfyUI interface testing not automated
- **GPU Dependency**: Video testing requires specific hardware
- **Model Dependencies**: Large model files not easily versioned

---

## Version History

### Current Version: 2.1 (Development)
- **Video Generation Issues**: Ongoing investigation into black video problem
- **API Compatibility**: Enhanced compatibility between different API servers
- **Error Handling**: Improved error reporting and diagnostics
- **Testing Framework**: Isolated testing capabilities added

### Version 2.0 (Stable - Partial)
- **Enhanced Video Generation**: Attempted fixes for black video issues
- **Improved API Compatibility**: Standardized request formats
- **Better Error Handling**: Comprehensive error management
- **Optimized Performance**: Faster processing pipeline

### Future Enhancements
- **Video Quality Resolution**: Fix black video generation (Priority 1)
- **Multi-GPU Support**: Parallel processing across GPUs
- **Advanced Effects**: More sophisticated video effects
- **Batch Optimization**: Improved batch processing
- **Web Interface**: Browser-based control panel

---

*This documentation covers the complete Music-Based Image & Video Generation Automation system, including current challenges and development status. The black video generation issue remains the primary blocking issue for full system functionality.*