#!/usr/bin/env python3
"""
Sync dev errors from Supabase to markdown files in repo
Creates DEV_ERRORS.md files per directory for Cursor context
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load .env from project root
QIOS_ROOT = Path(__file__).parent.parent.parent
env_path = QIOS_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

try:
    from supabase import create_client, Client
except ImportError:
    print("Error: supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

def format_error_markdown(error):
    """Format a single error as markdown"""
    date_str = datetime.fromisoformat(error['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
    resolved_str = ""
    if error.get('resolved_at'):
        resolved_date = datetime.fromisoformat(error['resolved_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        resolved_str = f" *(Resolved: {resolved_date})*"
    
    fix_summary = ""
    if error.get('fix_summary'):
        fix_summary = f"\n**Fix:** {error['fix_summary']}"
    
    tags_str = ""
    if error.get('tags'):
        tags_str = f" `{'` `'.join(error['tags'])}`"
    
    return f"""## {date_str} – {error['error_type']}{resolved_str}

**File:** {error['file_path']}  
**Error:** {error['error_message']}  
**Type:** {error['error_type']}{tags_str}{fix_summary}

"""

def sync_errors_to_markdown(directory: str = None, limit: int = 50):
    """Sync errors to DEV_ERRORS.md files"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("Warning: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        return False
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get recent errors
        query = supabase.table("dev_error_log").select("*").order("created_at", desc=True).limit(limit)
        
        if directory:
            query = query.ilike("file_path", f"{directory}%")
        
        result = query.execute()
        errors = result.data or []
        
        if not errors:
            print("No errors found")
            return True
        
        # Group by directory
        errors_by_dir = {}
        for error in errors:
            file_path = error['file_path']
            # Normalize path separators
            file_path = file_path.replace('\\', '/')
            # Get directory (parent of file)
            dir_path = str(Path(file_path).parent)
            if dir_path == '.':
                dir_path = 'root'
            # Normalize directory path too
            dir_path = dir_path.replace('\\', '/')
            
            if dir_path not in errors_by_dir:
                errors_by_dir[dir_path] = []
            errors_by_dir[dir_path].append(error)
        
        # Write DEV_ERRORS.md to each directory
        files_written = 0
        for dir_path, dir_errors in errors_by_dir.items():
            if dir_path == 'root':
                target_dir = QIOS_ROOT
            else:
                target_dir = QIOS_ROOT / dir_path
            
            # Skip if directory doesn't exist
            if not target_dir.exists():
                continue
            
            dev_errors_file = target_dir / "DEV_ERRORS.md"
            
            # Build markdown content
            content = f"""# Dev Error History

This file is auto-generated from `dev_error_log` table. It provides context for Cursor/GINA about past errors in this directory.

**Last synced:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
            for error in dir_errors:
                content += format_error_markdown(error)
            
            # Write file
            dev_errors_file.write_text(content, encoding='utf-8')
            files_written += 1
            print(f"[OK] Wrote {len(dir_errors)} errors to {dev_errors_file.relative_to(QIOS_ROOT)}")
        
        print(f"\n[OK] Synced {len(errors)} errors to {files_written} DEV_ERRORS.md files")
        return True
        
    except Exception as e:
        print(f"Error syncing errors: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Sync dev errors to markdown files")
    parser.add_argument("--dir", help="Directory to sync (default: all)")
    parser.add_argument("--limit", type=int, default=50, help="Max errors to sync")
    
    args = parser.parse_args()
    
    sync_errors_to_markdown(directory=args.dir, limit=args.limit)

if __name__ == "__main__":
    main()

