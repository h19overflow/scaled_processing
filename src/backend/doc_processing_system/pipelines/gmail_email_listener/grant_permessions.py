from google.cloud import pubsub_v1
from dotenv import load_dotenv

# Load environment variables (including GOOGLE_APPLICATION_CREDENTIALS for API authentication)
load_dotenv()


def grant_gmail_permissions():
    """
    Grants the Gmail API service account permission to publish messages to a specific Cloud Pub/Sub topic.
    This lets the Gmail API push notifications or events to your topic, enabling automated message processing
    downstream (e.g., in document or email pipelines).
    """

    # Initialize the Pub / Sub Publisher client using service account credentials from environment
    publisher = pubsub_v1.PublisherClient()

    # Build the fully qualified topic path using the actual Google Cloud project ID and topic name
    topic_path = publisher.topic_path("gmail-monitor-project-472511", "gmail-notifications")
    # e.g., 'projects/gmail-monitor-project-472511/topics/gmail-notifications'

    # Fetch the existing IAM policy for the topic (shows who has which permissions)
    policy = publisher.get_iam_policy(request={"resource": topic_path})

    # Grant the 'roles/pubsub.publisher' to the Gmail API service account,
    # allowing it to publish (send) messages to this topic.
    # This does NOT allow reading, deleting, or otherwise managing the topic.
    policy.bindings.add(
        role="roles/pubsub.publisher",
        members=["serviceAccount:gmail-monitor-sa@gmail-monitor-project-472511.iam.gserviceaccount.com"]
    )

    # Commit the updated policy, applying the publisher role to this service account for this topic only.
    publisher.set_iam_policy(request={"resource": topic_path, "policy": policy})
    print("Permissions granted successfully")


if __name__ == "__main__":
    # Entry point: grant the publisher permission to the Gmail API service account
    grant_gmail_permissions()
