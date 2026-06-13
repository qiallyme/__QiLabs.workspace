"""
Check if a worker is running (via worker_status table or process check).
"""
import os
import subprocess
from typing import Dict, Any
from db import get_connection


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Check worker status.
    
    Args:
        args: {
            "worker_name": str - Optional name of worker to check (if not provided, list all)
        }
        env: Environment context
    
    Returns:
        {
            "workers": list[dict] - List of worker statuses
        }
    """
    worker_name = args.get("worker_name")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if worker_name:
            # Check specific worker
            cursor.execute("""
                SELECT name, status, last_heartbeat, meta
                FROM worker_status
                WHERE name = ?
                ORDER BY last_heartbeat DESC
                LIMIT 1
            """, (worker_name,))
        else:
            # List all workers
            cursor.execute("""
                SELECT name, status, last_heartbeat, meta
                FROM worker_status
                ORDER BY last_heartbeat DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        workers = []
        for row in rows:
            name, status, last_heartbeat, meta_json = row
            workers.append({
                "name": name,
                "status": status,
                "last_heartbeat": last_heartbeat,
                "meta": meta_json
            })
        
        return {
            "workers": workers
        }
    
    except Exception as e:
        return {
            "workers": [],
            "error": f"Failed to check worker status: {str(e)}"
        }

