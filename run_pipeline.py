#!/usr/bin/env python
"""Complete Dancer Content Pipeline - From Generation to YouTube Upload

FIXED: Unicode encoding issues when capturing subprocess output.
Only changes made to pipeline runner, automation script left unchanged.

This script runs the entire pipeline:
1. API Server (background)
2. Content Generation (images/videos) 
3. Beat Synchronization
4. 4K Upscaling
5. Crop to Reels Format
6. Generate Viral Metadata
7. Upload to YouTube
"""

from __future__ import annotations

import subprocess
import sys
import time
import json
import os
from pathlib import Path
from datetime import datetime

# === UNICODE FIX FOR PIPELINE RUNNER ===
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent

# === PIPELINE SCRIPTS ===
API_SERVER = ROOT / "api_server_v5_without_faceswap.py"
AUTOMATION_SCRIPT = ROOT / "main_automation_without_faceswap.py"
BEAT_SYNC_SCRIPT = ROOT / "beat_sync_single.py"
UPSCALE_SCRIPT = ROOT / "upscale_4k_parallel.py"

# === NEW: MISSING PIPELINE STEPS ===
CROP_TO_REELS_SCRIPT = ROOT / "crop_to_reels.py"
METADATA_GENERATOR_SCRIPT = ROOT / "youtube_metadata_generator.py"
YOUTUBE_UPLOADER_SCRIPT = ROOT / "youtube_shorts_poster.py"

# === CONFIGURATION ===
ENABLE_AUTO_UPLOAD = True  # Set to False to stop before YouTube upload
ENABLE_METADATA_GENERATION = True  # Set to False to skip AI metadata generation
DELAY_BETWEEN_STEPS = 3  # Seconds to wait between major steps
LOG_FILE = ROOT / "pipeline_log.txt"

def safe_log_message(message):
    """Sanitize Unicode characters for safe logging."""
    if isinstance(message, str):
        replacements = {
            '🔥': '[FIRE]', '🎭': '[THEATER]', '👗': '[DRESS]', '✅': '[OK]',
            '❌': '[ERROR]', '⚠️': '[WARN]', '🚀': '[ROCKET]', '📝': '[MEMO]',
            '📊': '[CHART]', '🎬': '[MOVIE]', '🖼️': '[IMAGE]', '💃': '[DANCER]',
            '🟢': '[GREEN]', '🎉': '[PARTY]', '📤': '[UPLOAD]', '🛑': '[STOP]',
            '⏰': '[CLOCK]', '⏱️': '[TIMER]', '🛡️': '[SHIELD]', '🔍': '[SEARCH]'
        }
        safe_message = message
        for unicode_char, replacement in replacements.items():
            safe_message = safe_message.replace(unicode_char, replacement)
        return safe_message
    return str(message)

class PipelineRunner:
    def __init__(self):
        self.start_time = datetime.now()
        self.api_proc = None
        self.completed_steps = []
        self.failed_steps = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to both console and file with Unicode safety."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_message = safe_log_message(message)
        log_entry = f"[{timestamp}] [{level}] {safe_message}"
        print(log_entry)
        
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # Don't fail pipeline due to logging issues

    def run_step(self, script_path: Path, step_name: str, required: bool = True) -> bool:
        """Run a pipeline step with Unicode-safe subprocess handling."""
        if not script_path.exists():
            self.log(f"[ERROR] MISSING SCRIPT: {script_path}", "ERROR")
            if required:
                self.log(f"[STOP] Pipeline stopped - required script missing", "FATAL")
                return False
            else:
                self.log(f"[WARN] Skipping optional step: {step_name}", "WARN")
                return True
        
        cmd = [sys.executable, str(script_path)]
        self.log(f"[ROCKET] Starting Step: {step_name}")
        self.log(f"   Command: {' '.join(cmd)}")
        
        try:
            # === CRITICAL FIX: Don't capture output to avoid Unicode issues ===
            # Let the subprocess write directly to console instead of capturing
            result = subprocess.run(
                cmd, 
                check=True,
                # Remove capture_output=True to avoid Unicode encoding issues
                text=True,
                encoding='utf-8',
                errors='replace'  # Replace problematic characters instead of failing
            )
            
            self.log(f"[OK] COMPLETED: {step_name}")
            self.completed_steps.append(step_name)
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] FAILED: {step_name}", "ERROR")
            self.log(f"   Exit code: {e.returncode}", "ERROR")
            
            self.failed_steps.append(step_name)
            
            if required:
                self.log(f"[STOP] Pipeline stopped due to required step failure", "FATAL")
                return False
            else:
                self.log(f"[WARN] Continuing despite optional step failure", "WARN")
                return True
                
        except Exception as e:
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            self.log(f"[ERROR] UNEXPECTED ERROR in {step_name}: {error_msg}", "ERROR")
            self.failed_steps.append(step_name)
            return not required

    def start_api_server(self) -> bool:
        """Start the API server in background."""
        if not API_SERVER.exists():
            self.log(f"[ERROR] FATAL: API server script not found: {API_SERVER}", "FATAL")
            return False
            
        self.log("[ROCKET] Starting API server in background...")
        try:
            # Start with Unicode-safe environment
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            self.api_proc = subprocess.Popen(
                [sys.executable, str(API_SERVER)],
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            self.log(f"   API server PID: {self.api_proc.pid}")
            
            # Give server time to start
            self.log("   Waiting for API server to initialize...")
            time.sleep(8)
            
            # Check if process is still running
            if self.api_proc.poll() is not None:
                self.log("[ERROR] API server failed to start or crashed immediately", "ERROR")
                return False
                
            self.log("[OK] API server started successfully")
            return True
            
        except Exception as e:
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            self.log(f"[ERROR] Failed to start API server: {error_msg}", "ERROR")
            return False

    def stop_api_server(self):
        """Gracefully stop the API server."""
        if self.api_proc:
            self.log("[STOP] Stopping API server...")
            try:
                self.api_proc.terminate()
                try:
                    self.api_proc.wait(timeout=15)
                    self.log("[OK] API server stopped gracefully")
                except subprocess.TimeoutExpired:
                    self.log("[WARN] API server timeout, force killing...")
                    self.api_proc.kill()
                    self.log("[OK] API server force stopped")
            except Exception as e:
                error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
                self.log(f"[WARN] Error stopping API server: {error_msg}", "WARN")

    def run_complete_pipeline(self) -> bool:
        """Run the complete pipeline from start to finish."""
        self.log("=" * 80)
        self.log("[MOVIE] STARTING COMPLETE DANCER CONTENT PIPELINE")
        self.log("=" * 80)
        
        # Step 0: Start API Server
        if not self.start_api_server():
            return False
            
        try:
            # Step 1: Content Generation (Images + Videos)
            if not self.run_step(AUTOMATION_SCRIPT, "Content Generation", required=True):
                return False
            time.sleep(DELAY_BETWEEN_STEPS)

            # Step 2: Beat Synchronization
            if not self.run_step(BEAT_SYNC_SCRIPT, "Beat Synchronization", required=True):
                return False
            time.sleep(DELAY_BETWEEN_STEPS)

            # Step 3: 4K Upscaling
            if not self.run_step(UPSCALE_SCRIPT, "4K Upscaling", required=True):
                return False
            time.sleep(DELAY_BETWEEN_STEPS)

            # Step 4: Crop to Reels Format
            if not self.run_step(CROP_TO_REELS_SCRIPT, "Crop to Reels", required=True):
                return False
            time.sleep(DELAY_BETWEEN_STEPS)

            # Step 5: Generate Viral Metadata (Optional)
            if ENABLE_METADATA_GENERATION:
                if not self.run_step(METADATA_GENERATOR_SCRIPT, "Viral Metadata Generation", required=False):
                    self.log("[WARN] Metadata generation failed, will use fallback for upload", "WARN")
                time.sleep(DELAY_BETWEEN_STEPS)

            # Step 6: Upload to YouTube (Optional)
            if ENABLE_AUTO_UPLOAD:
                if not self.run_step(YOUTUBE_UPLOADER_SCRIPT, "YouTube Upload", required=False):
                    self.log("[WARN] YouTube upload failed - videos ready for manual upload", "WARN")
            else:
                self.log("[UPLOAD] Auto-upload disabled - videos ready for manual upload")

            return True
            
        finally:
            self.stop_api_server()

    def print_final_summary(self):
        """Print a comprehensive summary of the pipeline run."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.log("=" * 80)
        self.log("[CHART] PIPELINE EXECUTION SUMMARY")
        self.log("=" * 80)
        self.log(f"[CLOCK] Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"[CLOCK] End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"[TIMER] Total Duration: {str(duration).split('.')[0]}")
        self.log("")
        
        self.log(f"[OK] Completed Steps ({len(self.completed_steps)}):")
        for step in self.completed_steps:
            self.log(f"   [OK] {step}")
            
        if self.failed_steps:
            self.log(f"[ERROR] Failed Steps ({len(self.failed_steps)}):")
            for step in self.failed_steps:
                self.log(f"   [ERROR] {step}")
        
        self.log("")
        if len(self.failed_steps) == 0:
            self.log("[PARTY] PIPELINE COMPLETED SUCCESSFULLY!")
            self.log("   All content generated and ready!")
        elif len(self.completed_steps) >= 4:  # At least core steps completed
            self.log("[WARN] PIPELINE PARTIALLY COMPLETED")
            self.log("   Core content generated but some final steps failed")
        else:
            self.log("[ERROR] PIPELINE FAILED")
            self.log("   Critical steps failed - check logs for details")
            
        self.log("=" * 80)

def check_required_scripts():
    """Check if all required scripts exist."""
    required_scripts = [
        (API_SERVER, "API Server", True),
        (AUTOMATION_SCRIPT, "Main Automation", True), 
        (BEAT_SYNC_SCRIPT, "Beat Sync", True),
        (UPSCALE_SCRIPT, "4K Upscaling", True),
        (CROP_TO_REELS_SCRIPT, "Crop to Reels", True),
        (METADATA_GENERATOR_SCRIPT, "Metadata Generator", False),
        (YOUTUBE_UPLOADER_SCRIPT, "YouTube Uploader", False)
    ]
    
    missing_required = []
    missing_optional = []
    
    for script_path, name, required in required_scripts:
        if not script_path.exists():
            if required:
                missing_required.append(f"[ERROR] {name}: {script_path}")
            else:
                missing_optional.append(f"[WARN] {name}: {script_path}")
        else:
            print(f"[OK] {name}: Found")
    
    if missing_required:
        print("\n[STOP] MISSING REQUIRED SCRIPTS:")
        for missing in missing_required:
            print(f"   {missing}")
        print("\n[MEMO] Pipeline cannot run without these scripts!")
        return False
        
    if missing_optional:
        print("\n[WARN] MISSING OPTIONAL SCRIPTS:")
        for missing in missing_optional:
            print(f"   {missing}")
        print("   Pipeline will run but some features will be skipped")
    
    return True

def main() -> None:
    print("[SEARCH] Checking pipeline scripts...")
    if not check_required_scripts():
        print("\n[ERROR] Please ensure all required scripts are present")
        sys.exit(1)
    
    print(f"\n[GEAR] Pipeline Configuration:")
    print(f"   [UPLOAD] Auto Upload: {'Enabled' if ENABLE_AUTO_UPLOAD else 'Disabled'}")
    print(f"   [ROBOT] AI Metadata: {'Enabled' if ENABLE_METADATA_GENERATION else 'Disabled'}")
    print(f"   [TIMER] Step Delay: {DELAY_BETWEEN_STEPS}s")
    
    # Ask for confirmation
    response = input(f"\n[ROCKET] Ready to start complete pipeline? (y/N): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Pipeline cancelled by user")
        sys.exit(0)
    
    # Run the pipeline
    runner = PipelineRunner()
    success = runner.run_complete_pipeline()
    runner.print_final_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()