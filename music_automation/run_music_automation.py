#!/usr/bin/env python3
"""
Music Automation Entry Point

This script provides a unified entry point for the Music-Based Image & Video Generation Automation system.
It handles the complete workflow from audio analysis to final video compilation.

Usage:
    python run_music_automation.py [options]

Options:
    --mode: automation|audio-only|video-only|beat-sync|test
    --config: path to configuration file
    --audio: path to audio file (overrides config)
    --debug: enable debug mode
    --test: run in test mode with limited processing
"""

import os
import sys
import argparse
import logging
import time
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Load environment variables from parent directory
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Add current directory to Python path for relative imports
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup logging configuration"""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(logs_dir / f'automation_main_{int(time.time())}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger('music_automation')

def validate_environment() -> bool:
    """Validate that all required components are available"""
    logger = logging.getLogger('music_automation')
    logger.info("Validating environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        logger.error(f"Python 3.11+ required, found {sys.version}")
        return False
    
    # Check required directories
    required_dirs = [
        'core', 'audio_processing', 'video_compilation', 
        'config', 'config/base_workflows'
    ]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            logger.error(f"Required directory missing: {dir_path}")
            return False
    
    # Check configuration file
    config_path = Path('config/config_music.json')
    if not config_path.exists():
        logger.error(f"Configuration file missing: {config_path}")
        return False
    
    # Check workflow files
    workflow_path = Path('config/base_workflows/API_flux_without_faceswap_music.json')
    if not workflow_path.exists():
        logger.error(f"Workflow file missing: {workflow_path}")
        return False
    
    # Test imports
    try:
        import requests
        import fastapi
        import librosa
        import numpy
        logger.info("All required packages available")
    except ImportError as e:
        logger.error(f"Missing required package: {e}")
        return False
    
    logger.info("Environment validation passed")
    return True

def load_configuration(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file"""
    logger = logging.getLogger('music_automation')
    
    if config_path is None:
        config_path = 'config/config_music.json'
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    logger.info(f"Configuration loaded from {config_file}")
    return config

def check_comfyui_running(config: Dict[str, Any]) -> bool:
    """Check if ComfyUI is running and accessible"""
    logger = logging.getLogger('music_automation')
    
    try:
        import requests
        comfyui_url = config.get('comfyui_api_url', 'http://127.0.0.1:8188')
        
        logger.info(f"Checking ComfyUI at {comfyui_url}")
        response = requests.get(f"{comfyui_url}/system_stats", timeout=10)
        
        if response.status_code == 200:
            logger.info("ComfyUI is running and accessible")
            return True
        else:
            logger.warning(f"ComfyUI responded with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"ComfyUI not accessible: {e}")
        logger.error("Please start ComfyUI first: python main.py")
        return False

def start_api_server(config: Dict[str, Any], test_mode: bool = False) -> subprocess.Popen:
    """Start the music API server"""
    logger = logging.getLogger('music_automation')
    
    logger.info("Starting music API server...")
    
    env = os.environ.copy()
    if test_mode:
        env['TEST_MODE'] = 'true'
    
    try:
        api_process = subprocess.Popen([
            sys.executable, 'core/api_server_v5_music.py'
        ], env=env)
        
        # Wait a moment for server to start
        time.sleep(5)
        
        # Check if server is responding
        import requests
        api_url = config.get('api_server_url', 'http://127.0.0.1:8006')
        
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("Music API server started successfully")
                return api_process
            else:
                logger.error(f"API server health check failed: {response.status_code}")
                api_process.terminate()
                return None
        except requests.exceptions.RequestException:
            logger.error("API server not responding to health checks")
            api_process.terminate()
            return None
            
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return None

def run_audio_analysis(audio_file: Optional[str] = None) -> bool:
    """Run audio analysis to generate prompts"""
    logger = logging.getLogger('music_automation')
    
    logger.info("Starting audio analysis...")
    
    try:
        env = os.environ.copy()
        if audio_file:
            env['AUDIO_FILE_OVERRIDE'] = audio_file
        
        result = subprocess.run([
            sys.executable, 'audio_processing/audio_to_prompts_generator.py'
        ], env=env, timeout=600, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Audio analysis completed successfully")
            logger.debug(f"Audio analysis output: {result.stdout}")
            return True
        else:
            logger.error(f"Audio analysis failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Audio analysis timed out")
        return False
    except Exception as e:
        logger.error(f"Audio analysis error: {e}")
        return False

def run_main_automation(test_mode: bool = False) -> bool:
    """Run the main automation pipeline"""
    logger = logging.getLogger('music_automation')
    
    logger.info("Starting main automation pipeline...")
    
    try:
        env = os.environ.copy()
        if test_mode:
            env['TEST_MODE'] = 'true'
            env['MAX_IMAGES'] = '2'  # Limit for testing
        
        result = subprocess.run([
            sys.executable, 'core/main_automation_music.py'
        ], env=env, timeout=3600, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Main automation completed successfully")
            logger.debug(f"Automation output: {result.stdout}")
            return True
        else:
            logger.error(f"Main automation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Main automation timed out")
        return False
    except Exception as e:
        logger.error(f"Main automation error: {e}")
        return False

def run_beat_sync_compilation(test_mode: bool = False) -> bool:
    """Run beat sync video compilation"""
    logger = logging.getLogger('music_automation')
    
    logger.info("Starting beat sync compilation...")
    
    try:
        env = os.environ.copy()
        if test_mode:
            env['TEST_MODE'] = 'true'
        
        result = subprocess.run([
            sys.executable, 'video_compilation/music_video_beat_sync_compiler.py'
        ], env=env, timeout=1800, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Beat sync compilation completed successfully")
            logger.debug(f"Beat sync output: {result.stdout}")
            return True
        else:
            logger.error(f"Beat sync compilation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Beat sync compilation timed out")
        return False
    except Exception as e:
        logger.error(f"Beat sync compilation error: {e}")
        return False

def run_test_suite() -> bool:
    """Run the test suite to validate functionality"""
    logger = logging.getLogger('music_automation')
    
    logger.info("Running test suite...")
    
    try:
        result = subprocess.run([
            sys.executable, 'debug_tools/test_all_components.py'
        ], timeout=300, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Test suite passed")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"Test suite failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Test suite timed out")
        return False
    except FileNotFoundError:
        logger.warning("Test suite not found, skipping...")
        return True
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Music Automation System')
    parser.add_argument('--mode', choices=['automation', 'audio-only', 'video-only', 'beat-sync', 'test'], 
                       default='automation', help='Execution mode')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--audio', help='Path to audio file (overrides config)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.debug)
    logger.info("Starting Music Automation System")
    logger.info(f"Mode: {args.mode}, Test: {args.test}, Debug: {args.debug}")
    
    try:
        # Validate environment
        if not validate_environment():
            logger.error("Environment validation failed")
            return 1
        
        # Load configuration
        config = load_configuration(args.config)
        
        # For test mode, run test suite first
        if args.mode == 'test':
            if run_test_suite():
                logger.info("Test mode completed successfully")
                return 0
            else:
                logger.error("Test mode failed")
                return 1
        
        # Check ComfyUI for modes that need it
        if args.mode in ['automation', 'video-only']:
            if not check_comfyui_running(config):
                logger.error("ComfyUI is required but not running")
                return 1
        
        # Start API server for modes that need it
        api_process = None
        if args.mode in ['automation', 'video-only']:
            api_process = start_api_server(config, args.test)
            if not api_process:
                logger.error("Failed to start API server")
                return 1
        
        try:
            # Execute based on mode
            success = True
            
            if args.mode == 'automation':
                # Full automation pipeline
                success &= run_audio_analysis(args.audio)
                if success:
                    success &= run_main_automation(args.test)
                if success:
                    success &= run_beat_sync_compilation(args.test)
                    
            elif args.mode == 'audio-only':
                success = run_audio_analysis(args.audio)
                
            elif args.mode == 'video-only':
                success = run_main_automation(args.test)
                
            elif args.mode == 'beat-sync':
                success = run_beat_sync_compilation(args.test)
            
            if success:
                logger.info(f"Music automation ({args.mode}) completed successfully")
                return 0
            else:
                logger.error(f"Music automation ({args.mode}) failed")
                return 1
                
        finally:
            # Cleanup API server
            if api_process:
                logger.info("Stopping API server...")
                api_process.terminate()
                try:
                    api_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    api_process.kill()
                    logger.warning("API server force killed")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())