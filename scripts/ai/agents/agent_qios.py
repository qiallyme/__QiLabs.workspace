#!/usr/bin/env python
"""
QiOS Local Scanner Agent (Step 0 + Stage 1)

- Step 0: Scans QiOS/_intake (except manual_review/)
  - Computes content_hash
  - Upserts rows into ingestion_queue + file_history

- Stage 1: Extracts text from pending files
  - Reads .md, .txt directly
  - Extracts from .docx using python-docx
  - Inserts into semantic_profile with extracted_text
  - Updates ingestion_queue status
"""

import os
import sys
import hashlib
import mimetypes
import time
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

# ------------------------
# CONFIG
# ------------------------

# Adjust these if needed
QIOS_ROOT = Path(os.getenv("QIOS_ROOT", r"C:\QiOS_v1")).resolve()
INTAKE_ROOT = QIOS_ROOT / "_intake"

# Supabase env vars must be in your .env at QiOS root
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=xxxx
ENV_PATH = QIOS_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("[ERROR] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env", file=sys.stderr)
    sys.exit(1)

SUPABASE_REST = SUPABASE_URL.rstrip("/") + "/rest/v1"

# Batch size for upserts (avoid hitting request limits)
BATCH_SIZE = 50

# ------------------------
# FILE CLASSIFICATION
# ------------------------

TEXT_EXTS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv", ".sql", ".py", ".js", ".ts", ".html", ".css", ".xml"}
DOC_EXTS = {".docx", ".doc"}
PDF_EXTS = {".pdf"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".opus"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".webm", ".flv", ".m4v", ".3gp"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic", ".tiff", ".tif"}
IGNORE_EXTS = {".lock", ".tmp", ".swp", ".bak", ".log"}


def classify_file(path: Path) -> str:
    """
    Return a simple category so Gina/orchestrator can reason about it later.
    
    Returns: "text", "docx", "pdf", "audio", "video", "image", "binary", "ignore"
    """
    ext = path.suffix.lower()
    
    if ext in IGNORE_EXTS:
        return "ignore"
    if ext in TEXT_EXTS:
        return "text"
    if ext in DOC_EXTS:
        return "docx"
    if ext in PDF_EXTS:
        return "pdf"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    
    # fallback
    return "binary"

# ------------------------
# UTILITIES
# ------------------------

def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        raise IOError(f"Failed to read {path}: {e}") from e


def rel_path(path: Path) -> str:
    """Return repo-relative path like '_intake/desktop_drops/file.pdf'."""
    try:
        return str(path.relative_to(QIOS_ROOT)).replace("\\", "/")
    except ValueError:
        # Path is outside QIOS_ROOT, return as-is
        return str(path).replace("\\", "/")


def guess_mime(path: Path) -> str:
    """Guess MIME type from file extension."""
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def now_tz() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def supabase_upsert(
    table: str, 
    rows: List[Dict[str, Any]], 
    on_conflict: Optional[str] = None,
    batch_size: int = BATCH_SIZE
) -> tuple[int, int]:
    """
    Upsert or insert rows into Supabase table in batches.
    
    Args:
        table: Table name
        rows: List of row dictionaries
        on_conflict: Optional conflict target for upserts (e.g., "file_path").
                     If None, performs plain inserts.
        batch_size: Number of rows per batch
    
    Returns: (success_count, error_count)
    """
    if not rows:
        return (0, 0)
    
    url = f"{SUPABASE_REST}/{table}"
    
    # Adjust Prefer header based on operation type
    if on_conflict:
        prefer_header = "resolution=merge-duplicates,return=representation"
    else:
        prefer_header = "return=representation"
    
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer_header
    }
    
    success_count = 0
    error_count = 0
    
    # Process in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        
        try:
            params = {}
            if on_conflict:
                params["on_conflict"] = on_conflict
            
            resp = requests.post(
                url, 
                headers=headers, 
                params=params if params else None, 
                data=json.dumps(batch),
                timeout=30
            )
            
            if not resp.ok:
                error_msg = resp.text[:500]  # Truncate long errors
                operation = "upsert" if on_conflict else "insert"
                print(
                    f"[ERROR] Supabase {operation} to {table} failed (batch {i//batch_size + 1}): "
                    f"{resp.status_code} {error_msg}",
                    file=sys.stderr
                )
                error_count += len(batch)
            else:
                success_count += len(batch)
                operation = "Upserted" if on_conflict else "Inserted"
                print(f"[OK] {operation} {len(batch)} row(s) into {table} (batch {i//batch_size + 1})")
                
        except requests.exceptions.RequestException as e:
            print(
                f"[ERROR] Network error upserting to {table}: {e}",
                file=sys.stderr
            )
            error_count += len(batch)
        except Exception as e:
            print(
                f"[ERROR] Unexpected error upserting to {table}: {e}",
                file=sys.stderr
            )
            error_count += len(batch)
    
    return (success_count, error_count)


# ------------------------
# SCAN + QUEUE
# ------------------------

SKIP_DIRS = {"manual_review", "quarantine"}  # stage 0: we ignore these completely


def find_intake_files() -> List[Path]:
    """Find all files in _intake, excluding skip directories."""
    files: List[Path] = []
    
    if not INTAKE_ROOT.exists():
        print(f"[WARN] Intake root does not exist: {INTAKE_ROOT}")
        return files
    
    if not INTAKE_ROOT.is_dir():
        print(f"[WARN] Intake root is not a directory: {INTAKE_ROOT}")
        return files
    
    try:
        for root, dirs, filenames in os.walk(INTAKE_ROOT):
            # Mutate dirs in-place to skip folders
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            
            for fn in filenames:
                p = Path(root) / fn
                # Skip hidden files and system files
                if not fn.startswith(".") and not fn.startswith("~"):
                    files.append(p)
                    
    except Exception as e:
        print(f"[ERROR] Error walking intake directory: {e}", file=sys.stderr)
    
    return files


def build_ingestion_row(path: Path, content_hash: str) -> Dict[str, Any]:
    """Build a row for ingestion_queue table."""
    rp = rel_path(path)  # e.g. "_intake/desktop_drops/file.pdf"
    slug = path.stem
    mime = guess_mime(path)
    ext = path.suffix.lower().lstrip(".")
    
    # Very dumb initial realm guess: everything is QiVault until router improves it
    realm_guess = "QiVault"
    
    return {
        "file_path": rp,
        "slug": slug,
        "qid": None,
        "realm": None,
        "realm_guess": realm_guess,
        "realm_slug": None,
        "mime_type": mime,
        "file_ext": ext,
        "content_hash": content_hash,
        "route_confidence": 0,
        "status": "pending",
        "meta": {
            "source": "qios_agent_scan",
            "intake_root": str(INTAKE_ROOT.relative_to(QIOS_ROOT)),
        },
        "updated_at": now_tz(),
    }


def build_history_row(path: Path, content_hash: str) -> Dict[str, Any]:
    """Build a row for file_history table."""
    rp = rel_path(path)
    return {
        "file_path": rp,
        "content_hash": content_hash,
        "event_type": "seen",
        "actor": "qios_agent",
        "meta": {
            "intake": True,
        },
    }


def scan_and_queue() -> None:
    """Main scanning function: find files, hash them, upsert to Supabase."""
    print(f"[INFO] QiOS scanner starting. Root={QIOS_ROOT}")
    print(f"[INFO] Intake={INTAKE_ROOT}")
    
    if not INTAKE_ROOT.exists():
        print(f"[ERROR] Intake directory does not exist: {INTAKE_ROOT}")
        return
    
    files = find_intake_files()
    if not files:
        print("[INFO] No files found in intake.")
        return
    
    print(f"[INFO] Found {len(files)} files in intake.")
    
    ingestion_rows: List[Dict[str, Any]] = []
    history_rows: List[Dict[str, Any]] = []
    
    processed = 0
    skipped = 0
    
    for p in files:
        try:
            # Compute hash
            content_hash = sha256_file(p)
            processed += 1
            
            # Build rows
            ingestion_rows.append(build_ingestion_row(p, content_hash))
            history_rows.append(build_history_row(p, content_hash))
            
            if processed % 10 == 0:
                print(f"[INFO] Processed {processed}/{len(files)} files...")
                
        except IOError as e:
            skipped += 1
            print(f"[WARN] Skipping {p}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            skipped += 1
            print(f"[ERROR] Unexpected error processing {p}: {e}", file=sys.stderr)
            continue
    
    print(f"[INFO] Processing complete: {processed} processed, {skipped} skipped")
    
    # Batch upserts
    if ingestion_rows:
        print(f"[INFO] Upserting {len(ingestion_rows)} rows to ingestion_queue...")
        success, errors = supabase_upsert("ingestion_queue", ingestion_rows, on_conflict="file_path")
        print(f"[INFO] ingestion_queue: {success} succeeded, {errors} failed")
    
    if history_rows:
        print(f"[INFO] Inserting {len(history_rows)} rows to file_history...")
        # file_history is append-only event log, so use plain inserts (no upsert)
        success, errors = supabase_upsert("file_history", history_rows, on_conflict=None)
        print(f"[INFO] file_history: {success} succeeded, {errors} failed")
    
    print("[INFO] Scan complete.")


# ------------------------
# STAGE 1: EXTRACTION
# ------------------------

def get_file_metadata(path: Path) -> Dict[str, Any]:
    """
    Extract file metadata (size, dates, etc.) for any file type.
    
    Returns a dictionary with file metadata.
    """
    try:
        stat = path.stat()
        
        # Format file size
        size_bytes = stat.st_size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        
        # Format dates
        created_ts = stat.st_ctime
        modified_ts = stat.st_mtime
        
        created_dt = datetime.fromtimestamp(created_ts, tz=timezone.utc)
        modified_dt = datetime.fromtimestamp(modified_ts, tz=timezone.utc)
        
        return {
            "file_name": path.name,
            "file_stem": path.stem,
            "file_ext": path.suffix.lower(),
            "file_size_bytes": size_bytes,
            "file_size_human": size_str,
            "created_at": created_dt.isoformat(),
            "modified_at": modified_dt.isoformat(),
            "created_timestamp": created_ts,
            "modified_timestamp": modified_ts,
        }
    except Exception as e:
        # Return minimal metadata even if stat fails
        return {
            "file_name": path.name,
            "file_stem": path.stem,
            "file_ext": path.suffix.lower(),
            "error": f"Failed to read file stats: {e}",
        }


def create_metadata_description(path: Path, metadata: Dict[str, Any], file_type: str) -> str:
    """
    Create a text description from file metadata for files we can't extract text from.
    
    This allows semantic search to find files by name, size, dates, etc.
    """
    name = metadata.get("file_name", path.name)
    size = metadata.get("file_size_human", "unknown size")
    created = metadata.get("created_at", "unknown date")
    modified = metadata.get("modified_at", "unknown date")
    
    # Create a descriptive text based on file type
    if file_type == "image":
        desc = f"Image file: {name}\nFile size: {size}\nCreated: {created}\nModified: {modified}\n\nThis is an image file. Text content extraction (OCR) is pending. File metadata extracted from filesystem."
    elif file_type == "video":
        desc = f"Video file: {name}\nFile size: {size}\nCreated: {created}\nModified: {modified}\n\nThis is a video file. Audio transcription (ASR) is pending. File metadata extracted from filesystem."
    elif file_type == "audio":
        desc = f"Audio file: {name}\nFile size: {size}\nCreated: {created}\nModified: {modified}\n\nThis is an audio file. Audio transcription (ASR) is pending. File metadata extracted from filesystem."
    elif file_type == "pdf":
        desc = f"PDF document: {name}\nFile size: {size}\nCreated: {created}\nModified: {modified}\n\nThis is a PDF file. Text extraction (OCR) is pending. File metadata extracted from filesystem."
    else:
        desc = f"File: {name}\nType: {file_type}\nFile size: {size}\nCreated: {created}\nModified: {modified}\n\nFile metadata extracted from filesystem. Text content extraction not yet implemented for this file type."
    
    return desc


def extract_text_markdown(path: Path) -> str:
    """Extract text from .md or .txt files."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except PermissionError as e:
        raise IOError(f"Permission denied reading {path}: {e}") from e
    except Exception as e:
        raise IOError(f"Failed to read text file {path}: {e}") from e


def extract_text_docx(path: Path) -> str:
    """Extract text from .docx files using python-docx."""
    try:
        from docx import Document
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)
        if not text.strip():
            raise ValueError("Document appears to be empty")
        return text
    except ImportError:
        raise ImportError("python-docx not installed. Run: pip install python-docx")
    except Exception as e:
        raise IOError(f"Failed to extract from DOCX {path}: {e}") from e


def extract_text_pdf(path: Path) -> str:
    """Placeholder for PDF extraction (OCR path - to be implemented)."""
    # TODO: Implement PDF → images → OCR pipeline
    raise NotImplementedError("PDF extraction not yet implemented. Use OCR pipeline.")


def extract_text_media(path: Path) -> str:
    """Placeholder for media extraction (ASR path - to be implemented)."""
    # TODO: Implement audio/video → ASR transcription pipeline
    raise NotImplementedError("Media extraction (ASR) not yet implemented.")


def extract_text_from_file(root_path: Path, rel_path: str) -> tuple[Optional[str], str]:
    """
    Extract text from a file based on its classification.
    
    Returns: (text, status_hint)
    
    status_hint values:
      - "ok"           → got usable text
      - "empty"        → file readable but empty
      - "unsupported"  → we will never handle this here (e.g. .exe)
      - "needs_ocr"    → pdf/image but OCR pipeline not wired yet
      - "needs_asr"    → audio/video waiting for ASR
      - "ignore"       → explicitly ignored type
      - "error"        → extraction failed
    """
    full_path = root_path / rel_path
    
    if not full_path.exists():
        return None, "error"  # File not found
    
    category = classify_file(full_path)
    
    if category == "ignore":
        return None, "ignore"
    
    try:
        if category == "text":
            text = extract_text_markdown(full_path)
            return (text, "ok" if text.strip() else "empty")
        
        if category == "docx":
            text = extract_text_docx(full_path)
            return (text, "ok" if text.strip() else "empty")
        
        if category == "pdf":
            # For now we *mark* it as needing OCR instead of erroring
            return None, "needs_ocr"
        
        if category == "image":
            # Images need OCR pipeline
            return None, "needs_ocr"
        
        if category == "audio" or category == "video":
            # We will pipe these into ASR later
            return None, "needs_asr"
        
        # Everything else – binary/unknown
        return None, "unsupported"
        
    except Exception as e:
        # Extraction failed
        print(f"[WARN] Extraction error for {rel_path}: {e}", file=sys.stderr)
        return None, "error"


def fetch_all_queue_rows() -> List[Dict[str, Any]]:
    """
    Fetch all queue rows with pagination.
    """
    rows = []
    page_size = 1000
    offset = 0
    
    url = f"{SUPABASE_REST}/ingestion_queue"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    
    while True:
        params = {
            "select": "*",
            "offset": str(offset),
            "limit": str(page_size),
            "order": "id.asc",
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
            if not resp.ok:
                print(f"[ERROR] Failed to fetch queue rows: {resp.status_code}", file=sys.stderr)
                break
            
            batch = resp.json() or []
            if not batch:
                break
            
            rows.extend(batch)
            
            if len(batch) < page_size:
                break
            
            offset += page_size
            
            if offset % 5000 == 0:
                print(f"[INFO] Fetched {offset} queue rows...")
                
        except Exception as e:
            print(f"[ERROR] Error fetching queue rows: {e}", file=sys.stderr)
            break
    
    return rows


def fetch_pending_queue_items(limit: int = 50, prioritize_text: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch pending items from ingestion_queue.
    
    Args:
        limit: Maximum number of items to fetch
        prioritize_text: If True, prioritize .md, .txt, .docx files and skip .trash directories
    """
    url = f"{SUPABASE_REST}/ingestion_queue"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    
    # Query: status='pending', ordered by updated_at (or created_at), limit
    params = {
        "status": "eq.pending",
        "order": "updated_at.asc.nullslast,file_path.asc",
        "limit": str(limit * 3 if prioritize_text else limit),  # Fetch more to filter
        "select": "*"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if not resp.ok:
            print(f"[ERROR] Failed to fetch pending items: {resp.status_code} {resp.text[:500]}", file=sys.stderr)
            return []
        
        items = resp.json() or []
        
        # Filter and prioritize if requested
        if prioritize_text:
            # Supported text file extensions
            supported_exts = {".md", ".txt", ".markdown", ".docx"}
            
            # Separate into supported and unsupported
            supported = []
            unsupported = []
            
            for item in items:
                file_path = item.get("file_path", "")
                file_ext = item.get("file_ext", "").lower()
                
                # Skip .trash directories
                if ".trash" in file_path.lower() or "/trash/" in file_path.lower():
                    continue
                
                # Check if supported
                if f".{file_ext}" in supported_exts or any(file_path.lower().endswith(ext) for ext in supported_exts):
                    supported.append(item)
                else:
                    unsupported.append(item)
            
            # Return supported first, then unsupported, up to limit
            result = supported[:limit]
            remaining = limit - len(result)
            if remaining > 0:
                result.extend(unsupported[:remaining])
            
            if len(supported) > 0:
                print(f"[INFO] Prioritized {len(supported)} text files, {len(unsupported)} other files in queue")
            
            return result
        else:
            return items[:limit]
            
    except Exception as e:
        print(f"[ERROR] Error fetching pending items: {e}", file=sys.stderr)
        return []


def upsert_semantic_profile(row: Dict[str, Any], extracted_text: str, file_metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Upsert a row into semantic_profile with extracted text."""
    url = f"{SUPABASE_REST}/semantic_profile"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation"
    }
    
    # Merge metadata into meta field
    existing_meta = row.get("meta", {})
    if isinstance(existing_meta, str):
        try:
            existing_meta = json.loads(existing_meta)
        except:
            existing_meta = {}
    
    if file_metadata:
        existing_meta["file_metadata"] = file_metadata
    
    profile = {
        "file_path": row["file_path"],
        "realm": row.get("realm") or row.get("realm_guess") or "QiVault",
        "realm_slug": row.get("realm_slug"),
        "qid": row.get("qid"),
        "slug": row.get("slug"),
        "mime_type": row.get("mime_type"),
        "file_ext": row.get("file_ext"),
        "content_hash": row.get("content_hash"),
        "extracted_text": extracted_text,  # Always populated (text or metadata description)
        "chunk_count": 0,
        "embedding_status": "pending",  # Embedder will pick this up
        "meta": existing_meta,
        "updated_at": now_tz(),
    }
    
    params = {"on_conflict": "file_path"}
    
    try:
        resp = requests.post(url, headers=headers, params=params, data=json.dumps(profile), timeout=30)
        if not resp.ok:
            error_msg = resp.text[:500]
            print(f"[ERROR] Failed to upsert semantic_profile for {row['file_path']}: {resp.status_code} {error_msg}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Error upserting semantic_profile for {row['file_path']}: {e}", file=sys.stderr)
        return False


def update_queue_status(file_path_or_id: str, status: str, error_message: Optional[str] = None, by_id: bool = False) -> bool:
    """
    Update ingestion_queue status for a file.
    
    Args:
        file_path_or_id: Either file_path (string) or row id (int/string)
        status: New status value
        error_message: Optional error message to store in meta
        by_id: If True, treat file_path_or_id as row id; otherwise as file_path
    """
    url = f"{SUPABASE_REST}/ingestion_queue"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    update_data: Dict[str, Any] = {
        "status": status,
        "updated_at": now_tz(),
    }
    
    if error_message:
        # Store error in meta
        update_data["meta"] = {"extraction_error": error_message}
    
    # Use PATCH with appropriate filter
    if by_id:
        params = {"id": f"eq.{file_path_or_id}"}
    else:
        params = {"file_path": f"eq.{file_path_or_id}"}
    
    try:
        resp = requests.patch(url, headers=headers, params=params, data=json.dumps(update_data), timeout=30)
        if not resp.ok:
            error_msg = resp.text[:500]
            print(f"[ERROR] Failed to update queue status: {resp.status_code} {error_msg}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Error updating queue status: {e}", file=sys.stderr)
        return False


def run_extract_pass(root_path: Optional[Path] = None, limit: int = 50, prioritize_text: bool = True) -> None:
    """
    Run one extraction pass: fetch pending, extract text, upsert to semantic_profile.
    
    Args:
        root_path: Root path to scan (default: QIOS_ROOT)
        limit: Maximum number of files to process
        prioritize_text: If True, prioritize text files (.md, .txt, .docx) and skip .trash
    """
    if root_path is None:
        root_path = QIOS_ROOT
    
    print(f"[INFO] Running extract pass (limit={limit}, prioritize_text={prioritize_text})")
    
    # Fetch pending items
    pending_items = fetch_pending_queue_items(limit, prioritize_text=prioritize_text)
    if not pending_items:
        print("[INFO] No pending items in ingestion_queue.")
        return
    
    print(f"[INFO] Found {len(pending_items)} pending items to process.")
    
    success = 0
    unsupported = 0
    needs_ocr = 0
    needs_asr = 0
    errors = 0
    ignored = 0
    empties = 0
    
    for i, row in enumerate(pending_items):
        rel_path = row.get("file_path", "")
        if not rel_path:
            print(f"[WARN] Item {i+1} missing file_path, skipping.", file=sys.stderr)
            errors += 1
            continue
        
        row_id = row.get("id")
        
        try:
            text, status_hint = extract_text_from_file(root_path, rel_path)
            
            if status_hint == "ignore":
                update_queue_status(rel_path, "ignored", "ignored_by_classifier", by_id=False)
                ignored += 1
                continue
            
            if status_hint == "unsupported":
                update_queue_status(rel_path, "unsupported", "unsupported_type", by_id=False)
                unsupported += 1
                continue
            
            if status_hint == "needs_ocr":
                update_queue_status(rel_path, "needs_ocr", "pdf_or_image_awaiting_ocr", by_id=False)
                needs_ocr += 1
                continue
            
            if status_hint == "needs_asr":
                update_queue_status(rel_path, "needs_asr", "media_awaiting_asr", by_id=False)
                needs_asr += 1
                continue
            
            if status_hint == "empty":
                update_queue_status(rel_path, "error", "empty_text", by_id=False)
                empties += 1
                continue
            
            if status_hint == "error":
                update_queue_status(rel_path, "error", "extraction_failed", by_id=False)
                errors += 1
                continue
            
            # status_hint == "ok"
            if not text or not text.strip():
                update_queue_status(rel_path, "error", "no_text_after_extraction")
                errors += 1
                continue
            
            # Extract metadata for semantic_profile
            full_path = root_path / rel_path
            file_metadata = get_file_metadata(full_path) if full_path.exists() else {}
            
            # Upsert to semantic_profile with embedding_status='pending'
            if upsert_semantic_profile(row, text, file_metadata):
                update_queue_status(rel_path, "complete", None, by_id=False)
                success += 1
                if (i + 1) % 10 == 0:
                    print(f"[INFO] Processed {i+1}/{len(pending_items)}...")
            else:
                update_queue_status(rel_path, "error", "failed_to_upsert_semantic_profile", by_id=False)
                errors += 1
        
        except Exception as e:
            print(f"[ERROR] Failed to extract {rel_path}: {e}", file=sys.stderr)
            update_queue_status(rel_path, "error", str(e), by_id=False)
            errors += 1
            continue
    
    print("\n" + "-" * 30)
    print("EXTRACT SUMMARY")
    print("-" * 30)
    print(f"Success:     {success}")
    print(f"Unsupported: {unsupported}")
    print(f"Needs OCR:   {needs_ocr}")
    print(f"Needs ASR:   {needs_asr}")
    print(f"Ignored:     {ignored}")
    print(f"Empty:       {empties}")
    print(f"Errors:      {errors}")
    print("-" * 30)


# ------------------------
# STAGE 0.5: RECONCILIATION
# ------------------------

def run_reconcile_pass(root_path: Optional[Path] = None) -> None:
    """
    Stage 0.5 – Reconcile ingestion_queue with real filesystem state.
    
    Compares actual files on disk against ingestion_queue entries and:
    - Marks missing files as 'missing'
    - Checks if files are already in semantic_profile (mark as 'complete')
    - Reports accurate pending count
    """
    if root_path is None:
        root_path = QIOS_ROOT
    
    print("[INFO] Running reconciliation pass...")
    print(f"[INFO] Scanning filesystem: {root_path}")
    
    # 1. Build a real-time set of files currently on disk
    real_files = []
    skipped_dirs = {"manual_review", "quarantine", ".trash", "__pycache__", ".git"}
    
    try:
        for path in root_path.rglob("*"):
            if path.is_file():
                # Skip hidden files and certain directories
                if any(skip in path.parts for skip in skipped_dirs):
                    continue
                if path.name.startswith(".") and path.name != ".env":
                    continue
                
                rel = rel_path(path)
                real_files.append(rel)
    except Exception as e:
        print(f"[ERROR] Error scanning filesystem: {e}", file=sys.stderr)
        return
    
    real_set = set(real_files)
    print(f"[INFO] Found {len(real_set)} real files on disk.")
    
    # 2. Pull all queue entries (with pagination)
    print("[INFO] Fetching all queue entries...")
    try:
        queue = fetch_all_queue_rows()
        print(f"[INFO] Found {len(queue)} entries in ingestion_queue.")
    except Exception as e:
        print(f"[ERROR] Failed to fetch queue: {e}", file=sys.stderr)
        return
    
    # 3. Check which files are already in semantic_profile
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    semantic_url = f"{SUPABASE_REST}/semantic_profile"
    semantic_params = {
        "select": "file_path",
    }
    
    try:
        semantic_resp = requests.get(semantic_url, headers=headers, params=semantic_params, timeout=60)
        processed_files = set()
        if semantic_resp.ok:
            semantic_data = semantic_resp.json() or []
            processed_files = {row.get("file_path") for row in semantic_data if row.get("file_path")}
            print(f"[INFO] Found {len(processed_files)} files already in semantic_profile.")
    except Exception as e:
        print(f"[WARN] Could not check semantic_profile: {e}", file=sys.stderr)
        processed_files = set()
    
    # 4. Analyze queue entries
    updates = []
    missing_count = 0
    already_processed_count = 0
    still_pending_count = 0
    already_complete_count = 0
    
    for row in queue:
        file_path = row.get("file_path", "")
        if not file_path:
            continue
        
        status = row.get("status", "pending")
        row_id = row.get("id")
        
        # FILE IS MISSING
        if file_path not in real_set:
            missing_count += 1
            if status != "missing":
                updates.append({
                    "id": row_id,
                    "status": "missing",
                    "meta": {"reconciliation_error": "file_missing", "reconciled_at": now_tz()},
                    "updated_at": now_tz(),
                })
            continue
        
        # FILE EXISTS - check if already processed
        if file_path in processed_files:
            if status == "pending":
                already_processed_count += 1
                updates.append({
                    "id": row_id,
                    "status": "complete",
                    "meta": {"reconciliation_note": "already_in_semantic_profile", "reconciled_at": now_tz()},
                    "updated_at": now_tz(),
                })
            elif status == "complete":
                already_complete_count += 1
            continue
        
        # FILE EXISTS BUT NOT PROCESSED
        if status == "pending":
            still_pending_count += 1
            continue
    
    # 5. Batch update missing/processed files
    if updates:
        print(f"[INFO] Marking {len(updates)} files in ingestion_queue...")
        
        url = f"{SUPABASE_REST}/ingestion_queue"
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        
        # Process in batches
        success_count = 0
        error_count = 0
        
        for i in range(0, len(updates), BATCH_SIZE):
            batch = updates[i:i + BATCH_SIZE]
            
            try:
                # Use PATCH for individual updates (Supabase doesn't support bulk PATCH easily)
                for update in batch:
                    update_id = update.pop("id")
                    update_url = f"{url}?id=eq.{update_id}"
                    
                    patch_resp = requests.patch(
                        update_url,
                        headers=headers,
                        data=json.dumps(update),
                        timeout=30
                    )
                    
                    if patch_resp.ok:
                        success_count += 1
                    else:
                        error_count += 1
                        if error_count <= 5:  # Only show first 5 errors
                            print(f"[WARN] Failed to update queue entry {update_id}: {patch_resp.status_code}", file=sys.stderr)
                
                # Progress indicator
                if (i + BATCH_SIZE) % 100 == 0:
                    print(f"[INFO] Updated {i + BATCH_SIZE}/{len(updates)} entries...")
                    
            except Exception as e:
                error_count += len(batch)
                print(f"[ERROR] Error updating batch: {e}", file=sys.stderr)
        
        print(f"[INFO] Queue updates: {success_count} succeeded, {error_count} failed")
    
    # 6. Final report
    print("\n" + "=" * 50)
    print("RECONCILIATION SUMMARY")
    print("=" * 50)
    print(f"Real files on disk:        {len(real_set):,}")
    print(f"Queue entries total:       {len(queue):,}")
    print(f"")
    print(f"Missing files marked:      {missing_count:,}")
    print(f"Already processed (fixed): {already_processed_count:,}")
    print(f"Already complete:          {already_complete_count:,}")
    print(f"Still pending (real):      {still_pending_count:,}")
    print("=" * 50)
    print(f"\n✅ Reconciliation complete!")
    print(f"   Next: Run 'python tools/qios_agent.py extract --limit 50' to process pending files.")


# ------------------------
# STATUS / HEALTH
# ------------------------

def run_status_pass() -> None:
    """
    Show high-level counts for ingestion_queue and semantic_profile.
    Uses efficient pagination to avoid loading all rows into memory.
    """
    print("[INFO] Fetching status summary...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    
    # Get ingestion_queue status counts (with pagination)
    queue_statuses = {}
    try:
        url = f"{SUPABASE_REST}/ingestion_queue"
        params = {"select": "status", "limit": "1000"}
        offset = 0
        
        while True:
            params["offset"] = str(offset)
            resp_q = requests.get(url, headers=headers, params=params, timeout=30)
            
            if not resp_q.ok:
                break
            
            queue_data = resp_q.json() or []
            if not queue_data:
                break
            
            for row in queue_data:
                status = row.get("status", "unknown")
                queue_statuses[status] = queue_statuses.get(status, 0) + 1
            
            if len(queue_data) < 1000:
                break
            offset += 1000
    except Exception as e:
        print(f"[WARN] Could not fetch ingestion_queue status: {e}", file=sys.stderr)
        queue_statuses = {}
    
    # Get semantic_profile status counts (with pagination)
    semantic_statuses = {}
    try:
        semantic_url = f"{SUPABASE_REST}/semantic_profile"
        params = {"select": "embedding_status", "limit": "1000"}
        offset = 0
        
        while True:
            params["offset"] = str(offset)
            resp_s = requests.get(semantic_url, headers=headers, params=params, timeout=30)
            
            if not resp_s.ok:
                break
            
            semantic_data = resp_s.json() or []
            if not semantic_data:
                break
            
            for row in semantic_data:
                status = row.get("embedding_status", "unknown")
                semantic_statuses[status] = semantic_statuses.get(status, 0) + 1
            
            if len(semantic_data) < 1000:
                break
            offset += 1000
    except Exception as e:
        print(f"[WARN] Could not fetch semantic_profile status: {e}", file=sys.stderr)
        semantic_statuses = {}
    
    # Get file_history total count (optional, for completeness)
    file_history_count = 0
    try:
        history_url = f"{SUPABASE_REST}/file_history"
        params = {"select": "id", "limit": "1"}
        resp_h = requests.get(history_url, headers=headers, params=params, timeout=10)
        if resp_h.ok:
            # Get count header if available, otherwise estimate
            count_header = resp_h.headers.get("content-range")
            if count_header:
                # Parse "0-0/12345" format
                try:
                    file_history_count = int(count_header.split("/")[-1])
                except:
                    pass
    except:
        pass
    
    print("\n" + "=" * 50)
    print("QIOS PIPELINE STATUS")
    print("=" * 50)
    print("\nINGESTION QUEUE")
    print("-" * 50)
    if queue_statuses:
        total = sum(queue_statuses.values())
        for status, count in sorted(queue_statuses.items()):
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {status:20s}: {count:>8,} ({pct:5.1f}%)")
        print(f"  {'TOTAL':20s}: {total:>8,}")
    else:
        print("  (no data)")
    
    print("\nSEMANTIC PROFILE")
    print("-" * 50)
    if semantic_statuses:
        total = sum(semantic_statuses.values())
        for status, count in sorted(semantic_statuses.items()):
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {status:20s}: {count:>8,} ({pct:5.1f}%)")
        print(f"  {'TOTAL':20s}: {total:>8,}")
    else:
        print("  (no data)")
    
    if file_history_count > 0:
        print("\nFILE HISTORY")
        print("-" * 50)
        print(f"  {'Total events':20s}: {file_history_count:>8,}")
    
    print("=" * 50)


# ------------------------
# HTTP SERVER (Agent API)
# ------------------------

AGENT_PORT = int(os.getenv("AGENT_PORT", "5050"))
AGENT_HOST = os.getenv("AGENT_HOST", "localhost")


class QiOSAgentHandler(BaseHTTPRequestHandler):
    """HTTP handler for QiOS Agent API"""
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == "/health":
            self.send_json_response({"status": "ok", "agent": "qios_agent", "port": AGENT_PORT})
        elif path == "/status":
            # Return status summary as JSON
            status_data = get_status_json()
            self.send_json_response(status_data)
        elif path == "/tables/ingestion_queue":
            limit = int(query.get("limit", ["100"])[0])
            data = fetch_queue_table(limit)
            self.send_json_response(data)
        elif path == "/tables/semantic_profile":
            limit = int(query.get("limit", ["100"])[0])
            data = fetch_semantic_profile_table(limit)
            self.send_json_response(data)
        elif path == "/tables/file_history":
            limit = int(query.get("limit", ["100"])[0])
            data = fetch_file_history_table(limit)
            self.send_json_response(data)
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == "/start/dev-stack":
            result = start_dev_stack()
            self.send_json_response(result)
        elif path == "/start/workers":
            worker_name = data.get("worker", None)
            result = start_worker(worker_name)
            self.send_json_response(result)
        elif path == "/start/qinote":
            result = start_qinote()
            self.send_json_response(result)
        elif path == "/agent/scan":
            result = run_scan_async()
            self.send_json_response(result)
        elif path == "/agent/extract":
            limit = data.get("limit", 50)
            result = run_extract_async(limit)
            self.send_json_response(result)
        elif path == "/agent/reconcile":
            result = run_reconcile_async()
            self.send_json_response(result)
        else:
            self.send_error(404, "Not Found")
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def get_status_json() -> Dict[str, Any]:
    """Get status summary as JSON"""
    # Simplified status for API
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    
    queue_statuses = {}
    try:
        url = f"{SUPABASE_REST}/ingestion_queue"
        params = {"select": "status", "limit": "1000"}
        offset = 0
        while True:
            params["offset"] = str(offset)
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if not resp.ok:
                break
            batch = resp.json() or []
            if not batch:
                break
            for row in batch:
                status = row.get("status", "unknown")
                queue_statuses[status] = queue_statuses.get(status, 0) + 1
            if len(batch) < 1000:
                break
            offset += 1000
    except:
        pass
    
    semantic_statuses = {}
    try:
        url = f"{SUPABASE_REST}/semantic_profile"
        params = {"select": "embedding_status", "limit": "1000"}
        offset = 0
        while True:
            params["offset"] = str(offset)
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if not resp.ok:
                break
            batch = resp.json() or []
            if not batch:
                break
            for row in batch:
                status = row.get("embedding_status", "unknown")
                semantic_statuses[status] = semantic_statuses.get(status, 0) + 1
            if len(batch) < 1000:
                break
            offset += 1000
    except:
        pass
    
    return {
        "ingestion_queue": queue_statuses,
        "semantic_profile": semantic_statuses,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def fetch_queue_table(limit: int = 100) -> Dict[str, Any]:
    """Fetch ingestion_queue table data"""
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    url = f"{SUPABASE_REST}/ingestion_queue"
    params = {"select": "*", "limit": str(limit), "order": "id.desc"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.ok:
            return {"data": resp.json() or [], "count": len(resp.json() or [])}
        return {"data": [], "count": 0, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


def fetch_semantic_profile_table(limit: int = 100) -> Dict[str, Any]:
    """Fetch semantic_profile table data"""
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    url = f"{SUPABASE_REST}/semantic_profile"
    params = {"select": "*", "limit": str(limit), "order": "created_at.desc"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.ok:
            return {"data": resp.json() or [], "count": len(resp.json() or [])}
        return {"data": [], "count": 0, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


def fetch_file_history_table(limit: int = 100) -> Dict[str, Any]:
    """Fetch file_history table data"""
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    url = f"{SUPABASE_REST}/file_history"
    params = {"select": "*", "limit": str(limit), "order": "event_time.desc"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.ok:
            return {"data": resp.json() or [], "count": len(resp.json() or [])}
        return {"data": [], "count": 0, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


def start_dev_stack() -> Dict[str, Any]:
    """Start all workers via PowerShell script"""
    try:
        script_path = QIOS_ROOT / "qios_start_all.ps1"
        if not script_path.exists():
            return {"success": False, "error": "qios_start_all.ps1 not found"}
        
        # Start in background
        subprocess.Popen(
            ["powershell", "-File", str(script_path)],
            cwd=str(QIOS_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        return {"success": True, "message": "Dev stack start requested"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_worker(worker_name: Optional[str] = None) -> Dict[str, Any]:
    """Start a specific worker or all workers"""
    try:
        if worker_name:
            worker_path = QIOS_ROOT / "workers" / worker_name
            if not worker_path.exists():
                return {"success": False, "error": f"Worker {worker_name} not found"}
            
            subprocess.Popen(
                ["powershell", "-NoExit", "-Command", f"cd '{worker_path}'; npx wrangler dev"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
            )
            return {"success": True, "message": f"Worker {worker_name} start requested"}
        else:
            # Start all workers
            return start_dev_stack()
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_qinote() -> Dict[str, Any]:
    """Start QiNote app"""
    try:
        qinote_path = QIOS_ROOT / "apps" / "QiNote"
        if not qinote_path.exists():
            return {"success": False, "error": "QiNote not found"}
        
        subprocess.Popen(
            ["powershell", "-NoExit", "-Command", f"cd '{qinote_path}'; npm run dev"],
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        return {"success": True, "message": "QiNote start requested"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_scan_async() -> Dict[str, Any]:
    """Run scan in background thread"""
    def _scan():
        try:
            scan_and_queue()
        except Exception as e:
            print(f"[ERROR] Scan failed: {e}", file=sys.stderr)
    
    thread = threading.Thread(target=_scan, daemon=True)
    thread.start()
    return {"success": True, "message": "Scan started in background"}


def run_extract_async(limit: int = 50) -> Dict[str, Any]:
    """Run extract in background thread"""
    def _extract():
        try:
            run_extract_pass(root_path=QIOS_ROOT, limit=limit, prioritize_text=True)
        except Exception as e:
            print(f"[ERROR] Extract failed: {e}", file=sys.stderr)
    
    thread = threading.Thread(target=_extract, daemon=True)
    thread.start()
    return {"success": True, "message": f"Extract started in background (limit={limit})"}


def run_reconcile_async() -> Dict[str, Any]:
    """Run reconcile in background thread"""
    def _reconcile():
        try:
            run_reconcile_pass(root_path=QIOS_ROOT)
        except Exception as e:
            print(f"[ERROR] Reconcile failed: {e}", file=sys.stderr)
    
    thread = threading.Thread(target=_reconcile, daemon=True)
    thread.start()
    return {"success": True, "message": "Reconcile started in background"}


def run_agent_server():
    """Run the HTTP server"""
    server = HTTPServer((AGENT_HOST, AGENT_PORT), QiOSAgentHandler)
    print(f"[INFO] QiOS Agent HTTP server starting on http://{AGENT_HOST}:{AGENT_PORT}")
    print(f"[INFO] Endpoints:")
    print(f"  GET  /health")
    print(f"  GET  /status")
    print(f"  GET  /tables/ingestion_queue?limit=100")
    print(f"  GET  /tables/semantic_profile?limit=100")
    print(f"  GET  /tables/file_history?limit=100")
    print(f"  POST /start/dev-stack")
    print(f"  POST /start/workers (body: {{\"worker\": \"name\"}})")
    print(f"  POST /start/qinote")
    print(f"  POST /agent/scan")
    print(f"  POST /agent/extract (body: {{\"limit\": 50}})")
    print(f"  POST /agent/reconcile")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down agent server...")
        server.shutdown()


# ------------------------
# CLI
# ------------------------

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QiOS Local Scanner Agent (Step 0 + Stage 1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Step 0: Scan intake directory
  python tools/qios_agent.py scan --intake
  
  # Stage 1: Extract text from pending files (default limit: 50)
  python tools/qios_agent.py extract
  
  # Stage 1: Extract with custom limit
  python tools/qios_agent.py extract --limit 100
  
  # Stage 0.5: Reconcile queue with filesystem (fix missing/processed files)
  python tools/qios_agent.py reconcile
  
  # Set QIOS_ROOT if different from default
  QIOS_ROOT=/path/to/qios python tools/qios_agent.py scan --intake
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan intake directory")
    scan_parser.add_argument(
        "--intake",
        action="store_true",
        help="Scan _intake and upsert into ingestion_queue + file_history",
    )
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract text from pending files")
    extract_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of files to process (default: 50)",
    )
    extract_parser.add_argument(
        "--no-prioritize",
        dest="no_prioritize",
        action="store_true",
        help="Don't prioritize text files (process in queue order)",
    )
    
    # Reconcile command
    reconcile_parser = subparsers.add_parser("reconcile", help="Reconcile ingestion_queue with filesystem state")
    reconcile_parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Override root path (default: QIOS_ROOT from env or C:\\QiOS_v1)",
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show pipeline status summary")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start HTTP API server")
    server_parser.add_argument(
        "--port",
        type=int,
        default=AGENT_PORT,
        help=f"Port to listen on (default: {AGENT_PORT})",
    )
    server_parser.add_argument(
        "--host",
        type=str,
        default=AGENT_HOST,
        help=f"Host to bind to (default: {AGENT_HOST})",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.command == "scan":
        if args.intake:
            scan_and_queue()
        else:
            scan_parser.print_help()
            sys.exit(1)
    elif args.command == "extract":
        no_prioritize = getattr(args, 'no_prioritize', False)
        run_extract_pass(root_path=QIOS_ROOT, limit=args.limit, prioritize_text=not no_prioritize)
    elif args.command == "reconcile":
        root_path = None
        if args.root:
            root_path = Path(args.root).resolve()
        run_reconcile_pass(root_path=root_path)
    elif args.command == "status":
        run_status_pass()
    elif args.command == "server":
        global AGENT_PORT, AGENT_HOST
        AGENT_PORT = args.port
        AGENT_HOST = args.host
        run_agent_server()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

