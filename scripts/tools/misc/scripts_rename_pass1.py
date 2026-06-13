from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path.cwd()


def log(msg: str) -> None:
    print(msg)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst: Path) -> None:
    if not src.exists():
        log(f"[skip] missing: {src}")
        return

    ensure_dir(dst.parent)

    if dst.exists():
        log(f"[skip] destination exists: {dst}")
        return

    log(f"[move] {src} -> {dst}")
    shutil.move(str(src), str(dst))


def remove_dir_if_empty(path: Path) -> None:
    if not path.exists():
        log(f"[skip] missing dir: {path}")
        return
    if path.is_dir() and not any(path.iterdir()):
        log(f"[rmdir] removing empty dir: {path}")
        path.rmdir()
    else:
        log(f"[keep] not empty: {path}")


def main() -> None:
    manifest_path = ROOT / "tools" / "misc" / "scripts_rename_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    for rel in manifest.get("create_dirs", []):
        ensure_dir(ROOT / rel)
        log(f"[mkdir] {rel}")

    for item in manifest.get("moves", []):
        safe_move(ROOT / item["from"], ROOT / item["to"])

    for item in manifest.get("renames", []):
        safe_move(ROOT / item["from"], ROOT / item["to"])

    for rel in manifest.get("remove_empty_dirs", []):
        remove_dir_if_empty(ROOT / rel)

    log("\n[done] rename pass complete.")


if __name__ == "__main__":
    main()