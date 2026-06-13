"""
Append content to an existing note in realms/qivault/kb.
"""
import os
import sys
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_connection

QIOS_ROOT = Path(__file__).parent.parent.parent.parent


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Append content to an existing vault note.
    
    Args:
        args: {
            "path": str - QiOS-relative path to note
            "content": str - Markdown content to append
        }
        env: Environment context
    
    Returns:
        {
            "path": str
            "appended": bool
        }
    """
    path = args.get("path", "")
    content = args.get("content", "")
    
    if not path:
        raise ValueError("Path is required")
    
    # Ensure path is under realms/qivault/kb
    if not path.startswith("realms/qivault/kb/"):
        raise ValueError("Path must be under realms/qivault/kb/")
    
    # Resolve full path
    file_path = QIOS_ROOT / path
    
    if not file_path.exists():
        raise FileNotFoundError(f"Note not found: {path}")
    
    # Read existing content
    with open(file_path, "r", encoding="utf-8") as f:
        existing = f.read()
    
    # Append content
    updated = existing.rstrip() + "\n\n" + content
    
    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)
    
    # Compute new hash
    content_hash = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    
    # Update filesystem_index
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        now_iso = datetime.utcnow().isoformat()
        stat = file_path.stat()
        last_modified = datetime.utcfromtimestamp(stat.st_mtime).isoformat()
        
        cursor.execute("""
            UPDATE filesystem_index
            SET content_hash = ?,
                last_modified_utc = ?,
                last_scanned_utc = ?,
                size_bytes = ?,
                last_ingested_utc = NULL
            WHERE file_path = ?
        """, (content_hash, last_modified, now_iso, stat.st_size, path))
        
        # Re-enqueue for ingestion
        queue_id = str(uuid.uuid4())
        import json
        cursor.execute("""
            INSERT INTO ingestion_queue (
                id, file_path, slug, realm, mime_type, file_ext,
                content_hash, status, meta, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (
            queue_id,
            path,
            file_path.stem.lower().replace(" ", "_"),
            "QiVault",
            "text/markdown",
            ".md",
            content_hash,
            json.dumps({
                "source": "append_to_vault_note",
            }),
            now_iso,
            now_iso,
        ))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
    
    return {
        "path": path,
        "appended": True
    }

