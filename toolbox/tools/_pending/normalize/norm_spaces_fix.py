#!/usr/bin/env python3
"""
Fix filenames with trailing spaces before extension
"""
import re
from pathlib import Path

QIOS_BASE = Path(r"C:\QiOS")

def fix_filename(filename):
    """Fix trailing spaces before extension."""
    # Check if there are spaces before the extension
    if re.search(r'\s+\.', filename):
        # Remove spaces before extension
        fixed = re.sub(r'\s+\.', '.', filename)
        return fixed
    return filename

def fix_directory(directory):
    """Fix filenames in a directory recursively."""
    renamed = []
    
    for filepath in directory.rglob('*'):
        if not filepath.is_file():
            continue
        
        fixed_name = fix_filename(filepath.name)
        if fixed_name != filepath.name:
            new_path = filepath.parent / fixed_name
            
            # Handle conflicts
            if new_path.exists():
                counter = 1
                stem = Path(fixed_name).stem
                ext = Path(fixed_name).suffix
                while new_path.exists():
                    new_path = filepath.parent / f"{stem}_{counter}{ext}"
                    counter += 1
                fixed_name = new_path.name
            
            try:
                filepath.rename(new_path)
                renamed.append((filepath.name, fixed_name))
            except Exception as e:
                print(f"Error renaming {filepath.name}: {e}")
    
    return renamed

def main():
    """Fix trailing spaces in all organized directories."""
    directories = [
        QIOS_BASE / 'docs',
        QIOS_BASE / 'data',
        QIOS_BASE / 'images',
        QIOS_BASE / 'assets',
    ]
    
    total_renamed = 0
    
    print("Fixing trailing spaces in filenames...\n")
    
    for directory in directories:
        if not directory.exists():
            continue
        
        print(f"Processing {directory}...")
        renamed = fix_directory(directory)
        total_renamed += len(renamed)
        
        if renamed:
            print(f"  Fixed {len(renamed)} files")
    
    print(f"\n=== Fix Complete ===\n")
    print(f"Total files fixed: {total_renamed}")

if __name__ == '__main__':
    main()
