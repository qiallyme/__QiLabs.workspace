#!/usr/bin/env python3
"""
FFmpeg Utility - Find and validate ffmpeg/ffprobe installations
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

def find_ffmpeg() -> Tuple[Optional[str], Optional[str]]:
    """
    Find ffmpeg and ffprobe executables.
    Returns: (ffmpeg_path, ffprobe_path) or (None, None) if not found
    """
    # First, check if they're in PATH
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    
    if ffmpeg_path and ffprobe_path:
        return ffmpeg_path, ffprobe_path
    
    # Common Windows installation paths
    common_paths = [
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/Program Files (x86)/ffmpeg/bin"),
        Path.home() / "ffmpeg" / "bin",
        Path.home() / "Downloads" / "ffmpeg" / "bin",
    ]
    
    for path in common_paths:
        if path.exists():
            ffmpeg_exe = path / "ffmpeg.exe"
            ffprobe_exe = path / "ffprobe.exe"
            if ffmpeg_exe.exists() and ffprobe_exe.exists():
                return str(ffmpeg_exe), str(ffprobe_exe)
    
    # Check in current directory and parent directories
    script_dir = Path(__file__).parent
    for i in range(3):  # Check up to 3 levels up
        check_dir = script_dir / ("../" * i) / "ffmpeg" / "bin"
        check_dir = check_dir.resolve()
        if check_dir.exists():
            ffmpeg_exe = check_dir / "ffmpeg.exe"
            ffprobe_exe = check_dir / "ffprobe.exe"
            if ffmpeg_exe.exists() and ffprobe_exe.exists():
                return str(ffmpeg_exe), str(ffprobe_exe)
    
    return None, None

def check_ffmpeg() -> bool:
    """
    Check if ffmpeg is available and working.
    Returns True if available, False otherwise.
    Prints helpful error messages.
    """
    ffmpeg_path, ffprobe_path = find_ffmpeg()
    
    if not ffmpeg_path or not ffprobe_path:
        print("\n" + "="*80)
        print("ERROR: FFmpeg not found!")
        print("="*80)
        print("FFmpeg is required for video processing but was not found on your system.")
        print()
        print("SOLUTION:")
        print("1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/")
        print("   (Get the 'ffmpeg-release-essentials.zip')")
        print()
        print("2. Extract the ZIP file to: C:\\ffmpeg\\")
        print("   - You should have: C:\\ffmpeg\\bin\\ffmpeg.exe")
        print("   - And: C:\\ffmpeg\\bin\\ffprobe.exe")
        print()
        print("3. Add to PATH (optional but recommended):")
        print("   - Open 'Edit system environment variables'")
        print("   - Click 'Environment Variables'")
        print("   - Under 'System variables', find 'Path' and click 'Edit'")
        print("   - Click 'New' and add: C:\\ffmpeg\\bin")
        print("   - Click OK and restart your terminal")
        print()
        print("Alternative: Place ffmpeg in one of these locations:")
        for path in [
            "C:\\ffmpeg\\bin",
            "C:\\Program Files\\ffmpeg\\bin",
            str(Path.home() / "ffmpeg" / "bin")
        ]:
            print(f"  - {path}")
        print()
        print("="*80)
        return False
    
    # Test ffmpeg
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print(f"Warning: FFmpeg found at {ffmpeg_path} but failed version check")
            return False
    except Exception as e:
        print(f"Warning: FFmpeg found at {ffmpeg_path} but failed to run: {e}")
        return False
    
    print(f"✓ FFmpeg found: {ffmpeg_path}")
    print(f"✓ FFprobe found: {ffprobe_path}")
    return True

if __name__ == "__main__":
    # Test the utility
    if check_ffmpeg():
        print("\nFFmpeg is ready to use!")
    else:
        print("\nPlease install FFmpeg before continuing.")

