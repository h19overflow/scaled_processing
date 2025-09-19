"""
Fix Gmail Pub/Sub permissions by finding the correct service account.
Gmail uses project-specific service accounts that follow a pattern.
"""

from google.cloud import pubsub_v1
from dotenv import load_dotenv

load_dotenv()

def fix_gmail_permissions():
    """Add the correct Gmail service account permissions."""

    publisher = pubsub_v1.PublisherClient()
    project_id = "gmail-monitor-project-472511"
    topic_name = "gmail-notifications"
    topic_path = publisher.topic_path(project_id, topic_name)

    # Get the project number (needed for Gmail service account)
    from google.cloud import resourcemanager

    try:
        client = resourcemanager.ProjectsClient()
        project = client.get_project(name=f"projects/{project_id}")
        project_number = project.name.split("/")[1]
        print(f"Project ID: {project_id}")
        print(f"Project Number: {project_number}")
    except Exception as e:
        print(f"Could not get project number: {e}")
        # Use a common pattern as fallback
        project_number = "472511"

    # Gmail service account patterns to try
    gmail_service_accounts = [
        f"serviceAccount:service-{project_number}@gcp-sa-gmail.iam.gserviceaccount.com",
        f"serviceAccount:gmail-api-push@system.gserviceaccount.com",
        f"serviceAccount:{project_id}@appspot.gserviceaccount.com",
        f"serviceAccount:service-{project_number}@gmail-api-push.iam.gserviceaccount.com"
    ]

    # Get current policy
    try:
        policy = publisher.get_iam_policy(request={"resource": topic_path})
        print(f"\nCurrent permissions on {topic_path}:")

        for binding in policy.bindings:
            if binding.role == "roles/pubsub.publisher":
                print(f"  Publisher role members:")
                for member in binding.members:
                    print(f"    - {member}")

    except Exception as e:
        print(f"Error getting current policy: {e}")
        return

    print(f"\nTrying to add Gmail service accounts...")

    success_count = 0
    for sa in gmail_service_accounts:
        try:
            # Check if already exists
            already_exists = False
            for binding in policy.bindings:
                if binding.role == "roles/pubsub.publisher" and sa in binding.members:
                    already_exists = True
                    break

            if already_exists:
                print(f"✅ Already exists: {sa}")
                success_count += 1
                continue

            # Try to add it
            test_policy = publisher.get_iam_policy(request={"resource": topic_path})

            # Find publisher binding or create one
            publisher_binding = None
            for binding in test_policy.bindings:
                if binding.role == "roles/pubsub.publisher":
                    publisher_binding = binding
                    break

            if publisher_binding:
                publisher_binding.members.append(sa)
            else:
                test_policy.bindings.add(
                    role="roles/pubsub.publisher",
                    members=[sa]
                )

            # Try to set the policy
            publisher.set_iam_policy(request={"resource": topic_path, "policy": test_policy})
            print(f"✅ Successfully added: {sa}")
            success_count += 1

        except Exception as e:
            if "does not exist" in str(e) or "must be associated with an active" in str(e):
                print(f"❌ Invalid account: {sa}")
            else:
                print(f"❌ Error with {sa}: {e}")

    print(f"\n{'='*60}")
    if success_count > 0:
        print(f"✅ Successfully configured {success_count} service accounts!")
        print("Try your Gmail authentication again at: http://localhost:8000/auth/login")
    else:
        print("❌ No valid Gmail service accounts found.")
        print("\nMANUAL SOLUTION:")
        print("1. Go to Google Cloud Console")
        print("2. Navigate to IAM & Admin > Service Accounts")
        print("3. Look for accounts with 'gmail' or 'gcp-sa-gmail' in the name")
        print("4. Copy that service account email")
        print("5. Go to Pub/Sub > Topics > gmail-notifications > Permissions")
        print("6. Add that service account with 'Pub/Sub Publisher' role")

if __name__ == "__main__":
    fix_gmail_permissions()