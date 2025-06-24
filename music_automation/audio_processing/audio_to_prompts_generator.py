#!/usr/bin/env python3
"""
Audio to Visual Prompts Generator
Converts audio files to detailed visual prompts for Flux image generation.

This script:
1. Finds the latest MP3 file in the songs directory
2. Creates a timestamped output folder
3. Uses Gemini API to analyze audio and generate prompts
4. Validates JSON output with robust parsing
5. Provides comprehensive logging for debugging

Author: Claude Code Assistant
Date: 2025-06-19
"""

import os
import sys
import json
import logging
import traceback
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import base64

# Load environment variables from parent .env file
def load_env_file(env_path: str = None):
    """Load environment variables from .env file"""
    if env_path is None:
        # Use parent directory .env file
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    else:
        env_path = Path(env_path)
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value
        print(f"SUCCESS: Loaded environment variables from {env_path}")
    else:
        print(f"WARNING: .env file not found at {env_path}")

# Load environment variables at startup
load_env_file()

# Google AI imports
try:
    import google.generativeai as genai
    import google.generativeai.types as genai_types
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    print("ERROR: Missing google-generativeai package. Install with: pip install google-generativeai")
    sys.exit(1)

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

# Paths
SONGS_DIR = Path(r"D:\Comfy_UI_V20\ComfyUI\output\dancer\songs")
OUTPUT_BASE_DIR = Path(r"H:\dancers_content")

# API Configuration
MODEL_NAME = "gemini-2.0-flash-exp"
API_RETRY_COUNT = 3
MAX_API_TIMEOUT = 300  # 5 minutes

# Segmentation Configuration (Optimization for efficiency)
MAX_SEGMENTS = 15  # Maximum number of segments to generate (limits computation)
MINIMUM_SEGMENT_DURATION = 5  # Minimum seconds per segment
DEFAULT_SEGMENT_DURATION = 5  # Default for short songs

# =============================================================================
# SEGMENTATION OPTIMIZATION FUNCTIONS
# =============================================================================

def calculate_optimal_segmentation(total_duration: float) -> tuple[int, float]:
    """
    Calculate optimal number of segments and duration per segment.
    
    Args:
        total_duration: Total song duration in seconds
        
    Returns:
        tuple: (segment_count, segment_duration)
    """
    # For short songs (75 seconds or less), use 5-second intervals
    max_duration_for_default = MAX_SEGMENTS * DEFAULT_SEGMENT_DURATION  # 75 seconds
    
    if total_duration <= max_duration_for_default:
        # Use default 5-second segments, but don't exceed MAX_SEGMENTS
        segment_count = min(MAX_SEGMENTS, int(total_duration // DEFAULT_SEGMENT_DURATION))
        segment_duration = DEFAULT_SEGMENT_DURATION
    else:
        # For longer songs, calculate dynamic segment duration
        segment_count = MAX_SEGMENTS
        segment_duration = total_duration / MAX_SEGMENTS
        
        # Ensure we don't go below minimum duration
        if segment_duration < MINIMUM_SEGMENT_DURATION:
            segment_duration = MINIMUM_SEGMENT_DURATION
            segment_count = int(total_duration // segment_duration)
    
    return segment_count, segment_duration

# Expected JSON Schema for validation
EXPECTED_JSON_SCHEMA = {
    "metadata": {
        "song_file": "string",
        "total_duration": "number",
        "total_segments": "number", 
        "generation_timestamp": "string",
        "processing_stats": {
            "total_api_calls": "number",
            "retry_count": "number",
            "total_processing_time": "string",
            "success_rate": "string"
        }
    },
    "segments": [
        {
            "segment_id": "number",
            "start_time": "string",
            "end_time": "string", 
            "primary_prompt": "string",
            "style_tags": ["array of strings"],
            "scene_type": "string",
            "energy_level": "string",
            "technical_specs": {
                "aspect_ratio": "string",
                "lighting": "string", 
                "camera_angle": "string",
                "composition": "string"
            }
        }
    ]
}

# =============================================================================
# LOGGING SETUP
# =============================================================================

class AudioToPromptsLogger:
    """Centralized logging configuration and management"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.logs_dir = output_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup multiple loggers
        self.main_logger = self._setup_logger("main", "execution.log")
        self.api_logger = self._setup_logger("gemini_api", "gemini_api.log")
        self.json_logger = self._setup_logger("json_parsing", "json_parsing.log")
        self.performance_logger = self._setup_logger("performance", "performance.log")
        
    def _setup_logger(self, name: str, filename: str) -> logging.Logger:
        """Setup individual logger with file and console handlers"""
        logger = logging.getLogger(f"AudioToPrompts.{name}")
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(self.logs_dir / filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

# =============================================================================
# JSON VALIDATION AND PARSING
# =============================================================================

class JSONValidator:
    """Handles JSON parsing, cleaning, and validation"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def clean_response(self, response_text: str) -> str:
        """Remove markdown code fences and clean whitespace"""
        self.logger.debug(f"Cleaning response text (length: {len(response_text)})")
        
        # Log original response preview
        preview = response_text[:300].replace('\n', '\\n')
        self.logger.debug(f"Original response preview: {preview}...")
        
        # Strip whitespace
        cleaned = response_text.strip()
        
        # Remove markdown code fences - more robust regex
        # Handles: ```json, ```, ```JSON, with optional whitespace
        cleaned = re.sub(r'^```(?:json|JSON)?\s*\n?', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        cleaned = re.sub(r'\n?\s*```\s*$', '', cleaned, flags=re.MULTILINE)
        
        # Additional cleanup for edge cases
        cleaned = re.sub(r'^`+', '', cleaned)  # Leading backticks
        cleaned = re.sub(r'`+$', '', cleaned)  # Trailing backticks
        
        cleaned = cleaned.strip()
        
        # Log cleaned result
        cleaned_preview = cleaned[:300].replace('\n', '\\n')
        self.logger.debug(f"Cleaned response preview: {cleaned_preview}...")
        
        return cleaned
    
    def validate_json_structure(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate JSON against expected schema"""
        errors = []
        
        # Check metadata
        if 'metadata' not in data:
            errors.append("Missing 'metadata' field")
        else:
            metadata = data['metadata']
            required_meta_fields = ['song_file', 'total_duration', 'total_segments', 'generation_timestamp', 'primary_deity']
            for field in required_meta_fields:
                if field not in metadata:
                    errors.append(f"Missing metadata field: {field}")
        
        # Check segments
        if 'segments' not in data:
            errors.append("Missing 'segments' field")
        elif not isinstance(data['segments'], list):
            errors.append("'segments' must be an array")
        else:
            for i, segment in enumerate(data['segments']):
                required_segment_fields = ['segment_id', 'start_time', 'end_time', 'primary_prompt']
                for field in required_segment_fields:
                    if field not in segment:
                        errors.append(f"Segment {i+1} missing field: {field}")
        
        is_valid = len(errors) == 0
        self.logger.debug(f"JSON validation result: {'VALID' if is_valid else 'INVALID'}")
        if errors:
            self.logger.warning(f"Validation errors: {errors}")
        
        return is_valid, errors
    
    def parse_and_validate(self, response_text: str) -> Tuple[Optional[Dict], List[str]]:
        """Clean, parse, and validate JSON response"""
        self.logger.info("Starting JSON parsing and validation")
        
        # Clean the response
        cleaned_text = self.clean_response(response_text)
        
        # Attempt to parse JSON
        try:
            parsed_data = json.loads(cleaned_text)
            self.logger.info("SUCCESS: JSON parsing successful")
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            self.logger.error(f"ERROR: {error_msg}")
            return None, [error_msg]
        
        # Validate structure
        is_valid, validation_errors = self.validate_json_structure(parsed_data)
        
        if is_valid:
            self.logger.info("SUCCESS: JSON validation successful")
            return parsed_data, []
        else:
            self.logger.error(f"ERROR: JSON validation failed: {validation_errors}")
            return parsed_data, validation_errors

# =============================================================================
# GEMINI API INTEGRATION
# =============================================================================

class GeminiAPIClient:
    """Handles all Gemini API interactions with retry logic and validation"""
    
    def __init__(self, api_logger: logging.Logger, json_logger: logging.Logger):
        self.api_logger = api_logger
        self.json_logger = json_logger
        self.json_validator = JSONValidator(json_logger)
        
        # Initialize Gemini
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=MODEL_NAME)
        
        # Generation config
        self.generation_config = genai_types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=8192
        )
        
        # Safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
    
    def upload_audio_file(self, audio_path: Path) -> Optional[Any]:
        """Upload audio file to Gemini with progress tracking"""
        self.api_logger.info(f"UPLOAD: Uploading audio file: {audio_path.name}")
        
        try:
            # Check file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            self.api_logger.info(f"File size: {file_size_mb:.2f} MB")
            
            # Upload file
            uploaded_file = genai.upload_file(path=str(audio_path), display_name=audio_path.name)
            self.api_logger.info(f"SUCCESS: Upload initiated. File ID: {uploaded_file.name}")
            
            # Wait for processing
            self.api_logger.info("WAIT: Waiting for file processing...")
            start_time = time.time()
            
            while True:
                file_status = genai.get_file(uploaded_file.name)
                elapsed = time.time() - start_time
                
                if file_status.state.name == "ACTIVE":
                    self.api_logger.info(f"SUCCESS: File processing complete ({elapsed:.1f}s)")
                    return file_status
                elif file_status.state.name == "FAILED":
                    self.api_logger.error("ERROR: File processing failed")
                    return None
                elif elapsed > MAX_API_TIMEOUT:
                    self.api_logger.error("ERROR: File processing timeout")
                    return None
                
                time.sleep(5)
                
        except Exception as e:
            self.api_logger.error(f"ERROR: Upload failed: {str(e)}")
            self.api_logger.debug(traceback.format_exc())
            return None
    
    def create_analysis_prompt(self, segment_count: int, segment_duration: float) -> str:
        """Create the structured prompt for deity-focused audio analysis with dynamic segmentation"""
        return f"""
Analyze this devotional audio file and generate deity-focused visual prompts for exactly {segment_count} segments distributed evenly across the entire song duration (approximately {segment_duration:.1f} seconds per segment), optimized for Flux image generation.

STEP 1: Listen to the audio and identify the PRIMARY DEITY being worshipped (Shiva, Ganesha, Krishna, Hanuman, Durga, etc.)

STEP 2: Generate prompts featuring ONLY that deity throughout the entire video with different poses, moods, and settings.

CRITICAL: Your response must be ONLY a valid JSON object with NO markdown formatting, NO code blocks, NO extra text.

Required JSON structure:
{{
    "metadata": {{
        "song_file": "filename.mp3",
        "total_duration": 145.5,
        "total_segments": {segment_count},
        "primary_deity": "Lord Shiva/Lord Ganesha/Lord Krishna/Lord Hanuman/Goddess Durga/etc.",
        "deity_attributes": ["cosmic dancer", "meditation master", "destroyer of evil", "lord of wisdom", "etc."],
        "consistent_theme": "All prompts focus on [DEITY NAME] with variations in pose, mood, and divine setting",
        "generation_timestamp": "{datetime.now().isoformat()}",
        "processing_stats": {{
            "total_api_calls": 1,
            "retry_count": 0,
            "total_processing_time": "processing_time",
            "success_rate": "100%"
        }}
    }},
    "segments": [
        {{
            "segment_id": 1,
            "start_time": "00:00",
            "end_time": "{int(segment_duration):02d}:{int((segment_duration % 60)):02d}",
            "primary_prompt": "Photorealistic image of [DEITY NAME] in [specific pose/action] with [divine attributes], [setting/background], [mood/energy matching audio], 16:9 aspect ratio, cinematic lighting, engaging composition perfect for YouTube thumbnail",
            "deity_pose": "meditation/dancing/blessing/cosmic form/etc.",
            "deity_mood": "serene/powerful/compassionate/fierce/joyful",
            "divine_setting": "Mount Kailash/lotus throne/cosmic space/temple/forest/etc.",
            "style_tags": ["photorealistic", "divine", "cinematic", "devotional"],
            "energy_level": "low/medium/high",
            "technical_specs": {{
                "aspect_ratio": "16:9",
                "lighting": "divine glow/cinematic/dramatic/soft",
                "camera_angle": "wide shot/medium shot/close-up/dynamic",
                "composition": "rule of thirds/centered/diagonal/dynamic"
            }}
        }}
    ]
}}

DEITY-SPECIFIC PROMPT GUIDELINES:

FOR LORD SHIVA:
- Poses: meditation, cosmic dance (Nataraja), blessing pose, third eye, trident holding
- Attributes: blue skin, crescent moon, Ganges in hair, snake around neck, tiger skin
- Settings: Mount Kailash, cosmic space, cremation ground, temple, meditation cave
- Moods: serene meditation, powerful cosmic dance, fierce destroyer, compassionate protector

FOR LORD GANESHA:
- Poses: sitting on lotus, dancing, blessing devotees, removing obstacles
- Attributes: elephant head, large belly, four arms, modak in hand, mouse vahana
- Settings: temple, lotus pond, forest clearing, devotee gatherings
- Moods: wise and benevolent, joyful celebration, protective guardian

FOR LORD KRISHNA:
- Poses: flute playing, dancing, childhood play, Govardhan lifting, chariot driving
- Attributes: blue skin, peacock feather crown, yellow dhoti, flute
- Settings: Vrindavan, battlefield, cow herds, river banks, royal court
- Moods: playful child, romantic lover, wise teacher, powerful warrior

REQUIREMENTS for each prompt:
1. SAME DEITY throughout ALL segments (consistency is key)
2. PHOTOREALISTIC style for Flux generation
3. 16:9 aspect ratio (YouTube optimized)
4. VISUALLY STRIKING and devotionally engaging
5. Vary pose, mood, and setting while keeping same deity
6. Match audio intensity with deity's expression/pose
7. Use exactly {segment_count} segments distributed evenly across song duration
8. Include specific deity attributes in EVERY prompt

Respond with ONLY the JSON object, no other text or formatting.
"""
    
    def generate_prompts_with_retry(self, audio_file: Any, output_dir: Path, segment_count: int, segment_duration: float) -> Optional[Dict]:
        """Generate prompts with retry logic and validation"""
        self.api_logger.info("START: Starting prompt generation with retry logic")
        self.api_logger.info(f"STATS: Segmentation: {segment_count} segments of {segment_duration:.1f}s each")
        
        prompt_text = self.create_analysis_prompt(segment_count, segment_duration)
        
        for attempt in range(1, API_RETRY_COUNT + 1):
            self.api_logger.info(f"LOG: Attempt {attempt}/{API_RETRY_COUNT}")
            
            try:
                # Create the content with audio file
                content = [
                    audio_file,
                    prompt_text
                ]
                
                # Generate response
                self.api_logger.info("SEND: Sending request to Gemini...")
                start_time = time.time()
                
                response = self.model.generate_content(
                    content,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings
                )
                
                elapsed = time.time() - start_time
                self.api_logger.info(f"SUCCESS: Received response ({elapsed:.1f}s)")
                
                # Get response text
                response_text = response.text if hasattr(response, 'text') else ""
                
                if not response_text:
                    self.api_logger.warning("WARNING: Empty response received")
                    continue
                
                # Save raw response for debugging
                raw_file = output_dir / "logs" / f"raw_response_attempt_{attempt}.txt"
                with open(raw_file, 'w', encoding='utf-8') as f:
                    f.write(response_text)
                
                self.api_logger.info(f"SAVE: Raw response saved: {raw_file}")
                
                # Parse and validate JSON
                parsed_data, errors = self.json_validator.parse_and_validate(response_text)
                
                if parsed_data and not errors:
                    self.api_logger.info("SUCCESS: Prompt generation successful!")
                    return parsed_data
                else:
                    self.api_logger.warning(f"WARNING: Validation failed: {errors}")
                    
                    # If we have more attempts, try to fix with re-prompt
                    if attempt < API_RETRY_COUNT:
                        self.api_logger.info("RETRY: Attempting to fix with re-prompt...")
                        fix_result = self._retry_with_format_correction(
                            content, response_text, attempt, output_dir
                        )
                        if fix_result:
                            return fix_result
            
            except Exception as e:
                self.api_logger.error(f"ERROR: Attempt {attempt} failed: {str(e)}")
                self.api_logger.debug(traceback.format_exc())
            
            # Wait before retry
            if attempt < API_RETRY_COUNT:
                wait_time = attempt * 5
                self.api_logger.info(f"WAIT: Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        self.api_logger.error("ERROR: All attempts failed")
        return None
    
    def _retry_with_format_correction(self, original_content: List, 
                                    failed_response: str, attempt: int, 
                                    output_dir: Path) -> Optional[Dict]:
        """Attempt to fix JSON format issues with a correction prompt"""
        self.api_logger.info("CONFIG: Attempting format correction...")
        
        correction_prompt = f"""
The previous response had formatting issues. Please regenerate the EXACT same content but ensure:

1. Response is ONLY a valid JSON object
2. NO markdown code blocks (no ``` or ```json)
3. NO extra text before or after the JSON
4. Proper JSON syntax with correct quotes and commas

Previous response had these issues, please fix:
- Make sure it's valid JSON
- Remove any markdown formatting
- Ensure all strings are properly quoted

Generate ONLY the corrected JSON object:
"""
        
        try:
            # Create conversation with correction
            correction_content = original_content + [correction_prompt]
            
            response = self.model.generate_content(
                correction_content,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            response_text = response.text if hasattr(response, 'text') else ""
            
            if response_text:
                # Save corrected response
                corrected_file = output_dir / "logs" / f"corrected_response_attempt_{attempt}.txt"
                with open(corrected_file, 'w', encoding='utf-8') as f:
                    f.write(response_text)
                
                # Parse and validate
                parsed_data, errors = self.json_validator.parse_and_validate(response_text)
                
                if parsed_data and not errors:
                    self.api_logger.info("SUCCESS: Format correction successful!")
                    return parsed_data
                else:
                    self.api_logger.warning(f"WARNING: Correction failed: {errors}")
        
        except Exception as e:
            self.api_logger.error(f"ERROR: Format correction error: {str(e)}")
        
        return None

# =============================================================================
# AUDIO PROCESSING AND FILE MANAGEMENT
# =============================================================================

class AudioProcessor:
    """Handles audio file discovery and processing"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def find_latest_mp3(self, songs_dir: Path) -> Optional[Path]:
        """Find the most recent MP3 file in the songs directory"""
        self.logger.info(f"SEARCH: Searching for MP3 files in: {songs_dir}")
        
        if not songs_dir.exists():
            self.logger.error(f"ERROR: Songs directory not found: {songs_dir}")
            return None
        
        # Find all MP3 files
        mp3_files = list(songs_dir.glob("*.mp3"))
        self.logger.info(f"Found {len(mp3_files)} MP3 files")
        
        if not mp3_files:
            self.logger.error("ERROR: No MP3 files found")
            return None
        
        # Sort by modification time (newest first)
        latest_file = max(mp3_files, key=lambda f: f.stat().st_mtime)
        
        # Log file details
        file_size_mb = latest_file.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
        
        self.logger.info(f"SUCCESS: Latest MP3: {latest_file.name}")
        self.logger.info(f"   Size: {file_size_mb:.2f} MB")
        self.logger.info(f"   Modified: {mod_time}")
        
        return latest_file
    
    def create_output_directory(self, base_dir: Path) -> Path:
        """Create timestamped output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = base_dir / f"Run_{timestamp}_music"
        
        self.logger.info(f"FOLDER: Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (output_dir / "logs").mkdir(exist_ok=True)
        
        self.logger.info(f"SUCCESS: Output directory created: {output_dir}")
        return output_dir

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

class PerformanceMonitor:
    """Track performance metrics and statistics"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_time = None
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_duration": None,
            "api_calls": 0,
            "retry_count": 0,
            "success_rate": 0,
            "file_operations": [],
            "errors": []
        }
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.stats["start_time"] = datetime.now().isoformat()
        self.logger.info("STATS: Performance monitoring started")
    
    def log_api_call(self):
        """Log an API call"""
        self.stats["api_calls"] += 1
        self.logger.debug(f"API calls: {self.stats['api_calls']}")
    
    def log_retry(self):
        """Log a retry attempt"""
        self.stats["retry_count"] += 1
        self.logger.debug(f"Retries: {self.stats['retry_count']}")
    
    def log_error(self, error: str):
        """Log an error"""
        self.stats["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
        self.logger.warning(f"Error logged: {error}")
    
    def finish_monitoring(self, success: bool) -> Dict:
        """Finish monitoring and return stats"""
        end_time = time.time()
        self.stats["end_time"] = datetime.now().isoformat()
        
        if self.start_time:
            duration = end_time - self.start_time
            self.stats["total_duration"] = f"{duration:.2f}s"
            self.stats["success_rate"] = "100%" if success else f"{(1-len(self.stats['errors'])/max(1,self.stats['api_calls']))*100:.1f}%"
        
        self.logger.info(f"STATS: Monitoring finished - Duration: {self.stats.get('total_duration', 'N/A')}")
        return self.stats

# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

class AudioToPromptsGenerator:
    """Main orchestration class"""
    
    def __init__(self):
        self.audio_processor = None
        self.gemini_client = None
        self.performance_monitor = None
        self.logger_manager = None
    
    def run(self) -> bool:
        """Main execution flow"""
        print("MUSIC: Audio to Visual Prompts Generator")
        print("=" * 50)
        
        try:
            # Step 1: Find latest MP3 file
            audio_processor = AudioProcessor(logging.getLogger("temp"))
            latest_mp3 = audio_processor.find_latest_mp3(SONGS_DIR)
            
            if not latest_mp3:
                print("ERROR: No MP3 file found!")
                return False
            
            # Step 2: Create output directory
            output_dir = audio_processor.create_output_directory(OUTPUT_BASE_DIR)
            
            # Step 3: Setup logging
            self.logger_manager = AudioToPromptsLogger(output_dir)
            main_logger = self.logger_manager.main_logger
            
            main_logger.info("START: Starting Audio to Prompts Generation (OPTIMIZED)")
            main_logger.info(f"TARGET: Efficiency Mode: Maximum {MAX_SEGMENTS} segments regardless of song length")
            main_logger.info(f"FAST: Resource Savings: Prevents excessive computation on long songs")
            main_logger.info(f"Input file: {latest_mp3}")
            main_logger.info(f"Output directory: {output_dir}")
            
            # Step 4: Initialize components
            self.audio_processor = AudioProcessor(main_logger)
            self.gemini_client = GeminiAPIClient(
                self.logger_manager.api_logger,
                self.logger_manager.json_logger
            )
            self.performance_monitor = PerformanceMonitor(
                self.logger_manager.performance_logger
            )
            
            # Step 5: Start performance monitoring
            self.performance_monitor.start_monitoring()
            
            # Step 6: Upload audio file
            main_logger.info("UPLOAD: Uploading audio file to Gemini...")
            uploaded_file = self.gemini_client.upload_audio_file(latest_mp3)
            
            if not uploaded_file:
                main_logger.error("ERROR: Failed to upload audio file")
                return False
            
            self.performance_monitor.log_api_call()
            
            # Step 7: Calculate optimal segmentation
            # Use MAX_SEGMENTS as target, let Gemini determine exact duration and adjust
            segment_count = MAX_SEGMENTS
            estimated_duration = segment_count * DEFAULT_SEGMENT_DURATION  # Rough estimate for prompt
            
            main_logger.info(f"TARGET: Target segmentation: {segment_count} segments (max efficiency)")
            main_logger.info(f"STATS: This limits computation to {segment_count * 4} total images (manageable approval process)")
            
            # Step 8: Generate prompts
            main_logger.info("PROMPTS: Generating visual prompts...")
            prompts_data = self.gemini_client.generate_prompts_with_retry(
                uploaded_file, output_dir, segment_count, DEFAULT_SEGMENT_DURATION
            )
            
            if not prompts_data:
                main_logger.error("ERROR: Failed to generate prompts")
                self.performance_monitor.log_error("Prompt generation failed")
                return False
            
            # Step 8: Update metadata with performance stats
            stats = self.performance_monitor.finish_monitoring(True)
            prompts_data["metadata"]["processing_stats"] = {
                "total_api_calls": stats["api_calls"],
                "retry_count": stats["retry_count"],
                "total_processing_time": stats["total_duration"],
                "success_rate": stats["success_rate"]
            }
            
            # Step 9: Save final output
            output_file = output_dir / "prompts.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(prompts_data, f, indent=2, ensure_ascii=False)
            
            main_logger.info(f"SUCCESS: Prompts saved to: {output_file}")
            
            # Step 10: Save performance stats
            stats_file = output_dir / "performance_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            # Step 11: Print summary
            self._print_summary(prompts_data, output_dir, stats)
            
            return True
            
        except Exception as e:
            error_msg = f"ERROR: Unexpected error: {str(e)}"
            print(error_msg)
            if hasattr(self, 'logger_manager') and self.logger_manager:
                self.logger_manager.main_logger.error(error_msg)
                self.logger_manager.main_logger.debug(traceback.format_exc())
            else:
                print(traceback.format_exc())
            return False
    
    def _print_summary(self, prompts_data: Dict, output_dir: Path, stats: Dict):
        """Print execution summary"""
        print("\n" + "=" * 50)
        print("STATS: EXECUTION SUMMARY")
        print("=" * 50)
        
        metadata = prompts_data.get("metadata", {})
        segments = prompts_data.get("segments", [])
        
        print(f"MUSIC: Song: {metadata.get('song_file', 'Unknown')}")
        print(f"TIME: Duration: {metadata.get('total_duration', 'Unknown')}s")
        print(f"VIDEO: Segments: {len(segments)} (STATS: Optimized: Limited to max {MAX_SEGMENTS} for efficiency)")
        print(f"IMAGES: Total Images: {len(segments) * 4} (4 per segment)")
        print(f"FAST: Computation Saved: {max(0, (int(metadata.get('total_duration', 0)) // 5 - len(segments)) * 4)} images avoided")
        print(f"OUTPUT: Output: {output_dir}")
        print(f"FAST: Processing Time: {stats.get('total_duration', 'Unknown')}")
        print(f"TARGET: Success Rate: {stats.get('success_rate', 'Unknown')}")
        print(f"API: API Calls: {stats.get('api_calls', 0)}")
        print(f"RETRY: Retries: {stats.get('retry_count', 0)}")
        
        print("\nLOG: Generated Files:")
        print(f"   - prompts.json ({len(segments)} segments)")
        print(f"   - performance_stats.json")
        print(f"   - logs/execution.log")
        print(f"   - logs/gemini_api.log")
        print(f"   - logs/json_parsing.log")
        print(f"   - logs/performance.log")
        
        if segments:
            print(f"\nSample Prompt (Segment 1):")
            first_segment = segments[0]
            print(f"   {first_segment.get('primary_prompt', 'N/A')[:100]}...")
        
        print("\nSUCCESS: Generation Complete!")

# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI entry point"""
    try:
        generator = AudioToPromptsGenerator()
        success = generator.run()
        
        if success:
            print("\nSUCCESS: Generation completed! Check the output directory for results.")
            sys.exit(0)
        else:
            print("\nERROR: Generation failed. Check the logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nWARNING: Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Fatal error: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()