#!/usr/bin/env python3
"""
Video Processing Orchestrator
Prompts user to select which step to run:
- Step 1: Group and Concatenate
- Step 2: Convert to MP4
- Step 2.5: Flip Videos (if needed)
- Step 3: Enhance Quality
- Step 3.5: AI Content Filter (Optional)
"""

import subprocess
import shutil
import sys
from pathlib import Path

# Add parent directory to path so we can import core module
SCRIPT_DIR = Path(__file__).parent.resolve()  # 04_scripts/
SCRIPTS_DIR = SCRIPT_DIR  # 04_scripts/
CONVERTER_DIR = SCRIPTS_DIR.parent.resolve()  # .converter/
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.ffmpeg_utils import check_ffmpeg

LOCAL_TEMP_DIR = Path("C:/Users/codyr/.videoconverter/temp")

def print_menu():
    """Print the main menu"""
    print("\n" + "="*80)
    print("VIDEO PROCESSING ORCHESTRATOR")
    print("="*80)
    print("\nSelect workflow type:")
    print()
    print("  [S] Standard Workflow - Use predefined pipeline steps")
    print("  [P] Project Workflow - Custom path and step configuration")
    print()
    print("  [0] Exit")
    print()
    print("="*80)

def print_standard_menu():
    """Print the standard workflow menu"""
    print("\n" + "="*80)
    print("STANDARD WORKFLOW")
    print("="*80)
    print("\nSelect a step to run:")
    print()
    print("  1. Step 1: Group and Concatenate Videos")
    print("     - Groups videos by folder and date/time (max 1 hour per batch)")
    print("     - Concatenates MKV files")
    print("     - Combines videos in each group")
    print("     - Input: workflow/input/")
    print("     - Output: workflow/stage1_combine/")
    print()
    print("  1.5. Step 1.5: Fast Concatenation (Alternative to Step 1)")
    print("     - Fast concatenation using -c copy (no re-encoding)")
    print("     - Groups files by type within each folder")
    print("     - Much faster than Step 1")
    print("     - Input: workflow/input/")
    print("     - Output: workflow/stage1_combine/")
    print()
    print("  2. Step 2: Convert to MP4")
    print("     - Converts all video formats to MP4")
    print("     - Input: auto-detects workflow/stage1_combine/")
    print("     - Output: workflow/stage2_convert/")
    print()
    print("  2.5. Step 2.5: Flip Videos (if needed)")
    print("     - Checks for rotation issues")
    print("     - Flips videos that are upside down")
    print("     - Input: workflow/stage2_convert/")
    print("     - Output: workflow/stage2_flip/")
    print()
    print("  3. Step 3: Enhance Quality")
    print("     - Applies brightness, contrast, sharpness")
    print("     - Cleans up audio")
    print("     - Input: auto-detects workflow/stage2_flip/ or workflow/stage2_convert/")
    print("     - Output: workflow/stage3_enhance/")
    print()
    print("  3.5. Step 3.5: AI Content Filter (Optional)")
    print("     - Analyzes videos for human content")
    print("     - Filters out videos without faces/bodies/movement")
    print("     - Input: workflow/stage3_enhance/")
    print("     - Output: workflow/stage3_filter/ (accepted), archive/trash/ (rejected)")
    print()
    print("  4. Run All Steps (1 → 2 → 2.5 → 3)")
    print("  5. Run All Steps with AI Filter (1 → 2 → 2.5 → 3 → 3.5)")
    print()
    print("  [B] Back to main menu")
    print("  [0] Exit")
    print()
    print("="*80)

def get_folder_size(folder: Path) -> int:
    """Calculate total size of a folder in bytes"""
    total = 0
    try:
        for item in folder.rglob('*'):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, FileNotFoundError):
                    pass  # Skip files that can't be accessed
    except Exception:
        pass
    return total

def copy_to_local_batched(source: Path, dest: Path, max_size_gb: float = 5.0, 
                          processed_folders: set = None, verbose: bool = False) -> tuple:
    """
    Copy folders from source to local temp, up to max_size_gb limit.
    Only copies complete folders (doesn't split folders).
    
    Returns: (success: bool, copied_folders: list, remaining_folders: list, total_size_gb: float)
    """
    if processed_folders is None:
        processed_folders = set()
    
    max_size_bytes = max_size_gb * 1024 * 1024 * 1024  # Convert GB to bytes
    current_size = 0
    copied_folders = []
    remaining_folders = []
    
    # Get all top-level folders and files
    top_level_items = []
    try:
        for item in source.iterdir():
            if item.name.startswith('.'):
                continue  # Skip hidden files/folders
            top_level_items.append(item)
    except Exception as e:
        print(f"Error reading source directory: {e}")
        return False, [], [], 0.0
    
    # Sort items (folders first, then files)
    folders = [item for item in top_level_items if item.is_dir() and item.name not in processed_folders]
    files = [item for item in top_level_items if item.is_file()]
    
    if verbose:
        print(f"\nFound {len(folders)} folders and {len(files)} files to process")
        print(f"Max batch size: {max_size_gb} GB")
    
    # Calculate sizes for each folder
    folder_sizes = {}
    for folder in folders:
        if verbose:
            print(f"  Calculating size for {folder.name}...")
        size = get_folder_size(folder)
        folder_sizes[folder] = size
        if verbose:
            print(f"    {folder.name}: {size / (1024**3):.2f} GB")
    
    # Add folders until we reach the limit
    for folder in folders:
        folder_size = folder_sizes[folder]
        
        # Check if adding this folder would exceed the limit
        if current_size + folder_size > max_size_bytes:
            remaining_folders.append(folder)
            if verbose:
                print(f"  Skipping {folder.name} ({folder_size / (1024**3):.2f} GB) - would exceed limit")
            continue
        
        # Copy the entire folder
        try:
            rel_path = folder.relative_to(source)
            dest_folder = dest / rel_path
            
            if verbose:
                print(f"  Copying folder: {folder.name} ({folder_size / (1024**3):.2f} GB)...")
            
            # Copy folder contents
            copied_files = 0
            failed_files = 0
            
            for item in folder.rglob('*'):
                if item.is_file():
                    try:
                        item_rel = item.relative_to(folder)
                        dest_file = dest_folder / item_rel
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file - triggers Google Drive download if needed
                        shutil.copy2(item, dest_file)
                        copied_files += 1
                        
                        if verbose and copied_files % 20 == 0:
                            print(f"    Copied {copied_files} files...")
                    except Exception as e:
                        failed_files += 1
                        if verbose:
                            print(f"    Warning: Could not copy {item.name}: {e}")
            
            if copied_files > 0:
                copied_folders.append(folder.name)
                current_size += folder_size
                processed_folders.add(folder.name)
                
                if verbose:
                    print(f"  ✓ Copied {folder.name}: {copied_files} files ({folder_size / (1024**3):.2f} GB)")
            else:
                remaining_folders.append(folder)
                if verbose:
                    print(f"  ✗ Failed to copy {folder.name}")
                    
        except Exception as e:
            remaining_folders.append(folder)
            if verbose:
                print(f"  ✗ Error copying {folder.name}: {e}")
    
    # Copy top-level files if there's space
    for file in files:
        try:
            file_size = file.stat().st_size
            if current_size + file_size > max_size_bytes:
                remaining_folders.append(file)  # Treat as remaining
                continue
            
            dest_file = dest / file.name
            shutil.copy2(file, dest_file)
            current_size += file_size
            copied_folders.append(file.name)
            if verbose:
                print(f"  ✓ Copied file: {file.name} ({file_size / (1024**3):.2f} GB)")
        except Exception as e:
            if verbose:
                print(f"  ✗ Error copying {file.name}: {e}")
    
    total_size_gb = current_size / (1024**3)
    success = len(copied_folders) > 0
    
    if verbose:
        print(f"\n✓ Batch complete: {len(copied_folders)} items copied ({total_size_gb:.2f} GB)")
        if remaining_folders:
            print(f"  Remaining: {len(remaining_folders)} items")
    
    return success, copied_folders, remaining_folders, total_size_gb

def copy_from_local(source: Path, dest: Path, verbose: bool = False):
    """Copy directory tree from local temp back to destination"""
    if verbose:
        print(f"Copying {source} to {dest}...")
    
    if not source.exists():
        print(f"Warning: Local source {source} does not exist")
        return False
    
    # Ensure destination exists
    dest.mkdir(parents=True, exist_ok=True)
    
    # Copy files, preserving structure
    try:
        for item in source.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(source)
                dest_file = dest / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)
        
        if verbose:
            print(f"✓ Copied from local temp: {dest}")
        return True
    except Exception as e:
        print(f"Error copying from local: {e}")
        return False

def run_step(step_num: str, args: list = None, use_local: bool = True, 
             processed_folders: set = None, max_batch_gb: float = 5.0):
    """
    Run a specific step script, optionally using local temp folder with batching.
    
    Returns: (success: bool, has_more: bool, processed_folders: set)
    """
    if processed_folders is None:
        processed_folders = set()
    
    step_scripts = {
        "1": "steps/step1_combine.py",
        "1.5": "steps/step1_fast_combine.py",
        "2": "steps/step2_convert.py",
        "2.5": "steps/step2_flip.py",
        "3": "steps/step3_enhance.py",
        "3.5": "steps/step3_filter.py"
    }
    
    if step_num not in step_scripts:
        print(f"Invalid step number: {step_num}")
        return False, False, processed_folders
    
    script_path = SCRIPT_DIR / step_scripts[step_num]
    
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return False, False, processed_folders
    
    print(f"\n{'='*80}")
    print(f"Running Step {step_num}...")
    if use_local:
        print("Mode: Using local temp folder for processing (files on cloud storage)")
        print(f"Batch size limit: {max_batch_gb} GB")
    else:
        print("Mode: Direct processing (no copying to temp folder)")
    print(f"{'='*80}\n")
    
    # Parse args to extract source, output, trash directories
    source_dir = None
    output_dir = None
    trash_dir = None
    verbose = False
    
    if args:
        i = 0
        while i < len(args):
            if args[i] == "--output" or args[i] == "-o":
                if i + 1 < len(args):
                    output_dir = Path(args[i + 1])
                    i += 2
                    continue
            elif args[i] == "--trash" or args[i] == "-t":
                if i + 1 < len(args):
                    trash_dir = Path(args[i + 1])
                    i += 2
                    continue
            elif args[i] == "--verbose" or args[i] == "-v":
                verbose = True
                i += 1
                continue
            elif not args[i].startswith("-"):
                # Positional argument (source directory)
                source_dir = Path(args[i])
            i += 1
    
    # If using local processing, copy files in batches and adjust paths
    if use_local and source_dir:
        # Resolve source_dir path (might be relative)
        if not source_dir.is_absolute():
            converter_dir = Path(__file__).parent.parent.resolve()
            source_dir = converter_dir / source_dir
        
        # Create local temp directories
        local_source = LOCAL_TEMP_DIR / f"step{step_num}_source"
        local_output = LOCAL_TEMP_DIR / f"step{step_num}_output"
        local_trash = LOCAL_TEMP_DIR / f"step{step_num}_trash" if trash_dir else None
        
        local_source.mkdir(parents=True, exist_ok=True)
        local_output.mkdir(parents=True, exist_ok=True)
        if local_trash:
            local_trash.mkdir(parents=True, exist_ok=True)
        
        # Copy source to local in batches (max 5GB, complete folders only)
        print("Copying source files to local temp folder (batched)...")
        print(f"  From: {source_dir}")
        print(f"  To: {local_source}")
        
        success, copied_folders, remaining_folders, total_size_gb = copy_to_local_batched(
            source_dir, local_source, max_batch_gb, processed_folders, verbose
        )
        
        if not success:
            print("Failed to copy source files to local temp")
            return False, len(remaining_folders) > 0, processed_folders
        
        print(f"\n✓ Copied batch: {len(copied_folders)} items ({total_size_gb:.2f} GB)")
        if remaining_folders:
            print(f"  Remaining: {len(remaining_folders)} items")
        
        has_more = len(remaining_folders) > 0
        
        # Update args to use local paths
        local_args = [str(local_source)]
        if output_dir:
            # Replace output with local output
            for i, arg in enumerate(args):
                if arg == "--output" or arg == "-o":
                    if i + 1 < len(args):
                        args[i + 1] = str(local_output)
                elif arg == "--trash" or arg == "-t":
                    if i + 1 < len(args) and local_trash:
                        args[i + 1] = str(local_trash)
            local_args.extend(args[1:])  # Skip source_dir, keep rest
        else:
            # Add output if not specified
            local_args.extend(["--output", str(local_output)])
            if args:
                local_args.extend([a for a in args[1:] if a != str(source_dir)])
        
        # Add trash if needed
        if trash_dir and "--trash" not in local_args and "-t" not in local_args:
            local_args.extend(["--trash", str(local_trash)])
        
        args = local_args
    else:
        # Direct processing mode - no copying
        print("Processing files directly from source (no temp folder copying)...")
        if not args:
            args = []
        has_more = False  # No batching if not using local processing
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd)
        success = result.returncode == 0
        
        # If using local processing and successful, copy results back
        if use_local and success:
            print("\nCopying results back from local temp folder...")
            if output_dir:
                # Resolve output_dir if relative
                if not output_dir.is_absolute():
                    converter_dir = Path(__file__).parent.parent.resolve()
                    output_dir = converter_dir / output_dir
                print(f"  Output: {output_dir}")
                copy_from_local(local_output, output_dir, verbose)
            if trash_dir and local_trash and local_trash.exists():
                # Resolve trash_dir if relative
                if not trash_dir.is_absolute():
                    converter_dir = Path(__file__).parent.parent.resolve()
                    trash_dir = converter_dir / trash_dir
                print(f"  Trash: {trash_dir}")
                copy_from_local(local_trash, trash_dir, verbose)
            
            # Cleanup local temp (optional - comment out to keep for debugging)
            try:
                if local_source.exists():
                    shutil.rmtree(local_source)
                if local_output.exists():
                    shutil.rmtree(local_output)
                if local_trash and local_trash.exists():
                    shutil.rmtree(local_trash)
            except Exception as e:
                print(f"Warning: Error cleaning up local temp: {e}")
        
        return success, has_more, processed_folders
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return False, has_more, processed_folders
    except Exception as e:
        print(f"Error running step: {e}")
        return False, has_more, processed_folders

def main():
    """Main orchestrator loop"""
    # Check for ffmpeg first
    print("\n" + "="*80)
    print("CHECKING DEPENDENCIES")
    print("="*80)
    if not check_ffmpeg():
        print("\nFFmpeg is required but not found. Please install it first.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Ask about local processing once at startup
    print("\n" + "="*80)
    print("LOCAL PROCESSING SETUP")
    print("="*80)
    print("Files are on Google Drive (cloud storage)")
    print()
    print("OPTIONS:")
    print("  [y] Use local temp folder - Copy files to local temp first (recommended for cloud storage)")
    print("  [n] Process directly - Skip copying, process files directly from source")
    print()
    print(f"Local temp folder: {LOCAL_TEMP_DIR}")
    use_local = input("Use local temp folder for processing? (y/n, default: y): ").strip().lower()
    use_local = use_local != 'n'  # Default to True
    
    # Show what mode we're in
    if use_local:
        print("\n✓ Using local temp folder mode (files will be copied to local temp)")
    else:
        print("\n✓ Direct processing mode (no copying, processing files in-place)")
    
    # Ask about batch size limit
    max_batch_gb = 5.0
    if use_local:
        batch_size_input = input("Max batch size in GB (default: 5.0): ").strip()
        if batch_size_input:
            try:
                max_batch_gb = float(batch_size_input)
                if max_batch_gb <= 0:
                    print("Invalid batch size, using default 5.0 GB")
                    max_batch_gb = 5.0
            except ValueError:
                print("Invalid batch size, using default 5.0 GB")
                max_batch_gb = 5.0
        print(f"Batch size limit set to: {max_batch_gb} GB")
    
    # Main menu loop
    while True:
        print_menu()
        
        try:
            choice = input("Enter your choice (S/P/0): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            break
        
        if choice == "0":
            print("Exiting...")
            break
        elif choice == "S" or choice == "":
            # Standard workflow
            run_standard_workflow(use_local, max_batch_gb)
        elif choice == "P":
            # Project workflow
            configure_project_workflow(use_local, max_batch_gb)
            input("\nPress Enter to continue...")
        else:
            print(f"\nInvalid choice: {choice}")
            input("\nPress Enter to continue...")

def configure_project_workflow(use_local: bool, max_batch_gb: float):
    """Configure and run project workflow with custom settings"""
    print("\n" + "="*80)
    print("PROJECT WORKFLOW CONFIGURATION")
    print("="*80)
    
    # Get custom input path
    print("\nInput Configuration:")
    input_path = input("Enter source directory path (or press Enter for workflow/input/): ").strip()
    if not input_path:
        input_path = "workflow/input"
    input_path = Path(input_path).resolve()
    
    if not input_path.exists():
        print(f"Error: Source directory {input_path} does not exist")
        return False
    
    # Get custom output path
    output_base = input("Enter output base directory (or press Enter for workflow/project_output/): ").strip()
    if not output_base:
        output_base = "workflow/project_output"
    output_base = Path(output_base).resolve()
    
    # Combine configuration
    print("\n" + "="*80)
    print("COMBINE STEP CONFIGURATION")
    print("="*80)
    print("\nCombine mode:")
    print("  [1] Truncate per batch (group by date/time with duration limit)")
    print("  [2] Combine all into one (all videos in folder → one video)")
    combine_mode = input("Select mode (1 or 2, default: 1): ").strip() or "1"
    
    combine_all = combine_mode == "2"
    max_duration = 3600  # default
    
    if not combine_all:
        duration_input = input("Max duration per batch in seconds (0 = unlimited, default: 3600 = 1 hour): ").strip()
        if duration_input:
            try:
                max_duration = int(duration_input)
                if max_duration < 0:
                    max_duration = 0  # unlimited
            except ValueError:
                print("Invalid input, using default 3600 seconds")
                max_duration = 3600
    else:
        max_duration = 0  # unlimited when combining all
    
    # Step toggles
    print("\n" + "="*80)
    print("STEP CONFIGURATION")
    print("="*80)
    print("\nEnable/disable each step:")
    
    enable_convert = input("Enable Step 2: Convert to MP4? (y/n, default: y): ").strip().lower() != 'n'
    enable_flip = input("Enable Step 2.5: Flip Videos? (y/n, default: n): ").strip().lower() == 'y'
    enable_enhance = input("Enable Step 3: Enhance Quality? (y/n, default: n): ").strip().lower() == 'y'
    enable_filter = input("Enable Step 3.5: AI Content Filter? (y/n, default: n): ").strip().lower() == 'y'
    
    # Summary
    print("\n" + "="*80)
    print("CONFIGURATION SUMMARY")
    print("="*80)
    print(f"Input: {input_path}")
    print(f"Output base: {output_base}")
    print(f"Combine mode: {'Combine all into one' if combine_all else f'Truncate per batch (max {max_duration}s)'}")
    print(f"Step 2 (Convert): {'Enabled' if enable_convert else 'Disabled'}")
    print(f"Step 2.5 (Flip): {'Enabled' if enable_flip else 'Disabled'}")
    print(f"Step 3 (Enhance): {'Enabled' if enable_enhance else 'Disabled'}")
    print(f"Step 3.5 (Filter): {'Enabled' if enable_filter else 'Disabled'}")
    print("="*80)
    
    confirm = input("\nProceed with this configuration? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return False
    
    # Run the pipeline
    print("\n" + "="*80)
    print("RUNNING PROJECT WORKFLOW")
    print("="*80)
    
    # Step 1: Combine
    print("\n[STEP 1] Combining videos...")
    step1_output = output_base / "stage1_combine"
    step1_trash = output_base / "archive" / "stage1_combine"
    
    step1_args = [
        str(input_path),
        "--output", str(step1_output),
        "--trash", str(step1_trash),
    ]
    if combine_all:
        step1_args.append("--combine-all")
    else:
        step1_args.extend(["--max-duration", str(max_duration)])
    
    success, _, _ = run_step("1", step1_args, use_local, set(), max_batch_gb)
    if not success:
        print("\nStep 1 failed. Stopping.")
        return False
    
    current_input = step1_output
    
    # Step 2: Convert
    if enable_convert:
        print("\n[STEP 2] Converting to MP4...")
        step2_output = output_base / "stage2_convert"
        step2_trash = output_base / "archive" / "stage2_convert"
        
        step2_args = [
            str(current_input),
            "--output", str(step2_output),
            "--trash", str(step2_trash),
        ]
        
        success, _, _ = run_step("2", step2_args, use_local)
        if not success:
            print("\nStep 2 failed. Stopping.")
            return False
        current_input = step2_output
    
    # Step 2.5: Flip
    if enable_flip:
        print("\n[STEP 2.5] Flipping videos...")
        step2_5_output = output_base / "stage2_flip"
        
        step2_5_args = [
            str(current_input),
            "--output", str(step2_5_output),
        ]
        
        success, _, _ = run_step("2.5", step2_5_args, use_local)
        if not success:
            print("\nStep 2.5 failed. Stopping.")
            return False
        current_input = step2_5_output
    
    # Step 3: Enhance
    if enable_enhance:
        print("\n[STEP 3] Enhancing quality...")
        step3_output = output_base / "stage3_enhance"
        step3_trash = output_base / "archive" / "stage3_enhance"
        
        step3_args = [
            str(current_input),
            "--output", str(step3_output),
            "--trash", str(step3_trash),
        ]
        
        success, _, _ = run_step("3", step3_args, use_local)
        if not success:
            print("\nStep 3 failed. Stopping.")
            return False
        current_input = step3_output
    
    # Step 3.5: Filter
    if enable_filter:
        print("\n[STEP 3.5] AI Content Filtering...")
        step3_5_output = output_base / "stage3_filter"
        step3_5_rejected = output_base / "archive" / "stage3_filter_rejected"
        
        step3_5_args = [
            str(current_input),
            "--output", str(step3_5_output),
            "--rejected", str(step3_5_rejected),
        ]
        
        success, _, _ = run_step("3.5", step3_5_args, use_local)
        if not success:
            print("\nStep 3.5 failed. Stopping.")
            return False
        current_input = step3_5_output
    
    print("\n" + "="*80)
    print("PROJECT WORKFLOW COMPLETE!")
    print("="*80)
    print(f"Final output: {current_input}")
    return True

def run_standard_workflow(use_local: bool, max_batch_gb: float):
    """Run standard workflow menu"""
    while True:
        print_standard_menu()
        
        try:
            choice = input("Enter your choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            break
        
        if choice == "0":
            print("Exiting...")
            break
        elif choice.lower() == "b":
            break
        elif choice == "1":
            print("\nStep 1: Group and Concatenate")
            print("Default: source=workflow/input, output=workflow/stage1_combine, trash=archive/trash/stage1_combine")
            custom = input("Use custom directories? (y/n): ").strip().lower()
            args = []
            if custom == 'y':
                source = input("Source directory (default: workflow/input): ").strip()
                if source:
                    args.append(source)
                else:
                    args.append("workflow/input")  # Use default
                output = input("Output directory (default: workflow/stage1_combine): ").strip()
                if output:
                    args.extend(["--output", output])
                else:
                    args.extend(["--output", "workflow/stage1_combine"])  # Use default
                trash = input("Trash directory (default: archive/trash/stage1_combine): ").strip()
                if trash:
                    args.extend(["--trash", trash])
                else:
                    args.extend(["--trash", "archive/trash/stage1_combine"])  # Use default
            else:
                # Use defaults
                args = ["workflow/input", "--output", "workflow/stage1_combine", "--trash", "archive/trash/stage1_combine"]
            verbose = input("Verbose output? (y/n): ").strip().lower()
            if verbose == 'y':
                args.append("--verbose")
            dry_run = input("Dry run (show what would be done)? (y/n): ").strip().lower()
            if dry_run == 'y':
                args.append("--dry-run")
            
            # Process in batches with continuation prompt
            processed_folders = set()
            while True:
                success, has_more, processed_folders = run_step("1", args, use_local, processed_folders, max_batch_gb)
                if not success:
                    print("\nStep 1 failed. Stopping.")
                    break
                if not has_more:
                    print("\n✓ All folders processed!")
                    break
                print("\n" + "="*80)
                print(f"Batch complete! {len(processed_folders)} folders processed so far.")
                print("="*80)
                continue_choice = input("\nContinue with next batch? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    print("Stopping. You can restart the app later to continue.")
                    break
        elif choice == "1.5":
            print("\nStep 1.5: Fast Concatenation (Alternative to Step 1)")
            print("Default: source=1.5-fast-combine, output=done/1.5-fast-combine, trash=trash/1.5-fast-combine")
            custom = input("Use custom directories? (y/n): ").strip().lower()
            args = []
            if custom == 'y':
                source = input("Source directory (default: 1.5-fast-combine): ").strip()
                if source:
                    args.append(source)
                output = input("Output directory (default: done/1.5-fast-combine): ").strip()
                if output:
                    args.extend(["--output", output])
                trash = input("Trash directory (default: trash/1.5-fast-combine): ").strip()
                if trash:
                    args.extend(["--trash", trash])
            parallel = input("Parallel workers (default: 1): ").strip()
            if parallel:
                args.extend(["--parallel", parallel])
            verbose = input("Verbose output? (y/n): ").strip().lower()
            if verbose == 'y':
                args.append("--verbose")
            dry_run = input("Dry run (show what would be done)? (y/n): ").strip().lower()
            if dry_run == 'y':
                args.append("--dry-run")
            # Process in batches with continuation prompt
            processed_folders = set()
            while True:
                success, has_more, processed_folders = run_step("1.5", args, use_local, processed_folders, max_batch_gb)
                if not success:
                    print("\nStep 1.5 failed. Stopping.")
                    break
                if not has_more:
                    print("\n✓ All folders processed!")
                    break
                print("\n" + "="*80)
                print(f"Batch complete! {len(processed_folders)} folders processed so far.")
                print("="*80)
                continue_choice = input("\nContinue with next batch? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    print("Stopping. You can restart the app later to continue.")
                    break
        elif choice == "2":
            print("\nStep 2: Convert to MP4")
            print("Default: source=auto-detect, output=done/2-convert, trash=trash/2-convert")
            custom = input("Use custom directories? (y/n): ").strip().lower()
            args = []
            if custom == 'y':
                source = input("Source directory (default: auto-detect done/1-combine or done/1.5-fast-combine): ").strip()
                if source:
                    args.append(source)
                output = input("Output directory (default: done/2-convert): ").strip()
                if output:
                    args.extend(["--output", output])
                trash = input("Trash directory (default: trash/2-convert): ").strip()
                if trash:
                    args.extend(["--trash", trash])
            no_gpu = input("Disable GPU? (y/n): ").strip().lower()
            if no_gpu == 'y':
                args.append("--no-gpu")
            threads = input("Number of threads (default: 4): ").strip()
            if threads:
                args.extend(["--threads", threads])
            verbose = input("Verbose output? (y/n): ").strip().lower()
            if verbose == 'y':
                args.append("--verbose")
            dry_run = input("Dry run (show what would be done)? (y/n): ").strip().lower()
            if dry_run == 'y':
                args.append("--dry-run")
            success, _, _ = run_step("2", args, use_local)
            if not success:
                print("\nStep 2 failed.")
        elif choice == "2.5":
            print("\nStep 2.5: Flip Videos (if needed)")
            print("Default: source=2.5-flip, output=done/2.5-flip")
            print("Note: Files are copied (not moved), so originals remain in source")
            custom = input("Use custom directories? (y/n): ").strip().lower()
            args = []
            if custom == 'y':
                source = input("Source directory (default: 2.5-flip): ").strip()
                if source:
                    args.append(source)
                output = input("Output directory (default: done/2.5-flip): ").strip()
                if output:
                    args.extend(["--output", output])
            verbose = input("Verbose output? (y/n): ").strip().lower()
            if verbose == 'y':
                args.append("--verbose")
            dry_run = input("Dry run (show what would be done)? (y/n): ").strip().lower()
            if dry_run == 'y':
                args.append("--dry-run")
            success, _, _ = run_step("2.5", args, use_local)
            if not success:
                print("\nStep 2.5 failed.")
        elif choice == "3":
            print("\nStep 3: Enhance Quality")
            print("Default: source=auto-detect, output=done/3-enhance, trash=trash/3-enhance")
            custom = input("Use custom directories? (y/n): ").strip().lower()
            args = []
            if custom == 'y':
                source = input("Source directory (default: auto-detect done/2.5-flip or done/2-convert): ").strip()
                if source:
                    args.append(source)
                output = input("Output directory (default: done/3-enhance): ").strip()
                if output:
                    args.extend(["--output", output])
                trash = input("Trash directory (default: trash/3-enhance): ").strip()
                if trash:
                    args.extend(["--trash", trash])
            no_gpu = input("Disable GPU? (y/n): ").strip().lower()
            if no_gpu == 'y':
                args.append("--no-gpu")
            threads = input("Number of threads (default: 4): ").strip()
            if threads:
                args.extend(["--threads", threads])
            verbose = input("Verbose output? (y/n): ").strip().lower()
            if verbose == 'y':
                args.append("--verbose")
            dry_run = input("Dry run (show what would be done)? (y/n): ").strip().lower()
            if dry_run == 'y':
                args.append("--dry-run")
            success, _, _ = run_step("3", args, use_local)
            if not success:
                print("\nStep 3 failed.")
        elif choice == "3.5":
            print("\nStep 3.5: AI Content Filter (Optional)")
            print("Default: source=3.5-ai-enhance, output=done/3.5-ai-enhance, rejected=trash/3.5-ai-enhance")
            print("Note: Files are copied (not moved), so originals remain in source")
            custom = input("Use custom directories? (y/n): ").strip().lower()
            args = []
            if custom == 'y':
                source = input("Source directory (default: 3.5-ai-enhance): ").strip()
                if source:
                    args.append(source)
                output = input("Output directory for accepted (default: done/3.5-ai-enhance): ").strip()
                if output:
                    args.extend(["--output", output])
                rejected = input("Rejected directory (default: trash/3.5-ai-enhance): ").strip()
                if rejected:
                    args.extend(["--rejected", rejected])
            confidence = input("Confidence threshold (default: 0.4): ").strip()
            if confidence:
                args.extend(["--confidence", confidence])
            samples = input("Frames to sample per video (default: 5): ").strip()
            if samples:
                args.extend(["--samples", samples])
            verbose = input("Verbose output? (y/n): ").strip().lower()
            if verbose == 'y':
                args.append("--verbose")
            dry_run = input("Dry run (show what would be done)? (y/n): ").strip().lower()
            if dry_run == 'y':
                args.append("--dry-run")
            success, _, _ = run_step("3.5", args, use_local)
            if not success:
                print("\nStep 3.5 failed.")
        elif choice == "4":
            print("\nRunning all steps in sequence...")
            print("This will run: Step 1 → Step 2 → Step 2.5 → Step 3")
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
            
            verbose = input("Verbose output for all steps? (y/n): ").strip().lower()
            verbose_arg = ["--verbose"] if verbose == 'y' else []
            
            print("\n" + "="*80)
            print("STEP 1: Group and Concatenate")
            print("="*80)
            processed_folders = set()
            while True:
                success, has_more, processed_folders = run_step("1", verbose_arg, use_local, processed_folders)
                if not success:
                    print("\nStep 1 failed. Stopping.")
                    break
                if not has_more:
                    break
                print("\n" + "="*80)
                print(f"Batch complete! {len(processed_folders)} folders processed so far.")
                print("="*80)
                continue_choice = input("\nContinue with next batch? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    print("Stopping. You can restart the app later to continue.")
                    break
            
            print("\n" + "="*80)
            print("STEP 2: Convert to MP4")
            print("="*80)
            success, _, _ = run_step("2", verbose_arg, use_local)
            if not success:
                print("\nStep 2 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("STEP 2.5: Flip Videos")
            print("="*80)
            success, _, _ = run_step("2.5", verbose_arg, use_local)
            if not success:
                print("\nStep 2.5 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("STEP 3: Enhance Quality")
            print("="*80)
            success, _, _ = run_step("3", verbose_arg, use_local)
            if not success:
                print("\nStep 3 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("ALL STEPS COMPLETE!")
            print("="*80)
            print("Final videos are in: done/3-enhance/")
        elif choice == "5":
            print("\nRunning all steps with AI filter in sequence...")
            print("This will run: Step 1 → Step 2 → Step 2.5 → Step 3 → Step 3.5")
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
            
            verbose = input("Verbose output for all steps? (y/n): ").strip().lower()
            verbose_arg = ["--verbose"] if verbose == 'y' else []
            
            print("\n" + "="*80)
            print("STEP 1: Group and Concatenate")
            print("="*80)
            processed_folders = set()
            while True:
                success, has_more, processed_folders = run_step("1", verbose_arg, use_local, processed_folders)
                if not success:
                    print("\nStep 1 failed. Stopping.")
                    break
                if not has_more:
                    break
                print("\n" + "="*80)
                print(f"Batch complete! {len(processed_folders)} folders processed so far.")
                print("="*80)
                continue_choice = input("\nContinue with next batch? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    print("Stopping. You can restart the app later to continue.")
                    break
            
            print("\n" + "="*80)
            print("STEP 2: Convert to MP4")
            print("="*80)
            success, _, _ = run_step("2", verbose_arg, use_local)
            if not success:
                print("\nStep 2 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("STEP 2.5: Flip Videos")
            print("="*80)
            success, _, _ = run_step("2.5", verbose_arg, use_local)
            if not success:
                print("\nStep 2.5 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("STEP 3: Enhance Quality")
            print("="*80)
            success, _, _ = run_step("3", verbose_arg, use_local)
            if not success:
                print("\nStep 3 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("STEP 3.5: AI Content Filter")
            print("="*80)
            ai_args = verbose_arg.copy()
            confidence = input("AI filter confidence threshold (default: 0.4): ").strip()
            if confidence:
                ai_args.extend(["--confidence", confidence])
            success, _, _ = run_step("3.5", ai_args, use_local)
            if not success:
                print("\nStep 3.5 failed. Stopping.")
                continue
            
            print("\n" + "="*80)
            print("ALL STEPS COMPLETE!")
            print("="*80)
            print("Filtered videos are in: 3-5-filtered/")
            print("Rejected videos are in: 3-5-rejected/")
        else:
            print(f"\nInvalid choice: {choice}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()

