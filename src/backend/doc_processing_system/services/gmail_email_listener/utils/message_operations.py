"""
Message operations utilities for Gmail service endpoints.

Handles message listing, details retrieval, and attachment processing.
Dependencies: GmailService for Gmail API operations.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MessageSummary(BaseModel):
    """Summary of a Gmail message."""
    id: str
    thread_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None
    date: Optional[str] = None


async def list_messages(service, max_results: int, query: Optional[str] = None) -> List[MessageSummary]:
    """List Gmail messages with pagination and search support."""
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


async def get_message_details(service, message_id: str) -> Dict[str, Any]:
    """Get full message details including body."""
    message = await service.get_message(message_id)
    body = await service.extract_message_body(message)

    return {
        "message": message,
        "body": body
    }


async def get_message_attachments_info(service, message_id: str) -> Dict[str, Any]:
    """Get message attachments information."""
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


async def get_history_changes(service, start_history_id: str) -> Dict[str, Any]:
    """Get Gmail history changes since the specified history ID."""
    changes = await service.get_history_changes(start_history_id)
    return {
        "start_history_id": start_history_id,
        "changes": changes
    }