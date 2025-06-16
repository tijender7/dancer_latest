#!/usr/bin/env python3
"""
Security Check Script - Detects hardcoded credentials in Python files
"""

import os
import re
from pathlib import Path

# Patterns to detect hardcoded credentials
CREDENTIAL_PATTERNS = [
    # API Keys and tokens
    (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
    (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
    (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
    (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
    
    # Specific patterns
    (r'ACCESS_TOKEN\s*=\s*["\']EAA[^"\']+["\']', "Hardcoded Facebook/Instagram access token"),
    (r'BOT_TOKEN\s*=\s*["\'][0-9]+:[^"\']+["\']', "Hardcoded Telegram bot token"),
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key pattern"),
    (r'sk-ant-[a-zA-Z0-9]{20,}', "Anthropic API key pattern"),
    
    # Instagram/Facebook IDs
    (r'APP_ID\s*=\s*["\'][0-9]{15,}["\']', "Hardcoded Facebook App ID"),
    (r'PAGE_ID\s*=\s*["\'][0-9]{12,}["\']', "Hardcoded Facebook Page ID"),
    (r'CHAT_ID\s*=\s*["\']?[0-9]{9,}["\']?', "Hardcoded Telegram Chat ID"),
]

def check_file(file_path):
    """Check a single file for hardcoded credentials."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        for pattern, description in CREDENTIAL_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'line': line_num,
                    'description': description,
                    'match': match.group()[:50] + "..." if len(match.group()) > 50 else match.group()
                })
        
        return issues
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def scan_directory(directory):
    """Scan directory for Python files with hardcoded credentials."""
    print("🔍 Scanning for hardcoded credentials...")
    print("=" * 60)
    
    total_files = 0
    total_issues = 0
    
    # Get all Python files in the directory (excluding venv)
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment directories
        if 'venv' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    for file_path in python_files:
        issues = check_file(file_path)
        if issues:
            total_issues += len(issues)
            print(f"\n❌ {file_path.relative_to(directory)}")
            for issue in issues:
                print(f"   Line {issue['line']}: {issue['description']}")
                print(f"   Match: {issue['match']}")
        
        total_files += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Scan Results:")
    print(f"   Files scanned: {total_files}")
    print(f"   Issues found: {total_issues}")
    
    if total_issues == 0:
        print("✅ No hardcoded credentials detected!")
    else:
        print("⚠️  Security issues found! Please move credentials to .env file.")
    
    return total_issues

def main():
    print("🛡️  Security Check - Hardcoded Credentials Scanner")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    total_issues = scan_directory(script_dir)
    
    if total_issues > 0:
        print("\n💡 Recommendations:")
        print("1. Move all hardcoded credentials to .env file")
        print("2. Use os.getenv() to load environment variables")
        print("3. Add .env to .gitignore to prevent committing secrets")
        print("4. Use python-dotenv to load .env variables")
        
        print("\n📝 Example fix:")
        print("   Instead of: SAMPLE_KEY = 'hardcoded_value'")
        print("   Use: SAMPLE_KEY = os.getenv('SAMPLE_KEY')")
    
    return total_issues

if __name__ == "__main__":
    exit_code = main()
    exit(1 if exit_code > 0 else 0)