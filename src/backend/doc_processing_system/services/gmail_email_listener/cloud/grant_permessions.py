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

    # First, create the topic if it doesn't exist
    try:
        publisher.create_topic(request={"name": topic_path})
        print(f"Topic created: {topic_path}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"Topic already exists: {topic_path}")
        else:
            print(f"Error creating topic: {e}")
            # Continue anyway - topic might exist

    # Fetch the existing IAM policy for the topic (shows who has which permissions)
    try:
        policy = publisher.get_iam_policy(request={"resource": topic_path})
    except Exception as e:
        print(f"Error getting IAM policy: {e}")
        return

    # Grant the 'roles/pubsub.publisher' to the Gmail API service account,
    # allowing it to publish (send) messages to this topic.
    # This does NOT allow reading, deleting, or otherwise managing the topic.

    # Gmail API needs special permissions - add both your service account AND Gmail's system account
    service_accounts = [
        "serviceAccount:gmail-monitor-sa@gmail-monitor-project-472511.iam.gserviceaccount.com",  # Your service account
        "serviceAccount:gmail-api@system.gserviceaccount.com"  # Gmail API system account
    ]

    # Check existing bindings
    existing_members = set()
    for binding in policy.bindings:
        if binding.role == "roles/pubsub.publisher":
            existing_members.update(binding.members)

    # Add missing service accounts
    new_members = []
    for sa in service_accounts:
        if sa not in existing_members:
            new_members.append(sa)
            print(f"Adding publisher permission for: {sa}")
        else:
            print(f"Permission already exists for: {sa}")

    if new_members:
        # Find existing pubsub.publisher binding or create new one
        publisher_binding = None
        for binding in policy.bindings:
            if binding.role == "roles/pubsub.publisher":
                publisher_binding = binding
                break

        if publisher_binding:
            # Add to existing binding
            publisher_binding.members.extend(new_members)
        else:
            # Create new binding
            policy.bindings.add(
                role="roles/pubsub.publisher",
                members=new_members
            )

    # Commit the updated policy, s applying the publisher role to this service account for this topic only.
    try:
        publisher.set_iam_policy(request={"resource": topic_path, "policy": policy})
        print("Permissions granted successfully")
    except Exception as e:
        print(f"Error setting IAM policy: {e}")


if __name__ == "__main__":
    # Entry point: grant the publisher permission to the Gmail API service account
    grant_gmail_permissions()
