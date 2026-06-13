import shutil
import os

def migrate_qicare():
    src = r"c:\QiLabs\apps\qicare\src"
    dest = r"c:\QiLabs\apps\qi1ne-portal\src\features\qicare"
    
    folders = ["components", "data", "engine", "hooks", "store", "types", "pages"]
    
    for folder in folders:
        src_folder = os.path.join(src, folder)
        dest_folder = os.path.join(dest, folder)
        
        if os.path.exists(src_folder):
            print(f"Migrating {folder}...")
            # If destination exists, remove it to ensure a clean copy
            if os.path.exists(dest_folder):
                shutil.rmtree(dest_folder)
            shutil.copytree(src_folder, dest_folder)
            print(f"Migrated {folder} successfully.")
        else:
            print(f"Skip {folder} (not found in source).")

if __name__ == "__main__":
    migrate_qicare()
