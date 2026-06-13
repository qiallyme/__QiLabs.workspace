#!/usr/bin/env python3
"""
QiOS Step 3 Directory Tree Compiler v1

Inputs:
- data/sheets/realms_registry.csv
- rules/folder_registry.yaml

Outputs:
- Canonical QiOS folder tree (stubs)
- Realm mirror trees (omit client_excluded folders)
- README placeholders per folder
- data/outputs/tree_compile_log.json

Idempotent, supports --dry-run.
"""

import csv, json, argparse, hashlib
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    raise SystemExit("Missing dependency: pyyaml. Install with `pip install pyyaml`.")

ROOT = Path(__file__).resolve().parents[1]  # QiOS_v1/
DEFAULT_REALMS_CSV = ROOT / "data" / "sheets" / "realms_registry.csv"
DEFAULT_FOLDER_YAML = ROOT / "rules" / "folder_registry.yaml"
LOG_PATH = ROOT / "data" / "outputs" / "tree_compile_log.json"

README_NAME = "_readme.md"

README_TEMPLATE = """---
title: {title}
slug: {slug}
realm: QiOS
qi_decimal: {qi_decimal}
type: doc
node: file
status: active
system: qios
created: {created}
updated: {updated}
---

## Purpose
{purpose}

## Scope
- Owned by: {owned_by}
- Realm-bound: {realm_bound}

## Governance
- Related rules: {rules}

## Allowed File Types
{allowed_types}

## Workers Touching This Folder
{workers}

## Examples
{examples}
"""

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d")

def load_realms(csv_path: Path):
    realms = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "active").lower() != "active":
                continue
            realms.append(row)
    return realms

def load_folders(yaml_path: Path):
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Expected shape: folders: [ {path, title, qi_decimal, owned_by, realm_bound, client_excluded, allowed_types, workers, rules, examples} ]
    return data.get("folders", [])

def ensure_dir(path: Path, dry_run=False, log=None):
    if not path.exists():
        if dry_run:
            log.append({"action": "mkdir", "path": str(path)})
        else:
            path.mkdir(parents=True, exist_ok=True)
            log.append({"action": "mkdir", "path": str(path)})

def write_readme(folder_path: Path, folder_def: dict, dry_run=False, log=None):
    readme_path = folder_path / README_NAME
    if readme_path.exists():
        return  # idempotent: do not overwrite unless you add a flag later

    content = README_TEMPLATE.format(
        title=folder_def.get("title", folder_path.name),
        slug=folder_def.get("slug", folder_path.name.lower()),
        qi_decimal=folder_def.get("qi_decimal", ""),
        purpose=folder_def.get("purpose", "TODO: define purpose"),
        owned_by=folder_def.get("owned_by", "qios"),
        realm_bound=folder_def.get("realm_bound", False),
        rules=", ".join(folder_def.get("rules", [])) or "TODO",
        allowed_types="\n".join(f"- `{t}`" for t in folder_def.get("allowed_types", [])) or "- TODO",
        workers="\n".join(f"- {w}" for w in folder_def.get("workers", [])) or "- TODO",
        examples="\n".join(f"- {e}" for e in folder_def.get("examples", [])) or "- TODO",
        created=now_iso(),
        updated=now_iso()
    )

    if dry_run:
        log.append({"action": "write_readme", "path": str(readme_path)})
    else:
        readme_path.write_text(content, encoding="utf-8")
        log.append({"action": "write_readme", "path": str(readme_path)})

def compile_root_tree(folders, dry_run=False, log=None):
    for fd in folders:
        rel_path = fd["path"].strip("/").replace("\\", "/")
        full_path = ROOT / rel_path
        ensure_dir(full_path, dry_run=dry_run, log=log)
        write_readme(full_path, fd, dry_run=dry_run, log=log)

def compile_realm_trees(realms, folders, dry_run=False, log=None):
    # Realm roots assumed at realms/<realm_slug>/
    for r in realms:
        realm_slug = r.get("realm_slug") or r.get("slug") or r["realm"].lower()
        realm_root = ROOT / "realms" / realm_slug
        ensure_dir(realm_root, dry_run=dry_run, log=log)

        # Mirror folders that are realm_bound OR are standard realm scaffolds
        for fd in folders:
            if fd.get("client_excluded", False):
                continue
            if not fd.get("realm_mirror", True):
                continue

            # Mirror path under realm root by stripping "QiOS/" prefix if present
            rel_path = fd["path"].strip("/").replace("\\", "/")
            rel_parts = Path(rel_path).parts

            # If folder is a top-level system folder (apps/workers/etc), skip mirroring into realm
            if rel_parts and rel_parts[0] in ("apps","workers","components","workflows","rules","data","security","connections","sites","docs","darkmatter","templates","projects"):
                continue

            mirror_rel = Path(*rel_parts)
            mirror_path = realm_root / mirror_rel
            ensure_dir(mirror_path, dry_run=dry_run, log=log)
            write_readme(mirror_path, fd, dry_run=dry_run, log=log)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--realms-csv", default=str(DEFAULT_REALMS_CSV))
    ap.add_argument("--folders-yaml", default=str(DEFAULT_FOLDER_YAML))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    log = []
    realms = load_realms(Path(args.realms_csv))
    folders = load_folders(Path(args.folders_yaml))

    # Ensure output log folder exists
    ensure_dir(LOG_PATH.parent, dry_run=args.dry_run, log=log)

    compile_root_tree(folders, dry_run=args.dry_run, log=log)
    compile_realm_trees(realms, folders, dry_run=args.dry_run, log=log)

    if args.dry_run:
        print(json.dumps(log, indent=2))
    else:
        LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")
        print(f"Tree compile complete. Log written to {LOG_PATH}")

if __name__ == "__main__":
    main()
