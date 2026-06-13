import os
import hashlib
import sys
import shutil
import re
import time
import ctypes
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# CONFIGURATION & THEMING
# ==========================================
VERSION = "2.3.1"
BANNER = f"""
##########################################################
#                                                        #
#   🚀 STORAGE BLOAT DESTROYER v{VERSION}                 #
#   [ TURBO-DISCOVERY & DRIVE-AWARE ]                    #
#                                                        #
##########################################################
"""

WEAPONS = {
    "1": "📦 Node Module Warhead (Deletes all node_modules)",
    "2": "🎯 Dup Destroyer Drone (The 4-Sweep Master Engine)",
    "3": "🧹 Cache Cannon (Clears .turbo, .next, .cache, dist, build, etc.)",
    "4": "📝 Log Laser (Vaporizes .log, .bak, .tmp, npm-debug, etc.)",
    "5": "🖥️ System Shrapnel (Removes desktop.ini, lockfiles, tsbuildinfo)",
    "6": "⚖️ Heavy Weight Tracker (Identifies Top 20 Largest Files)",
    "7": "💥 Total Bloat Annihilator (Combines 1, 3, 4, 5)",
    "8": "🧬 Twin Folder Merger (Consolidates 'exp_' twins in experiments)",
    "Q": "❌ Exit Arsenal"
}

# --- GLOBAL PROFILE SETTINGS ---
SETTINGS = {
    "MAX_THREADS": 8,
    "SYNC_DELAY": 0.0,
    "SKIP_OFFLINE": True,
    "DRIVE_TYPE": "LOCAL"
}

IGNORED_FILES = {
    'desktop.ini', 'thumbs.db', '.ds_store', 'package-lock.json', 
    'pnpm-lock.yaml', 'yarn.lock', 'tsconfig.tsbuildinfo'
}
PROTECTED_DIRS = {'.git', '.svn', '.hg', '.vscode', '.idea', '.husky', '.github'}
CACHE_DIRS = {
    '.turbo', '.next', '.astro', 'dist', 'build', 'out', '.pnpm', 
    '.pnpm-store', '.cache', '__pycache__', '.venv', 'venv', 'env', 
    '.pytest_cache', '.vercel', 'target'
}
LOG_PATTERNS = [r'.*\.log$', r'npm-debug\.log.*', r'yarn-error\.log.*', r'.*\.bak\d*$', r'.*\.tmp$']

VIDEO_EXTS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.mpeg', '.mpg', '.media'}
IMAGE_EXTS = {'.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
DOC_EXTS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.rar', '.7z'}
SUPPORTED_FUZZY_EXTS = VIDEO_EXTS | IMAGE_EXTS | DOC_EXTS

GENERIC_NAMES = {'video', 'image', 'movie', 'index', 'output', 'test', 'sample', 'final', 'copy', 'untitled'}

# ==========================================
# ADVANCED DRIVE SENSING & PATH UTILS
# ==========================================

def get_volume_name(drive_path):
    if os.name != 'nt': return ""
    try:
        vol = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(drive_path), vol, ctypes.sizeof(vol), None, None, None, None, 0)
        return vol.value
    except: return ""

def is_placeholder(path):
    if os.name != 'nt': return False
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        return attrs != -1 and (attrs & 0x1000 or attrs & 0x400 or attrs & 0x00400000)
    except: return False

def apply_profile(profile_type):
    if profile_type == "CLOUD":
        SETTINGS.update({"DRIVE_TYPE": "CLOUD", "MAX_THREADS": 4, "SYNC_DELAY": 0.6, "SKIP_OFFLINE": True})
    elif profile_type == "USB":
        SETTINGS.update({"DRIVE_TYPE": "USB", "MAX_THREADS": 4, "SYNC_DELAY": 0.1, "SKIP_OFFLINE": False})
    else:
        SETTINGS.update({"DRIVE_TYPE": "LOCAL", "MAX_THREADS": 8, "SYNC_DELAY": 0.0, "SKIP_OFFLINE": False})

def detect_drive_profile(path):
    p_lower = path.lower()
    drive_root = os.path.splitdrive(path)[0] + "\\"
    vol_label = get_volume_name(drive_root).lower()
    cloud_k = ["google drive", "gdrive", "onedrive", "dropbox", "icloud", "sync", "cloud"]
    if any(k in p_lower for k in cloud_k) or any(k in vol_label for k in cloud_k):
        apply_profile("CLOUD")
        return f"🌩️ CLOUD SYNC DRIVE (Detected: '{vol_label or path}')"
    if os.name == 'nt' and drive_root:
        dtype = ctypes.windll.kernel32.GetDriveTypeW(drive_root)
        if dtype == 2: # REMOVABLE
            apply_profile("USB")
            return "🔌 USB / EXTERNAL DRIVE"
    apply_profile("LOCAL")
    return "🏠 LOCAL STORAGE (Direct Access)"

# ==========================================
# CORE UTILITIES
# ==========================================

def safe_remove_directory(path):
    if not os.path.exists(path): return False
    try:
        if SETTINGS["DRIVE_TYPE"] == "CLOUD":
            print(f"  [☁️ CLOUD PURGE] Wiping {path}...", end="", flush=True)
            shutil.rmtree(path)
            print(" DONE.")
        else:
            print(f"  [⚡ SWEEPING] Purging {path}...", end="", flush=True)
            shutil.rmtree(path)
            print(" DONE.")
        return True
    except Exception as e:
        print(f" FAILED. ({e})")
        return False

def safe_remove_file(path):
    try:
        if os.path.exists(path): os.remove(path); return True
    except: pass
    return False

def get_file_hash(file_path, skip_header=0, chunk_size=256 * 1024):
    if SETTINGS["SKIP_OFFLINE"] and is_placeholder(file_path): return None
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            if skip_header > 0: f.seek(min(skip_header, os.path.getsize(file_path)))
            while chunk := f.read(chunk_size): hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except: return None

def get_triple_fingerprint(file_path):
    if SETTINGS["SKIP_OFFLINE"] and is_placeholder(file_path): return None
    try:
        size = os.path.getsize(file_path)
        if size <= 256 * 1024: return get_file_hash(file_path)
        hash_sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            hash_sha.update(f.read(64 * 1024))
            f.seek(size // 2); hash_sha.update(f.read(64 * 1024))
            f.seek(size - 64 * 1024); hash_sha.update(f.read(64 * 1024))
        return hash_sha.hexdigest()
    except: return None

def get_clean_basename(filename):
    name, ext = os.path.splitext(filename)
    cleaned = re.sub(r'[\(\[\s]copy[\)\]\s]', '', name, flags=re.I)
    cleaned = re.sub(r'[\s\-_\.]+([vV]\d+|\d+|HD|4K|1080p|720p|copy|副本)', '', cleaned)
    cleaned = re.sub(r'[\(\[\s]\d+[\)\]\s]', '', cleaned)
    cleaned = cleaned.strip().lower()
    if not cleaned or len(cleaned) < 3 or cleaned in GENERIC_NAMES:
        return name.strip().lower(), ext.lower()
    return cleaned, ext.lower()

def print_progress(current, total, label="Progress"):
    percent = (current / total) * 100
    bar = ('#' * int(percent // 5)).ljust(20)
    sys.stdout.write(f"\r  {label}: [{bar}] {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()
    if current == total: print()

# ==========================================
# TURBO-DISCOVERY ENGINE
# ==========================================

def fast_discovery(root_dir, find_dirs=False, target_dir_names=None, find_files=False):
    """
    Optimized directory crawler using os.scandir().
    Allows targeted discovery and pruning.
    """
    results = []
    folders_checked = 0
    target_dir_names = [t.lower() for t in target_dir_names] if target_dir_names else []

    print(f"Starting discovery engine...", end="", flush=True)

    stack = [root_dir]
    while stack:
        current_dir = stack.pop()
        folders_checked += 1

        if folders_checked % 100 == 0:
            sys.stdout.write(f"\r🔍 Indexing {folders_checked} folders... Detected {len(results)} items...")
            sys.stdout.flush()

        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    if entry.is_dir():
                        dname = entry.name.lower()

                        # Check if this is a directory we specifically want to find
                        if find_dirs and dname in target_dir_names:
                            results.append(entry.path)
                            continue # Successfully found a target dir, we don't need to go inside it

                        # Pruning: Skip system and cache dirs based on the mission context
                        if dname in PROTECTED_DIRS or (dname in CACHE_DIRS and not find_dirs):
                            continue

                        stack.append(entry.path)
                    elif find_files:
                        if entry.name.lower() in IGNORED_FILES: continue
                        if SETTINGS["SKIP_OFFLINE"] and is_placeholder(entry.path): continue

                        try:
                            f_info = entry.stat()
                            results.append({
                                'path': entry.path,
                                'name': entry.name,
                                'size': f_info.st_size
                            })
                        except: pass
        except: pass

    print(f"\nDone. Found {len(results)} items across {folders_checked} folders.")
    return results

# ==========================================
# WEAPONS
# ==========================================

def node_module_warhead(root_dir):
    print("\n[💣 LAUNCHING NODE MODULE WARHEAD]")
    targets = fast_discovery(root_dir, find_dirs=True, target_dir_names=['node_modules'])

    if not targets:
        print("No node_modules found. Workspace is already clean.")
        return

    print(f"Initiating terminal purge of {len(targets)} targets...")
    c = 0
    for t in targets:
        if safe_remove_directory(t):
            c += 1
            if SETTINGS["SYNC_DELAY"] > 0: time.sleep(SETTINGS["SYNC_DELAY"])

    print(f"\nPurge Complete. {c} node_modules folders destroyed.")

def dup_destroyer_drone(root_dir):
    print(f"\n[🎯 DEPLOYING DUP DESTROYER DRONE - Mode: {SETTINGS['DRIVE_TYPE']}]")
    indexed = fast_discovery(root_dir, find_files=True)
    if not indexed: return

    def report_and_action(groups, label, risk_warning, enforce_quarantine=False):
        if not groups:
            print(f"\n[Sweep: {label}] No matches found.")
            return

        print(f"\n[Sweep: {label}] Results:")
        print("-" * 50)

        q_dir = os.path.join(root_dir, "_QUARANTINE_")
        valid_groups = []
        for paths in groups:
            paths = [p for p in paths if os.path.exists(p)]
            if len(paths) < 2: continue
            paths.sort(key=lambda x: os.path.getmtime(x))
            print(f"\n  [KEEP] (Oldest) {paths[0]}")
            for p in paths[1:]: print(f"  [DUPE]          {p}")
            valid_groups.append(paths)

        if not valid_groups: return
        act = input(f"\nAction for {label} (d=delete, q=quarantine, s=skip): ").lower().strip()

        if act in ['d', 'q']:
            if enforce_quarantine and act == 'd':
                print("⛔ ERROR: Direct deletion blocked. Use Quarantine."); return
            c = 1
            for paths in valid_groups:
                for p in paths[1:]:
                    if not os.path.exists(p): continue
                    if act == 'd':
                        if safe_remove_file(p):
                            print(f"    DELETED: {p}")
                            if SETTINGS["SYNC_DELAY"] > 0: time.sleep(SETTINGS["SYNC_DELAY"])
                    else:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        q_name = f"{timestamp}_{c:03d}_{os.path.basename(p)}"
                        dest = os.path.join(q_dir, q_name)
                        if not os.path.exists(q_dir): os.makedirs(q_dir)
                        try:
                            shutil.move(p, dest)
                            print(f"    QUARANTINED: {p}")
                            c += 1
                            if SETTINGS["SYNC_DELAY"] > 0: time.sleep(SETTINGS["SYNC_DELAY"])
                        except: pass
            print(f"\nSuccessfully handled {c-1 if act=='q' else len(valid_groups)} files.")

    # Sweep 1: 100% Exact
    print("\nSweep 1: Checking for 100% Bit-for-Bit matches...")
    sz_map = defaultdict(list)
    for f in indexed: sz_map[f['size']].append(f['path'])
    potentials = [p for paths in sz_map.values() if len(paths) > 1 for p in paths]

    triage_map = defaultdict(list)
    if potentials:
        with ThreadPoolExecutor(max_workers=SETTINGS["MAX_THREADS"]) as ex:
            futs = {ex.submit(get_triple_fingerprint, p): p for p in potentials}
            done = 0
            for fut in as_completed(futs):
                p, h = futs[fut], fut.result()
                if h: triage_map[h].append(p)
                done += 1; print_progress(done, len(potentials), "Triage Filter")

    exact_map = defaultdict(list)
    final_p = [p for paths in triage_map.values() if len(paths) > 1 for p in paths]
    if final_p:
        with ThreadPoolExecutor(max_workers=SETTINGS["MAX_THREADS"]) as ex:
            futs = {ex.submit(get_file_hash, p): p for p in final_p}
            done = 0
            for fut in as_completed(futs):
                p, h = futs[fut], fut.result()
                if h: exact_map[h].append(p)
                done += 1; print_progress(done, len(final_p), "Deep Hash Scan")
    report_and_action([p for h, p in exact_map.items() if len(p) > 1], "Sweep 1: 100% Exact", "")


# ==========================================
# MAIN INTERFACE
# ==========================================
def main():
    print(BANNER)
    user_target = input("Enter target path to secure (or Enter for current): ").strip().strip('"').strip("'")
    target = os.path.abspath(user_target) if user_target else os.getcwd()
    if not os.path.exists(target):
        print(f"❌ ERROR: Invalid Path."); return

    profile_msg = detect_drive_profile(target)
    print(f"\n[SYSTEM SENSING COMPLETE]")
    print(f"📍 Target: {target}")
    print(f"🛠️  Detected: {profile_msg}")

    print("\n[FORCE OVERRIDE?]")
    print("  [1] Leave as detected")
    print("  [2] Force CLOUD Profile")
    print("  [3] Force USB Profile")
    print("  [4] Force LOCAL Profile")

    override = input("\nSelect profile (Enter to keep current): ").strip()
    if override == "2": apply_profile("CLOUD")
    elif override == "3": apply_profile("USB")
    elif override == "4": apply_profile("LOCAL")

    print(f"\n--- ACTIVE SETTINGS ---")
    print(f"  Discovery Mode: TURBO SCANDIR")
    print(f"  Hashing Threads: {SETTINGS['MAX_THREADS']}")
    print(f"  Sync Delay: {SETTINGS['SYNC_DELAY']}s")
    print(f"  Skip Offline: {'✅ YES' if SETTINGS['SKIP_OFFLINE'] else '❌ NO'}")

    while True:
        print(f"\n--- ARSENAL SELECTION ---")
        for k, v in WEAPONS.items(): print(f"  [{k}] {v}")
        choice = input("\nSelect weapon: ").upper().strip()

        if choice == "1":
            node_module_warhead(target)
        elif choice == "2":
            dup_destroyer_drone(target)
        elif choice == "3":
            print("\n[🧹 DEPLOYING CACHE CANNON]")
            targets = fast_discovery(target, find_dirs=True, target_dir_names=list(CACHE_DIRS))
            if not targets:
                print("No cache folders found.")
            else:
                print(f"Found {len(targets)} cache targets.")
                for t in targets:
                    safe_remove_directory(t)
                print("Cache Purge Complete.")
        elif choice == "4":
            print("\n[📝 DEPLOYING LOG LASER]")
            indexed = fast_discovery(target, find_files=True)
            for f in indexed:
                for p in LOG_PATTERNS:
                    if re.match(p, f['name'], re.I):
                        if safe_remove_file(f['path']): print(f"  Vaporized: {f['path']}")
            print("Log Laser Sweep Complete.")
        elif choice == "5":
            print("\n[🖥️ DEPLOYING SYSTEM SHRAPNEL]")
            indexed = fast_discovery(target, find_files=True)
            for f in indexed:
                if f['name'].lower() in IGNORED_FILES:
                    if safe_remove_file(f['path']): print(f"  Extracted: {f['path']}")
            print("System Shrapnel Cleanup Complete.")
        elif choice == "6":
            print("\n[⚖️ DEPLOYING HEAVY WEIGHT TRACKER]")
            indexed = fast_discovery(target, find_files=True)
            indexed.sort(key=lambda x: x['size'], reverse=True)
            print("\nTop 20 Heaviest Files:")
            for i, f in enumerate(indexed[:20]):
                name = f['path']
                print(f"{i+1:2d}. [{f['size'] / (1024*1024):.2f} MB] {name}")
        elif choice == "7":
            print("\n[💥 LAUNCHING TOTAL BLOAT ANNIHILATOR]")
            print("Combining Node Modules, Cache, Logs, and System Shrapnel sweeps...")
            
            # 1. Node Modules
            targets = fast_discovery(target, find_dirs=True, target_dir_names=['node_modules'])
            for t in targets: safe_remove_directory(t)
            
            # 3. Cache
            targets = fast_discovery(target, find_dirs=True, target_dir_names=list(CACHE_DIRS))
            for t in targets: safe_remove_directory(t)
            
            # 4 & 5. Logs & System Shrapnel
            indexed = fast_discovery(target, find_files=True)
            for f in indexed:
                is_junk = False
                name_lower = f['name'].lower()
                
                # Check patterns (Logs, backups, tmp)
                for p in LOG_PATTERNS:
                    if re.match(p, name_lower, re.I):
                        is_junk = True; break
                
                # Check specific files (System junk, lockfiles)
                if not is_junk and name_lower in IGNORED_FILES:
                    is_junk = True
                
                if is_junk:
                    if safe_remove_file(f['path']): print(f"  Vaporized: {f['path']}")
            
            print("\n[✅ ANNIHILATION COMPLETE] Workspace is now lean.")

        elif choice == "8":
            print("\n[🧬 DEPLOYING TWIN FOLDER MERGER]")
            exp_path = os.path.join(target, "experiments")
            if not os.path.exists(exp_path):
                print(f"❌ Error: 'experiments' folder not found in {target}")
            else:
                try:
                    import subprocess
                    script_path = os.path.join(target, "scripts", "python", "merge_experiment_twins.py")
                    subprocess.run(["python", script_path], check=True)
                except Exception as e:
                    print(f"❌ Merge failed: {e}")

        elif choice == "Q":
            print("Exiting Arsenal. Stay safe out there.")
            break
        else:
            print("⚠️ Invalid Selection. Please pick 1, 2, 3, 4, 5, 6, or Q.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation aborted by user.")
        sys.exit(0)
