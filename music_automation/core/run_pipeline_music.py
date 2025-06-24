#!/usr/bin/env python
"""
Music Pipeline Orchestrator

This script orchestrates the complete music-based image and video generation pipeline:
1. Validates that ComfyUI is running
2. Ensures music prompts are available
3. Starts the music API server
4. Runs the main music automation
5. Handles cleanup and error recovery

Author: Claude Code Assistant
Date: 2025-06-19
"""

import os
import sys
import time
import subprocess
import requests
import logging
from pathlib import Path
from datetime import datetime

# Setup basic logging with UTF-8 encoding
log_file = f'run_pipeline_music_{datetime.now():%Y%m%d_%H%M%S}.log'

# Console handler with UTF-8 encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# File handler with UTF-8 encoding  
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)

# Constants
SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_OUTPUT_DIR_BASE = Path("H:/dancers_content")

def check_comfyui_running():
    """Check if ComfyUI is running and accessible"""
    logger.info("Checking if ComfyUI is running...")
    
    try:
        response = requests.get("http://127.0.0.1:8188/", timeout=10)
        if response.status_code == 200:
            logger.info("ComfyUI is running and accessible")
            return True
        else:
            logger.error(f"ComfyUI returned status: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"ComfyUI is not accessible: {e}")
        return False

def check_music_prompts_available():
    """Check if music prompts are available"""
    logger.info("Checking for available music prompts...")
    
    import glob
    pattern = str(COMFYUI_OUTPUT_DIR_BASE / "Run_*_music")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        logger.error("No music run folders found")
        logger.error("   Please run: python audio_to_prompts_generator.py first")
        return False
    
    # Check latest folder has prompts.json
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    latest_folder = Path(music_folders[0])
    prompts_file = latest_folder / "prompts.json"
    
    if not prompts_file.exists():
        logger.error(f"No prompts.json found in {latest_folder}")
        return False
    
    # Count segments
    try:
        import json
        with open(prompts_file, 'r') as f:
            data = json.load(f)
        
        segments = data.get("segments", [])
        metadata = data.get("metadata", {})
        
        logger.info(f"Found music prompts in: {latest_folder.name}")
        logger.info(f"   Song: {metadata.get('song_file', 'Unknown')}")
        logger.info(f"   Segments: {len(segments)}")
        logger.info(f"   Duration: {metadata.get('total_duration', 'Unknown')}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to read prompts file: {e}")
        return False

def check_config_files():
    """Check if required configuration files exist"""
    logger.info("Checking configuration files...")
    
    required_files = [
        ("config/config_music.json", SCRIPT_DIR.parent),
        ("api_server_v5_music.py", SCRIPT_DIR), 
        ("main_automation_music.py", SCRIPT_DIR),
        ("config/base_workflows/API_flux_without_faceswap_music.json", SCRIPT_DIR.parent)
    ]
    
    missing_files = []
    for file_name, base_path in required_files:
        file_path = base_path / file_name
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        logger.error("Missing required files:")
        for file_name in missing_files:
            logger.error(f"   - {file_name}")
        return False
    
    logger.info("All required configuration files found")
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    logger.info("Checking Python dependencies...")
    
    # Package mappings for import names vs pip names
    package_mappings = {
        "requests": "requests",
        "fastapi": "fastapi", 
        "uvicorn": "uvicorn",
        "flask": "flask",
        "tqdm": "tqdm",
        "google.generativeai": "google-generativeai"
    }
    
    missing_packages = []
    for import_name, pip_name in package_mappings.items():
        try:
            __import__(import_name)
            logger.info(f"  - {pip_name}: OK")
        except ImportError:
            missing_packages.append(pip_name)
            logger.error(f"  - {pip_name}: MISSING")
    
    if missing_packages:
        logger.error("Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        logger.error("Install with: pip install " + " ".join(missing_packages))
        return False
    
    logger.info("All required dependencies found")
    return True

def run_music_pipeline():
    """Run the main music automation pipeline"""
    logger.info("Starting music automation pipeline...")
    
    main_script = SCRIPT_DIR / "main_automation_music.py"
    
    try:
        # Run the main automation script
        result = subprocess.run(
            [sys.executable, str(main_script)],
            cwd=str(SCRIPT_DIR),
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Music pipeline completed successfully!")
            return True
        else:
            logger.error(f"Music pipeline failed with exit code: {result.returncode}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run music pipeline: {e}")
        return False

def print_banner():
    """Print startup banner"""
    print("\n" + "="*80)
    print("MUSIC: MUSIC-BASED IMAGE & VIDEO GENERATION PIPELINE")
    print("="*80)
    print("This pipeline will:")
    print("1. SEARCH: Validate system requirements")
    print("2. LOG: Load music prompts from latest analysis")
    print("3. 🎨 Generate images for each music segment")
    print("4. 📱 Provide Telegram approval interface")
    print("5. VIDEO: Prepare for video generation")
    print("="*80)
    print()

def print_summary(success: bool):
    """Print completion summary"""
    print("\n" + "="*80)
    if success:
        print("🎉 MUSIC PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("SUCCESS: What was accomplished:")
        print("   • Images generated for all music segments")
        print("   • Telegram approval process completed")  
        print("   • Approved images ready for video generation")
        print()
        print("📁 Check the output folder for results:")
        print(f"   {COMFYUI_OUTPUT_DIR_BASE}/Run_*_music_images/")
        print()
        print("VIDEO: Next steps:")
        print("   • Review approved images")
        print("   • Run video generation if desired")
        print("   • Upload content to social media")
    else:
        print("💥 MUSIC PIPELINE FAILED!")
        print("="*80)
        print("ERROR: Please check the logs above for error details")
        print("LOG: Common issues:")
        print("   • ComfyUI not running (start with: python main.py)")
        print("   • No music prompts available (run: python audio_to_prompts_generator.py)")
        print("   • Missing dependencies (install with pip)")
        print("   • Configuration file issues")
    print("="*80)

def main():
    """Main orchestration function"""
    print_banner()
    
    logger.info("Music Pipeline Orchestrator Starting...")
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print_summary(False)
        return False
    
    # Step 2: Check configuration files
    if not check_config_files():
        print_summary(False)
        return False
    
    # Step 3: Check ComfyUI
    if not check_comfyui_running():
        logger.error("Please start ComfyUI first:")
        logger.error("   1. Navigate to ComfyUI directory")
        logger.error("   2. Run: python main.py")
        logger.error("   3. Wait for 'Starting server' message")
        logger.error("   4. Then run this script again")
        print_summary(False)
        return False
    
    # Step 4: Check music prompts
    if not check_music_prompts_available():
        logger.error("Please generate music prompts first:")
        logger.error("   1. Run: python audio_to_prompts_generator.py")
        logger.error("   2. Wait for prompt generation to complete")
        logger.error("   3. Then run this script again")
        print_summary(False)
        return False
    
    # Step 5: Run the main pipeline
    logger.info("All prerequisites met. Starting main pipeline...")
    success = run_music_pipeline()
    
    # Step 6: Print summary
    print_summary(success)
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        print("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Unexpected error: {e}")
        sys.exit(1)