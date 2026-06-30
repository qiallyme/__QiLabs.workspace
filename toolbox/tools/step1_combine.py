#!/usr/bin/env python3
"""
Step 1: Group and Concatenate Videos
- Finds all video files
- Groups by folder and date/time (max 1 hour per group)
- Concatenates MKV files first
- Combines all videos in each group
- Outputs to 2-combine/ directory
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Add parent directories to path so we can import scripts module
SCRIPT_DIR = Path(__file__).parent.resolve()  # 04_scripts/steps/
SCRIPTS_DIR = SCRIPT_DIR.parent.resolve()  # 04_scripts/
CONVERTER_DIR = SCRIPTS_DIR.parent.resolve()  # .converter/
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.ffmpeg_utils import find_ffmpeg, check_ffmpeg

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg', '.media'}

class Step1GroupAndConcat:
    def __init__(self, source_dir: Path, output_dir: Path, trash_dir: Path = None, verbose: bool = False, dry_run: bool = False, 
                 max_duration_per_batch: Optional[int] = 3600, combine_all_in_one: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.trash_dir = Path(trash_dir).resolve() if trash_dir else None
        self.verbose = verbose
        self.dry_run = dry_run
        self.max_duration_per_batch = max_duration_per_batch  # None = unlimited, int = seconds
        self.combine_all_in_one = combine_all_in_one  # If True, combine all videos in folder into one video
        
        # Find ffmpeg executables
        self.ffmpeg_path, self.ffprobe_path = find_ffmpeg()
        if not self.ffmpeg_path or not self.ffprobe_path:
            check_ffmpeg()  # Print error message
            sys.exit(1)
        
        # Create output directory
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if self.trash_dir:
                self.trash_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file
        self.log_file = self.output_dir.parent / f"step1_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, message: str):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def move_to_trash(self, files: List[Path], relative_path: Path = None):
        """Move files to trash directory, preserving relative path structure"""
        if not self.trash_dir or self.dry_run:
            if self.dry_run:
                for f in files:
                    trash_path = self.trash_dir / f.relative_to(self.source_dir) if self.trash_dir and relative_path else self.trash_dir / f.name
                    self.log(f"[DRY RUN] Would move {f.name} -> {trash_path}")
            return
        
        for file_path in files:
            try:
                # Preserve relative path structure
                if relative_path:
                    # Calculate relative path from source_dir
                    rel_path = file_path.relative_to(self.source_dir)
                    trash_path = self.trash_dir / rel_path
                else:
                    trash_path = self.trash_dir / file_path.name
                
                # Create parent directories in trash
                trash_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(file_path), str(trash_path))
                self.log(f"Moved to trash: {file_path.name} -> {trash_path}")
            except Exception as e:
                self.log(f"Error moving {file_path.name} to trash: {e}")
    
    def run_ffmpeg(self, cmd: List[str], timeout: int = 3600) -> Tuple[int, str]:
        """Run ffmpeg command with timeout"""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
    
    def get_video_info(self, video_path: Path) -> Dict:
        """Get video metadata using ffprobe"""
        cmd = [
            self.ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            self.log(f"Error getting video info for {video_path}: {e}")
        
        return {}
    
    def get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds"""
        info = self.get_video_info(video_path)
        try:
            return float(info['format']['duration'])
        except (KeyError, ValueError):
            return 0.0
    
    def get_video_datetime(self, video_path: Path) -> Optional[datetime]:
        """Extract date/time from video metadata"""
        info = self.get_video_info(video_path)
        
        try:
            creation_time = info.get('format', {}).get('tags', {}).get('creation_time')
            if creation_time:
                dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                return dt.replace(tzinfo=None)
        except:
            pass
        
        try:
            mtime = os.path.getmtime(video_path)
            return datetime.fromtimestamp(mtime)
        except:
            pass
        
        return None
    
    def find_all_videos(self) -> List[Path]:
        """Find all video files in source directory"""
        videos = []
        for ext in VIDEO_EXTENSIONS:
            for video_file in self.source_dir.rglob(f'*{ext}'):
                if video_file.is_file():
                    videos.append(video_file)
        return sorted(videos)
    
    def get_folder_group_key(self, video_path: Path) -> Tuple[str, str]:
        """Get folder group key and identifier for naming"""
        rel_path = video_path.relative_to(self.source_dir)
        parts = rel_path.parts
        
        skip_folders = {'Photos from 2022', 'Photos from 2023', 'Photos from 2024', 
                       'Photos from 2025', 'Review', 'Sort', 'bdl', '_metadata'}
        
        identifier = "video"
        meaningful_parts = []
        
        for part in parts[:-1]:
            if part not in skip_folders and not part.startswith('.'):
                if not identifier or identifier == "video":
                    identifier = re.sub(r'[^\w\-]', '_', part).lower()
                meaningful_parts.append(part)
        
        if identifier == "video" and len(parts) > 1:
            parent = parts[-2]
            if parent not in skip_folders:
                identifier = re.sub(r'[^\w\-]', '_', parent).lower()
                meaningful_parts = [parent]
        
        if meaningful_parts:
            group_key = '/'.join(meaningful_parts)
        else:
            group_key = "root"
        
        return group_key, identifier
    
    def concatenate_mkv_files(self, mkv_files: List[Path], output_path: Path) -> bool:
        """Concatenate MKV files using mkvmerge or ffmpeg"""
        if not mkv_files:
            return False
        
        if len(mkv_files) == 1:
            shutil.copy2(mkv_files[0], output_path)
            return True
        
        self.log(f"Concatenating {len(mkv_files)} MKV files")
        
        # Try mkvmerge first
        try:
            cmd = ["mkvmerge", "-o", str(output_path)]
            for mkv_file in mkv_files:
                cmd.append(str(mkv_file.as_posix()))
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0 and output_path.exists():
                self.log(f"✓ MKV concatenated using mkvmerge: {output_path.name}")
                return True
        except FileNotFoundError:
            self.log("mkvmerge not found, using ffmpeg fallback")
        except Exception as e:
            self.log(f"mkvmerge failed: {e}, trying ffmpeg")
        
        # Fallback to ffmpeg concat
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                for mkv_file in mkv_files:
                    path = str(mkv_file.as_posix()).replace("'", "'\\''")
                    f.write(f"file '{path}'\n")
                concat_file = f.name
            
            cmd = [
                self.ffmpeg_path, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", str(output_path)
            ]
            
            code, error = self.run_ffmpeg(cmd, timeout=600)
            
            os.unlink(concat_file)
            
            if code == 0 and output_path.exists():
                self.log(f"✓ MKV concatenated using ffmpeg: {output_path.name}")
                return True
        except Exception as e:
            self.log(f"FFmpeg concat error: {e}")
        
        return False
    
    def combine_videos(self, video_files: List[Path], output_file: Path) -> bool:
        """Combine multiple video files into one"""
        if not video_files:
            return False
        
        if len(video_files) == 1:
            shutil.copy2(video_files[0], output_file)
            return True
        
        self.log(f"Combining {len(video_files)} videos")
        
        video_files = sorted(video_files, key=lambda x: x.name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            for video_file in video_files:
                path = str(video_file.as_posix()).replace("'", "'\\''")
                f.write(f"file '{path}'\n")
            concat_file = f.name
        
        try:
            cmd = [
                self.ffmpeg_path, "-hide_banner", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", str(output_file)
            ]
            
            code, error = self.run_ffmpeg(cmd, timeout=3600)
            
            if code == 0 and output_file.exists():
                self.log(f"✓ Combined {len(video_files)} videos -> {output_file.name}")
                return True
            else:
                self.log(f"✗ Combine failed: {error}")
                return False
        finally:
            os.unlink(concat_file)
    
    def group_videos_by_date_time(self, videos: List[Path]) -> Dict[str, List[Path]]:
        """Group videos by date and hour slot (max duration per group, or unlimited if max_duration_per_batch is None)"""
        video_data = []
        for video in videos:
            dt = self.get_video_datetime(video)
            if not dt:
                try:
                    dt = datetime.fromtimestamp(video.stat().st_mtime)
                except:
                    self.log(f"Warning: Could not get date/time for {video.name}, skipping")
                    continue
            
            duration = self.get_video_duration(video)
            video_data.append({
                'video': video,
                'datetime': dt,
                'duration': duration
            })
        
        video_data.sort(key=lambda x: x['datetime'])
        
        groups = {}
        
        for data in video_data:
            dt = data['datetime']
            date_str = dt.strftime('%Y-%m-%d')
            hour = dt.hour
            base_group_key = f"{date_str}_{hour:02d}"
            
            group_key = None
            # If max_duration is None, combine all videos in same date/hour into one group
            if self.max_duration_per_batch is None:
                # Find existing group for this date/hour
                for existing_key in groups.keys():
                    if existing_key.startswith(base_group_key):
                        group_key = existing_key
                        break
            else:
                # Find existing group that has room for this video
                for existing_key in groups.keys():
                    if existing_key.startswith(base_group_key):
                        total_duration = sum(self.get_video_duration(v) for v in groups[existing_key])
                        if total_duration + data['duration'] <= self.max_duration_per_batch:
                            group_key = existing_key
                            break
            
            if group_key:
                groups[group_key].append(data['video'])
            else:
                group_key = base_group_key
                counter = 1
                while group_key in groups:
                    group_key = f"{base_group_key}_{counter:02d}"
                    counter += 1
                
                groups[group_key] = [data['video']]
        
        return groups
    
    def process_group(self, group_key: str, videos: List[Path], identifier: str) -> Optional[Path]:
        """Process a group: concatenate MKV, then combine all"""
        if not videos:
            return None
        
        self.log(f"\n{'='*80}")
        self.log(f"Processing group: {group_key} ({len(videos)} videos)")
        self.log(f"{'='*80}")
        
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', group_key)
        if not date_match:
            self.log(f"Invalid date format in group key: {group_key}")
            return None
        
        date_str = date_match.group(1)
        output_filename = f"{identifier}_{date_str}_{group_key.split('_')[-1]}.mkv"
        output_path = self.output_dir / output_filename
        
        if output_path.exists():
            self.log(f"Output already exists: {output_filename}")
            return output_path
        
        # Separate MKV files from others
        mkv_files = [v for v in videos if v.suffix.lower() == '.mkv']
        other_files = [v for v in videos if v.suffix.lower() != '.mkv']
        
        # Concatenate MKV files first
        temp_files = []
        if mkv_files:
            temp_mkv = self.output_dir / f"temp_mkv_{group_key.replace('-', '_')}.mkv"
            if self.concatenate_mkv_files(mkv_files, temp_mkv):
                temp_files.append(temp_mkv)
                other_files.append(temp_mkv)
        
        # Combine all files
        if not other_files:
            self.log("No files to combine")
            return None
        
        if not self.combine_videos(other_files, output_path):
            # Clean up temp files
            for tf in temp_files:
                if tf.exists():
                    tf.unlink()
            return None
        
        # Clean up temp files
        for tf in temp_files:
            if tf.exists():
                tf.unlink()
        
        self.log(f"✓ Successfully grouped and concatenated: {output_filename}")
        return output_path
    
    def run(self):
        """Run Step 1: Group and Concatenate"""
        self.log("="*80)
        self.log("STEP 1: Group and Concatenate Videos")
        self.log("="*80)
        self.log(f"Source directory: {self.source_dir}")
        self.log(f"Output directory: {self.output_dir}")
        
        all_videos = self.find_all_videos()
        self.log(f"Found {len(all_videos)} video files")
        
        if not all_videos:
            self.log("No video files found")
            return
        
        videos_by_folder = defaultdict(list)
        folder_identifiers = {}
        
        for video in all_videos:
            group_key, identifier = self.get_folder_group_key(video)
            videos_by_folder[group_key].append(video)
            folder_identifiers[group_key] = identifier
        
        total_processed = 0
        for group_key, videos in videos_by_folder.items():
            identifier = folder_identifiers[group_key]
            self.log(f"\n{'#'*80}")
            self.log(f"Processing folder: {group_key} (identifier: {identifier}, {len(videos)} videos)")
            self.log(f"{'#'*80}")
            
            if self.combine_all_in_one:
                # Combine all videos in this folder into one video
                self.log(f"Mode: Combining all {len(videos)} videos into one file")
                group_key_all = f"{identifier}_all_combined"
                result = self.process_group(group_key_all, videos, identifier)
                if result:
                    total_processed += 1
                    # Move original files to trash
                    self.move_to_trash(videos, relative_path=True)
            else:
                # Group by date/time (with optional duration limit)
                if self.max_duration_per_batch is None:
                    self.log(f"Mode: Unlimited duration per batch (combining all videos in same date/hour)")
                else:
                    self.log(f"Mode: Max {self.max_duration_per_batch} seconds per batch")
                
                time_groups = self.group_videos_by_date_time(videos)
                
                for time_group_key, group_videos in time_groups.items():
                    result = self.process_group(time_group_key, group_videos, identifier)
                    if result:
                        total_processed += 1
                        # Move original files to trash
                        self.move_to_trash(group_videos, relative_path=True)
        
        self.log(f"\n{'='*80}")
        self.log(f"STEP 1 Complete: {total_processed} groups processed")
        self.log(f"Output in: {self.output_dir}")
        self.log(f"Log file: {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="Step 1: Group and Concatenate Videos")
    parser.add_argument("source_dir", nargs='?', default="1-combine", help="Source directory (default: 1-combine)")
    parser.add_argument("--output", "-o", default="done/1-combine", help="Output directory (default: done/1-combine)")
    parser.add_argument("--trash", "-t", default="trash/1-combine", help="Trash directory for originals (default: trash/1-combine)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--max-duration", type=int, default=3600, help="Max duration per batch in seconds (default: 3600 = 1 hour). Use 0 for unlimited.")
    parser.add_argument("--combine-all", action="store_true", help="Combine all videos in each folder into one video (ignores time grouping and duration limits)")
    
    args = parser.parse_args()
    
    # Resolve paths relative to .converter directory (parent of Video-Converter)
    converter_dir = Path(__file__).parent.parent.resolve()
    
    source_dir = (converter_dir / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    output_dir = (converter_dir / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    trash_dir = (converter_dir / args.trash).resolve() if args.trash and not Path(args.trash).is_absolute() else (Path(args.trash).resolve() if args.trash else None)
    
    # Handle max_duration: 0 means unlimited (None), otherwise use the value
    max_duration = None if args.max_duration == 0 else args.max_duration
    
    step1 = Step1GroupAndConcat(source_dir, output_dir, trash_dir, args.verbose, args.dry_run, 
                                max_duration_per_batch=max_duration, combine_all_in_one=args.combine_all)
    step1.run()

if __name__ == "__main__":
    main()

