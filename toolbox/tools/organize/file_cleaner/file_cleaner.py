# file: file_cleaner.py
# purpose: Toolbox tool module for File Cleaner in the organize bucket. Provides FilenameCleanerTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

# tools/filename_cleaner.py
import os
import re
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from core.base_tool import BaseTool


class FilenameCleanerTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False

    def get_name(self):
        return "✏️ Filename Cleaner"

    def build_ui(self, parent):
        self.prefix_date_var = tk.BooleanVar(value=True)

        tk.Checkbutton(
            parent,
            text="Prefix cleaned files with today's date",
            variable=self.prefix_date_var,
            bg="#0f0f11",
            fg="white",
            selectcolor="#1c1c1e",
            activebackground="#0f0f11",
            activeforeground="white"
        ).pack(anchor="w", pady=(0, 8))

    def clean_name(self, name):
        base, ext = os.path.splitext(name)
        base = base.lower().strip()
        base = re.sub(r"[^\w\s-]", "", base)
        base = re.sub(r"[\s-]+", "_", base)
        base = re.sub(r"_+", "_", base).strip("_")

        if self.prefix_date_var.get():
            today = datetime.now().strftime("%Y-%m-%d")
            return f"{today}_{base}{ext.lower()}"

        return f"{base}{ext.lower()}"

    def execute(self, target_path, is_live, log, prog):
        files = [
            f for f in os.listdir(target_path)
            if os.path.isfile(os.path.join(target_path, f))
        ]

        if not files:
            log("❌ No files found.")
            return

        total = len(files)
        log(f"✏️ FILENAME CLEANER {'LIVE' if is_live else 'DRY RUN'}")
        log("-" * 40)

        for i, file in enumerate(files, start=1):
            if self.cancel_requested:
                log("🛑 Cancelled by user.")
                break

            old_path = os.path.join(target_path, file)
            new_name = self.clean_name(file)
            new_path = os.path.join(target_path, new_name)

            if old_path == new_path:
                log(f"⏭️ No change: {file}")
            elif os.path.exists(new_path):
                log(f"⚠️ Skipped, target exists: {new_name}")
            elif is_live:
                try:
                    os.rename(old_path, new_path)
                    log(f"✅ Renamed: {file} → {new_name}")
                except Exception as e:
                    log(f"❌ Failed: {file} → {e}")
            else:
                log(f"🔎 Would rename: {file} → {new_name}")

            prog((i / total) * 100)

        log("-" * 40)
        log("✅ Filename cleaning complete.")
