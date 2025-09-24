from google.cloud import pubsub_v1
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

#TODO test out the subscriber Created subscription [projects/gmail-monitor-project-472511/subscriptions/gmail-notifications-processor-sub].
# (scaled_processing) PS C:\Users\User\Projects\scaled_processing> python -m src.backend.doc_processing_system.utils.gmail_email_listener.cloud.pubsub_subscriber
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
            # Get raw message data for debugging
            raw_data = message.data.decode("utf-8")
            logger.info(f"Received raw PubSub message: '{raw_data}' (length: {len(raw_data)})")

            # Validate message data
            if not raw_data or raw_data.strip() == "":
                logger.warning("Received empty PubSub message, acknowledging and skipping")
                message.ack()
                return

            # Try to parse JSON
            try:
                data = json.loads(raw_data)
                logger.info(f"Parsed Gmail notification data: {data}")
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse JSON from message: {json_err}")
                logger.error(f"Raw message content: '{raw_data}'")
                # Acknowledge malformed messages to avoid reprocessing
                message.ack()
                return

            # Check message age (Pub/Sub adds publish_time)
            import time
            message_age = time.time() - message.publish_time.timestamp()
            if message_age > 300:  # Ignore messages older than 5 minutes
                logger.warning(f"Ignoring old notification (age: {message_age:.0f}s)")
                message.ack()
                return

            # Extract history ID from Gmail notification
            history_id = data.get("historyId")
            if not history_id:
                logger.warning(f"No historyId found in notification: {data}")
                message.ack()
                return

            logger.info(f"Processing Gmail history changes for historyId: {history_id}")

            # Wait synchronously for processing to complete before ack
            asyncio.run(self._process_history_changes(history_id))

            # Acknowledge only after processing succeeds
            message.ack()
            logger.info("Successfully processed Gmail notification")

        except Exception as e:
            logger.error(f"Failed to process Gmail notification: {e}")
            logger.error(f"Message attributes: {message.attributes}")
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
        logger.info("Press Ctrl+C to stop listening...")

        # Use subscribe() instead of pull()
        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path,
            callback=self.process_gmail_notification,
            flow_control=self.flow_control,
        )

        try:
            # Block forever until interrupted
            streaming_pull_future.result()
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received...")
            print("🔄 Gracefully shutting down subscriber...")
            streaming_pull_future.cancel()
            streaming_pull_future.result()  # Wait for cancellation to complete
            logger.info("✅ Subscriber stopped gracefully")
        except Exception as e:
            logger.error(f"❌ Unexpected error in subscriber: {e}")
            streaming_pull_future.cancel()
            raise

async def setup_pubsub_subscriber(gmail_service):
    project_id = "gmail-monitor-project-472511"
    subscription_name = "gmail-notifications-processor-sub"  # Updated to match your actual subscription
    subscriber = GmailPubSubSubscriber(project_id, subscription_name, gmail_service)
    # Simply call start_listening in the current thread (it blocks)
    subscriber.start_listening()
    return subscriber


# HELPER FUNCTIONS

def check_pubsub_setup():
    """Check PubSub topic and subscription setup"""
    try:
        from google.cloud import pubsub_v1

        project_id = "gmail-monitor-project-472511"
        topic_name = "gmail-notifications"
        subscription_name = "gmail-notifications-processor-sub"

        # Initialize clients
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()

        topic_path = publisher.topic_path(project_id, topic_name)
        subscription_path = subscriber.subscription_path(project_id, subscription_name)

        print(f"🔍 Checking PubSub setup for project: {project_id}")
        print(f"📰 Topic: {topic_path}")
        print(f"📨 Subscription: {subscription_path}")

        # Check topic exists
        try:
            topic = publisher.get_topic(request={"topic": topic_path})
            print(f"✅ Topic exists: {topic.name}")
        except Exception as e:
            print(f"❌ Topic not found: {e}")
            return False

        # Check subscription exists
        try:
            subscription = subscriber.get_subscription(request={"subscription": subscription_path})
            print(f"✅ Subscription exists: {subscription.name}")
            print(f"📎 Connected to topic: {subscription.topic}")
        except Exception as e:
            print(f"❌ Subscription not found: {e}")
            return False

        # Test pulling messages (non-blocking)
        print("\n🎧 Testing message pull (non-blocking)...")
        try:
            response = subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": 1,
                    "return_immediately": True,
                }
            )
            if response.received_messages:
                print(f"📧 Found {len(response.received_messages)} pending messages")
                for msg in response.received_messages:
                    raw_data = msg.message.data.decode("utf-8", errors="replace")
                    print(f"📄 Message data: '{raw_data}' (length: {len(raw_data)})")
                    # Don't acknowledge, just check
            else:
                print("📭 No pending messages in subscription")
        except Exception as e:
            print(f"❌ Failed to test message pull: {e}")

        return True

    except Exception as e:
        print(f"❌ PubSub setup check failed: {e}")
        return False

def check_gmail_watch_status(gmail_service):
    """Check if Gmail watch is properly set up"""
    try:
        print("🔍 Checking Gmail watch configuration...")

        # Check if we can access Gmail API
        profile = gmail_service.service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')
        print(f"✅ Gmail API access confirmed for: {email}")

        # Check recent message to see if we have the right permissions
        try:
            messages = gmail_service.service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()

            if messages.get('messages'):
                print("✅ Can read Gmail messages")
                current_history_id = profile.get('historyId', 'Unknown')
                print(f"📍 Current history ID: {current_history_id}")
            else:
                print("⚠️  No messages found in mailbox")
        except Exception as msg_err:
            print(f"⚠️  Could not list messages: {msg_err}")
            print("📍 Using profile history ID instead")

        # Try to set up Gmail watch manually with inclusive configuration
        print("\n🔧 Setting up Gmail watch...")
        watch_request = {
            'topicName': 'projects/gmail-monitor-project-472511/topics/gmail-notifications',
            'labelFilterBehavior': 'EXCLUDE',  # Exclude no labels = watch everything
            'labelIds': []  # Empty list with EXCLUDE = watch all activity
        }

        try:
            result = gmail_service.setup_watch(watch_request)
            expiration = result.get('expiration', 'Unknown')
            print(f"✅ Gmail watch setup successful!")
            print(f"📧 Watching email: {email}")
            print(f"📅 Expires: {expiration}")
            print(f"🎯 Topic: projects/gmail-monitor-project-472511/topics/gmail-notifications")
            return True
        except Exception as watch_error:
            print(f"❌ Failed to setup Gmail watch: {watch_error}")
            return False

    except Exception as e:
        print(f"❌ Gmail API error: {e}")
        return False

def test_subscriber():
    """Test the PubSub subscriber with actual Gmail service"""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Import your Gmail utils
    from .gmail_auth_manager import GmailAuthManager
    from .gmail_service import GmailService

    try:
        # First check PubSub setup
        print("🔍 Step 1: Checking PubSub setup...")
        if not check_pubsub_setup():
            print("❌ PubSub setup failed. Fix the topic/subscription first.")
            return

        # Setup Gmail service (same as your main app)
        client_secrets_path = os.getenv("GMAIL_CLIENT_SECRETS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")

        if not client_secrets_path or not token_path:
            raise ValueError("GMAIL_CLIENT_SECRETS_PATH and GMAIL_TOKEN_PATH must be set in .env")

        if not os.path.exists(token_path):
            raise ValueError(f"Token file not found: {token_path}. Run OAuth flow first via /auth/login")

        print("\n🔧 Step 2: Initializing Gmail service...")
        auth_manager = GmailAuthManager(client_secrets_path, token_path)
        gmail_service = GmailService(auth_manager)
        print("✅ Gmail service initialized")

        # Check Gmail watch status
        print("\n🔍 Step 3: Checking Gmail watch status...")
        check_gmail_watch_status(gmail_service)

        # Create and test subscriber
        print("\n🔧 Step 4: Creating PubSub subscriber...")
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

        print("\n🎧 Step 5: Starting to listen for Gmail notifications...")
        print("📧 Send yourself an email to test!")
        print("⏹️  Press Ctrl+C to stop\n")

        # Start listening (this will block until Ctrl+C)
        try:
            subscriber.start_listening()
        except KeyboardInterrupt:
            print("\n👋 Test stopped by user")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
        finally:
            print("🏁 Test completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you:")
        print("   1. Have run the OAuth flow (/auth/login)")
        print("   2. Have set up the Pub/Sub subscription")
        print("   3. Have valid environment variables")
        print("   4. Have proper GCP permissions for the topic/subscription")


def main():
    """Main CLI entry point with command options"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "check-pubsub":
            print("🚀 Checking PubSub Setup")
            print("=" * 30)
            check_pubsub_setup()
        elif command == "test":
            print("🚀 Testing Gmail PubSub Subscriber")
            print("=" * 40)
            test_subscriber()
        else:
            print("Usage:")
            print("  python -m ...pubsub_subscriber.py check-pubsub  # Check PubSub setup only")
            print("  python -m ...pubsub_subscriber.py test          # Full test")
            print("  python -m ...pubsub_subscriber.py               # Full test (default)")
    else:
        print("🚀 Testing Gmail PubSub Subscriber")
        print("=" * 40)
        test_subscriber()

if __name__ == "__main__":
    main()
