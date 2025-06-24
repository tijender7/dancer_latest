#!/usr/bin/env python3
"""
Music Automation Setup Validator

This script validates that all components are properly set up after reorganization.
"""

import sys
import json
from pathlib import Path

def validate_structure():
    """Validate folder structure"""
    print("🔍 Validating folder structure...")
    
    required_dirs = [
        "core", "audio_processing", "video_compilation", 
        "beat_sync", "karaoke", "config", "debug_tools", 
        "docs", "assets"
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    else:
        print("✅ All required directories present")
        return True

def validate_config():
    """Validate configuration file"""
    print("🔍 Validating configuration...")
    
    config_path = Path("config/config_music.json")
    if not config_path.exists():
        print(f"❌ Configuration file missing: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        required_keys = [
            'comfyui_api_url', 'api_server_url', 
            'base_workflow_image', 'base_workflow_video'
        ]
        
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            print(f"❌ Missing config keys: {missing_keys}")
            return False
        
        print("✅ Configuration file valid")
        return True
        
    except Exception as e:
        print(f"❌ Configuration file error: {e}")
        return False

def validate_workflows():
    """Validate workflow files"""
    print("🔍 Validating workflow files...")
    
    workflow_file = Path("config/base_workflows/API_flux_without_faceswap_music.json")
    if not workflow_file.exists():
        print(f"❌ Workflow file missing: {workflow_file}")
        return False
    
    try:
        with open(workflow_file, 'r') as f:
            workflow = json.load(f)
        
        if not isinstance(workflow, dict) or len(workflow) == 0:
            print("❌ Invalid workflow file format")
            return False
        
        print("✅ Workflow files valid")
        return True
        
    except Exception as e:
        print(f"❌ Workflow file error: {e}")
        return False

def validate_core_files():
    """Validate core Python files"""
    print("🔍 Validating core files...")
    
    core_files = [
        "core/main_automation_music.py",
        "core/api_server_v5_music.py", 
        "core/run_pipeline_music.py",
        "audio_processing/audio_to_prompts_generator.py",
        "run_music_automation.py"
    ]
    
    missing_files = []
    for file_path in core_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing core files: {missing_files}")
        return False
    else:
        print("✅ All core files present")
        return True

def test_imports():
    """Test that imports work correctly"""
    print("🔍 Testing imports...")
    
    import_tests = [
        ("Core main automation", "sys.path.append('core'); import main_automation_music"),
        ("Audio processing", "sys.path.append('audio_processing'); import audio_to_prompts_generator"),
        ("Main entry point", "import run_music_automation")
    ]
    
    failed_imports = []
    for test_name, import_statement in import_tests:
        try:
            exec(import_statement)
            print(f"  ✅ {test_name}")
        except Exception as e:
            print(f"  ❌ {test_name}: {e}")
            failed_imports.append(test_name)
    
    if failed_imports:
        print(f"❌ Failed imports: {failed_imports}")
        return False
    else:
        print("✅ All imports working")
        return True

def test_config_loading():
    """Test configuration loading"""
    print("🔍 Testing config loading...")
    
    try:
        sys.path.append('core')
        import main_automation_music
        
        # Test config loading
        config = main_automation_music.load_config()
        print("✅ Configuration loading works")
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🧪 Music Automation Setup Validation")
    print("=" * 50)
    
    tests = [
        ("Folder Structure", validate_structure),
        ("Configuration File", validate_config),
        ("Workflow Files", validate_workflows),
        ("Core Files", validate_core_files),
        ("Import Tests", test_imports),
        ("Config Loading", test_config_loading)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            if test_func():
                passed += 1
            else:
                print(f"   Test failed: {test_name}")
        except Exception as e:
            print(f"   ❌ Error in {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All validation tests passed!")
        print("\n🚀 Ready to run:")
        print("   python run_music_automation.py --mode automation")
        return 0
    else:
        print("❌ Some validation tests failed!")
        print("\n🔧 Please fix the issues above before running the automation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())