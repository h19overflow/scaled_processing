"""
Find the correct Gmail API service account for your project.
Different projects have different Gmail service account formats.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def find_gmail_service_account():
    """Find the Gmail API service account for your project."""
    project_id = "gmail-monitor-project-472511"

    # Common Gmail API service account patterns
    gmail_service_accounts = [
        f"serviceAccount:gmail-api@{project_id}.iam.gserviceaccount.com",
        f"serviceAccount:gmail-api@system.gserviceaccount.com",
        f"serviceAccount:{project_id}@{project_id}.iam.gserviceaccount.com",
        f"serviceAccount:service-{project_id}@gmail-api-push.iam.gserviceaccount.com",
        "serviceAccount:gmail-api@system.gserviceaccount.com"
    ]

    print("Common Gmail API service account patterns:")
    for i, sa in enumerate(gmail_service_accounts, 1):
        print(f"{i}. {sa}")

    print("\n" + "="*80)
    print("SOLUTION: Try Google Cloud Console approach")
    print("="*80)

    print("\n1. Go to: https://console.cloud.google.com/cloudpubsub/topic")
    print(f"2. Select project: {project_id}")
    print("3. Click on topic: gmail-notifications")
    print("4. Go to 'PERMISSIONS' tab")
    print("5. Click '+ GRANT ACCESS'")
    print("6. In 'New principals', add: gmail-api@system.gserviceaccount.com")
    print("7. Select role: 'Pub/Sub Publisher'")
    print("8. Click 'Save'")

    print("\n" + "="*80)
    print("ALTERNATIVE: Enable Gmail Push Notifications in Console")
    print("="*80)
    print("1. Go to: https://console.cloud.google.com/apis/api/gmail.googleapis.com")
    print("2. Make sure Gmail API is enabled")
    print("3. Go to 'Push Notifications' section")
    print("4. Configure with your topic name")

if __name__ == "__main__":
    find_gmail_service_account()