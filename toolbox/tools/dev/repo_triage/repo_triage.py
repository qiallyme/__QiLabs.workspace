from __future__ import annotations

import shutil
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk

from core.base_tool import BaseTool


IGNORE_PARTS = {".git", "node_modules", ".pnpm-store", "_quarantine"}
JUNK_NAMES = ["tmp", ".pytest_cache", ".ruff_cache", ".mypy_cache"]
JUNK_PREFIXES = ["tmp_"]


class RepoTriageTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.docs_folder_var = None
        self.quarantine_folder_var = None
        self.append_gitignore_var = None
        self.quarantine_junk_var = None

    def get_name(self):
        return "Repo Triage"

    def build_ui(self, parent):
        ttk.Label(parent, text="Inventory a repo, quarantine obvious root junk, and harden .gitignore without deleting source files.", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 10))

        self.docs_folder_var = tk.StringVar(value="docs")
        self.quarantine_folder_var = tk.StringVar(value="_quarantine")
        self.append_gitignore_var = tk.BooleanVar(value=True)
        self.quarantine_junk_var = tk.BooleanVar(value=True)

        for label, variable in [
            ("Inventory folder", self.docs_folder_var),
            ("Quarantine folder", self.quarantine_folder_var),
        ]:
            ttk.Label(parent, text=label, background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
            tk.Entry(parent, textvariable=variable, bg="#10192a", fg="white", insertbackground="white", relief="flat").pack(fill="x", ipady=6, pady=(0, 10))

        for label, variable in [
            ("Append QiOS repo hygiene block to .gitignore", self.append_gitignore_var),
            ("Move obvious root temp/cache folders into quarantine", self.quarantine_junk_var),
        ]:
            tk.Checkbutton(parent, text=label, variable=variable, bg="#121a2b", fg="white", selectcolor="#182338", activebackground="#121a2b", activeforeground="white").pack(anchor="w", pady=(0, 6))

    def should_skip(self, path):
        return any(part in IGNORE_PARTS for part in path.parts)

    def inventory_paths(self, root):
        dirs = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_dir() and not self.should_skip(path))
        files = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and not self.should_skip(path))
        return dirs, files

    def gitignore_block(self):
        return (
            "# --- QiOS repo hygiene ---\n"
            "node_modules/\n"
            ".pnpm-store/\n\n"
            ".env\n"
            ".env.*\n"
            "!.env.example\n\n"
            ".pytest_cache/\n"
            ".ruff_cache/\n"
            ".mypy_cache/\n"
            "__pycache__/\n"
            "*.pyc\n\n"
            "dist/\n"
            "build/\n"
            ".next/\n"
            ".vite/\n\n"
            "tmp/\n"
            "tmp_*/\n"
            "_quarantine/\n\n"
            "*.log\n"
            "npm-debug.log*\n"
            "pnpm-debug.log*\n"
            "yarn-debug.log*\n\n"
            ".DS_Store\n"
            "Thumbs.db\n"
            ".vscode/\n"
            ".idea/\n"
            "# --- end QiOS repo hygiene ---\n"
        )

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        self.reset_run_state()
        root = Path(target_path).resolve()
        today = date.today().isoformat()
        docs_root = root / (self.docs_folder_var.get().strip() or "docs")
        quarantine_root = root / (self.quarantine_folder_var.get().strip() or "_quarantine")

        log(f"Repo triage {'LIVE' if is_live else 'SCAN'}")
        log(f"Root: {root}")
        log(f"Inventory folder: {docs_root}")
        log(f"Quarantine folder: {quarantine_root}")
        log("-" * 56)

        dirs, files = self.inventory_paths(root)
        dirs_out = docs_root / f"repo_dirs_{today}.txt"
        files_out = docs_root / f"repo_files_{today}.txt"

        log(f"Inventory counts: {len(dirs)} directories, {len(files)} files")
        log(f"Would write: {dirs_out}")
        log(f"Would write: {files_out}")
        prog(30)

        moved = []
        if self.quarantine_junk_var.get():
            for item in root.iterdir():
                if item.name in JUNK_NAMES or any(item.name.startswith(prefix) for prefix in JUNK_PREFIXES):
                    destination = quarantine_root / item.name
                    if destination.exists():
                        destination = quarantine_root / f"{item.name}_{today}"
                    moved.append((item, destination))

        if moved:
            for source, destination in moved:
                log(f"{'Will move' if not is_live else 'Moving'}: {source.name} -> {destination.relative_to(root)}")
        else:
            log("No obvious root-level junk folders matched the current rules.")
        prog(55)

        gitignore = root / ".gitignore"
        append_block = self.append_gitignore_var.get()
        if append_block:
            log("Will ensure the QiOS repo hygiene block exists in .gitignore.")
        prog(70)

        if not is_live:
            log("Dry run only. No files were changed.")
            prog(100)
            return

        docs_root.mkdir(parents=True, exist_ok=True)
        quarantine_root.mkdir(parents=True, exist_ok=True)
        dirs_out.write_text("\n".join(dirs), encoding="utf-8")
        files_out.write_text("\n".join(files), encoding="utf-8")

        for source, destination in moved:
            if self.cancel_requested:
                log("Canceled before quarantine move phase finished.")
                prog(100)
                return
            shutil.move(str(source), str(destination))

        if append_block:
            existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
            if "QiOS repo hygiene" not in existing:
                gitignore.write_text(existing.rstrip() + "\n\n" + self.gitignore_block(), encoding="utf-8")
                log("Appended hygiene block to .gitignore.")
            else:
                log("QiOS repo hygiene block already present in .gitignore.")

        lockfiles = {
            "package-lock.json": (root / "package-lock.json").exists(),
            "pnpm-lock.yaml": (root / "pnpm-lock.yaml").exists(),
            "yarn.lock": (root / "yarn.lock").exists(),
            "pnpm-workspace.yaml": (root / "pnpm-workspace.yaml").exists(),
        }
        for name, exists in lockfiles.items():
            log(f"{name}: {'FOUND' if exists else 'not found'}")

        if lockfiles["package-lock.json"] and lockfiles["pnpm-lock.yaml"]:
            warning_message = "Both package-lock.json and pnpm-lock.yaml exist."
            log(f"WARNING: {warning_message}")
            self.set_run_status("warning", warning_message)

        log("Repo triage complete. Review git status before committing.")
        prog(100)
