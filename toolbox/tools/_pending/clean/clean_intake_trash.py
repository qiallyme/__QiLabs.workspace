#!/usr/bin/env python3
"""
Cleanup script to empty all `_intake` and `.trash` directories
under specific top-level scopes (realms, data, _intake), while
ignoring tooling/noise directories.

- Only affects directories named exactly "_intake" or ".trash".
- Only when they are under top-level: realms, data, _intake.
- Keeps the directory itself, deletes its contents (files + subdirs).
- Has a DRY_RUN flag so you can see what would be cleaned.
"""

import os
from pathlib import Path
import shutil

# --- CONFIG ---

# Run once in DRY_RUN=True to inspect, then set to False to actually delete.
DRY_RUN = True

# Top-level dirs we care about for cleanup
TARGET_TOP_LEVELS = {"realms", "data", "_intake"}

# Top-level dirs we want to completely ignore
IGNORED_TOP_LEVELS = {
    "apps",
    "workers",
    ".git",
    "sites",
    "node_modules",
    "components",
    "tools",
    "templates",
    "logs",
    "",
    ".cursor",
    "docs",
    ".vscode",
}

# Directory names we want to empty (when under a target top-level)
TARGET_DIR_NAMES = {".trash", "_intake"}


# --- LOGIC ---

def empty_directory(dir_path: Path) -> tuple[int, int]:
    """
    Empty all files and subdirectories under dir_path, but keep dir_path itself.

    Returns: (file_count_deleted, dir_count_deleted)
    """
    files_deleted = 0
    dirs_deleted = 0

    # We want to delete contents, so we iterate direct children
    for child in dir_path.iterdir():
        try:
            if child.is_file() or child.is_symlink():
                if not DRY_RUN:
                    child.unlink()
                files_deleted += 1
            elif child.is_dir():
                if not DRY_RUN:
                    shutil.rmtree(child)
                dirs_deleted += 1
        except Exception as e:
            print(f"[ERROR] Failed to delete {child}: {e}")

    return files_deleted, dirs_deleted


def main() -> None:
    root = Path(__file__).resolve().parent
    print(f"QiOS root: {root}")

    candidate_dirs: list[Path] = []

    # Walk the whole tree, but prune ignored top-levels
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        # Determine top-level directory name
        try:
            rel = current.relative_to(root)
        except ValueError:
            # Shouldn't happen
            continue

        parts = rel.parts
        if not parts:
            top_level = "<root>"
        else:
            top_level = parts[0]

        # Prune ignored top-levels
        if top_level in IGNORED_TOP_LEVELS:
            dirnames[:] = []  # don't descend further
            continue

        # Only descend into target top-levels + their subdirs
        if top_level not in TARGET_TOP_LEVELS:
            dirnames[:] = []  # stop descending here
            continue

        # Check if this directory itself is one of the target names
        if current.name in TARGET_DIR_NAMES:
            candidate_dirs.append(current)

    if not candidate_dirs:
        print("No `_intake` or `.trash` directories found under target scopes.")
        return

    print("\n=== CANDIDATE DIRECTORIES TO EMPTY ===")
    for d in candidate_dirs:
        print(f"  - {d.relative_to(root)}")

    print(f"\nTotal candidate dirs: {len(candidate_dirs)}")
    print(f"DRY_RUN = {DRY_RUN}")
    if DRY_RUN:
        print("\nNo deletions performed. Set DRY_RUN = False to actually empty these directories.")
        return

    # Actually empty them
    total_files = 0
    total_dirs = 0

    print("\n=== EMPTYING DIRECTORIES ===")
    for d in candidate_dirs:
        files_deleted, dirs_deleted = empty_directory(d)
        total_files += files_deleted
        total_dirs += dirs_deleted
        print(f"Emptied {d.relative_to(root)} -> {files_deleted} files, {dirs_deleted} subdirs deleted.")

    print("\n=== SUMMARY ===")
    print(f"Directories emptied: {len(candidate_dirs)}")
    print(f"Files deleted:       {total_files}")
    print(f"Subdirs deleted:     {total_dirs}")


if __name__ == "__main__":
    main()
