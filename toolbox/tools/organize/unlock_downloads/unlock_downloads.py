# file: unlock_downloads.py
# purpose: Toolbox tool module for Unlock Downloads in the organize bucket. Provides UnblockDownloadsTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import tkinter as tk
from tkinter import ttk
from core.base_tool import BaseTool
import traceback


class UnblockDownloadsTool(BaseTool):
    def __init__(self):
        # State
        self.cancel_requested = False
        self.memory_cache = []
        self.memory_params = None

        # Common document/media extensions you may want to unblock selectively
        self.common_extensions = {
            ".pdf", ".md", ".csv", ".xls", ".xlsx", ".doc", ".docx",
            ".ppt", ".pptx", ".txt", ".rtf",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff",
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
            ".zip", ".7z", ".rar", ".json", ".xml"
        }

        self.ignore_folders = {
            ".git", ".vscode", ".idea", "node_modules", "dist", "build",
            ".next", ".turbo", ".cache", "__pycache__", "vendor"
        }

    def get_name(self):
        return "🔓 Unblock Files"

    def build_ui(self, parent):
        tk.Label(
            parent,
            text="Extension Filter (comma separated, blank = use defaults):",
            bg="#0f0f11",
            fg="white"
        ).pack(anchor="w")

        self.ext_var = tk.StringVar(value=".pdf")
        tk.Entry(
            parent,
            textvariable=self.ext_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white"
        ).pack(fill="x", pady=(0, 5), ipady=5)

        self.all_files_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            parent,
            text="Process ALL file types",
            variable=self.all_files_var
        ).pack(anchor="w", pady=(0, 5))

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent,
            text="Scan subfolders recursively",
            variable=self.recursive_var
        ).pack(anchor="w", pady=(0, 5))

        self.skip_ignored_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent,
            text="Skip common junk/dev folders",
            variable=self.skip_ignored_var
        ).pack(anchor="w", pady=(0, 10))

    def _parse_extensions(self, raw_exts):
        """
        Normalize comma-separated extensions into a set like {'.pdf', '.docx'}.
        Blank input falls back to {'.pdf'} unless ALL is checked.
        """
        if not raw_exts.strip():
            return {".pdf"}

        parsed = set()
        for ext in raw_exts.split(","):
            ext = ext.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = "." + ext
            parsed.add(ext)
        return parsed or {".pdf"}

    def _has_zone_identifier(self, file_path):
        """
        Check whether the file has the Zone.Identifier ADS.
        """
        ads_path = file_path + ":Zone.Identifier"
        return os.path.exists(ads_path)

    def _remove_zone_identifier(self, file_path):
        """
        Remove the Zone.Identifier ADS from the file.
        Returns True if removed, False if there was nothing to remove.
        """
        ads_path = file_path + ":Zone.Identifier"
        if os.path.exists(ads_path):
            os.remove(ads_path)
            return True
        return False

    def _should_skip_root(self, root):
        root_parts = set(root.lower().replace("\\", "/").split("/"))
        return bool(root_parts.intersection(self.ignore_folders))

    def _collect_candidates(self, target_path, recursive, process_all, extensions, skip_ignored):
        """
        Build a list of files eligible for inspection/unblocking.
        """
        candidates = []

        if recursive:
            walker = os.walk(target_path)
        else:
            # Simulate os.walk top-level only
            try:
                entries = os.listdir(target_path)
            except Exception:
                return candidates

            files = []
            dirs = []
            for name in entries:
                full = os.path.join(target_path, name)
                if os.path.isdir(full):
                    dirs.append(name)
                elif os.path.isfile(full):
                    files.append(name)
            walker = [(target_path, dirs, files)]

        for root, dirs, files in walker:
            if skip_ignored and self._should_skip_root(root):
                continue

            for file in files:
                full_path = os.path.join(root, file)

                if process_all:
                    candidates.append(full_path)
                    continue

                _, ext = os.path.splitext(file)
                if ext.lower() in extensions:
                    candidates.append(full_path)

        return candidates

    def execute(self, target_path, is_live, log, prog):
        try:
            self.cancel_requested = False

            raw_exts = self.ext_var.get().strip()
            process_all = self.all_files_var.get()
            recursive = self.recursive_var.get()
            skip_ignored = self.skip_ignored_var.get()
            extensions = self._parse_extensions(raw_exts)

            current_params = (
                target_path,
                raw_exts,
                process_all,
                recursive,
                skip_ignored
            )

            # Live mode can reuse dry-run memory if params match
            if is_live and self.memory_cache and self.memory_params == current_params:
                log("🚀 [UNBLOCKER] EXECUTING DIRECTLY FROM DRY RUN MEMORY...\n" + "-" * 40)
                total = len(self.memory_cache)

                unblocked = 0
                failed = 0

                for i, file_path in enumerate(self.memory_cache):
                    if self.cancel_requested:
                        log("🛑 OPERATION ABORTED BY USER.")
                        break

                    try:
                        changed = self._remove_zone_identifier(file_path)
                        if changed:
                            unblocked += 1
                            log(f"✅ UNBLOCKED: {file_path}")
                        else:
                            log(f"⏭️ ALREADY CLEAN: {file_path}")
                    except Exception as e:
                        failed += 1
                        log(f"❌ ERROR: {file_path} -> {e}")

                    prog(((i + 1) / max(1, total)) * 100)

                self.memory_cache = []

                log("-" * 40)
                log(f"✅ UNBLOCK COMPLETE | Unblocked: {unblocked} | Failed: {failed}\n")
                return

            # Fresh scan
            self.memory_cache = []
            self.memory_params = current_params

            mode_label = "ALL FILE TYPES" if process_all else f"EXTENSIONS: {', '.join(sorted(extensions))}"
            recurse_label = "RECURSIVE" if recursive else "TOP-LEVEL ONLY"

            log(f"🚀 [UNBLOCKER] STARTING {'LIVE' if is_live else 'DRY RUN'} IN: {target_path}")
            log(f"📌 Mode: {mode_label}")
            log(f"📌 Scope: {recurse_label}")
            log("-" * 40)

            log("⏳ Scanning for candidate files...")
            candidates = self._collect_candidates(
                target_path=target_path,
                recursive=recursive,
                process_all=process_all,
                extensions=extensions,
                skip_ignored=skip_ignored
            )

            total = len(candidates)
            log(f"📊 Found {total} candidate files to inspect.")

            inspected = 0
            blocked_found = 0
            unblocked = 0
            skipped = 0
            failed = 0

            for file_path in candidates:
                if self.cancel_requested:
                    log("\n🛑 SCAN ABORTED BY USER.")
                    break

                inspected += 1
                prog((inspected / max(1, total)) * 100)

                try:
                    has_block = self._has_zone_identifier(file_path)

                    if not has_block:
                        skipped += 1
                        continue

                    blocked_found += 1

                    if is_live:
                        changed = self._remove_zone_identifier(file_path)
                        if changed:
                            unblocked += 1
                            log(f"✅ UNBLOCKED: {file_path}")
                        else:
                            skipped += 1
                            log(f"⏭️ ALREADY CLEAN: {file_path}")
                    else:
                        log(f"🔎 PREVIEW: BLOCKED -> {file_path}")
                        self.memory_cache.append(file_path)

                except Exception as e:
                    failed += 1
                    log(f"❌ ERROR: {file_path} -> {e}")

            if not self.cancel_requested:
                if not is_live:
                    log("-" * 40)
                    log(
                        f"✅ DRY RUN COMPLETE | "
                        f"Candidates: {total} | "
                        f"Blocked Found: {blocked_found} | "
                        f"Ready to Unblock: {len(self.memory_cache)} | "
                        f"Failed: {failed}\n"
                    )
                else:
                    log("-" * 40)
                    log(
                        f"✅ UNBLOCK COMPLETE | "
                        f"Candidates: {total} | "
                        f"Blocked Found: {blocked_found} | "
                        f"Unblocked: {unblocked} | "
                        f"Skipped: {skipped} | "
                        f"Failed: {failed}\n"
                    )

        except Exception:
            log(f"\n❌ CRITICAL THREAD ERROR ❌\n{traceback.format_exc()}")
