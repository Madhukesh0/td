"""
Download and setup FFmpeg for Windows
"""
import os
import zipfile
import urllib.request
import shutil
from pathlib import Path

def download_ffmpeg():
    """Download FFmpeg essentials build for Windows"""
    print("Downloading FFmpeg...")
    
    # Create ffmpeg directory
    ffmpeg_dir = Path(__file__).parent / "ffmpeg"
    ffmpeg_dir.mkdir(exist_ok=True)
    
    # Download URL for FFmpeg essentials build
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = ffmpeg_dir / "ffmpeg.zip"
    
    try:
        # Download with progress
        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(downloaded * 100 / total_size, 100)
            print(f"\rDownloading: {percent:.1f}%", end="")
        
        urllib.request.urlretrieve(url, zip_path, reporthook)
        print("\n✅ Download complete!")
        
        # Extract
        print("Extracting FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        
        # Find the bin directory
        for item in ffmpeg_dir.iterdir():
            if item.is_dir() and item.name.startswith("ffmpeg-"):
                bin_dir = item / "bin"
                if bin_dir.exists():
                    # Copy executables to ffmpeg root
                    for exe in bin_dir.glob("*.exe"):
                        shutil.copy(exe, ffmpeg_dir)
                    print(f"✅ FFmpeg extracted to: {ffmpeg_dir}")
                    break
        
        # Clean up
        zip_path.unlink()
        
        # Remove extracted folder
        for item in ffmpeg_dir.iterdir():
            if item.is_dir() and item.name.startswith("ffmpeg-"):
                shutil.rmtree(item)
        
        print(f"\n✅ FFmpeg setup complete!")
        print(f"FFmpeg location: {ffmpeg_dir / 'ffmpeg.exe'}")
        
        return str(ffmpeg_dir / "ffmpeg.exe")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    ffmpeg_path = download_ffmpeg()
    if ffmpeg_path:
        print(f"\n🎉 You can now convert videos!")
        print(f"FFmpeg is ready at: {ffmpeg_path}")
