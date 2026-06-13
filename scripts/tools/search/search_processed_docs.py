"""
Search processed documents tool - searches semantic_profile for processed documents.
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_connection


async def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Search for processed documents in semantic_profile.
    
    Args:
        args: {
            "query": str - Search query (searches file_path, slug, realm, content) (optional)
            "realm": str - Filter by realm (optional)
            "limit": int - Maximum number of results (default: 20)
        }
        env: Environment context
    
    Returns:
        {
            "documents": [
                {
                    "file_path": str,
                    "realm": str,
                    "slug": str,
                    "content_preview": str,
                    "created_at": str
                }
            ],
            "total": int,
            "error": str (if failed)
        }
    """
    query = args.get("query", "").strip()
    realm = args.get("realm", "").strip()
    limit = args.get("limit", 20)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build query
        if query and realm:
            cursor.execute("""
                SELECT file_path, realm, slug, content, created_at
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                AND (file_path LIKE ? OR slug LIKE ? OR content LIKE ?)
                AND realm = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", realm, limit))
        elif query:
            cursor.execute("""
                SELECT file_path, realm, slug, content, created_at
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                AND (file_path LIKE ? OR slug LIKE ? OR content LIKE ?)
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        elif realm:
            cursor.execute("""
                SELECT file_path, realm, slug, content, created_at
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                AND realm = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (realm, limit))
        else:
            cursor.execute("""
                SELECT file_path, realm, slug, content, created_at
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        
        # Get total count
        if query and realm:
            cursor.execute("""
                SELECT COUNT(*)
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                AND (file_path LIKE ? OR slug LIKE ? OR content LIKE ?)
                AND realm = ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", realm))
        elif query:
            cursor.execute("""
                SELECT COUNT(*)
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                AND (file_path LIKE ? OR slug LIKE ? OR content LIKE ?)
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        elif realm:
            cursor.execute("""
                SELECT COUNT(*)
                FROM semantic_profile
                WHERE file_path IS NOT NULL
                AND realm = ?
            """, (realm,))
        else:
            cursor.execute("SELECT COUNT(*) FROM semantic_profile WHERE file_path IS NOT NULL")
        
        total = cursor.fetchone()[0]
        conn.close()
        
        documents = []
        for row in rows:
            file_path, realm_val, slug, content, created_at = row
            content_preview = content[:200] if content else ""
            if content and len(content) > 200:
                content_preview += "..."
            
            documents.append({
                "file_path": file_path,
                "realm": realm_val,
                "slug": slug,
                "content_preview": content_preview,
                "created_at": created_at
            })
        
        return {
            "documents": documents,
            "total": total
        }
    
    except Exception as e:
        return {
            "documents": [],
            "total": 0,
            "error": f"Search failed: {str(e)}"
        }

