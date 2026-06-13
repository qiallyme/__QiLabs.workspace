# file: extractor.py
# purpose: Toolbox tool module for Extractor in the dev bucket. Provides TextExtractorTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from core.base_tool import BaseTool

# New dependencies for OCR-based PDF extraction
try:
    from pdf2image import convert_from_path
    import pytesseract
except ImportError:
    # We'll handle the error inside the extraction method so the tool doesn't crash on boot
    pass

class TextExtractorTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.supported_extensions = {'.txt', '.md', '.csv', '.py', '.json', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.pdf'}
        self.ignored_dirs = {'.git', 'node_modules', '.turbo', '.next', 'dist', 'build', '.cache', '__pycache__', '.vscode', '.idea'}

    def get_name(self):
        return "📄 Text Extractor"

    def build_ui(self, parent):
        ttk.Label(parent, text="Extract text and format into a single master document.", background="#0f0f11", foreground="white").pack(anchor="w", pady=(0, 8))

        self.w_recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="🔄 Recursive (Scan all sub-folders)", variable=self.w_recursive).pack(anchor='w', pady=2)

        ttk.Label(parent, text=f"Supported: {', '.join(self.supported_extensions)}", background="#0f0f11", foreground="#a1a1aa").pack(anchor="w", pady=(5,0))

    def build_ascii_tree(self, startpath, is_recursive):
        """Generates the visual folder tree for the header."""
        tree_str = ""
        for root, dirs, files in os.walk(startpath):
            dirs[:] = [d for d in dirs if d.lower() not in self.ignored_dirs]
            if not is_recursive and root != startpath:
                dirs[:] = []

            level = root.replace(startpath, '').count(os.sep)
            indent = ' ' * 4 * level
            folder_name = os.path.basename(root) or startpath
            tree_str += f"{indent}|----{folder_name}\n"

            subindent = ' ' * 4 * (level + 1)
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in self.supported_extensions:
                    tree_str += f"{subindent}|-{f}\n"
        return tree_str

    def extract_text_from_file(self, full_path, ext):
        """
        Modified to use OCR for PDFs by converting to temporary images first.
        """
        try:
            if ext == '.pdf':
                # Verify dependencies are present
                try:
                    import pdf2image
                    import pytesseract
                except ImportError:
                    return "[ERROR] Missing pdf2image or pytesseract. Please 'pip install' them."

                text_content = []
                # Convert PDF pages to PIL images (300 DPI for best OCR accuracy)
                pages = convert_from_path(full_path, dpi=300)

                for i, page in enumerate(pages):
                    if self.cancel_requested: break
                    # Direct OCR from the image object
                    page_text = pytesseract.image_to_string(page)
                    text_content.append(f"--- Page {i+1} ---\n{page_text}")

                return "\n\n".join(text_content)

            else:
                # Standard text-based files
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            return f"[ERROR] Extraction failed: {str(e)}"

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        is_rec = self.w_recursive.get()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_filename = f"_Extraction_{timestamp}.md"
        out_filepath = os.path.join(target_path, out_filename)

        log(f"📄 STARTING TEXT EXTRACTOR {'LIVE' if is_live else 'DRY RUN'}\n" + "-" * 40)

        # 1. Gather Files
        files_to_process = []
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d.lower() not in self.ignored_dirs]
            if not is_rec and root != target_path:
                dirs[:] = []

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in self.supported_extensions:
                    files_to_process.append(os.path.join(root, f))

        if not files_to_process:
            log("❌ No supported files found.")
            return

        total = len(files_to_process)
        log(f"Found {total} files. Generating structure tree...")
        prog(10)

        # 2. Build Tree String
        tree_visual = self.build_ascii_tree(target_path, is_rec)

        if not is_live:
            log(f"🔍 [DRY RUN] Would extract {total} files into {out_filename}")
            prog(100)
            return

        # 3. Compile Master Document
        log(f"Writing extractions to: {out_filename}")

        try:
            with open(out_filepath, 'w', encoding='utf-8') as out:
                # HEADER
                out.write("HEADER\n----------------------\n")
                out.write("TYPE: MASTER TEXT EXTRACTION\n")
                out.write(f"PATH: {target_path}\n")
                out.write(f"RECURSIVE: {'[X]' if is_rec else '[ ]'}\n")
                out.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                out.write("------------\n\n")

                # TREE
                out.write(tree_visual)
                out.write("\n\n")

                # CONTENT LOOP
                for i, f_path in enumerate(files_to_process, start=1):
                    if self.cancel_requested:
                        log("🛑 Cancelled by user.")
                        break

                    ext = os.path.splitext(f_path)[1].lower()
                    rel_path = os.path.relpath(f_path, target_path)

                    text = self.extract_text_from_file(f_path, ext)

                    if text is not None:
                        # Write the file block
                        out.write(f"``` {ext.strip('.')}\n")
                        out.write(f"// FILE: {rel_path}\n")
                        out.write(f"// EXTRACTED: {datetime.now().strftime('%H:%M:%S')}\n")
                        out.write(f"{text}\n")
                        out.write("```\n")
                        out.write("---\n")

                        log(f"✅ Extracted: {rel_path}")
                    else:
                        log(f"⚠️ Failed to read: {rel_path}")

                    prog(10 + int((i / total) * 90))

                # FOOTER
                out.write("------------------------END OF EXTRACTION--------\n")

            log("-" * 40)
            log(f"✅ Extraction complete. Saved to: {out_filename}")

        except Exception as e:
            log(f"❌ ERROR writing file: {e}")
