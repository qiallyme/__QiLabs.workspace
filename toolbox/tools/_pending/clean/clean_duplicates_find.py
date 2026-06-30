#!/usr/bin/env python3
"""
QiOS Duplicate Finder
Finds duplicate files by name and/or content hash.
Generates a report for review and potential deduplication.
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import json
from datetime import datetime

class DuplicateFinder:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.duplicates_by_name = defaultdict(list)
        self.duplicates_by_hash = defaultdict(list)
        self.stats = {
            'files_scanned': 0,
            'duplicate_names': 0,
            'duplicate_content': 0,
            'errors': 0
        }
    
    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            print(f"Error hashing {file_path}: {e}")
            return ""
    
    def find_duplicates_by_name(self, folder_path: Path = None, same_folder_only: bool = True) -> Dict[str, List[Path]]:
        """Find files with duplicate names in the same folder (not across different folders)"""
        if folder_path is None:
            folder_path = self.root_path
        
        duplicates = defaultdict(list)
        
        # Group by folder, then by filename
        folder_to_files = defaultdict(lambda: defaultdict(list))
        
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                parent_folder = str(file_path.parent.relative_to(folder_path))
                folder_to_files[parent_folder][file_path.name.lower()].append(file_path)
                self.stats['files_scanned'] += 1
        
        # Only report duplicates within the same folder
        for folder, files_by_name in folder_to_files.items():
            for filename, paths in files_by_name.items():
                if len(paths) > 1:
                    # These are actual duplicates in the same folder
                    duplicates[f"{folder}/{filename}"].extend(paths)
        
        return duplicates
    
    def find_duplicates_by_content(self, folder_path: Path = None, sample_size: int = None) -> Dict[str, List[Path]]:
        """Find files with duplicate content (by hash)"""
        if folder_path is None:
            folder_path = self.root_path
        
        hash_to_files = defaultdict(list)
        
        files_to_check = list(folder_path.rglob('*'))
        if sample_size:
            files_to_check = files_to_check[:sample_size]
        
        for file_path in files_to_check:
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    file_hash = self.compute_file_hash(file_path)
                    if file_hash:
                        hash_to_files[file_hash].append(file_path)
                        self.stats['files_scanned'] += 1
                except Exception as e:
                    self.stats['errors'] += 1
                    continue
        
        # Filter to only actual duplicates
        return {file_hash: paths for file_hash, paths in hash_to_files.items() if len(paths) > 1}
    
    def generate_report(self, name_duplicates: Dict, content_duplicates: Dict, output_path: Path) -> str:
        """Generate a markdown report of duplicates"""
        total_name_dups = sum(len(v) for v in name_duplicates.values())
        total_content_dups = sum(len(v) for v in content_duplicates.values())
        
        report = f"""# Duplicate Files Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Root Path:** `{self.root_path}`
**Files Scanned:** {self.stats['files_scanned']}

---

## Summary

- **Duplicate Names (same folder):** {len(name_duplicates)} folders with duplicate filenames ({total_name_dups} total duplicate files)
- **Duplicate Content (identical files):** {len(content_duplicates)} unique content hashes with {total_content_dups} total files
- **Errors:** {self.stats['errors']}

**Note:** Files with the same name in different folders are NOT considered duplicates. Only files with the same name in the same folder, or files with identical content, are reported.

---

## Duplicates by Filename (Same Folder Only)

"""
        
        if name_duplicates:
            # Sort by number of duplicates (most first)
            sorted_names = sorted(name_duplicates.items(), key=lambda x: len(x[1]), reverse=True)
            
            for folder_and_filename, paths in sorted_names:
                # Extract folder and filename from key
                parts = folder_and_filename.rsplit('/', 1)
                if len(parts) == 2:
                    folder, filename = parts
                    report += f"### {filename} in `{folder}/` ({len(paths)} copies)\n\n"
                else:
                    report += f"### {folder_and_filename} ({len(paths)} copies)\n\n"
                
                for i, path in enumerate(paths, 1):
                    rel_path = str(path.relative_to(self.root_path)).replace('\\', '/')
                    size = path.stat().st_size if path.exists() else 0
                    size_kb = size / 1024
                    report += f"{i}. `{rel_path}` ({size_kb:.1f} KB)\n"
                report += "\n"
        else:
            report += "*No duplicate filenames found in the same folders.*\n\n"
        
        report += "\n---\n\n## Duplicates by Content Hash\n\n"
        
        # Sort by number of duplicates (most first)
        sorted_hashes = sorted(content_duplicates.items(), key=lambda x: len(x[1]), reverse=True)
        
        for file_hash, paths in sorted_hashes[:50]:  # Limit to top 50
            report += f"### Hash: {file_hash[:16]}... ({len(paths)} identical files)\n\n"
            for i, path in enumerate(paths, 1):
                rel_path = str(path.relative_to(self.root_path)).replace('\\', '/')
                size = path.stat().st_size if path.exists() else 0
                size_kb = size / 1024
                report += f"{i}. `{rel_path}` ({size_kb:.1f} KB)\n"
            report += "\n"
        
        if len(sorted_hashes) > 50:
            report += f"\n*... and {len(sorted_hashes) - 50} more content duplicate groups*\n"
        
        return report
    
    def find_duplicates(self, check_content: bool = False, sample_size: int = None, same_folder_only: bool = True) -> Tuple[Dict, Dict]:
        """Find all duplicates"""
        print("Finding duplicates by filename (same folder only)...")
        name_dups = self.find_duplicates_by_name(same_folder_only=same_folder_only)
        self.stats['duplicate_names'] = len(name_dups)
        total_dup_files = sum(len(v) for v in name_dups.values())
        print(f"  Found {len(name_dups)} folders with duplicate filenames ({total_dup_files} total duplicate files)")
        
        content_dups = {}
        if check_content:
            print("Finding duplicates by content hash...")
            content_dups = self.find_duplicates_by_content(sample_size=sample_size)
            self.stats['duplicate_content'] = len(content_dups)
            total_content_dups = sum(len(v) for v in content_dups.values())
            print(f"  Found {len(content_dups)} duplicate content groups ({total_content_dups} total files)")
        
        return name_dups, content_dups


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Find duplicate files in QiOS vault')
    parser.add_argument('--root', default='realms/qivault/kb',
                       help='Root directory to scan')
    parser.add_argument('--folder', default=None,
                       help='Specific folder to scan (relative to root)')
    parser.add_argument('--check-content', action='store_true',
                       help='Also check for duplicate content (slower)')
    parser.add_argument('--sample-size', type=int, default=None,
                       help='Limit content hash checking to first N files (for speed)')
    parser.add_argument('--output', default=None,
                       help='Output report file path (default: _DUPLICATES_REPORT.md in root)')
    
    args = parser.parse_args()
    
    root = Path(args.root)
    if args.folder:
        root = root / args.folder
    
    finder = DuplicateFinder(root)
    
    print("=" * 60)
    print("QIOS DUPLICATE FINDER")
    print("=" * 60)
    print(f"Scanning: {root}")
    print(f"Check content: {args.check_content}")
    print()
    
    name_dups, content_dups = finder.find_duplicates(
        check_content=args.check_content,
        sample_size=args.sample_size
    )
    
    # Generate report
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = root / "_DUPLICATES_REPORT.md"
    
    report = finder.generate_report(name_dups, content_dups, output_path)
    output_path.write_text(report, encoding='utf-8')
    
    print()
    print("=" * 60)
    print("REPORT GENERATED")
    print("=" * 60)
    print(f"Output: {output_path}")
    print(f"Files scanned: {finder.stats['files_scanned']}")
    print(f"Duplicate names: {finder.stats['duplicate_names']}")
    print(f"Duplicate content: {finder.stats['duplicate_content']}")
    print(f"Errors: {finder.stats['errors']}")


if __name__ == '__main__':
    main()

