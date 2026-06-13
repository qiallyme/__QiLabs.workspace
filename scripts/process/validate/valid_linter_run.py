#!/usr/bin/env python3
import subprocess, threading, queue, sys
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parent.parent  # adjust if needed
SCRIPT = ROOT / "housekeeper.py"

def run_housekeeper(dry):
    q = queue.Queue()
    def worker():
        cmd = [sys.executable, str(SCRIPT)]
        if dry: cmd.append("--dry-run")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(proc.stdout.readline, ''):
            q.put(line)
        proc.stdout.close()
        proc.wait()
        q.put(f"\n[Done] Exit code: {proc.returncode}\n")
    return q, threading.Thread(target=worker, daemon=True)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Qi Housekeeper")
        self.geometry("780x520")

        top = ttk.Frame(self); top.pack(fill="x", padx=8, pady=8)
        self.var_dry = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Dry run", variable=self.var_dry).pack(side="left")
        ttk.Button(top, text="Run", command=self.start_run).pack(side="left", padx=6)

        self.text = tk.Text(self, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)

        self.q = None
        self.after(100, self.pump)

    def start_run(self):
        if not SCRIPT.exists():
            messagebox.showerror("Missing", f"Not found: {SCRIPT}")
            return
        self.text.insert("end", f"\n== Run at {datetime.now().isoformat(timespec='seconds')} ==\n")
        self.q, th = run_housekeeper(self.var_dry.get())
        th.start()

    def pump(self):
        if self.q:
            try:
                while True:
                    line = self.q.get_nowait()
                    self.text.insert("end", line)
                    self.text.see("end")
            except queue.Empty:
                pass
        self.after(100, self.pump)

if __name__ == "__main__":
    App().mainloop()
