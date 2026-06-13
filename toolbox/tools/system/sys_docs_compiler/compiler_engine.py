#!/usr/bin/env python3
"""
sys_docs_compiler.py

Purpose:
    Tree-aware documentation compiler for the QiLabs Python toolbox.

Context:
    This tool walks a repo tree, finds documentation-worthy Markdown, copies only
    selected docs and referenced assets, preserves source hierarchy, and builds
    one clean generated documentation site.

Safety:
    - Default behavior never mutates source files.
    - The target output folder is disposable and overwritten on build.
    - Use --fix only when you intentionally want safe Markdown fixes written
      back to source files.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Any


DEFAULT_CONFIG_NAME = ".qios/docs_compiler.config.json"


@dataclass
class DocIssue:
    severity: str
    path: str
    message: str


@dataclass
class BuildReport:
    started_at: str
    root: str
    target: str
    mode: str
    markdown_files_found: int = 0
    markdown_files_copied: int = 0
    assets_referenced: int = 0
    assets_copied: int = 0
    issues: list[DocIssue] | None = None

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [asdict(i) for i in (self.issues or [])]
        return data


DEFAULT_CONFIG: dict[str, Any] = {
    "site_title": "QiLabs Documentation",
    "exclude_dirs": [
        ".git", ".github", ".vscode", ".qios/tmp",
        "node_modules", ".next", "dist", "build", ".cache", "__pycache__",
        ".venv", "venv", "env", ".pytest_cache",
        "99_QiProject_Receipts",
        "aider_test",
    ],
    "exclude_file_globs": [
        "*.env", ".env*", "*.log", "*.tmp", "*.bak", "*.pyc",
        "*.sqlite", "*.db", "*.db-wal", "*.db-shm",
        "*secret*", "*secrets*", "*credential*", "*credentials*",
        "*token*", "*tokens*",
    ],
    "include_markdown_globs": ["*.md", "*.mdx"],
    "asset_extensions": [
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
        ".pdf", ".drawio", ".mermaid", ".mmd",
    ],
    "copy_unreferenced_assets": False,
    "preserve_hierarchy": True,
    "generate_index": True,
    "normalize_generated_markdown": True,
    "fix_source_markdown": False,
    "max_file_size_mb": 15,
}


ASSET_LINK_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|\[[^\]]+\]\(([^)]+)\)")


def load_config(root: Path, config_path: Path | None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    path = config_path or root / DEFAULT_CONFIG_NAME
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            user_config = json.load(f)
        config.update(user_config)
    return config


def is_inside(path: Path, possible_parent: Path) -> bool:
    try:
        path.resolve().relative_to(possible_parent.resolve())
        return True
    except ValueError:
        return False


def matches_any_glob(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name.lower(), pattern.lower()) for pattern in patterns)


def should_skip_dir(path: Path, root: Path, target: Path, config: dict[str, Any]) -> bool:
    if is_inside(path, target) or path.resolve() == target.resolve():
        return True

    rel = path.relative_to(root).as_posix() if is_inside(path, root) else path.as_posix()
    parts = set(path.parts)

    for excluded in config["exclude_dirs"]:
        ex_norm = excluded.replace("\\", "/").strip("/")
        if path.name == excluded or ex_norm in rel or excluded in parts:
            return True

    return False


def should_skip_file(path: Path, config: dict[str, Any]) -> bool:
    name = path.name
    if matches_any_glob(name, config["exclude_file_globs"]):
        return True

    max_bytes = int(config.get("max_file_size_mb", 15)) * 1024 * 1024
    try:
        if path.stat().st_size > max_bytes:
            return True
    except OSError:
        return True

    return False


def is_markdown(path: Path, config: dict[str, Any]) -> bool:
    return any(fnmatch.fnmatch(path.name.lower(), pat.lower()) for pat in config["include_markdown_globs"])


def walk_markdown(root: Path, target: Path, config: dict[str, Any]) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        dirnames[:] = [
            d for d in dirnames
            if not should_skip_dir(current / d, root, target, config)
        ]

        if should_skip_dir(current, root, target, config):
            continue

        for filename in filenames:
            path = current / filename
            if should_skip_file(path, config):
                continue
            if is_markdown(path, config):
                found.append(path)
    return sorted(found)


def normalize_markdown_text(text: str) -> str:
    # Safe generated-copy normalization.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def lint_markdown(path: Path, root: Path) -> list[DocIssue]:
    issues: list[DocIssue] = []
    rel = path.relative_to(root).as_posix()

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(DocIssue("error", rel, "File is not valid UTF-8."))
        return issues

    if "\t" in text:
        issues.append(DocIssue("warn", rel, "Contains tab characters."))

    h1_count = len(re.findall(r"^# ", text, flags=re.MULTILINE))
    if h1_count == 0:
        issues.append(DocIssue("info", rel, "No H1 title found."))
    elif h1_count > 1:
        issues.append(DocIssue("warn", rel, "Multiple H1 titles found."))

    if re.search(r"[ \t]+$", text, flags=re.MULTILINE):
        issues.append(DocIssue("info", rel, "Trailing whitespace found."))

    if text and not text.endswith("\n"):
        issues.append(DocIssue("info", rel, "Missing final newline."))

    return issues


def extract_local_links(markdown_text: str) -> list[str]:
    links: list[str] = []
    for match in ASSET_LINK_RE.finditer(markdown_text):
        target = match.group(1) or match.group(2)
        if not target:
            continue
        target = target.strip().split("#", 1)[0].split("?", 1)[0]
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        if target.startswith("#"):
            continue
        links.append(target)
    return links


def find_referenced_assets(markdown_files: list[Path], root: Path, config: dict[str, Any], issues: list[DocIssue]) -> set[Path]:
    asset_exts = {ext.lower() for ext in config["asset_extensions"]}
    assets: set[Path] = set()

    for md_path in markdown_files:
        rel_md = md_path.relative_to(root).as_posix()
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for link in extract_local_links(text):
            candidate = (md_path.parent / link).resolve()
            if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in asset_exts:
                assets.add(candidate)
            elif Path(link).suffix.lower() in asset_exts:
                issues.append(DocIssue("warn", rel_md, f"Referenced asset not found: {link}"))

    return assets


def copy_file_preserve_tree(src: Path, root: Path, target: Path, normalize_md: bool = False) -> Path:
    rel = src.relative_to(root)
    dest = target / rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    if normalize_md and src.suffix.lower() in {".md", ".mdx"}:
        text = src.read_text(encoding="utf-8")
        dest.write_text(normalize_markdown_text(text), encoding="utf-8")
    else:
        shutil.copy2(src, dest)

    return dest


def build_index(root: Path, target: Path, markdown_files: list[Path], title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "Generated documentation index.",
        "",
        "> This folder is generated. Edit the source files in their original locations, then rebuild.",
        "",
        "## Sections",
        "",
    ]

    by_top: dict[str, list[Path]] = {}
    for path in markdown_files:
        rel = path.relative_to(root)
        top = rel.parts[0] if rel.parts else "_root"
        by_top.setdefault(top, []).append(rel)

    for top in sorted(by_top):
        lines.append(f"### {top}")
        lines.append("")
        for rel in sorted(by_top[top]):
            link = rel.as_posix()
            label = rel.as_posix()
            lines.append(f"- [{label}]({link})")
        lines.append("")

    (target / "index.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def apply_source_fixes(markdown_files: list[Path], root: Path) -> int:
    changed = 0
    for path in markdown_files:
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        fixed = normalize_markdown_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            changed += 1
    return changed


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    target = Path(args.target).resolve()
    config = load_config(root, Path(args.config).resolve() if args.config else None)

    mode = "check" if args.check else "fix" if args.fix else "build"
    issues: list[DocIssue] = []
    report = BuildReport(
        started_at=datetime.now().isoformat(timespec="seconds"),
        root=str(root),
        target=str(target),
        mode=mode,
        issues=issues,
    )

    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    markdown_files = walk_markdown(root, target, config)
    report.markdown_files_found = len(markdown_files)

    for md in markdown_files:
        issues.extend(lint_markdown(md, root))

    assets = find_referenced_assets(markdown_files, root, config, issues)
    report.assets_referenced = len(assets)

    if args.check:
        print_summary(report)
        return 1 if any(i.severity == "error" for i in issues) else 0

    if args.fix:
        changed = apply_source_fixes(markdown_files, root)
        print(f"Applied safe source Markdown fixes to {changed} file(s).")
        print_summary(report)
        return 0

    # Build mode.
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    normalize = bool(config.get("normalize_generated_markdown", True))
    for md in markdown_files:
        copy_file_preserve_tree(md, root, target, normalize_md=normalize)
    report.markdown_files_copied = len(markdown_files)

    for asset in sorted(assets):
        if is_inside(asset, root) and not should_skip_file(asset, config):
            copy_file_preserve_tree(asset, root, target, normalize_md=False)
            report.assets_copied += 1

    if config.get("generate_index", True):
        build_index(root, target, markdown_files, str(config.get("site_title", "Documentation")))

    build_dir = target / "_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    report_path = build_dir / "docs_build_report.json"
    report_path.write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")

    print_summary(report)
    print(f"\nGenerated docs: {target}")
    print(f"Build report:    {report_path}")
    return 0 if not any(i.severity == "error" for i in issues) else 1


def print_summary(report: BuildReport) -> None:
    print("\nTree-Aware Docs Compiler")
    print("=" * 28)
    print(f"Mode:                 {report.mode}")
    print(f"Root:                 {report.root}")
    print(f"Target:               {report.target}")
    print(f"Markdown found:       {report.markdown_files_found}")
    print(f"Markdown copied:      {report.markdown_files_copied}")
    print(f"Assets referenced:    {report.assets_referenced}")
    print(f"Assets copied:        {report.assets_copied}")

    issues = report.issues or []
    if issues:
        print(f"Issues:               {len(issues)}")
        for issue in issues[:40]:
            print(f"  [{issue.severity.upper()}] {issue.path}: {issue.message}")
        if len(issues) > 40:
            print(f"  ... {len(issues) - 40} more issue(s), see build report.")
    else:
        print("Issues:               0")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tree-aware docs compiler.")
    parser.add_argument("--root", default=".", help="Repo/root folder to scan.")
    parser.add_argument("--target", required=True, help="Generated docs output folder.")
    parser.add_argument("--config", help="Optional JSON config path.")
    parser.add_argument("--check", action="store_true", help="Scan/lint only. Do not build.")
    parser.add_argument("--fix", action="store_true", help="Apply safe Markdown fixes to source files.")
    parser.add_argument("--build", action="store_true", help="Build generated docs site.")
    args = parser.parse_args(argv)

    selected = sum([bool(args.check), bool(args.fix), bool(args.build)])
    if selected == 0:
        args.build = True
    elif selected > 1:
        parser.error("Use only one of --check, --fix, or --build.")

    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
