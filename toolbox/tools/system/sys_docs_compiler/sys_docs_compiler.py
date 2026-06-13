from __future__ import annotations

import argparse
import io
import tkinter as tk
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tkinter import filedialog, ttk

from core.base_tool import BaseTool
from .compiler_engine import run as compiler_run


class SysDocsCompilerTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.target_var = None
        self.config_var = None
        self.mode_var = None

    def get_name(self):
        return "Tree-Aware Docs Compiler"

    def build_ui(self, parent):
        ttk.Label(
            parent,
            text="Compile documentation-worthy Markdown into a disposable generated docs tree.",
            background="#121a2b",
            foreground="white",
        ).pack(anchor="w", pady=(0, 10))

        self.mode_var = tk.StringVar(value="check")
        self.target_var = tk.StringVar(value="")
        self.config_var = tk.StringVar(value="")

        ttk.Label(parent, text="Mode", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
        mode_row = tk.Frame(parent, bg="#121a2b")
        mode_row.pack(fill="x", pady=(0, 10))

        for label, value in [("Check", "check"), ("Build", "build"), ("Fix", "fix")]:
            tk.Radiobutton(
                mode_row,
                text=label,
                variable=self.mode_var,
                value=value,
                bg="#121a2b",
                fg="white",
                selectcolor="#182338",
                activebackground="#121a2b",
                activeforeground="white",
            ).pack(side="left", padx=(0, 12))

        ttk.Label(parent, text="Generated docs target folder", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
        target_row = tk.Frame(parent, bg="#121a2b")
        target_row.pack(fill="x", pady=(0, 10))
        tk.Entry(target_row, textvariable=self.target_var, bg="#10192a", fg="white", insertbackground="white", relief="flat").pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(target_row, text="Browse", command=self.choose_target).pack(side="left", padx=(8, 0))

        ttk.Label(parent, text="Optional config JSON", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
        config_row = tk.Frame(parent, bg="#121a2b")
        config_row.pack(fill="x")
        tk.Entry(config_row, textvariable=self.config_var, bg="#10192a", fg="white", insertbackground="white", relief="flat").pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(config_row, text="Browse", command=self.choose_config).pack(side="left", padx=(8, 0))

    def choose_target(self):
        selected = filedialog.askdirectory(title="Select generated docs folder")
        if selected:
            self.target_var.set(selected)

    def choose_config(self):
        selected = filedialog.askopenfilename(
            title="Select docs compiler config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.config_var.set(selected)

    def execute(self, target_path, is_live, log, prog):
        del is_live
        self.cancel_requested = False
        self.reset_run_state()

        root = Path(target_path).resolve()
        target = self.target_var.get().strip()
        if not target:
            message = "Choose a generated docs target folder."
            log(f"ERROR: {message}")
            self.set_run_status("failed", message)
            prog(100)
            return

        config = self.config_var.get().strip()
        mode = self.mode_var.get().strip() or "check"
        args = argparse.Namespace(
            root=str(root),
            target=target,
            config=config or None,
            check=mode == "check",
            fix=mode == "fix",
            build=mode == "build",
        )

        log(f"Docs compiler mode: {mode}")
        log(f"Root: {root}")
        log(f"Target: {target}")
        if config:
            log(f"Config: {config}")
        log("-" * 56)
        prog(15)

        buffer = io.StringIO()
        with redirect_stdout(buffer), redirect_stderr(buffer):
            exit_code = compiler_run(args)
        prog(90)

        for line in buffer.getvalue().splitlines():
            log(line)

        if exit_code != 0:
            self.set_run_status("warning", f"Compiler finished with exit code {exit_code}")
        log(f"Exit code: {exit_code}")
        prog(100)
