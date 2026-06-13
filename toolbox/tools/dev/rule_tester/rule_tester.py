# file: rule_tester.py
# purpose: Toolbox tool module for Rule Tester in the dev bucket. Provides RuleTesterTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

# tools/rule_tester.py
import os
import tkinter as tk
from tkinter import ttk
from rapidfuzz import fuzz

from core.base_tool import BaseTool


class RuleTesterTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.default_rules = (
            "tax, w2, 1099 = Finances/Taxes\n"
            "invoice, receipt = Finances/Invoices\n"
            ".mp4, .mov, video = Media/Videos\n"
            "bbr4821 = Clients/BBR4821\n"
            ".exe, .msi = System/Installers\n"
            "* = Unsorted_Review_Needed\n"
        )
        self.fuzzy_threshold = 70

    def get_name(self):
        return "🧪 Rule Tester"

    def build_ui(self, parent):
        ttk.Label(
            parent,
            text="Routing Rules:",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor="w", pady=(0, 5))

        self.rules_text = tk.Text(
            parent,
            bg="#1c1c1e",
            fg="#32d74b",
            font=("Consolas", 10),
            height=10,
            relief="flat",
            padx=10,
            pady=10
        )
        self.rules_text.pack(fill="x", pady=(0, 8))
        self.rules_text.insert("1.0", self.default_rules)

    def parse_rules(self):
        raw = self.rules_text.get("1.0", tk.END).strip()
        rules = {}

        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            left, right = line.split("=", 1)
            dest = right.strip().strip("/\\")

            for key in left.split(","):
                key = key.strip().lower()
                if key:
                    rules[key] = dest

        return rules

    def execute(self, target_path, is_live, log, prog):
        rules = self.parse_rules()

        files = [
            f for f in os.listdir(target_path)
            if os.path.isfile(os.path.join(target_path, f))
        ]

        if not files:
            log("❌ No files found.")
            return

        total = len(files)
        log("🧪 RULE TESTER")
        log("-" * 40)

        for i, file in enumerate(files, start=1):
            if self.cancel_requested:
                log("🛑 Cancelled by user.")
                break

            name = file.lower()
            _, ext = os.path.splitext(name)

            matched_key = None
            matched_dest = None
            confidence = 100
            method = "none"

            if ext in rules:
                matched_key = ext
                matched_dest = rules[ext]
                method = "extension"
            else:
                for key, dest in rules.items():
                    if key != "*" and not key.startswith(".") and key in name:
                        matched_key = key
                        matched_dest = dest
                        method = "keyword"
                        break

            if not matched_dest:
                best_score = 0
                best_key = None
                best_dest = None

                for key, dest in rules.items():
                    if key == "*" or key.startswith("."):
                        continue

                    score = fuzz.partial_ratio(key, name)
                    if score > best_score:
                        best_score = score
                        best_key = key
                        best_dest = dest

                if best_score >= self.fuzzy_threshold:
                    matched_key = best_key
                    matched_dest = best_dest
                    confidence = best_score
                    method = "fuzzy"

            if not matched_dest and "*" in rules:
                matched_key = "*"
                matched_dest = rules["*"]
                confidence = 0
                method = "fallback"

            log(f"{file}")
            log(f"   method: {method}")
            log(f"   rule: {matched_key}")
            log(f"   confidence: {confidence}%")
            log(f"   destination: {matched_dest}")
            log("")

            prog((i / total) * 100)

        log("-" * 40)
        log("✅ Rule testing complete.")
