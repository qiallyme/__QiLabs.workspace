#!/usr/bin/env python3
import subprocess
import os
import sys

# Automatically finds the root directory of your monorepo
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

def run_command(cmd, cwd=None):
    """Helper to run shell commands safely."""
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except subprocess.CalledProcessError:
        print(f"\n❌ Error executing: {' '.join(cmd)}")
        sys.exit(1)

def log_action(action, target_path, details=""):
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    log_file = os.path.join(ROOT_DIR, '..', 'logs', 'scripts.log')
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [CREATOR] {action:<10} | {target_path} {details}\n")

def main():
    print("\n" + "="*60)
    print(" 🚀 Monorepo App & Submodule Initializer")
    print("="*60)

    # 1. The Guide / Reminder
    print("\n🛑 BEFORE WE BEGIN:")
    print("Go to GitHub/GitLab and create a completely EMPTY repository.")
    print("(Do NOT check the box to add a README, .gitignore, or license).")
    
    # 2. Ask for URL
    repo_url = input("\n🔗 Enter the exact Git URL of your new empty repo:\n> ").strip()
    if not repo_url:
        print("⚠️ URL cannot be empty. Exiting.")
        sys.exit(1)

    # Parse repo name from URL (e.g., https://github.com/name/my-client-site.git -> my-client-site)
    repo_name = repo_url.split('/')[-1].replace('.git', '')

    # 3. Categorize the project
    print("\n📂 What type of project is this? (Select 1-4)")
    print("  1. Clients")
    print("  2. Internal")
    print("  3. Private")
    print("  4. Public")
    
    category_map = {'1': 'clients', '2': 'internal', '3': 'private', '4': 'public'}
    cat_choice = input("> ").strip()
    
    if cat_choice not in category_map:
        print("⚠️ Invalid choice. Defaulting to 'internal'.")
        category = 'internal'
    else:
        category = category_map[cat_choice]

    # Build the target path (e.g., apps/clients/my-client-site)
    target_path = f"apps/{category}/{repo_name}"
    abs_target_path = os.path.join(ROOT_DIR, target_path)

    print(f"\n✨ Setting up {repo_name} at {target_path}...")

    # 4. Git Submodule Add (This will clone the empty repo and create the folder)
    print("📥 Linking submodule to monorepo...")
    run_command(["git", "submodule", "add", repo_url, target_path], cwd=ROOT_DIR)

    # 5. Write default README
    print("📝 Writing default README...")
    readme_path = os.path.join(abs_target_path, "README.md")
    with open(readme_path, "w") as f:
        f.write(f"# {repo_name}\n\nAutomated initialization for {category} project.")

    # 6. Init, Commit, and Push inside the new submodule
    print(f"⬆️  Committing and pushing to 'main'...")
    # Force branch name to 'main'
    run_command(["git", "checkout", "-b", "main"], cwd=abs_target_path)
    run_command(["git", "add", "README.md"], cwd=abs_target_path)
    run_command(["git", "commit", "-m", "Initial commit: Add default README"], cwd=abs_target_path)
    run_command(["git", "push", "-u", "origin", "main"], cwd=abs_target_path)

    # 7. Commit the newly bound submodule to the parent monorepo
    print("🔒 Locking submodule into the parent monorepo...")
    run_command(["git", "add", ".gitmodules", target_path], cwd=ROOT_DIR)
    parent_commit_msg = f"chore: initialized {category} app '{repo_name}' as submodule"
    run_command(["git", "commit", "-m", parent_commit_msg], cwd=ROOT_DIR)

    log_action('CREATED', target_path, f"Repo: {repo_url}")

    # Success output
    print("\n" + "="*60)
    print(f"✅ SUCCESS! Your app '{repo_name}' is fully set up.")
    print(f"📁 Location: {target_path}")
    print("🌿 Branch: main (pushed to origin)")
    print("="*60)

if __name__ == "__main__":
    main()