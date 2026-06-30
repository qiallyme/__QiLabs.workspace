"""
Run a qios_agent command.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

QIOS_ROOT = Path(__file__).parent.parent.parent.parent


def find_agent_binary() -> Path | None:
    """Find the qios_agent binary or script."""
    # Check common locations
    candidates = [
        QIOS_ROOT / "tools" / "qios_agent",
        QIOS_ROOT / "tools" / "qios_agent.py",
        QIOS_ROOT / "qios_agent",
        QIOS_ROOT / "qios_agent.py",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    # Check PATH
    import shutil
    agent_path = shutil.which("qios_agent")
    if agent_path:
        return Path(agent_path)
    
    return None


def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Run a qios_agent command.
    
    Args:
        args: {
            "command": str - Subcommand name
            "args": list[str] - Additional arguments
        }
        env: Environment context
    
    Returns:
        {
            "command": str,
            "args": list,
            "exit_code": int,
            "stdout": str,
            "stderr": str
        }
    """
    command = args.get("command", "")
    cmd_args = args.get("args", [])
    
    if not command:
        raise ValueError("Command is required")
    
    # Find agent binary
    agent_path = find_agent_binary()
    if not agent_path:
        return {
            "command": command,
            "args": cmd_args,
            "exit_code": -1,
            "stdout": "",
            "stderr": "qios_agent not found. Please ensure it's installed and in PATH."
        }
    
    # Build command
    full_cmd = [str(agent_path), command] + cmd_args
    
    try:
        # Run with timeout
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=30.0,
            cwd=str(QIOS_ROOT)
        )
        
        return {
            "command": command,
            "args": cmd_args,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "args": cmd_args,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "command": command,
            "args": cmd_args,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Failed to run command: {str(e)}"
        }

