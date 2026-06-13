"""
Web search tool for GINA.
Searches the web using a configurable search API.
"""
import os
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


async def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Search the web for information.
    
    Args:
        args: {
            "query": str - Search query
            "max_results": int - Max results (default: 5)
        }
        env: Environment context
    
    Returns:
        {
            "query": str,
            "results": [
                {
                    "title": str,
                    "url": str,
                    "snippet": str
                }
            ]
        }
    """
    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    
    if not query:
        raise ValueError("Query is required")
    
    # Check for search API configuration
    search_api_url = os.getenv("WEB_SEARCH_API_URL")
    search_api_key = os.getenv("WEB_SEARCH_API_KEY")
    
    if not search_api_url:
        # Return a helpful error message
        return {
            "query": query,
            "results": [],
            "error": "WEB_SEARCH_API_URL not configured. Set environment variable to enable web search.",
            "note": "You can configure a search API (e.g. SerpAPI, Google Custom Search) via WEB_SEARCH_API_URL and WEB_SEARCH_API_KEY"
        }
    
    # Make search request
    try:
        headers = {}
        if search_api_key:
            headers["Authorization"] = f"Bearer {search_api_key}"
        
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    search_api_url,
                    params={"q": query, "num": max_results},
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                else:
                    return {
                        "query": query,
                        "results": [],
                        "error": f"Search API returned {response.status_code}"
                    }
        elif HAS_REQUESTS:
            response = requests.get(
                search_api_url,
                params={"q": query, "num": max_results},
                headers=headers,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
            else:
                return {
                    "query": query,
                    "results": [],
                    "error": f"Search API returned {response.status_code}"
                }
        else:
            return {
                "query": query,
                "results": [],
                "error": "No HTTP client available (install httpx or requests)"
            }
        
        # Parse results (adjust based on your search API format)
        results = []
        if isinstance(data, dict):
            # Common formats: items, results, organic_results
            items = data.get("items") or data.get("results") or data.get("organic_results", [])
            for item in items[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", item.get("link", "")),
                    "snippet": item.get("snippet", item.get("description", ""))
                })
        
        return {
            "query": query,
            "results": results
        }
    
    except Exception as e:
        return {
            "query": query,
            "results": [],
            "error": f"Search failed: {str(e)}"
        }

