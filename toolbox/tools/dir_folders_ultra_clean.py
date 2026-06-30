import os
import shutil
import re
from pathlib import Path

def clean_and_normalize_folders(root_path):
    root = Path(root_path)
    if not root.exists():
        print(f"Path not found: {root}")
        return

    # 1. Get all directories
    current_dirs = [d for d in root.iterdir() if d.is_dir() and d.name != "experiments"]
    
    for d in current_dirs:
        old_name = d.name
        
        # 1. Remove "exp" (case-insensitive)
        # We replace "exp_" and "exp" at the start or surrounded by separators
        new_name = re.sub(r'(^exp_|^exp|exp_|_exp)', '', old_name, flags=re.I)
        
        # 2. Remove hyphens and spaces
        new_name = new_name.replace("-", "").replace(" ", "").replace("_", "")
        
        if not new_name: # Safety for empty names
            new_name = f"unnamed_{old_name}"

        if new_name != old_name:
            target_path = root / new_name
            
            # 3. Handle Merge if target exists
            if target_path.exists() and target_path != d:
                print(f"  [MERGE] {old_name} -> {new_name}")
                # Move content from old to new
                for item in d.iterdir():
                    dest = target_path / item.name
                    if dest.exists():
                        import time
                        ts = int(time.time() * 1000) % 10000
                        dest = target_path / f"{item.stem}_{ts}{item.suffix}"
                    try:
                        shutil.move(str(item), str(dest))
                    except:
                        pass
                # Cleanup empty old dir
                try:
                    shutil.rmtree(d)
                except:
                    pass
            else:
                print(f"  [RENAME] {old_name} -> {new_name}")
                try:
                    d.rename(target_path)
                except Exception as e:
                    print(f"    Error renaming {old_name}: {e}")

    # 2. Final Sorted List
    final_list = sorted([d.name for d in root.iterdir() if d.is_dir() and d.name != "experiments"], key=lambda s: s.lower())
    
    print("\n" + "="*50)
    print("ULTRA-CLEAN CONSOLIDATED FOLDER LIST (A-Z)")
    print("="*50)
    for name in final_list:
        print(f"  - {name}")

if __name__ == "__main__":
    target = r"c:\_QiOne_MonoRepo_v2\experiments"
    clean_and_normalize_folders(target)
