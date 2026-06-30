"""
List files in a realm directory.
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_connection


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    List files under a given realm path.
    
    Args:
        args: {
            "path": str - QiOS-relative path
        }
        env: Environment context
    
    Returns:
        {
            "path": str,
            "files": [
                {
                    "path": str,
                    "size": int,
                    "last_modified_utc": str
                }
            ]
        }
    """
    path = args.get("path", "")
    
    if not path:
        raise ValueError("Path is required")
    
    # Query filesystem_index
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT file_path, size_bytes, last_modified_utc
            FROM filesystem_index
            WHERE file_path LIKE ? AND is_ignored = 0
            ORDER BY file_path
        """, (f"{path}%",))
        
        rows = cursor.fetchall()
        
        files = []
        for row in rows:
            files.append({
                "path": row[0],
                "size": row[1] or 0,
                "last_modified_utc": row[2] or ""
            })
        
        return {
            "path": path,
            "files": files
        }
    
    finally:
        conn.close()

