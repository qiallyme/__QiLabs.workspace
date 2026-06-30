import os
from pathlib import Path
import shutil

apps_dir = Path(r"C:\QiOS_v1\apps")

# Files that are typically needed in app roots
needed_files = {
    # Config files
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "tsconfig.node.json", "vite.config.ts", "vite.config.js",
    "tailwind.config.js", "tailwind.config.cjs", "postcss.config.js", "postcss.config.cjs",
    "vite-env.d.ts", "index.html", "LICENSE",
    
    # Documentation (main README is needed, others might be legacy)
    "README.md", "readme.md", "_readme.md",
    
    # Source directories
    "src", "app", "components", "public", "static", "templates", "styles",
    "api", "hooks", "utils", "types", "legacy", "node_modules",
    
    # Build/system files
    ".gitignore", ".git", ".env", ".env.example",
    
    # Other common needed files
    "main.jsx", "App.tsx", "index.css", "styles.css", "manifest.json",
    "captain-definition-app-server", "captain-definition-client",
    "docker-compose.yml", "Dockerfile", ".dockerignore",
    "commitlint.config.js", "turbo.json", "pnpm-workspace.yaml",
    "vitest.config.ts", "keydb.conf", "template.env", "postgres-init.sql",
}

# Patterns for likely legacy files
legacy_patterns = [
    # Old config files
    r".*\.config\.js\.timestamp.*",
    r".*\.old$",
    r".*\.bak$",
    r".*\.backup$",
    r".*\.orig$",
    
    # Old documentation (already merged)
    r".*\.md$",  # We'll check if it's not README
    
    # Test/temp files
    r".*test\.py$",
    r".*\.tmp$",
    r".*\.temp$",
    
    # Desktop/system files
    r"desktop\.ini$",
    r"Thumbs\.db$",
    r"\.DS_Store$",
]

def is_needed_file(filepath, app_root):
    """Check if a file is needed in the app root"""
    filename = filepath.name
    
    # Directories are generally needed (except .legacy)
    if filepath.is_dir():
        if filename == ".legacy":
            return True  # Keep .legacy itself
        return True  # Keep all directories for now
    
    # Check against needed files list
    if filename in needed_files:
        return True
    
    # README variants are needed
    if filename.lower() in ["readme.md", "readme.txt", "_readme.md"]:
        return True
    
    # Check if it matches legacy patterns
    import re
    for pattern in legacy_patterns:
        if re.match(pattern, filename, re.IGNORECASE):
            return False
    
    # If it's a markdown file that's not README, it might be legacy
    if filename.endswith('.md') and 'readme' not in filename.lower():
        return False
    
    # Unknown files - be conservative, keep them
    return True

def cleanup_app_root(app_path):
    """Clean up a single app's root directory"""
    if not app_path.exists() or not app_path.is_dir():
        return
    
    legacy_dir = app_path / ".legacy"
    legacy_dir.mkdir(exist_ok=True)
    
    legacy_files = []
    
    # Check all files in root (not subdirectories)
    for item in app_path.iterdir():
        # Skip .legacy directory itself
        if item.name == ".legacy":
            continue
        
        # Skip if it's a directory (we're only checking root files)
        if item.is_dir():
            continue
        
        # Check if file is needed
        if not is_needed_file(item, app_path):
            legacy_files.append(item)
    
    return legacy_files, legacy_dir

# Main execution
print("=" * 80)
print("CLEANING UP APP ROOT DIRECTORIES")
print("=" * 80)

# Get main apps
main_apps = ["QiBP", "QiDocs", "QiLauncher", "QiNote", "QiStory", "QiAppStore"]

# Also check _QiLabs apps
qilabs_dir = apps_dir / "_QiLabs"
qilabs_apps = []
if qilabs_dir.exists():
    for app_dir in qilabs_dir.iterdir():
        if app_dir.is_dir() and not app_dir.name.startswith('.'):
            qilabs_apps.append(app_dir)

all_apps = [(apps_dir / app, app) for app in main_apps] + [(app, app.name) for app in qilabs_apps]

total_moved = 0

for app_path, app_name in all_apps:
    if not app_path.exists():
        continue
    
    print(f"\n{app_name}:")
    legacy_files, legacy_dir = cleanup_app_root(app_path)
    
    if legacy_files:
        print(f"  Found {len(legacy_files)} legacy files:")
        for file_path in legacy_files:
            dest = legacy_dir / file_path.name
            # Handle name conflicts
            counter = 1
            while dest.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                dest = legacy_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            try:
                shutil.move(str(file_path), str(dest))
                print(f"    → Moved: {file_path.name} → .legacy/{dest.name}")
                total_moved += 1
            except Exception as e:
                print(f"    ✗ Error moving {file_path.name}: {e}")
    else:
        print(f"  No legacy files found")

print("\n" + "=" * 80)
print(f"COMPLETE: Moved {total_moved} files to .legacy folders")
print("=" * 80)

