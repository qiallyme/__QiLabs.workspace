"""
Create a new note in realms/qivault/kb.
"""
import os
import sys
import re
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_connection

QIOS_ROOT = Path(__file__).parent.parent.parent.parent
VAULT_KB_PATH = QIOS_ROOT / "realms" / "qivault" / "kb"


def slugify(text: str) -> str:
    """Convert text to a slug (lowercase, underscores, no spaces)."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and hyphens with underscores
    text = re.sub(r'[\s\-]+', '_', text)
    # Remove non-alphanumeric except underscores
    text = re.sub(r'[^a-z0-9_]', '', text)
    # Remove multiple underscores
    text = re.sub(r'_+', '_', text)
    # Remove leading/trailing underscores
    text = text.strip('_')
    return text or "untitled_note"


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Create a new vault note.
    
    Args:
        args: {
            "title": str - Note title
            "content": str - Markdown content
        }
        env: Environment context
    
    Returns:
        {
            "path": str - QiOS-relative path
            "slug": str
            "realm": "QiVault"
        }
    """
    title = args.get("title", "")
    content = args.get("content", "")
    
    if not title:
        raise ValueError("Title is required")
    
    # Ensure vault directory exists
    VAULT_KB_PATH.mkdir(parents=True, exist_ok=True)
    
    # Generate slug and filename
    slug = slugify(title)
    filename = f"{slug}.md"
    file_path = VAULT_KB_PATH / filename
    
    # If file exists, append number
    counter = 1
    while file_path.exists():
        filename = f"{slug}_{counter}.md"
        file_path = VAULT_KB_PATH / filename
        counter += 1
    
    # Generate front matter
    now = datetime.utcnow().isoformat() + "Z"
    front_matter = f"""---
title: "{title}"
slug: "{slug}"
realm: "QiVault"
type: "doc"
node: "concept"
created: "{now}"
updated: "{now}"
---

{content}
"""
    
    # Write file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(front_matter)
    
    # Get relative path
    rel_path = file_path.relative_to(QIOS_ROOT)
    rel_path_str = str(rel_path).replace("\\", "/")
    
    # Compute hash
    content_hash = hashlib.sha256(front_matter.encode("utf-8")).hexdigest()
    
    # Update filesystem_index
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        file_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO filesystem_index (
                id, root_label, realm, file_path, file_ext, mime_type,
                content_hash, last_modified_utc, last_scanned_utc,
                size_bytes, is_ignored
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            file_id,
            "realms_qivault_kb",
            "QiVault",
            rel_path_str,
            ".md",
            "text/markdown",
            content_hash,
            now_iso,
            now_iso,
            len(front_matter.encode("utf-8")),
        ))
        
        # Enqueue for ingestion
        queue_id = str(uuid.uuid4())
        import json
        cursor.execute("""
            INSERT INTO ingestion_queue (
                id, file_path, slug, realm, mime_type, file_ext,
                content_hash, status, meta, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (
            queue_id,
            rel_path_str,
            slug,
            "QiVault",
            "text/markdown",
            ".md",
            content_hash,
            json.dumps({
                "source": "create_vault_note",
                "root_label": "realms_qivault_kb",
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
        "path": rel_path_str,
        "slug": slug,
        "realm": "QiVault"
    }

