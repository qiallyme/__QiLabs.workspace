# file: git_push.py
# purpose: Toolbox tool module for Git Push in the dev bucket. Provides GitPushTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from core.base_tool import BaseTool

class GitPushTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        # Windows-specific flag to prevent the CMD window from flashing on screen
        self.creationflags = 0x08000000 if os.name == 'nt' else 0

    def get_name(self):
        return "🐙 Recursive Git Push"

    def build_ui(self, parent):
        ttk.Label(parent, text="Target Branch:", background="#0f0f11", foreground="white").pack(anchor='w', pady=(0, 5))

        self.branch_var = tk.StringVar(value="main")
        tk.Entry(parent, textvariable=self.branch_var, bg="#1c1c1e", fg="white", insertbackground="white", relief="flat").pack(fill='x', pady=(0, 15), ipady=5)

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        branch = self.branch_var.get().strip() or "main"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Recursive Mono Repo Push - [{timestamp}]"
        error_log_path = os.path.join(target_path, "repo_push_errors.log")

        log(f"🚀 STARTING {'LIVE MODE' if is_live else 'DRY RUN'} RECURSIVE PUSH\nTarget: {target_path}\n" + "-"*40)

        git_repos = []
        for root, dirs, files in os.walk(target_path):
            if '.git' in dirs:
                git_repos.append(root)
                dirs.remove('.git')

        if not git_repos:
            log("❌ ERROR: No .git directories found in the target path.")
            return

        git_repos.sort(key=lambda x: x.count(os.sep), reverse=True)
        total_repos = len(git_repos)
        errors_encountered = 0

        log(f"Found {total_repos} repositories. Processing bottom-up...\n")

        for i, repo in enumerate(git_repos):
            if self.cancel_requested:
                log("\n🛑 CANCELED BY USER.")
                break

            prog(int(((i) / total_repos) * 100))
            rel_path = os.path.relpath(repo, target_path)
            display_path = "ROOT REPO" if rel_path == "." else rel_path

            log(f"\n📁 [{i+1}/{total_repos}] {display_path}")

            if not is_live:
                log(f"   [DRY RUN] Would run: git add .")
                log(f"   [DRY RUN] Would run: git commit -m \"{commit_msg}\"")
                log(f"   [DRY RUN] Would run: git push origin {branch} --force")
                continue

            try:
                # 1. git add .
                log("   -> git add .")
                subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True, creationflags=self.creationflags)

                # 2. git commit -m
                log(f"   -> git commit -m \"{commit_msg}\"")
                commit_res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo, capture_output=True, text=True, creationflags=self.creationflags)

                # Print the commit stats (e.g., "3 files changed, 10 insertions...")
                if commit_res.stdout:
                    log(f"      {commit_res.stdout.strip()}")

                if commit_res.returncode != 0 and "nothing to commit" not in commit_res.stdout.lower() and "clean" not in commit_res.stdout.lower():
                    raise subprocess.CalledProcessError(commit_res.returncode, commit_res.args, output=commit_res.stdout, stderr=commit_res.stderr)

                # 3. git push
                log(f"   -> git push origin {branch} --force")
                push_res = subprocess.run(["git", "push", "origin", branch, "--force"], cwd=repo, capture_output=True, text=True, creationflags=self.creationflags)

                # Git push outputs its progress (Enumerating objects, etc) to stderr.
                if push_res.stderr:
                    log(f"      {push_res.stderr.strip()}")
                if push_res.stdout:
                    log(f"      {push_res.stdout.strip()}")

                # Manually check for errors since we aren't using check=True here
                if push_res.returncode != 0:
                    raise subprocess.CalledProcessError(push_res.returncode, push_res.args, output=push_res.stdout, stderr=push_res.stderr)

                log("   ✅ Push successful.")

            except subprocess.CalledProcessError as e:
                errors_encountered += 1
                error_details = e.stderr if e.stderr else e.stdout
                err_msg = f"[{timestamp}] Failed at {display_path}. Error: {error_details.strip()}"

                log(f"   ❌ ERROR: Push failed. Logging to root and continuing...\n      {error_details.strip()}")

                with open(error_log_path, "a", encoding="utf-8") as err_file:
                    err_file.write(err_msg + "\n")

        prog(100)
        log("\n" + "-" * 40)
        if errors_encountered > 0:
            log(f"⚠️ MODULE COMPLETE WITH {errors_encountered} ERRORS.\nReview: {error_log_path}")
        else:
            log("✅ MODULE OPERATION COMPLETE. ALL REPOS PUSHED.")
