# file: vault_router.py
# purpose: Toolbox tool module for Vault Router in the organize bucket. Provides VaultRouterTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog
from send2trash import send2trash
from datetime import datetime
from rapidfuzz import fuzz

from core.base_tool import BaseTool


class VaultRouterTool(BaseTool):

    def __init__(self):
        self.cancel_requested = False

        # fuzzy match sensitivity (0-100)
        self.fuzzy_threshold = 70

        self.default_rules = (
            "# Routing Configuration\n"
            "# Format: keyword1, keyword2, .extension = Folder/Subfolder\n"
            "# Use * as fallback\n\n"
            "tax, w2, 1099 = Finances/Taxes\n"
            "invoice, receipt = Finances/Invoices\n"
            ".mp4, .mov, video = Media/Videos\n"
            "bbr4821 = Clients/BBR4821\n"
            ".exe, .msi = System/Installers\n"
            "* = Unsorted_Review_Needed\n"
        )

    def get_name(self):
        return "📥 Vault Auto-Router"

    def build_ui(self, parent):

        ttk.Label(
            parent,
            text="Vault Root Directory (Destination):",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor='w', pady=(0, 5))

        vault_frame = tk.Frame(parent, bg="#0f0f11")
        vault_frame.pack(fill='x', pady=(0, 15))

        self.vault_var = tk.StringVar()

        tk.Entry(
            vault_frame,
            textvariable=self.vault_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(side='left', fill='x', expand=True, ipady=5)

        tk.Button(
            vault_frame,
            text="BROWSE",
            command=self.browse_vault,
            bg="#2c2c2e",
            fg="white",
            relief="flat",
            padx=10
        ).pack(side='right', padx=(10, 0))

        ttk.Label(
            parent,
            text="Routing Rules",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor='w', pady=(0, 5))

        self.rules_text = tk.Text(
            parent,
            bg="#1c1c1e",
            fg="#32d74b",
            font=("Consolas", 10),
            height=8,
            relief="flat",
            padx=10,
            pady=10
        )

        self.rules_text.pack(fill='x', pady=(0, 5))
        self.rules_text.insert("1.0", self.default_rules)

    def browse_vault(self):
        p = filedialog.askdirectory()
        if p:
            self.vault_var.set(p)

    def parse_rules(self):

        raw = self.rules_text.get("1.0", tk.END).strip()
        rules = {}

        for line in raw.split('\n'):

            line = line.strip()

            if not line or line.startswith('#') or '=' not in line:
                continue

            left, right = line.split('=')

            dest = right.strip().strip("/\\")

            for key in left.split(','):
                key = key.strip().lower()
                if key:
                    rules[key] = dest

        return rules

    def fuzzy_route(self, filename, rules):

        name = filename.lower()

        best_score = 0
        best_dest = None

        for key, dest in rules.items():

            if key.startswith('.') or key == '*':
                continue

            score = fuzz.partial_ratio(key, name)

            if score > best_score:

                best_score = score
                best_dest = dest

        if best_score >= self.fuzzy_threshold:
            return best_dest

        return None

    def find_best_route(self, filename, rules):

        name = filename.lower()

        # Extension match first
        _, ext = os.path.splitext(name)

        if ext in rules:
            return rules[ext]

        # direct keyword match
        for key, dest in rules.items():

            if key != '*' and not key.startswith('.'):

                if key in name:
                    return dest

        # fuzzy match
        fuzzy_dest = self.fuzzy_route(name, rules)

        if fuzzy_dest:
            return fuzzy_dest

        # fallback
        if '*' in rules:
            return rules['*']

        return None

    def execute(self, target_path, is_live, log, prog):

        vault_root = self.vault_var.get()

        if not vault_root or not os.path.isdir(vault_root):
            log("❌ ERROR: Select a valid Vault Root Directory.")
            return

        rules = self.parse_rules()

        log(f"🚀 VAULT ROUTER {'LIVE' if is_live else 'DRY RUN'}")
        log("-" * 40)

        files = [
            f for f in os.listdir(target_path)
            if os.path.isfile(os.path.join(target_path, f))
        ]

        total = len(files)

        if total == 0:
            log("✅ Nothing to route.")
            return

        for i, file in enumerate(files):

            if self.cancel_requested:
                log("🛑 Cancelled by user")
                break

            src = os.path.join(target_path, file)

            route = self.find_best_route(file, rules)

            if route:

                dst_dir = os.path.join(vault_root, route)

                if route == "Unsorted_Review_Needed":

                    today = datetime.now().strftime("%Y-%m-%d")
                    filename = f"{today}_{file}"

                else:

                    filename = file

                dst = os.path.join(dst_dir, filename)

                if is_live:

                    try:

                        os.makedirs(dst_dir, exist_ok=True)

                        if os.path.exists(dst):
                            log(f"⚠️ EXISTS: {filename}")
                            continue

                        shutil.copy2(src, dst)

                        if os.path.exists(dst):

                            send2trash(src)

                            log(f"✅ {file} → {route}")

                        else:

                            log(f"❌ COPY FAIL: {file}")

                    except Exception as e:

                        log(f"❌ ERROR {file}: {e}")

                else:

                    log(f"🔎 {file} → {route}")

            prog(((i + 1) / total) * 100)

        log("-" * 40)
        log("✅ Routing complete\n")
