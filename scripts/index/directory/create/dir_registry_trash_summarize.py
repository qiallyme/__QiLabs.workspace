#!/usr/bin/env python3
"""
Summarize .trash contents from file_registry.json by extension.
No files are moved or modified.
"""

import json
import sys
from pathlib import Path
from collections import Counter

REGISTRY_FILENAME = "file_registry.json"
TRASH_DIRNAME = ".trash"


def main() -> None:
    root = Path(__file__).resolve().parent
    registry_path = root / REGISTRY_FILENAME

    if not registry_path.exists():
        print(f"[ERROR] {REGISTRY_FILENAME} not found at {registry_path}")
        sys.exit(1)

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to read {registry_path}: {e}")
        sys.exit(1)

    files = data.get("files", [])
    if not isinstance(files, list):
        print("[ERROR] 'files' key in registry is not a list")
        sys.exit(1)

    total_trash = 0
    ext_counts = Counter()
    parent_counts = Counter()

    for f in files:
        if not f.get("is_trash"):
            continue

        rel_path = f.get("path")
        if not rel_path:
            continue

        total_trash += 1
        ext = (f.get("extension") or "").lower()
        ext_counts[ext] += 1

        parent_dir = (f.get("parent_dir") or "").split("/")
        parent_root = parent_dir[0] if parent_dir and parent_dir[0] else TRASH_DIRNAME
        parent_counts[parent_root] += 1

    print("=== .trash SUMMARY ===")
    print(f"Total .trash files in registry: {total_trash}")
    print()

    print("Top extensions in .trash:")
    for ext, count in ext_counts.most_common(30):
        label = ext if ext else "<no extension>"
        print(f"  {label:15} {count:6}")

    print()
    print("Top parent dirs under .trash:")
    for parent, count in parent_counts.most_common():
        print(f"  {parent:20} {count:6}")


if __name__ == "__main__":
    main()
