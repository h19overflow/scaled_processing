from google.cloud import pubsub_v1
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

#TODO test out the subscriber Created subscription [projects/gmail-monitor-project-472511/subscriptions/gmail-notifications-processor-sub].
# (scaled_processing) PS C:\Users\User\Projects\scaled_processing> python -m src.backend.doc_processing_system.services.gmail_email_listener.cloud.pubsub_subscriber
# 🚀 Testing Gmail PubSub Subscriber
# ========================================
# 🔧 Initializing Gmail service...
# ✅ Gmail service initialized
# 🔧 Creating PubSub subscriber...
# ✅ Subscriber created for: projects/gmail-monitor-project-472511/subscriptions/gmail-notifications-processor-sub
# 🔧 Testing Pub/Sub connection...
# ✅ Successfully connected to Pub/Sub subscription
#
# 🎧 Starting to listen for Gmail notifications...
# 📧 Send yourself an email to test!
# ⏹️  Press Ctrl+C to stop,
#Failed to get history changes: <HttpError 404 when requesting https://gmail.googleapis.com/gmail/v1/users/me/history?startHistoryId=2106520&alt=json returned "Requested entity was not found.". Details: "[{'message': 'Requested entity was not found.', 'domain': 'global', 'reason': 'notFound'}]">
# TODO Not working properly.
class GmailPubSubSubscriber:
    def __init__(self, project_id: str, subscription_name: str, gmail_service):
        self.gmail_service = gmail_service
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(project_id, subscription_name)
        # Recommended flow control
        self.flow_control = pubsub_v1.types.FlowControl(
            max_messages=100,
            max_bytes=10 * 1024 * 1024,
        )

    def process_gmail_notification(self, message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            data = json.loads(message.data.decode("utf-8"))
            logger.info(f"Received Gmail notification: {data}")

            # Check message age (Pub/Sub adds publish_time)
            import time
            message_age = time.time() - message.publish_time.timestamp()
            if message_age > 3600:  # Ignore messages older than 1 hour
                logger.warning(f"Ignoring old notification (age: {message_age:.0f}s)")
                message.ack()
                return

            history_id = data.get("historyId")
            if history_id:
                # Wait synchronously for processing to complete before ack
                asyncio.run(self._process_history_changes(history_id))

            # Acknowledge only after processing succeeds
            message.ack()

        except Exception as e:
            logger.error(f"Failed to process Gmail notification: {e}")
            message.nack()

    async def _process_history_changes(self, history_id: str) -> None:
        try:
            changes = await self.gmail_service.get_history_changes(history_id)
            for change in changes.get("history", []):
                for msg in change.get("messagesAdded", []):
                    await self._process_new_message(msg["message"]["id"])
        except Exception as e:
            if "404" in str(e) or "notFound" in str(e):
                logger.warning(f"History ID {history_id} not found (likely too old). Checking recent messages instead.")
                # Fallback: get recent messages instead
                await self._process_recent_messages()
            else:
                logger.error(f"Unexpected error processing history: {e}")
                raise

    async def _process_recent_messages(self) -> None:
        """Fallback: process recent messages when history ID is invalid"""
        try:
            # Get recent messages from INBOX
            result = self.gmail_service.service.users().messages().list(
                userId='me',
                maxResults=5,
                q='in:inbox'
            ).execute()

            messages = result.get('messages', [])
            logger.info(f"Processing {len(messages)} recent messages as fallback")

            for msg in messages:
                await self._process_new_message(msg['id'])

        except Exception as e:
            logger.error(f"Failed to process recent messages: {e}")

    async def _process_new_message(self, message_id: str) -> None:
        msg = await self.gmail_service.get_message(message_id)
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
        logger.info(f"Processing new email: {subject} from {sender}")

        attachments = await self.gmail_service.process_attachments(message_id, msg)
        for attachment in attachments or []:
            await self.gmail_service.save_attachment(attachment)

    def start_listening(self) -> None:
        logger.info(f"Listening on {self.subscription_path}")
        # Use subscribe() instead of pull()
        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path,
            callback=self.process_gmail_notification,
            flow_control=self.flow_control,
        )
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            logger.info("Subscriber stopped")

async def setup_pubsub_subscriber(gmail_service):
    project_id = "gmail-monitor-project-472511"
    subscription_name = "gmail-notifications-processor-sub"  # Updated to match your actual subscription
    subscriber = GmailPubSubSubscriber(project_id, subscription_name, gmail_service)
    # Simply call start_listening in the current thread (it blocks)
    subscriber.start_listening()
    return subscriber


# HELPER FUNCTIONS

def test_subscriber():
    """Test the PubSub subscriber with actual Gmail service"""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Import your Gmail services
    from .gmail_auth_manager import GmailAuthManager
    from .gmail_service import GmailService

    try:
        # Setup Gmail service (same as your main app)
        client_secrets_path = os.getenv("GMAIL_CLIENT_SECRETS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")

        if not client_secrets_path or not token_path:
            raise ValueError("GMAIL_CLIENT_SECRETS_PATH and GMAIL_TOKEN_PATH must be set in .env")

        if not os.path.exists(token_path):
            raise ValueError(f"Token file not found: {token_path}. Run OAuth flow first via /auth/login")

        print("🔧 Initializing Gmail service...")
        auth_manager = GmailAuthManager(client_secrets_path, token_path)
        gmail_service = GmailService(auth_manager)
        print("✅ Gmail service initialized")

        # Create and test subscriber
        print("🔧 Creating PubSub subscriber...")
        project_id = "gmail-monitor-project-472511"
        subscription_name = "gmail-notifications-processor-sub"
        subscriber = GmailPubSubSubscriber(project_id, subscription_name, gmail_service)
        print(f"✅ Subscriber created for: {subscriber.subscription_path}")

        # Test connection
        print("🔧 Testing Pub/Sub connection...")
        try:
            # Just check if we can connect to the subscription
            subscriber.subscriber.get_subscription(request={"subscription": subscriber.subscription_path})
            print("✅ Successfully connected to Pub/Sub subscription")
        except Exception as e:
            print(f"❌ Failed to connect to subscription: {e}")
            return

        print("\n🎧 Starting to listen for Gmail notifications...")
        print("📧 Send yourself an email to test!")
        print("⏹️  Press Ctrl+C to stop\n")

        # Start listening (this will block until Ctrl+C)
        subscriber.start_listening()

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you:")
        print("   1. Have run the OAuth flow (/auth/login)")
        print("   2. Have set up the Pub/Sub subscription")
        print("   3. Have valid environment variables")


if __name__ == "__main__":
    print("🚀 Testing Gmail PubSub Subscriber")
    print("=" * 40)
    test_subscriber()
