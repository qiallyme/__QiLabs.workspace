# file: export_blueprint.py
# purpose: Toolbox tool module for Export Blueprint in the dev bucket. Provides ExportBlueprintTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import tkinter as tk
from tkinter import ttk
from core.base_tool import BaseTool

class ExportBlueprintTool(BaseTool):
    def __init__(self):
        # 1. INITIALIZATION
        self.exclude_dirs = {'.github', '.obsidian', '.git', 'node_modules', '__pycache__'}
        self.exclude_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.pyc', '.exe', '.dll'}
        self.cancel_requested = False

    def get_name(self):
        # 2. SIDEBAR NAME
        return "📄 Blueprint Exporter"

    def build_ui(self, parent):
        # 3. SETTINGS UI
        ttk.Label(parent, text="Output Markdown File:", background="#0f0f11", foreground="white").pack(anchor='w', pady=(0, 5))
        
        self.output_var = tk.StringVar(value="blueprint_export.md")
        tk.Entry(parent, textvariable=self.output_var, bg="#1c1c1e", fg="white", insertbackground="white", relief="flat").pack(fill='x', pady=(0, 15), ipady=5)

    def execute(self, target_path, is_live, log, prog):
        # 4. THE ENGINE LOGIC
        self.cancel_requested = False
        output_filename = self.output_var.get() or "blueprint_export.md"
        output_file = os.path.join(target_path, output_filename)

        log(f"🚀 STARTING {'LIVE MODE' if is_live else 'DRY RUN'} IN: {target_path}\n" + "-"*40)
        
        # Scan phase
        files_to_process = []
        for root, dirs, files in os.walk(target_path):
            # Modify dirs in place to prevent os.walk from visiting excluded dirs
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            dirs.sort()
            files.sort()
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in self.exclude_exts and file != output_filename:
                    files_to_process.append(os.path.join(root, file))

        total_files = len(files_to_process)
        if total_files == 0:
            log("No files found to process.")
            log("-" * 40 + "\n✅ MODULE OPERATION COMPLETE.\n")
            return

        if not is_live:
            log(f"Found {total_files} files to export.")
            log(f"Would write output to: {output_file}")
            log("-" * 40 + "\n✅ EXPECTED OUTPUT COMPLETE.\n")
            return

        # Execute phase
        try:
            with open(output_file, 'w', encoding='utf-8') as outfile:
                for index, filepath in enumerate(files_to_process):
                    if self.cancel_requested:
                        log("⚠️ OPERATION CANCELLED BY USER.")
                        break

                    rel_path = os.path.relpath(filepath, target_path)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                        
                        outfile.write(f"\n\n# =========================================\n")
                        outfile.write(f"# File: {rel_path}\n")
                        outfile.write(f"# =========================================\n\n")
                        outfile.write(content)
                        if index % 10 == 0 or index == total_files - 1:
                            log(f"Included: {rel_path}")
                    except UnicodeDecodeError:
                        try:
                            with open(filepath, 'r', encoding='latin-1') as infile:
                                content = infile.read()
                            outfile.write(f"\n\n# =========================================\n")
                            outfile.write(f"# File: {rel_path}\n")
                            outfile.write(f"# =========================================\n\n")
                            outfile.write(content)
                            log(f"Included (latin-1 fallback): {rel_path}")
                        except Exception as e:
                            log(f"Skipping {rel_path}: {e}")
                    except Exception as e:
                        log(f"Skipping {rel_path}: {e}")
                    
                    prog(float(index + 1) / total_files * 100)

            if not self.cancel_requested:
                prog(100)
                log("-" * 40 + f"\n✅ EXPORT COMPLETED TO {output_file}\n")
        except Exception as e:
            log(f"❌ ERROR: {str(e)}")
