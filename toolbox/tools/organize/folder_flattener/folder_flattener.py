# file: folder_flattener.py
# purpose: Toolbox tool module for Folder Flattener in the organize bucket. Provides FolderFlattenerTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from core.base_tool import BaseTool

class FolderFlattenerTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False

    def get_name(self):
        return "📁 Folder Flattener"

    def build_ui(self, parent):
        # Brief instruction label
        ttk.Label(parent, text="Moves files from child folders into the root directory.", 
                  background="#0f0f11", foreground="#a1a1a6", font=("Segoe UI", 10)).pack(anchor='w', pady=(0, 15))
        
        # Mode Selection
        self.recursive_var = tk.BooleanVar(value=False)
        
        # Styled Checkbutton
        tk.Checkbutton(
            parent,
            text="RECURSIVE MODE (ALL nested folders)",
            variable=self.recursive_var,
            bg="#0f0f11",
            fg="#0a84ff",
            selectcolor="#1c1c1e",
            activebackground="#0f0f11",
            activeforeground="#0a84ff",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(parent, text="ℹ️ Tip: One-level mode only moves files from immediate children.", 
                  background="#0f0f11", foreground="#4c4c4e", font=("Segoe UI", 9, "italic")).pack(anchor='w')

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        recursive = self.recursive_var.get()
        
        mode_str = "RECURSIVE" if recursive else "ONE LEVEL"
        log(f"🚀 FOLDER FLATTENER RUNNING ({mode_str})")
        log(f"📍 TARGET: {target_path}")
        log("-" * 40)

        # 1. Collect files to move
        files_to_move = []
        
        try:
            if recursive:
                for rootdir, dirs, files in os.walk(target_path):
                    if rootdir == target_path:
                        continue # Skip root
                    for f in files:
                        files_to_move.append(os.path.join(rootdir, f))
            else:
                # Only immediate subfolders
                for item in os.listdir(target_path):
                    item_path = os.path.join(target_path, item)
                    if os.path.isdir(item_path):
                        for f in os.listdir(item_path):
                            file_full = os.path.join(item_path, f)
                            if os.path.isfile(file_full):
                                files_to_move.append(file_full)
                                
            total_found = len(files_to_move)
            if total_found == 0:
                log("ℹ️ No files were found in subfolders to flatten.")
                prog(100)
                return

            log(f"📋 Found {total_found} files to move.")

            # If recursive and live, follow the "run dry then confirm" instruction
            if is_live and recursive:
                log("\n🔎 [RECURSIVE SAFETY] Running dry scan first...")
                # Show representative sample
                sample_count = min(15, total_found)
                for i in range(sample_count):
                    log(f"   - Would move: {os.path.relpath(files_to_move[i], target_path)}")
                if total_found > sample_count:
                    log(f"   - ... and {total_found - sample_count} more.")
                
                # Blocking confirmation
                if not messagebox.askyesno("CONFIRM RECURSIVE FLATTENING", 
                                            f"Found {total_found} files across nested folders.\n\nAre you sure you want to MOVE all these into the root directory?\nThis cannot be easily undone."):
                    log("🛑 RECURSIVE OPERATION CANCELLED BY USER.")
                    prog(100)
                    return
                log("✅ USER CONFIRMED. Executing movement...")

            # 2. Move (or Dry Run Log)
            moved_count = 0
            
            for i, src in enumerate(files_to_move):
                if self.cancel_requested:
                    log("\n🛑 CANCELLATION REQUESTED. Stopped.")
                    break
                    
                filename = os.path.basename(src)
                dst = os.path.join(target_path, filename)

                # Collision check
                if os.path.exists(dst):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(os.path.join(target_path, f"{base}_{counter}{ext}")):
                        counter += 1
                    dst = os.path.join(target_path, f"{base}_{counter}{ext}")
                    new_filename = os.path.basename(dst)
                else:
                    new_filename = filename
                
                if is_live:
                    try:
                        shutil.move(src, dst)
                        log(f"✅ MOVED: {filename} -> {new_filename}")
                        moved_count += 1
                    except Exception as e:
                        log(f"❌ ERROR: {filename} -> {e}")
                else:
                    log(f"🔎 [DRY] Move: {os.path.relpath(src, target_path)} -> {new_filename}")
                    moved_count += 1
                
                prog(int((i + 1) / total_found * 100))

            log("-" * 40)
            status = "FLATTENED" if is_live else "PLANNED"
            log(f"✅ TOTAL {status}: {moved_count}/{total_found}")
            
        except Exception as e:
            log(f"💣 ERROR ENCOUNTERED: {e}")
