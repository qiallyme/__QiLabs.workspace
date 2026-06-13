#!/usr/bin/env python3
"""
Step 1.5: Fast Concatenation (Alternative to Step 1)
- Fast concatenation using ffmpeg concat with -c copy (no re-encoding)
- Groups files by type (.media, .mkv, .mp4, etc.) within each folder
- Uses natural sorting for correct file order
- Much faster than Step 1 as it skips conversion
- Outputs to 1-5-fast-concat/ directory
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg', '.media'}

NUM_RE = re.compile(r"(\d+)")

def nsort_key(p: Path):
    """Natural sort: split digits so 0000, 0012, 0024… order correctly"""
    parts = NUM_RE.split(p.stem)
    return [int(s) if s.isdigit() else s.lower() for s in parts] + [p.suffix.lower()]

class Step1_5FastConcat:
    def __init__(self, source_dir: Path, output_dir: Path, trash_dir: Path = None, parallel: int = 1, verbose: bool = False, dry_run: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.trash_dir = Path(trash_dir).resolve() if trash_dir else None
        self.parallel = parallel
        self.verbose = verbose
        self.dry_run = dry_run
        
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if self.trash_dir:
                self.trash_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir.parent / f"step1_5_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, message: str):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def run_ffmpeg(self, cmd: List[str], timeout: int = 600) -> Tuple[int, str]:
        """Run ffmpeg command with timeout"""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
    
    def get_file_types_in_dir(self, dir_path: Path) -> set:
        """Get all video file types in directory"""
        found_types = set()
        for ext in VIDEO_EXTENSIONS:
            for p in dir_path.glob(f"*{ext}"):
                if p.is_file() and p.suffix.lower() == ext.lower():
                    found_types.add(ext)
                    break
        return found_types
    
    def gather_files_by_type(self, dir_path: Path, file_ext: str) -> List[Path]:
        """Get all files of a specific type in directory, sorted naturally"""
        files = []
        for p in dir_path.glob(f"*{file_ext}"):
            if p.is_file() and p.suffix.lower() == file_ext.lower():
                files.append(p)
        return sorted(files, key=nsort_key)
    
    def has_video_files(self, dir_path: Path) -> bool:
        """Check if directory contains video files"""
        return len(self.get_file_types_in_dir(dir_path)) > 0
    
    def move_to_trash(self, files: List[Path], relative_path: bool = True):
        """Move files to trash directory, preserving relative path structure"""
        if not self.trash_dir or self.dry_run:
            if self.dry_run:
                for f in files:
                    if relative_path:
                        trash_path = self.trash_dir / f.relative_to(self.source_dir)
                    else:
                        trash_path = self.trash_dir / f.name
                    self.log(f"[DRY RUN] Would move {f.name} -> {trash_path}")
            return
        
        import shutil
        for file_path in files:
            try:
                if relative_path:
                    rel_path = file_path.relative_to(self.source_dir)
                    trash_path = self.trash_dir / rel_path
                else:
                    trash_path = self.trash_dir / file_path.name
                
                trash_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(trash_path))
                self.log(f"Moved to trash: {file_path.name}")
            except Exception as e:
                self.log(f"Error moving {file_path.name} to trash: {e}")
    
    def unique_name(self, base: str, root: Path, ext: str) -> Path:
        """Generate unique filename in root directory"""
        candidate = root / f"{base}{ext}"
        if not candidate.exists():
            return candidate
        i = 2
        while True:
            cand = root / f"{base}__{i}{ext}"
            if not cand.exists():
                return cand
            i += 1
    
    def process_folder_by_type(self, folder_path: Path, file_ext: str) -> Tuple[Path, str]:
        """Process a single folder for a specific file type"""
        chunks = self.gather_files_by_type(folder_path, file_ext)
        if len(chunks) == 0:
            return None, f"No {file_ext} files found"
        
        # Generate output filename based on folder name
        if folder_path == self.source_dir:
            rel = self.source_dir.name or "root"
        else:
            rel = folder_path.relative_to(self.source_dir).as_posix().replace("/", "_")
        
        rel = rel.lstrip("._")
        if not rel:
            rel = "output"
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = f"{rel}_{file_ext.replace('.', '')}__{timestamp}"
        out_file = self.unique_name(base, self.output_dir, file_ext)
        
        if self.dry_run:
            file_list = "\n    ".join([f"{i+1}. {f.name}" for i, f in enumerate(chunks[:10])])
            if len(chunks) > 10:
                file_list += f"\n    ... and {len(chunks) - 10} more files"
            self.log(f"[DRY RUN] Would process {folder_path.name}: {len(chunks)} {file_ext} files -> {out_file.name}")
            self.log(f"  Files to combine:\n    {file_list}")
            if len(chunks) == 1:
                return out_file, f"[DRY RUN] Would copy: {chunks[0].name}"
            return out_file, f"[DRY RUN] Would concatenate {len(chunks)} files"
        
        self.log(f"Processing {folder_path.name}: {len(chunks)} {file_ext} files -> {out_file.name}")
        
        if len(chunks) == 1:
            # Single file, just copy
            import shutil
            shutil.copy2(chunks[0], out_file)
            return out_file, f"Copied single file: {chunks[0].name}"
        
        # Create concat list
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            for p in chunks:
                path = str(p.as_posix()).replace("'", "'\\''")
                f.write(f"file '{path}'\n")
            concat_file = f.name
        
        try:
            # Fast concatenation using ffmpeg concat demuxer with -c copy (no re-encoding)
            cmd = [
                "ffmpeg", "-hide_banner", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",  # Copy streams without any processing (very fast!)
                "-fflags", "+genpts",  # Generate presentation timestamps
                str(out_file)
            ]
            
            code, error = self.run_ffmpeg(cmd, timeout=600)
            
            if code == 0 and out_file.exists():
                return out_file, f"Success: {len(chunks)} {file_ext} files merged"
            else:
                return None, f"Concatenation failed: {error}"
        finally:
            os.unlink(concat_file)
    
    def process_folder(self, folder_path: Path) -> List[Tuple[str, Path, str]]:
        """Process a folder containing multiple file types, grouping by type"""
        file_types = self.get_file_types_in_dir(folder_path)
        if not file_types:
            return []
        
        results = []
        for file_ext in sorted(file_types):
            result, message = self.process_folder_by_type(folder_path, file_ext)
            results.append((file_ext, result, message))
        
        return results
    
    def find_folders_with_videos(self) -> List[Path]:
        """Find all folders containing video files"""
        folders = []
        
        # Check root directory
        if self.has_video_files(self.source_dir):
            folders.append(self.source_dir)
        
        # Check subdirectories
        for sub in self.source_dir.rglob("*"):
            if sub.is_dir() and sub != self.source_dir and self.has_video_files(sub):
                folders.append(sub)
        
        return sorted(folders)
    
    def run(self):
        """Run Step 1.5: Fast Concatenation"""
        self.log("="*80)
        if self.dry_run:
            self.log("STEP 1.5: Fast Concatenation [DRY RUN MODE]")
        else:
            self.log("STEP 1.5: Fast Concatenation")
        self.log("="*80)
        self.log(f"Source directory: {self.source_dir}")
        self.log(f"Output directory: {self.output_dir}")
        self.log(f"Parallel workers: {self.parallel}")
        
        folders = self.find_folders_with_videos()
        self.log(f"Found {len(folders)} folders with video files")
        
        if not folders:
            self.log("No folders with video files found")
            return
        
        total_successful = 0
        total_failed = 0
        
        if self.parallel == 1:
            # Sequential processing
            for i, folder in enumerate(folders, 1):
                self.log(f"\n[{i}/{len(folders)}] Processing {folder.name}...")
                results = self.process_folder(folder)
                
                for file_ext, result, message in results:
                    if result:
                        total_successful += 1
                        self.log(f"  ✓ {file_ext}: {message}")
                        # Move original files to trash
                        chunks = self.gather_files_by_type(folder, file_ext)
                        if chunks:
                            self.move_to_trash(chunks, relative_path=True)
                    else:
                        total_failed += 1
                        self.log(f"  ✗ {file_ext}: {message}")
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                future_to_folder = {
                    executor.submit(self.process_folder, folder): folder
                    for folder in folders
                }
                
                completed = 0
                for future in as_completed(future_to_folder):
                    folder = future_to_folder[future]
                    completed += 1
                    try:
                        results = future.result()
                        for file_ext, result, message in results:
                            if result:
                                total_successful += 1
                                self.log(f"[{completed}/{len(folders)}] {folder.name} ({file_ext}): ✓ {message}")
                            else:
                                total_failed += 1
                                self.log(f"[{completed}/{len(folders)}] {folder.name} ({file_ext}): ✗ {message}")
                    except Exception as e:
                        total_failed += 1
                        self.log(f"[{completed}/{len(folders)}] {folder.name}: ERROR - {e}")
        
        self.log(f"\n{'='*80}")
        self.log(f"STEP 1.5 Complete: {total_successful} successful, {total_failed} failed")
        self.log(f"Output in: {self.output_dir}")
        self.log(f"Log file: {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="Step 1.5: Fast Concatenation (Alternative to Step 1)")
    parser.add_argument("source_dir", nargs='?', default="1.5-fast-combine", help="Source directory (default: 1.5-fast-combine)")
    parser.add_argument("--output", "-o", default="done/1.5-fast-combine", help="Output directory (default: done/1.5-fast-combine)")
    parser.add_argument("--trash", "-t", default="trash/1.5-fast-combine", help="Trash directory for originals (default: trash/1.5-fast-combine)")
    parser.add_argument("--parallel", type=int, default=1, help="Number of folders to process in parallel (default: 1)")
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
    trash_dir = (converter_dir / args.trash).resolve() if args.trash and not Path(args.trash).is_absolute() else (Path(args.trash).resolve() if args.trash else None)
    
    step1_5 = Step1_5FastConcat(source_dir, output_dir, trash_dir, args.parallel, args.verbose, args.dry_run)
    step1_5.run()

if __name__ == "__main__":
    main()

