from __future__ import annotations

import csv
import json
import os
import tkinter as tk
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import ttk

from core.base_tool import BaseTool


EXPECTED_ROOTS = [
    ".github",
    ".qios",
    ".vscode",
    "00_QiEOS",
    "10_QiOS_Start",
    "20_QiSystem",
    "30_QiServer",
    "40_QiCapture",
    "50_QiNexus",
    "60_QiApps",
    "60_QiConnect",
    "packages",
    "scripts",
    "toolbox",
    "_QUARANTINE_",
]

EXPECTED_QINEXUS_BUCKETS = [
    "00_inbox",
    "01_workbench",
    "02_timeline",
    "03_life",
    "04_people",
    "05_business",
    "06_finance",
    "07_legal",
    "08_tech",
    "09_assets",
    "10_data",
    "11_reference",
    "12_archive",
    "13_system",
]

DUPLICATE_QINEXUS_ROOTS = ["20_qinexus", "30_qiarchive", "40_qisystem", "60_qiconnect"]
GENERATED_NAMES = {
    ".git",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".cache",
    ".wrangler",
    "tmp",
    "temp",
    "site",
}
HEAVY_SCRIPT_DIRS = ["ai", "ingest", "process", "services", "tools", "repo_triage", "archive", "automate"]


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str
    suggestion: str = ""


class QiLabsStructureCheckerTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.long_path_threshold_var = None
        self.fail_on_warn_var = None
        self.report_folder_var = None

    def get_name(self):
        return "QiLabs Structure Checker"

    def build_ui(self, parent):
        ttk.Label(
            parent,
            text="Audit a QiLabs workspace layout and generate a structured findings report.",
            background="#121a2b",
            foreground="white",
        ).pack(anchor="w", pady=(0, 10))

        self.long_path_threshold_var = tk.IntVar(value=240)
        self.fail_on_warn_var = tk.BooleanVar(value=False)
        self.report_folder_var = tk.StringVar(value="00_QiEOS/90_receipts/50_generated_reports")

        for label, variable in [
            ("Long path threshold", self.long_path_threshold_var),
            ("Report folder (relative to selected root)", self.report_folder_var),
        ]:
            ttk.Label(parent, text=label, background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
            tk.Entry(
                parent,
                textvariable=variable,
                bg="#10192a",
                fg="white",
                insertbackground="white",
                relief="flat",
            ).pack(fill="x", ipady=6, pady=(0, 10))

        tk.Checkbutton(
            parent,
            text="Treat warnings as failure in final summary",
            variable=self.fail_on_warn_var,
            bg="#121a2b",
            fg="white",
            selectcolor="#182338",
            activebackground="#121a2b",
            activeforeground="white",
        ).pack(anchor="w")

    def add(self, findings, severity, code, path, message, suggestion=""):
        findings.append(Finding(severity, code, str(path), message, suggestion))

    def check_root(self, root, findings):
        for name in EXPECTED_ROOTS:
            path = root / name
            if not path.exists():
                self.add(findings, "error" if name == "50_QiNexus" else "warn", "missing_root", path, f"Expected root folder missing: {name}")

        allowed = set(EXPECTED_ROOTS) | {".git"}
        for item in root.iterdir():
            if item.is_dir() and item.name not in allowed:
                severity = "info" if item.name.startswith(".") else "warn"
                suggestion = ""
                if item.name == "data":
                    suggestion = "Absorb into 50_QiNexus/My Drive/10_data unless it is active capture/runtime data."
                self.add(findings, severity, "unexpected_root", item, f"Unexpected root folder: {item.name}", suggestion)

    def check_qinexus(self, root, findings):
        my_drive = root / "50_QiNexus" / "My Drive"
        if not my_drive.exists():
            self.add(findings, "error", "missing_mydrive", my_drive, "QiNexus requires 50_QiNexus/My Drive.")
            return

        for name in DUPLICATE_QINEXUS_ROOTS:
            path = my_drive / name
            if path.exists():
                self.add(findings, "warn", "duplicate_root_inside_qinexus", path, f"Duplicate root folder inside My Drive: {name}", "Absorb/remove it into the QiNexus bucket model.")

        for name in EXPECTED_QINEXUS_BUCKETS:
            path = my_drive / name
            if not path.exists():
                self.add(findings, "info", "missing_qinexus_bucket", path, f"QiNexus bucket not found yet: {name}", "Create when needed.")

    def check_generated(self, root, findings, log):
        for index, (dirpath, dirnames, filenames) in enumerate(os.walk(root)):
            if self.cancel_requested:
                return
            if index % 40 == 0:
                log(f"Scanning generated folders: {dirpath}")

            dirnames[:] = [name for name in dirnames if not name.startswith(".") or name in GENERATED_NAMES]
            if "_QUARANTINE_" in dirnames:
                dirnames.remove("_QUARANTINE_")

            path = Path(dirpath)
            if ".git" in path.parts:
                dirnames[:] = []
                continue

            if path.name in GENERATED_NAMES or path.name.startswith("_tmp"):
                self.add(findings, "info", "generated_or_cache_folder", path, f"Generated/cache folder present: {path.name}", "Usually gitignore/delete unless intentionally preserved.")
                dirnames[:] = []
                continue

            for filename in filenames:
                if filename.startswith("."):
                    continue
                if filename.endswith((".pyc", ".tsbuildinfo", ".log")):
                    self.add(findings, "info", "generated_file", path / filename, f"Generated/cache-like file: {filename}", "Usually gitignore/delete.")

    def check_scripts(self, root, findings):
        scripts_root = root / "scripts"
        if not scripts_root.exists():
            return

        for name in HEAVY_SCRIPT_DIRS:
            path = scripts_root / name
            if path.exists():
                self.add(
                    findings,
                    "warn",
                    "scripts_too_heavy",
                    path,
                    f"scripts/{name} looks like real logic.",
                    "Keep scripts thin; move tools to toolbox, capture logic to 40_QiCapture, connectors to 60_QiConnect, server/deploy to 30_QiServer.",
                )

    def check_long_paths(self, root, findings, threshold, log):
        for index, (dirpath, dirnames, filenames) in enumerate(os.walk(root)):
            if self.cancel_requested:
                return
            if index % 40 == 0:
                log(f"Scanning path lengths: {dirpath}")

            dirnames[:] = [name for name in dirnames if name not in GENERATED_NAMES and not name.startswith("_tmp") and not name.startswith(".")]
            if "_QUARANTINE_" in dirnames:
                dirnames.remove("_QUARANTINE_")

            path = Path(dirpath)
            if ".git" in path.parts:
                dirnames[:] = []
                continue

            if len(str(path)) > threshold:
                self.add(findings, "warn", "long_path", path, f"Folder path length is {len(str(path))}.", "Shorten or relocate.")

            for filename in filenames:
                if filename.startswith("."):
                    continue
                file_path = path / filename
                if len(str(file_path)) > threshold:
                    self.add(findings, "warn", "long_path", file_path, f"File path length is {len(str(file_path))}.", "Shorten or relocate.")

    def summarize_findings(self, findings):
        errors = sum(1 for finding in findings if finding.severity == "error")
        warnings = sum(1 for finding in findings if finding.severity == "warn")
        infos = sum(1 for finding in findings if finding.severity == "info")
        return errors, warnings, infos

    def write_reports(self, root, findings):
        report_root = root / self.report_folder_var.get().strip().replace("\\", "/")
        report_root.mkdir(parents=True, exist_ok=True)

        rows = [asdict(finding) for finding in findings]
        (report_root / "qilabs_structure_check.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

        with (report_root / "qilabs_structure_check.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["severity", "code", "path", "message", "suggestion"])
            writer.writeheader()
            writer.writerows(rows)

        errors, warnings, infos = self.summarize_findings(findings)
        lines = [
            "# QiLabs Structure Check",
            "",
            f"- error: {errors}",
            f"- warn: {warnings}",
            f"- info: {infos}",
            "",
        ]
        for finding in findings:
            lines.append(f"## {finding.severity.upper()} - {finding.code}")
            lines.append(f"- Path: `{finding.path}`")
            lines.append(f"- Message: {finding.message}")
            if finding.suggestion:
                lines.append(f"- Suggestion: {finding.suggestion}")
            lines.append("")

        (report_root / "qilabs_structure_check.md").write_text("\n".join(lines), encoding="utf-8")
        return report_root

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        self.reset_run_state()
        root = Path(target_path).resolve()
        findings = []
        try:
            threshold = int(self.long_path_threshold_var.get() or 240)
        except (TypeError, ValueError):
            message = "Long path threshold must be a whole number."
            log(f"ERROR: {message}")
            self.set_run_status("failed", message)
            prog(100)
            return

        log(f"QiLabs structure check {'LIVE' if is_live else 'SCAN'}")
        log(f"Root: {root}")
        log(f"Long path threshold: {threshold}")
        log("-" * 56)

        if not root.exists():
            log(f"ERROR: Root does not exist: {root}")
            prog(100)
            return

        self.check_root(root, findings)
        prog(20)

        if not self.cancel_requested:
            self.check_qinexus(root, findings)
        prog(35)

        if not self.cancel_requested:
            self.check_generated(root, findings, log)
        prog(60)

        if not self.cancel_requested:
            self.check_scripts(root, findings)
            self.check_long_paths(root, findings, threshold, log)
        prog(85)

        if self.cancel_requested:
            log("Canceled before report generation.")
            prog(100)
            return

        errors, warnings, infos = self.summarize_findings(findings)
        log(f"Summary: {errors} errors, {warnings} warnings, {infos} info findings")

        if is_live:
            report_root = self.write_reports(root, findings)
            log(f"Reports written to: {report_root}")
        else:
            preview_root = root / self.report_folder_var.get().strip().replace("\\", "/")
            log(f"Would write reports to: {preview_root}")

        if errors or (self.fail_on_warn_var.get() and warnings):
            self.set_run_status("warning", f"{errors} errors, {warnings} warnings, {infos} info findings")
            log("Result: FAILED policy threshold")
        else:
            log("Result: PASS")

        prog(100)
