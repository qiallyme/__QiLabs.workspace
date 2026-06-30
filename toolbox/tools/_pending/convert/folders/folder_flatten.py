#!/usr/bin/env python3
"""
Script to flatten folder structure by moving contents up one or more levels.
Empty folders are moved to .trash after flattening.
"""

import os
import shutil
from pathlib import Path
from typing import List


def get_unique_path(destination_dir: Path, filename: str) -> Path:
    """Get a unique path if file already exists, appending a number."""
    base_path = destination_dir / filename
    if not base_path.exists():
        return base_path
    
    stem = base_path.stem
    suffix = base_path.suffix
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = destination_dir / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def flatten_folder(folder_path: Path, target_path: Path, trash_path: Path) -> None:
    """
    Flatten a folder by moving all its contents to the target path.
    Then move the empty folder to trash.
    """
    if not folder_path.exists() or not folder_path.is_dir():
        return
    
    # Skip if trying to process the trash folder itself
    if folder_path.name == ".trash" or folder_path == trash_path:
        return
    
    # Get all items in the folder
    items = list(folder_path.iterdir())
    
    if not items:
        # Folder is already empty, just move it to trash
        print(f"  Moving empty folder to trash: {folder_path.name}")
        trash_folder = trash_path / folder_path.name
        if trash_folder.exists():
            # If trash folder with same name exists, add a number
            counter = 1
            while (trash_path / f"{folder_path.name}_{counter}").exists():
                counter += 1
            trash_folder = trash_path / f"{folder_path.name}_{counter}"
        shutil.move(str(folder_path), str(trash_folder))
        return
    
    # Move all contents to target path
    for item in items:
        target_item = target_path / item.name
        
        # Handle name conflicts
        if target_item.exists():
            target_item = get_unique_path(target_path, item.name)
            print(f"  Renaming due to conflict: {item.name} -> {target_item.name}")
        
        print(f"  Moving: {item.name}")
        shutil.move(str(item), str(target_item))
    
    # Move empty folder to trash
    print(f"  Moving empty folder to trash: {folder_path.name}")
    trash_folder = trash_path / folder_path.name
    if trash_folder.exists():
        counter = 1
        while (trash_path / f"{folder_path.name}_{counter}").exists():
            counter += 1
        trash_folder = trash_path / f"{folder_path.name}_{counter}"
    shutil.move(str(folder_path), str(trash_folder))


def flatten_level(base_path: Path, level: int, current_level: int, trash_path: Path) -> None:
    """
    Recursively flatten folders at the specified level.
    
    Args:
        base_path: The base folder to process
        level: Target level to flatten (1 = immediate subfolders)
        current_level: Current depth (starts at 0)
        trash_path: Path to .trash folder
    """
    if current_level >= level:
        return
    
    if not base_path.exists() or not base_path.is_dir():
        return
    
    # Get all subdirectories at current level, excluding .trash
    subdirs = [item for item in base_path.iterdir() 
               if item.is_dir() and item.name != ".trash"]
    
    if current_level == level - 1:
        # We're at the level to flatten
        print(f"\nFlattening level {level} in: {base_path}")
        for subdir in subdirs:
            print(f"Processing folder: {subdir.name}")
            flatten_folder(subdir, base_path, trash_path)
    else:
        # Recurse deeper
        for subdir in subdirs:
            flatten_level(subdir, level, current_level + 1, trash_path)


def main():
    """Main function to run the folder flattening script."""
    print("=" * 60)
    print("Folder Flattening Script")
    print("=" * 60)
    
    # Get folder path
    folder_path_input = input("\nEnter the path of the folder to flatten: ").strip()
    if not folder_path_input:
        print("Error: No path provided.")
        return
    
    # Remove surrounding quotes if present
    folder_path_input = folder_path_input.strip('"\'')
    
    folder_path = Path(folder_path_input)
    
    if not folder_path.exists():
        print(f"Error: Path does not exist: {folder_path}")
        return
    
    if not folder_path.is_dir():
        print(f"Error: Path is not a directory: {folder_path}")
        return
    
    # Get number of levels
    levels_input = input("How many levels down to flatten? (default: 1): ").strip()
    if not levels_input:
        levels = 1
    else:
        try:
            levels = int(levels_input)
            if levels < 1:
                print("Error: Number of levels must be at least 1.")
                return
        except ValueError:
            print("Error: Invalid number. Using default of 1.")
            levels = 1
    
    # Create .trash folder in the target directory
    trash_path = folder_path / ".trash"
    trash_path.mkdir(exist_ok=True)
    print(f"\nTrash folder: {trash_path}")
    
    # Confirm before proceeding
    print(f"\nAbout to flatten {levels} level(s) in: {folder_path}")
    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Process each level from 1 to the specified number
    for level in range(1, levels + 1):
        print(f"\n{'=' * 60}")
        print(f"Processing Level {level}")
        print(f"{'=' * 60}")
        flatten_level(folder_path, level, 0, trash_path)
    
    print(f"\n{'=' * 60}")
    print("Flattening complete!")
    print(f"Empty folders moved to: {trash_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

