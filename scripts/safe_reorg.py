#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Dict, Iterable, List, Optional


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def same_file(a: Path, b: Path) -> bool:
    if not a.exists() or not b.exists() or not a.is_file() or not b.is_file():
        return False
    if a.stat().st_size != b.stat().st_size:
        return False
    return sha256_file(a) == sha256_file(b)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rel_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def is_subpath(path: Path, maybe_parent: Path) -> bool:
    try:
        path.resolve().relative_to(maybe_parent.resolve())
        return True
    except Exception:
        return False


class Logger:
    def __init__(self, root: Path, op_name: str):
        self.root = root
        self.op_name = op_name
        self.stamp = now_stamp()
        self.run_dir = root / ".trash" / self.stamp
        self.logs_dir = self.run_dir / "_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.logs_dir / "manifest.jsonl"
        self.summary_path = self.logs_dir / "summary.csv"
        self.rows: List[Dict[str, str]] = []

    def log(self, **row: str) -> None:
        row = {k: ("" if v is None else str(v)) for k, v in row.items()}
        with self.manifest_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.rows.append(row)

    def write_summary(self) -> None:
        if not self.rows:
            return
        keys: List[str] = sorted({k for row in self.rows for k in row.keys()})
        with self.summary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.rows)


SAFE_RENAME_SUFFIX = "__MERGE_CONFLICT__"


def unique_conflict_path(path: Path) -> Path:
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 1
    candidate = parent / f"{stem}{SAFE_RENAME_SUFFIX}{suffix}"
    while candidate.exists():
        i += 1
        candidate = parent / f"{stem}{SAFE_RENAME_SUFFIX}_{i}{suffix}"
    return candidate


def move_item(src: Path, dst: Path, dry_run: bool, logger: Logger, reason: str, action: str) -> None:
    ensure_parent(dst)
    logger.log(action=action, reason=reason, src=str(src), dst=str(dst))
    if not dry_run:
        shutil.move(str(src), str(dst))


def trash_destination(src: Path, root: Path, logger: Logger) -> Path:
    return logger.run_dir / "trash" / rel_to_root(src, root)


def apply_trash(root: Path, item: Dict, dry_run: bool, logger: Logger) -> None:
    path = root / item["source"]
    if not path.exists():
        logger.log(action="skip_missing", reason=item.get("reason", ""), src=str(path), dst="")
        return
    dst = trash_destination(path, root, logger)
    move_item(path, dst, dry_run, logger, item.get("reason", ""), "trash")


def apply_merge_dir(root: Path, item: Dict, dry_run: bool, logger: Logger) -> None:
    src = root / item["source"]
    dst = root / item["target"]
    if not src.exists():
        logger.log(action="skip_missing", reason=item.get("reason", ""), src=str(src), dst=str(dst))
        return
    if not src.is_dir():
        logger.log(action="skip_not_dir", reason=item.get("reason", ""), src=str(src), dst=str(dst))
        return
    dst.mkdir(parents=True, exist_ok=True)
    for child in sorted(src.rglob("*")):
        rel = child.relative_to(src)
        target_path = dst / rel
        if child.is_dir():
            if not dry_run:
                target_path.mkdir(parents=True, exist_ok=True)
            continue
        if target_path.exists():
            if target_path.is_file() and same_file(child, target_path):
                dup_dst = logger.run_dir / "duplicates" / rel_to_root(child, root)
                move_item(child, dup_dst, dry_run, logger, item.get("reason", ""), "merge_duplicate_to_trash")
            else:
                conflict_dst = unique_conflict_path(target_path)
                move_item(child, conflict_dst, dry_run, logger, item.get("reason", ""), "merge_conflict_copy")
        else:
            move_item(child, target_path, dry_run, logger, item.get("reason", ""), "merge_move")
    # if source tree is empty afterwards, trash it
    if src.exists():
        try:
            remaining = [p for p in src.rglob("*") if p.exists()]
        except FileNotFoundError:
            remaining = []
        if not remaining:
            dst_trash = trash_destination(src, root, logger)
            move_item(src, dst_trash, dry_run, logger, item.get("reason", ""), "merge_empty_source_to_trash")


def path_matches_any(rel_path: str, patterns: Iterable[str]) -> bool:
    rp = rel_path.replace("\\", "/")
    return any(fnmatch.fnmatch(rp, pat) for pat in patterns)


def scan_candidates(root: Path, patterns: List[str], ignore: List[str], logger: Logger, dry_run: bool) -> None:
    for path in sorted(root.rglob("*")):
        rel = rel_to_root(path, root)
        if rel.startswith(".trash/"):
            continue
        if path_matches_any(rel, ignore):
            continue
        if path_matches_any(rel, patterns):
            dst = trash_destination(path, root, logger)
            logger.log(action="scan_match", reason="scan", src=str(path), dst=str(dst))
            if not dry_run:
                ensure_parent(dst)
                shutil.move(str(path), str(dst))


def restore_from_manifest(manifest: Path, dry_run: bool) -> None:
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    # reverse order so children restore before parents not required but okay
    for row in reversed(rows):
        action = row.get("action", "")
        src = Path(row.get("src", ""))
        dst = Path(row.get("dst", ""))
        if action.startswith("skip"):
            continue
        if not dst.exists():
            continue
        if src.exists():
            # avoid overwrite during restore
            restore_target = unique_conflict_path(src)
        else:
            restore_target = src
        print(f"RESTORE {dst} -> {restore_target}")
        if not dry_run:
            ensure_parent(restore_target)
            shutil.move(str(dst), str(restore_target))


def load_plan(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Plan must be valid JSON. {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe move-only repo reorg tool with .trash quarantine and restore support.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ap_apply = sub.add_parser("apply", help="Apply a JSON plan.")
    ap_apply.add_argument("--root", required=True, help="Repo or workspace root.")
    ap_apply.add_argument("--plan", required=True, help="Path to JSON plan.")
    ap_apply.add_argument("--execute", action="store_true", help="Actually move files. Default is dry-run.")

    ap_scan = sub.add_parser("scan-trash", help="Move files matching glob patterns into .trash.")
    ap_scan.add_argument("--root", required=True)
    ap_scan.add_argument("--patterns", nargs="+", required=True)
    ap_scan.add_argument("--ignore", nargs="*", default=[])
    ap_scan.add_argument("--execute", action="store_true")

    ap_restore = sub.add_parser("restore", help="Restore from manifest.jsonl.")
    ap_restore.add_argument("--manifest", required=True)
    ap_restore.add_argument("--execute", action="store_true")

    args = parser.parse_args()

    if args.cmd == "restore":
        restore_from_manifest(Path(args.manifest), dry_run=not args.execute)
        return 0

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found: {root}")

    if args.cmd == "scan-trash":
        logger = Logger(root, "scan-trash")
        scan_candidates(root, args.patterns, args.ignore, logger, dry_run=not args.execute)
        logger.write_summary()
        print(f"Manifest: {logger.manifest_path}")
        print(f"Summary:  {logger.summary_path}")
        print("DRY RUN" if not args.execute else "EXECUTED")
        return 0

    plan = load_plan(Path(args.plan))
    logger = Logger(root, plan.get("name", "plan"))
    actions = plan.get("actions", [])
    if not isinstance(actions, list):
        raise SystemExit("Plan JSON must contain an 'actions' array.")

    for item in actions:
        kind = item.get("action")
        if kind == "trash":
            apply_trash(root, item, dry_run=not args.execute, logger=logger)
        elif kind == "merge_dir":
            apply_merge_dir(root, item, dry_run=not args.execute, logger=logger)
        elif kind == "keep":
            logger.log(action="keep", reason=item.get("reason", ""), src=str(root / item.get("source", "")), dst="")
        else:
            logger.log(action="unknown_action", reason=item.get("reason", ""), src=json.dumps(item), dst="")

    logger.write_summary()
    print(f"Manifest: {logger.manifest_path}")
    print(f"Summary:  {logger.summary_path}")
    print("DRY RUN" if not args.execute else "EXECUTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
