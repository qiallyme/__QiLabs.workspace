"""
Calendar get upcoming events tool - fetches upcoming calendar events.
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
    Get upcoming calendar events.
    
    Args:
        args: {
            "hours_ahead": int - How many hours ahead to look (default: 24)
        }
        env: Environment context
    
    Returns:
        {
            "events": [
                {
                    "id": str,
                    "title": str,
                    "start": str,
                    "end": str,
                    "location": str,
                    "attendees": [str]
                }
            ],
            "error": str (if failed)
        }
    """
    hours_ahead = args.get("hours_ahead", 24)
    
    try:
        client = CalendarClient()
        events = client.get_upcoming_events(hours_ahead=hours_ahead)
        
        return {
            "events": events
        }
    
    except IntegrationError as e:
        return {
            "events": [],
            "error": str(e)
        }
    except Exception as e:
        return {
            "events": [],
            "error": f"Unexpected error: {str(e)}"
        }

