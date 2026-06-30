"""
Quick diagnostic script to check worker status.
Run this to see if workers are registered and active.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from db import get_connection

def check_workers():
    """Check worker status in database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("=" * 60)
    print("WORKER STATUS CHECK")
    print("=" * 60)
    
    try:
        # Check if worker_id column exists
        try:
            cursor.execute("SELECT worker_id, worker_name, status, last_heartbeat, meta FROM worker_status ORDER BY worker_name")
            has_worker_id = True
            print("[OK] Using worker_id column (migration 006 applied)")
        except sqlite3.OperationalError:
            cursor.execute("SELECT worker_name, status, last_heartbeat, meta FROM worker_status ORDER BY worker_name")
            has_worker_id = False
            print("[WARN] Using worker_name only (migration 006 not applied)")
        
        rows = cursor.fetchall()
        
        if not rows:
            print("\n[ERROR] NO WORKERS FOUND IN DATABASE")
            print("\nThis means:")
            print("  1. The worker process is not running, OR")
            print("  2. The worker has never called update_worker_status()")
            print("\nTo start the worker:")
            print("  cd workers/local_core")
            print("  python worker.py")
            return
        
        print(f"\nFound {len(rows)} worker(s) in database:\n")
        
        now = datetime.utcnow()
        
        for i, row in enumerate(rows, 1):
            if has_worker_id:
                worker_id = row[0] if row[0] else "N/A"
                worker_name = row[1]
                status = row[2]
                last_heartbeat_str = row[3]
                meta_str = row[4] if len(row) > 4 else "{}"
            else:
                worker_id = f"local_{row[0].lower().replace(' ', '_')}"
                worker_name = row[0]
                status = row[1]
                last_heartbeat_str = row[2]
                meta_str = row[3] if len(row) > 3 else "{}"
            
            # Parse heartbeat time
            try:
                last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace('Z', '+00:00'))
                if last_heartbeat.tzinfo:
                    last_heartbeat = last_heartbeat.replace(tzinfo=None)
                age_seconds = (now - last_heartbeat).total_seconds()
                age_minutes = age_seconds / 60
            except Exception as e:
                age_seconds = None
                age_minutes = None
            
            # Parse meta
            try:
                meta = json.loads(meta_str) if meta_str else {}
            except:
                meta = {}
            
            print(f"Worker #{i}:")
            print(f"  ID: {worker_id}")
            print(f"  Name: {worker_name}")
            print(f"  Status: {status}")
            print(f"  Last Heartbeat: {last_heartbeat_str}")
            if age_seconds is not None:
                if age_seconds < 60:
                    print(f"  Age: {age_seconds:.1f} seconds ago")
                elif age_minutes < 60:
                    print(f"  Age: {age_minutes:.1f} minutes ago")
                else:
                    print(f"  Age: {age_minutes/60:.1f} hours ago")
                
                # Determine if worker is "active"
                if age_seconds < 120:  # 2 minutes
                    print(f"  [ACTIVE] Heartbeat within 2 minutes")
                else:
                    print(f"  [STALE] Heartbeat older than 2 minutes")
            else:
                print(f"  [WARN] Could not parse heartbeat time")
            
            if meta:
                print(f"  Meta: {json.dumps(meta, indent=4)}")
            print()
        
        # Summary
        active_count = 0
        for row in rows:
            if has_worker_id:
                last_heartbeat_str = row[3]
            else:
                last_heartbeat_str = row[2]
            
            try:
                last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace('Z', '+00:00'))
                if last_heartbeat.tzinfo:
                    last_heartbeat = last_heartbeat.replace(tzinfo=None)
                age_seconds = (now - last_heartbeat).total_seconds()
                if age_seconds < 120:
                    active_count += 1
            except:
                pass
        
        print("=" * 60)
        print(f"SUMMARY: {active_count}/{len(rows)} active worker(s)")
        print("=" * 60)
        
        if active_count == 0:
            print("\n[WARN] NO ACTIVE WORKERS")
            print("\nTo start a worker:")
            print("  cd workers/local_core")
            print("  python worker.py")
            print("\nMake sure:")
            print("  - OPENAI_API_KEY is set (for embeddings)")
            print("  - Database is accessible")
            print("  - Worker process is running in a terminal")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    check_workers()

