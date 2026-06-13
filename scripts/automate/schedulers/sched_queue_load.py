#!/usr/bin/env python3
"""
QiOS Queue Loader v1
- Reads fs_scan_events.jsonl
- Inserts/updates ingestion_queue in Supabase
- Handles deduplication by file_path
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

try:
    from supabase import create_client, Client
except ImportError:
    raise SystemExit("Missing dependency: supabase-py. Install with `pip install supabase`.")

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "data" / "outputs" / "fs_scan_events.jsonl"

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def extract_file_metadata(file_path: str):
    """Extract slug, realm, extension, mime type from file path."""
    path_obj = Path(file_path)
    slug = path_obj.stem.lower().replace(" ", "_").replace("-", "_")
    ext = path_obj.suffix.lstrip(".")
    
    # Infer realm from path
    realm_guess = None
    realm_slug = None
    if file_path.startswith("realms/"):
        parts = file_path.split("/")
        if len(parts) >= 2:
            realm_slug = parts[1]
            # Map slug to realm name
            realm_map = {
                "qipersonal": "QiPersonal",
                "qibusiness": "QiBusiness",
                "qiclients": "QiClients",
                "qivault": "QiVault",
                "qilegal": "QiLegal",
                "qiresearch": "QiResearch",
                "qitemp": "QiTemp",
            }
            realm_guess = realm_map.get(realm_slug, "QiVault")
    
    # Simple MIME type mapping
    mime_map = {
        "md": "text/markdown",
        "txt": "text/plain",
        "yaml": "application/x-yaml",
        "yml": "application/x-yaml",
        "json": "application/json",
        "csv": "text/csv",
        "sql": "application/sql",
        "ts": "application/typescript",
        "tsx": "application/typescript",
        "js": "application/javascript",
        "py": "text/x-python",
        "html": "text/html",
        "css": "text/css",
    }
    mime_type = mime_map.get(ext.lower(), "application/octet-stream")
    
    return {
        "slug": slug,
        "realm": realm_guess,
        "realm_slug": realm_slug,
        "file_ext": ext,
        "mime_type": mime_type,
    }

def load_events(events_path: Path, limit: int = None):
    """Load events from JSONL file."""
    events = []
    if not events_path.exists():
        return events
    
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            if limit and len(events) >= limit:
                break
    
    return events

def upsert_queue_item(supabase: Client, event: dict, metadata: dict):
    """Upsert a file into ingestion_queue."""
    file_path = event.get("path", "")
    content_hash = event.get("sha256", "")
    event_type = event.get("event", "")
    
    # Only process file_added and file_changed events
    if event_type not in ("file_added", "file_changed"):
        return None
    
    queue_item = {
        "file_path": file_path,
        "slug": metadata["slug"],
        "realm": metadata.get("realm"),
        "realm_guess": metadata.get("realm"),
        "realm_slug": metadata.get("realm_slug"),
        "mime_type": metadata.get("mime_type"),
        "file_ext": metadata.get("file_ext"),
        "content_hash": content_hash,
        "status": "pending",
        "meta": {
            "scan_trigger": event.get("trigger", "unknown"),
            "scan_timestamp": event.get("ts", now_iso()),
            "event_type": event_type,
        },
    }
    
    # Upsert with conflict on file_path
    result = supabase.table("ingestion_queue").upsert(
        queue_item,
        on_conflict="file_path",
    ).execute()
    
    return result.data[0] if result.data else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(EVENTS_PATH))
    ap.add_argument("--limit", type=int, help="Limit number of events to process")
    ap.add_argument("--dry-run", action="store_true", help="Don't insert, just show what would be inserted")
    args = ap.parse_args()
    
    # Load Supabase credentials from env
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not args.dry_run:
        if not supabase_url or not supabase_key:
            raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables.")
        supabase: Client = create_client(supabase_url, supabase_key)
    else:
        supabase = None
    
    # Load events
    events = load_events(Path(args.events), args.limit)
    
    if not events:
        print("No events to process.")
        return
    
    print(f"Processing {len(events)} events...")
    
    inserted = 0
    skipped = 0
    errors = 0
    
    for event in events:
        file_path = event.get("path", "")
        if not file_path:
            skipped += 1
            continue
        
        try:
            metadata = extract_file_metadata(file_path)
            
            if args.dry_run:
                print(f"Would insert: {file_path} -> {metadata['slug']}")
                inserted += 1
            else:
                result = upsert_queue_item(supabase, event, metadata)
                if result:
                    inserted += 1
                else:
                    skipped += 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            errors += 1
    
    print(f"Queue load complete. inserted={inserted} skipped={skipped} errors={errors}")

if __name__ == "__main__":
    main()

