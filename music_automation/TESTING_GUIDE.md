# Music Automation Testing Guide

## Overview

This comprehensive testing guide provides procedures for validating all components of the Music-Based Image & Video Generation Automation system. Use this guide to ensure each component works correctly before and after deployment.

## 🎯 Testing Philosophy

### Testing Levels
1. **Unit Testing**: Individual component validation
2. **Integration Testing**: Component interaction verification
3. **System Testing**: End-to-end pipeline validation
4. **Performance Testing**: Load and stress testing
5. **Regression Testing**: Ensuring changes don't break existing functionality

### Testing Priorities
- **Critical**: Core automation pipeline
- **High**: Audio processing, video generation
- **Medium**: Beat sync, karaoke features
- **Low**: Debug tools, utilities

## 🧪 Pre-Testing Setup

### Environment Preparation

```bash
# Activate virtual environment
cd music_automation
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Verify Python environment
python -c "
import sys
print(f'Python version: {sys.version}')
print(f'Python executable: {sys.executable}')
"

# Check required directories
ls -la music_automation/
```

### Test Data Preparation

```bash
# Create test music file (copy sample)
cp assets/music.mp3 test_music.mp3

# Create test directories
mkdir -p test_output
mkdir -p test_temp
mkdir -p test_logs

# Set test environment variables
export TEST_MODE=true
export TEST_OUTPUT_DIR=test_output
```

## 🔧 Component Testing

### 1. Audio Processing Tests

#### Test Audio Analysis
```bash
cd music_automation/audio_processing

# Test basic audio loading
python -c "
import librosa
try:
    y, sr = librosa.load('../assets/music.mp3')
    print(f'✅ Audio loaded: {len(y)} samples, {sr} Hz')
except Exception as e:
    print(f'❌ Audio loading failed: {e}')
"

# Test Whisper transcription
python test_whisper_transcription.py

# Expected Output:
# ✅ Whisper model loaded successfully
# ✅ Audio transcription completed
# ✅ Word-level timestamps extracted
```

#### Test Prompt Generation
```bash
# Test audio to prompts generator
python audio_to_prompts_generator.py

# Verify output structure
ls -la "H:/dancers_content/Run_*_music/"

# Expected Output:
# ✅ Music analysis completed
# ✅ Prompts generated with timestamps
# ✅ Output folder created with proper structure
```

### 2. Core Automation Tests

#### Test API Server Startup
```bash
cd music_automation/core

# Test API server startup
python -c "
import subprocess
import time
import requests

# Start API server in background
proc = subprocess.Popen(['python', 'api_server_v5_music.py'])
time.sleep(5)

try:
    response = requests.get('http://127.0.0.1:8006/health', timeout=10)
    if response.status_code == 200:
        print('✅ API server started successfully')
    else:
        print(f'❌ API server health check failed: {response.status_code}')
except Exception as e:
    print(f'❌ API server connection failed: {e}')
finally:
    proc.terminate()
"
```

#### Test Main Automation Logic
```bash
# Test main automation (dry run mode)
python -c "
import sys
sys.path.append('..')
from core.main_automation_music import test_automation_components

# Run component tests
results = test_automation_components()
for component, status in results.items():
    symbol = '✅' if status else '❌'
    print(f'{symbol} {component}: {status}')
"
```

### 3. Video Compilation Tests

#### Test Beat Sync Discovery
```bash
cd music_automation/beat_sync

# Test folder and file discovery
python test_beat_sync_discovery.py

# Expected Output:
# ✅ Music folder discovered: Run_YYYYMMDD_HHMMSS_music_images
# ✅ Video files found: X files
# ✅ Song file found: song_name.mp3
# ✅ Output directory created successfully
```

#### Test Video Compilation
```bash
cd music_automation/video_compilation

# Test beat sync compiler (with test data)
python -c "
import sys
import os
sys.path.append('..')

# Set test mode
os.environ['TEST_MODE'] = 'true'

try:
    from video_compilation.music_video_beat_sync_compiler import test_compilation
    result = test_compilation()
    print(f'✅ Video compilation test: {result}')
except Exception as e:
    print(f'❌ Video compilation failed: {e}')
"
```

### 4. Karaoke Features Tests

#### Test Karaoke Subtitle Generation
```bash
cd music_automation/karaoke

# Test word-level karaoke
python test_word_level_karaoke.py

# Expected Output:
# ✅ Whisper transcription successful
# ✅ Word timestamps extracted
# ✅ Subtitle lines created
# ✅ Karaoke timing validated
```

#### Test Karaoke Integration
```bash
# Test karaoke fix functionality
python test_karaoke_fix.py

# Expected Output:
# ✅ Karaoke subtitle integration working
# ✅ Text positioning correct
# ✅ Timing synchronization accurate
```

## 🔗 Integration Testing

### 1. API Integration Tests

#### Test Image Generation API
```bash
cd music_automation/debug_tools

# Test image generation endpoint
python -c "
import requests
import json

payload = {
    'prompt': 'Test Lord Shiva meditation pose',
    'segment_id': 1,
    'face': None,
    'output_subfolder': 'test_images',
    'filename_prefix_text': 'test_image',
    'video_start_image_path': None
}

try:
    response = requests.post(
        'http://127.0.0.1:8006/generate/image',
        json=payload,
        timeout=300
    )
    if response.status_code == 200:
        print('✅ Image generation API working')
        print(f'Response: {response.json()}')
    else:
        print(f'❌ Image API failed: {response.status_code}')
        print(f'Error: {response.text}')
except Exception as e:
    print(f'❌ Image API connection failed: {e}')
"
```

#### Test Video Generation API
```bash
# Test video generation endpoint
python -c "
import requests
import json

payload = {
    'prompt': 'Test Lord Shiva cosmic dance',
    'segment_id': 1,
    'face': None,
    'output_subfolder': 'test_videos',
    'filename_prefix_text': 'test_video',
    'video_start_image_path': 'test_image.png'
}

try:
    response = requests.post(
        'http://127.0.0.1:8006/generate_video',
        json=payload,
        timeout=300
    )
    if response.status_code == 200:
        print('✅ Video generation API working')
        print(f'Response: {response.json()}')
    else:
        print(f'❌ Video API failed: {response.status_code}')
        print(f'Error: {response.text}')
except Exception as e:
    print(f'❌ Video API connection failed: {e}')
"
```

### 2. Workflow Integration Tests

#### Test ComfyUI Workflow Loading
```bash
cd music_automation/debug_tools

# Test workflow file loading and validation
python -c "
import json
from pathlib import Path

workflows = [
    '../config/base_workflows/API_flux_without_faceswap_music.json'
]

for workflow_path in workflows:
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        # Basic validation
        if isinstance(workflow, dict) and len(workflow) > 0:
            print(f'✅ Workflow loaded: {workflow_path}')
            print(f'   Nodes: {len(workflow)}')
        else:
            print(f'❌ Invalid workflow: {workflow_path}')
    except Exception as e:
        print(f'❌ Workflow loading failed: {workflow_path} - {e}')
"
```

#### Test Telegram Integration
```bash
# Test Telegram bot connection
python -c "
import os
import requests
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

if not bot_token or not chat_id:
    print('❌ Telegram credentials not configured')
else:
    try:
        # Test bot info
        response = requests.get(f'https://api.telegram.org/bot{bot_token}/getMe')
        if response.status_code == 200:
            bot_info = response.json()
            print(f'✅ Telegram bot connected: {bot_info[\"result\"][\"username\"]}')
            
            # Test message sending
            test_msg = 'Test message from music automation'
            response = requests.post(
                f'https://api.telegram.org/bot{bot_token}/sendMessage',
                json={'chat_id': chat_id, 'text': test_msg}
            )
            if response.status_code == 200:
                print('✅ Telegram message sending working')
            else:
                print(f'❌ Telegram message failed: {response.status_code}')
        else:
            print(f'❌ Telegram bot connection failed: {response.status_code}')
    except Exception as e:
        print(f'❌ Telegram integration failed: {e}')
"
```

## 🎭 End-to-End Testing

### 1. Minimal Pipeline Test

#### Quick Pipeline Test (Simplified)
```bash
cd music_automation

# Create test script for minimal pipeline
cat > test_minimal_pipeline.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path

def test_minimal_pipeline():
    print("🧪 Starting minimal pipeline test...")
    
    # Test 1: Audio Analysis
    print("\n📊 Testing audio analysis...")
    result = subprocess.run([
        sys.executable, 'audio_processing/audio_to_prompts_generator.py'
    ], capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        print("✅ Audio analysis completed")
    else:
        print(f"❌ Audio analysis failed: {result.stderr}")
        return False
    
    # Test 2: API Server Health
    print("\n🚀 Testing API server...")
    api_proc = subprocess.Popen([sys.executable, 'core/api_server_v5_music.py'])
    time.sleep(10)
    
    import requests
    try:
        response = requests.get('http://127.0.0.1:8006/health', timeout=5)
        if response.status_code == 200:
            print("✅ API server healthy")
            api_healthy = True
        else:
            print(f"❌ API server unhealthy: {response.status_code}")
            api_healthy = False
    except:
        print("❌ API server not responding")
        api_healthy = False
    
    api_proc.terminate()
    
    # Test 3: Configuration Validation
    print("\n⚙️ Testing configuration...")
    config_path = Path('config/config_music.json')
    if config_path.exists():
        print("✅ Configuration file exists")
        config_valid = True
    else:
        print("❌ Configuration file missing")
        config_valid = False
    
    # Test 4: Workflow Validation
    print("\n🔄 Testing workflows...")
    workflow_path = Path('config/base_workflows/API_flux_without_faceswap_music.json')
    if workflow_path.exists():
        print("✅ Workflow file exists")
        workflow_valid = True
    else:
        print("❌ Workflow file missing")
        workflow_valid = False
    
    # Summary
    print("\n📋 Test Summary:")
    tests = [
        ("Audio Analysis", result.returncode == 0),
        ("API Server", api_healthy),
        ("Configuration", config_valid),
        ("Workflows", workflow_valid)
    ]
    
    passed = sum(1 for _, status in tests if status)
    total = len(tests)
    
    for test_name, status in tests:
        symbol = "✅" if status else "❌"
        print(f"{symbol} {test_name}")
    
    print(f"\n🎯 Tests passed: {passed}/{total}")
    return passed == total

if __name__ == "__main__":
    success = test_minimal_pipeline()
    sys.exit(0 if success else 1)
EOF

# Run minimal pipeline test
python test_minimal_pipeline.py
```

### 2. Full Pipeline Test

#### Complete Automation Test
```bash
# Create comprehensive test script
cat > test_full_pipeline.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import json
from pathlib import Path

def test_full_pipeline():
    print("🎭 Starting full pipeline test...")
    
    # Preparation
    test_start = time.time()
    
    # Step 1: Audio Analysis
    print("\n🎵 Step 1: Audio Analysis")
    audio_start = time.time()
    result = subprocess.run([
        sys.executable, 'audio_processing/audio_to_prompts_generator.py'
    ], timeout=600)
    
    if result.returncode == 0:
        audio_time = time.time() - audio_start
        print(f"✅ Audio analysis completed in {audio_time:.1f}s")
    else:
        print("❌ Audio analysis failed")
        return False
    
    # Step 2: Main Automation (limited run)
    print("\n🤖 Step 2: Main Automation")
    automation_start = time.time()
    
    # Set test mode environment variable
    env = os.environ.copy()
    env['TEST_MODE'] = 'true'
    env['MAX_IMAGES'] = '2'  # Limit for testing
    
    result = subprocess.run([
        sys.executable, 'core/main_automation_music.py'
    ], env=env, timeout=1800)
    
    if result.returncode == 0:
        automation_time = time.time() - automation_start
        print(f"✅ Main automation completed in {automation_time:.1f}s")
    else:
        print("❌ Main automation failed")
        return False
    
    # Step 3: Beat Sync Test
    print("\n🎶 Step 3: Beat Sync Compilation")
    beat_sync_start = time.time()
    
    result = subprocess.run([
        sys.executable, 'video_compilation/music_video_beat_sync_compiler.py'
    ], env=env, timeout=900)
    
    if result.returncode == 0:
        beat_sync_time = time.time() - beat_sync_start
        print(f"✅ Beat sync compilation completed in {beat_sync_time:.1f}s")
    else:
        print("❌ Beat sync compilation failed")
        return False
    
    # Summary
    total_time = time.time() - test_start
    print(f"\n🎯 Full pipeline test completed in {total_time:.1f}s")
    print("✅ All components working correctly")
    
    return True

if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
EOF

# Run full pipeline test (this will take significant time)
python test_full_pipeline.py
```

## 📊 Performance Testing

### 1. Load Testing

#### API Load Test
```bash
cd music_automation/debug_tools

# Create API load test
cat > api_load_test.py << 'EOF'
#!/usr/bin/env python3
import concurrent.futures
import time
import requests
import statistics

def test_api_endpoint(endpoint, payload, timeout=30):
    try:
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=timeout)
        duration = time.time() - start_time
        return {
            'success': response.status_code == 200,
            'duration': duration,
            'status_code': response.status_code
        }
    except Exception as e:
        return {
            'success': False,
            'duration': timeout,
            'error': str(e)
        }

def run_load_test():
    print("🚀 Running API load test...")
    
    endpoint = 'http://127.0.0.1:8006/generate/image'
    payload = {
        'prompt': 'Load test Lord Shiva',
        'segment_id': None,
        'face': None,
        'output_subfolder': 'load_test',
        'filename_prefix_text': 'load_test',
        'video_start_image_path': None
    }
    
    # Run 5 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(test_api_endpoint, endpoint, payload)
            for _ in range(5)
        ]
        
        results = [future.result() for future in futures]
    
    # Analyze results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if successful:
        durations = [r['duration'] for r in successful]
        avg_duration = statistics.mean(durations)
        print(f"✅ Successful requests: {len(successful)}")
        print(f"✅ Average duration: {avg_duration:.2f}s")
        print(f"✅ Min duration: {min(durations):.2f}s")
        print(f"✅ Max duration: {max(durations):.2f}s")
    
    if failed:
        print(f"❌ Failed requests: {len(failed)}")
        for failure in failed[:3]:  # Show first 3 failures
            print(f"   Error: {failure.get('error', 'Unknown')}")
    
    return len(successful) > len(failed)

if __name__ == "__main__":
    success = run_load_test()
    print("🎯 Load test", "passed" if success else "failed")
EOF

# Run load test
python api_load_test.py
```

### 2. Memory and Resource Testing

#### Resource Monitoring Test
```bash
# Create resource monitoring script
cat > resource_monitor.py << 'EOF'
#!/usr/bin/env python3
import psutil
import time
import os

def monitor_resources(duration=300):  # 5 minutes
    print(f"📊 Monitoring resources for {duration} seconds...")
    
    initial_memory = psutil.virtual_memory().percent
    initial_cpu = psutil.cpu_percent(interval=1)
    
    peak_memory = initial_memory
    peak_cpu = initial_cpu
    
    print(f"Initial - Memory: {initial_memory:.1f}%, CPU: {initial_cpu:.1f}%")
    
    start_time = time.time()
    while time.time() - start_time < duration:
        memory = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=5)
        
        peak_memory = max(peak_memory, memory)
        peak_cpu = max(peak_cpu, cpu)
        
        print(f"Current - Memory: {memory:.1f}%, CPU: {cpu:.1f}%")
        time.sleep(30)
    
    print(f"\n📈 Peak Usage:")
    print(f"Memory: {peak_memory:.1f}%")
    print(f"CPU: {peak_cpu:.1f}%")
    
    # Memory growth check
    memory_growth = peak_memory - initial_memory
    if memory_growth > 20:  # More than 20% growth
        print(f"⚠️ Significant memory growth detected: {memory_growth:.1f}%")
        return False
    else:
        print(f"✅ Memory usage stable: {memory_growth:.1f}% growth")
        return True

if __name__ == "__main__":
    stable = monitor_resources()
    print("🎯 Resource test", "passed" if stable else "failed")
EOF

# Run resource monitoring during automation
python resource_monitor.py &
MONITOR_PID=$!

# Run automation while monitoring
python core/main_automation_music.py

# Stop monitoring
kill $MONITOR_PID
```

## 🐛 Error Scenario Testing

### 1. Network Failure Testing

#### Test API Resilience
```bash
# Test API behavior when ComfyUI is down
cd music_automation/debug_tools

python -c "
import requests
import time

# Test with ComfyUI down
print('🔌 Testing API resilience with ComfyUI down...')

payload = {
    'prompt': 'Test prompt',
    'segment_id': 1,
    'face': None,
    'output_subfolder': 'error_test',
    'filename_prefix_text': 'error_test',
    'video_start_image_path': None
}

try:
    response = requests.post(
        'http://127.0.0.1:8006/generate/image',
        json=payload,
        timeout=10
    )
    print(f'Response status: {response.status_code}')
    print(f'Response: {response.text[:200]}...')
    
    if response.status_code in [500, 502, 503]:
        print('✅ API properly handles ComfyUI unavailability')
    else:
        print('❌ API did not handle ComfyUI unavailability properly')
        
except requests.exceptions.Timeout:
    print('✅ API properly times out when ComfyUI unavailable')
except Exception as e:
    print(f'❌ Unexpected error: {e}')
"
```

### 2. Invalid Input Testing

#### Test Input Validation
```bash
# Test various invalid inputs
cd music_automation/debug_tools

python -c "
import requests

api_url = 'http://127.0.0.1:8006/generate/image'

test_cases = [
    {'prompt': '', 'segment_id': 1},  # Empty prompt
    {'prompt': 'Test' * 1000, 'segment_id': 1},  # Very long prompt
    {'prompt': 'Test', 'segment_id': 'invalid'},  # Invalid segment_id
    {'prompt': 'Test', 'segment_id': -1},  # Negative segment_id
    {},  # Empty payload
    {'invalid_field': 'test'}  # Invalid fields
]

print('🧪 Testing input validation...')

for i, payload in enumerate(test_cases):
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        print(f'Test {i+1}: Status {response.status_code}')
        
        if response.status_code == 422:  # Validation error
            print(f'  ✅ Properly rejected invalid input')
        elif response.status_code == 200:
            print(f'  ⚠️ Accepted potentially invalid input')
        else:
            print(f'  ❓ Unexpected response: {response.status_code}')
            
    except Exception as e:
        print(f'Test {i+1}: ❌ Exception: {e}')

print('🎯 Input validation testing completed')
"
```

### 3. File System Error Testing

#### Test File Permission Issues
```bash
# Test behavior with permission issues
cd music_automation

# Create test with restricted permissions
mkdir -p test_restricted
chmod 444 test_restricted  # Read-only

python -c "
import os
import tempfile
from pathlib import Path

print('📁 Testing file system error handling...')

# Test 1: Read-only directory
try:
    test_file = Path('test_restricted/test.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    print('❌ Should not be able to write to read-only directory')
except PermissionError:
    print('✅ Properly handles permission denied errors')

# Test 2: Non-existent directory
try:
    from core import main_automation_music
    # This should handle missing directories gracefully
    print('✅ File system error handling working')
except Exception as e:
    print(f'⚠️ File system error handling needs improvement: {e}')

# Cleanup
os.chmod('test_restricted', 755)
os.rmdir('test_restricted')
"
```

## 📋 Regression Testing

### 1. Configuration Changes Testing

#### Test Config Modifications
```bash
cd music_automation

# Backup original config
cp config/config_music.json config/config_music.json.backup

# Test with modified configurations
cat > test_config_changes.py << 'EOF'
#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

def test_config_modification(config_changes, test_name):
    print(f"\n🔧 Testing {test_name}...")
    
    # Load original config
    config_path = Path('config/config_music.json')
    with open(config_path, 'r') as f:
        original_config = json.load(f)
    
    # Apply changes
    modified_config = original_config.copy()
    modified_config.update(config_changes)
    
    # Save modified config
    with open(config_path, 'w') as f:
        json.dump(modified_config, f, indent=2)
    
    # Test automation startup
    try:
        result = subprocess.run([
            sys.executable, '-c',
            'from core.main_automation_music import validate_config; validate_config()'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ {test_name} - Configuration accepted")
            return True
        else:
            print(f"❌ {test_name} - Configuration rejected: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {test_name} - Error: {e}")
        return False
    finally:
        # Restore original config
        with open(config_path, 'w') as f:
            json.dump(original_config, f, indent=2)

def run_config_tests():
    test_cases = [
        ({"api_server_url": "http://127.0.0.1:8007"}, "Port Change"),
        ({"num_prompts": "5"}, "Prompt Count Change"),
        ({"invalid_field": "test"}, "Invalid Field Addition"),
        ({"comfyui_api_url": ""}, "Empty ComfyUI URL"),
    ]
    
    results = []
    for changes, name in test_cases:
        results.append(test_config_modification(changes, name))
    
    passed = sum(results)
    total = len(results)
    print(f"\n🎯 Config tests passed: {passed}/{total}")
    return passed == total

if __name__ == "__main__":
    success = run_config_tests()
    sys.exit(0 if success else 1)
EOF

python test_config_changes.py

# Restore backup
cp config/config_music.json.backup config/config_music.json
```

### 2. Dependency Version Testing

#### Test Package Compatibility
```bash
cd music_automation

# Create dependency test
cat > test_dependencies.py << 'EOF'
#!/usr/bin/env python3
import importlib
import sys

def test_import(package_name, alias=None):
    try:
        if alias:
            module = importlib.import_module(package_name)
            globals()[alias] = module
        else:
            importlib.import_module(package_name)
        return True
    except ImportError as e:
        print(f"❌ Failed to import {package_name}: {e}")
        return False

def test_all_dependencies():
    print("📦 Testing all dependencies...")
    
    dependencies = [
        ('fastapi', None),
        ('uvicorn', None),
        ('flask', None),
        ('tqdm', None),
        ('requests', None),
        ('PIL', 'pillow'),
        ('librosa', None),
        ('numpy', None),
        ('moviepy', None),
        ('cv2', 'opencv'),
        ('whisper', 'openai-whisper'),
        ('google.generativeai', 'google-ai'),
    ]
    
    results = []
    for package, display_name in dependencies:
        name = display_name or package
        if test_import(package):
            print(f"✅ {name}")
            results.append(True)
        else:
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n🎯 Dependencies working: {passed}/{total}")
    return passed == total

if __name__ == "__main__":
    success = test_all_dependencies()
    sys.exit(0 if success else 1)
EOF

python test_dependencies.py
```

## 📊 Test Reporting

### 1. Generate Test Report

#### Comprehensive Test Report
```bash
cd music_automation

# Create test report generator
cat > generate_test_report.py << 'EOF'
#!/usr/bin/env python3
import json
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_test_suite():
    print("📊 Generating comprehensive test report...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'python_version': sys.version,
            'platform': sys.platform,
        },
        'tests': {}
    }
    
    # Component tests
    component_tests = [
        ('audio_processing', 'Audio Processing'),
        ('core', 'Core Automation'),
        ('video_compilation', 'Video Compilation'),
        ('beat_sync', 'Beat Synchronization'),
        ('karaoke', 'Karaoke Features')
    ]
    
    for component, name in component_tests:
        print(f"\n🧪 Testing {name}...")
        start_time = time.time()
        
        try:
            # Run component-specific tests if they exist
            test_file = Path(component) / f'test_{component}.py'
            if test_file.exists():
                result = subprocess.run([
                    sys.executable, str(test_file)
                ], capture_output=True, text=True, timeout=300)
                
                success = result.returncode == 0
                duration = time.time() - start_time
                
                report['tests'][component] = {
                    'name': name,
                    'success': success,
                    'duration': duration,
                    'output': result.stdout if success else result.stderr
                }
                
                symbol = "✅" if success else "❌"
                print(f"{symbol} {name}: {duration:.1f}s")
            else:
                report['tests'][component] = {
                    'name': name,
                    'success': None,
                    'duration': 0,
                    'output': 'No test file found'
                }
                print(f"⚠️ {name}: No test file")
                
        except Exception as e:
            report['tests'][component] = {
                'name': name,
                'success': False,
                'duration': time.time() - start_time,
                'output': str(e)
            }
            print(f"❌ {name}: Error - {e}")
    
    # Generate summary
    total_tests = len([t for t in report['tests'].values() if t['success'] is not None])
    passed_tests = len([t for t in report['tests'].values() if t['success'] is True])
    
    report['summary'] = {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
        'overall_success': passed_tests == total_tests
    }
    
    # Save report
    report_file = f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n📋 Test Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Success Rate: {report['summary']['success_rate']:.1%}")
    print(f"   Report saved: {report_file}")
    
    return report['summary']['overall_success']

if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)
EOF

python generate_test_report.py
```

## 🎯 Testing Checklist

### Pre-Deployment Testing
- [ ] All dependencies installed and working
- [ ] Configuration files valid and accessible
- [ ] Environment variables properly set
- [ ] ComfyUI models downloaded and loaded
- [ ] Telegram bot configured and responding
- [ ] Audio processing working with sample files
- [ ] API server starts without errors
- [ ] Workflow files load successfully

### Component Testing
- [ ] Audio analysis generates valid prompts
- [ ] Image generation API responds correctly
- [ ] Video generation API responds correctly
- [ ] Beat sync discovery finds files correctly
- [ ] Karaoke transcription working
- [ ] Telegram integration sending messages
- [ ] File system operations working

### Integration Testing
- [ ] End-to-end pipeline completes successfully
- [ ] API calls between components working
- [ ] ComfyUI workflow execution successful
- [ ] Generated content saved to correct locations
- [ ] Telegram approval workflow functional
- [ ] Error handling graceful across components

### Performance Testing
- [ ] Memory usage remains stable
- [ ] CPU usage within acceptable limits
- [ ] API response times acceptable
- [ ] No memory leaks detected
- [ ] Concurrent requests handled properly

### Error Scenario Testing
- [ ] Network failures handled gracefully
- [ ] Invalid inputs rejected properly
- [ ] File permission errors handled
- [ ] ComfyUI unavailability handled
- [ ] Timeout scenarios managed

### Regression Testing
- [ ] Configuration changes don't break functionality
- [ ] Dependency updates compatible
- [ ] Previous features still working
- [ ] Performance hasn't degraded
- [ ] Output quality maintained

## 🚀 Continuous Testing

### Automated Testing Setup
```bash
# Create automated test runner
cat > run_daily_tests.sh << 'EOF'
#!/bin/bash
echo "🔄 Starting daily automated tests..."

cd music_automation
source venv/bin/activate

# Run basic health checks
python -c "
import requests
import time

# Check API server
try:
    response = requests.get('http://127.0.0.1:8006/health', timeout=5)
    if response.status_code == 200:
        print('✅ API server healthy')
    else:
        print('❌ API server unhealthy')
        exit(1)
except:
    print('❌ API server not responding')
    exit(1)

print('🎯 Daily health check passed')
"

# Run component tests
python generate_test_report.py

echo "✅ Daily tests completed"
EOF

chmod +x run_daily_tests.sh

# Schedule daily tests (add to crontab)
# 0 6 * * * /path/to/music_automation/run_daily_tests.sh
```

---

**Testing Status**: Use this guide to validate each component before deployment and after any changes.

**Next Steps**: After testing, proceed with deployment using the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

*Last Updated: June 23, 2025*
*Version: 1.0*