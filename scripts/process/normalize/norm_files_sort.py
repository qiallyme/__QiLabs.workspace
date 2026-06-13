"""
Interactive File Sorter

A robust command-line tool to help organize files by type, detect duplicates,
and move files into organized inbox folders.

Usage:
    python interactive_file_sorter.py [directory_path]

If no directory is provided, uses the configured BASE_SCAN_DIR.
"""

import hashlib
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# === CONFIGURATION ===

BASE_SCAN_DIR = r"C:\QiOS\_inbox"  # default scan directory (can be overridden via CLI/input)

QIVAULT_INBOX = r"C:\QiOS\qivault\_inbox"

ASSETS_INBOX = r"C:\QiOS\assets\_inbox"

DATA_INBOX = r"C:\QiOS\data\_inbox"

DRY_RUN_DEFAULT = True  # default to dry-run to avoid accidental moves

# ======================


@dataclass
class FileRecord:
    """Represents a file with its metadata."""
    path: Path
    size: int
    extension: str
    category: str  # "markdown", "media", "spreadsheet", "other"
    hash: Optional[str] = None  # computed lazily when needed


# File type classification
MARKDOWN_EXTENSIONS = {'.md'}
MEDIA_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
    # Audio
    '.mp3', '.wav', '.m4a', '.ogg', '.flac',
    # Video
    '.mp4', '.mov', '.mkv', '.avi', '.webm'
}
SPREADSHEET_EXTENSIONS = {'.csv', '.tsv', '.xls', '.xlsx', '.ods'}


def classify_file(extension: str) -> str:
    """Classify a file by its extension."""
    ext_lower = extension.lower()
    if ext_lower in MARKDOWN_EXTENSIONS:
        return "markdown"
    elif ext_lower in MEDIA_EXTENSIONS:
        return "media"
    elif ext_lower in SPREADSHEET_EXTENSIONS:
        return "spreadsheet"
    else:
        return "other"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file's contents."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (IOError, OSError) as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def scan_files(base_dir: Path, recursive: bool = True) -> list[FileRecord]:
    """
    Scan a directory for files and return a list of FileRecord objects.
    
    Args:
        base_dir: Directory to scan
        recursive: Whether to scan subdirectories
        
    Returns:
        List of FileRecord objects
    """
    file_records = []
    
    if not base_dir.exists():
        print(f"Error: Directory {base_dir} does not exist.")
        return file_records
    
    if not base_dir.is_dir():
        print(f"Error: {base_dir} is not a directory.")
        return file_records
    
    pattern = "**/*" if recursive else "*"
    
    try:
        for file_path in base_dir.glob(pattern):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    extension = file_path.suffix
                    category = classify_file(extension)
                    file_records.append(FileRecord(
                        path=file_path,
                        size=size,
                        extension=extension,
                        category=category
                    ))
                except (OSError, PermissionError) as e:
                    print(f"Warning: Could not access {file_path}: {e}")
    except Exception as e:
        print(f"Error scanning directory: {e}")
    
    return file_records


def group_duplicates(file_records: list[FileRecord]) -> list[list[FileRecord]]:
    """
    Group files by size, then by hash to find exact duplicates.
    
    Returns:
        List of groups, where each group contains duplicate files
    """
    # Stage 1: Group by size
    size_groups = defaultdict(list)
    for record in file_records:
        size_groups[record.size].append(record)
    
    # Stage 2: For same-size groups, compute hash and group by hash
    duplicate_groups = []
    for size, records in size_groups.items():
        if len(records) > 1:
            # Compute hashes for same-size files
            hash_groups = defaultdict(list)
            for record in records:
                if record.hash is None:
                    record.hash = compute_file_hash(record.path)
                if record.hash:
                    hash_groups[record.hash].append(record)
            
            # Add groups with multiple files (duplicates)
            for hash_val, group in hash_groups.items():
                if len(group) > 1:
                    duplicate_groups.append(group)
    
    return duplicate_groups


def normalize_filename(name: str) -> str:
    """Normalize filename by lowercasing and removing punctuation/numbers."""
    import re
    # Remove extension, lowercase, remove punctuation and numbers
    base = Path(name).stem.lower()
    normalized = re.sub(r'[^a-z]', '', base)
    return normalized


def group_similar_names(file_records: list[FileRecord]) -> list[list[FileRecord]]:
    """
    Group files with similar names in the same directory.
    
    Returns:
        List of groups with similar normalized names in the same folder
    """
    # Group by directory and normalized name
    similar_groups = defaultdict(list)
    
    for record in file_records:
        dir_path = record.path.parent
        normalized = normalize_filename(record.path.name)
        if normalized:  # Only group if normalized name is not empty
            key = (dir_path, normalized)
            similar_groups[key].append(record)
    
    # Return only groups with multiple files
    return [group for group in similar_groups.values() if len(group) > 1]


def get_inbox_path(category: str) -> Optional[Path]:
    """Get the inbox path for a given category."""
    category_map = {
        "markdown": QIVAULT_INBOX,
        "media": ASSETS_INBOX,
        "spreadsheet": DATA_INBOX
    }
    inbox_path_str = category_map.get(category)
    if inbox_path_str:
        return Path(inbox_path_str)
    return None


def ensure_inbox_exists(inbox_path: Path) -> bool:
    """Ensure an inbox directory exists, creating it if necessary."""
    try:
        inbox_path.mkdir(parents=True, exist_ok=True)
        return True
    except (OSError, PermissionError) as e:
        print(f"Error creating inbox directory {inbox_path}: {e}")
        return False


def move_files_by_type(file_records: list[FileRecord], dry_run: bool = True) -> dict:
    """
    Move files to their respective inbox folders based on type.
    
    Args:
        file_records: List of files to move
        dry_run: If True, only show what would be moved
    
    Returns:
        Dictionary with move results
    """
    results = {
        "moved": 0,
        "skipped": 0,
        "errors": 0,
        "other_files": 0
    }
    
    # Filter out "other" category files
    files_to_move = [f for f in file_records if f.category != "other"]
    other_files = [f for f in file_records if f.category == "other"]
    results["other_files"] = len(other_files)
    
    # Group by category
    by_category = defaultdict(list)
    for record in files_to_move:
        by_category[record.category].append(record)
    
    # Process each category
    for category, records in by_category.items():
        inbox_path = get_inbox_path(category)
        if not inbox_path:
            continue
        
        if not dry_run:
            if not ensure_inbox_exists(inbox_path):
                print(f"Could not create inbox for {category}, skipping...")
                results["errors"] += len(records)
                continue
        
        for record in records:
            try:
                dest_path = inbox_path / record.path.name
                
                # Handle name conflicts
                counter = 1
                original_dest = dest_path
                while dest_path.exists():
                    stem = original_dest.stem
                    suffix = original_dest.suffix
                    dest_path = inbox_path / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                if dry_run:
                    print(f"[DRY-RUN] Would move: {record.path} → {dest_path}")
                else:
                    shutil.move(str(record.path), str(dest_path))
                    print(f"Moved: {record.path.name} → {dest_path}")
                
                results["moved"] += 1
            except (OSError, PermissionError, shutil.Error) as e:
                print(f"Error moving {record.path}: {e}")
                results["errors"] += 1
    
    return results


def print_summary(file_records: list[FileRecord], duplicate_groups: list, similar_groups: list):
    """Print a summary of scanned files."""
    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)
    print(f"Total files scanned: {len(file_records)}")
    
    # Count by category
    by_category = defaultdict(int)
    for record in file_records:
        by_category[record.category] += 1
    
    print(f"\nFiles by category:")
    print(f"  Markdown:    {by_category['markdown']}")
    print(f"  Media:       {by_category['media']}")
    print(f"  Spreadsheets: {by_category['spreadsheet']}")
    print(f"  Other:       {by_category['other']}")
    
    print(f"\nDuplicate groups found: {len(duplicate_groups)}")
    print(f"Similar-name groups found: {len(similar_groups)}")
    print("=" * 60 + "\n")


def review_duplicates(duplicate_groups: list[list[FileRecord]], dry_run: bool) -> int:
    """Interactive review of duplicate files."""
    if not duplicate_groups:
        print("No duplicate groups found.")
        return 0
    
    deleted_count = 0
    
    for idx, group in enumerate(duplicate_groups, 1):
        print(f"\n--- Duplicate Group {idx}/{len(duplicate_groups)} ---")
        for i, record in enumerate(group, 1):
            print(f"  [{i}] {record.path}")
            print(f"      Size: {record.size:,} bytes")
            if record.hash:
                print(f"      Hash: {record.hash[:16]}...")
        
        print("\nOptions:")
        print("  [1-N] Keep file number N, delete others")
        print("  [s]kip - Skip this group")
        print("  [a]uto - Keep first, delete others")
        print("  [q]uit - Exit duplicate review")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 's':
            continue
        elif choice == 'a':
            # Auto: keep first, delete others
            keep_file = group[0]
            for record in group[1:]:
                if delete_file(record, dry_run):
                    deleted_count += 1
        elif choice.isdigit():
            file_idx = int(choice) - 1
            if 0 <= file_idx < len(group):
                keep_file = group[file_idx]
                for i, record in enumerate(group):
                    if i != file_idx:
                        if delete_file(record, dry_run):
                            deleted_count += 1
            else:
                print("Invalid file number.")
        else:
            print("Invalid choice.")
    
    return deleted_count


def delete_file(record: FileRecord, dry_run: bool) -> bool:
    """Delete a file with confirmation."""
    if dry_run:
        print(f"[DRY-RUN] Would delete: {record.path}")
        return True
    
    confirm = input(f"Type 'DELETE' to confirm deletion of {record.path.name}: ").strip()
    if confirm == "DELETE":
        try:
            record.path.unlink()
            print(f"Deleted: {record.path}")
            return True
        except (OSError, PermissionError) as e:
            print(f"Error deleting {record.path}: {e}")
            return False
    else:
        print("Deletion cancelled.")
        return False


def review_similar_names(similar_groups: list[list[FileRecord]]):
    """Interactive review of similar-name files."""
    if not similar_groups:
        print("No similar-name groups found.")
        return
    
    for idx, group in enumerate(similar_groups, 1):
        print(f"\n--- Similar Name Group {idx}/{len(similar_groups)} ---")
        for i, record in enumerate(group, 1):
            print(f"  [{i}] {record.path.name} ({record.path.parent})")
        
        print("\nOptions:")
        print("  [k]eep all - Keep all files")
        print("  [r]eview as duplicates - Mark some as duplicates")
        print("  [s]kip - Ignore this group")
        print("  [q]uit - Exit similar-name review")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 's':
            continue
        elif choice == 'k':
            print("Keeping all files in this group.")
        elif choice == 'r':
            # Treat as duplicates
            print("Reviewing as duplicates...")
            review_duplicates([group], False)  # Reuse duplicate review
        else:
            print("Invalid choice.")


def interactive_menu(file_records: list[FileRecord], dry_run: bool = True):
    """Main interactive menu loop."""
    current_records = file_records
    current_dry_run = dry_run
    
    while True:
        # Recompute groups for current records
        duplicate_groups = group_duplicates(current_records)
        similar_groups = group_similar_names(current_records)
        
        print_summary(current_records, duplicate_groups, similar_groups)
        
        print("What would you like to do?")
        print(f"  [1] Review duplicate files")
        print(f"  [2] Review similar-name files")
        print(f"  [3] Move files by type into inbox folders")
        print(f"  [4] Toggle DRY-RUN mode (currently: {'ON' if current_dry_run else 'OFF'})")
        print(f"  [5] Rescan directory")
        print(f"  [0] Exit")
        
        choice = input("\nYour choice: ").strip()
        
        if choice == '0':
            print("Goodbye!")
            break
        elif choice == '1':
            review_duplicates(duplicate_groups, current_dry_run)
        elif choice == '2':
            review_similar_names(similar_groups)
        elif choice == '3':
            print("\nMoving files by type...")
            results = move_files_by_type(current_records, current_dry_run)
            print(f"\nResults:")
            print(f"  Moved: {results['moved']}")
            print(f"  Errors: {results['errors']}")
            print(f"  Other files (not moved): {results['other_files']}")
            if results['other_files'] > 0:
                print(f"\nNote: {results['other_files']} files classified as 'Other' were not moved.")
                print("      They are listed in the summary above.")
            input("\nPress Enter to continue...")
        elif choice == '4':
            current_dry_run = not current_dry_run
            print(f"DRY-RUN mode is now: {'ON' if current_dry_run else 'OFF'}")
            input("Press Enter to continue...")
        elif choice == '5':
            base_dir = input(f"Enter directory to scan (or press Enter for {BASE_SCAN_DIR}): ").strip()
            if not base_dir:
                base_dir = BASE_SCAN_DIR
            current_records = scan_files(Path(base_dir))
            if not current_records:
                print("No files found or error scanning directory.")
                input("Press Enter to continue...")
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")


def main():
    """Main entry point."""
    import sys
    
    # Get scan directory from command line or use default
    if len(sys.argv) > 1:
        scan_dir = Path(sys.argv[1])
    else:
        scan_dir_input = input(f"Enter directory to scan (or press Enter for {BASE_SCAN_DIR}): ").strip()
        if scan_dir_input:
            scan_dir = Path(scan_dir_input)
        else:
            scan_dir = Path(BASE_SCAN_DIR)
    
    print(f"Scanning directory: {scan_dir}")
    file_records = scan_files(scan_dir)
    
    if not file_records:
        print("No files found in the specified directory.")
        return
    
    print(f"Found {len(file_records)} files.")
    
    # Start interactive menu
    interactive_menu(file_records, DRY_RUN_DEFAULT)


if __name__ == "__main__":
    main()

