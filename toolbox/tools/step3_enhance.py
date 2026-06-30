#!/usr/bin/env python3
"""
Step 3: Enhance Video Quality
- Takes videos from 2-5-flip/ (or 2-convert/ if step 2.5 skipped)
- Applies brightness, contrast, sharpness improvements
- Cleans up audio (removes inaudible frequencies, normalizes)
- Outputs final videos to 3-enhance/ directory
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

class Step3Enhance:
    def __init__(self, source_dir: Path, output_dir: Path, trash_dir: Path = None, gpu_enabled: bool = True,
                 threads: int = 4, verbose: bool = False, dry_run: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.trash_dir = Path(trash_dir).resolve() if trash_dir else None
        self.gpu_enabled = gpu_enabled
        self.threads = threads
        self.verbose = verbose
        self.dry_run = dry_run
        
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if self.trash_dir:
                self.trash_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir.parent / f"step3_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, message: str):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def run_ffmpeg(self, cmd: List[str], timeout: int = 7200) -> Tuple[int, str]:
        """Run ffmpeg command with timeout"""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
    
    def get_gpu_encoder(self) -> str:
        """Detect available GPU encoder"""
        if not self.gpu_enabled:
            return "libx264"
        
        test_cmd = ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1", 
                   "-c:v", "h264_nvenc", "-f", "null", "-"]
        
        try:
            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                return "h264_nvenc"
        except:
            pass
        
        test_cmd[6] = "h264_qsv"
        try:
            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                return "h264_qsv"
        except:
            pass
        
        test_cmd[6] = "h264_amf"
        try:
            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                return "h264_amf"
        except:
            pass
        
        return "libx264"
    
    def enhance_video_quality(self, input_file: Path, output_file: Path) -> bool:
        """Enhance video quality: brightness, contrast, sharpness, audio cleanup"""
        if self.dry_run:
            self.log(f"[DRY RUN] Would enhance {input_file.name} -> {output_file.name}")
            self.log(f"  - Brightness: +10%, Contrast: +15%")
            self.log(f"  - Sharpness: moderate increase")
            self.log(f"  - Audio: normalize, remove inaudible frequencies")
            self.log(f"  - Scale: max 1920x1080")
            return True
        
        self.log(f"Enhancing video quality: {input_file.name}")
        
        encoder = self.get_gpu_encoder()
        
        # Build video filters
        vf_filters = []
        vf_filters.append("eq=brightness=0.1:contrast=1.15")  # Increase brightness by 10%, contrast by 15%
        vf_filters.append("unsharp=5:5:1.2:5:5:0.0")  # Moderate sharpening
        vf_filters.append("scale=iw*min(1920/iw\\,1080/ih):ih*min(1920/iw\\,1080/ih)")  # Scale to max 1920x1080
        
        # Build audio filters
        af_filters = []
        af_filters.append("highpass=f=20")  # Remove subsonic
        af_filters.append("lowpass=f=20000")  # Remove ultrasonic
        af_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")  # Normalize audio
        
        cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(input_file)]
        
        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])
        
        if af_filters:
            cmd.extend(["-af", ",".join(af_filters)])
        
        if encoder != "libx264":
            cmd.extend(["-c:v", encoder, "-preset", "medium", "-crf", "18"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-threads", str(self.threads)])
        
        cmd.extend(["-c:a", "aac", "-b:a", "192k", str(output_file)])
        
        code, error = self.run_ffmpeg(cmd, timeout=7200)
        
        if code == 0 and output_file.exists():
            self.log(f"✓ Enhanced: {output_file.name}")
            return True
        else:
            self.log(f"✗ Enhancement failed: {error}")
            return False
    
    def move_to_trash(self, file_path: Path):
        """Move file to trash directory, preserving relative path structure"""
        if not self.trash_dir or self.dry_run:
            if self.dry_run:
                rel_path = file_path.relative_to(self.source_dir)
                trash_path = self.trash_dir / rel_path
                self.log(f"[DRY RUN] Would move {file_path.name} -> {trash_path}")
            return
        
        import shutil
        try:
            rel_path = file_path.relative_to(self.source_dir)
            trash_path = self.trash_dir / rel_path
            trash_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(trash_path))
            self.log(f"Moved to trash: {file_path.name}")
        except Exception as e:
            self.log(f"Error moving {file_path.name} to trash: {e}")
    
    def find_videos(self) -> List[Path]:
        """Find all MP4 files in source directory"""
        videos = []
        for video_file in self.source_dir.rglob('*.mp4'):
            if video_file.is_file():
                videos.append(video_file)
        return sorted(videos)
    
    def run(self):
        """Run Step 3: Enhance Video Quality"""
        self.log("="*80)
        if self.dry_run:
            self.log("STEP 3: Enhance Video Quality [DRY RUN MODE]")
        else:
            self.log("STEP 3: Enhance Video Quality")
        self.log("="*80)
        self.log(f"Source directory: {self.source_dir}")
        self.log(f"Output directory: {self.output_dir}")
        self.log(f"GPU enabled: {self.gpu_enabled}")
        self.log(f"Threads: {self.threads}")
        
        videos = self.find_videos()
        self.log(f"Found {len(videos)} video files to enhance")
        
        if not videos:
            self.log("No video files found")
            return
        
        enhanced = 0
        failed = 0
        
        for i, video in enumerate(videos, 1):
            self.log(f"\nProcessing {i}/{len(videos)}: {video.name}")
            
            output_file = self.output_dir / video.name
            
            if output_file.exists():
                self.log(f"Already enhanced: {output_file.name}")
                enhanced += 1
                continue
            
            if self.enhance_video_quality(video, output_file):
                enhanced += 1
                # Move original to trash
                self.move_to_trash(video)
            else:
                failed += 1
        
        self.log(f"\n{'='*80}")
        self.log(f"STEP 3 Complete: {enhanced} enhanced, {failed} failed")
        self.log(f"Final videos in: {self.output_dir}")
        self.log(f"Log file: {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="Step 3: Enhance Video Quality")
    parser.add_argument("source_dir", nargs='?', default=None, help="Source directory (default: auto-detect done/2.5-flip or done/2-convert)")
    parser.add_argument("--output", "-o", default="done/3-enhance", help="Output directory (default: done/3-enhance)")
    parser.add_argument("--trash", "-t", default="trash/3-enhance", help="Trash directory for originals (default: trash/3-enhance)")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads (default: 4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    
    args = parser.parse_args()
    
    # Resolve paths relative to .converter directory (parent of Video-Converter)
    converter_dir = Path(__file__).parent.parent.resolve()
    
    # Auto-detect source directory if not provided
    if args.source_dir is None:
        # Check for step 2.5 output first, then step 2 output
        step2_5_output = converter_dir / "done/2.5-flip"
        step2_output = converter_dir / "done/2-convert"
        
        if step2_5_output.exists() and any(step2_5_output.rglob('*')):
            source_dir = step2_5_output
            print(f"Auto-detected source: {source_dir} (from Step 2.5)")
        elif step2_output.exists() and any(step2_output.rglob('*')):
            source_dir = step2_output
            print(f"Auto-detected source: {source_dir} (from Step 2)")
        else:
            source_dir = step2_5_output  # Default to step 2.5 output
            print(f"Using default source: {source_dir}")
    else:
        source_dir = (converter_dir / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    output_dir = (converter_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    trash_dir = (converter_dir / args.trash).resolve() if args.trash and not Path(args.trash).is_absolute() else (Path(args.trash).resolve() if args.trash else None)
    
    step3 = Step3Enhance(source_dir, output_dir, trash_dir, not args.no_gpu, args.threads, args.verbose, args.dry_run)
    step3.run()

if __name__ == "__main__":
    main()

