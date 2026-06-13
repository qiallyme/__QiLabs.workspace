"""
Calendar create event tool - creates a calendar event.
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.calendar.client import CalendarClient
from integrations.base import IntegrationError


async def run(args: Dict[str, Any], env: Dict) -> Dict[str, Any]:
    """
    Create a calendar event.
    
    Args:
        args: {
            "title": str - Event title (required)
            "start": str - ISO 8601 start time (required)
            "end": str - ISO 8601 end time (required)
            "location": str - Optional location
            "description": str - Optional description
            "attendees": [str] - Optional list of email addresses
        }
        env: Environment context
    
    Returns:
        {
            "success": bool,
            "event": {
                "id": str,
                "title": str,
                "start": str,
                "end": str
            },
            "error": str (if failed)
        }
    """
    title = args.get("title")
    start = args.get("start")
    end = args.get("end")
    location = args.get("location")
    description = args.get("description")
    attendees = args.get("attendees", [])
    
    if not all([title, start, end]):
        return {
            "success": False,
            "event": None,
            "error": "title, start, and end are required"
        }
    
    try:
        client = CalendarClient()
        event = client.create_event(
            title=title,
            start=start,
            end=end,
            location=location,
            description=description,
            attendees=attendees
        )
        
        return {
            "success": True,
            "event": event
        }
    
    except IntegrationError as e:
        return {
            "success": False,
            "event": None,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "event": None,
            "error": f"Unexpected error: {str(e)}"
        }

