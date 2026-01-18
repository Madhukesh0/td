# 🎬 Video Conversion Guide

## Problem Solved

Telegram videos use **Opus audio codec** (usually in WebM or MKV containers) which many Windows media players don't support properly. This causes:

- ❌ No sound when playing videos
- ❌ "Encrypted codec" or "Unsupported format" errors
- ❌ Audio codec warnings

## ✅ Solution

The app now **automatically converts** downloaded videos to **MP4 format with AAC audio**, which is:

- ✅ Compatible with Windows Media Player
- ✅ Works with VLC, Chrome, Edge, and all modern players
- ✅ Maintains video quality (only audio is re-encoded)
- ✅ Optimized for fast playback

## 🚀 How to Use

### 1. **Automatic Conversion (Recommended)**

The conversion is **enabled by default**:

1. Open the Streamlit app: http://localhost:8501
2. In the sidebar, you'll see "🎬 Video Settings"
3. "Auto-convert videos to MP4" checkbox is **checked** by default
4. Download any video - it will automatically convert!

### 2. **Manual Conversion (if needed)**

If you already have videos with audio issues:

```powershell
# Convert a single video
python -c "from src.app import convert_video_to_mp4; convert_video_to_mp4('path/to/video.webm')"
```

### 3. **Batch Convert Existing Files**

```powershell
# Convert all WebM files in downloads folder
Get-ChildItem downloads -Recurse -Filter "*.webm" | ForEach-Object {
    python -c "from src.app import convert_video_to_mp4; convert_video_to_mp4('$($_.FullName)')"
}
```

## ⚙️ Technical Details

### What FFmpeg Does:

- **Video Stream**: Copies directly (no quality loss, very fast)
- **Audio Stream**: Converts Opus → AAC at 192kbps
- **Container**: Changes WebM/MKV → MP4
- **Speed**: ~10-30 seconds per video (depends on length)

### Conversion Command:

```bash
ffmpeg -i input.webm -c:v copy -c:a aac -b:a 192k -movflags +faststart output.mp4
```

### Settings Explained:

- `-c:v copy`: Copy video codec (no re-encoding = fast!)
- `-c:a aac`: Convert audio to AAC (compatible with everything)
- `-b:a 192k`: High quality audio bitrate
- `-movflags +faststart`: Optimize for streaming/web playback

## 📊 Download Progress

When downloading with conversion enabled, you'll see:

1. **📄 Downloading...** - File is being downloaded
2. **🔄 Converting to MP4...** - Video is being converted
3. **✅ Completed** - Ready to play!

## 🎯 Benefits

### Before (Opus codec):

```
Video: H.264
Audio: Opus ❌
Format: WebM
Result: No sound in most players
```

### After (AAC codec):

```
Video: H.264 (same quality)
Audio: AAC ✅
Format: MP4
Result: Works everywhere!
```

## 🔧 Troubleshooting

### "FFmpeg not found" warning:

Run the setup script again:

```powershell
python setup_ffmpeg.py
```

### Conversion takes too long:

- Small videos (< 50MB): ~10 seconds
- Medium videos (50-200MB): ~30 seconds
- Large videos (> 200MB): ~1-2 minutes

### Want to disable conversion:

Uncheck "Auto-convert videos to MP4" in the sidebar

### Original file preservation:

By default, the original file is **deleted** after successful conversion to save space. The converted MP4 replaces it.

## 📝 Notes

- **Image files** (photos, GIFs) are not affected
- **Audio files** (voice messages, music) are not converted
- **Only videos** with incompatible codecs are converted
- **MP4 files** that are already compatible are skipped
- **Conversion is automatic** - no extra steps needed!

## 🎉 Result

Now all your downloaded videos will play perfectly with sound in:

- ✅ Windows Media Player
- ✅ VLC Media Player
- ✅ Web browsers (Chrome, Edge, Firefox)
- ✅ Mobile apps
- ✅ Video editing software

Enjoy your media! 🎬🔊
