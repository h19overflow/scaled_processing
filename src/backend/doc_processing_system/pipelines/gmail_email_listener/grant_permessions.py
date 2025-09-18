# grant_permissions.py
from google.cloud import pubsub_v1


def grant_gmail_permissions():
    """Grant Gmail API permission to publish to Pub/Sub topic"""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path("gmail-monitor-project", "gmail-notifications")

    policy = publisher.get_iam_policy(request={"resource": topic_path})

    # Add Gmail API service account as publisher
    policy.bindings.add(
        role="roles/pubsub.publisher",
        members=["serviceAccount:gmail-monitor-sa@gmail-monitor-project-472511.iam.gserviceaccount.com"]
    )

    publisher.set_iam_policy(request={"resource": topic_path, "policy": policy})
    print("Permissions granted successfully")


if __name__ == "__main__":
    grant_gmail_permissions()
