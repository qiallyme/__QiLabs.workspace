"""
Email send tool - sends an email via SMTP.
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
    Send an email.
    
    Args:
        args: {
            "to": str - Recipient email address (required)
            "subject": str - Email subject (required)
            "body": str - Email body (required)
        }
        env: Environment context
    
    Returns:
        {
            "success": bool,
            "to": str,
            "subject": str,
            "message": str,
            "error": str (if failed)
        }
    """
    to = args.get("to")
    subject = args.get("subject")
    body = args.get("body")
    
    if not all([to, subject, body]):
        return {
            "success": False,
            "to": to,
            "subject": subject,
            "message": None,
            "error": "to, subject, and body are required"
        }
    
    try:
        client = EmailClient()
        result = client.send_email(to=to, subject=subject, body=body)
        
        return result
    
    except IntegrationError as e:
        return {
            "success": False,
            "to": to,
            "subject": subject,
            "message": None,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "to": to,
            "subject": subject,
            "message": None,
            "error": f"Unexpected error: {str(e)}"
        }

