# gmail_service.py
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
        """Initialize Gmail service with authentication"""
        try:
            credentials = self.auth_manager.get_credentials()
            self.service = build('gmail', 'v1', credentials=credentials)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise

    def setup_watch(self, watch_request: dict) -> dict:
        """Setup Gmail push notifications"""
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
        """Get history changes from Gmail"""
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
        """Get full message content"""
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
        """Extract text content from email message"""
        try:
            payload = message.get('payload', {})
            body = ""

            if 'parts' in payload:
                # Multipart message
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part['mimeType'] == 'text/html':
                        # Handle HTML content if needed
                        pass
            else:
                # Single part message
                if payload['mimeType'] == 'text/plain':
                    data = payload['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')

            return body
        except Exception as e:
            logger.error(f"Failed to extract message body: {e}")
            return ""

    async def process_attachments(self, message_id: str, message: dict) -> List[Dict]:
        """Download and process email attachments"""
        attachments = []

        try:
            payload = message.get('payload', {})
            parts = payload.get('parts', [])

            if not parts:
                # Check if the payload itself is an attachment
                if payload.get('filename'):
                    parts = [payload]

            for part in parts:
                filename = part.get('filename', '')

                if filename:  # This part has an attachment
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
        """Download attachment data"""
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
        """Save attachment to disk"""
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
