#!/usr/bin/env python3
"""
Step 2: Convert Videos to MP4
- Takes videos from 2-combine/
- Converts all formats to MP4
- Outputs to 2-convert/ directory
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg', '.media'}

class Step2ConvertToMP4:
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
        self.log_file = self.output_dir.parent / f"step2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
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
    
    def convert_to_mp4(self, input_file: Path, output_file: Path) -> bool:
        """Convert any video format to MP4"""
        if self.dry_run:
            if input_file.suffix.lower() == '.mp4':
                self.log(f"[DRY RUN] Would copy {input_file.name} -> {output_file.name} (already MP4)")
            else:
                encoder = self.get_gpu_encoder()
                self.log(f"[DRY RUN] Would convert {input_file.name} ({input_file.suffix}) -> {output_file.name} using {encoder}")
            return True
        
        if input_file.suffix.lower() == '.mp4':
            # Already MP4, just copy
            import shutil
            shutil.copy2(input_file, output_file)
            return True
        
        encoder = self.get_gpu_encoder()
        self.log(f"Converting {input_file.name} to MP4 using {encoder}")
        
        cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(input_file)]
        
        if encoder != "libx264":
            cmd.extend(["-c:v", encoder, "-preset", "medium", "-crf", "20"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-threads", str(self.threads)])
        
        cmd.extend(["-c:a", "aac", "-b:a", "128k", str(output_file)])
        
        code, error = self.run_ffmpeg(cmd, timeout=1800)
        
        if code == 0 and output_file.exists():
            self.log(f"✓ Converted: {input_file.name} -> {output_file.name}")
            return True
        else:
            self.log(f"✗ Conversion failed: {error}")
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
        """Find all video files in source directory"""
        videos = []
        for ext in VIDEO_EXTENSIONS:
            for video_file in self.source_dir.rglob(f'*{ext}'):
                if video_file.is_file():
                    videos.append(video_file)
        return sorted(videos)
    
    def run(self):
        """Run Step 2: Convert to MP4"""
        self.log("="*80)
        if self.dry_run:
            self.log("STEP 2: Convert Videos to MP4 [DRY RUN MODE]")
        else:
            self.log("STEP 2: Convert Videos to MP4")
        self.log("="*80)
        self.log(f"Source directory: {self.source_dir}")
        self.log(f"Output directory: {self.output_dir}")
        self.log(f"GPU enabled: {self.gpu_enabled}")
        self.log(f"Threads: {self.threads}")
        
        videos = self.find_videos()
        self.log(f"Found {len(videos)} video files to convert")
        
        if not videos:
            self.log("No video files found")
            return
        
        converted = 0
        failed = 0
        
        for i, video in enumerate(videos, 1):
            self.log(f"\nProcessing {i}/{len(videos)}: {video.name}")
            
            # Output filename: keep same name but change extension to .mp4
            output_file = self.output_dir / f"{video.stem}.mp4"
            
            if output_file.exists():
                self.log(f"Already exists: {output_file.name}")
                converted += 1
                continue
            
            if self.convert_to_mp4(video, output_file):
                converted += 1
                # Move original to trash
                self.move_to_trash(video)
            else:
                failed += 1
        
        self.log(f"\n{'='*80}")
        self.log(f"STEP 2 Complete: {converted} converted, {failed} failed")
        self.log(f"Output in: {self.output_dir}")
        self.log(f"Log file: {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="Step 2: Convert Videos to MP4")
    parser.add_argument("source_dir", nargs='?', default=None, help="Source directory (default: auto-detect done/1-combine or done/1.5-fast-combine)")
    parser.add_argument("--output", "-o", default="done/2-convert", help="Output directory (default: done/2-convert)")
    parser.add_argument("--trash", "-t", default="trash/2-convert", help="Trash directory for originals (default: trash/2-convert)")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads (default: 4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    
    args = parser.parse_args()
    
    # Resolve paths relative to .converter directory (parent of Video-Converter)
    converter_dir = Path(__file__).parent.parent.resolve()
    
    # Auto-detect source directory if not provided
    if args.source_dir is None:
        # Check for step 1.5 output first (faster path), then step 1 output
        step1_5_output = converter_dir / "done/1.5-fast-combine"
        step1_output = converter_dir / "done/1-combine"
        
        if step1_5_output.exists() and any(step1_5_output.rglob('*')):
            source_dir = step1_5_output
            print(f"Auto-detected source: {source_dir} (from Step 1.5)")
        elif step1_output.exists() and any(step1_output.rglob('*')):
            source_dir = step1_output
            print(f"Auto-detected source: {source_dir} (from Step 1)")
        else:
            source_dir = step1_output  # Default to step 1 output
            print(f"Using default source: {source_dir}")
    else:
        source_dir = (converter_dir / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    output_dir = (converter_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    trash_dir = (converter_dir / args.trash).resolve() if args.trash and not Path(args.trash).is_absolute() else (Path(args.trash).resolve() if args.trash else None)
    
    step2 = Step2ConvertToMP4(source_dir, output_dir, trash_dir, not args.no_gpu, args.threads, args.verbose, args.dry_run)
    step2.run()

if __name__ == "__main__":
    main()

