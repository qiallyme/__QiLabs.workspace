#!/usr/bin/env python3
import subprocess
import sys

# ==========================================
# CONFIGURATION
# ==========================================
# ⚠️ Update these paths! Make sure to keep the trailing slash '/' at the end.
LOCAL_DIR = "c:/QiLabs/"
GDRIVE_DIR = "G:/My Drive/Backups/QiLabs/"

# Add any folders/files you want to ignore (e.g., node_modules, .git, .venv)
EXCLUDES = [
    "node_modules/", 
    ".git/", 
    ".venv/", 
    "__pycache__/",
    ".DS_Store"
]
# ==========================================

def run_rsync(source, destination, is_push):
    print(f"\n🚀 Starting sync...\n   From: {source}\n   To:   {destination}\n")
    
    # Base command
    cmd = ["rsync", "-avu"]
    
    # Add excludes
    for exc in EXCLUDES:
        cmd.extend(["--exclude", exc])
        
    # Add delete flag ONLY for pushing (Local -> GDrive)
    if is_push:
        cmd.append("--delete")
        print("⚠️  Warning: '--delete' is active. Files removed locally will be removed on GDrive.")
    
    cmd.extend([source, destination])
    
    # Execute the command
    try:
        # subprocess.run will print the rsync output directly to your terminal
        subprocess.run(cmd, check=True)
        print("\n✅ Sync completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during sync. Rsync exited with code {e.returncode}")
    except FileNotFoundError:
        print("\n❌ Error: 'rsync' command not found. Are you sure it is installed?")

def main():
    while True:
        print("\n" + "="*45)
        print(" 🔄 Dev Folder Sync Tool (Local ↔ GDrive)")
        print("="*45)
        print("  1. ⬆️  Push: Local ➔ GDrive (Backup local changes)")
        print("  2. ⬇️  Pull: GDrive ➔ Local (Get cloud changes)")
        print("  3. ❌  Exit")
        print("="*45)
        
        choice = input("\nSelect an option (1-3): ").strip()
        
        if choice == '1':
            run_rsync(LOCAL_DIR, GDRIVE_DIR, is_push=True)
            break # Exits the script after running
        elif choice == '2':
            run_rsync(GDRIVE_DIR, LOCAL_DIR, is_push=False)
            break # Exits the script after running
        elif choice == '3':
            print("Exiting. Have a great day coding!")
            sys.exit(0)
        else:
            print("⚠️ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()