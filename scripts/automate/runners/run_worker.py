"""
Start a QiOS worker (local Python worker or Cloudflare Worker).
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

QIOS_ROOT = Path(__file__).parent.parent.parent.parent


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Start a worker by name.
    
    Args:
        args: {
            "worker_name": str - Name of worker to start (e.g., "local_core", "ingestion")
            "worker_type": str - Type: "local" or "cloudflare" (default: "local")
        }
        env: Environment context
    
    Returns:
        {
            "success": bool,
            "worker_name": str,
            "worker_type": str,
            "message": str,
            "process_id": int | None
        }
    """
    worker_name = args.get("worker_name", "")
    worker_type = args.get("worker_type", "local")
    
    if not worker_name:
        return {
            "success": False,
            "worker_name": "",
            "worker_type": worker_type,
            "message": "worker_name is required",
            "process_id": None
        }
    
    try:
        if worker_type == "local":
            # Start local Python worker
            worker_path = QIOS_ROOT / "workers" / worker_name
            
            if not worker_path.exists():
                return {
                    "success": False,
                    "worker_name": worker_name,
                    "worker_type": worker_type,
                    "message": f"Worker directory not found: {worker_path}",
                    "process_id": None
                }
            
            # Check if it's the local_core worker
            if worker_name == "local_core":
                worker_script = worker_path / "worker.py"
                if not worker_script.exists():
                    return {
                        "success": False,
                        "worker_name": worker_name,
                        "worker_type": worker_type,
                        "message": f"Worker script not found: {worker_script}",
                        "process_id": None
                    }
                
                # Start Python worker
                if sys.platform == "win32":
                    # Windows: use PowerShell
                    process = subprocess.Popen(
                        ["powershell", "-NoExit", "-Command", f"cd '{worker_path}'; python worker.py"],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    # Unix: use bash
                    process = subprocess.Popen(
                        ["bash", "-c", f"cd '{worker_path}' && python worker.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                
                return {
                    "success": True,
                    "worker_name": worker_name,
                    "worker_type": worker_type,
                    "message": f"Started local worker: {worker_name}",
                    "process_id": process.pid
                }
            else:
                return {
                    "success": False,
                    "worker_name": worker_name,
                    "worker_type": worker_type,
                    "message": f"Unknown local worker: {worker_name}. Only 'local_core' is supported.",
                    "process_id": None
                }
        
        elif worker_type == "cloudflare":
            # Start Cloudflare Worker via wrangler
            worker_path = QIOS_ROOT / "workers" / worker_name
            
            if not worker_path.exists():
                return {
                    "success": False,
                    "worker_name": worker_name,
                    "worker_type": worker_type,
                    "message": f"Worker directory not found: {worker_path}",
                    "process_id": None
                }
            
            # Check if wrangler.toml exists
            wrangler_toml = worker_path / "wrangler.toml"
            if not wrangler_toml.exists():
                return {
                    "success": False,
                    "worker_name": worker_name,
                    "worker_type": worker_type,
                    "message": f"wrangler.toml not found in {worker_path}",
                    "process_id": None
                }
            
            # Start wrangler dev
            if sys.platform == "win32":
                process = subprocess.Popen(
                    ["powershell", "-NoExit", "-Command", f"cd '{worker_path}'; npx wrangler dev"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                process = subprocess.Popen(
                    ["bash", "-c", f"cd '{worker_path}' && npx wrangler dev"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            return {
                "success": True,
                "worker_name": worker_name,
                "worker_type": worker_type,
                "message": f"Started Cloudflare worker: {worker_name}",
                "process_id": process.pid
            }
        
        else:
            return {
                "success": False,
                "worker_name": worker_name,
                "worker_type": worker_type,
                "message": f"Unknown worker_type: {worker_type}. Must be 'local' or 'cloudflare'.",
                "process_id": None
            }
    
    except Exception as e:
        return {
            "success": False,
            "worker_name": worker_name,
            "worker_type": worker_type,
            "message": f"Failed to start worker: {str(e)}",
            "process_id": None
        }

