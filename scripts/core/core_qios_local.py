"""
QiOS Local Core - FastAPI service for local-first brain
Complete backend: /health, /queue, /workers, /ingest, /ingest/{id}, /query, /gina/chat
"""
import os
import json
import hashlib
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Load .env file from project root
try:
    from dotenv import load_dotenv
    QIOS_ROOT = Path(__file__).parent.parent.parent
    env_path = QIOS_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[CONFIG] Loaded .env from {env_path}")
    else:
        print(f"[CONFIG] .env file not found at {env_path}, using system environment variables")
except ImportError:
    print("[CONFIG] python-dotenv not installed, using system environment variables only")

from db import get_connection, run_migrations
from frontmatter_utils import ensure_frontmatter
from models import (
    IngestRequest, IngestResponse, IngestStatusResponse,
    QueryRequest, QueryResponse, QueryResult,
    GinaChatRequest, GinaChatResponse, ToolSuggestion,
    ToolInvokeRequest, ToolInvokeResponse,
    QueueContext, WorkerContext, HealthContext, GinaChatContext,
    GinaTTSRequest, SourceReference,
    JobCreateRequest, JobResponse,
    DevCodeAssistRequest, DevCodeAssistResponse,
    Note, NoteCreate, NoteUpdate, NoteAssistRequest, NoteAssistResponse
)
from rag import search_semantic_profile_async
from gina_prompt import GINA_SYSTEM_PROMPT
from memory import GinaMemory
from tools import list_tools as list_tools_impl
from jobs import create_job, get_job, list_jobs, update_job_status, format_job_state_for_prompt
from dev_error_helpers import get_recent_errors_for_file, format_errors_for_prompt

# OpenAI client (optional - falls back to Ollama if not available)
try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("[GINA] OpenAI package not installed. Install with: pip install openai")

# Determine DB path (QIOS_ROOT already set above if dotenv loaded, otherwise set it here)
if 'QIOS_ROOT' not in locals():
    QIOS_ROOT = Path(__file__).parent.parent.parent
DB_PATH = QIOS_ROOT / "data" / "vector" / "qios_local.db"


# Initialize GINA memory system (global instance)
gina_memory = GinaMemory(stm_max=30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    # Ensure data/vector directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Run migrations
    run_migrations()
    print("[GINA] Memory system initialized (STM max: 30 messages)")
    yield
    # Cleanup (if needed) on shutdown


app = FastAPI(
    title="QiOS Local Core",
    description="Local-first brain for QiOS: ingestion, embeddings, semantic search, GINA",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend
# Get allowed origins from env or use defaults for development
allowed_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
    allow_origin_regex = None
else:
    # Default: use regex to allow any localhost/127.0.0.1 port for development
    # This matches http://localhost:PORT or http://127.0.0.1:PORT
    allowed_origins = []
    allow_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

# Configure CORS middleware
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],  # Allow all methods including OPTIONS
    "allow_headers": ["*"],
    "expose_headers": ["*"],
    "max_age": 3600,
}

if allow_origin_regex:
    cors_kwargs["allow_origin_regex"] = allow_origin_regex
else:
    cors_kwargs["allow_origins"] = allowed_origins

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Include dev history router (if available)
try:
    from api_dev_history import router as dev_history_router
    app.include_router(dev_history_router)
    print("[CONFIG] Dev history API enabled")
except ImportError:
    print("[CONFIG] Dev history API not available (api_dev_history.py not found)")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "QiOS Local Core",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "queue": "/queue",
            "workers": "/workers",
            "ingest": "/ingest",
            "query": "/query",
            "gina_chat": "/gina/chat",
            "gina_note_assist": "/gina/note_assist",
            "notes": "/notes",
            "dev_history": "/dev-history",
        }
    }


@app.get("/health")
async def health():
    """Quick status check."""
    return {"status": "ok", "db_path": str(DB_PATH)}


@app.get("/status")
async def status():
    """
    Unified status endpoint for launcher dashboard.
    Returns health, queue, workers, and integrations status in one call.
    """
    import os
    
    # Get health
    health_data = {"status": "ok", "db_path": str(DB_PATH)}
    
    # Get queue stats
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM ingestion_queue
            GROUP BY status
        """)
        rows = cursor.fetchall()
        status_counts = {
            "pending": 0,
            "processing": 0,
            "complete": 0,
            "error": 0
        }
        for row in rows:
            status = row[0]
            count = row[1]
            if status == "embedded":
                status = "complete"
            elif status == "in_progress":
                status = "processing"
            if status in status_counts:
                status_counts[status] = count
        conn.close()
    except Exception as e:
        status_counts = {"pending": 0, "processing": 0, "complete": 0, "error": 0}
    
    # Get workers
    try:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT worker_id, worker_name, status, last_heartbeat, meta FROM worker_status ORDER BY worker_name")
            has_worker_id = True
        except Exception:
            cursor.execute("SELECT worker_name, status, last_heartbeat, meta FROM worker_status ORDER BY worker_name")
            has_worker_id = False
        
        rows = cursor.fetchall()
        workers_list = []
        for row in rows:
            if has_worker_id:
                worker_id = row["worker_id"] if row["worker_id"] else f"local_{row['worker_name'].lower().replace(' ', '_')}"
                worker_name = row["worker_name"]
                status = row["status"]
                last_heartbeat = row["last_heartbeat"]
                meta_str = row["meta"] if row["meta"] is not None else "{}"
            else:
                worker_id = f"local_{row['worker_name'].lower().replace(' ', '_')}"
                worker_name = row["worker_name"]
                status = row["status"]
                last_heartbeat = row["last_heartbeat"]
                meta_str = row["meta"] if row["meta"] is not None else "{}"
            
            try:
                meta = json.loads(meta_str) if meta_str else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            
            workers_list.append({
                "worker_id": worker_id,
                "worker_name": worker_name,
                "status": status,
                "last_heartbeat": last_heartbeat,
                "meta": meta
            })
        conn.close()
    except Exception:
        workers_list = []
    
    # Get integrations status (env flags)
    integrations = {
        "ollama": {
            "configured": bool(os.getenv("OLLAMA_BASE_URL")),
            "base_url": os.getenv("OLLAMA_BASE_URL", ""),
            "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", ""),
            "llm_model": os.getenv("OLLAMA_LLM_MODEL", ""),
        },
        "supabase": {
            "configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")),
            "url": os.getenv("SUPABASE_URL", ""),
        },
        "openai": {
            "configured": bool(os.getenv("OPENAI_API_KEY")),
        },
    }
    
    return {
        "health": health_data,
        "queue": status_counts,
        "workers": {
            "workers": workers_list,
            "active": len([w for w in workers_list if w["status"] in ["idle", "working"]]),
            "total": len(workers_list),
        },
        "integrations": integrations,
    }


@app.get("/queue")
async def queue():
    """
    Get ingestion queue summary grouped by status.
    Returns normalized status counts: pending, processing, complete, error.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get counts by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM ingestion_queue
            GROUP BY status
        """)
        rows = cursor.fetchall()
        
        # Build status dict with defaults
        status_counts = {
            "pending": 0,
            "processing": 0,
            "complete": 0,
            "error": 0
        }
        
        for row in rows:
            status = row[0]
            count = row[1]
            # Normalize status names (handle legacy 'embedded' and 'in_progress')
            if status == "embedded":
                status = "complete"
            elif status == "in_progress":
                status = "processing"
            if status in status_counts:
                status_counts[status] = count
        
        return status_counts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.get("/queue/items")
async def queue_items(
    limit: int = 20,
    status: Optional[str] = None
):
    """
    Get a sample of queue items for inspection.
    
    Args:
        limit: Maximum number of items to return (default: 20)
        status: Optional filter by status (pending, processing, complete, error)
    
    Returns:
        List of queue items with metadata
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if status:
            cursor.execute("""
                SELECT id, file_path, slug, realm, status, created_at, updated_at, meta
                FROM ingestion_queue
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT id, file_path, slug, realm, status, created_at, updated_at, meta
                FROM ingestion_queue
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            try:
                meta = json.loads(row[7]) if row[7] else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            
            items.append({
                "id": row[0],
                "file_path": row[1],
                "slug": row[2],
                "realm": row[3],
                "status": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "meta": meta
            })
        
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.post("/queue/reset")
async def queue_reset():
    """
    Dev-only endpoint: Clear all items from ingestion_queue.
    Use with caution - this deletes all pending/processing/complete/error items.
    
    Returns:
        {"cleared": true, "deleted": <count>}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM ingestion_queue")
        count = cursor.fetchone()[0]
        
        # Delete all items
        cursor.execute("DELETE FROM ingestion_queue")
        conn.commit()
        
        return {"cleared": True, "deleted": count}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.post("/queue/retry_errors")
async def queue_retry_errors():
    """
    Reset all items with status='error' back to status='pending' so they can be retried.
    
    Returns:
        {"retried": <count>}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Count errors before retry
        cursor.execute("SELECT COUNT(*) FROM ingestion_queue WHERE status = 'error'")
        count = cursor.fetchone()[0]
        
        # Reset error items to pending
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE ingestion_queue
            SET status = 'pending', updated_at = ?
            WHERE status = 'error'
        """, (now,))
        
        conn.commit()
        
        return {"retried": count}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.get("/workers")
async def workers():
    """Get worker status summary."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if worker_id column exists (after migration 006)
        try:
            cursor.execute("SELECT worker_id, worker_name, status, last_heartbeat, meta FROM worker_status ORDER BY worker_name")
            has_worker_id = True
        except Exception:
            # Fallback: worker_id column doesn't exist yet, use worker_name as PK
            cursor.execute("SELECT worker_name, status, last_heartbeat, meta FROM worker_status ORDER BY worker_name")
            has_worker_id = False
        
        rows = cursor.fetchall()
        
        workers_list = []
        for row in rows:
            if has_worker_id:
                worker_id = row["worker_id"] if row["worker_id"] else f"local_{row['worker_name'].lower().replace(' ', '_')}"
                worker_name = row["worker_name"]
                status = row["status"]
                last_heartbeat = row["last_heartbeat"]
                # sqlite3.Row doesn't have .get(), access directly and handle None
                meta_str = row["meta"] if row["meta"] is not None else "{}"
            else:
                worker_id = f"local_{row['worker_name'].lower().replace(' ', '_')}"
                worker_name = row["worker_name"]
                status = row["status"]
                last_heartbeat = row["last_heartbeat"]
                # sqlite3.Row doesn't have .get(), access directly and handle None
                meta_str = row["meta"] if row["meta"] is not None else "{}"
            
            # Parse meta JSON
            try:
                meta = json.loads(meta_str) if meta_str else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            
            workers_list.append({
                "worker_id": worker_id,
                "worker_name": worker_name,
                "status": status,
                "last_heartbeat": last_heartbeat,
                "meta": meta
            })
        
        # Sanity check: ensure workers_list is always a list
        if not isinstance(workers_list, list):
            workers_list = []
        
        return {
            "workers": workers_list
        }
    except Exception as e:
        # Log error but return safe empty structure
        import sys
        print(f"Error in /workers endpoint: {e}", file=sys.stderr)
        return {
            "workers": []
        }
    finally:
        conn.close()


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """Enqueue a file/note for processing."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Generate ID and hash
        ingest_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(request.content.encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        
        # Derive file_ext and mime_type if not provided
        file_ext = request.file_ext or (Path(request.file_path).suffix.lstrip(".") if request.file_path else "")
        mime_type = request.mime_type or ("text/markdown" if file_ext == "md" else "text/plain")
        
        # Insert into ingestion_queue
        cursor.execute("""
            INSERT INTO ingestion_queue (
                id, file_path, slug, qid, realm, mime_type, file_ext,
                content_hash, extracted_text, status, meta, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ingest_id, request.file_path, request.slug, request.qid, request.realm,
            mime_type, file_ext, content_hash, request.content, "pending",
            json.dumps(request.meta or {}), now, now
        ))
        
        # Insert into file_history
        history_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO file_history (
                id, file_path, content_hash, event_type, actor, meta, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id, request.file_path, content_hash, "ingest", "api_ingest",
            json.dumps({"source": "api_ingest", "ingest_id": ingest_id}), now
        ))
        
        conn.commit()
        
        return IngestResponse(ok=True, id=ingest_id)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.get("/ingest/{ingest_id}", response_model=IngestStatusResponse)
async def ingest_status(ingest_id: str = PathParam(..., description="Ingestion ID")):
    """Get status of an ingestion job."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, file_path, slug, realm, status, created_at, updated_at, meta
            FROM ingestion_queue
            WHERE id = ?
        """, (ingest_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ingestion not found")
        
        meta = json.loads(row[7]) if row[7] else {}
        error = meta.get("error")
        
        return IngestStatusResponse(
            id=row[0],
            file_path=row[1],
            status=row[4],
            slug=row[2],
            realm=row[3],
            created_at=row[5],
            updated_at=row[6],
            error=error
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Semantic search over semantic_profile."""
    # TODO: Milestone 3 - implement actual embedding search
    # For now, return empty results
    return QueryResponse(results=[])


@app.post("/jobs", response_model=JobResponse)
async def create_job_endpoint(request: JobCreateRequest):
    """Create a new background job."""
    job_id = create_job(request.job_type, request.params)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create job")
    return JobResponse(**job)


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_endpoint(job_id: int = PathParam(..., description="Job ID")):
    """Get a specific job by ID."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)


@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs_endpoint(
    limit: int = 20,
    job_type: Optional[str] = None
):
    """List recent jobs, newest first."""
    jobs = list_jobs(limit=limit, job_type=job_type)
    return [JobResponse(**job) for job in jobs]


@app.post("/gina/chat", response_model=GinaChatResponse)
async def gina_chat(request: GinaChatRequest):
    """GINA orchestrator-aware chat with system context.
    
    Implements the full contract from gina_chat_contract.md:
    - Validates messages array
    - Injects GINA system prompt
    - Gathers live system context (queue, workers, health)
    - Logs conversation to conversation_history
    - Calls LLM (OpenAI) for response
    - Returns reply + optional context
    
    Optional `with_voice` flag:
    - If `with_voice: true`, this is a hint that the frontend will call /gina/tts separately
    - The response format remains the same (text reply, no embedded audio)
    - Frontend should call POST /gina/tts with the reply text to get audio
    """
    import os
    import re
    try:
        import httpx
        HAS_HTTPX = True
    except ImportError:
        HAS_HTTPX = False
        try:
            import requests
            HAS_REQUESTS = True
        except ImportError:
            HAS_REQUESTS = False
    
    # Validate request
    if not request.messages or len(request.messages) == 0:
        raise HTTPException(status_code=400, detail="Missing or invalid 'messages' array in request body.")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get latest user message for RAG and system state detection
    latest_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            latest_user_message = msg.content
            break
    
    # Detect if user is asking about system state
    system_keywords = ["queue", "workers", "ingest", "embedding", "crawl", "system health", "status"]
    needs_system_state = latest_user_message and any(
        keyword in latest_user_message.lower() for keyword in system_keywords
    )
    
    # Detect heavy requests that should be jobs
    created_job = None
    job_context_message = None
    if latest_user_message:
        text_l = latest_user_message.lower()
        import re
        
        # Vault crawl detection - expanded patterns
        vault_crawl_patterns = [
            "crawl qivault", "rescan qivault", "reindex qivault", "scan qivault",
            "crawl vault", "rescan vault", "reindex vault", "scan vault",
            "crawl and re-embed", "re-embed everything", "re-embed all",
            "index vault", "index qivault", "scan my vault", "scan my files"
        ]
        if any(phrase in text_l for phrase in vault_crawl_patterns):
            # Extract roots if mentioned, otherwise use default
            roots = ["realms/qivault/kb"]  # Default
            if "realms/" in latest_user_message:
                # Try to extract realm paths
                realm_matches = re.findall(r'realms/[^\s]+', latest_user_message)
                if realm_matches:
                    roots = list(set(realm_matches))  # Deduplicate
            
            job_id = create_job("vault_crawl", {"roots": roots})
            created_job = {"job_id": job_id, "job_type": "vault_crawl", "params": {"roots": roots}}
            job_context_message = f"""
A new background job has been created:
- job_type: vault_crawl
- job_id: {job_id}
- roots: {', '.join(roots)}

You have NOT executed this job yourself; a worker will process it asynchronously in the background.
Acknowledge that the job has been queued and tell the user:
1. The job ID ({job_id})
2. What will happen (vault crawl will scan and index files)
3. How to check status ("ask me about job {job_id}" or check the Jobs panel)
4. That you can continue chatting while the job runs
"""
        
        # Full reindex detection - expanded patterns
        elif any(phrase in text_l for phrase in [
            "reindex everything", "full reindex", "re-embed all", "re-embed everything",
            "reindex all", "rebuild index", "rebuild embeddings", "refresh all embeddings",
            "re-embed all files", "reindex all files"
        ]):
            job_id = create_job("full_reindex", {})
            created_job = {"job_id": job_id, "job_type": "full_reindex", "params": {}}
            job_context_message = f"""
A new background job has been created:
- job_type: full_reindex
- job_id: {job_id}

You have NOT executed this job yourself; a worker will process it asynchronously in the background.
Acknowledge that the job has been queued and tell the user:
1. The job ID ({job_id})
2. What will happen (all files will be re-embedded)
3. How to check status ("ask me about job {job_id}" or check the Jobs panel)
4. That you can continue chatting while the job runs
"""
        
        # Job status query detection - expanded patterns
        elif any(phrase in text_l for phrase in [
            "status of job", "job status", "what's running", "what is running",
            "check job", "job #", "how is job", "is job done", "job progress",
            "what jobs", "list jobs", "show jobs", "recent jobs", "running jobs"
        ]):
            # Try to extract job ID
            job_id_match = re.search(r'job[#\s]*(\d+)', text_l)
            if job_id_match:
                job_id = int(job_id_match.group(1))
                job = get_job(job_id)
                if job:
                    created_job = {"job_id": job_id, "job": job}
                    job_state = format_job_state_for_prompt(job)
                    job_context_message = f"""
The user is asking about job #{job_id}. Here is the current status:

{job_state}

Provide a clear, conversational status update. If the job is complete, summarize the results.
If it's running, explain what's happening. If it failed, explain the error clearly.
"""
            else:
                # List recent jobs
                recent_jobs = list_jobs(limit=5)
                if recent_jobs:
                    created_job = {"recent_jobs": recent_jobs}
                    # Format each job using the helper
                    job_list = "\n".join([
                        format_job_state_for_prompt(j) for j in recent_jobs
                    ])
                    job_context_message = f"""
The user is asking about job status. Here are the recent jobs:

{job_list}

Provide a summary of what's running or recently completed. Highlight any jobs that are currently running.
"""
    
    # Step 1: RAG Search (always run for all queries)
    rag_results = []
    rag_sources = []
    rag_context_block = None
    retrieval_used = False
    
    if latest_user_message:
        try:
            # Always run RAG search (vector similarity will handle relevance)
            print(f"[GINA] [RAG] Searching for: {latest_user_message[:100]}...")
            rag_results = await search_semantic_profile_async(latest_user_message, limit=8)
            if rag_results:
                retrieval_used = True
                print(f"[GINA] [RAG] Found {len(rag_results)} matches")
                print(f"[GINA] [RAG] Top 3: {[r.get('file_path', 'unknown') for r in rag_results[:3]]}")
                print(f"[GINA] [RAG] Top scores: {[r.get('score', 0.0) for r in rag_results[:3]]}")
                # Build context block with [S1], [S2], etc.
                context_entries = []
                for idx, chunk in enumerate(rag_results, start=1):
                    source_id = f"S{idx}"
                    file_path = chunk.get('file_path', 'unknown')
                    content = chunk.get('content', chunk.get('chunk_text', ''))
                    score = chunk.get('score', 0.0)
                    
                    context_entries.append(
                        f"[{source_id}] File: {file_path} (score={score:.3f})\n"
                        f"Excerpt:\n{content}\n"
                    )
                    rag_sources.append(SourceReference(
                        id=source_id,
                        file_path=file_path,
                        score=score
                    ))
                
                if context_entries:
                    rag_context_block = (
                        "You have the following local context from QiVault and other roots.\n"
                        "Use it as primary evidence when relevant:\n\n" +
                        "\n\n".join(context_entries)
                    )
        except Exception as e:
            print(f"[GINA] [RAG] ERROR: RAG search failed: {e}")
            import traceback
            traceback.print_exc()
            rag_results = []
            # Don't fail silently - this is a critical error
            # The error will be logged in system_event
    
    # Step 2: Gather live system context (only if needed)
    context = None
    try:
        # Get queue state
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM ingestion_queue")
        queue_total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM ingestion_queue
            GROUP BY status
        """)
        queue_rows = cursor.fetchall()
        queue_by_status = {row[0]: row[1] for row in queue_rows}
        
        # Get workers state
        cursor.execute("""
            SELECT worker_name, status, last_heartbeat, meta
            FROM worker_status
            ORDER BY worker_name
        """)
        worker_rows = cursor.fetchall()
        workers_list = []
        for row in worker_rows:
            meta = json.loads(row[3]) if row[3] else {}
            workers_list.append(WorkerContext(
                name=row[0],
                status=row[1],
                last_heartbeat=row[2],
                meta=meta
            ))
        
        # Get realm/vault summaries
        cursor.execute("""
            SELECT realm, COUNT(*) as count
            FROM semantic_profile
            WHERE realm IS NOT NULL
            GROUP BY realm
            ORDER BY count DESC
        """)
        realm_rows = cursor.fetchall()
        realm_summary = {row[0]: row[1] for row in realm_rows}
        
        # Get total processed documents count
        cursor.execute("SELECT COUNT(*) FROM semantic_profile")
        total_processed = cursor.fetchone()[0]
        
        # Get recent processed documents (last 10)
        cursor.execute("""
            SELECT file_path, realm, slug, created_at
            FROM semantic_profile
            WHERE file_path IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """)
        recent_docs = cursor.fetchall()
        
        # Get recent conversation history (last 10 messages for context)
        cursor.execute("""
            SELECT role, content, created_at
            FROM conversation_history
            ORDER BY created_at DESC
            LIMIT 10
        """)
        recent_messages = cursor.fetchall()
        conversation_context = ""
        if recent_messages:
            conversation_context = "\n### Recent Conversation History:\n"
            for msg_row in reversed(recent_messages):  # Reverse to show chronological
                role, content, created = msg_row
                conversation_context += f"- {role}: {content[:200]}{'...' if len(content) > 200 else ''}\n"
        
        # Build health context
        health = HealthContext(
            status="ok",
            runtime="local",
            last_tick=None,  # TODO: Add tick tracking if needed
            layers=None
        )
        
        # Build full context
        context = GinaChatContext(
            queue=QueueContext(
                total=queue_total,
                by_status=queue_by_status
            ),
            workers=workers_list if workers_list else None,
            health=health
        )
        
        conn.close()
    except Exception as e:
        # If context gathering fails, continue without it
        print(f"Warning: Failed to gather system context: {e}")
        context = None
    
    # Step 3: Build system state context (only if user asked about it)
    system_state_context = ""
    if needs_system_state and context:
        # Add realm/vault summaries
        realm_summary_text = ""
        if realm_summary:
            realm_summary_text = "\n### Realm/Vault Summary:\n"
            for realm, count in realm_summary.items():
                realm_summary_text += f"- {realm}: {count} processed documents\n"
        else:
            realm_summary_text = "\n### Realm/Vault Summary:\nNo documents processed yet. Ingest items to populate the index.\n"
        
        # Add recent documents
        recent_docs_text = ""
        if recent_docs:
            recent_docs_text = "\n### Recent Processed Documents (last 10):\n"
            for doc in recent_docs:
                file_path, realm, slug, created = doc
                recent_docs_text += f"- {file_path} (realm: {realm or 'unknown'}, slug: {slug or 'unknown'})\n"
        
        worker_states = []
        if context.workers:
            for w in context.workers:
                state_emoji = "🟢" if w.status == "healthy" else "🔴" if w.status == "down" else "🟡"
                worker_states.append(f"{state_emoji} {w.name}: {w.status} (last heartbeat: {w.last_heartbeat or 'never'})")
        
        queue_status = context.queue.by_status if context.queue else {}
        system_state_context = f"""
## Current QiOS System State (as of {datetime.now(timezone.utc).isoformat()})

### Worker Status:
{chr(10).join(worker_states) if worker_states else "No workers registered"}

### Ingestion Queue:
- Pending: {queue_status.get('pending', 0)}
- In Progress: {queue_status.get('in_progress', 0)}
- Complete: {queue_status.get('complete', 0)}
- Embedded: {queue_status.get('embedded', 0)}
- Quarantined: {queue_status.get('quarantined', 0)}
- Error: {queue_status.get('error', 0)}
- Total in queue: {context.queue.total if context.queue else 0}

### Processed Documents:
- Total processed: {total_processed}
{realm_summary_text}
{recent_docs_text}

### System Health:
- Runtime: {context.health.runtime if context.health else 'unknown'}
- Status: {context.health.status if context.health else 'unknown'}
{conversation_context}

## Important Context Limits:
- This telemetry shows ONLY aggregate counts from the local SQLite database
- You do NOT have access to raw files, Supabase, or full vault contents
- You do NOT have realm-specific file counts unless provided here
- If asked about vault contents or realms, and you don't see realm stats above, say the local index is empty or not yet built

## Instructions:
You are GINA, the Orchestrator for the QiOS system. You have telemetry from the local database about workers, queues, and health.

**About Workers (Local-Core Architecture):**
- In local-core, a "worker" is just a Python process running a loop
- It polls the ingestion_queue table, extracts content, embeds it, writes to semantic_profile, and updates statuses
- There are NO registration commands - workers just start and write their status to worker_status table
- If asked about worker registration, say: "To register a worker in your local QiOS, you just run the worker process. There is no external registration step — when the worker starts, it automatically writes its status into the worker_status table in your local SQLite database. Once running, it will begin consuming items from the ingestion queue."
- Do NOT mention "registration commands" or cloud/Supabase architecture

When the human asks about system state, workers, queues, or ingestion:
- Use ONLY the telemetry data above to answer accurately
- Highlight any risks (degraded workers, large pending queues, etc.)
- Suggest concrete next actions based on the current state
- Do NOT claim you have access to raw files, Supabase, or vault contents
- Do NOT invent or guess system state - only use the data provided above
- If asked about vault/realms and you don't have realm stats, say: "The local index does not yet contain realm or vault summaries. Ingest items or run the worker to populate the database."

**About Memory:**
- All conversations are logged to conversation_history table
- Conversations become part of the system's semantic memory via conversation_embeddings
- You can recall previous conversation turns using conversation_history
- When relevant, reference past conversations that are in your context

The telemetry is updated with each request, so your answers reflect the current state visible in the local database.
""".strip()
    
    # Step 4: Build messages array in correct order
    openai_messages = []
    
    # 1. System: GINA personality prompt
    openai_messages.append({
        "role": "system",
        "content": GINA_SYSTEM_PROMPT
    })
    
    # 2. System: Job context (if a job was created or queried)
    if job_context_message:
        openai_messages.append({
            "role": "system",
            "content": job_context_message
        })
    
    # 3. System: RAG context (if available)
    if rag_context_block:
        openai_messages.append({
            "role": "system",
            "content": rag_context_block
        })
    
    # 3.5. System: Dev error history (if user mentions files/code)
    error_history_block = None
    if latest_user_message:
        # Detect if user is asking about code/files
        code_keywords = ["file", "code", "function", "component", "error", "bug", "fix", "implement", "change", "update"]
        if any(keyword in latest_user_message.lower() for keyword in code_keywords):
            # Try to extract file paths from message
            import re
            file_matches = re.findall(r'[\w/]+\.(ts|tsx|js|jsx|py|md)', latest_user_message)
            if file_matches:
                # Get error history for mentioned files
                try:
                    from api_dev_history import get_file_error_history
                    error_contexts = []
                    for file_match in file_matches[:3]:  # Limit to 3 files
                        # Try to find full path
                        file_path = None
                        # Look for full path in message
                        full_path_match = re.search(rf'[\w/]+{re.escape(file_match[0])}', latest_user_message)
                        if full_path_match:
                            file_path = full_path_match.group(0)
                        else:
                            # Try common paths
                            for prefix in ['apps/', 'workers/', 'tools/']:
                                test_path = prefix + file_match[0]
                                if Path(QIOS_ROOT / test_path).exists():
                                    file_path = test_path
                                    break
                        
                        if file_path:
                            # Query Supabase for error history
                            try:
                                supabase_url = os.getenv("SUPABASE_URL")
                                supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
                                if supabase_url and supabase_key:
                                    from supabase import create_client
                                    supabase = create_client(supabase_url, supabase_key)
                                    result = supabase.table("dev_error_log").select("*").eq(
                                        "file_path", file_path
                                    ).order("created_at", desc=True).limit(5).execute()
                                    
                                    if result.data:
                                        error_list = []
                                        for err in result.data:
                                            resolved = " (RESOLVED)" if err.get('resolved_at') else ""
                                            fix_note = f" → Fixed: {err['fix_summary']}" if err.get('fix_summary') else ""
                                            error_list.append(
                                                f"- **{err['error_type']}**{resolved}: {err['error_message'][:150]}{fix_note}"
                                            )
                                        if error_list:
                                            error_contexts.append(
                                                f"**Past errors in {file_path}:**\n" + "\n".join(error_list)
                                            )
                            except Exception as e:
                                print(f"[GINA] Error fetching dev history: {e}")
                    
                    if error_contexts:
                        error_history_block = (
                            "## Development Error History\n\n"
                            "The following files have past error history. Use this to avoid repeating mistakes:\n\n" +
                            "\n\n".join(error_contexts) +
                            "\n\nWhen making changes to these files, ensure you don't reintroduce the same errors."
                        )
                except ImportError:
                    pass  # Dev history API not available
    
    if error_history_block:
        openai_messages.append({
            "role": "system",
            "content": error_history_block
        })
    
    # 4. System: Live system state (if user asked about it)
    if system_state_context:
        openai_messages.append({
            "role": "system",
            "content": system_state_context
        })
    
    # 4. Build tools definition for function calling
    tools_definition = []
    tool_name_to_config = {}
    try:
        from tools import load_manifest
        manifest = load_manifest()
        available_tools = manifest.get("tools", [])
        
        for tool in available_tools:
            tool_name = tool.get("name")
            tool_desc = tool.get("description", "")
            tool_args = tool.get("args", {})
            
            # Build JSON schema for tool parameters
            properties = {}
            required = []
            
            for arg_name, arg_spec in tool_args.items():
                arg_type = arg_spec.get("type", "string")
                # Map our types to JSON schema types
                json_type = "string"
                if arg_type == "integer":
                    json_type = "integer"
                elif arg_type == "array":
                    json_type = "array"
                elif arg_type == "object":
                    json_type = "object"
                
                properties[arg_name] = {
                    "type": json_type,
                    "description": arg_spec.get("description", "")
                }
                
                if arg_spec.get("default") is not None:
                    properties[arg_name]["default"] = arg_spec.get("default")
                
                if arg_spec.get("required", False):
                    required.append(arg_name)
            
            # Create Ollama tool definition
            tool_params = {
                "type": "object",
                "properties": properties
            }
            # Only add "required" if there are required fields
            if required:
                tool_params["required"] = required
            
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_desc,
                    "parameters": tool_params
                }
            }
            
            tools_definition.append(tool_def)
            tool_name_to_config[tool_name] = tool
        
        print(f"[GINA] Loaded {len(tools_definition)} tools for function calling")
    except Exception as e:
        print(f"Warning: Failed to load tools for function calling: {e}")
        import traceback
        traceback.print_exc()
        tools_definition = []
    
    # Add tool instruction to system prompt
    if tools_definition:
        tool_instruction = f"""## Available Tools

You have access to {len(tools_definition)} tools that you can invoke automatically.

**How to use tools:**
- When the user asks you to perform an action, you can automatically invoke the appropriate tool.
- Use the tool calling format to request tool execution.
- After tool execution, you will receive the results and can provide a response based on them.
- You can chain multiple tool calls if needed.
- Always explain what you're doing when using tools."""
    else:
        tool_instruction = (
            "You have access to tools for web search, email, calendar, CRM, and vault operations. "
            "You can invoke them automatically when needed."
        )
    
    openai_messages.append({
        "role": "system",
        "content": tool_instruction
    })
    
    # 5. Voice mode hint (if applicable)
    is_voice_mode = request.mode == "voice" or request.with_voice
    if is_voice_mode:
        openai_messages.append({
            "role": "system",
            "content": (
                "The user is interacting with you via voice. "
                "Keep your responses short and easy to listen to: "
                "1–3 concise sentences, no long lists unless specifically requested."
            )
        })
    
    # 6. Memory System: STM (Short-Term Memory) + LTM (Long-Term Memory)
    # Get full context from memory system (STM + LTM combined)
    try:
        # Get combined STM + LTM context
        memory_context = await gina_memory.get_full_context_async(
            user_id=session_id,
            query=latest_user_message,
            realm=request.realm,
            ltm_k=5 if request.enableRag else 0  # Only use LTM if RAG is enabled
        )
        
        # Add memory context to messages (STM messages + LTM system message)
        # Insert after system prompts but before tools
        # Find where to insert (after system prompts, before tools)
        insert_idx = len(openai_messages)
        for i, msg in enumerate(openai_messages):
            if msg.get("role") == "system" and "Available Tools" in msg.get("content", ""):
                insert_idx = i
                break
        
        # Insert STM messages (conversation history)
        for mem_msg in memory_context:
            if mem_msg.get("role") != "system":  # STM messages (user/assistant)
                openai_messages.insert(insert_idx, mem_msg)
                insert_idx += 1
            else:  # LTM system message
                # Insert LTM context as a system message
                openai_messages.insert(insert_idx, mem_msg)
                insert_idx += 1
        
        print(f"[GINA] Memory context: {len([m for m in memory_context if m.get('role') != 'system'])} STM messages, "
              f"{len([m for m in memory_context if m.get('role') == 'system'])} LTM context")
    except Exception as e:
        print(f"Warning: Failed to load memory context: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to conversation_history if memory system fails
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT role, content
                FROM conversation_history
                ORDER BY created_at DESC
                LIMIT 10
            """)
            history_rows = cursor.fetchall()
            for role, content in reversed(history_rows):
                openai_messages.append({
                    "role": role,
                    "content": content
                })
        except Exception as e2:
            print(f"Warning: Fallback conversation history also failed: {e2}")
        finally:
            conn.close()
    
    # 7. Latest user message (must be last)
    # Also log user messages to conversation_history and STM
    try:
        for msg in request.messages:
            # Skip user-provided system messages (GINA's prompt takes precedence)
            if msg.role != "system":
                # Only add if not already in history
                if msg.role == "user" and msg.content == latest_user_message:
                    # This is the latest message, add it
                    openai_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                
                # Log user messages to conversation_history (persistent storage)
                if msg.role == "user":
                    msg_id = str(uuid.uuid4())
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT INTO conversation_history (id, session_id, role, content, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (msg_id, session_id, "user", msg.content, now))
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        print(f"Warning: Failed to log to conversation_history: {e}")
                    finally:
                        conn.close()
                    
                    # Add to STM (short-term memory)
                    gina_memory.add_to_stm(session_id, "user", msg.content)
        
    except Exception as e:
        print(f"Warning: Failed to process user messages: {e}")
    
    # Step 4: Call LLM (OpenAI preferred, Ollama fallback) with function calling support
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    use_openai = HAS_OPENAI and openai_api_key
    
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_llm_model = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
    
    if use_openai:
        print(f"[GINA] Using OpenAI model: {openai_model}")
    else:
        if not HAS_OPENAI:
            print("[GINA] OpenAI package not installed, falling back to Ollama")
        elif not openai_api_key:
            print("[GINA] OPENAI_API_KEY not set, falling back to Ollama")
        print(f"[GINA] Using Ollama model: {ollama_llm_model} at {ollama_base_url}")
    
    # Tool execution loop: allow multiple rounds of tool calls
    max_tool_iterations = 5
    tool_iteration = 0
    final_reply = None
    tool_suggestions = None
    executed_tools = []
    
    try:
        if use_openai and HAS_OPENAI:
            # Use OpenAI with function calling
            client = AsyncOpenAI(api_key=openai_api_key)
            current_messages = openai_messages.copy()
            
            while tool_iteration < max_tool_iterations:
                # Prepare OpenAI function calling format
                call_kwargs = {
                    "model": openai_model,
                    "messages": current_messages,
                    "temperature": 0.7,
                }
                
                # Add tools if available (OpenAI uses "tools" parameter)
                if tools_definition:
                    # Convert tools_definition to OpenAI format
                    openai_tools = []
                    for tool_def in tools_definition:
                        openai_tools.append({
                            "type": "function",
                            "function": tool_def["function"]
                        })
                    call_kwargs["tools"] = openai_tools
                
                try:
                    response = await client.chat.completions.create(**call_kwargs)
                    message = response.choices[0].message
                    
                    # Check for tool calls
                    tool_calls = message.tool_calls if hasattr(message, 'tool_calls') else None
                    
                    if tool_calls and len(tool_calls) > 0:
                        # Execute tools
                        tool_iteration += 1
                        print(f"[GINA] [OpenAI] Tool iteration {tool_iteration}: {len(tool_calls)} tool calls")
                        
                        # Add assistant message with tool calls to conversation
                        current_messages.append({
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in tool_calls
                            ]
                        })
                        
                        # Execute each tool call
                        for tool_call in tool_calls:
                            tool_id = tool_call.id
                            tool_name = tool_call.function.name
                            tool_args_str = tool_call.function.arguments
                            
                            try:
                                tool_args = json.loads(tool_args_str)
                            except:
                                tool_args = {}
                            
                            print(f"[GINA] [ITER {tool_iteration}] Executing tool: {tool_name}")
                            print(f"[GINA] [ITER {tool_iteration}] Tool args: {tool_args}")
                            
                            # Invoke tool
                            from tools import invoke_tool
                            tool_result = await invoke_tool(tool_name, tool_args, {})
                            
                            status = "OK" if tool_result.ok else "ERROR"
                            print(f"[GINA] [ITER {tool_iteration}] Tool {tool_name}: {status}")
                            if not tool_result.ok:
                                print(f"[GINA] [ITER {tool_iteration}] Tool error: {tool_result.error}")
                            
                            executed_tools.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "success": tool_result.ok,
                                "result": tool_result.result if tool_result.ok else None,
                                "error": tool_result.error
                            })
                            
                            # Add tool result to conversation (OpenAI format)
                            tool_result_content = json.dumps(tool_result.result) if tool_result.ok else f"Error: {tool_result.error}"
                            
                            current_messages.append({
                                "role": "tool",
                                "content": tool_result_content,
                                "tool_call_id": tool_id
                            })
                        
                        # Continue loop to get final response with tool results
                        continue
                    else:
                        # No tool calls, get final reply
                        final_reply = message.content or "I couldn't generate a reply. Please try again."
                        break
                
                except Exception as e:
                    print(f"[GINA] [OpenAI] Error: {e}")
                    # Fall back to Ollama if OpenAI fails
                    print("[GINA] Falling back to Ollama...")
                    use_openai = False
                    break
            
            # If we hit max iterations, use the last reply
            if not final_reply:
                final_reply = "I processed your request but reached the maximum number of tool execution rounds. Please try a simpler request."
            
            reply = final_reply
            
            # Build tool suggestions from executed tools
            if executed_tools:
                from tools import get_tool_config
                tool_suggestions = []
                for t in executed_tools:
                    tool_name = t["tool"]
                    tool_config = get_tool_config(tool_name)
                    label = tool_config.get("description", tool_name) if tool_config else tool_name
                    tool_suggestions.append({
                        "tool": tool_name,
                        "label": label,
                        "args": t["args"]
                    })
            
        elif HAS_HTTPX and not use_openai:
            # Use httpx (async) to call Ollama
            async with httpx.AsyncClient() as client:
                current_messages = openai_messages.copy()
                
                while tool_iteration < max_tool_iterations:
                    # Ollama chat API format with tools
                    ollama_payload = {
                        "model": ollama_llm_model,
                        "messages": current_messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                        }
                    }
                    
                    # Add tools if available
                    if tools_definition:
                        ollama_payload["tools"] = tools_definition
                    
                    response = await client.post(
                        f"{ollama_base_url}/api/chat",
                        json=ollama_payload,
                        timeout=60.0
                    )
                    
                    if response.status_code != 200:
                        error_text = response.text
                        raise HTTPException(
                            status_code=500,
                            detail=f"Ollama API error: {response.status_code} – {error_text}"
                        )
                    
                    data = response.json()
                    message = data.get("message", {})
                    
                    # Check for tool calls
                    tool_calls = message.get("tool_calls")
                    
                    if tool_calls and len(tool_calls) > 0:
                        # Execute tools
                        tool_iteration += 1
                        print(f"[GINA] Tool iteration {tool_iteration}: {len(tool_calls)} tool calls")
                        
                        # Add assistant message with tool calls to conversation
                        current_messages.append({
                            "role": "assistant",
                            "content": message.get("content", ""),
                            "tool_calls": tool_calls
                        })
                        
                        # Execute each tool call
                        for tool_call in tool_calls:
                            tool_id = tool_call.get("id")
                            tool_name = tool_call.get("function", {}).get("name")
                            tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                            
                            try:
                                import json as json_lib
                                tool_args = json_lib.loads(tool_args_str)
                            except:
                                tool_args = {}
                            
                            print(f"[GINA] [ITER {tool_iteration}] Executing tool: {tool_name}")
                            print(f"[GINA] [ITER {tool_iteration}] Tool args: {tool_args}")
                            
                            # Invoke tool
                            from tools import invoke_tool
                            tool_result = await invoke_tool(tool_name, tool_args, {})
                            
                            status = "OK" if tool_result.ok else "ERROR"
                            print(f"[GINA] [ITER {tool_iteration}] Tool {tool_name}: {status}")
                            if not tool_result.ok:
                                print(f"[GINA] [ITER {tool_iteration}] Tool error: {tool_result.error}")
                            
                            executed_tools.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "success": tool_result.ok,
                                "result": tool_result.result if tool_result.ok else None,
                                "error": tool_result.error
                            })
                            
                            # Add tool result to conversation
                            tool_result_content = json.dumps(tool_result.result) if tool_result.ok else f"Error: {tool_result.error}"
                            
                            current_messages.append({
                                "role": "tool",
                                "content": tool_result_content,
                                "name": tool_name,
                                "tool_call_id": tool_id
                            })
                        
                        # Continue loop to get final response with tool results
                        continue
                    else:
                        # No tool calls, get final reply
                        final_reply = message.get("content") or data.get("response", "I couldn't generate a reply. Please try again.")
                        break
                
                # If we hit max iterations, use the last reply
                if not final_reply:
                    final_reply = "I processed your request but reached the maximum number of tool execution rounds. Please try a simpler request."
                
                reply = final_reply
                
                # Build tool suggestions from executed tools
                if executed_tools:
                    from tools import get_tool_config
                    tool_suggestions = []
                    for t in executed_tools:
                        tool_name = t["tool"]
                        tool_config = get_tool_config(tool_name)
                        label = tool_config.get("description", tool_name) if tool_config else tool_name
                        tool_suggestions.append({
                            "tool": tool_name,
                            "label": label,
                            "args": t["args"]
                        })
                
                # Strip markdown formatting from reply
                import re
                # Remove markdown headers (# ## ###)
                reply = re.sub(r'^#{1,6}\s+', '', reply, flags=re.MULTILINE)
                # Remove bold (**text** or __text__)
                reply = re.sub(r'\*\*(.*?)\*\*', r'\1', reply)
                reply = re.sub(r'__(.*?)__', r'\1', reply)
                # Remove italic (*text* or _text_)
                reply = re.sub(r'\*(.*?)\*', r'\1', reply)
                reply = re.sub(r'_(.*?)_', r'\1', reply)
                # Remove inline code (`code`)
                reply = re.sub(r'`([^`]+)`', r'\1', reply)
                # Remove code blocks (```...```)
                reply = re.sub(r'```[\s\S]*?```', '', reply)
                # Remove links [text](url)
                reply = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', reply)
                # Remove horizontal rules (--- or ***)
                reply = re.sub(r'^[-*]{3,}$', '', reply, flags=re.MULTILINE)
                # Clean up extra whitespace
                reply = re.sub(r'\n{3,}', '\n\n', reply)
                reply = reply.strip()
                
                # Tool suggestions already built from executed tools above
                
                # Log GINA's reply to conversation_history
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    gina_msg_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO conversation_history (id, session_id, role, content, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (gina_msg_id, session_id, "assistant", reply, datetime.now(timezone.utc).isoformat()))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Warning: Failed to log GINA reply: {e}")
                
                # Add assistant reply to STM (short-term memory)
                try:
                    gina_memory.add_to_stm(session_id, "assistant", reply)
                except Exception as e:
                    print(f"Warning: Failed to add reply to STM: {e}")
                
                # Log debug info
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    event_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        event_id,
                        "gina_chat",
                        "info",
                        "Chat request processed",
                    json.dumps({
                        "session_id": session_id,
                        "rag_hits": len(rag_results),
                        "rag_top_files": [r.get("file_path", "unknown") for r in rag_results[:3]],
                        "rag_top_scores": [r.get("score", 0.0) for r in rag_results[:3]],
                        "retrieval_used": retrieval_used,
                        "needs_system_state": needs_system_state,
                        "mode": request.mode or "chat",
                        "message_count": len(request.messages),
                        "tool_iterations": tool_iteration,
                        "tools_executed": len(executed_tools) if executed_tools else 0,
                        "tool_details": [
                            {
                                "tool": t.get("tool"),
                                "success": t.get("success"),
                                "error": t.get("error")
                            }
                            for t in (executed_tools or [])
                        ],
                        "reply_length": len(reply) if reply else 0
                    }),
                        datetime.now(timezone.utc).isoformat()
                    ))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Warning: Failed to log debug info: {e}")
                
                return GinaChatResponse(
                    reply=reply,
                    context=context,
                    tool_suggestions=tool_suggestions,
                    retrieval_used=retrieval_used,
                    sources=rag_sources if rag_sources else None
                )
        elif HAS_REQUESTS:
            # Fallback to requests (sync) for Ollama
            # Note: Function calling with tool loops is more complex in sync mode
            # For now, do a single call without tool loops
            tool_suggestions = None
            executed_tools = []
            
            ollama_payload = {
                "model": ollama_llm_model,
                "messages": openai_messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                }
            }
            
            # Add tools if available
            if tools_definition:
                ollama_payload["tools"] = tools_definition
            
            response = requests.post(
                f"{ollama_base_url}/api/chat",
                json=ollama_payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                error_text = response.text
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama API error: {response.status_code} – {error_text}"
                )
            
            data = response.json()
            message = data.get("message", {})
            reply = message.get("content") or data.get("response", "I couldn't generate a reply. Please try again.")
            
            # Check for tool calls (single iteration only in sync mode)
            tool_calls = message.get("tool_calls")
            if tool_calls and len(tool_calls) > 0:
                # Execute tools synchronously
                executed_tools = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name")
                    tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                    
                    try:
                        tool_args = json.loads(tool_args_str)
                    except:
                        tool_args = {}
                    
                    # Invoke tool (async)
                    from tools import invoke_tool
                    tool_result = await invoke_tool(tool_name, tool_args, {})
                    
                    executed_tools.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "success": tool_result.ok
                    })
                
                if executed_tools:
                    from tools import get_tool_config
                    tool_suggestions = []
                    for t in executed_tools:
                        tool_name = t["tool"]
                        tool_config = get_tool_config(tool_name)
                        label = tool_config.get("description", tool_name) if tool_config else tool_name
                        tool_suggestions.append({
                            "tool": tool_name,
                            "label": label,
                            "args": t["args"]
                        })
            
            # Strip markdown formatting from reply
            import re
            # Remove markdown headers (# ## ###)
            reply = re.sub(r'^#{1,6}\s+', '', reply, flags=re.MULTILINE)
            # Remove bold (**text** or __text__)
            reply = re.sub(r'\*\*(.*?)\*\*', r'\1', reply)
            reply = re.sub(r'__(.*?)__', r'\1', reply)
            # Remove italic (*text* or _text_)
            reply = re.sub(r'\*(.*?)\*', r'\1', reply)
            reply = re.sub(r'_(.*?)_', r'\1', reply)
            # Remove inline code (`code`)
            reply = re.sub(r'`([^`]+)`', r'\1', reply)
            # Remove code blocks (```...```)
            reply = re.sub(r'```[\s\S]*?```', '', reply)
            # Remove links [text](url)
            reply = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', reply)
            # Remove horizontal rules (--- or ***)
            reply = re.sub(r'^[-*]{3,}$', '', reply, flags=re.MULTILINE)
            # Clean up extra whitespace
            reply = re.sub(r'\n{3,}', '\n\n', reply)
            reply = reply.strip()
            
            # Extract tool suggestions from reply (simple pattern matching for now)
            # TODO: Use structured output or function calling when available
            tool_suggestions = None
            
            # Log GINA's reply to conversation_history
            try:
                conn = get_connection()
                cursor = conn.cursor()
                gina_msg_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO conversation_history (id, session_id, role, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (gina_msg_id, session_id, "assistant", reply, datetime.now(timezone.utc).isoformat()))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Warning: Failed to log GINA reply: {e}")
            
            # Add assistant reply to STM (short-term memory)
            try:
                gina_memory.add_to_stm(session_id, "assistant", reply)
            except Exception as e:
                print(f"Warning: Failed to add reply to STM: {e}")
            
            # Log debug info
            try:
                conn = get_connection()
                cursor = conn.cursor()
                event_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    "gina_chat",
                    "info",
                    "Chat request processed",
                        json.dumps({
                            "session_id": session_id,
                            "rag_hits": len(rag_results),
                            "rag_top_files": [r.get("file_path", "unknown") for r in rag_results[:3]],
                            "rag_top_scores": [r.get("score", 0.0) for r in rag_results[:3]],
                            "retrieval_used": retrieval_used,
                            "needs_system_state": needs_system_state,
                            "mode": request.mode or "chat",
                            "message_count": len(request.messages),
                            "tools_executed": len(executed_tools) if executed_tools else 0,
                            "reply_length": len(reply) if reply else 0
                        }),
                    datetime.now(timezone.utc).isoformat()
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Warning: Failed to log debug info: {e}")
            
            return GinaChatResponse(
                reply=reply,
                context=context,
                tool_suggestions=tool_suggestions,
                retrieval_used=retrieval_used,
                sources=rag_sources if rag_sources else None
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="No HTTP client available. Install 'httpx' or 'requests' package."
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        # Log full traceback for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"[GINA] [ERROR] Exception in gina_chat: {str(e)}")
        print(f"[GINA] [ERROR] Traceback:\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response from Ollama: {str(e)}. Make sure Ollama is running at {ollama_base_url} and model {ollama_llm_model} is available."
        )


@app.post("/dev/code_assist", response_model=DevCodeAssistResponse)
async def dev_code_assist(req: DevCodeAssistRequest) -> DevCodeAssistResponse:
    """
    Dev-specific code assistance endpoint that ALWAYS queries dev_error_log.
    
    Per DEV.ERROR.MEMORY.V1 rule: For any development-assistance request involving
    a specific file or symbol, QiOS must query the dev_error_log for prior errors
    and fixes and inject them into the AI context before generating suggestions.
    
    This endpoint is separate from /gina/chat to enforce the dev memory requirement.
    """
    # 1) Query dev_error_log for this file (and symbol, if present)
    errors = await get_recent_errors_for_file(
        req.file_path,
        symbol=req.symbol,
        limit=10,
        include_resolved=False  # Focus on unresolved errors
    )
    
    # 2) Build system + user messages
    error_context = format_errors_for_prompt(errors)
    
    system_msg = {
        "role": "system",
        "content": (
            "You are a development assistant for the QiOS codebase.\n"
            "You have access to prior errors and fixes for this file.\n"
            "DO NOT reintroduce patterns that caused past errors.\n"
            "Use the dev_error_log context below to avoid repeating mistakes.\n\n"
            f"dev_error_log for {req.file_path}:\n"
            f"{error_context}\n\n"
            "When providing suggestions:\n"
            "- Carefully read the provided dev_error_log entries.\n"
            "- Treat them as constraints and past lessons.\n"
            "- Do not reintroduce the exact patterns, types, or schema mismatches that previously caused failures.\n"
            "- When relevant, explicitly explain how your suggestion avoids those prior errors.\n"
        ),
    }
    
    user_msg = {
        "role": "user",
        "content": (
            f"File: {req.file_path}\n"
            f"Symbol: {req.symbol or 'n/a'}\n\n"
            f"Snippet:\n{req.snippet}\n\n"
            f"Question: {req.question or 'Fix or improve this code safely.'}"
        ),
    }
    
    # 3) Call OpenAI (reuse existing OpenAI logic from /gina/chat)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    use_openai = HAS_OPENAI and openai_api_key
    
    if not use_openai:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured. /dev/code_assist requires OpenAI."
        )
    
    try:
        client = AsyncOpenAI(api_key=openai_api_key)
        response = await client.chat.completions.create(
            model=openai_model,
            messages=[system_msg, user_msg],
            temperature=0.7,
        )
        
        reply_text = response.choices[0].message.content or "No response generated."
        
        return DevCodeAssistResponse(
            answer=reply_text,
            used_errors=errors,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dev assistance: {str(e)}"
        )


@app.get("/deployments")
async def deployments():
    """Get deployment history (placeholder)."""
    # TODO: Implement deployment tracking
    return []


@app.get("/logs")
async def logs():
    """Get system event logs."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, event_type, severity, message, meta, created_at
            FROM system_event
            ORDER BY created_at DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        
        logs_list = []
        for row in rows:
            logs_list.append({
                "id": row[0],
                "timestamp": row[5],
                "type": row[2] or "INFO",
                "message": row[3] or row[1],
            })
        
        return logs_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.post("/action")
async def action(request: Dict[str, Any]):
    """Trigger system action (rebuild index, rescan vault, etc.)."""
    action_type = request.get("action", "")
    
    # TODO: Implement actual actions
    if action_type == "REBUILD_INDEX":
        return {"success": True, "message": "Rebuild signal sent. Worker halting for exclusive lock."}
    elif action_type == "RESCAN_VAULT":
        return {"success": True, "message": "Scan initiated on root /vault."}
    elif action_type == "CLEAR_LOGS":
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM system_event")
            conn.commit()
            return {"success": True, "message": "Log buffer flushed."}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()
    elif action_type == "CLEANUP_DUPLICATE_WORKERS":
        """Remove duplicate worker entries, keeping only the most recent per worker_name."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Count before cleanup
            cursor.execute("SELECT COUNT(*) FROM worker_status")
            before_count = cursor.fetchone()[0]
            
            # After migration 005, worker_name is primary key, so duplicates shouldn't exist
            # But if they do (from old data), this will keep only one per worker_name
            # Note: This is now a no-op after migration, but kept for safety
            cursor.execute("""
                DELETE FROM worker_status
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM worker_status
                    GROUP BY worker_name
                )
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            
            # Count after cleanup
            cursor.execute("SELECT COUNT(*) FROM worker_status")
            after_count = cursor.fetchone()[0]
            
            return {
                "success": True,
                "message": f"Cleaned up {deleted_count} duplicate worker entries.",
                "before": before_count,
                "after": after_count,
                "deleted": deleted_count
            }
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
        finally:
            conn.close()
    else:
        return {"success": False, "message": f"Unknown action: {action_type}"}


@app.post("/tools/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(request: ToolInvokeRequest):
    """Invoke a tool by name with given arguments."""
    from tools import invoke_tool as invoke_tool_impl
    
    # Log tool invocation
    try:
        conn = get_connection()
        cursor = conn.cursor()
        event_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            "tool_invoke",
            "info",
            f"Tool invoked: {request.tool}",
            json.dumps({
                "tool": request.tool,
                "args_keys": list(request.args.keys())  # Sanitized - just keys
            }),
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to log tool invocation: {e}")
    
    # Invoke tool
    try:
        result = await invoke_tool_impl(request.tool, request.args, {})
        
        # Log tool invocation result summary to system_event
        try:
            conn = get_connection()
            cursor = conn.cursor()
            event_id = str(uuid.uuid4())
            result_summary = "success" if result.ok else f"error: {result.error[:100] if result.error else 'unknown'}"
            cursor.execute("""
                INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                "tool_invoke_result",
                "info" if result.ok else "warning",
                f"Tool {request.tool}: {result_summary}",
                json.dumps({
                    "tool": request.tool,
                    "ok": result.ok,
                    "result_keys": list(result.result.keys()) if isinstance(result.result, dict) else None
                }),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to log tool result: {e}")
        
        return ToolInvokeResponse(
            ok=result.ok,
            tool=result.tool,
            result=result.result,
            error=result.error
        )
    except Exception as e:
        return ToolInvokeResponse(
            ok=False,
            tool=request.tool,
            error=f"Tool invocation failed: {str(e)}"
        )


@app.get("/tools")
async def list_tools():
    """List all available tools."""
    from tools import list_tools as list_tools_impl
    return {"tools": list_tools_impl()}


@app.post("/debug/ingest_once")
async def debug_ingest_once():
    """
    Debug endpoint: process a single pending item without the worker loop.
    Useful for testing the embedding pipeline on one file.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from worker import process_queue_item
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get one pending item
        cursor.execute("""
            SELECT id, file_path, extracted_text, slug, realm, status
            FROM ingestion_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {
                "ok": False,
                "error": "No pending items found"
            }
        
        item_id, file_path, extracted_text, slug, realm, status = row
        
        # Mark as processing
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE ingestion_queue
            SET status = 'processing', updated_at = ?
            WHERE id = ?
        """, (now, item_id))
        conn.commit()
        conn.close()
        
        # Process item
        success, chunks, embeddings_written, errors = process_queue_item(
            item_id, file_path, extracted_text, slug, realm
        )
        
        return {
            "ok": success,
            "item_id": item_id,
            "file_path": file_path,
            "chunks": chunks,
            "embeddings_written": embeddings_written,
            "errors": errors
        }
    
    except Exception as e:
        import traceback
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.post("/crawl/vault")
async def crawl_vault(request: Optional[Dict[str, Any]] = None):
    """
    Crawl vault directories and enqueue files for ingestion.
    
    Request body (optional):
    {
        "roots": ["realms/qivault/kb", "docs"]
    }
    
    If no roots provided, uses default crawl roots (prioritizes realms/qivault/kb).
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from crawler.vault_crawler import crawl, DEFAULT_CRAWL_ROOTS
    
    roots = None
    if request and "roots" in request:
        roots = request["roots"]
    
    try:
        result = crawl(roots=roots)
        return result
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Crawl failed: {str(e)}\n{traceback.format_exc()}"
        )


@app.post("/gina/tts")
async def gina_tts(request: GinaTTSRequest):
    """
    Text-to-Speech using ElevenLabs API.
    Converts GINA's text response to audio using ElevenLabs voice synthesis.
    
    Environment variables:
    - ELEVENLABS_API_KEY: Your ElevenLabs API key (required)
    - ELEVENLABS_VOICE_ID: Optional voice ID (defaults to Rachel)
    - ELEVENLABS_MODEL_ID: Optional model ID (defaults to "eleven_monolingual_v1")
    
    Returns:
        Audio/mpeg response with GINA's voice
    """
    from fastapi.responses import Response
    from integrations.tts.elevenlabs import synthesize_speech
    from integrations.base import IntegrationBase
    
    # Validate text (non-empty, limit length)
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    max_length = 1500  # Limit to avoid very long audio
    text = request.text[:max_length] if len(request.text) > max_length else request.text.strip()
    
    # Log integration attempt
    integration = IntegrationBase("elevenlabs")
    
    try:
        # Call ElevenLabs TTS
        audio_data = await synthesize_speech(
            text=text,
            voice_id=request.voice_id,
            model_id=request.model_id
        )
        
        # Log successful TTS event (info level)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                "integration_event",
                "info",
                "elevenlabs.tts",
                json.dumps({
                    "provider": "elevenlabs",
                    "action": "tts",
                    "text_length": len(text),
                    "voice_id": request.voice_id,
                    "model_id": request.model_id,
                    "audio_size_bytes": len(audio_data)
                }),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to log TTS event: {e}")
        
        # Return audio as binary response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": "inline; filename=gina_response.mp3"
            }
        )
    
    except RuntimeError as e:
        # Configuration error (API key missing, etc.)
        error_msg = str(e)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                "integration_event",
                "error",
                "elevenlabs.tts",
                json.dumps({
                    "provider": "elevenlabs",
                    "action": "tts",
                    "error": error_msg,
                    "text_length": len(text)
                }),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as log_err:
            print(f"Warning: Failed to log TTS error: {log_err}")
        
        raise HTTPException(
            status_code=500,
            detail=f"TTS configuration error: {error_msg}"
        )
    
    except Exception as e:
        # API error or other failure
        error_msg = str(e)
        
        # Check for 401 Unauthorized (API key issue)
        is_unauthorized = "401" in error_msg or "Unauthorized" in error_msg
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                "integration_event",
                "error",
                "elevenlabs.tts",
                json.dumps({
                    "provider": "elevenlabs",
                    "action": "tts",
                    "error": error_msg,
                    "text_length": len(text),
                    "is_unauthorized": is_unauthorized
                }),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as log_err:
            print(f"Warning: Failed to log TTS error: {log_err}")
        
        # Return appropriate status code and user-friendly message
        if is_unauthorized:
            status_code = 401
            user_message = "ElevenLabs API key is missing or invalid. Please configure ELEVENLABS_API_KEY in your environment."
        else:
            # Return 502 for external API failures, 500 for other errors
            status_code = 502 if "HTTP" in str(type(e)) or "status" in error_msg.lower() else 500
            user_message = error_msg
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "TTS generation failed",
                "message": user_message,
                "details": error_msg if not is_unauthorized else None
            }
        )


# ============================================================================
# Notes API (QiNote v2.0)
# ============================================================================

@app.post("/notes", response_model=Note)
async def create_note(note: NoteCreate):
    """Create a new note."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        note_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Ensure front matter is present (MTA.001 compliance)
        content_md_with_fm = ensure_frontmatter(
            note.content_md,
            title=note.title,
            slug=note.slug,
            realm=note.realm,
            tags=note.tags,
            sensitivity=note.sensitivity or "internal",
            qid=note_id,  # Use note ID as QID for now
        )
        
        # Serialize JSON fields
        tags_json = json.dumps(note.tags or [])
        backlinks_json = json.dumps(note.backlinks or [])
        metadata_json = json.dumps(note.metadata or {})
        
        cursor.execute("""
            INSERT INTO notes (
                id, title, slug, realm, content_md, content_html,
                tags, backlinks, sensitivity, metadata,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id, note.title, note.slug, note.realm,
            content_md_with_fm, note.content_html or "",
            tags_json, backlinks_json,
            note.sensitivity or "internal",
            metadata_json,
            now, now
        ))
        
        conn.commit()
        
        # Fetch the created note
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create note")
        
        # Deserialize JSON fields
        tags = json.loads(row["tags"]) if row["tags"] else []
        backlinks = json.loads(row["backlinks"]) if row["backlinks"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        
        return Note(
            id=row["id"],
            title=row["title"],
            slug=row["slug"],
            realm=row["realm"],
            content_md=row["content_md"],
            content_html=row["content_html"],
            tags=tags,
            backlinks=backlinks,
            sensitivity=row["sensitivity"],
            metadata=metadata,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}")


@app.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: str):
    """Get a note by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        
        # Deserialize JSON fields
        tags = json.loads(row["tags"]) if row["tags"] else []
        backlinks = json.loads(row["backlinks"]) if row["backlinks"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        
        return Note(
            id=row["id"],
            title=row["title"],
            slug=row["slug"],
            realm=row["realm"],
            content_md=row["content_md"],
            content_html=row["content_html"],
            tags=tags,
            backlinks=backlinks,
            sensitivity=row["sensitivity"],
            metadata=metadata,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error fetching note: {str(e)}")


@app.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id: str, note: NoteUpdate):
    """Update an existing note."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if note exists
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail="Note not found")
        
        # Build update query dynamically
        updates = []
        values = []
        
        if note.title is not None:
            updates.append("title = ?")
            values.append(note.title)
        if note.slug is not None:
            updates.append("slug = ?")
            values.append(note.slug)
        if note.realm is not None:
            updates.append("realm = ?")
            values.append(note.realm)
        if note.content_md is not None:
            # Ensure front matter is present (MTA.001 compliance)
            # If existing note has front matter, preserve it; otherwise add it
            existing_content = existing["content_md"] or ""
            content_md_with_fm = ensure_frontmatter(
                note.content_md,
                title=note.title or existing["title"],
                slug=note.slug or existing["slug"],
                realm=note.realm or existing["realm"],
                tags=note.tags or json.loads(existing["tags"]) if existing["tags"] else [],
                sensitivity=note.sensitivity or existing["sensitivity"],
                qid=note_id,
            )
            updates.append("content_md = ?")
            values.append(content_md_with_fm)
        if note.content_html is not None:
            updates.append("content_html = ?")
            values.append(note.content_html)
        if note.tags is not None:
            updates.append("tags = ?")
            values.append(json.dumps(note.tags))
        if note.backlinks is not None:
            updates.append("backlinks = ?")
            values.append(json.dumps(note.backlinks))
        if note.sensitivity is not None:
            updates.append("sensitivity = ?")
            values.append(note.sensitivity)
        if note.metadata is not None:
            updates.append("metadata = ?")
            values.append(json.dumps(note.metadata))
        
        if not updates:
            # No updates provided, return existing note
            conn.close()
            tags = json.loads(existing["tags"]) if existing["tags"] else []
            backlinks = json.loads(existing["backlinks"]) if existing["backlinks"] else []
            metadata = json.loads(existing["metadata"]) if existing["metadata"] else {}
            return Note(
                id=existing["id"],
                title=existing["title"],
                slug=existing["slug"],
                realm=existing["realm"],
                content_md=existing["content_md"],
                content_html=existing["content_html"],
                tags=tags,
                backlinks=backlinks,
                sensitivity=existing["sensitivity"],
                metadata=metadata,
                created_at=existing["created_at"],
                updated_at=existing["updated_at"]
            )
        
        # Always update updated_at
        updates.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(note_id)
        
        query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        
        # Fetch updated note
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=500, detail="Failed to update note")
        
        # Deserialize JSON fields
        tags = json.loads(row["tags"]) if row["tags"] else []
        backlinks = json.loads(row["backlinks"]) if row["backlinks"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        
        return Note(
            id=row["id"],
            title=row["title"],
            slug=row["slug"],
            realm=row["realm"],
            content_md=row["content_md"],
            content_html=row["content_html"],
            tags=tags,
            backlinks=backlinks,
            sensitivity=row["sensitivity"],
            metadata=metadata,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}")


@app.get("/notes", response_model=List[Note])
async def list_notes(
    realm: Optional[str] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None
):
    """List notes with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM notes WHERE 1=1"
        params = []
        
        if realm:
            query += " AND realm = ?"
            params.append(realm)
        
        if q:
            query += " AND (title LIKE ? OR content_md LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term])
        
        query += " ORDER BY updated_at DESC LIMIT 100"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        notes = []
        for row in rows:
            # Deserialize JSON fields
            tags = json.loads(row["tags"]) if row["tags"] else []
            backlinks = json.loads(row["backlinks"]) if row["backlinks"] else []
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            
            # Filter by tag if specified (simple string match in JSON array)
            if tag:
                if tag not in tags:
                    continue
            
            notes.append(Note(
                id=row["id"],
                title=row["title"],
                slug=row["slug"],
                realm=row["realm"],
                content_md=row["content_md"],
                content_html=row["content_html"],
                tags=tags,
                backlinks=backlinks,
                sensitivity=row["sensitivity"],
                metadata=metadata,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))
        
        return notes
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error listing notes: {str(e)}")


# ============================================================================
# Note Assist API (QiNote v2.0)
# ============================================================================

@app.post("/gina/note_assist", response_model=NoteAssistResponse)
async def note_assist(request: NoteAssistRequest):
    """Task-oriented AI endpoint for note operations (summarize, rewrite, outline, tag, qa)."""
    if not HAS_OPENAI:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not available. Install with: pip install openai"
        )
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY not configured"
        )
    
    client = AsyncOpenAI(api_key=openai_api_key)
    
    # Build prompt based on intent
    note = request.note
    content = note.get("content_md", "")
    title = note.get("title", "")
    realm = note.get("realm", "")
    tags = note.get("tags", [])
    
    selection_text = ""
    if request.selection:
        selection_text = f"\n\nSelected text:\n{request.selection.get('value', '')}"
    
    user_instruction = request.user_instruction or ""
    
    system_prompt = "You are GINA, the Generative Intelligence Neural Archivist for QiOS. You help users work with their notes through structured AI operations."
    
    intent_prompts = {
        "summarize": f"""Summarize the following note in 2-3 concise paragraphs. Focus on key points and main ideas.

Title: {title}
Realm: {realm}
Tags: {', '.join(tags) if tags else 'none'}

Content:
{content}{selection_text}

{user_instruction}

Provide only the summary text, no preamble.""",
        
        "rewrite": f"""Rewrite the following note content to be clearer, more concise, and better structured. Maintain the original meaning and key information.

Title: {title}
Realm: {realm}

Original content:
{content}{selection_text}

{user_instruction}

Provide only the rewritten content in markdown format, no preamble.""",
        
        "outline": f"""Create a structured outline of the following note. Use markdown heading hierarchy (##, ###, etc.) to organize the main topics and subtopics.

Title: {title}
Realm: {realm}

Content:
{content}{selection_text}

{user_instruction}

Provide only the outline in markdown format, no preamble.""",
        
        "tag": f"""Analyze the following note and suggest 3-5 relevant tags. Consider the content, realm ({realm}), and existing tags ({', '.join(tags) if tags else 'none'}).

Title: {title}

Content:
{content}{selection_text}

{user_instruction}

Return only a JSON array of tag strings, e.g. ["tag1", "tag2", "tag3"]. No other text.""",
        
        "qa": f"""Answer the following question about the note. Use the note content as context.

Title: {title}
Realm: {realm}

Note content:
{content}{selection_text}

Question: {user_instruction or 'What are the key points in this note?'}

Provide a clear, concise answer based on the note content. If the question cannot be answered from the note, say so."""
    }
    
    user_prompt = intent_prompts.get(request.intent)
    if not user_prompt:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid intent: {request.intent}. Must be one of: summarize, rewrite, outline, tag, qa"
        )
    
    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        reply_text = response.choices[0].message.content or ""
        
        # Parse response based on intent
        result = NoteAssistResponse(intent=request.intent)
        
        if request.intent == "summarize":
            result.summary_md = reply_text
        elif request.intent == "rewrite":
            result.rewritten_md = reply_text
        elif request.intent == "outline":
            result.outline_md = reply_text
        elif request.intent == "tag":
            # Try to parse JSON array from response
            try:
                import re
                # Extract JSON array from response
                json_match = re.search(r'\[.*?\]', reply_text, re.DOTALL)
                if json_match:
                    result.suggested_tags = json.loads(json_match.group())
                else:
                    # Fallback: split by comma and clean
                    result.suggested_tags = [t.strip().strip('"\'') for t in reply_text.split(",") if t.strip()]
            except Exception:
                result.suggested_tags = []
        elif request.intent == "qa":
            result.answer_md = reply_text
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calling OpenAI: {str(e)}"
        )


@app.get("/integrations/status")
async def get_integrations_status():
    """
    Get status of all integrations (env vars configured, tokens present, etc.).
    Returns status without exposing sensitive values.
    """
    import os
    from datetime import datetime, timezone
    
    integrations = {}
    
    # Zoho CRM
    zoho_configured = all([
        os.getenv("ZOHO_CLIENT_ID"),
        os.getenv("ZOHO_CLIENT_SECRET"),
        os.getenv("ZOHO_REFRESH_TOKEN")
    ])
    zoho_token = None
    zoho_token_expires = None
    if zoho_configured:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT expires_at, updated_at
                FROM integration_tokens
                WHERE provider = 'zoho'
            """)
            row = cursor.fetchone()
            conn.close()
            if row:
                zoho_token = "present"
                zoho_token_expires = row["expires_at"]
        except Exception:
            pass
    
    integrations["zoho"] = {
        "name": "Zoho CRM",
        "configured": zoho_configured,
        "token_status": zoho_token or "not_configured",
        "token_expires": zoho_token_expires,
        "capabilities": ["Search contacts", "Create tasks", "List contacts"]
    }
    
    # Email (IMAP/SMTP)
    email_imap_configured = all([
        os.getenv("EMAIL_IMAP_HOST"),
        os.getenv("EMAIL_IMAP_USER"),
        os.getenv("EMAIL_IMAP_PASSWORD")
    ])
    email_smtp_configured = all([
        os.getenv("EMAIL_SMTP_HOST"),
        os.getenv("EMAIL_SMTP_USER"),
        os.getenv("EMAIL_SMTP_PASSWORD")
    ])
    integrations["email"] = {
        "name": "Email (IMAP/SMTP)",
        "configured": email_imap_configured and email_smtp_configured,
        "imap_configured": email_imap_configured,
        "smtp_configured": email_smtp_configured,
        "capabilities": ["Read emails", "Send emails", "Search emails"]
    }
    
    # Calendar (Google Calendar)
    calendar_configured = all([
        os.getenv("GOOGLE_CLIENT_ID"),
        os.getenv("GOOGLE_CLIENT_SECRET"),
        os.getenv("GOOGLE_REFRESH_TOKEN")
    ])
    calendar_token = None
    calendar_token_expires = None
    if calendar_configured:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT expires_at, updated_at
                FROM integration_tokens
                WHERE provider = 'calendar'
            """)
            row = cursor.fetchone()
            conn.close()
            if row:
                calendar_token = "present"
                calendar_token_expires = row["expires_at"]
        except Exception:
            pass
    
    integrations["calendar"] = {
        "name": "Google Calendar",
        "configured": calendar_configured,
        "token_status": calendar_token or "not_configured",
        "token_expires": calendar_token_expires,
        "capabilities": ["Get upcoming events", "Create events"],
        "note": "OAuth2 setup required (skeleton implementation)"
    }
    
    # Twilio
    twilio_configured = all([
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
        os.getenv("TWILIO_FROM_NUMBER")
    ])
    integrations["twilio"] = {
        "name": "Twilio (SMS/Voice)",
        "configured": twilio_configured,
        "capabilities": ["Send SMS", "Place calls (future)"]
    }
    
    return {"integrations": integrations}


if __name__ == "__main__":
    # Default port 7130, can be overridden via env
    port = int(os.getenv("QIOS_LOCAL_PORT", "7130"))
    uvicorn.run(app, host="0.0.0.0", port=port)

