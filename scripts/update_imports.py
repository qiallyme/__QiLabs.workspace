#!/usr/bin/env python3
"""
Update import paths in migrated scripts to use new package structure.
Run this after migrate_structure.ps1
"""

import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Files that need import updates
FILES_TO_UPDATE = {
    # Step scripts
    "steps/step1_combine.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    "steps/step1_fast_combine.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    "steps/step2_convert.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    "steps/step2_flip.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    "steps/step3_enhance.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    "steps/step3_filter.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    # Core scripts
    "core/check_ffmpeg.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
    # Orchestrator
    "orchestrator.py": {
        "from ffmpeg_utils import": "from scripts.core.ffmpeg_utils import"
    },
}

def update_imports(file_path: Path, replacements: dict):
    """Update imports in a file"""
    if not file_path.exists():
        print(f"  ⚠ Skipping (not found): {file_path}")
        return False
    
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        for old_pattern, new_pattern in replacements.items():
            # Use regex to match the import line
            pattern = re.compile(re.escape(old_pattern), re.MULTILINE)
            content = pattern.sub(new_pattern, content)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"  ✓ Updated: {file_path.name}")
            return True
        else:
            print(f"  - No changes: {file_path.name}")
            return False
    except Exception as e:
        print(f"  ✗ Error updating {file_path}: {e}")
        return False

def main():
    print("Updating import paths in migrated scripts...\n")
    
    updated_count = 0
    for rel_path, replacements in FILES_TO_UPDATE.items():
        file_path = SCRIPT_DIR / rel_path
        print(f"Processing: {rel_path}")
        if update_imports(file_path, replacements):
            updated_count += 1
        print()
    
    print(f"✓ Updated {updated_count} files")
    print("\nNote: You may need to add sys.path modifications for relative imports")
    print("Or use: python -m scripts.orchestrator (from .converter/ directory)")

if __name__ == "__main__":
    main()

