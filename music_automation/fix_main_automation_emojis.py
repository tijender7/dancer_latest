#!/usr/bin/env python3
"""
Fix emoji characters in main_automation_music.py that cause Windows encoding errors
"""

import re
from pathlib import Path

# Define emoji replacements
EMOJI_REPLACEMENTS = {
    '📁': 'FOLDER:',
    '🎨': 'GENERATE:',
    '🎭': 'PROMPT:',
    '📤': 'SEND:',
    '🔗': 'URL:',
    '📦': 'DATA:',
    '⏰': 'TIMEOUT:',
    '🧪': 'TEST:',
    '🏥': 'HEALTH:',
    '📄': 'RESPONSE:',
    '⏳': 'WAIT:',
    '📈': 'PROGRESS:',
    '📱': 'TELEGRAM:',
    '➡️': 'ARROW:',
    '🎉': 'SUCCESS:',
    '🎞️': 'VIDEO:',
    '🧹': 'CLEANUP:',
    '💥': 'ERROR:',
    '→': ' -> ',
    '\xa0': ' ',  # Non-breaking space
    '️': '',  # Variation selector
}

def fix_emojis_in_file(file_path: Path):
    """Fix emoji characters in the specified file"""
    print(f"Fixing emojis in: {file_path}")
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count original emojis
    original_emojis = re.findall(r'[^\x00-\x7F]', content)
    print(f"Found {len(original_emojis)} non-ASCII characters")
    
    # Replace emojis
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        content = content.replace(emoji, replacement)
    
    # Check remaining non-ASCII characters
    remaining_emojis = re.findall(r'[^\x00-\x7F]', content)
    if remaining_emojis:
        print(f"Remaining non-ASCII characters: {set(remaining_emojis)}")
        # Replace any remaining non-ASCII with placeholders
        for char in set(remaining_emojis):
            content = content.replace(char, '[EMOJI]')
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Emoji replacement complete. Fixed {len(original_emojis)} characters")

if __name__ == "__main__":
    file_path = Path("core/main_automation_music.py")
    fix_emojis_in_file(file_path)
    print("Done!")