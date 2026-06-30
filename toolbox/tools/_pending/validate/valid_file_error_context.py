#!/usr/bin/env python3
"""
Get error history for a file to include in GINA/Cursor context
Usage: python get_file_error_context.py path/to/file.ts
"""

import os
import sys
import argparse
from pathlib import Path
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

def get_file_error_context(file_path: str, limit: int = 10):
    """Get error history for a file formatted for GINA/Cursor context"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("Warning: Supabase not configured")
        return None
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Make path relative
        if os.path.isabs(file_path):
            try:
                rel_path = os.path.relpath(file_path, QIOS_ROOT)
            except ValueError:
                rel_path = file_path
        else:
            rel_path = file_path
        
        # Normalize path separators to forward slashes (for cross-platform consistency)
        rel_path = rel_path.replace('\\', '/')
        
        # Query errors (handle both forward and backslash paths)
        # Try exact match first
        result = supabase.table("dev_error_log").select("*").eq(
            "file_path", rel_path
        ).order("created_at", desc=True).limit(limit).execute()
        
        # If no results, try with backslashes (for legacy data)
        if not result.data:
            backslash_path = rel_path.replace('/', '\\')
            result = supabase.table("dev_error_log").select("*").eq(
                "file_path", backslash_path
            ).order("created_at", desc=True).limit(limit).execute()
        
        errors = result.data or []
        
        if not errors:
            return None
        
        # Format for context
        context = f"## Past Errors in {rel_path}\n\n"
        
        for i, error in enumerate(errors, 1):
            resolved = " (RESOLVED)" if error.get('resolved_at') else ""
            fix_note = ""
            if error.get('fix_summary'):
                fix_note = f" → Fixed: {error['fix_summary']}"
            
            context += f"{i}. **{error['error_type']}**{resolved}: {error['error_message'][:200]}{fix_note}\n"
        
        return context
        
    except Exception as e:
        print(f"Error querying dev history: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Get error context for a file")
    parser.add_argument("file", help="File path")
    parser.add_argument("--limit", type=int, default=10, help="Max errors to return")
    
    args = parser.parse_args()
    
    context = get_file_error_context(args.file, args.limit)
    if context:
        print(context)
    else:
        print("No error history found for this file")

if __name__ == "__main__":
    main()

