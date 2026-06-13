#!/usr/bin/env python3
"""
Step 3.5: AI Content Filter (Optional)
- Analyzes videos from 3-enhance/ for human content
- Filters out videos without human content (faces, bodies, movement)
- Outputs filtered videos to 3-5-filtered/ directory
- Moves filtered-out videos to 3-5-rejected/ directory
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

try:
    from ai_video_filter import AIVideoFilter
    AI_FILTER_AVAILABLE = True
except ImportError:
    AI_FILTER_AVAILABLE = False
    print("Warning: AI video filter not available. Install dependencies: pip install opencv-python mediapipe")

class Step3_5AIFilter:
    def __init__(self, source_dir: Path, output_dir: Path, rejected_dir: Path,
                 confidence: float = 0.4, sample_count: int = 5, verbose: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.rejected_dir = Path(rejected_dir).resolve()
        self.confidence = confidence
        self.sample_count = sample_count
        self.verbose = verbose
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir.parent / f"step3_5_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        if not AI_FILTER_AVAILABLE:
            raise ImportError("AI filter dependencies not available. Install: pip install opencv-python mediapipe")
        
        self.ai_filter = AIVideoFilter(confidence_threshold=confidence, sample_count=sample_count)
        
    def log(self, message: str):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def find_videos(self) -> List[Path]:
        """Find all MP4 files in source directory"""
        videos = []
        for video_file in self.source_dir.rglob('*.mp4'):
            if video_file.is_file():
                videos.append(video_file)
        return sorted(videos)
    
    def run(self):
        """Run Step 3.5: AI Content Filter"""
        self.log("="*80)
        self.log("STEP 3.5: AI Content Filter")
        self.log("="*80)
        self.log(f"Source directory: {self.source_dir}")
        self.log(f"Output directory (accepted): {self.output_dir}")
        self.log(f"Rejected directory: {self.rejected_dir}")
        self.log(f"Confidence threshold: {self.confidence}")
        self.log(f"Sample frames per video: {self.sample_count}")
        
        videos = self.find_videos()
        self.log(f"Found {len(videos)} video files to analyze")
        
        if not videos:
            self.log("No video files found")
            return
        
        accepted = 0
        rejected = 0
        failed = 0
        
        for i, video in enumerate(videos, 1):
            self.log(f"\nAnalyzing {i}/{len(videos)}: {video.name}")
            
            output_file = self.output_dir / video.name
            rejected_file = self.rejected_dir / video.name
            
            if output_file.exists() or rejected_file.exists():
                self.log(f"Already processed: {video.name}")
                continue
            
            try:
                has_content, details = self.ai_filter.analyze_video(video)
                
                detection_methods = [k for k, v in details.items() if v and k != 'frames_analyzed']
                
                if has_content:
                    shutil.copy2(video, output_file)
                    self.log(f"✓ ACCEPTED: {video.name} - Detected: {detection_methods}")
                    accepted += 1
                else:
                    shutil.copy2(video, rejected_file)
                    self.log(f"✗ REJECTED: {video.name} - No human content detected")
                    rejected += 1
                    
            except Exception as e:
                self.log(f"✗ ERROR analyzing {video.name}: {e}")
                failed += 1
        
        self.log(f"\n{'='*80}")
        self.log(f"STEP 3.5 Complete: {accepted} accepted, {rejected} rejected, {failed} failed")
        self.log(f"Accepted videos in: {self.output_dir}")
        self.log(f"Rejected videos in: {self.rejected_dir}")
        self.log(f"Log file: {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="Step 3.5: AI Content Filter (Optional)")
    parser.add_argument("source_dir", nargs='?', default="3-enhance", help="Source directory (default: 3-enhance)")
    parser.add_argument("--output", "-o", default="3-5-filtered", help="Output directory for accepted videos (default: 3-5-filtered)")
    parser.add_argument("--rejected", "-r", default="3-5-rejected", help="Directory for rejected videos (default: 3-5-rejected)")
    parser.add_argument("--confidence", type=float, default=0.4, help="Detection confidence threshold (default: 0.4)")
    parser.add_argument("--samples", type=int, default=5, help="Number of frames to sample per video (default: 5)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    
    args = parser.parse_args()
    
    if not AI_FILTER_AVAILABLE:
        print("Error: AI filter dependencies not available.")
        print("Install with: pip install opencv-python mediapipe")
        sys.exit(1)
    
    # Resolve paths relative to .converter directory (parent of Video-Converter)
    converter_dir = Path(__file__).parent.parent.resolve()
    
    source_dir = (converter_dir / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    output_dir = (converter_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    rejected_dir = (converter_dir / args.rejected).resolve() if not Path(args.rejected).is_absolute() else Path(args.rejected).resolve()
    
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        rejected_dir.mkdir(parents=True, exist_ok=True)
    
    step3_5 = Step3_5AIFilter(source_dir, output_dir, rejected_dir, args.confidence, args.samples, args.verbose)
    step3_5.run()

if __name__ == "__main__":
    main()

