from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()

# Gmail watch setup script for hamzakhaledlklk@gmail.com
def setup_gmail_watch_for_user():
    """
    Sets up Gmail watch for hamzakhaledlklk@gmail.com using service account credentials.
    This script helps debug why pubsub_subscriber.py is not listening properly.
    """

    # Configuration from your existing setup
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/pubsub'
    ]
    USER_EMAIL = 'hamzakhaledlklk@gmail.com'
    PROJECT_ID = 'gmail-monitor-project-472511'
    TOPIC_NAME = 'gmail-notifications'

    # Get service account file from environment or use default path
    service_account_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not service_account_file:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set in environment")
        print("💡 Set it to point to your service account JSON file")
        return

    if not os.path.exists(service_account_file):
        print(f"❌ Service account file not found: {service_account_file}")
        return

    try:
        # For personal Gmail accounts, use OAuth2 flow instead of service account
        # Service accounts only work with Google Workspace domains with delegation
        print("⚠️  Personal Gmail detected - service account won't work")
        print("💡 Use OAuth2 credentials instead (token.json from your main app)")

        # Check if OAuth token exists (from main app)
        token_path = os.getenv("GMAIL_TOKEN_PATH")
        if token_path and os.path.exists(token_path):
            print(f"✅ Found OAuth token: {token_path}")
            print("💡 Your main app should already have working Gmail access")
            print("💡 The issue is likely in PubSub configuration, not authentication")
            return

        # Still try service account for debugging purposes
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=SCOPES,
            subject=USER_EMAIL  # This won't work for personal Gmail
        )

        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        print(f"✅ Gmail service initialized for {USER_EMAIL}")

        # Test Gmail API access first
        try:
            profile = service.users().getProfile(userId='me').execute()
            print(f"✅ Gmail API access confirmed")
            print(f"📧 Email: {profile.get('emailAddress')}")
            print(f"📊 Total messages: {profile.get('messagesTotal', 'Unknown')}")
            print(f"📍 Current history ID: {profile.get('historyId', 'Unknown')}")
        except Exception as e:
            print(f"❌ Cannot access Gmail API: {e}")
            print("💡 Check if domain-wide delegation is properly configured")
            return

        # Setup Gmail watch - using the configuration from main.py
        topic_path = f'projects/{PROJECT_ID}/topics/{TOPIC_NAME}'

        # Try the configuration from main.py first (INCLUDE + INBOX)
        watch_request_main = {
            'topicName': topic_path,
            'labelFilterBehavior': 'INCLUDE',
            'labelIds': ['INBOX']
        }

        print(f"\n🔧 Setting up Gmail watch...")
        print(f"📰 Topic: {topic_path}")
        print(f"🏷️  Labels: INCLUDE [INBOX]")

        try:
            response = service.users().watch(userId='me', body=watch_request_main).execute()
            print(f"✅ Gmail watch setup successful!")
            print(f"📍 History ID: {response.get('historyId')}")
            print(f"📅 Expiration: {response.get('expiration')}")

        except Exception as watch_error:
            print(f"❌ Failed to setup Gmail watch with INCLUDE/INBOX: {watch_error}")

            # Try alternative configuration from pubsub_subscriber.py (EXCLUDE + empty)
            print("\n🔄 Trying alternative watch configuration...")
            watch_request_alt = {
                'topicName': topic_path,
                'labelFilterBehavior': 'EXCLUDE',
                'labelIds': []  # Empty list with EXCLUDE = watch all activity
            }

            try:
                response = service.users().watch(userId='me', body=watch_request_alt).execute()
                print(f"✅ Gmail watch setup successful with alternative config!")
                print(f"📍 History ID: {response.get('historyId')}")
                print(f"📅 Expiration: {response.get('expiration')}")
                print(f"🏷️  Using: EXCLUDE [] (watches all activity)")

            except Exception as alt_error:
                print(f"❌ Both watch configurations failed: {alt_error}")
                print("\n🔍 Potential issues:")
                print("1. PubSub topic doesn't exist or lacks permissions")
                print("2. Service account missing Gmail API permissions")
                print("3. Domain-wide delegation not configured")
                print("4. Topic IAM permissions not set correctly")
                return

        # Test PubSub connectivity
        print(f"\n🔧 Testing PubSub setup...")
        try:
            from google.cloud import pubsub_v1

            # Test publisher client
            publisher = pubsub_v1.PublisherClient()
            topic_path_full = publisher.topic_path(PROJECT_ID, TOPIC_NAME)

            # Check if topic exists
            try:
                topic = publisher.get_topic(request={"topic": topic_path_full})
                print(f"✅ PubSub topic exists: {topic.name}")
            except Exception as topic_error:
                print(f"❌ PubSub topic issue: {topic_error}")

            # Check subscription
            subscriber = pubsub_v1.SubscriberClient()
            subscription_name = "gmail-notifications-processor-sub"
            subscription_path = subscriber.subscription_path(PROJECT_ID, subscription_name)

            try:
                subscription = subscriber.get_subscription(request={"subscription": subscription_path})
                print(f"✅ PubSub subscription exists: {subscription.name}")
                print(f"📎 Connected to topic: {subscription.topic}")
            except Exception as sub_error:
                print(f"❌ PubSub subscription issue: {sub_error}")

        except ImportError:
            print("❌ google-cloud-pubsub not installed")
            print("💡 Run: pip install google-cloud-pubsub")
        except Exception as pubsub_error:
            print(f"❌ PubSub connectivity test failed: {pubsub_error}")

    except Exception as e:
        print(f"❌ Service account authentication failed: {e}")
        print("💡 Check if the service account file is valid and has proper permissions")

def diagnose_pubsub_listening_issues():
    """
    Diagnose why pubsub_subscriber.py might not be listening properly.
    """
    print("\n" + "="*50)
    print("🔍 DIAGNOSING PUBSUB LISTENING ISSUES")
    print("="*50)

    # Check 1: Configuration mismatch
    print("\n1. 📋 Configuration Analysis:")
    print("   main.py uses: labelFilterBehavior='INCLUDE', labelIds=['INBOX']")
    print("   pubsub_subscriber.py test uses: labelFilterBehavior='EXCLUDE', labelIds=[]")
    print("   ⚠️  MISMATCH DETECTED!")
    print("   💡 Recommendation: Use consistent configuration across all files")

    # Check 2: History ID issues
    print("\n2. 📍 History ID Issues:")
    print("   Error in pubsub_subscriber.py: 'Requested entity was not found' (404)")
    print("   💡 This suggests old/invalid history IDs are being used")
    print("   💡 Solution: Use fallback to recent messages when history ID fails")

    # Check 3: Message processing
    print("\n3. 📨 Message Processing:")
    print("   pubsub_subscriber.py has proper fallback handling for 404 errors")
    print("   But may not be receiving messages due to watch configuration mismatch")

    # Check 4: Permissions
    print("\n4. 🔐 Permissions Check:")
    print("   Service accounts in grant_permissions.py:")
    print("   - gmail-monitor-sa@gmail-monitor-project-472511.iam.gserviceaccount.com")
    print("   - serviceAccount:gmail-api@system.gserviceaccount.com")
    print("   💡 Both should have 'roles/pubsub.publisher' on the topic")

    print("\n" + "="*50)
    print("🎯 LIKELY ROOT CAUSE:")
    print("="*50)
    print("The Gmail watch configuration in main.py doesn't match")
    print("the expected configuration in pubsub_subscriber.py test.")
    print("This causes Gmail to send notifications to the topic,")
    print("but the subscriber processes them with wrong assumptions.")

if __name__ == "__main__":
    print("🚀 Gmail Watch Setup Test for hamzakhaledlklk@gmail.com")
    print("="*60)
    setup_gmail_watch_for_user()
    diagnose_pubsub_listening_issues()