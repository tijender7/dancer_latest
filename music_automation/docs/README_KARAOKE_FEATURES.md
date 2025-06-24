# 🎤 Karaoke Features Documentation

## New Karaoke Subtitle System

The music video compiler now includes **automatic karaoke-style subtitles** with Hinglish support!

## 🎯 Features Added

### ✅ **Whisper Integration**
- **Automatic transcription** using OpenAI Whisper large model
- **Word-level timestamps** for precise synchronization
- **Hinglish support** (Hindi written in English characters)
- **High accuracy** for Indian language content

### ✅ **Karaoke-Style Subtitles**
- **Line-by-line highlighting** synchronized with audio
- **Progressive highlighting** effect (normal → highlighted)
- **Professional styling** with stroke/outline for visibility
- **Bottom-positioned** subtitles that don't obstruct video

### ✅ **Smart Text Processing**
- **Automatic line breaking** (8 words per line by default)
- **Timing synchronization** with music beats
- **Error handling** for transcription failures
- **Graceful fallback** if Whisper unavailable

## 📊 How It Works

### **Step 1: Audio Transcription**
```
🎵 Song: "ओम नमः शिवाय.mp3" → Whisper Large Model → Word timestamps
```

### **Step 2: Subtitle Line Creation**
```
Words: [om, namah, shivaye, om, namah, shivaye...]
↓
Lines: ["om namah shivaye om namah", "shivaye om namah shivaye..."]
```

### **Step 3: Karaoke Effect**
```
Line 1 (0-5s):  Normal text (white) → Highlighted text (yellow)
Line 2 (5-10s): Normal text (white) → Highlighted text (yellow)
```

## 🎨 Visual Styling

### **Text Properties**:
- **Font**: Arial-Bold
- **Size**: 48px
- **Normal Color**: White
- **Highlight Color**: Yellow
- **Stroke**: Black outline (2px width)
- **Position**: Bottom center with 50px margin

### **Timing Effects**:
- **Highlight Delay**: 10% into each line
- **Highlight Duration**: 80% of line duration
- **Smooth Transitions**: Between normal and highlighted states

## 📁 Output Files

### **With Karaoke Subtitles**:
```
equal_time_compilation_[song_name]_with_karaoke_[timestamp].mp4
```

### **Without Subtitles** (if Whisper unavailable):
```
equal_time_compilation_[song_name]_[timestamp].mp4
```

## ⚙️ Configuration Options

Located in the script's configuration section:

```python
# Subtitle Configuration
ENABLE_SUBTITLES = True and WHISPER_AVAILABLE
WHISPER_MODEL_SIZE = "large"  # tiny, base, small, medium, large
SUBTITLE_FONTSIZE = 48
SUBTITLE_COLOR_NORMAL = "white"
SUBTITLE_COLOR_HIGHLIGHT = "yellow"
WORDS_PER_LINE = 8
```

## 🚀 Installation & Usage

### **Install Whisper**:
```bash
pip install openai-whisper
```

### **Run with Karaoke**:
```bash
python music_video_beat_sync_compiler.py
```

### **Test Whisper Setup**:
```bash
python test_whisper_transcription.py
```

## 📈 Performance Notes

### **Model Sizes**:
- **tiny**: Fastest, lower accuracy
- **base**: Balanced speed/accuracy
- **small**: Good accuracy, reasonable speed
- **medium**: High accuracy, slower
- **large**: Best accuracy, slowest (recommended)

### **Processing Time**:
- **Transcription**: ~30-60 seconds for 3-minute song
- **Subtitle Creation**: ~10-20 seconds
- **Total Added Time**: ~1-2 minutes per video

## 🛠️ Troubleshooting

### **Common Issues**:

1. **Whisper Import Error**:
   ```
   ⚠️ Whisper not available. Install with: pip install openai-whisper
   ```

2. **Font Not Found**:
   - Script falls back to default system font
   - Install Arial or modify `SUBTITLE_FONT` setting

3. **Low Transcription Accuracy**:
   - Try `WHISPER_MODEL_SIZE = "large"` for better accuracy
   - Ensure clean audio without background noise

4. **Subtitle Positioning Issues**:
   - Adjust `SUBTITLE_MARGIN_BOTTOM` for vertical position
   - Modify `SUBTITLE_FONTSIZE` for readability

## 🎯 Example Output

For the song "ओम नमः शिवाय":

```
0-3s:   "om namah shivaye om"     [white → yellow highlighting]
3-6s:   "namah shivaye mantra"    [white → yellow highlighting]  
6-9s:   "hindu devotional song"   [white → yellow highlighting]
```

## 🔧 Customization

### **Change Colors**:
```python
SUBTITLE_COLOR_NORMAL = "lightblue"
SUBTITLE_COLOR_HIGHLIGHT = "gold"
```

### **Adjust Timing**:
```python
WORDS_PER_LINE = 6  # Shorter lines
SUBTITLE_FONTSIZE = 56  # Larger text
```

### **Different Model**:
```python
WHISPER_MODEL_SIZE = "medium"  # Faster processing
```

---

**🎉 Result**: Professional karaoke-style music videos with synchronized Hinglish subtitles!

*Perfect for Instagram, YouTube, and social media content with Indian music.*