#!/usr/bin/env python3
"""
Fix Unicode/Emoji Issues in Audio Processing

This script replaces all emoji characters with text equivalents
to prevent Unicode encoding errors on Windows systems.
"""

import re
from pathlib import Path

def fix_unicode_in_file(file_path):
    """Replace emoji characters with text equivalents"""
    
    emoji_replacements = {
        "🔍": "SEARCH:",
        "❌": "ERROR:",
        "✅": "SUCCESS:",
        "⚠️": "WARNING:",
        "🎵": "MUSIC:",
        "📊": "STATS:",
        "🚀": "START:",
        "🎬": "VIDEO:",
        "🎯": "TARGET:",
        "⚡": "FAST:",
        "💾": "SAVE:",
        "🔧": "CONFIG:",
        "📝": "LOG:",
        "🌟": "FEATURE:"
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        for emoji, replacement in emoji_replacements.items():
            if emoji in content:
                count = content.count(emoji)
                content = content.replace(emoji, replacement)
                changes_made += count
                print(f"  Replaced {count} instances of '{emoji}' with '{replacement}'")
        
        if changes_made > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"SUCCESS: Fixed {changes_made} emoji characters in {file_path}")
            return True
        else:
            print(f"INFO: No emoji characters found in {file_path}")
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to process {file_path}: {e}")
        return False

def main():
    """Fix unicode issues in all relevant files"""
    print("🔧 Fixing Unicode/Emoji Issues...")
    print("=" * 50)
    
    files_to_fix = [
        "audio_processing/audio_to_prompts_generator.py",
        "core/main_automation_music.py",
        "core/api_server_v5_music.py",
        "core/run_pipeline_music.py",
        "video_compilation/music_video_beat_sync_compiler.py"
    ]
    
    fixed_files = 0
    total_files = len(files_to_fix)
    
    for file_path in files_to_fix:
        path_obj = Path(file_path)
        if path_obj.exists():
            print(f"\nProcessing: {file_path}")
            if fix_unicode_in_file(path_obj):
                fixed_files += 1
        else:
            print(f"WARNING: File not found: {file_path}")
    
    print("\n" + "=" * 50)
    print(f"SUMMARY: Processed {fixed_files}/{total_files} files")
    
    if fixed_files == total_files:
        print("SUCCESS: All files processed successfully!")
        print("\nYou can now run the automation without Unicode errors:")
        print("  python run_music_automation.py --mode automation")
    else:
        print("WARNING: Some files could not be processed.")
    
    return fixed_files == total_files

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)