#!/usr/bin/env python3
"""
Test word-level karaoke functionality
"""

def test_word_grouping():
    """Test word grouping into lines"""
    print("🧪 Testing Word Grouping Logic...")
    
    # Sample word data (similar to what Whisper provides)
    sample_words = [
        {'word': 'Om', 'start': 0.0, 'end': 0.5},
        {'word': 'namah', 'start': 0.5, 'end': 1.0},
        {'word': 'shivaya', 'start': 1.0, 'end': 1.8},
        {'word': 'Om', 'start': 2.0, 'end': 2.5},
        {'word': 'namah', 'start': 2.5, 'end': 3.0},
        {'word': 'shivaya', 'start': 3.0, 'end': 3.8},
        {'word': 'mantra', 'start': 4.0, 'end': 4.6},
        {'word': 'chanting', 'start': 4.8, 'end': 5.5},
    ]
    
    WORDS_PER_LINE = 4
    
    # Group words into lines
    lines = []
    current_line = []
    
    for word_info in sample_words:
        current_line.append(word_info)
        if len(current_line) >= WORDS_PER_LINE:
            lines.append(current_line.copy())
            current_line = []
    
    # Add remaining words
    if current_line:
        lines.append(current_line)
    
    print(f"Input: {len(sample_words)} words")
    print(f"Output: {len(lines)} lines")
    
    for i, line in enumerate(lines):
        line_text = ' '.join([w['word'] for w in line])
        line_start = line[0]['start']
        line_end = line[-1]['end']
        print(f"Line {i+1}: '{line_text}' ({line_start:.1f}s - {line_end:.1f}s)")
        
        # Show word-level timing
        for word in line:
            print(f"  '{word['word']}': {word['start']:.1f}s - {word['end']:.1f}s")
    
    print("✅ Word grouping test complete!")

def test_configuration():
    """Test current configuration settings"""
    print("\n🧪 Testing Configuration...")
    
    config = {
        'WORDS_PER_LINE': 4,
        'SUBTITLE_FONTSIZE': 36,
        'SUBTITLE_COLOR_NORMAL': 'white',
        'SUBTITLE_COLOR_HIGHLIGHT': 'yellow',
        'SUBTITLE_MARGIN_BOTTOM': 50,
    }
    
    print("Current Settings:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # Calculate video resolution impact
    video_height = 720  # Assuming 720p
    subtitle_area = config['SUBTITLE_MARGIN_BOTTOM'] + config['SUBTITLE_FONTSIZE'] * 2  # Space for 2 lines
    available_video_height = video_height - subtitle_area
    
    print(f"\nVideo Layout:")
    print(f"  Video Height: {video_height}px")
    print(f"  Subtitle Area: {subtitle_area}px")
    print(f"  Available Video: {available_video_height}px ({available_video_height/video_height*100:.1f}%)")
    
    print("✅ Configuration test complete!")

if __name__ == "__main__":
    print("="*60)
    print(" 🎤 WORD-LEVEL KARAOKE TEST 🎤 ".center(60, "="))
    print("="*60)
    
    test_word_grouping()
    test_configuration()
    
    print("\n" + "="*60)
    print(" ✅ TESTS COMPLETE ✅ ".center(60, "="))
    print("="*60)
    print("🎉 Ready to test improved karaoke system!")
    print("📝 Run: python music_video_beat_sync_compiler.py")
    
    input("\nPress Enter to exit...")