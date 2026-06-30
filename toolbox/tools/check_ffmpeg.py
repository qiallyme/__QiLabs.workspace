#!/usr/bin/env python3
"""
Quick check to see if ffmpeg is properly installed and accessible.
Run this before using the video converter.
"""

import sys
from pathlib import Path

# Add parent directories to path so we can import core module
SCRIPT_DIR = Path(__file__).parent.resolve()  # 04_scripts/core/
SCRIPTS_DIR = SCRIPT_DIR.parent.resolve()  # 04_scripts/
CONVERTER_DIR = SCRIPTS_DIR.parent.resolve()  # .converter/
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.ffmpeg_utils import check_ffmpeg

if __name__ == "__main__":
    print("\nChecking FFmpeg installation...\n")
    
    if check_ffmpeg():
        print("\n✓ All good! FFmpeg is installed and ready to use.")
        print("\nYou can now run the orchestrator to process videos.")
    else:
        print("\n✗ FFmpeg is not installed or not accessible.")
        print("\nPlease follow the instructions above to install FFmpeg.")
        print("Once installed, run this script again to verify.")
    
    input("\nPress Enter to exit...")

