#!/usr/bin/env python3
"""
Environment Setup Script for Music Automation

This script helps you set up the required environment variables and API keys.
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check current environment setup"""
    print("Checking Music Automation Environment Setup")
    print("=" * 50)
    
    # Check for .env file in parent directory
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        print("SUCCESS: .env file found")
        
        # Load and check environment variables
        load_env_file()
        
        required_vars = [
            'GOOGLE_API_KEY',
            'TELEGRAM_BOT_TOKEN', 
            'TELEGRAM_CHAT_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            value = os.getenv(var) or os.getenv(var.replace('GOOGLE_', 'GEMINI_'))
            if value and value != 'your_' + var.lower() + '_here':
                print(f"SUCCESS: {var} is configured")
            else:
                missing_vars.append(var)
                print(f"WARNING: {var} is missing or not configured")
        
        if missing_vars:
            print(f"\nNEXT STEPS: Configure these environment variables:")
            for var in missing_vars:
                if 'GOOGLE' in var:
                    print(f"  {var}: Get from https://makersuite.google.com/app/apikey")
                elif 'TELEGRAM_BOT' in var:
                    print(f"  {var}: Get from @BotFather on Telegram")
                elif 'TELEGRAM_CHAT' in var:
                    print(f"  {var}: Get by messaging your bot, then visit:")
                    print(f"         https://api.telegram.org/bot<TOKEN>/getUpdates")
            return False
        else:
            print("\nSUCCESS: All required environment variables are configured!")
            return True
            
    else:
        print("WARNING: .env file not found")
        print("\nCREATING: .env file from template...")
        
        print("INFO: .env file found in parent directory")
        print("Using existing .env file from parent directory")
        print("\nNEXT STEPS:")
        print("1. Verify your API keys are configured in the parent .env file")
        print("2. Run this script again to verify setup")
        
        return False

def load_env_file(env_path=None):
    """Load environment variables from .env file"""
    if env_path is None:
        # Use parent directory .env file
        env_path = Path(__file__).resolve().parent.parent / ".env"
    else:
        env_path = Path(env_path)
        
    if not env_path.exists():
        return False
        
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                os.environ[key] = value
    return True

def test_google_api():
    """Test Google API connection"""
    print("\nTesting Google API connection...")
    
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key or api_key.startswith('your_'):
        print("WARNING: Google API key not configured")
        return False
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Test with a simple request
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'API test successful'")
        
        if response.text:
            print("SUCCESS: Google API connection working")
            return True
        else:
            print("WARNING: Google API responded but with empty content")
            return False
            
    except ImportError:
        print("WARNING: google-generativeai package not installed")
        print("Install with: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"ERROR: Google API test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("Music Automation Environment Setup")
    print("=" * 50)
    
    # Check environment
    env_ok = check_environment()
    
    if env_ok:
        # Test Google API if configured
        api_ok = test_google_api()
        
        if api_ok:
            print("\n" + "=" * 50)
            print("SUCCESS: Environment setup complete!")
            print("You can now run: python run_music_automation.py --mode automation")
            return True
        else:
            print("\n" + "=" * 50)
            print("WARNING: Environment variables configured but API test failed")
            print("Check your API keys and internet connection")
            return False
    else:
        print("\n" + "=" * 50)
        print("TODO: Complete environment setup first")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\nSetup {'completed' if success else 'incomplete'}")
    sys.exit(0 if success else 1)