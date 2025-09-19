"""
Utilities for Gmail email listener service.

Exports message and watch operations for Gmail service endpoints.
"""

from .message_operations import (
    MessageSummary,
    list_messages,
    get_message_details,
    get_message_attachments_info,
    get_history_changes
)

from .watch_operations import (
    WatchRequest,
    setup_gmail_watch,
    get_watch_status
)

__all__ = [
    "MessageSummary",
    "list_messages",
    "get_message_details",
    "get_message_attachments_info",
    "get_history_changes",
    "WatchRequest",
    "setup_gmail_watch",
    "get_watch_status"
]