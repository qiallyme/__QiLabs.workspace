# file: unzip_sync.py
# purpose: Toolbox tool module for Unzip Sync in the organize bucket. Provides UnzipSyncTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import zipfile
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from core.base_tool import BaseTool

class UnzipSyncTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False

    def get_name(self):
        return "📦 Unzip & Sync"

    def build_ui(self, parent):
        ttk.Label(parent, text="Extracts .zip files recursively and deletes originals after a sync delay.", 
                  background="#0f0f11", foreground="#a1a1a6", font=("Segoe UI", 10)).pack(anchor='w', pady=(0, 15))
        
        # Delay Setting
        delay_frame = tk.Frame(parent, bg="#0f0f11")
        delay_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(delay_frame, text="Sync Delay (seconds):", background="#0f0f11", foreground="white").pack(side='left', padx=(0, 10))
        self.delay_var = tk.IntVar(value=10)
        tk.Entry(delay_frame, textvariable=self.delay_var, bg="#1c1c1e", fg="white", width=5, relief="flat", insertbackground="white").pack(side='left')

        # Delete Option
        self.delete_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            parent,
            text="Delete original .zip after extraction",
            variable=self.delete_var,
            bg="#0f0f11",
            fg="#ff453a",
            selectcolor="#1c1c1e",
            activebackground="#0f0f11",
            activeforeground="#ff453a"
        ).pack(anchor="w", pady=(5, 0))

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        delay = self.delay_var.get()
        should_delete = self.delete_var.get()
        
        log(f"🚀 UNZIP & SYNC {'LIVE' if is_live else 'DRY RUN'}")
        log(f"📍 TARGET: {target_path}")
        log(f"⏱️ DELAY: {delay}s | 🗑️ DELETE: {'YES' if should_delete else 'NO'}")
        log("-" * 40)

        base_dir = Path(target_path)
        zip_files = list(base_dir.rglob('*.zip'))

        if not zip_files:
            log("ℹ️ No zip files found.")
            prog(100)
            return

        total = len(zip_files)
        log(f"📋 Found {total} zip file(s).")

        for i, zip_path in enumerate(zip_files):
            if self.cancel_requested:
                log("🛑 Cancellation requested. Stopping...")
                break

            log(f"\n📦 Processing: {zip_path.name}")
            extract_dir = zip_path.parent / zip_path.stem

            if is_live:
                try:
                    # 1. Extract
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    log(f"   [+] Extracted to folder: {zip_path.stem}")

                    # 2. Sync Delay
                    if should_delete:
                        log(f"   [~] Waiting {delay}s for cloud sync...")
                        for s in range(delay):
                            if self.cancel_requested: break
                            time.sleep(1)
                        
                        # 3. Cleanup
                        if not self.cancel_requested:
                            zip_path.unlink()
                            log("   [-] Deleted original zip.")
                    else:
                        log("   [i] Keeping original zip (as requested).")

                except Exception as e:
                    log(f"   [!] ERROR: {e}")
            else:
                log(f"   🔎 [DRY] Would extract to: {zip_path.stem}")
                if should_delete:
                    log(f"   🔎 [DRY] Would wait {delay}s then delete: {zip_path.name}")

            prog(int((i + 1) / total * 100))

        log("-" * 40)
        log("✅ OPERATION COMPLETE.")
