"""Merge & deduplicate client_Client Docs CSVs, then move originals to trash."""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
from pathlib import Path

QISYSTEM = Path("C:/QiLabs/20_QiSystem")
TRASH = Path("C:/QiLabs/20_QiSystem/_trash_client_docs")
OUTPUT = QISYSTEM / "client_Client Docs.csv"

# Column order for the merged output (matches base file + numbered set)
CANONICAL_COLS = ["Name", "Tags", "ROOT FOLDER", "Docs/Folder"]

# Map "all"-set headers to canonical names
ALL_COL_MAP = {
    "Name": "Name",
    "Docs/Folder": "Docs/Folder",
    "ROOT FOLDER": "ROOT FOLDER",
    "Tags": "Tags",
}


def normalized_rows(path: Path):
    """Yield dicts with canonical columns from any variant CSV."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return
        actual = [c.strip() for c in reader.fieldnames]

        # Detect "all" variant by column order
        if actual == ["Name", "Docs/Folder", "ROOT FOLDER", "Tags"]:
            col_map = ALL_COL_MAP
        elif actual == CANONICAL_COLS:
            col_map = {c: c for c in CANONICAL_COLS}
        else:
            # Unknown header — skip
            return

        for row in reader:
            out = {}
            for c in CANONICAL_COLS:
                val = row.get(col_map[c], "")
                out[c] = val.strip() if val else ""
            yield out


def row_fingerprint(row: dict) -> str:
    """SHA-256 of the concatenated column values."""
    raw = "|".join(row.get(c, "") for c in CANONICAL_COLS).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main():
    # Collect all CSV paths
    all_csvs = sorted(
        [p for p in QISYSTEM.glob("*client*Client*Docs*.csv") if p.is_file()]
    )
    if not all_csvs:
        print("No files to process.")
        return

    print(f"Found {len(all_csvs)} CSV files to merge.")

    # ── 1. Read & merge ──────────────────────────────────────────────
    seen: set[str] = set()
    merged_rows: list[dict] = []
    total_read = 0

    for path in all_csvs:
        before = len(merged_rows)
        for row in normalized_rows(path):
            total_read += 1
            fp = row_fingerprint(row)
            if fp not in seen:
                seen.add(fp)
                merged_rows.append(row)
        after = len(merged_rows)
        print(f"  {path.name}: {after - before:>4} new rows ({total_read} total read)")

    print(f"\nMerged {len(merged_rows)} unique rows from {total_read} total reads.")

    # ── 2. Write merged CSV ──────────────────────────────────────────
    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_COLS)
        writer.writeheader()
        writer.writerows(merged_rows)

    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")

    # ── 3. Move originals to trash (excluding the freshly written merged file) ──
    TRASH.mkdir(parents=True, exist_ok=True)
    moved = 0
    for path in all_csvs:
        if path.resolve() == OUTPUT.resolve():
            continue  # skip the merged output we just wrote
        dest = TRASH / path.name
        if dest.exists():
            stem = path.stem
            suffix = path.suffix
            counter = 1
            while dest.exists():
                dest = TRASH / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.move(str(path), str(dest))
        moved += 1

    print(f"Moved {moved} original files to {TRASH}")


if __name__ == "__main__":
    main()
