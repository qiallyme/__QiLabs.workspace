import os
from pathlib import Path
import zipfile
import sys
import itertools


# -------- CONFIG --------
# Default root is ~/Downloads; you can override via CLI argument or prompt.
MAX_NAME_LEN = 30  # max characters for the base filename (without extension)
# ------------------------


def truncate_name(stem: str, max_len: int = MAX_NAME_LEN) -> str:
    """Truncate a filename stem to max_len characters."""
    if len(stem) <= max_len:
        return stem
    return stem[:max_len]


def unique_path(base: Path) -> Path:
    """
    If 'base' exists, append _1, _2, etc. until it's unique.
    Works for both files and folders.
    """
    if not base.exists():
        return base

    stem = base.stem
    suffix = base.suffix
    parent = base.parent

    for i in itertools.count(1):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate


def rename_zip(zip_path: Path) -> Path:
    """
    Truncate the filename (stem) to MAX_NAME_LEN, keep .zip extension,
    and ensure the new name is unique.
    Returns the new path (which may be unchanged if no rename needed).
    """
    parent = zip_path.parent
    old_stem = zip_path.stem
    new_stem = truncate_name(old_stem, MAX_NAME_LEN)

    new_path = parent / f"{new_stem}.zip"
    new_path = unique_path(new_path)

    if new_path != zip_path:
        zip_path.rename(new_path)

    return new_path


def extract_zip(zip_path: Path):
    """
    Extract a zip file into a folder with the same base name (no .zip).
    Deletes the zip afterwards.
    """
    # Ensure filename is truncated & clean first
    zip_path = rename_zip(zip_path)

    # Folder name = same as zip stem
    dest_dir = zip_path.with_suffix("")  # remove .zip
    dest_dir = unique_path(dest_dir)

    print(f"\n[+] Extracting: {zip_path}")
    print(f"    -> {dest_dir}")

    dest_dir.mkdir(parents=True, exist_ok=False)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
    except zipfile.BadZipFile:
        print(f"    [!] Skipping bad zip file: {zip_path}")
        # If you want to keep bad zips for later inspection, comment out the unlink below.
        zip_path.unlink(missing_ok=True)
        return
    except Exception as e:
        print(f"    [!] Error extracting {zip_path}: {e}")
        # Decide whether to delete or keep the zip on extraction error
        return

    # Delete the original zip
    zip_path.unlink(missing_ok=True)
    print(f"    [✓] Deleted zip: {zip_path}")


def find_all_zips(root: Path):
    """Yield all .zip files under root (recursive)."""
    return list(root.rglob("*.zip"))


def process_all_zips(root: Path):
    """
    Repeatedly scan for zip files under root and extract them
    until no zip files remain.
    """
    root = root.resolve()
    print(f"Root directory: {root}")

    if not root.exists():
        print(f"[!] Root path does not exist: {root}")
        return

    round_num = 0

    while True:
        round_num += 1
        zips = find_all_zips(root)
        if not zips:
            print("\nNo more zip files found. We’re done here.")
            break

        print(f"\n=== Round {round_num}: Found {len(zips)} zip file(s) ===")
        for zip_path in zips:
            extract_zip(zip_path)


if __name__ == "__main__":
    # Get default Downloads folder
    default_downloads = Path.home() / "Downloads"
    
    # Allow optional CLI arg: python unzip_downloads.py "C:\path\to\folder"
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1]).expanduser()
    else:
        # Prompt user with default Downloads folder
        default_path = str(default_downloads)
        user_input = input(f"Enter path to process (default: {default_path}): ").strip()
        
        if user_input:
            root_dir = Path(user_input).expanduser()
        else:
            root_dir = default_downloads

    process_all_zips(root_dir)
