"""
Gmail service endpoints router.

Provides Gmail operations endpoints:
- /messages: List messages
- /messages/{message_id}: Get message details
- /messages/{message_id}/attachments: Get message attachments
- /watch/setup: Setup Gmail watch
- /watch/status: Check watch status

Dependencies: GmailService for Gmail API operations
"""

import logging
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from src.backend.doc_processing_system.api.dependencies import (
    get_gmail_service
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail Service"])


class WatchRequest(BaseModel):
    """Gmail watch setup request."""
    topic_name: str = "projects/gmail-monitor-project-472511/topics/gmail-notifications"
    label_ids: List[str] = ["INBOX"]
    label_filter_behavior: str = "INCLUDE"


class MessageSummary(BaseModel):
    """Summary of a Gmail message."""
    id: str
    thread_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None
    date: Optional[str] = None


@router.get("/messages", response_model=List[MessageSummary])
async def list_messages(
    max_results: int = Query(10, ge=1, le=100),
    query: Optional[str] = Query(None, description="Gmail search query"),
    service=Depends(get_gmail_service)
):
    """List Gmail messages."""

    try:
        # Get messages list
        loop = asyncio.get_event_loop()

        # Build query parameters
        list_params = {
            'userId': 'me',
            'maxResults': max_results
        }
        if query:
            list_params['q'] = query

        # Get message list
        result = await loop.run_in_executor(
            None,
            lambda: service.service.users().messages().list(**list_params).execute()
        )

        messages = result.get('messages', [])
        summaries = []

        # Get message details for each message
        for msg in messages:
            try:
                message_detail = await service.get_message(msg['id'])
                headers = message_detail.get('payload', {}).get('headers', [])

                # Extract header information
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
                sender = next((h['value'] for h in headers if h['name'] == 'From'), None)
                date = next((h['value'] for h in headers if h['name'] == 'Date'), None)

                summaries.append(MessageSummary(
                    id=msg['id'],
                    thread_id=msg['threadId'],
                    subject=subject,
                    sender=sender,
                    snippet=message_detail.get('snippet'),
                    date=date
                ))
            except Exception as e:
                logger.warning(f"Failed to get details for message {msg['id']}: {e}")
                # Add basic info even if details fail
                summaries.append(MessageSummary(
                    id=msg['id'],
                    thread_id=msg['threadId']
                ))

        return summaries

    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list messages: {e}")


@router.get("/messages/{message_id}")
async def get_message(
    message_id: str,
    service=Depends(get_gmail_service)
):
    """Get full message details."""

    try:
        message = await service.get_message(message_id)
        body = await service.extract_message_body(message)

        return {
            "message": message,
            "body": body
        }
    except Exception as e:
        logger.error(f"Failed to get message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get message: {e}")


@router.get("/messages/{message_id}/attachments")
async def get_message_attachments(message_id: str):
    """Get message attachments."""
    service = get_gmail_service()
    if not service:
        raise HTTPException(status_code=503, detail="Gmail service not initialized. Use /auth/login first.")

    try:
        message = await service.get_message(message_id)
        attachments = await service.process_attachments(message_id, message)

        # Return attachment info without binary data
        attachment_info = []
        for att in attachments:
            attachment_info.append({
                "filename": att['filename'],
                "size": att['size'],
                "mime_type": att['mime_type']
            })

        return {
            "message_id": message_id,
            "attachment_count": len(attachments),
            "attachments": attachment_info
        }
    except Exception as e:
        logger.error(f"Failed to get attachments for message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get attachments: {e}")


@router.post("/watch/setup")
async def setup_watch(watch_request: WatchRequest):
    """Setup Gmail watch for push notifications."""
    service = get_gmail_service()
    if not service:
        raise HTTPException(status_code=503, detail="Gmail service not initialized. Use /auth/login first.")

    try:
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
    except Exception as e:
        logger.error(f"Failed to setup Gmail watch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to setup watch: {e}")


@router.get("/watch/status")
async def watch_status():
    """Check Gmail watch status."""
    service = get_gmail_service()
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


@router.get("/history/{start_history_id}")
async def get_history_changes(start_history_id: str):
    """Get Gmail history changes since the specified history ID."""
    service = get_gmail_service()
    if not service:
        raise HTTPException(status_code=503, detail="Gmail service not initialized. Use /auth/login first.")

    try:
        changes = await service.get_history_changes(start_history_id)
        return {
            "start_history_id": start_history_id,
            "changes": changes
        }
    except Exception as e:
        logger.error(f"Failed to get history changes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {e}")
