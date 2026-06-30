"""
Filesystem Scanner for QiOS Local Core
Walks configured roots, tracks changes, and enqueues files for ingestion.
"""
import os
import sys
import json
import yaml
import hashlib
import uuid
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Optional
from fnmatch import fnmatch

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db import get_connection, run_migrations

QIOS_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = Path(__file__).parent / "fs_scan_config.yaml"


def load_config() -> Dict:
    """Load filesystem scan configuration."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def should_ignore(file_path: Path, ignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on patterns."""
    # Normalize path to use forward slashes for pattern matching
    normalized = str(file_path).replace("\\", "/")
    
    for pattern in ignore_patterns:
        # Remove leading **/ for root-relative matching
        clean_pattern = pattern.lstrip("**/")
        if fnmatch(normalized, pattern) or fnmatch(normalized, f"**/{pattern}"):
            return True
        # Also check if any part of the path matches
        parts = normalized.split("/")
        for i in range(len(parts)):
            subpath = "/".join(parts[i:])
            if fnmatch(subpath, pattern) or fnmatch(subpath, f"**/{pattern}"):
                return True
    
    return False


def matches_include(file_path: Path, include_patterns: List[str]) -> bool:
    """Check if a file matches any include pattern."""
    if not include_patterns:
        return True  # If no includes, match everything
    
    normalized = str(file_path).replace("\\", "/")
    
    for pattern in include_patterns:
        if fnmatch(normalized, pattern) or fnmatch(normalized, f"**/{pattern}"):
            return True
        # Check filename only
        if fnmatch(file_path.name, pattern):
            return True
    
    return False


def compute_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Warning: Failed to hash {file_path}: {e}")
        return ""


def infer_realm(root_path: Path, root_config: Dict, file_path: Path) -> str:
    """Infer realm from file path and root configuration."""
    realm = root_config.get("realm", "")
    
    if realm == "auto":
        # For realms/ path, infer from subdirectory
        if "realms" in str(file_path):
            parts = file_path.parts
            try:
                realms_idx = parts.index("realms")
                if realms_idx + 1 < len(parts):
                    realm_slug = parts[realms_idx + 1]
                    # Convert slug to realm name
                    realm_map = {
                        "qivault": "QiVault",
                        "qibusiness": "QiBusiness",
                        "qiclients": "QiClients",
                        "qipersonal": "QiPersonal",
                        "qipublish": "QiPublish",
                        "qilegal": "QiLegal",
                        "qiresearch": "QiResearch",
                        "qitemp": "QiTemp",
                    }
                    return realm_map.get(realm_slug.lower(), "QiVault")
            except (ValueError, IndexError):
                pass
        return "QiVault"  # Default
    
    return realm


def get_mime_type(file_ext: str) -> str:
    """Get MIME type from file extension."""
    mime_map = {
        ".md": "text/markdown",
        ".mdx": "text/markdown",
        ".txt": "text/plain",
        ".yaml": "application/x-yaml",
        ".yml": "application/x-yaml",
        ".json": "application/json",
        ".csv": "text/csv",
        ".html": "text/html",
        ".py": "text/x-python",
        ".ts": "text/typescript",
        ".ps1": "text/x-powershell",
        ".snippet": "text/plain",
    }
    return mime_map.get(file_ext.lower(), "application/octet-stream")


def scan_root(root_config: Dict, ignore_patterns: List[str], conn) -> Dict:
    """Scan a single root directory."""
    root_path = QIOS_ROOT / root_config["path"]
    root_label = root_config["path"].replace("/", "_").replace("\\", "_")
    
    if not root_path.exists():
        print(f"Warning: Root path does not exist: {root_path}")
        return {
            "root_label": root_label,
            "files_scanned": 0,
            "files_changed": 0,
            "files_new": 0,
            "files_deleted": 0,
            "files_ignored": 0,
        }
    
    include_patterns = root_config.get("include", [])
    cursor = conn.cursor()
    
    # Track what we see in this scan
    seen_paths: Set[str] = set()
    files_new = 0
    files_changed = 0
    files_ignored = 0
    
    # Walk the directory tree
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if not should_ignore(Path(dirpath) / d, ignore_patterns)]
        
        for filename in filenames:
            file_path = Path(dirpath) / filename
            
            # Check if ignored
            if should_ignore(file_path, ignore_patterns):
                files_ignored += 1
                continue
            
            # Check if matches include patterns
            if not matches_include(file_path, include_patterns):
                continue
            
            # Get relative path from QiOS root
            try:
                rel_path = file_path.relative_to(QIOS_ROOT)
            except ValueError:
                # File is outside QiOS root, skip
                continue
            
            rel_path_str = str(rel_path).replace("\\", "/")
            seen_paths.add(rel_path_str)
            
            # Get file stats
            try:
                stat = file_path.stat()
                last_modified = datetime.utcfromtimestamp(stat.st_mtime).isoformat()
                size_bytes = stat.st_size
            except Exception as e:
                print(f"Warning: Failed to stat {file_path}: {e}")
                continue
            
            # Compute hash
            content_hash = compute_hash(file_path)
            if not content_hash:
                continue
            
            # Get file extension and MIME type
            file_ext = file_path.suffix
            mime_type = get_mime_type(file_ext)
            
            # Infer realm
            realm = infer_realm(root_path, root_config, file_path)
            
            # Derive slug from filename
            slug = file_path.stem.lower().replace(" ", "_").replace("-", "_")
            
            # Check if file exists in index
            cursor.execute("""
                SELECT id, content_hash, last_modified_utc, last_ingested_utc
                FROM filesystem_index
                WHERE file_path = ?
            """, (rel_path_str,))
            
            existing = cursor.fetchone()
            now = datetime.utcnow().isoformat()
            
            if existing:
                # File exists in index
                existing_id, existing_hash, existing_mtime, last_ingested = existing
                
                # Check if changed
                if existing_hash != content_hash or existing_mtime != last_modified:
                    # File changed
                    files_changed += 1
                    
                    # Update index
                    cursor.execute("""
                        UPDATE filesystem_index
                        SET content_hash = ?,
                            last_modified_utc = ?,
                            last_scanned_utc = ?,
                            size_bytes = ?,
                            mime_type = ?,
                            file_ext = ?,
                            realm = ?
                        WHERE id = ?
                    """, (content_hash, last_modified, now, size_bytes, mime_type, file_ext, realm, existing_id))
                    
                    # Enqueue for ingestion (if not already pending/in_progress)
                    cursor.execute("""
                        SELECT id FROM ingestion_queue
                        WHERE file_path = ? AND status IN ('pending', 'in_progress')
                    """, (rel_path_str,))
                    
                    if not cursor.fetchone():
                        queue_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO ingestion_queue (
                                id, file_path, slug, realm, mime_type, file_ext,
                                content_hash, status, meta, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                        """, (
                            queue_id,
                            rel_path_str,
                            slug,
                            realm,
                            mime_type,
                            file_ext,
                            content_hash,
                            json.dumps({
                                "source": "fs_scanner",
                                "root_label": root_label,
                                "realm_guess": realm,
                            }),
                            now,
                            now,
                        ))
                        
                        # Update last_ingested_utc to NULL (will be set when ingested)
                        cursor.execute("""
                            UPDATE filesystem_index
                            SET last_ingested_utc = NULL
                            WHERE id = ?
                        """, (existing_id,))
                else:
                    # No change, just update scan time
                    cursor.execute("""
                        UPDATE filesystem_index
                        SET last_scanned_utc = ?
                        WHERE id = ?
                    """, (now, existing_id))
            else:
                # New file
                files_new += 1
                file_id = str(uuid.uuid4())
                
                # Insert into index
                cursor.execute("""
                    INSERT INTO filesystem_index (
                        id, root_label, realm, file_path, file_ext, mime_type,
                        content_hash, last_modified_utc, last_scanned_utc,
                        size_bytes, is_ignored
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    file_id,
                    root_label,
                    realm,
                    rel_path_str,
                    file_ext,
                    mime_type,
                    content_hash,
                    last_modified,
                    now,
                    size_bytes,
                ))
                
                # Enqueue for ingestion
                queue_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO ingestion_queue (
                        id, file_path, slug, realm, mime_type, file_ext,
                        content_hash, status, meta, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """, (
                    queue_id,
                    rel_path_str,
                    slug,
                    realm,
                    mime_type,
                    file_ext,
                    content_hash,
                    json.dumps({
                        "source": "fs_scanner",
                        "root_label": root_label,
                        "realm_guess": realm,
                    }),
                    now,
                    now,
                ))
    
    # Detect deletions: files in index for this root that weren't seen
    cursor.execute("""
        SELECT id, file_path FROM filesystem_index
        WHERE root_label = ? AND is_ignored = 0
    """, (root_label,))
    
    files_deleted = 0
    for row in cursor.fetchall():
        file_id, file_path = row
        if file_path not in seen_paths:
            # File was deleted
            files_deleted += 1
            # Mark as ignored (soft delete) or remove from index
            cursor.execute("""
                UPDATE filesystem_index
                SET is_ignored = 1
                WHERE id = ?
            """, (file_id,))
    
    return {
        "root_label": root_label,
        "files_scanned": len(seen_paths),
        "files_changed": files_changed,
        "files_new": files_new,
        "files_deleted": files_deleted,
        "files_ignored": files_ignored,
    }


def scan_once():
    """Run a single scan of all configured roots."""
    print("Loading configuration...")
    config = load_config()
    roots = config.get("roots", [])
    ignore_patterns = config.get("ignore", [])
    
    print(f"Found {len(roots)} root(s) to scan")
    
    # Run migrations to ensure tables exist
    print("Running migrations...")
    run_migrations()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    scan_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()
    
    print(f"\nStarting scan at {started_at}")
    print("=" * 60)
    
    total_scanned = 0
    total_changed = 0
    total_new = 0
    total_deleted = 0
    total_ignored = 0
    
    for root_config in roots:
        root_path = root_config["path"]
        print(f"\nScanning: {root_path} ({root_config.get('realm', 'auto')})")
        
        try:
            stats = scan_root(root_config, ignore_patterns, conn)
            conn.commit()
            
            total_scanned += stats["files_scanned"]
            total_changed += stats["files_changed"]
            total_new += stats["files_new"]
            total_deleted += stats["files_deleted"]
            total_ignored += stats["files_ignored"]
            
            print(f"  Scanned: {stats['files_scanned']}")
            print(f"  New: {stats['files_new']}")
            print(f"  Changed: {stats['files_changed']}")
            print(f"  Deleted: {stats['files_deleted']}")
            print(f"  Ignored: {stats['files_ignored']}")
        except Exception as e:
            print(f"  Error scanning {root_path}: {e}")
            conn.rollback()
    
    finished_at = datetime.utcnow().isoformat()
    
    # Log scan
    cursor.execute("""
        INSERT INTO filesystem_scan_log (
            id, started_at, finished_at, root_label,
            files_scanned, files_changed, files_new, files_deleted, files_ignored
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scan_id,
        started_at,
        finished_at,
        "all",
        total_scanned,
        total_changed,
        total_new,
        total_deleted,
        total_ignored,
    ))
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"Scan complete at {finished_at}")
    print(f"Total: {total_scanned} files scanned")
    print(f"  New: {total_new}")
    print(f"  Changed: {total_changed}")
    print(f"  Deleted: {total_deleted}")
    print(f"  Ignored: {total_ignored}")


def scan_watch(interval_seconds: int = 60):
    """Run scans continuously with a sleep interval."""
    print(f"Starting watch mode (scanning every {interval_seconds} seconds)")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            scan_once()
            print(f"\nWaiting {interval_seconds} seconds until next scan...")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n\nStopped by user")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan QiOS filesystem and enqueue files for ingestion")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit")
    parser.add_argument("--watch", action="store_true", help="Run scans continuously")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between scans in watch mode (default: 60)")
    
    args = parser.parse_args()
    
    if args.watch:
        scan_watch(args.interval)
    else:
        scan_once()

