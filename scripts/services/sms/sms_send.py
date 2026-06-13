"""
SMS send tool - sends an SMS via Twilio.
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.twilio.client import TwilioClientWrapper
from integrations.base import IntegrationError


async def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Send an SMS message.
    
    Args:
        args: {
            "to": str - Recipient phone number in E.164 format (e.g., +1234567890) (required)
            "body": str - Message body (required)
        }
        env: Environment context
    
    Returns:
        {
            "success": bool,
            "sid": str - Twilio message SID,
            "status": str,
            "to": str,
            "from": str,
            "error": str (if failed)
        }
    """
    to = args.get("to")
    body = args.get("body")
    
    if not all([to, body]):
        return {
            "success": False,
            "sid": None,
            "status": None,
            "to": to,
            "from": None,
            "error": "to and body are required"
        }
    
    try:
        client = TwilioClientWrapper()
        result = client.send_sms(to=to, body=body)
        
        return {
            "success": True,
            **result
        }
    
    except IntegrationError as e:
        return {
            "success": False,
            "sid": None,
            "status": None,
            "to": to,
            "from": None,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "sid": None,
            "status": None,
            "to": to,
            "from": None,
            "error": f"Unexpected error: {str(e)}"
        }

