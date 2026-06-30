#!/usr/bin/env python3
"""
Build a file registry for the repo for later deduplication / analysis.

- Walks from the current directory.
- Includes .trash (recursively).
- Skips common junk dirs (.git, node_modules, etc.).
- Collects metadata for each file and writes file_registry.json at the repo root.
"""

import os
import sys
import json
import hashlib
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple


EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".venv",
    "__pycache__",
}

REGISTRY_FILENAME = "file_registry.json"


def to_utc_iso(ts: float) -> str:
    """Convert a POSIX timestamp to an ISO 8601 UTC string."""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def calculate_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Calculate SHA-256 hash of a file.

    Reads in chunks to avoid loading large files fully into memory.
    Returns empty string if hashing fails.
    """
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f"[WARN] Failed to hash {path}: {e}", file=sys.stderr)
        return ""


def collect_files(root: Path) -> List[Path]:
    """
    Walk the directory tree under `root`, skipping EXCLUDE_DIRS,
    and return a list of file paths.
    """
    files: List[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Normalize and filter dirnames in-place to control traversal
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        current_dir = Path(dirpath)
        for name in filenames:
            file_path = current_dir / name
            # Just in case: skip registry file itself if you don't want to hash it
            # (comment this out if you *do* want it included)
            if file_path.name == REGISTRY_FILENAME:
                continue
            files.append(file_path)

    return files


def process_one_file(root: Path, path: Path) -> dict[str, Any] | None:
    try:
        rel_path = path.relative_to(root).as_posix()
    except ValueError:
        rel_path = str(path)

    try:
        stat = path.stat()
    except Exception as e:
        print(f"[WARN] Failed to stat {rel_path}: {e}", file=sys.stderr)
        return None

    size_bytes = stat.st_size
    mtime_iso = to_utc_iso(stat.st_mtime)
    ctime_iso = to_utc_iso(stat.st_ctime)

    filename = path.name
    suffix = path.suffix[1:] if path.suffix.startswith(".") else ""
    is_trash = ".trash" in Path(rel_path).parts

    parent = Path(rel_path).parent
    parent_dir = "" if parent == Path(".") else parent.as_posix()

    parts = Path(rel_path).parts
    top_level_dir = parts[0] if len(parts) > 1 else ""

    sha256 = calculate_sha256(path)
    if not sha256:
        return None

    return {
        "path": rel_path,
        "filename": filename,
        "extension": suffix,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "mtime": mtime_iso,
        "ctime": ctime_iso,
        "is_trash": is_trash,
        "top_level_dir": top_level_dir,
        "parent_dir": parent_dir,
    }


def build_registry(root: Path, max_workers: int | None = None) -> Dict[str, Any]:
    """
    Build the registry structure:
    {
      "files": [ { ...metadata... }, ... ],
      "by_hash": { "<sha256>": ["path1", "path2", ...] }
    }
    """
    all_files = collect_files(root)
    total_files = len(all_files)
    print(f"Discovered {total_files} files (excluding {', '.join(sorted(EXCLUDE_DIRS))}).")

    files_meta: List[Dict[str, Any]] = []
    by_hash: Dict[str, List[str]] = {}

    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 4))

    print(f"Hashing with up to {max_workers} worker threads...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one_file, root, path): path for path in all_files}

        for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            if idx % 100 == 0 or idx == total_files:
                print(f"  Processed {idx}/{total_files} files...")

            record = future.result()
            if record is None:
                continue

            files_meta.append(record)
            sha256 = record["sha256"]
            by_hash.setdefault(sha256, []).append(record["path"])

    registry = {
        "files": files_meta,
        "by_hash": by_hash,
    }
    return registry


def main() -> None:
    root = Path(".").resolve()
    print(f"Building file registry for repo root: {root}")

    registry = build_registry(root)

    output_path = root / REGISTRY_FILENAME
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write {output_path}: {e}", file=sys.stderr)
        sys.exit(1)

    num_files = len(registry["files"])
    num_hashes = len(registry["by_hash"])

    # Count trash vs non-trash for a quick sanity check
    trash_count = sum(1 for f in registry["files"] if f.get("is_trash"))
    non_trash_count = num_files - trash_count

    print("\n" + "=" * 60)
    print("FILE REGISTRY SUMMARY")
    print("=" * 60)
    print(f"Registry file:        {output_path}")
    print(f"Total files indexed:  {num_files}")
    print(f"Unique hashes:        {num_hashes}")
    print(f"Files in .trash:      {trash_count}")
    print(f"Files outside .trash: {non_trash_count}")
    print("=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
