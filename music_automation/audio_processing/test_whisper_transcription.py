#!/usr/bin/env python3
"""
Test Whisper transcription functionality
"""

from pathlib import Path

# Test configuration
SONGS_DIR = Path("D:/Comfy_UI_V20/ComfyUI/output/dancer/songs")

def test_whisper_import():
    """Test if Whisper can be imported"""
    print("🧪 Testing Whisper Import...")
    
    try:
        import whisper
        print("✅ Whisper imported successfully")
        
        # Test model loading (using tiny model for faster testing)
        print("📥 Loading Whisper tiny model for testing...")
        model = whisper.load_model("tiny")
        print("✅ Whisper tiny model loaded successfully")
        
        return True
    except ImportError:
        print("❌ Whisper not available. Install with: pip install openai-whisper")
        return False
    except Exception as e:
        print(f"❌ Error with Whisper: {e}")
        return False

def test_song_discovery():
    """Test song file discovery"""
    print(f"\n🧪 Testing Song Discovery...")
    print(f"Songs directory: {SONGS_DIR}")
    
    if not SONGS_DIR.exists():
        print(f"❌ Songs directory not found: {SONGS_DIR}")
        return None
    
    # Look for audio files
    audio_extensions = ["*.mp3", "*.wav", "*.m4a", "*.flac"]
    audio_files = []
    
    for ext in audio_extensions:
        audio_files.extend(SONGS_DIR.glob(ext))
    
    if not audio_files:
        print(f"❌ No audio files found in {SONGS_DIR}")
        return None
    
    latest_song = max(audio_files, key=lambda x: x.stat().st_mtime)
    file_size = latest_song.stat().st_size / (1024*1024)  # MB
    
    print(f"✅ Found {len(audio_files)} audio files")
    print(f"📄 Latest song: {latest_song.name} ({file_size:.1f} MB)")
    
    return latest_song

def test_whisper_transcription():
    """Test actual transcription with a small audio sample"""
    print(f"\n🧪 Testing Whisper Transcription...")
    
    # Test import first
    if not test_whisper_import():
        return False
    
    # Find song file
    song_path = test_song_discovery()
    if not song_path:
        return False
    
    try:
        import whisper
        
        print(f"🎤 Transcribing: {song_path.name}")
        print("   (Using tiny model for speed - real script uses large model)")
        
        # Load tiny model for testing
        model = whisper.load_model("tiny")
        
        # Transcribe with word timestamps
        result = model.transcribe(str(song_path), word_timestamps=True, language="hi")
        
        # Extract basic info
        full_text = result.get('text', '')
        segments = result.get('segments', [])
        
        print(f"✅ Transcription completed!")
        print(f"📝 Full text: {full_text[:100]}...")
        print(f"📊 Segments: {len(segments)}")
        
        # Extract word-level data
        word_count = 0
        if segments:
            for segment in segments:
                if 'words' in segment:
                    word_count += len(segment['words'])
        
        print(f"🔤 Words with timestamps: {word_count}")
        
        if word_count > 0:
            print("✅ Word-level timestamps available - karaoke subtitles possible!")
            return True
        else:
            print("⚠️ No word-level timestamps - basic subtitles only")
            return False
            
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print(" 🎤 WHISPER TRANSCRIPTION TEST 🎤 ".center(60, "="))
    print("="*60)
    
    success = test_whisper_transcription()
    
    print("\n" + "="*60)
    if success:
        print(" ✅ TEST PASSED - READY FOR KARAOKE! ✅ ".center(60, "="))
        print("="*60)
        print("🎉 Whisper transcription working correctly!")
        print("🎤 Karaoke subtitles will be available in main script.")
    else:
        print(" ❌ TEST FAILED - SUBTITLES DISABLED ❌ ".center(60, "="))
        print("="*60)
        print("⚠️ Install whisper: pip install openai-whisper")
        print("📝 Main script will run without subtitles.")
    
    print("\nPress Enter to exit...")
    input()