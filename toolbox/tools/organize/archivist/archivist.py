# file: archivist.py
# purpose: Toolbox tool module for Archivist in the organize bucket. Provides ArchiveRouterTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import re
import tkinter as tk
from tkinter import ttk
from core.base_tool import BaseTool
import traceback

class ArchiveRouterTool(BaseTool):
    def __init__(self):
        self.target_extensions = {
            '.pdf', '.md', '.csv', '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx', '.txt', '.rtf',
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff'
        }
        self.ignore_folders = {
            '.git', '.vscode', '.idea', 'node_modules', 'dist', 'build', 
            '.next', '.turbo', '.cache', '__pycache__', 'public', 'vendor'
        }
        
        # New State Variables
        self.cancel_requested = False
        self.memory_cache = []
        self.memory_params = None

    def get_name(self):
        return "📂 Archive Router"

    def build_ui(self, parent):
        tk.Label(parent, text="Target ID Prefix (e.g. BBR4821):", bg="#0f0f11", fg="white").pack(anchor='w')
        self.id_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.id_var, bg="#1c1c1e", fg="white", insertbackground="white").pack(fill='x', pady=(0, 10), ipady=5)

        tk.Label(parent, text="Keyword Hunter (Comma separated, leave blank for all):", bg="#0f0f11", fg="white").pack(anchor='w')
        self.kw_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.kw_var, bg="#1c1c1e", fg="white", insertbackground="white").pack(fill='x', pady=(0, 5), ipady=5)
        
        # The Exact Match Toggle
        self.exact_match_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Exact Keyword Match (e.g. '1' won't trigger '10' or '11')", variable=self.exact_match_var).pack(anchor='w', pady=(0, 10))

    def extract_and_format_date(self, name):
        date_pattern = re.compile(r'\b(\d{1,4})[-/](\d{1,2})[-/](\d{1,4})\b')
        match = date_pattern.search(name)
        formatted_date = ""
        if match:
            full_match = match.group(0)
            parts = re.split(r'[-/]', full_match)
            y, m, d = (parts[0], parts[1], parts[2]) if len(parts[0]) == 4 else (parts[2], parts[0], parts[1])
            formatted_date = f"{y}-{int(m):02d}-{int(d):02d}_"
            name = name.replace(full_match, '')
        return name, formatted_date

    def normalize_name(self, name, is_folder):
        name = re.sub(r'[()]', '', name)
        name = re.sub(r'\s*-\s*', '-', name)
        name = re.sub(r'\s+', '_', name)
        name = name.strip('_')
        name = re.sub(r'_+', '_', name)
        return name.capitalize() if is_folder else name.lower()

    def clean_base_name(self, name, target_id):
        clean_name = name
        if target_id:
            base_id = target_id.strip('_')
            clean_name = re.sub(re.escape(base_id), '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'bbr_', '', clean_name, flags=re.IGNORECASE)
        return clean_name

    def execute(self, target_path, is_live, log, prog):
        try:
            self.cancel_requested = False 
            target_id = self.id_var.get().strip().rstrip('_').upper() + '_' if self.id_var.get() else ""
            raw_kws = self.kw_var.get()
            keywords = [k.strip().lower() for k in raw_kws.split(',')] if raw_kws else []
            exact_match = self.exact_match_var.get()
            
            current_params = (target_path, target_id, raw_kws, exact_match)

            if is_live and self.memory_cache and self.memory_params == current_params:
                log(f"🚀 [ROUTER] EXECUTING DIRECTLY FROM DRY RUN MEMORY...\n" + "-"*40)
                total = len(self.memory_cache)
                for i, (old_path, new_path, type_lbl) in enumerate(self.memory_cache):
                    if self.cancel_requested:
                        log("🛑 OPERATION ABORTED BY USER.")
                        break
                    
                    try:
                        os.rename(old_path, new_path)
                        log(f"✅ {type_lbl} RENAMED: {os.path.basename(new_path)}")
                    except Exception as e:
                        log(f"❌ ERROR: {os.path.basename(old_path)} -> {e}")
                    
                    prog(((i+1) / max(1, total)) * 100)

                self.memory_cache = [] 
                log("-" * 40 + "\n✅ ROUTER COMPLETE.\n")
                return

            self.memory_cache = [] 
            self.memory_params = current_params
        
            log(f"🚀 [ROUTER] STARTING {'LIVE' if is_live else 'DRY RUN'} IN: {target_path}\n" + "-"*40)
        
            log("⏳ Calculating total items for progress bar (this might take a second)...")
            total_items = sum([len(dirs) + len(files) for _, dirs, files in os.walk(target_path)])
            log(f"📊 Found {total_items} items to scan. Beginning processing...")
            
            processed = 0
            current_root = ""

            for root, dirs, files in os.walk(target_path, topdown=False):
                if self.cancel_requested:
                    log("\n🛑 SCAN ABORTED BY USER.")
                    break

                if set(root.lower().replace('\\', '/').split('/')).intersection(self.ignore_folders):
                    continue

                # Breadcrumb Logging: Tell the user where we are currently looking
                if current_root != root:
                    log(f"\n📂 Scanning Directory: {root}")
                    current_root = root

                # --- Process Files ---
                for file in files:
                    processed += 1
                    prog((processed / max(1, total_items)) * 100)
                    
                    name, ext = os.path.splitext(file)
                    if ext.lower() not in self.target_extensions: continue
                    
                    if keywords:
                        match_found = False
                        for kw in keywords:
                            if exact_match and re.search(rf'\b{re.escape(kw)}\b', name.lower()): match_found = True; break
                            elif not exact_match and kw in name.lower(): match_found = True; break
                        if not match_found: continue

                    clean_name = self.clean_base_name(name, target_id)
                    clean_name, ext_date = self.extract_and_format_date(clean_name)
                    clean_name = self.normalize_name(clean_name, False)
                    new_name = f"{target_id}{ext_date}{clean_name}{ext.lower()}"

                    if file != new_name:
                        old_path = os.path.join(root, file)
                        new_path = os.path.join(root, new_name)
                        
                        if is_live:
                            try:
                                os.rename(old_path, new_path)
                                log(f"✅ FILE: {new_name}")
                            except Exception as e: log(f"❌ ERROR: {file} -> {e}")
                        else:
                            log(f"🔎 PREVIEW: {file} -> {new_name}")
                            self.memory_cache.append((old_path, new_path, "FILE")) # Store in memory

                # --- Process Folders ---
                for folder in dirs:
                    processed += 1
                    prog((processed / max(1, total_items)) * 100)
                    
                    if keywords:
                        match_found = False
                        for kw in keywords:
                            if exact_match and re.search(rf'\b{re.escape(kw)}\b', folder.lower()): match_found = True; break
                            elif not exact_match and kw in folder.lower(): match_found = True; break
                    if not match_found: continue

                    clean_folder = self.clean_base_name(folder, target_id)
                    clean_folder, ext_date = self.extract_and_format_date(clean_folder)
                    clean_folder = self.normalize_name(clean_folder, True)
                    new_name = f"{target_id}{ext_date}{clean_folder}"

                    if folder != new_name:
                        old_path = os.path.join(root, folder)
                        new_path = os.path.join(root, new_name)

                        if is_live:
                            try:
                                os.rename(old_path, new_path)
                                log(f"📁 FOLDER: {new_name}/")
                            except Exception as e: log(f"❌ ERROR: {folder} -> {e}")
                        else:
                            log(f"🔎 PREVIEW: {folder}/ -> {new_name}/")
                            self.memory_cache.append((old_path, new_path, "FOLDER")) # Store in memory

            if not self.cancel_requested:
                log("-" * 40 + "\n✅ ROUTER COMPLETE.\n")
        except Exception as e:
            log(f"\n❌ CRITICAL THREAD ERROR ❌\n{traceback.format_exc()}")
