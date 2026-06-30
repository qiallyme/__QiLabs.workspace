# file: pdf_splitter.py
# purpose: Toolbox tool module for Pdf Splitter in the docs bucket. Provides BulkPdfSplitterTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

# tools/bulk_pdf_splitter.py
import os
import re
import tkinter as tk
from tkinter import ttk
from PyPDF2 import PdfReader, PdfWriter

from core.base_tool import BaseTool


class BulkPdfSplitterTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False

    def get_name(self):
        return "🧾 Bulk PDF Splitter"

    def build_ui(self, parent):
        ttk.Label(
            parent,
            text="Split Mode:",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor="w", pady=(0, 5))

        self.split_mode = tk.StringVar(value="ranges")

        mode_frame = tk.Frame(parent, bg="#0f0f11")
        mode_frame.pack(fill="x", pady=(0, 12))

        tk.Radiobutton(
            mode_frame,
            text="Custom ranges",
            variable=self.split_mode,
            value="ranges",
            bg="#0f0f11",
            fg="white",
            selectcolor="#1c1c1e",
            activebackground="#0f0f11",
            activeforeground="white"
        ).pack(side="left", padx=(0, 12))

        tk.Radiobutton(
            mode_frame,
            text="One file per page",
            variable=self.split_mode,
            value="per_page",
            bg="#0f0f11",
            fg="white",
            selectcolor="#1c1c1e",
            activebackground="#0f0f11",
            activeforeground="white"
        ).pack(side="left")

        ttk.Label(
            parent,
            text="Ranges (example: 1-3, 4-7, 8-8):",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor="w", pady=(0, 5))

        self.ranges_var = tk.StringVar(value="1-3, 4-6")

        tk.Entry(
            parent,
            textvariable=self.ranges_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(fill="x", ipady=5, pady=(0, 12))

        ttk.Label(
            parent,
            text="Output Folder Name:",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor="w", pady=(0, 5))

        self.output_folder_var = tk.StringVar(value="_split_output")

        tk.Entry(
            parent,
            textvariable=self.output_folder_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(fill="x", ipady=5, pady=(0, 12))

        ttk.Label(
            parent,
            text="Filename Prefix (optional):",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor="w", pady=(0, 5))

        self.prefix_var = tk.StringVar(value="part")

        tk.Entry(
            parent,
            textvariable=self.prefix_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(fill="x", ipady=5, pady=(0, 5))

    def _parse_ranges(self, raw_text, total_pages):
        ranges = []
        parts = [p.strip() for p in raw_text.split(",") if p.strip()]

        for part in parts:
            match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
            if not match:
                raise ValueError(f"Invalid range format: {part}")

            start = int(match.group(1))
            end = int(match.group(2))

            if start < 1 or end < 1:
                raise ValueError(f"Page numbers must start at 1: {part}")
            if start > end:
                raise ValueError(f"Start page greater than end page: {part}")
            if end > total_pages:
                raise ValueError(f"Range exceeds PDF page count ({total_pages}): {part}")

            ranges.append((start, end))

        return ranges

    def execute(self, target_path, is_live, log, prog):
        pdf_files = [
            f for f in os.listdir(target_path)
            if os.path.isfile(os.path.join(target_path, f))
            and f.lower().endswith(".pdf")
        ]

        if not pdf_files:
            log("❌ No PDF files found in target directory.")
            return

        output_folder_name = self.output_folder_var.get().strip() or "_split_output"
        prefix = self.prefix_var.get().strip() or "part"
        output_root = os.path.join(target_path, output_folder_name)

        if is_live:
            os.makedirs(output_root, exist_ok=True)

        total_files = len(pdf_files)

        log(f"🧾 BULK PDF SPLITTER {'LIVE' if is_live else 'DRY RUN'}")
        log("-" * 40)
        log(f"PDF files found: {total_files}")
        log(f"Mode: {self.split_mode.get()}")
        log(f"Output folder: {output_root}")
        log("")

        for file_index, pdf_name in enumerate(pdf_files, start=1):
            if self.cancel_requested:
                log("🛑 Cancelled by user.")
                break

            pdf_path = os.path.join(target_path, pdf_name)
            base_name = os.path.splitext(pdf_name)[0]

            try:
                reader = PdfReader(pdf_path)
                total_pages = len(reader.pages)
            except Exception as e:
                log(f"❌ Failed to open {pdf_name}: {e}")
                prog((file_index / total_files) * 100)
                continue

            log(f"📄 {pdf_name} ({total_pages} pages)")

            if self.split_mode.get() == "per_page":
                jobs = [(p, p) for p in range(1, total_pages + 1)]
            else:
                try:
                    jobs = self._parse_ranges(self.ranges_var.get(), total_pages)
                except Exception as e:
                    log(f"❌ Range parse error for {pdf_name}: {e}")
                    prog((file_index / total_files) * 100)
                    continue

            for start, end in jobs:
                out_name = f"{prefix}_{base_name}_p{start:03d}-p{end:03d}.pdf"
                out_path = os.path.join(output_root, out_name)

                if is_live:
                    try:
                        writer = PdfWriter()
                        for page_num in range(start - 1, end):
                            writer.add_page(reader.pages[page_num])

                        with open(out_path, "wb") as f:
                            writer.write(f)

                        log(f"✅ Created: {out_name}")
                    except Exception as e:
                        log(f"❌ Failed writing {out_name}: {e}")
                else:
                    log(f"🔎 Would create: {out_name}")

            log("")

            prog((file_index / total_files) * 100)

        log("-" * 40)
        log("✅ PDF splitting complete.")
