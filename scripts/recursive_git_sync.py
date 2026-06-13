import os
import subprocess

def run_git_commands(repo_path):
    print(f"\n--- Syncing Repo: {repo_path} ---")
    try:
        # Check for changes
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True)
        if not status.stdout.strip():
            print("No changes to sync.")
            # Still try to push in case of local commits
        else:
            print("Changes detected. Committing...")
            subprocess.run(["git", "add", "."], cwd=repo_path)
            subprocess.run(["git", "commit", "-m", "QiOne Portal Consolidation: Auto-sync"], cwd=repo_path)
        
        # Push
        print("Pushing...")
        result = subprocess.run(["git", "push"], cwd=repo_path, capture_output=True, text=True)
        if result.returncode == 0:
            print("Push successful.")
        else:
            print(f"Push failed: {result.stderr}")
            
    except Exception as e:
        print(f"Error syncing {repo_path}: {e}")

def recursive_sync(root_dir):
    git_repos = []
    for root, dirs, files in os.walk(root_dir):
        if ".git" in dirs:
            git_repos.append(root)
            # Don't recurse into .git but do recurse into subdirectories
            # Actually, os.walk will continue into subdirectories which might have their own .git
            pass
    
    # Sort by depth (deepest first)
    git_repos.sort(key=lambda x: x.count(os.sep), reverse=True)
    
    for repo in git_repos:
        run_git_commands(repo)

if __name__ == "__main__":
    recursive_sync(r"c:\QiLabs")
