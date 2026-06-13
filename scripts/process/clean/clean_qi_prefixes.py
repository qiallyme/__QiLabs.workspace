import os
import shutil
from pathlib import Path

def rename_and_consolidate(root_path):
    root = Path(root_path)
    if not root.exists():
        print(f"Path not found: {root}")
        return

    # 1. Get all directories
    dirs = [d for d in root.iterdir() if d.is_dir() and d.name != "experiments"]
    
    renames = []
    
    for d in dirs:
        old_name = d.name
        new_name = old_name
        
        # Remove "Qi" prefix (case-insensitive check but specific to Qi)
        if old_name.startswith("Qi"):
            new_name = old_name[2:]
        elif old_name.startswith("qi"):
            new_name = old_name[2:]
            
        if not new_name: # In case the folder was just "Qi"
            continue
            
        if new_name != old_name:
            renames.append((d, new_name))

    # 2. Execute renames with collision handling (merging)
    for old_path, new_name in renames:
        target_path = root / new_name
        
        if target_path.exists() and target_path != old_path:
            print(f"  [MERGE] {old_path.name} -> {new_name} (target exists)")
            # Use the existing merge logic or a simple move if empty
            # For this script, we'll use a simple strategy: move unique items
            for item in old_path.iterdir():
                dest = target_path / item.name
                if dest.exists():
                    # Move with timestamp to avoid overwrite
                    import time
                    ts = int(time.time())
                    dest = target_path / f"{item.stem}_{ts}{item.suffix}"
                
                try:
                    shutil.move(str(item), str(dest))
                except:
                    pass
            
            # Remove old
            try:
                shutil.rmtree(old_path)
            except:
                pass
        else:
            print(f"  [RENAME] {old_path.name} -> {new_name}")
            try:
                old_path.rename(target_path)
            except Exception as e:
                print(f"    Error: {e}")

    # 3. Final Alphabetical List
    final_dirs = sorted([d.name for d in root.iterdir() if d.is_dir() and d.name != "experiments"], key=lambda s: s.lower())
    
    print("\n" + "="*40)
    print("FINAL CONSOLIDATED LIST (A-Z)")
    print("="*40)
    for name in final_dirs:
        print(f"  - {name}")

if __name__ == "__main__":
    target = r"c:\_QiOne_MonoRepo_v2\experiments"
    rename_and_consolidate(target)
