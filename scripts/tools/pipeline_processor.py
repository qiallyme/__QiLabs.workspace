#!/usr/bin/env python3
"""
Pipeline Processor - Assembly Line Processing
- Processes groups through all steps in parallel (like an assembly line)
- As soon as a group finishes one step, it moves to the next step
- Multiple groups can be at different stages simultaneously
- Final result: Only final files in 3-enhance/, everything else in trash/
"""

import argparse
import json
import shutil
import subprocess
import sys
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from queue import Queue

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()
CONVERTER_DIR = SCRIPT_DIR.parent.resolve()

class PipelineGroup:
    """Represents a group of videos moving through the pipeline"""
    def __init__(self, group_id: str, source_path: Path):
        self.group_id = group_id
        self.source_path = source_path
        self.stage = 0  # 0=combine, 1=convert, 2=flip, 3=enhance, 4=done
        self.output_paths = {
            0: None,  # 2-combine
            1: None,  # 2-convert
            2: None,  # 2-5-flip
            3: None   # 3-enhance
        }
        self.status = "pending"
        self.error = None

def get_folder_size(folder: Path) -> float:
    """Calculate total size of a folder in GB"""
    total = 0
    try:
        for item in folder.rglob('*'):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    return total / (1024**3)  # GB

def find_video_groups(source_dir: Path) -> List[Tuple[str, Path, float]]:
    """Find all folders/groups with videos"""
    groups = []
    
    # Check root for videos
    root_videos = list(source_dir.glob('*.mp4')) + list(source_dir.glob('*.mkv')) + \
                  list(source_dir.glob('*.avi')) + list(source_dir.glob('*.mov')) + \
                  list(source_dir.glob('*.media'))
    if root_videos:
        size = sum(f.stat().st_size for f in root_videos if f.is_file()) / (1024**3)
        groups.append(("root", source_dir, size))
    
    # Check subdirectories
    for subdir in source_dir.iterdir():
        if subdir.is_dir():
            videos = list(subdir.rglob('*.mp4')) + list(subdir.rglob('*.mkv')) + \
                    list(subdir.rglob('*.avi')) + list(subdir.rglob('*.mov')) + \
                    list(subdir.rglob('*.media'))
            if videos:
                size = get_folder_size(subdir)
                groups.append((subdir.name, subdir, size))
    
    return sorted(groups, key=lambda x: x[2])  # Sort by size (smallest first)

def run_step_script(script_name: str, args: List[str], timeout: int = 7200) -> Tuple[bool, str]:
    """Run a step script and return (success, error)"""
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        return False, f"Script not found: {script_name}"
    
    cmd = [sys.executable, str(script_path)] + args
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stderr if result.returncode != 0 else ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def step1_combine(group: PipelineGroup, parallel: int, verbose: bool) -> bool:
    """Step 1: Group and Concatenate - process this group's folder"""
    group.status = "combining"
    
    # Process this specific folder/group
    output_dir = CONVERTER_DIR / "2-combine" / group.group_id
    output_dir.mkdir(parents=True, exist_ok=True)
    trash_dir = CONVERTER_DIR / "trash" / "1-combine" / group.group_id
    trash_dir.mkdir(parents=True, exist_ok=True)
    
    args = [
        str(group.source_path),
        "--output", str(output_dir),
        "--trash", str(trash_dir),
        "--parallel", str(parallel)
    ]
    if verbose:
        args.append("--verbose")
    
    success, error = run_step_script("step1_group_and_concat.py", args)
    
    if success:
        group.output_paths[0] = output_dir
        group.stage = 1
        group.status = "ready_for_convert"
        return True
    else:
        group.error = f"Step 1 failed: {error}"
        group.status = "failed"
        return False

def step2_convert(group: PipelineGroup, parallel: int, verbose: bool) -> bool:
    """Step 2: Convert to MP4"""
    group.status = "converting"
    
    if not group.output_paths[0] or not group.output_paths[0].exists():
        group.error = "Step 1 output not found"
        group.status = "failed"
        return False
    
    output_dir = CONVERTER_DIR / "2-convert" / group.group_id
    output_dir.mkdir(parents=True, exist_ok=True)
    trash_dir = CONVERTER_DIR / "trash" / "2-convert" / group.group_id
    trash_dir.mkdir(parents=True, exist_ok=True)
    
    args = [
        str(group.output_paths[0]),
        "--output", str(output_dir),
        "--trash", str(trash_dir),
        "--parallel", str(parallel)
    ]
    if verbose:
        args.append("--verbose")
    
    success, error = run_step_script("step2_convert_to_mp4.py", args)
    
    if success:
        group.output_paths[1] = output_dir
        group.stage = 2
        group.status = "ready_for_flip"
        return True
    else:
        group.error = f"Step 2 failed: {error}"
        group.status = "failed"
        return False

def step2_5_flip(group: PipelineGroup, parallel: int, verbose: bool) -> bool:
    """Step 2.5: Auto-rotate"""
    group.status = "rotating"
    
    if not group.output_paths[1] or not group.output_paths[1].exists():
        group.error = "Step 2 output not found"
        group.status = "failed"
        return False
    
    output_dir = CONVERTER_DIR / "2-5-flip" / group.group_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    args = [
        str(group.output_paths[1]),
        "--output", str(output_dir),
        "--parallel", str(parallel)
    ]
    if verbose:
        args.append("--verbose")
    
    success, error = run_step_script("step2_5_flip_videos.py", args)
    
    if success:
        group.output_paths[2] = output_dir
        group.stage = 3
        group.status = "ready_for_enhance"
        return True
    else:
        group.error = f"Step 2.5 failed: {error}"
        group.status = "failed"
        return False

def step3_enhance(group: PipelineGroup, parallel: int, verbose: bool) -> bool:
    """Step 3: Complete Enhancement"""
    group.status = "enhancing"
    
    if not group.output_paths[2] or not group.output_paths[2].exists():
        group.error = "Step 2.5 output not found"
        group.status = "failed"
        return False
    
    output_dir = CONVERTER_DIR / "3-enhance" / group.group_id
    output_dir.mkdir(parents=True, exist_ok=True)
    trash_dir = CONVERTER_DIR / "trash" / "3-enhance" / group.group_id
    trash_dir.mkdir(parents=True, exist_ok=True)
    
    args = [
        str(group.output_paths[2]),
        "--output", str(output_dir),
        "--trash", str(trash_dir),
        "--parallel", str(min(parallel, 2))  # Step 3 is more intensive
    ]
    if verbose:
        args.append("--verbose")
    
    success, error = run_step_script("step3_enhance.py", args)
    
    if success:
        group.output_paths[3] = output_dir
        group.stage = 4
        group.status = "done"
        
        # Clean up intermediate outputs (they're already in trash from step scripts)
        # Move original source folder to trash if it's a subdirectory
        if group.source_path.exists() and group.source_path != CONVERTER_DIR / "1-combine":
            trash_source = CONVERTER_DIR / "trash" / "1-combine" / group.group_id
            trash_source.mkdir(parents=True, exist_ok=True)
            try:
                # Check if folder is empty (all files should be in trash already)
                remaining_videos = list(group.source_path.rglob('*.mp4')) + \
                                  list(group.source_path.rglob('*.mkv')) + \
                                  list(group.source_path.rglob('*.avi')) + \
                                  list(group.source_path.rglob('*.mov')) + \
                                  list(group.source_path.rglob('*.media'))
                if not remaining_videos:
                    # Folder is empty, can remove it
                    try:
                        shutil.rmtree(group.source_path, ignore_errors=True)
                    except:
                        pass
            except:
                pass
        
        return True
    else:
        group.error = f"Step 3 failed: {error}"
        group.status = "failed"
        return False

def process_group_pipeline(group: PipelineGroup, parallel: int, verbose: bool, 
                            stage_queues: Dict[int, Queue], log_file: Path, lock: threading.Lock):
    """Process a single group through the pipeline stages (assembly line)"""
    def log(msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{group.group_id}] {msg}"
        with lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
            if verbose:
                print(log_msg)
    
    try:
        # Stage 0: Combine
        log(f"Step 1: Combining...")
        stage_queues[0].get()  # Wait for slot in stage 0
        try:
            success = step1_combine(group, parallel, verbose)
            if not success:
                log(f"Failed: {group.error}")
                return
            log(f"Step 1 done, moving to Step 2")
        finally:
            stage_queues[0].put(None)  # Release slot
        
        # Stage 1: Convert (happens while next group is combining)
        log(f"Step 2: Converting...")
        stage_queues[1].get()  # Wait for slot in stage 1
        try:
            success = step2_convert(group, parallel, verbose)
            if not success:
                log(f"Failed: {group.error}")
                return
            log(f"Step 2 done, moving to Step 2.5")
        finally:
            stage_queues[1].put(None)  # Release slot
        
        # Stage 2: Flip (happens while previous group is converting, next is combining)
        log(f"Step 2.5: Rotating...")
        stage_queues[2].get()  # Wait for slot in stage 2
        try:
            success = step2_5_flip(group, parallel, verbose)
            if not success:
                log(f"Failed: {group.error}")
                return
            log(f"Step 2.5 done, moving to Step 3")
        finally:
            stage_queues[2].put(None)  # Release slot
        
        # Stage 3: Enhance (final step)
        log(f"Step 3: Enhancing...")
        stage_queues[3].get()  # Wait for slot in stage 3
        try:
            success = step3_enhance(group, parallel, verbose)
            if not success:
                log(f"Failed: {group.error}")
                return
            log(f"GROUP COMPLETE! Final files in 3-enhance/{group.group_id}/")
        finally:
            stage_queues[3].put(None)  # Release slot
            
    except Exception as e:
        log(f"Exception: {e}")
        group.status = "failed"
        group.error = str(e)


def main():
    parser = argparse.ArgumentParser(description="Pipeline Processor - Assembly Line Processing")
    parser.add_argument("source_dir", nargs='?', default="1-combine", help="Source directory (default: 1-combine)")
    parser.add_argument("--parallel", type=int, default=2, help="Parallel workers per stage (default: 2)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    source_dir = (CONVERTER_DIR / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    print("="*80)
    print("PIPELINE PROCESSOR - Assembly Line Processing")
    print("="*80)
    print(f"Source: {source_dir}")
    print(f"Parallel workers per stage: {args.parallel}")
    print(f"Pipeline: Combine -> Convert -> Rotate -> Enhance")
    print(f"Final output: 3-enhance/")
    print(f"Trash: trash/")
    print("="*80)
    
    # Find all groups
    groups_data = find_video_groups(source_dir)
    print(f"\nFound {len(groups_data)} group(s) to process")
    
    if not groups_data:
        print("No video groups found")
        return
    
    # Create pipeline groups
    groups = []
    for group_id, folder_path, size in groups_data:
        group = PipelineGroup(group_id, folder_path)
        groups.append(group)
        print(f"  - {group_id}: {size:.2f} GB")
    
    # Create log file
    log_file = CONVERTER_DIR / f"pipeline_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Create stage queues (limit concurrency per stage) - assembly line slots
    stage_queues = {}
    for stage in range(4):
        queue = Queue(maxsize=args.parallel)
        # Pre-fill with available slots
        for _ in range(args.parallel):
            queue.put(None)
        stage_queues[stage] = queue
    
    # Create lock for logging
    log_lock = threading.Lock()
    
    # Create output directories
    for dir_name in ["2-combine", "2-convert", "2-5-flip", "3-enhance", "trash"]:
        (CONVERTER_DIR / dir_name).mkdir(exist_ok=True)
    
    print(f"\n{'='*80}")
    print("Starting pipeline processing (assembly line)...")
    print(f"Groups will flow through: Combine -> Convert -> Rotate -> Enhance")
    print(f"Multiple groups can be at different stages simultaneously!")
    print(f"{'='*80}\n")
    
    # Process all groups through pipeline in parallel (assembly line)
    threads = []
    for group in groups:
        thread = threading.Thread(
            target=process_group_pipeline,
            args=(group, args.parallel, args.verbose, stage_queues, log_file, log_lock),
            daemon=False
        )
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Final summary
    print(f"\n{'='*80}")
    print("PIPELINE COMPLETE!")
    print(f"{'='*80}")
    
    done = sum(1 for g in groups if g.status == "done")
    failed = sum(1 for g in groups if g.status == "failed")
    
    print(f"Completed: {done}/{len(groups)}")
    print(f"Failed: {failed}/{len(groups)}")
    print(f"\nFinal videos: {CONVERTER_DIR / '3-enhance'}")
    print(f"Trash: {CONVERTER_DIR / 'trash'}")
    print(f"Log: {log_file}")
    
    # Final cleanup: remove empty intermediate folders
    print("\n[Final Cleanup] Removing empty intermediate folders...")
    for dir_name in ["2-combine", "2-convert", "2-5-flip"]:
        dir_path = CONVERTER_DIR / dir_name
        if dir_path.exists():
            try:
                # Check if empty
                if not any(dir_path.rglob('*')):
                    dir_path.rmdir()
                    print(f"  Removed empty: {dir_name}/")
            except:
                pass

if __name__ == "__main__":
    main()

