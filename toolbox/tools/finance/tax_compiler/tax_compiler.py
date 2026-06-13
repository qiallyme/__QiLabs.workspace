# file: tax_compiler.py
# purpose: Toolbox tool module for Tax Compiler in the finance bucket. Provides TaxPdfCompilerTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image
from pillow_heif import register_heif_opener
from core.base_tool import BaseTool

# Register HEIF opener so Pillow can read iPhone .HEIC files natively
register_heif_opener()

class TaxPdfCompilerTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False

    def get_name(self):
        return "📄 Tax PDF Compiler"

    def build_ui(self, parent):
        # UI Variables
        self.max_dim_var = tk.IntVar(value=1800)
        self.quality_var = tk.IntVar(value=75)
        self.grayscale_var = tk.BooleanVar(value=False)

        # Settings Group
        ttk.Label(parent, text="COMPRESSION SETTINGS", background="#0f0f11", foreground="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0, 5))

        # Max Dimension Input
        dim_frame = tk.Frame(parent, bg="#0f0f11")
        dim_frame.pack(fill='x', pady=2)
        ttk.Label(dim_frame, text="Max Dimension (px):", background="#0f0f11", foreground="white", width=20).pack(side='left')
        tk.Entry(dim_frame, textvariable=self.max_dim_var, bg="#1c1c1e", fg="white", insertbackground="white", relief="flat", width=10).pack(side='left', ipady=3)
        ttk.Label(dim_frame, text="(1500-2200 is best for readability)", background="#0f0f11", foreground="#666666", font=("Segoe UI", 8)).pack(side='left', padx=(10, 0))

        # Quality Input
        qual_frame = tk.Frame(parent, bg="#0f0f11")
        qual_frame.pack(fill='x', pady=2)
        ttk.Label(qual_frame, text="JPEG Quality (1-100):", background="#0f0f11", foreground="white", width=20).pack(side='left')
        tk.Entry(qual_frame, textvariable=self.quality_var, bg="#1c1c1e", fg="white", insertbackground="white", relief="flat", width=10).pack(side='left', ipady=3)

        # Grayscale Toggle
        tk.Checkbutton(
            parent,
            text="Convert to Grayscale (Saves massive space, keeps text readable)",
            variable=self.grayscale_var,
            bg="#0f0f11",
            fg="white",
            selectcolor="#1c1c1e",
            activebackground="#0f0f11",
            activeforeground="white"
        ).pack(anchor="w", pady=(10, 8))

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        supported_formats = ('.png', '.jpg', '.jpeg', '.heic')

        # Find all supported images
        image_files = [f for f in os.listdir(target_path) if f.lower().endswith(supported_formats)]

        if not image_files:
            log("❌ No supported images (.png, .jpg, .heic) found in the target directory.")
            prog(100)
            return

        # Sort alphabetically to keep tax forms in page order
        image_files.sort()
        total_files = len(image_files)

        log(f"📄 TAX PDF COMPILER {'LIVE' if is_live else 'DRY RUN'}")
        log(f"Found {total_files} images to process in: {target_path}")
        log("-" * 40)

        max_dim = self.max_dim_var.get()
        quality = self.quality_var.get()
        to_gray = self.grayscale_var.get()

        processed_images = []

        # Phase 1: Process Images
        for i, file_name in enumerate(image_files, start=1):
            if self.cancel_requested:
                log("🛑 Cancelled by user. Halting image processing.")
                break

            file_path = os.path.join(target_path, file_name)

            if not is_live:
                log(f"🔎 Would resize and append: {file_name}")
            else:
                try:
                    with Image.open(file_path) as img:
                        # Convert to Grayscale if requested, otherwise ensure RGB for PDF
                        if to_gray:
                            img = img.convert('L') # Convert to grayscale
                            img = img.convert('RGB') # PDF rendering works best if bundled as RGB, even if visually gray
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')

                        # Resize maintaining aspect ratio
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                        # Save to memory list
                        processed_images.append(img.copy())
                        log(f"✅ Processed: {file_name}")

                except Exception as e:
                    log(f"❌ Error processing {file_name}: {e}")

            # Scale progress up to 90% (leaving 10% for the PDF compilation step)
            prog((i / total_files) * 90)

        # Phase 2: Compile PDF
        if is_live and processed_images and not self.cancel_requested:
            log("⏳ Compiling images into final PDF (This may take a moment)...")
            output_pdf_path = os.path.join(target_path, "Compiled_Tax_Documents.pdf")

            first_image = processed_images[0]
            other_images = processed_images[1:]

            try:
                first_image.save(
                    output_pdf_path,
                    "PDF",
                    resolution=100.0,
                    save_all=True,
                    append_images=other_images,
                    optimize=True,
                    quality=quality
                )

                # Check file size
                file_size_mb = os.path.getsize(output_pdf_path) / (1024 * 1024)
                log(f"🎉 Done! PDF saved as: Compiled_Tax_Documents.pdf")
                log(f"📊 Final File Size: {file_size_mb:.2f} MB")

                if file_size_mb > 25.0:
                    log("⚠️ Warning: File is still over 25MB. Try lowering the max dimension or enabling grayscale.")

            except Exception as e:
                log(f"❌ Error saving final PDF: {e}")

        prog(100)
        log("-" * 40 + "\n✅ MODULE OPERATION COMPLETE.\n")
