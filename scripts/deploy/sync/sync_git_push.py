#!/usr/bin/env python3
import os
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple

# -----------------------------
# CONFIG
# -----------------------------

# Branch to push to; change if you use something else.
TARGET_BRANCH = "main"

# Whether to force push. This was True, but we'll set it to False for safety.
FORCE_PUSH = False

# -----------------------------
# PATHS
# -----------------------------

SCRIPT_PATH = Path(__file__).resolve()
# Assumes: ROOT/tools/git_pusher/git_pusher.py → ROOT is parents[2]
ROOT_DIR = SCRIPT_PATH.parents[3]

TOOLS_DIR = SCRIPT_PATH.parent
MANIFEST_PATH = TOOLS_DIR / "git_manifest.json"
LOG_PATH = TOOLS_DIR / "git_pusher.log"

# -----------------------------
# UTILITIES
# -----------------------------

def log(msg: str) -> None:
    """Append a timestamped line to the log file and print to console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_cmd(cmd: List[str], cwd: Path) -> Tuple[int, str, str]:
    """Run a command in a given directory and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60.0  # Avoid hanging on auth prompts
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired as e:
        return -1, (e.stdout or ""), f"Command timed out after 60s: {str(e)}"
    except Exception as e:
        return -1, "", str(e)



def find_git_repos(root: Path) -> List[Path]:
    """Walk from root and return a list of directories that contain a .git folder."""
    log(f"Scanning for git repos under: {root}")
    repos = []

    for current_root, dirs, files in os.walk(root):
        current_root_path = Path(current_root)

        # Skip the git_pusher tool folder itself
        if current_root_path == TOOLS_DIR:
            # Don't descend further into git_pusher
            dirs[:] = [d for d in dirs if Path(current_root_path, d) != TOOLS_DIR]
            continue

        if ".git" in dirs:
            repos.append(current_root_path)
            # Allow descending further even if this is a repo (to find submodules)
            # dirs[:] = [d for d in dirs if d == ".git"] 


    log(f"Found {len(repos)} git repos.")
    return sorted(repos)


def get_repo_name(path: Path) -> str:
    """Return a readable repo name from path (folder name)."""
    return path.name


def has_changes(repo_path: Path) -> bool:
    """Return True if there are staged or unstaged changes."""
    # Use porcelain so we can detect any change quickly.
    rc, out, err = run_cmd(["git", "status", "--porcelain"], cwd=repo_path)
    if rc != 0:
        log(f"[{repo_path}] git status failed: {err or out}")
        return False
    return bool(out.strip())


def handle_git_lock_file(repo_path: Path) -> bool:
    """
    Check for and handle stale .git/index.lock files.
    Returns True if lock was removed, False otherwise.
    """
    lock_file = repo_path / ".git" / "index.lock"

    if not lock_file.exists():
        return False

    # Check if lock file is stale (older than 5 minutes)
    lock_age = time.time() - lock_file.stat().st_mtime
    stale_threshold = 300  # 5 minutes in seconds

    if lock_age > stale_threshold:
        log(f"[{get_repo_name(repo_path)}] Detected stale git lock file (age: {int(lock_age)}s), removing...")
        try:
            lock_file.unlink()
            log(f"[{get_repo_name(repo_path)}] Lock file removed successfully")
            return True
        except Exception as e:
            log(f"[{get_repo_name(repo_path)}] Failed to remove lock file: {e}")
            return False
    else:
        log(f"[{get_repo_name(repo_path)}] Git lock file exists and appears active (age: {int(lock_age)}s). "
            f"Another git process may be running. Waiting 2 seconds...")
        time.sleep(2)
        # Check again after wait
        if lock_file.exists():
            log(f"[{get_repo_name(repo_path)}] Lock file still exists after wait. Manual intervention may be required.")
            return False
        return True


def git_add_commit_push(repo_path: Path) -> Dict[str, Any]:
    """
    Perform git add ., commit, and push.
    Returns a dict suitable for manifest entry with details.
    """
    repo_name = get_repo_name(repo_path)
    log(f"[{repo_name}] Processing repo at {repo_path}")

    entry: Dict[str, Any] = {
        "repo_name": repo_name,
        "repo_path": str(repo_path),
        "timestamp": datetime.now().isoformat(),
        "had_changes": False,
        "commit_success": False,
        "commit_msg": "",
        "commit_hash": None,
        "push_success": False,
        "push_error": None,
    }

    if not has_changes(repo_path):
        log(f"[{repo_name}] No changes detected; skipping commit and push.")
        return entry

    entry["had_changes"] = True
    commit_msg = f"updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    entry["commit_msg"] = commit_msg

    # git add . (with lock file handling)
    rc, out, err = run_cmd(["git", "add", "."], cwd=repo_path)
    if rc != 0:
        error_msg = err or out
        # Check if this is a lock file error
        if "index.lock" in error_msg.lower() or "another git process" in error_msg.lower():
            log(f"[{repo_name}] Git lock file detected, attempting to resolve...")
            if handle_git_lock_file(repo_path):
                # Retry git add after removing lock
                log(f"[{repo_name}] Retrying git add after lock removal...")
                rc, out, err = run_cmd(["git", "add", "."], cwd=repo_path)
                if rc != 0:
                    log(f"[{repo_name}] git add failed after lock removal: {err or out}")
                    entry["push_error"] = f"git add failed: {err or out}"
                    return entry
            else:
                log(f"[{repo_name}] git add failed: {error_msg}")
                entry["push_error"] = f"git add failed: {error_msg}"
                return entry
        else:
            log(f"[{repo_name}] git add failed: {error_msg}")
            entry["push_error"] = f"git add failed: {error_msg}"
            return entry

    # git commit -m "<msg>"
    rc, out, err = run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_path)
    if rc != 0:
        # If nothing to commit (even though status looked dirty) handle gracefully.
        if "nothing to commit" in (out + err).lower():
            log(f"[{repo_name}] Nothing to commit after add; skipping push.")
            entry["had_changes"] = False  # effectively no-op
            return entry
        else:
            log(f"[{repo_name}] git commit failed: {err or out}")
            entry["push_error"] = f"git commit failed: {err or out}"
            return entry

    entry["commit_success"] = True
    log(f"[{repo_name}] Commit created: {commit_msg}")

    # Get last commit hash
    rc, out, err = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
    if rc == 0:
        entry["commit_hash"] = out.strip()
    else:
        log(f"[{repo_name}] Failed to get commit hash: {err or out}")

    # git push origin main [--force]
    cmd = ["git", "push", "origin", TARGET_BRANCH]
    if FORCE_PUSH:
        cmd.append("--force")

    rc, out, err = run_cmd(cmd, cwd=repo_path)
    if rc != 0:
        log(f"[{repo_name}] git push failed: {err or out}")
        entry["push_error"] = f"git push failed: {err or out}"
    else:
        entry["push_success"] = True
        log(f"[{repo_name}] Pushed to origin/{TARGET_BRANCH} {'(force)' if FORCE_PUSH else ''}")

    return entry


def write_manifest(entries: List[Dict[str, Any]]) -> None:
    """Write the manifest file with full run details."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "root_dir": str(ROOT_DIR),
        "repos_processed": entries,
    }
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log(f"Manifest written to {MANIFEST_PATH}")


# -----------------------------
# MAIN
# -----------------------------

def main() -> None:
    log("========== git_pusher run started ==========")
    log(f"Script path: {SCRIPT_PATH}")
    log(f"Root dir (scan start): {ROOT_DIR}")

    repos = find_git_repos(ROOT_DIR)
    entries: List[Dict[str, Any]] = []

    for repo in repos:
        try:
            entry = git_add_commit_push(repo)
        except Exception as e:
            log(f"[{repo}] ERROR: {e}")
            entry = {
                "repo_name": get_repo_name(repo),
                "repo_path": str(repo),
                "timestamp": datetime.now().isoformat(),
                "had_changes": None,
                "commit_success": False,
                "commit_msg": None,
                "commit_hash": None,
                "push_success": False,
                "push_error": f"Exception: {e}",
            }
        entries.append(entry)

    write_manifest(entries)
    log("========== git_pusher run finished ==========")


if __name__ == "__main__":
    main()
