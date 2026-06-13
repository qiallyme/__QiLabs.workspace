# Git Pusher

Automatically finds all git repositories under the root directory, stages changes, commits, and force-pushes to `origin/main`.

## Features

- **Auto-discovery**: Scans the entire directory tree from root to find all `.git` directories
- **Automatic manifest**: Rebuilds `git_manifest.json` on every run with detailed results
- **Comprehensive logging**: Appends all operations to `git_pusher.log`
- **Force push**: Uses `--force` flag (configurable)
- **Smart skipping**: Only commits and pushes repos with actual changes

## Usage

From anywhere in your system:

```bash
python tools/git_pusher/git_pusher.py
```

Or from the `git_pusher` directory:

```bash
python git_pusher.py
```

## Configuration

Edit the constants at the top of `git_pusher.py`:

- `TARGET_BRANCH`: Default is `"main"` (change if you use `master` or another branch)
- `FORCE_PUSH`: Default is `True` (set to `False` to disable force push)

## How It Works

1. **Root Detection**: Assumes `ROOT/tools/git_pusher/git_pusher.py` → root is two levels up (`ROOT`)
2. **Repository Discovery**: Walks the entire tree from root, finds all folders containing `.git`
3. **For Each Repo**:
   - Checks if there are changes (`git status --porcelain`)
   - If changes exist:
     - `git add .`
     - `git commit -m "updated YYYY-MM-DD HH:MM:SS"`
     - `git push origin main --force`
4. **Manifest Generation**: Creates/overwrites `git_manifest.json` with:
   - Timestamp of run
   - Root directory scanned
   - Detailed results for each repo (success/failure, commit hash, errors)
5. **Logging**: Appends timestamped entries to `git_pusher.log`

## Output Files

- **`git_manifest.json`**: JSON manifest with full run details
- **`git_pusher.log`**: Timestamped log of all operations

## Safety Notes

⚠️ **Force push is enabled by default**. This will overwrite remote history. Use with caution, especially on shared repositories.

The script skips repos that:
- Have no changes
- Are not valid git repositories
- Fail during `git add` or `git commit`

## Example Manifest Entry

```json
{
  "generated_at": "2025-12-04T20:45:00.123456",
  "root_dir": "C:\\QiOS_v1",
  "repos_processed": [
    {
      "repo_name": "my-repo",
      "repo_path": "C:\\QiOS_v1\\my-repo",
      "timestamp": "2025-12-04T20:45:01.234567",
      "had_changes": true,
      "commit_success": true,
      "commit_msg": "updated 2025-12-04 20:45:01",
      "commit_hash": "abc123def456...",
      "push_success": true,
      "push_error": null
    }
  ]
}
```

