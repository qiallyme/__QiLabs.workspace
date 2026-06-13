#!/usr/bin/env python3
"""
Batch Processor - Process videos through all steps in batches
- Processes folders in batches from 1-combine/
- Runs Step 1 → Step 2 → Step 2.5 → Step 3 sequentially
- Moves all originals to trash after each step
- Cleans up intermediate folders after each batch
- Final result: Only final files in 3-enhance/, everything else in trash/
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()
CONVERTER_DIR = SCRIPT_DIR.parent.resolve()

def get_folder_size(folder: Path) -> int:
    """Calculate total size of a folder in bytes"""
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
    return total

def find_folders_with_videos(source_dir: Path, processed_folders: Set[str] = None) -> List[Tuple[Path, float]]:
    """Find folders containing videos, sorted by size"""
    if processed_folders is None:
        processed_folders = set()
    
    folders_with_size = []
    
    # Check root directory
    video_files = list(source_dir.glob('*.mp4')) + list(source_dir.glob('*.mkv')) + \
                  list(source_dir.glob('*.avi')) + list(source_dir.glob('*.mov')) + \
                  list(source_dir.glob('*.media'))
    if video_files:
        size = sum(f.stat().st_size for f in video_files if f.is_file())
        folders_with_size.append((source_dir, size / (1024**3)))  # GB
    
    # Check subdirectories
    for subdir in source_dir.iterdir():
        if subdir.is_dir() and subdir.name not in processed_folders:
            video_files = list(subdir.rglob('*.mp4')) + list(subdir.rglob('*.mkv')) + \
                         list(subdir.rglob('*.avi')) + list(subdir.rglob('*.mov')) + \
                         list(subdir.rglob('*.media'))
            if video_files:
                size = get_folder_size(subdir)
                folders_with_size.append((subdir, size / (1024**3)))  # GB
    
    # Sort by size (smallest first for faster batches)
    return sorted(folders_with_size, key=lambda x: x[1])

def run_step_script(script_name: str, args: List[str], verbose: bool = False) -> Tuple[bool, str]:
    """Run a step script and return (success, output)"""
    script_path = SCRIPT_DIR / script_name
    
    if not script_path.exists():
        return False, f"Script not found: {script_name}"
    
    cmd = [sys.executable, str(script_path)] + args
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if verbose:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        return result.returncode == 0, result.stderr if result.returncode != 0 else ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def cleanup_intermediate_folders(converter_dir: Path, keep_final: bool = True):
    """Clean up intermediate folders, keeping only final output"""
    intermediate_dirs = [
        "2-combine",
        "2-convert", 
        "2-5-flip"
    ]
    
    cleaned = []
    for dir_name in intermediate_dirs:
        dir_path = converter_dir / dir_name
        if dir_path.exists():
            try:
                # Check if empty
                if not any(dir_path.rglob('*')):
                    dir_path.rmdir()
                    cleaned.append(dir_name)
                else:
                    # Move remaining files to trash
                    trash_dir = converter_dir / "trash" / dir_name
                    trash_dir.mkdir(parents=True, exist_ok=True)
                    for item in dir_path.rglob('*'):
                        if item.is_file():
                            rel_path = item.relative_to(dir_path)
                            trash_path = trash_dir / rel_path
                            trash_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(item), str(trash_path))
                    # Remove empty dir
                    if not any(dir_path.rglob('*')):
                        dir_path.rmdir()
                        cleaned.append(dir_name)
            except Exception as e:
                print(f"Warning: Could not clean {dir_name}: {e}")
    
    return cleaned

def process_batch(source_dir: Path, batch_folders: List[Path], batch_num: int, 
                  parallel: int = 1, verbose: bool = False) -> bool:
    """Process a batch of folders through all steps"""
    print(f"\n{'='*80}")
    print(f"BATCH {batch_num}: Processing {len(batch_folders)} folder(s)")
    for folder in batch_folders:
        rel_path = folder.relative_to(source_dir) if folder != source_dir else Path("root")
        print(f"  - {rel_path}")
    print(f"{'='*80}")
    
    # Step 1: Group and Concatenate (processes entire source directory)
    print("\n[Step 1] Grouping and concatenating...")
    step1_args = [
        str(source_dir),
        "--output", "2-combine",
        "--trash", "trash/1-combine",
        "--parallel", str(parallel)
    ]
    if verbose:
        step1_args.append("--verbose")
    
    success, error = run_step_script("step1_group_and_concat.py", step1_args, verbose)
    if not success:
        print(f"Step 1 failed: {error}")
        return False
    print("  Step 1 done")
    
    # Step 2: Convert to MP4
    print("\n[Step 2] Converting to MP4...")
    step2_args = [
        "2-combine",
        "--output", "2-convert",
        "--trash", "trash/2-convert",
        "--parallel", str(parallel)
    ]
    if verbose:
        step2_args.append("--verbose")
    
    success, error = run_step_script("step2_convert_to_mp4.py", step2_args, verbose)
    if not success:
        print(f"Step 2 failed: {error}")
        return False
    print("  Step 2 done")
    
    # Step 2.5: Auto-rotate
    print("\n[Step 2.5] Auto-detecting and correcting rotation...")
    step2_5_args = [
        "2-convert",
        "--output", "2-5-flip",
        "--parallel", str(parallel)
    ]
    if verbose:
        step2_5_args.append("--verbose")
    
    success, error = run_step_script("step2_5_flip_videos.py", step2_5_args, verbose)
    if not success:
        print(f"Step 2.5 failed: {error}")
        return False
    print("  Step 2.5 done")
    
    # Step 3: Complete Enhancement
    print("\n[Step 3] Enhancing and optimizing...")
    step3_args = [
        "2-5-flip",
        "--output", "3-enhance",
        "--trash", "trash/3-enhance",
        "--parallel", str(min(parallel, 2))  # Step 3 is more intensive
    ]
    if verbose:
        step3_args.append("--verbose")
    
    success, error = run_step_script("step3_enhance.py", step3_args, verbose)
    if not success:
        print(f"Step 3 failed: {error}")
        return False
    print("  Step 3 done")
    
    # Clean up intermediate folders
    print("\n[Cleanup] Removing intermediate files...")
    cleaned = cleanup_intermediate_folders(CONVERTER_DIR)
    if cleaned:
        print(f"  Cleaned intermediate folders: {', '.join(cleaned)}")
    
    # Verify source folders are empty (or only have trash)
    print("\n[Verification] Checking source folders...")
    empty_folders = []
    for folder in batch_folders:
        if folder == source_dir:
            continue
        # Check if folder is empty (all files should be in trash)
        remaining_files = list(folder.rglob('*'))
        video_files = [f for f in remaining_files if f.is_file() and f.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.media']]
        if not video_files:
            empty_folders.append(folder.name)
            print(f"  {folder.name} is empty (all files processed)")
        else:
            print(f"  Warning: {folder.name} still has {len(video_files)} video file(s)")
    
    print(f"\nBatch {batch_num} done!")
    print(f"  Final files: {CONVERTER_DIR / '3-enhance'}")
    print(f"  Trash: {CONVERTER_DIR / 'trash'}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Batch Processor - Process videos through all steps")
    parser.add_argument("source_dir", nargs='?', default="1-combine", help="Source directory (default: 1-combine)")
    parser.add_argument("--batch-size", type=float, default=5.0, help="Max batch size in GB (default: 5.0)")
    parser.add_argument("--parallel", type=int, default=1, help="Parallel workers per step (default: 1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--auto-continue", action="store_true", help="Auto-continue to next batch without prompting")
    
    args = parser.parse_args()
    
    source_dir = (CONVERTER_DIR / args.source_dir).resolve() if not Path(args.source_dir).is_absolute() else Path(args.source_dir).resolve()
    
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    print("="*80)
    print("BATCH PROCESSOR - Complete Workflow")
    print("="*80)
    print(f"Source: {source_dir}")
    print(f"Batch size: {args.batch_size} GB")
    print(f"Parallel workers: {args.parallel}")
    print(f"Workflow: Step 1 -> Step 2 -> Step 2.5 -> Step 3")
    print(f"Final output: 3-enhance/")
    print(f"Trash: trash/")
    print("="*80)
    
    processed_folders = set()
    batch_num = 0
    total_processed = 0
    total_failed = 0
    
    while True:
        # Find folders for next batch
        folders_with_size = find_folders_with_videos(source_dir, processed_folders)
        
        if not folders_with_size:
            print("\n" + "="*80)
            print("ALL BATCHES COMPLETE!")
            print("="*80)
            print(f"Total processed: {total_processed}")
            print(f"Total failed: {total_failed}")
            print(f"\nFinal videos: {CONVERTER_DIR / '3-enhance'}")
            print(f"Trash: {CONVERTER_DIR / 'trash'}")
            break
        
        # Build batch up to size limit
        batch_folders = []
        current_size = 0.0
        
        for folder, size in folders_with_size:
            if current_size + size <= args.batch_size:
                batch_folders.append(folder)
                current_size += size
            else:
                break
        
        if not batch_folders:
            # Take at least one folder even if it exceeds limit
            batch_folders = [folders_with_size[0][0]]
        
        batch_num += 1
        print(f"\n{'#'*80}")
        print(f"BATCH {batch_num}: {len(batch_folders)} folder(s), {current_size:.2f} GB")
        print(f"{'#'*80}")
        
        # Process entire batch through all steps
        success = process_batch(source_dir, batch_folders, batch_num, args.parallel, args.verbose)
        if success:
            total_processed += len(batch_folders)
            for folder in batch_folders:
                processed_folders.add(folder.name if folder != source_dir else "root")
        else:
            total_failed += len(batch_folders)
            print(f"\nBatch {batch_num} failed")
        
        # Ask to continue (unless auto-continue)
        if not args.auto_continue:
            print(f"\n{'='*80}")
            print(f"Batch {batch_num} complete! Processed: {total_processed}, Failed: {total_failed}")
            print(f"{'='*80}")
            continue_choice = input("\nContinue with next batch? (y/n): ").strip().lower()
            if continue_choice != 'y':
                print("Stopping. You can restart later to continue.")
                break

if __name__ == "__main__":
    main()

