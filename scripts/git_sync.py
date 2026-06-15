#!/usr/bin/env python3
"""
git_sync.py - Automates Git workflows from top to bottom.
Performs: Git Status -> Stage -> Commit -> Pull -> Merge (optional) -> Push.
Can run on a single repository or recursively on all Git repositories under a path.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional


def run_cmd(args: List[str], cwd: Path, dry_run: bool = False) -> subprocess.CompletedProcess:
    """Runs a system command in the specified working directory."""
    if dry_run:
        print(f"  [DRY RUN] Would run: {' '.join(args)} in {cwd}")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False
        )
        return result
    except Exception as e:
        print(f"  [ERROR] Failed to execute {' '.join(args)}: {e}")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr=str(e))


def is_git_installed() -> bool:
    """Checks if Git is installed and accessible in the system path."""
    try:
        res = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False
        )
        return res.returncode == 0
    except Exception:
        return False


def get_current_branch(repo_path: Path) -> Optional[str]:
    """Gets the current active branch name."""
    res = run_cmd(["git", "branch", "--show-current"], cwd=repo_path)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    # Fallback for older git versions
    res = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    if res.returncode == 0 and res.stdout.strip():
        branch = res.stdout.strip()
        if branch != "HEAD":
            return branch
    return None


def is_dirty(repo_path: Path) -> bool:
    """Checks if the working tree has uncommitted local changes."""
    res = run_cmd(["git", "status", "--porcelain"], cwd=repo_path)
    return res.returncode == 0 and bool(res.stdout.strip())


def find_git_repos(root_path: Path) -> List[Path]:
    """
    Recursively scans for Git repositories starting from root_path.
    Intelligently skips standard build, cache, and dependency folders to maximize performance.
    """
    git_repos = []

    # Check if the root directory itself is a Git repository
    if (root_path / ".git").is_dir():
        git_repos.append(root_path)

    skip_dirs = {
        "node_modules", "dist", "build", ".next", ".vite", "__pycache__",
        ".venv", "venv", ".wrangler", ".cache", ".pytest_cache"
    }

    for root, dirs, _ in os.walk(root_path):
        # Modify dirs in-place to avoid traversing skipped directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        if ".git" in dirs:
            repo_path = Path(root)
            if repo_path not in git_repos:
                git_repos.append(repo_path)
            # Remove .git from dirs to prevent walking inside it
            dirs.remove(".git")

    return sorted(git_repos)


def sync_repository(
    repo_path: Path,
    commit_msg: str,
    merge_branch: Optional[str] = None,
    dry_run: bool = False,
    no_push: bool = False,
    no_pull: bool = False
) -> bool:
    """
    Performs the full git sync workflow on a single repository:
    1. Stages and commits local changes (if dirty).
    2. Pulls remote updates (with auto-merge of remote tracking branch).
    3. Merges an optional separate target branch.
    4. Pushes changes back to the remote.
    """
    print(f"\n" + "=" * 60)
    print(f"Syncing Repository: {repo_path}")
    print("=" * 60)

    # 1. Verify Git Repository
    if not (repo_path / ".git").is_dir():
        print(f"[ERROR] '{repo_path}' is not a valid Git repository.")
        return False

    branch = get_current_branch(repo_path)
    if not branch:
        print("[ERROR] Head is detached or current branch name cannot be determined.")
        return False
    print(f"[INFO] Current branch: {branch}")

    # 2. Stage and Commit Local Changes
    if is_dirty(repo_path):
        print("[INFO] Uncommitted changes detected. Staging and committing...")
        # Stage
        add_res = run_cmd(["git", "add", "-A"], cwd=repo_path, dry_run=dry_run)
        if add_res.returncode != 0:
            print(f"[ERROR] Failed to stage changes:\n{add_res.stderr}")
            return False

        # Commit
        commit_res = run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_path, dry_run=dry_run)
        if commit_res.returncode != 0:
            print(f"[ERROR] Commit failed:\n{commit_res.stderr}")
            return False
        print("[SUCCESS] Local changes committed.")
    else:
        print("[INFO] Working tree is clean. Nothing to commit.")

    # 3. Pull Remote Changes
    if not no_pull:
        print(f"[INFO] Pulling updates for '{branch}'...")
        pull_res = run_cmd(["git", "pull", "origin", branch], cwd=repo_path, dry_run=dry_run)
        if pull_res.returncode != 0:
            stderr = pull_res.stderr.lower()
            if "no tracking information" in stderr or "could not read from remote" in stderr or "does not appear to be a git" in stderr:
                print("[WARNING] Remote branch not found on origin. Trying generic 'git pull'...")
                pull_res = run_cmd(["git", "pull"], cwd=repo_path, dry_run=dry_run)

            if pull_res.returncode != 0:
                print(f"[ERROR] Pull failed:\n{pull_res.stderr}")
                if "conflict" in pull_res.stderr.lower() or "merge conflict" in pull_res.stdout.lower():
                    print("[CRITICAL] Merge conflict encountered during pull! Please resolve manually.")
                return False
        print("[SUCCESS] Pull complete.")

    # 4. Merge Separate Branch (optional)
    if merge_branch:
        print(f"[INFO] Merging target branch '{merge_branch}' into '{branch}'...")
        # Fetch target branch changes first
        run_cmd(["git", "fetch", "origin", merge_branch], cwd=repo_path, dry_run=dry_run)

        # Attempt to merge local branch
        merge_res = run_cmd(["git", "merge", merge_branch], cwd=repo_path, dry_run=dry_run)
        if merge_res.returncode != 0:
            print(f"[WARNING] Local merge of '{merge_branch}' failed. Attempting 'origin/{merge_branch}'...")
            merge_res = run_cmd(["git", "merge", f"origin/{merge_branch}"], cwd=repo_path, dry_run=dry_run)

        if merge_res.returncode != 0:
            print(f"[ERROR] Merge failed:\n{merge_res.stderr}")
            if "conflict" in merge_res.stderr.lower() or "merge conflict" in merge_res.stdout.lower():
                print("[CRITICAL] Merge conflict encountered! Aborting merge to restore safe state.")
                run_cmd(["git", "merge", "--abort"], cwd=repo_path, dry_run=dry_run)
            return False
        print(f"[SUCCESS] Merged '{merge_branch}' into '{branch}'.")

    # 5. Push Local and Merged Changes
    if not no_push:
        print(f"[INFO] Pushing changes to remote...")
        push_res = run_cmd(["git", "push", "origin", branch], cwd=repo_path, dry_run=dry_run)
        if push_res.returncode != 0:
            stderr = push_res.stderr.lower()
            if "no upstream branch" in stderr or "has no upstream branch" in stderr:
                print("[WARNING] Upstream branch not set. Attempting push with --set-upstream...")
                push_res = run_cmd(["git", "push", "--set-upstream", "origin", branch], cwd=repo_path, dry_run=dry_run)

            if push_res.returncode != 0:
                print(f"[ERROR] Push failed:\n{push_res.stderr}")
                return False
        print("[SUCCESS] Push complete.")

    print(f"[SUCCESS] Sync of '{repo_path.name}' finished successfully!")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage, Commit, Pull, Merge, and Push Git repositories sequentially."
    )
    parser.path_or_dir = parser.add_argument(
        "--path", "-p",
        default=".",
        help="Path to the Git repository or root folder (default: current directory)."
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Scan recursively for all Git repositories starting at --path and sync each."
    )
    parser.add_argument(
        "--message", "-m",
        default=f"Auto-sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        help="Commit message to use if there are local uncommitted changes."
    )
    parser.add_argument(
        "--merge", "-b",
        metavar="BRANCH",
        help="An optional target branch to merge into the current branch (e.g., 'main')."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the Git workflow steps without applying any changes."
    )
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip pulling remote updates."
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip pushing committed/merged changes to remote."
    )

    args = parser.parse_args()

    # Verify Git is installed
    if not is_git_installed():
        print("[CRITICAL] Git command-line tool is not installed or not in PATH.", file=sys.stderr)
        sys.exit(1)

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"[CRITICAL] Specified path '{args.path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Gather repositories to sync
    repos: List[Path] = []
    if args.recursive:
        print(f"[INFO] Scanning recursively for Git repositories in '{target_path}'...")
        repos = find_git_repos(target_path)
        if not repos:
            print(f"[WARNING] No Git repositories found under '{target_path}'.")
            sys.exit(0)
    else:
        # Check if the path itself is a git repo
        if (target_path / ".git").is_dir():
            repos = [target_path]
        else:
            print(f"[CRITICAL] '{target_path}' is not a Git repository. Use --recursive (-r) to scan subdirectories.", file=sys.stderr)
            sys.exit(1)

    print(f"[INFO] Found {len(repos)} repositories to process.")
    results: List[Tuple[Path, bool]] = []

    for repo in repos:
        success = sync_repository(
            repo_path=repo,
            commit_msg=args.message,
            merge_branch=args.merge,
            dry_run=args.dry_run,
            no_push=args.no_push,
            no_pull=args.no_pull
        )
        results.append((repo, success))

    # Summary report
    print("\n" + "=" * 60)
    print("Execution Summary")
    print("=" * 60)
    failed_any = False
    for repo, success in results:
        status_str = "SUCCESS" if success else "FAILED"
        print(f"- {repo.relative_to(target_path) if repo != target_path else repo.name} : {status_str}")
        if not success:
            failed_any = True

    if failed_any:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
