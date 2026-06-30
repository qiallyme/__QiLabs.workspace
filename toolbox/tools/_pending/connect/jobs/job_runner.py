"""
Job processor for background task execution.
Workers call these functions to execute jobs.
"""
import sys
from pathlib import Path
from typing import Dict, Any
from jobs import update_job_status

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from crawler.vault_crawler import crawl, DEFAULT_CRAWL_ROOTS


def run_vault_crawl_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a vault_crawl job.
    
    Args:
        job: Job dict with 'params' containing 'roots' list
    
    Returns:
        Result dict with statistics
    """
    params = job.get('params', {})
    roots = params.get('roots', DEFAULT_CRAWL_ROOTS)
    
    print(f"[JOB PROCESSOR] Starting vault_crawl job #{job['id']} for roots: {roots}")
    
    try:
        # Run the crawl
        stats = crawl(roots=roots)
        
        result = {
            "scanned_files": stats.get("scanned_files", 0),
            "new_files": stats.get("new_files", 0),
            "changed_files": stats.get("changed_files", 0),
            "enqueued": stats.get("enqueued", 0)
        }
        
        print(f"[JOB PROCESSOR] Vault crawl job #{job['id']} completed: {result}")
        return result
        
    except Exception as e:
        print(f"[JOB PROCESSOR] Vault crawl job #{job['id']} failed: {e}")
        raise


def run_full_reindex_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a full_reindex job.
    This will re-embed all files in the semantic_profile table.
    
    Args:
        job: Job dict
    
    Returns:
        Result dict with statistics
    """
    print(f"[JOB PROCESSOR] Starting full_reindex job #{job['id']}")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all files that need re-embedding
        cursor.execute("""
            SELECT DISTINCT file_path, slug, realm
            FROM semantic_profile
            WHERE file_path IS NOT NULL
        """)
        
        files = cursor.fetchall()
        conn.close()
        
        total_files = len(files)
        reindexed = 0
        errors = []
        
        # For now, just mark them for re-embedding by updating their status
        # The worker loop will pick them up
        conn = get_connection()
        cursor = conn.cursor()
        
        for file_path, slug, realm in files:
            try:
                # Update embedding_status to 'pending' to trigger re-embedding
                cursor.execute("""
                    UPDATE semantic_profile
                    SET embedding_status = 'pending'
                    WHERE file_path = ?
                """, (file_path,))
                reindexed += 1
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        result = {
            "total_files": total_files,
            "reindexed": reindexed,
            "errors": errors[:10]  # Limit error list
        }
        
        print(f"[JOB PROCESSOR] Full reindex job #{job['id']} completed: {result}")
        return result
        
    except Exception as e:
        print(f"[JOB PROCESSOR] Full reindex job #{job['id']} failed: {e}")
        raise


def process_job(job: Dict[str, Any]):
    """
    Process a single job based on its job_type.
    Status changes are automatically logged to system_event via update_job_status.
    
    Args:
        job: Job dict with 'id', 'job_type', 'params', etc.
    """
    job_id = job['id']
    job_type = job['job_type']
    
    # Mark as running (this will log to system_event)
    update_job_status(job_id, 'running')
    
    try:
        # Route to appropriate handler
        if job_type == 'vault_crawl':
            result = run_vault_crawl_job(job)
        elif job_type == 'full_reindex':
            result = run_full_reindex_job(job)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
        
        # Mark as complete (this will log to system_event)
        update_job_status(job_id, 'complete', result=result)
        
    except Exception as e:
        # Mark as failed (this will log to system_event)
        error_message = str(e)
        update_job_status(job_id, 'failed', error_message=error_message)
        raise

