"""
RAG (Retrieval-Augmented Generation) utilities for GINA.

Provides semantic search over semantic_profile embeddings using Supabase vector similarity.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load .env file from project root
try:
    from dotenv import load_dotenv
    QIOS_ROOT = Path(__file__).parent.parent.parent
    env_path = QIOS_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use system env vars

# Supabase client for RPC calls
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    print("Warning: supabase-py not installed. Install with: pip install supabase")

# Ollama for query embeddings
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    raise ImportError("Need httpx for Ollama embeddings")

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIM = 768  # nomic-embed-text dimension

# Initialize Supabase client
supabase_client: Optional[Client] = None
if HAS_SUPABASE and SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client for RAG: {e}")
        supabase_client = None
elif not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("Warning: SUPABASE_URL or SUPABASE_ANON_KEY not set. RAG search will fail.")


async def embed_query(query: str) -> List[float]:
    """
    Generate embedding for a query string using Ollama.
    
    Args:
        query: Search query text
        
    Returns:
        List[float]: 768-dimensional embedding vector
        
    Raises:
        RuntimeError: If embedding generation fails
    """
    if not query or not query.strip():
        raise RuntimeError("Cannot embed empty query.")
    
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": OLLAMA_EMBEDDING_MODEL,
        "prompt": query,
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
    except Exception as e:
        raise RuntimeError(f"Ollama connection failed: {e}") from e
    
    resp.raise_for_status()
    data = resp.json()
    emb = data.get("embedding")
    
    if not emb or not isinstance(emb, list):
        raise RuntimeError("No embedding returned from Ollama for query.")
    
    if len(emb) != EMBEDDING_DIM:
        raise RuntimeError(f"Unexpected embedding dimension: {len(emb)} (expected {EMBEDDING_DIM})")
    
    return emb


async def search_semantic_profile_async(
    query: str,
    limit: int = 10,
    realm: Optional[str] = None,
    min_score: float = 0.0,
    path_prefix: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Async RAG search used by GINA/local_core.
    
    Search semantic_profile using vector similarity via Supabase RPC.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        realm: Optional realm filter
        min_score: Minimum similarity score (distance threshold, lower = more similar)
        path_prefix: Optional file path prefix filter
    
    Returns:
        List of dicts with: id, file_path, content, realm, slug, score, distance
    """
    if not supabase_client:
        print("Error: Supabase client not initialized. Cannot perform vector search.")
        return []
    
    if not query or not query.strip():
        return []
    
    try:
        # Generate query embedding (async)
        query_emb = await embed_query(query)
        
        # Call Supabase RPC (sync client, run in executor to avoid blocking)
        def _rpc():
            rpc_params = {
                "query_embedding": query_emb,
                "match_count": limit,
                "filter_realm": realm,
                "filter_path_prefix": path_prefix
            }
            # Remove None values from params
            rpc_params = {k: v for k, v in rpc_params.items() if v is not None}
            return supabase_client.rpc("match_semantic_profile", rpc_params).execute()
        
        # Run sync Supabase call in executor
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, _rpc)
        
        if not resp.data:
            return []
        
        # Normalize results
        results = []
        for row in resp.data:
            # Extract text content
            chunk_text = row.get("chunk_text") or ""
            text_preview = chunk_text[:500] + "..." if len(chunk_text) > 500 else chunk_text
            
            # Distance: lower = more similar
            # Convert to score: higher = more similar (1 - normalized distance)
            distance = row.get("distance", 1.0)
            score = max(0.0, 1.0 - (distance / 2.0))  # Normalize distance to 0-1 score
            
            # Skip if below min_score threshold
            if score < min_score:
                continue
            
            results.append({
                "id": row.get("id"),
                "file_path": row.get("file_path") or "",
                "content": text_preview,
                "realm": row.get("realm") or "",
                "realm_slug": row.get("realm_slug") or "",
                "slug": "",  # Not in RPC response, can be added if needed
                "score": score,
                "distance": distance,
                "chunk_text": chunk_text,
                "chunk_id": row.get("chunk_id") or ""
            })
        
        return results
    
    except Exception as e:
        print(f"Error in semantic search: {e}")
        import traceback
        traceback.print_exc()
        return []


def search_semantic_profile(
    query: str,
    limit: int = 10,
    realm: Optional[str] = None,
    min_score: float = 0.0,
    path_prefix: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Sync wrapper for CLI / sanity tests.
    Safe to call from non-async code.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        realm: Optional realm filter
        min_score: Minimum similarity score (distance threshold, lower = more similar)
        path_prefix: Optional file path prefix filter
    
    Returns:
        List of dicts with: id, file_path, content, realm, slug, score, distance
    """
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context - this shouldn't be called!
        raise RuntimeError(
            "search_semantic_profile() called from async context. "
            "Use search_semantic_profile_async() instead."
        )
    except RuntimeError:
        # asyncio.get_running_loop() raises RuntimeError when no loop is running
        # This is expected for sync code - safe to use asyncio.run()
        pass
    
    # No event loop running, safe to use asyncio.run()
    return asyncio.run(
        search_semantic_profile_async(
            query,
            limit=limit,
            realm=realm,
            min_score=min_score,
            path_prefix=path_prefix
        )
    )


def search_with_embedding(
    query: str,
    limit: int = 10,
    realm: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search using embedding similarity (alias for search_semantic_profile).
    
    This function now uses Supabase vector similarity via RPC.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        realm: Optional realm filter
    
    Returns:
        List of dicts with: id, file_path, content, realm, slug, score
    """
    return search_semantic_profile(query, limit=limit, realm=realm)

