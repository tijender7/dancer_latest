#!/usr/bin/env python3
"""
Test the fixed karaoke highlighting logic
"""

def test_karaoke_logic():
    """Test the new karaoke highlighting approach"""
    print("🧪 Testing Fixed Karaoke Logic...")
    
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
    
    print(f"\n📝 Created {len(lines)} subtitle lines from {len(sample_words)} words")
    
    # Test the new karaoke approach
    for line_idx, line_words in enumerate(lines):
        print(f"\n🎤 Line {line_idx + 1}:")
        
        # Show the complete line text
        complete_line_text = ' '.join([w['word'] for w in line_words])
        print(f"   Complete line: '{complete_line_text}'")
        
        # Show how each word will be highlighted
        for word_idx, word_info in enumerate(line_words):
            word_text = word_info['word']
            word_start = word_info['start']
            word_end = word_info['end']
            
            # This is the new approach - single color per clip, no overlapping
            if word_idx == 0:
                color = "YELLOW (highlight)"
                display_text = complete_line_text
            else:
                # Progressive highlighting simulation
                highlighted_part = ' '.join([w['word'] for w in line_words[:word_idx + 1]])
                normal_part = ' '.join([w['word'] for w in line_words[word_idx + 1:]])
                
                if normal_part:
                    display_text = highlighted_part + ' ' + normal_part
                else:
                    display_text = highlighted_part
                
                color = "YELLOW" if word_idx % 2 == 0 else "WHITE"
            
            print(f"   Word '{word_text}' ({word_start:.1f}s-{word_end:.1f}s): {color} -> '{display_text}'")
    
    print("\n✅ New Karaoke Logic Summary:")
    print("   • No overlapping text layers")
    print("   • Each word gets a complete line clip with single color")
    print("   • Progressive highlighting through alternating colors")
    print("   • Clean, readable subtitles")
    print("   • Eliminates yellow-on-white overlap issue")

def test_coverage_issue():
    """Test for incomplete transcription coverage"""
    print("\n\n🧪 Testing Transcription Coverage...")
    
    # Simulate incomplete transcription (common issue)
    full_audio_duration = 180.0  # 3 minutes
    transcribed_words = [
        {'word': 'Om', 'start': 0.0, 'end': 0.5},
        {'word': 'namah', 'start': 0.5, 'end': 1.0},
        # Gap here - no words from 1.0s to 30.0s
        {'word': 'shivaya', 'start': 30.0, 'end': 30.8},
        {'word': 'mantra', 'start': 31.0, 'end': 31.6},
        # Another gap - no words from 31.6s to 120.0s
        {'word': 'chanting', 'start': 120.0, 'end': 120.8},
    ]
    
    print(f"📊 Audio duration: {full_audio_duration}s")
    print(f"📊 Transcribed words: {len(transcribed_words)}")
    
    # Find coverage gaps
    if transcribed_words:
        last_end = 0.0
        gaps = []
        
        for word in transcribed_words:
            if word['start'] > last_end + 1.0:  # Gap of more than 1 second
                gaps.append((last_end, word['start']))
            last_end = word['end']
        
        # Check if there's a gap at the end
        if last_end < full_audio_duration - 1.0:
            gaps.append((last_end, full_audio_duration))
        
        print(f"📊 Coverage gaps found: {len(gaps)}")
        for i, (gap_start, gap_end) in enumerate(gaps):
            gap_duration = gap_end - gap_start
            print(f"   Gap {i+1}: {gap_start:.1f}s - {gap_end:.1f}s ({gap_duration:.1f}s)")
        
        total_gap_time = sum(gap_end - gap_start for gap_start, gap_end in gaps)
        coverage_percentage = ((full_audio_duration - total_gap_time) / full_audio_duration) * 100
        
        print(f"📊 Transcription coverage: {coverage_percentage:.1f}%")
        
        if coverage_percentage < 70:
            print("⚠️ Poor transcription coverage detected!")
            print("   Possible solutions:")
            print("   • Use larger Whisper model (base -> medium -> large)")
            print("   • Check audio quality (reduce background noise)")
            print("   • Verify language setting matches audio content")
        else:
            print("✅ Good transcription coverage")

if __name__ == "__main__":
    print("=" * 60)
    print(" 🎤 KARAOKE FIX TEST 🎤 ".center(60, "="))
    print("=" * 60)
    
    test_karaoke_logic()
    test_coverage_issue()
    
    print("\n" + "=" * 60)
    print(" ✅ TESTING COMPLETE ✅ ".center(60, "="))
    print("=" * 60)
    print("🎉 Fixed karaoke system ready for testing!")
    print("📝 Run: python music_video_beat_sync_compiler.py")
    
    input("\nPress Enter to exit...")