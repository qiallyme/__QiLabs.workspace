# file: remote_ssh.py
# purpose: Toolbox tool module for Remote Ssh in the system bucket. Provides tool class for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import subprocess
import threading
import shutil
import tkinter as tk
from tkinter import ttk, messagebox


class RemoteSshTool:
    requires_path = False

    def __init__(self):
        self.cancel_requested = False
        self.proc = None
        self.host_var = None
        self.command_text = None

    def get_name(self):
        return "SSH Remote"

    def build_ui(self, parent):
        self.host_var = tk.StringVar(value="qiserver")

        ttk.Label(parent, text="SSH HOST / ALIAS").pack(anchor="w", pady=(0, 4))
        host_entry = tk.Entry(
            parent,
            textvariable=self.host_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Segoe UI", 11),
        )
        host_entry.pack(fill="x", ipady=8, pady=(0, 12))

        ttk.Label(parent, text="REMOTE COMMAND").pack(anchor="w", pady=(0, 4))
        self.command_text = tk.Text(
            parent,
            height=6,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            padx=8,
            pady=8,
        )
        self.command_text.pack(fill="x", pady=(0, 12))
        self.command_text.insert("1.0", "whoami && hostname && pwd")

        btn_row = tk.Frame(parent, bg="#0f0f11")
        btn_row.pack(fill="x", pady=(0, 8))

        tk.Button(
            btn_row,
            text="OPEN INTERACTIVE SHELL",
            command=self.open_interactive_shell,
            bg="#64d2ff",
            fg="black",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="TEST CONNECTION",
            command=self.test_connection_popup,
            bg="#30d158",
            fg="black",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        ).pack(side="left")

    def get_host(self):
        host = self.host_var.get().strip() if self.host_var else ""
        return host or "qiserver"

    def get_command(self):
        if not self.command_text:
            return ""
        return self.command_text.get("1.0", "end-1c").strip()

    def open_interactive_shell(self):
        host = self.get_host()

        try:
            if shutil.which("wt"):
                subprocess.Popen(["wt", "ssh", host])
            else:
                subprocess.Popen([
                    "powershell",
                    "-NoExit",
                    "-Command",
                    f"ssh {host}"
                ])
        except Exception as e:
            messagebox.showerror("SSH Error", f"Failed to open shell:\n{e}")

    def test_connection_popup(self):
        host = self.get_host()

        def worker():
            try:
                result = subprocess.run(
                    ["ssh", host, "whoami && hostname && pwd"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                if result.returncode == 0:
                    messagebox.showinfo("SSH OK", result.stdout.strip())
                else:
                    messagebox.showerror("SSH Failed", result.stderr.strip() or "Unknown SSH error.")
            except Exception as e:
                messagebox.showerror("SSH Error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def execute(self, path, is_live, update_log, update_progress):
        """
        SCAN (dry run)  = test connection only
        EXECUTE (live) = run the command from the text box
        """
        self.cancel_requested = False
        host = self.get_host()

        if is_live:
            remote_cmd = self.get_command()
            if not remote_cmd:
                update_log("❌ ERROR: No remote command entered.")
                return
            label = f"Running on {host}: {remote_cmd}"
        else:
            remote_cmd = "whoami && hostname && pwd"
            label = f"Testing SSH connection to {host}"

        update_log(f"🔌 {label}")
        update_progress(10)

        try:
            self.proc = subprocess.Popen(
                ["ssh", host, remote_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            update_progress(25)

            for line in self.proc.stdout:
                if self.cancel_requested:
                    update_log("⚠️ SSH command cancelled.")
                    self.proc.terminate()
                    break

                update_log(line.rstrip())

            self.proc.wait()

            if self.cancel_requested:
                update_progress(0)
                return

            if self.proc.returncode == 0:
                update_progress(100)
                update_log("✅ SSH task completed.")
            else:
                update_progress(100)
                update_log(f"❌ SSH task failed with exit code {self.proc.returncode}.")

        except Exception as e:
            update_log(f"❌ SSH ERROR: {e}")
            update_progress(0)
        finally:
            self.proc = None
