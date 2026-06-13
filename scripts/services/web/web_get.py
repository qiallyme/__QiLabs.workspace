"""
Web content fetcher for GINA.
Fetches content from a given URL.
"""
import os
from urllib.parse import urlparse
from typing import Dict, Any

# Try to use httpx (async) or requests (sync)
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


def is_safe_url(url: str) -> bool:
    """Check if URL is safe to fetch (not file:// or localhost)."""
    parsed = urlparse(url)
    
    # Block file:// URLs
    if parsed.scheme == "file":
        return False
    
    # Block localhost/127.0.0.1/0.0.0.0
    hostname = parsed.hostname or ""
    if hostname.lower() in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
        return False
    
    # Block private IP ranges (basic check)
    if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172."):
        return False
    
    return True


async def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Fetch content from a URL.
    
    Args:
        args: {
            "url": str - URL to fetch
        }
        env: Environment context
    
    Returns:
        {
            "url": str,
            "status_code": int,
            "content_type": str,
            "text_snippet": str (first 2000 chars)
        }
    """
    url = args.get("url", "")
    
    if not url:
        raise ValueError("URL is required")
    
    # Safety check
    if not is_safe_url(url):
        return {
            "url": url,
            "status_code": 0,
            "error": "URL is not safe to fetch (file:// or localhost blocked)"
        }
    
    try:
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                text = response.text[:2000] if response.text else ""
                
                return {
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "text_snippet": text
                }
        elif HAS_REQUESTS:
            response = requests.get(url, timeout=10.0, allow_redirects=True)
            text = response.text[:2000] if response.text else ""
            
            return {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "text_snippet": text
            }
        else:
            return {
                "url": url,
                "status_code": 0,
                "error": "No HTTP client available (install httpx or requests)"
            }
    
    except Exception as e:
        return {
            "url": url,
            "status_code": 0,
            "error": f"Failed to fetch URL: {str(e)}"
        }

