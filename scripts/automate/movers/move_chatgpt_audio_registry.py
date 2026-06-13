#!/usr/bin/env python3
"""
Using file_registry.json, find ChatGPT-style audio files (file_00000000*.wav)
ANYWHERE in the repo and move them into .trash/chatgpt_audio_purge.

- Matches:
    extension == "wav" (case-insensitive)
    filename starts with "file_00000000" (case-insensitive)
- Only moves files; does NOT delete anything.
"""

import json
import sys
from pathlib import Path
import shutil

REGISTRY_FILENAME = "file_registry.json"
TRASH_DIRNAME = ".trash"
PURGE_SUBDIR = "chatgpt_audio_purge"


def is_chatgpt_audio(filename: str, extension: str) -> bool:
    """
    Determine if a file looks like a ChatGPT audio file we want to purge.
    Rule:
      - extension == "wav"
      - filename starts with "file_00000000"
    """
    if not filename:
        return False
    ext = (extension or "").lower()
    if ext != "wav":
        return False
    name_lower = filename.lower()
    return name_lower.startswith("file_00000000")


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

    # Ensure .trash and purge dir exist
    trash_root = root / TRASH_DIRNAME
    trash_root.mkdir(parents=True, exist_ok=True)

    purge_dir = trash_root / PURGE_SUBDIR
    purge_dir.mkdir(parents=True, exist_ok=True)

    candidates = []

    for f in files:
        rel_path = f.get("path")
        if not rel_path:
            continue
        filename = (f.get("filename") or "").strip()
        ext = (f.get("extension") or "").strip().lower()

        if is_chatgpt_audio(filename, ext):
            candidates.append(rel_path)

    # Deduplicate and sort for stable output
    candidates = sorted(set(candidates))

    print(f"Found {len(candidates)} ChatGPT-style audio files to move.")
    if not candidates:
        return

    moved = 0
    skipped_missing = 0

    for rel in candidates:
        src = (root / rel).resolve()
        if not src.exists():
            skipped_missing += 1
            continue

        # If it's already in the purge_dir, skip
        try:
            rel_to_trash = src.relative_to(trash_root)
            if rel_to_trash.parts and rel_to_trash.parts[0] == PURGE_SUBDIR:
                # Already where we want it
                continue
        except ValueError:
            # Not under .trash, proceed
            pass

        dest = purge_dir / src.name
        counter = 1
        while dest.exists():
            dest = purge_dir / f"{src.stem}_{counter}{src.suffix}"
            counter += 1

        try:
            shutil.move(str(src), str(dest))
            moved += 1
            print(f"Moved {rel} -> {dest.relative_to(root)}")
        except Exception as e:
            print(f"[ERROR] Failed to move {rel}: {e}")

    print("\n=== SUMMARY ===")
    print(f"Total candidates from registry: {len(candidates)}")
    print(f"Moved:                           {moved}")
    print(f"Missing at time of move:         {skipped_missing}")
    print("ChatGPT audio now centralized in .trash/chatgpt_audio_purge.")


if __name__ == "__main__":
    main()
