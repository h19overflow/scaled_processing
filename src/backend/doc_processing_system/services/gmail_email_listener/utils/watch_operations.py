"""
Watch operations utilities for Gmail service endpoints.

Handles Gmail watch setup and status monitoring.
Dependencies: GmailService for Gmail API operations.

The WatchRequest object contains the following key fields :

topicName (required): A fully qualified Google Cloud Pub/Sub topic name where Gmail will publish notifications. Format: "projects/your-project-id/topics/your-topic-name"

labelIds (optional): Array of Gmail label IDs to filter which changes trigger notifications. If empty, all changes are monitored

labelFilterAction or labelFilterBehavior (optional): Determines filtering behavior - typically "INCLUDE" or "EXCLUDE"

Example POST Request Body
Here's what you should send to your endpoint :

json
{
  "topicName": "projects/myproject/topics/mytopic",
  "labelIds": ["INBOX"],
  "labelFilterBehavior": "INCLUDE"
}
"""

import logging
import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WatchRequest(BaseModel):
    """Gmail watch setup request."""
    topic_name: str = "projects/gmail-monitor-project-472511/topics/gmail-notifications"
    label_ids: List[str] = ["INBOX"]
    label_filter_behavior: str = "INCLUDE"


async def setup_gmail_watch(service, watch_request: WatchRequest) -> Dict[str, Any]:
    """Setup Gmail watch for push notifications."""
    request_dict = {
        'labelIds': watch_request.label_ids,
        'topicName': watch_request.topic_name,
        'labelFilterBehavior': watch_request.label_filter_behavior
    }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, service.setup_watch, request_dict)

    return {
        "message": "Gmail watch setup successful",
        "result": result
    }


def get_watch_status(service) -> Dict[str, Any]:
    """Check Gmail watch status."""
    if not service:
        return {
            "watch_active": False,
            "message": "Gmail service not initialized"
        }

    # For now, return basic status
    # In production, you might want to track watch expiration
    return {
        "watch_active": True,
        "message": "Gmail service is active",
        "service_initialized": True
    }