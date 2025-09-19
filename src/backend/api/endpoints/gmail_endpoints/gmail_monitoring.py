"""
Gmail monitoring endpoints for checking new messages.

Provides endpoints to manually check for new emails without Pub/Sub.
Dependencies: GmailService for Gmail API operations.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from src.backend.api.dependencies import get_gmail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail/monitor", tags=["Gmail Monitoring"])


@router.get("/check-new")
async def check_new_messages(
    since_history_id: Optional[str] = Query(None, description="Check changes since this history ID"),
    service=Depends(get_gmail_service)
):
    """Manually check for new messages since last history ID."""
    try:
        if since_history_id:
            # Check specific history changes
            changes = await service.get_history_changes(since_history_id)
            return {
                "status": "success",
                "since_history_id": since_history_id,
                "changes": changes
            }
        else:
            # Get recent messages (last 10)
            recent_messages = []
            result = service.service.users().messages().list(
                userId='me',
                maxResults=10,
                q='in:inbox'
            ).execute()

            messages = result.get('messages', [])
            for msg in messages[:5]:  # Just first 5 for quick check
                try:
                    message_detail = await service.get_message(msg['id'])
                    headers = message_detail.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), None)
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), None)

                    recent_messages.append({
                        "id": msg['id'],
                        "subject": subject,
                        "sender": sender,
                        "date": date,
                        "snippet": message_detail.get('snippet')
                    })
                except Exception as e:
                    logger.warning(f"Failed to get details for message {msg['id']}: {e}")

            return {
                "status": "success",
                "recent_messages": recent_messages,
                "total_found": len(messages)
            }

    except Exception as e:
        logger.error(f"Failed to check new messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check messages: {e}")


@router.get("/watch-status")
async def get_detailed_watch_status(service=Depends(get_gmail_service)):
    """Get detailed Gmail watch status information."""
    try:
        # This would require storing watch info when it's set up
        # For now, return basic status
        return {
            "watch_active": True,
            "message": "Gmail watch is configured",
            "topic_name": "projects/gmail-monitor-project-472511/topics/gmail-notifications",
            "note": "Use Pub/Sub subscriber to receive real-time notifications"
        }
    except Exception as e:
        logger.error(f"Failed to get watch status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.post("/test-notification")
async def test_notification_processing(service=Depends(get_gmail_service)):
    """Test notification processing by simulating a Gmail notification."""
    try:
        # Get the latest message to simulate processing
        result = service.service.users().messages().list(
            userId='me',
            maxResults=1
        ).execute()

        messages = result.get('messages', [])
        if not messages:
            return {"message": "No messages found to test with"}

        message_id = messages[0]['id']

        # Process like we would from a notification
        message = await service.get_message(message_id)
        attachments = await service.process_attachments(message_id, message)

        headers = message.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')

        return {
            "message": "Test notification processed successfully",
            "processed_message": {
                "id": message_id,
                "subject": subject,
                "attachment_count": len(attachments)
            }
        }

    except Exception as e:
        logger.error(f"Failed to test notification: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {e}")