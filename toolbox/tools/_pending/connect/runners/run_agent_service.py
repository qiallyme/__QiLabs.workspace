"""
Call qios_agent HTTP API to start services, scan, extract, etc.
"""
import os
import httpx
from typing import Dict, Any

QIOS_AGENT_URL = os.getenv("QIOS_AGENT_URL", "http://localhost:5050")


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Call qios_agent HTTP API endpoint.
    
    Args:
        args: {
            "endpoint": str - Agent endpoint (e.g., "/start/workers", "/start/dev-stack", "/agent/scan", "/agent/extract")
            "params": dict - Optional parameters for the endpoint (default: {})
        }
        env: Environment context
    
    Returns:
        {
            "success": bool,
            "endpoint": str,
            "response": dict | None,
            "error": str | None
        }
    """
    endpoint = args.get("endpoint", "")
    params = args.get("params", {})
    
    if not endpoint:
        return {
            "success": False,
            "endpoint": "",
            "response": None,
            "error": "endpoint is required"
        }
    
    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    
    url = f"{QIOS_AGENT_URL}{endpoint}"
    
    try:
        # Make HTTP request to agent
        with httpx.Client(timeout=30.0) as client:
            if params:
                # POST request with params
                response = client.post(url, json=params)
            else:
                # GET request
                response = client.get(url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        "success": True,
                        "endpoint": endpoint,
                        "response": data,
                        "error": None
                    }
                except:
                    # Response is not JSON
                    return {
                        "success": True,
                        "endpoint": endpoint,
                        "response": {"text": response.text},
                        "error": None
                    }
            else:
                return {
                    "success": False,
                    "endpoint": endpoint,
                    "response": None,
                    "error": f"Agent returned status {response.status_code}: {response.text}"
                }
    
    except httpx.ConnectError:
        return {
            "success": False,
            "endpoint": endpoint,
            "response": None,
            "error": f"Could not connect to agent at {QIOS_AGENT_URL}. Make sure qios_agent server is running."
        }
    except Exception as e:
        return {
            "success": False,
            "endpoint": endpoint,
            "response": None,
            "error": f"Failed to call agent: {str(e)}"
        }

