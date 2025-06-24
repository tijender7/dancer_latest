#!/usr/bin/env python
"""
Debug script to test the music pipeline and identify where video generation fails
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def test_comfyui():
    """Test if ComfyUI is running"""
    print("🔍 Testing ComfyUI...")
    try:
        response = requests.get("http://127.0.0.1:8188/", timeout=10)
        if response.status_code == 200:
            print("✅ ComfyUI is running")
            return True
        else:
            print(f"❌ ComfyUI returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ComfyUI not accessible: {e}")
        return False

def test_music_api_server():
    """Test if the music API server can start"""
    print("🔍 Testing Music API Server...")
    
    # Check if script exists
    api_script = SCRIPT_DIR / "api_server_v5_music.py"
    if not api_script.exists():
        print(f"❌ API server script not found: {api_script}")
        return False
    
    # Try to start it
    try:
        print("🚀 Starting API server...")
        process = subprocess.Popen(
            [sys.executable, str(api_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for startup
        time.sleep(8)
        
        # Test if it's responding
        try:
            response = requests.get("http://127.0.0.1:8006/", timeout=10)
            if response.status_code == 200:
                print("✅ Music API Server is running")
                
                # Test video endpoint exists
                try:
                    status_response = requests.get("http://127.0.0.1:8006/status", timeout=5)
                    if status_response.status_code == 200:
                        print("✅ Status endpoint works")
                    else:
                        print(f"⚠️ Status endpoint returned: {status_response.status_code}")
                except Exception as e:
                    print(f"⚠️ Status endpoint failed: {e}")
                
                # Cleanup
                process.terminate()
                process.wait()
                print("🧹 API server stopped")
                return True
            else:
                print(f"❌ API server returned status: {response.status_code}")
        except Exception as e:
            print(f"❌ API server not responding: {e}")
        
        # Cleanup
        process.terminate()
        process.wait()
        return False
        
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return False

def test_config_files():
    """Test if all required files exist"""
    print("🔍 Testing configuration files...")
    
    files_to_check = [
        "config_music.json",
        "api_server_v5_music.py",
        "main_automation_music.py",
        "base_workflows/API_flux_without_faceswap_music.json",
        "base_workflows/api_wanvideo_without_faceswap.json"
    ]
    
    all_exist = True
    for file_name in files_to_check:
        file_path = SCRIPT_DIR / file_name
        if file_path.exists():
            print(f"✅ {file_name}")
        else:
            print(f"❌ {file_name} - MISSING")
            all_exist = False
    
    return all_exist

def test_music_prompts():
    """Test if music prompts are available"""
    print("🔍 Testing music prompts...")
    
    import glob
    pattern = str(Path("H:/dancers_content") / "Run_*_music")
    music_folders = glob.glob(pattern)
    
    if not music_folders:
        print("❌ No music run folders found")
        print("   Run: python audio_to_prompts_generator.py first")
        return False
    
    # Check latest folder
    music_folders.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    latest_folder = Path(music_folders[0])
    prompts_file = latest_folder / "prompts.json"
    
    if not prompts_file.exists():
        print(f"❌ No prompts.json in {latest_folder}")
        return False
    
    try:
        with open(prompts_file, 'r') as f:
            data = json.load(f)
        segments = data.get("segments", [])
        print(f"✅ Found {len(segments)} music segments in {latest_folder.name}")
        return True
    except Exception as e:
        print(f"❌ Failed to read prompts: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 MUSIC PIPELINE DIAGNOSTIC TESTS")
    print("=" * 50)
    
    tests = [
        ("ComfyUI", test_comfyui),
        ("Config Files", test_config_files),
        ("Music Prompts", test_music_prompts),
        ("Music API Server", test_music_api_server)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        results[test_name] = test_func()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY:")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("   Your music pipeline should work correctly.")
        print("   Run: python run_pipeline_music.py")
    else:
        print("💥 SOME TESTS FAILED!")
        print("   Fix the failing components before running the pipeline.")
    print("=" * 50)

if __name__ == "__main__":
    main()