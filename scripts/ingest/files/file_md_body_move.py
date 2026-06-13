#!/usr/bin/env python3
"""
Move markdown files to .trash based on body content search.

Searches markdown files for a specific string in the BODY content only
(not in front matter/metadata). If the string is found, moves the file to .trash.

Usage:
    python move_md_by_body_content.py --search-string "source: " --root "realms/qivault"
    python move_md_by_body_content.py --search-string "source: " --root "." --dry-run
"""

import os
import re
import yaml
import shutil
import argparse
from pathlib import Path
from typing import Tuple, Optional


def extract_front_matter(content: str) -> Tuple[Optional[dict], str]:
    """
    Extract YAML front matter from markdown content.
    Returns: (front_matter_dict, body_content)
    """
    # Pattern: ---\n...yaml...\n---
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if match:
        try:
            yaml_content = match.group(1)
            body = match.group(2)
            frontmatter = yaml.safe_load(yaml_content) or {}
            return frontmatter, body
        except yaml.YAMLError:
            # Invalid YAML, treat as no front matter
            return None, content
    
    return None, content


def search_body_content(file_path: Path, search_string: str) -> bool:
    """
    Search for search_string in the body content of a markdown file.
    Returns True if found in body, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read {file_path}: {e}")
        return False
    
    # Extract front matter and body
    front_matter, body = extract_front_matter(content)
    
    # Search only in body content
    if search_string in body:
        return True
    
    return False


def move_to_trash(file_path: Path, trash_root: Path, dry_run: bool = False) -> bool:
    """
    Move file to .trash directory, preserving relative path structure.
    """
    # Get relative path from root to preserve structure
    try:
        # Find the root by looking for .trash parent
        root = trash_root.parent
        rel_path = file_path.relative_to(root)
    except ValueError:
        # If we can't get relative path, just use filename
        rel_path = Path(file_path.name)
    
    dest = trash_root / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Handle name conflicts
    counter = 1
    original_dest = dest
    while dest.exists():
        stem = original_dest.stem
        suffix = original_dest.suffix
        dest = original_dest.parent / f"{stem}_{counter}{suffix}"
        counter += 1
    
    if dry_run:
        print(f"[DRY RUN] Would move: {file_path} -> {dest}")
        return True
    
    try:
        shutil.move(str(file_path), str(dest))
        print(f"MOVED: {file_path.relative_to(root) if 'root' in locals() else file_path} -> {dest.relative_to(root) if 'root' in locals() else dest}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to move {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Move markdown files to .trash based on body content search'
    )
    parser.add_argument(
        '--search-string',
        required=True,
        help='String to search for in body content (e.g., "source: ")'
    )
    parser.add_argument(
        '--root',
        default='.',
        help='Root directory to search (default: current directory)'
    )
    parser.add_argument(
        '--trash-dir',
        default='.trash',
        help='Trash directory name (default: .trash)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be moved without actually moving files'
    )
    parser.add_argument(
        '--exclude-dirs',
        nargs='*',
        default=['.git', '.trash', '__pycache__', 'node_modules', '.venv'],
        help='Directories to exclude from search'
    )
    
    args = parser.parse_args()
    
    root = Path(args.root).resolve()
    trash_root = root / args.trash_dir
    
    if not root.exists():
        print(f"[ERROR] Root directory does not exist: {root}")
        return
    
    # Create trash directory if it doesn't exist
    if not args.dry_run:
        trash_root.mkdir(parents=True, exist_ok=True)
    
    print(f"Searching for '{args.search_string}' in markdown body content...")
    print(f"Root: {root}")
    print(f"Trash: {trash_root}")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be moved]")
    print()
    
    moved = 0
    checked = 0
    errors = 0
    
    # Walk through directory tree
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in args.exclude_dirs]
        
        # Skip .trash directory itself
        if args.trash_dir in Path(dirpath).parts:
            dirnames[:] = []
            continue
        
        current_dir = Path(dirpath)
        
        for filename in filenames:
            if not filename.lower().endswith('.md'):
                continue
            
            file_path = current_dir / filename
            checked += 1
            
            # Search body content
            if search_body_content(file_path, args.search_string):
                if move_to_trash(file_path, trash_root, args.dry_run):
                    moved += 1
                else:
                    errors += 1
    
    print()
    print("=== SUMMARY ===")
    print(f"Files checked: {checked}")
    print(f"Files moved: {moved}")
    if errors > 0:
        print(f"Errors: {errors}")
    if args.dry_run:
        print("\n[DRY RUN - No files were actually moved]")


if __name__ == "__main__":
    main()

