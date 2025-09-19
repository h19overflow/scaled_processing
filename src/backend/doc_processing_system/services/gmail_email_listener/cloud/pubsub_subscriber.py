"""
Pub/Sub subscriber for Gmail notifications.

Listens for Gmail push notifications and processes new emails.
Dependencies: GmailService for email processing.
"""

import json
import logging
from google.cloud import pubsub_v1
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)


class GmailPubSubSubscriber:
    """Subscribes to Gmail push notifications via Pub/Sub."""

    def __init__(self, project_id: str, subscription_name: str, gmail_service):
        self.project_id = project_id
        self.subscription_name = subscription_name
        self.gmail_service = gmail_service
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(project_id, subscription_name)

    def process_gmail_notification(self, message):
        """Process a Gmail push notification message."""
        try:
            # Decode the Pub/Sub message
            data = json.loads(message.data.decode('utf-8'))

            logger.info(f"Received Gmail notification: {data}")

            # Extract Gmail data
            email_address = data.get('emailAddress')
            history_id = data.get('historyId')

            if history_id:
                # Process the history changes
                asyncio.create_task(self._process_history_changes(history_id))

            # Acknowledge the message
            message.ack()

        except Exception as e:
            logger.error(f"Failed to process Gmail notification: {e}")
            message.nack()  # Negative acknowledgment - will retry

    async def _process_history_changes(self, history_id: str):
        """Process Gmail history changes."""
        try:
            # Get the history changes since last notification
            changes = await self.gmail_service.get_history_changes(history_id)

            # Process new messages
            history = changes.get('history', [])
            for change in history:
                messages_added = change.get('messagesAdded', [])
                for message_info in messages_added:
                    message_id = message_info['message']['id']
                    await self._process_new_message(message_id)

        except Exception as e:
            logger.error(f"Failed to process history changes: {e}")

    async def _process_new_message(self, message_id: str):
        """Process a single new message."""
        try:
            # Get the full message
            message = await self.gmail_service.get_message(message_id)

            # Extract information
            headers = message.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')

            logger.info(f"Processing new email: {subject} from {sender}")

            # Process attachments if any
            attachments = await self.gmail_service.process_attachments(message_id, message)

            if attachments:
                logger.info(f"Found {len(attachments)} attachments")
                # Save attachments
                for attachment in attachments:
                    await self.gmail_service.save_attachment(attachment)

            # Here you can add your custom email processing logic
            # For example: send to document processing pipeline

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")

    def start_listening(self):
        """Start listening for Gmail notifications."""
        logger.info(f"Starting to listen on subscription: {self.subscription_path}")

        # Configure subscriber settings
        flow_control = pubsub_v1.types.FlowControl(max_messages=100)

        # Start pulling messages
        streaming_pull_future = self.subscriber.pull(
            request={"subscription": self.subscription_path, "max_messages": 10},
            callback=self.process_gmail_notification,
            flow_control=flow_control,
        )

        logger.info("Listening for Gmail notifications...")

        try:
            # Keep the subscriber running
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            logger.info("Gmail notification listener stopped")


# HELPER FUNCTIONS

async def setup_pubsub_subscriber(gmail_service):
    """Setup and start the Pub/Sub subscriber for Gmail notifications."""
    project_id = "gmail-monitor-project-472511"
    subscription_name = "gmail-notifications-subscription"

    subscriber = GmailPubSubSubscriber(project_id, subscription_name, gmail_service)

    # Start listening in background
    import threading
    def run_subscriber():
        subscriber.start_listening()

    thread = threading.Thread(target=run_subscriber, daemon=True)
    thread.start()

    logger.info("Gmail Pub/Sub subscriber started in background")
    return subscriber