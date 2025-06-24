#!/usr/bin/env python
"""Horror CCTV Pipeline Runner - Complete automation orchestrator

This script runs the complete Horror CCTV automation pipeline:
1. Starts the Horror CCTV API server (port 8002)
2. Runs the main Horror CCTV automation script
3. Handles server lifecycle management

HORROR CCTV PIPELINE: API SERVER + AUTOMATION + LIFECYCLE MANAGEMENT
"""

import subprocess
import sys
import time
import signal
import threading
import os
from pathlib import Path

# === UNICODE FIX FOR HORROR CCTV PIPELINE ===
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def safe_log_message(message):
    """Sanitize Unicode characters for safe logging and printing."""
    if isinstance(message, str):
        replacements = {
            '🎬': '[MOVIE]', '🔤': '[TEXT]', '🟢': '[GREEN]', '📝': '[MEMO]',
            '✅': '[OK]', '❌': '[ERROR]', '⚠️': '[WARN]', '🧹': '[CLEAN]',
            '⏹️': '[STOP]', '🔥': '[FIRE]', '🚀': '[ROCKET]', '📊': '[CHART]',
            '🛑': '[STOP_SIGN]', '💪': '[MUSCLE]', '🏋️': '[WEIGHT]', '📋': '[CLIPBOARD]'
        }
        safe_message = message
        for unicode_char, replacement in replacements.items():
            safe_message = safe_message.replace(unicode_char, replacement)
        return safe_message
    return str(message)

print(safe_log_message("🎬 Horror CCTV Pipeline Runner Starting..."))

# --- Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
API_SERVER_SCRIPT = SCRIPT_DIR / "api_server_v5_horror_cctv.py"
MAIN_AUTOMATION_SCRIPT = SCRIPT_DIR / "main_automation_horror_cctv.py"
API_SERVER_PORT = 8002
STARTUP_DELAY = 10  # Seconds to wait for API server startup

# --- Global Variables ---
api_server_process = None
automation_process = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(safe_log_message(f"\n🛑 Received signal {signum}, shutting down Horror CCTV pipeline..."))
    cleanup_and_exit()

def cleanup_and_exit():
    """Clean up processes and exit"""
    global api_server_process, automation_process
    
    print(safe_log_message("🧹 Cleaning up Horror CCTV processes..."))
    
    # Terminate automation process first
    if automation_process and automation_process.poll() is None:
        print(safe_log_message("  ⏹️ Stopping Horror CCTV automation..."))
        try:
            automation_process.terminate()
            automation_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(safe_log_message("  🔥 Force killing Horror CCTV automation..."))
            automation_process.kill()
        except Exception as e:
            print(safe_log_message(f"  ⚠️ Error stopping automation: {e}"))
    
    # Terminate API server
    if api_server_process and api_server_process.poll() is None:
        print(safe_log_message(f"  ⏹️ Stopping Horror CCTV API server (port {API_SERVER_PORT})..."))
        try:
            api_server_process.terminate()
            api_server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(safe_log_message("  🔥 Force killing Horror CCTV API server..."))
            api_server_process.kill()
        except Exception as e:
            print(safe_log_message(f"  ⚠️ Error stopping API server: {e}"))
    
    print(safe_log_message("✅ Horror CCTV pipeline cleanup completed"))
    sys.exit(0)

def check_python_executable():
    """Verify Python executable"""
    python_cmd = sys.executable
    if not python_cmd:
        python_cmd = "python"
    
    print(f"Using Python: {python_cmd}")
    return python_cmd

def verify_scripts_exist():
    """Verify all required Horror CCTV scripts exist"""
    missing_scripts = []
    
    if not API_SERVER_SCRIPT.exists():
        missing_scripts.append(f"API Server: {API_SERVER_SCRIPT}")
    
    if not MAIN_AUTOMATION_SCRIPT.exists():
        missing_scripts.append(f"Main Automation: {MAIN_AUTOMATION_SCRIPT}")
    
    if missing_scripts:
        print(safe_log_message("❌ Missing Horror CCTV scripts:"))
        for script in missing_scripts:
            print(f"   {script}")
        print("\nPlease ensure all Horror CCTV scripts are in the correct location.")
        sys.exit(1)
    
    print(safe_log_message("✅ All Horror CCTV scripts found"))

def start_api_server():
    """Start the Horror CCTV API server"""
    global api_server_process
    
    print(safe_log_message(f"🚀 Starting Horror CCTV API Server on port {API_SERVER_PORT}..."))
    
    python_cmd = check_python_executable()
    
    try:
        api_server_process = subprocess.Popen(
            [python_cmd, str(API_SERVER_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True
        )
        
        # Start thread to monitor API server output
        def monitor_api_server():
            if api_server_process:
                for line in iter(api_server_process.stdout.readline, ''):
                    print(f"[API] {line.rstrip()}")
                    
                # Process ended
                if api_server_process.poll() is not None:
                    print(f"Horror CCTV API server process ended with code: {api_server_process.returncode}")
        
        api_monitor_thread = threading.Thread(target=monitor_api_server, daemon=True)
        api_monitor_thread.start()
        
        print(f"Waiting {STARTUP_DELAY} seconds for Horror CCTV API server startup...")
        time.sleep(STARTUP_DELAY)
        
        # Check if process is still running
        if api_server_process.poll() is None:
            print(safe_log_message(f"✅ Horror CCTV API Server started successfully on port {API_SERVER_PORT}"))
            return True
        else:
            print(safe_log_message(f"❌ Horror CCTV API Server failed to start (exit code: {api_server_process.returncode})"))
            return False
            
    except Exception as e:
        print(safe_log_message(f"❌ Failed to start Horror CCTV API server: {e}"))
        return False

def run_main_automation():
    """Run the main Horror CCTV automation script"""
    global automation_process
    
    print(safe_log_message("🎬 Starting Horror CCTV Main Automation..."))
    
    python_cmd = check_python_executable()
    
    try:
        automation_process = subprocess.Popen(
            [python_cmd, str(MAIN_AUTOMATION_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True
        )
        
        print(safe_log_message("📊 Horror CCTV Automation Output:"))
        print("=" * 60)
        
        # Stream automation output in real-time
        for line in iter(automation_process.stdout.readline, ''):
            print(f"{line.rstrip()}")
        
        # Wait for automation to complete
        automation_process.wait()
        
        print("=" * 60)
        
        if automation_process.returncode == 0:
            print(safe_log_message("✅ Horror CCTV automation completed successfully!"))
            return True
        else:
            print(safe_log_message(f"❌ Horror CCTV automation failed with exit code: {automation_process.returncode}"))
            return False
            
    except KeyboardInterrupt:
        print(safe_log_message("\n⏹️ Horror CCTV automation interrupted by user"))
        if automation_process:
            automation_process.terminate()
        return False
    except Exception as e:
        print(safe_log_message(f"❌ Error running Horror CCTV automation: {e}"))
        return False

def main():
    """Main Horror CCTV pipeline execution"""
    print(safe_log_message("🎬" + "=" * 58 + "🎬"))
    print("    HORROR CCTV AUTOMATION PIPELINE RUNNER")
    print(safe_log_message("🎬" + "=" * 58 + "🎬"))
    print()
    print("Configuration:")
    print(f"   Script Directory: {SCRIPT_DIR}")
    print(f"   API Server Port: {API_SERVER_PORT}")
    print(f"   Startup Delay: {STARTUP_DELAY}s")
    print()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # Termination
    
    try:
        # Step 1: Verify all scripts exist
        print("Step 1: Verifying Horror CCTV scripts...")
        verify_scripts_exist()
        print()
        
        # Step 2: Start API server
        print(safe_log_message("🚀 Step 2: Starting Horror CCTV API Server..."))
        if not start_api_server():
            print(safe_log_message("❌ Failed to start Horror CCTV API server, aborting pipeline"))
            sys.exit(1)
        print()
        
        # Step 3: Run main automation
        print(safe_log_message("🎬 Step 3: Running Horror CCTV Main Automation..."))
        automation_success = run_main_automation()
        print()
        
        # Step 4: Pipeline completion
        if automation_success:
            print("Horror CCTV Pipeline completed successfully!")
            print("Check your output directory for generated content")
        else:
            print(safe_log_message("⚠️ Horror CCTV Pipeline completed with issues"))
            print(safe_log_message("📋 Check the logs for more details"))
        
    except Exception as e:
        print(f"Fatal error in Horror CCTV pipeline: {e}")
        sys.exit(1)
    finally:
        # Always cleanup on exit
        cleanup_and_exit()

if __name__ == "__main__":
    main()