import json
from datetime import datetime
from typing import Dict, Any

def create_message(event_type: str, data: Dict[str, Any], source: str = None) -> str:
    """Create standardized message format."""
    return json.dumps({
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
        "source": source
    })

def parse_message(message: str) -> Dict[str, Any]:
    """Parse message back to dict."""
    try:
        return json.loads(message)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "raw_message": message}