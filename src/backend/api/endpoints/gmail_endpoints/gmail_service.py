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

from src.backend.api.dependencies import (
    get_gmail_service
)
from src.backend.doc_processing_system.services.gmail_email_listener.utils import (
    MessageSummary,
    WatchRequest,
    list_messages,
    get_message_details,
    get_message_attachments_info,
    get_history_changes,
    get_watch_status
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail Service"])


@router.get("/messages", response_model=List[MessageSummary])
async def list_messages_endpoint(
    max_results: int = Query(10, ge=1, le=200),
    query: Optional[str] = Query(None, description="Gmail search query"),
    service=Depends(get_gmail_service)
):
    """List Gmail messages."""
    try:

        return await list_messages(service, max_results, query)
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list messages: {e}")


@router.get("/messages/{message_id}")
async def get_message_endpoint(
    message_id: str,
    service=Depends(get_gmail_service)
):
    """Get full message details."""
    try:
        return await get_message_details(service, message_id)
    except Exception as e:
        logger.error(f"Failed to get message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get message: {e}")


@router.get("/messages/{message_id}/attachments")
async def get_message_attachments_endpoint(
    message_id: str,
    service=Depends(get_gmail_service)
):
    """Get message attachments."""
    if not service:
        raise HTTPException(status_code=503, detail="Gmail service not initialized. Use /auth/login first.")

    try:
        return await get_message_attachments_info(service, message_id)
    except Exception as e:
        logger.error(f"Failed to get attachments for message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get attachments: {e}")


@router.post("/watch/setup")
async def setup_watch_endpoint(
    watch_request: WatchRequest = WatchRequest(),
    service=Depends(get_gmail_service)
):
    """Setup Gmail watch for push notifications."""
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
async def watch_status_endpoint(service=Depends(get_gmail_service)):
    """Check Gmail watch status."""
    return get_watch_status(service)


@router.get("/history/{start_history_id}")
async def get_history_changes_endpoint(
    start_history_id: str,
    service=Depends(get_gmail_service)
):
    """Get Gmail history changes since the specified history ID."""
    if not service:
        raise HTTPException(status_code=503, detail="Gmail service not initialized. Use /auth/login first.")

    try:
        return await get_history_changes(service, start_history_id)
    except Exception as e:
        logger.error(f"Failed to get history changes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {e}")
