"""
gmail_service.py

Encapsulates authenticated Gmail API access and business logic helpers.

- Initializes Gmail API client using GmailAuthManager credentials.
- Handles mailbox watching, message/attachment fetching, body extraction, and attachment saving.
- Used by: FastAPI app for all Gmail event processing and automation.

Main roles:
- Set up Gmail "watch" (Pub/Sub push notifications)
- Fetch mailbox/history changes and messages
- Extract body/attachments; process, download, save for downstream automation
"""

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class GmailService:
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Build an authenticated Gmail API client."""
        try:
            credentials = self.auth_manager.get_credentials()
            self.service = build('gmail', 'v1', credentials=credentials)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise

    def setup_watch(self, watch_request: dict) -> dict:
        """Register/watch mailbox for push notifications (Pub/Sub)."""
        try:
            result = self.service.users().watch(
                userId='me',
                body=watch_request
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Gmail watch setup failed: {e}")
            raise

    async def get_history_changes(self, start_history_id: str) -> dict:
        """Fetch email history-changes (since last notification)."""
        try:
            result = self.service.users().history().list(
                userId='me',
                startHistoryId=start_history_id
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Failed to get history changes: {e}")
            return {}

    async def get_message(self, message_id: str) -> dict:
        """Fetch full message content by ID."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return message
        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    async def extract_message_body(self, message: dict) -> str:
        """Extract plain text body from message object."""
        try:
            payload = message.get('payload', {})
            body = ""
            if 'parts' in payload:
                # Multipart: look for plain text parts
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part['mimeType'] == 'text/html':
                        pass  # Extend for HTML if needed
            else:
                # Single part: extract if text
                if payload['mimeType'] == 'text/plain':
                    data = payload['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            return body
        except Exception as e:
            logger.error(f"Failed to extract message body: {e}")
            return ""

    async def process_attachments(self, message_id: str, message: dict) -> List[Dict]:
        """Download/process all attachments in a message."""
        attachments = []
        try:
            payload = message.get('payload', {})
            parts = payload.get('parts', [])
            if not parts:
                # May be single-part attachment
                if payload.get('filename'):
                    parts = [payload]
            for part in parts:
                filename = part.get('filename', '')
                if filename:
                    # Attachment present
                    attachment_id = part['body'].get('attachmentId')
                    if attachment_id:
                        attachment_data = await self._download_attachment(
                            message_id, attachment_id
                        )
                        if attachment_data:
                            attachments.append({
                                'filename': filename,
                                'data': attachment_data,
                                'size': len(attachment_data),
                                'mime_type': part.get('mimeType', 'application/octet-stream')
                            })
            logger.info(f"Processed {len(attachments)} attachments for message {message_id}")
            return attachments
        except Exception as e:
            logger.error(f"Failed to process attachments for message {message_id}: {e}")
            return []

    async def _download_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Download attachment by Gmail IDs."""
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            data = attachment.get('data', '')
            if data:
                return base64.urlsafe_b64decode(data)
        except HttpError as e:
            logger.error(f"Failed to download attachment {attachment_id}: {e}")
        return None

    async def save_attachment(self, attachment: Dict, save_directory: str = "./attachments"):
        """Save attachment data to disk for downstream processing."""
        try:
            os.makedirs(save_directory, exist_ok=True)
            file_path = os.path.join(save_directory, attachment['filename'])
            with open(file_path, 'wb') as f:
                f.write(attachment['data'])
            logger.info(f"Attachment saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save attachment {attachment['filename']}: {e}")
            return None
