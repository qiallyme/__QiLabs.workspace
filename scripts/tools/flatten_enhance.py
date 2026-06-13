#!/usr/bin/env python3
"""
Flatten Enhance Folder - Move all files from subfolders to root of 3-enhance/
"""

import shutil
from pathlib import Path

ENHANCE_DIR = Path(r"C:\Users\codyr\My Drive\.private\.converter\3-enhance")

def flatten_directory(root_dir: Path):
    """Move all files from subdirectories to root directory"""
    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist")
        return
    
    moved_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"Flattening {root_dir}...")
    print()
    
    # Find all files in subdirectories
    for subdir in root_dir.iterdir():
        if subdir.is_dir():
            print(f"Processing subdirectory: {subdir.name}")
            files_in_subdir = list(subdir.rglob('*'))
            video_files = [f for f in files_in_subdir if f.is_file()]
            
            for file_path in video_files:
                # Get relative path from subdir to preserve uniqueness if needed
                rel_path = file_path.relative_to(subdir)
                
                # Target file in root
                target_file = root_dir / file_path.name
                
                # If file with same name exists, add subdir name prefix
                if target_file.exists() and target_file != file_path:
                    # Add subdir name to filename to avoid conflicts
                    stem = file_path.stem
                    suffix = file_path.suffix
                    target_file = root_dir / f"{subdir.name}_{stem}{suffix}"
                
                try:
                    if target_file.exists() and target_file.samefile(file_path):
                        # Same file, skip
                        skipped_count += 1
                        continue
                    
                    # Move file to root
                    shutil.move(str(file_path), str(target_file))
                    print(f"  Moved: {file_path.name} -> {target_file.name}")
                    moved_count += 1
                except Exception as e:
                    print(f"  Error moving {file_path.name}: {e}")
                    error_count += 1
            
            # Try to remove empty subdirectory
            try:
                if not any(subdir.rglob('*')):
                    subdir.rmdir()
                    print(f"  Removed empty directory: {subdir.name}")
            except Exception as e:
                print(f"  Could not remove directory {subdir.name}: {e}")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Files moved: {moved_count}")
    print(f"Files skipped (already in root): {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"All files are now in: {root_dir}")

if __name__ == "__main__":
    flatten_directory(ENHANCE_DIR)

