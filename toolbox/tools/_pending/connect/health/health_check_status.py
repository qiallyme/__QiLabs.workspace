"""
Quick status check for QiOS Local Core.
Shows what's configured and what's running.
"""
import os
import sys
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    QIOS_ROOT = Path(__file__).parent.parent.parent
    env_path = QIOS_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded .env from {env_path}")
    else:
        print(f"⚠ .env file not found at {env_path}")
except ImportError:
    print("⚠ python-dotenv not installed")

print("\n" + "=" * 60)
print("QiOS Local Core - Status Check")
print("=" * 60)

# Check environment variables
print("\n[Environment Variables]")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase_anon = os.getenv("SUPABASE_ANON_KEY")
ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ollama_embed = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
ollama_llm = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

print(f"  SUPABASE_URL: {'✓ SET' if supabase_url else '✗ NOT SET'}")
print(f"  SUPABASE_SERVICE_ROLE_KEY: {'✓ SET' if supabase_key else '✗ NOT SET'}")
print(f"  SUPABASE_ANON_KEY: {'✓ SET' if supabase_anon else '✗ NOT SET'}")
print(f"  OLLAMA_BASE_URL: {ollama_url}")
print(f"  OLLAMA_EMBEDDING_MODEL: {ollama_embed}")
print(f"  OLLAMA_LLM_MODEL: {ollama_llm}")

# Check Ollama
print("\n[Ollama]")
try:
    import httpx
    import asyncio
    
    async def check_ollama():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{ollama_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    print(f"  Status: ✓ Running")
                    print(f"  Available models: {', '.join(models) if models else 'none'}")
                    
                    has_embed = any(ollama_embed in m for m in models)
                    has_llm = any(ollama_llm in m for m in models)
                    
                    print(f"  {ollama_embed}: {'✓' if has_embed else '✗'}")
                    print(f"  {ollama_llm}: {'✓' if has_llm else '✗'}")
                    return True
                else:
                    print(f"  Status: ✗ Error (status {response.status_code})")
                    return False
        except httpx.ConnectError:
            print(f"  Status: ✗ Not running or not accessible")
            print(f"    Start with: ollama serve")
            return False
        except Exception as e:
            print(f"  Status: ✗ Error: {e}")
            return False
    
    asyncio.run(check_ollama())
except ImportError:
    print("  Status: ⚠ Cannot check (httpx not installed)")

# Check Supabase
print("\n[Supabase]")
if supabase_url and supabase_key:
    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        
        # Try a simple query
        result = client.table("semantic_profile").select("id").limit(1).execute()
        print(f"  Status: ✓ Connected")
        print(f"  semantic_profile table: {'✓ Has data' if result.data else '⚠ Empty'}")
        
        # Check RPC
        try:
            test_emb = [0.01] * 768
            rpc_result = client.rpc("match_semantic_profile", {
                "query_embedding": test_emb,
                "match_count": 1
            }).execute()
            print(f"  RPC function: ✓ Working")
        except Exception as e:
            print(f"  RPC function: ✗ Error: {str(e)[:100]}")
            print(f"    Run migration: data/migrations/004_standardize_embedding_768.sql")
    except Exception as e:
        print(f"  Status: ✗ Connection failed: {str(e)[:100]}")
else:
    print("  Status: ⚠ Not configured (missing credentials)")

# Check local core service
print("\n[Local Core Service]")
local_port = os.getenv("QIOS_LOCAL_PORT", "7130")
base_url = f"http://localhost:{local_port}"

try:
    import httpx
    import asyncio
    
    async def check_service():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Status: ✓ Running on port {local_port}")
                    print(f"  Health: {data.get('status', 'unknown')}")
                    return True
                else:
                    print(f"  Status: ⚠ Responding but error (status {response.status_code})")
                    return False
        except httpx.ConnectError:
            print(f"  Status: ✗ Not running")
            print(f"    Start with: python qios_local_core.py")
            return False
        except Exception as e:
            print(f"  Status: ✗ Error: {e}")
            return False
    
    asyncio.run(check_service())
except ImportError:
    print("  Status: ⚠ Cannot check (httpx not installed)")

print("\n" + "=" * 60)
print("Next Steps:")
print("  1. Fix any ✗ items above")
print("  2. Run tests: python tests/test_sanity_checks.py")
print("=" * 60)

