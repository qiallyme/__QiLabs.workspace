"""
Email get recent tool - fetches recent emails from inbox.
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.email.client import EmailClient
from integrations.base import IntegrationError


async def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Get recent emails from inbox.
    
    Args:
        args: {
            "limit": int - Maximum number of emails (default: 20)
        }
        env: Environment context
    
    Returns:
        {
            "emails": [
                {
                    "id": str,
                    "from": str,
                    "subject": str,
                    "date": str (ISO 8601),
                    "snippet": str
                }
            ],
            "error": str (if failed)
        }
    """
    limit = args.get("limit", 20)
    
    try:
        client = EmailClient()
        emails = client.get_recent_emails(limit=limit)
        
        return {
            "emails": emails
        }
    
    except IntegrationError as e:
        return {
            "emails": [],
            "error": str(e)
        }
    except Exception as e:
        return {
            "emails": [],
            "error": f"Unexpected error: {str(e)}"
        }

