#!/usr/bin/env python3
"""
Step 2.5: Flip Videos (if needed)
- Checks videos from 2-convert/ for rotation issues
- Flips videos that are upside down (180°)
- Outputs to 2-5-flip/ directory
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

class Step2_5FlipVideos:
    def __init__(self, source_dir: Path, output_dir: Path, verbose: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.verbose = verbose
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir.parent / f"step2_5_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, message: str):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def run_ffmpeg(self, cmd: List[str], timeout: int = 3600) -> Tuple[int, str]:
        """Run ffmpeg command with timeout"""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
    
    def get_video_info(self, video_path: Path) -> dict:
        """Get video metadata using ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            self.log(f"Error getting video info for {video_path}: {e}")
        
        return {}
    
    def is_video_flipped(self, video_path: Path) -> bool:
        """Detect if video appears to be flipped (180°)"""
        info = self.get_video_info(video_path)
        try:
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    rotation = stream.get('tags', {}).get('rotate', '0')
                    if rotation in ['180', '-180']:
                        return True
                    
                    side_data = stream.get('side_data_list', [])
                    for data in side_data:
                        if data.get('side_data_type') == 'Display Matrix':
                            rotation_val = data.get('rotation', 0)
                            if abs(rotation_val - 180) < 10 or abs(rotation_val + 180) < 10:
                                return True
        except Exception:
            pass
        
        return False
    
    def flip_video(self, input_file: Path, output_file: Path) -> bool:
        """Flip video 180 degrees"""
        self.log(f"Flipping video: {input_file.name}")
        
        cmd = [
            "ffmpeg", "-hide_banner", "-y", "-i", str(input_file),
            "-vf", "rotate=PI", "-c:a", "copy", str(output_file)
        ]
        
        code, error = self.run_ffmpeg(cmd, timeout=1800)
        
        if code == 0 and output_file.exists():
            self.log(f"✓ Flipped: {output_file.name}")
            return True
        else:
            self.log(f"✗ Flip failed: {error}")
            return False
    
    def find_videos(self) -> List[Path]:
        """Find all MP4 files in source directory"""
        videos = []
        for video_file in self.source_dir.rglob('*.mp4'):
            if video_file.is_file():
                videos.append(video_file)
        return sorted(videos)
    
    def run(self):
        """Run Step 2.5: Flip Videos"""
        self.log("="*80)
        self.log("STEP 2.5: Flip Videos (if needed)")
        self.log("="*80)
        self.log(f"Source directory: {self.source_dir}")
        self.log(f"Output directory: {self.output_dir}")
        
        videos = self.find_videos()
        self.log(f"Found {len(videos)} video files to check")
        
        if not videos:
            self.log("No video files found")
            return
        
        flipped = 0
        copied = 0
        failed = 0
        
        for i, video in enumerate(videos, 1):
            self.log(f"\nChecking {i}/{len(videos)}: {video.name}")
            
            output_file = self.output_dir / video.name
            
            if output_file.exists():
                self.log(f"Already processed: {output_file.name}")
                continue
            
            if self.is_video_flipped(video):
                if self.flip_video(video, output_file):
                    flipped += 1
                else:
                    failed += 1
            else:
                # Not flipped, just copy
                shutil.copy2(video, output_file)
                self.log(f"No rotation needed: {video.name}")
                copied += 1
        
        self.log(f"\n{'='*80}")
        self.log(f"STEP 2.5 Complete: {flipped} flipped, {copied} copied, {failed} failed")
        self.log(f"Output in: {self.output_dir}")
        self.log(f"Log file: {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="Step 2.5: Flip Videos (if needed)")
    parser.add_argument("source_dir", nargs='?', default="2-convert", help="Source directory (default: 2-convert)")
    parser.add_argument("--output", "-o", default="2-5-flip", help="Output directory (default: 2-5-flip)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    
    args = parser.parse_args()
    
    # Resolve paths relative to .converter directory (parent of Video-Converter)
    converter_dir = Path(__file__).parent.parent.resolve()
    
    source_dir = (converter_dir / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    output_dir = (converter_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    step2_5 = Step2_5FlipVideos(source_dir, output_dir, args.verbose)
    step2_5.run()

if __name__ == "__main__":
    main()

