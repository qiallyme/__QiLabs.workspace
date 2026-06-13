# file: directory_markmind_mapper.py
# purpose: Toolbox tool module for Directory Markmind Mapper in the sys bucket. Provides DirectoryMarkmindMapperTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options for max depth, files/folders, exclusions, and output destination.
# outputs: A Markmind/Markmap-friendly Markdown file containing a directory tree of the selected root.
# safety: Read-only scanner. Does not modify, move, or delete source files. Writes only the generated Markdown output file.
# owner: QiLabs

# tools/sys/directory_markmind_mapper/directory_markmind_mapper.py

from __future__ import annotations

import json
import os
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

from core.base_tool import BaseTool


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".turbo",
    ".vercel",
    ".netlify",
    ".cache",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "logs",
    "tmp",
    "temp",
}

DEFAULT_EXCLUDED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}

DEFAULT_EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".bak",
    ".swp",
    ".map",
}


class DirectoryMarkmindMapperTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.output_directory_var = None
        self.output_filename_var = None
        self.max_depth_var = None
        self.include_files_var = None
        self.include_build_artifacts_var = None
        self.include_metadata_var = None
        self.extra_excluded_dirs_text = None
        self.extra_excluded_files_text = None
        self.extra_excluded_exts_text = None

    def get_name(self):
        return "🗺️ Directory Markmind Mapper"

    def build_ui(self, parent):
        ttk.Label(
            parent,
            text="Generate a Markmind/Markmap-friendly Markdown map of the selected directory.",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(0, 8))

        options_frame = ttk.Frame(parent)
        options_frame.pack(fill="x", pady=(0, 8))

        self.include_files_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Include files",
            variable=self.include_files_var,
        ).pack(anchor="w", pady=(0, 4))

        self.include_build_artifacts_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Include build/dependency artifacts",
            variable=self.include_build_artifacts_var,
        ).pack(anchor="w", pady=(0, 4))

        self.include_metadata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Include YAML metadata header",
            variable=self.include_metadata_var,
        ).pack(anchor="w", pady=(0, 4))

        depth_frame = ttk.Frame(parent)
        depth_frame.pack(fill="x", pady=(4, 8))

        ttk.Label(
            depth_frame,
            text="Max depth blank = unlimited:",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(0, 4))

        self.max_depth_var = tk.StringVar(value="")
        ttk.Entry(
            depth_frame,
            textvariable=self.max_depth_var,
        ).pack(fill="x")

        output_frame = ttk.Frame(parent)
        output_frame.pack(fill="x", pady=(4, 8))

        ttk.Label(
            output_frame,
            text="Output folder blank = selected root:",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(0, 4))

        self.output_directory_var = tk.StringVar(value="")
        output_row = ttk.Frame(output_frame)
        output_row.pack(fill="x")

        ttk.Entry(
            output_row,
            textvariable=self.output_directory_var,
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            output_row,
            text="Browse",
            command=self.choose_output_directory,
        ).pack(side="left", padx=(6, 0))

        ttk.Label(
            output_frame,
            text="Output filename blank = auto-generated:",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(8, 4))

        self.output_filename_var = tk.StringVar(value="")
        ttk.Entry(
            output_frame,
            textvariable=self.output_filename_var,
        ).pack(fill="x")

        ttk.Label(
            parent,
            text="Extra excluded folders comma-separated:",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(8, 4))

        self.extra_excluded_dirs_text = tk.Text(
            parent,
            bg="#1c1c1e",
            fg="#32d74b",
            font=("Consolas", 10),
            height=3,
            relief="flat",
            padx=10,
            pady=8,
        )
        self.extra_excluded_dirs_text.pack(fill="x", pady=(0, 8))
        self.extra_excluded_dirs_text.insert("1.0", "")

        ttk.Label(
            parent,
            text="Extra excluded files comma-separated:",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(0, 4))

        self.extra_excluded_files_text = tk.Text(
            parent,
            bg="#1c1c1e",
            fg="#32d74b",
            font=("Consolas", 10),
            height=3,
            relief="flat",
            padx=10,
            pady=8,
        )
        self.extra_excluded_files_text.pack(fill="x", pady=(0, 8))
        self.extra_excluded_files_text.insert("1.0", "")

        ttk.Label(
            parent,
            text="Extra excluded extensions comma-separated, example: .zip, .png:",
            background="#0f0f11",
            foreground="white",
        ).pack(anchor="w", pady=(0, 4))

        self.extra_excluded_exts_text = tk.Text(
            parent,
            bg="#1c1c1e",
            fg="#32d74b",
            font=("Consolas", 10),
            height=3,
            relief="flat",
            padx=10,
            pady=8,
        )
        self.extra_excluded_exts_text.pack(fill="x", pady=(0, 8))
        self.extra_excluded_exts_text.insert("1.0", "")

    def choose_output_directory(self):
        selected = filedialog.askdirectory(title="Select output folder")
        if selected:
            self.output_directory_var.set(selected)

    def parse_csv_text(self, text_widget):
        if not text_widget:
            return set()

        raw = text_widget.get("1.0", tk.END).strip()
        if not raw:
            return set()

        items = set()
        for part in raw.replace("\n", ",").split(","):
            item = part.strip()
            if item:
                items.add(item)

        return items

    def parse_max_depth(self, log):
        raw = self.max_depth_var.get().strip() if self.max_depth_var else ""

        if not raw:
            return None

        try:
            value = int(raw)
        except ValueError:
            log(f"⚠️ Invalid max depth '{raw}'. Using unlimited depth.")
            return None

        if value < 0:
            log(f"⚠️ Invalid max depth '{raw}'. Using unlimited depth.")
            return None

        return value

    def safe_slug(self, value):
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
        return cleaned or "directory_map"

    def get_output_path(self, target_path):
        root = Path(target_path)

        output_dir_raw = self.output_directory_var.get().strip() if self.output_directory_var else ""
        output_name_raw = self.output_filename_var.get().strip() if self.output_filename_var else ""

        output_dir = Path(output_dir_raw) if output_dir_raw else root

        if output_name_raw:
            output_name = output_name_raw
            if not output_name.lower().endswith(".md"):
                output_name += ".md"
        else:
            stamp = datetime.now().strftime("%Y-%m-%d")
            output_name = f"{stamp}_directory_map_{self.safe_slug(root.name)}.md"

        return output_dir / output_name

    def should_skip_dir(self, path, excluded_dirs):
        return path.name in excluded_dirs

    def should_skip_file(self, path, excluded_files, excluded_exts):
        return path.name in excluded_files or path.suffix.lower() in excluded_exts

    def build_tree_lines(
        self,
        root,
        max_depth,
        include_files,
        excluded_dirs,
        excluded_files,
        excluded_exts,
        log,
        prog,
    ):
        lines = []
        scanned_count = 0

        def walk(current, depth):
            nonlocal scanned_count

            if self.cancel_requested:
                return

            if max_depth is not None and depth > max_depth:
                return

            try:
                children = sorted(
                    current.iterdir(),
                    key=lambda item: (not item.is_dir(), item.name.lower()),
                )
            except PermissionError:
                indent = "  " * depth
                lines.append(f"{indent}- ⚠️ {current.name} — permission denied")
                return
            except OSError as exc:
                indent = "  " * depth
                lines.append(f"{indent}- ⚠️ {current.name} — read error: {exc}")
                return

            for child in children:
                if self.cancel_requested:
                    return

                scanned_count += 1

                if scanned_count % 50 == 0:
                    prog(min(95, scanned_count % 100))

                if child.is_dir():
                    if self.should_skip_dir(child, excluded_dirs):
                        continue

                    indent = "  " * depth
                    lines.append(f"{indent}- 📁 {child.name}")
                    walk(child, depth + 1)

                elif include_files:
                    if self.should_skip_file(child, excluded_files, excluded_exts):
                        continue

                    indent = "  " * depth
                    lines.append(f"{indent}- 📄 {child.name}")

        lines.append(f"- 📁 {root.name}")
        walk(root, 1)

        log(f"📊 Scanned items inspected: {scanned_count}")
        return lines

    def build_markmind_content(self, root, output_path, tree_lines):
        generated_at = datetime.now().isoformat(timespec="seconds")
        include_metadata = self.include_metadata_var.get() if self.include_metadata_var else True

        content = []

        if include_metadata:
            content.extend(
                [
                    "---",
                    f'title: "Directory Map: {root.name}"',
                    f'root_path: "{str(root)}"',
                    f'output_path: "{str(output_path)}"',
                    f'generated_at: "{generated_at}"',
                    'generator: "toolbox.sys.directory_markmind_mapper"',
                    "---",
                    "",
                ]
            )

        content.extend(
            [
                f"# Directory Map: {root.name}",
                "",
                f"Generated: `{generated_at}`",
                "",
                f"Root: `{root}`",
                "",
                "## Tree",
                "",
                *tree_lines,
                "",
            ]
        )

        return "\n".join(content)

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False

        root = Path(target_path).resolve()

        log("🗺️ DIRECTORY MARKMIND MAPPER")
        log("-" * 40)

        if not root.exists():
            log(f"❌ Target path does not exist: {root}")
            return

        if not root.is_dir():
            log(f"❌ Target path is not a directory: {root}")
            return

        max_depth = self.parse_max_depth(log)
        include_files = self.include_files_var.get() if self.include_files_var else True
        include_build_artifacts = (
            self.include_build_artifacts_var.get()
            if self.include_build_artifacts_var
            else False
        )

        excluded_dirs = set() if include_build_artifacts else set(DEFAULT_EXCLUDED_DIRS)
        excluded_files = set(DEFAULT_EXCLUDED_FILES)
        excluded_exts = set(DEFAULT_EXCLUDED_EXTENSIONS)

        excluded_dirs.update(self.parse_csv_text(self.extra_excluded_dirs_text))
        excluded_files.update(self.parse_csv_text(self.extra_excluded_files_text))
        excluded_exts.update(
            ext if ext.startswith(".") else f".{ext}"
            for ext in self.parse_csv_text(self.extra_excluded_exts_text)
        )

        output_path = self.get_output_path(root)

        log(f"📁 Root: {root}")
        log(f"📄 Output: {output_path}")
        log(f"🧱 Include files: {include_files}")
        log(f"🧹 Skip build artifacts: {not include_build_artifacts}")
        log(f"📏 Max depth: {max_depth if max_depth is not None else 'unlimited'}")
        log("")

        if not is_live:
            log("🔎 Dry run mode: no file will be written.")
            log("✅ Configuration looks ready.")
            prog(100)
            return

        tree_lines = self.build_tree_lines(
            root=root,
            max_depth=max_depth,
            include_files=include_files,
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files,
            excluded_exts=excluded_exts,
            log=log,
            prog=prog,
        )

        if self.cancel_requested:
            log("🛑 Cancelled by user.")
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = self.build_markmind_content(
            root=root,
            output_path=output_path,
            tree_lines=tree_lines,
        )

        output_path.write_text(content, encoding="utf-8")

        prog(100)
        log("-" * 40)
        log(f"✅ Directory map generated: {output_path}")