# Gmail Push Notifications Troubleshooting Guide

## Overview
This guide helps diagnose why Gmail isn't sending push notifications to your PubSub topic, even when the watch setup appears successful.

## Key Terms & Concepts

### OAuth2 Authentication Flow
- **Client Secret**: JSON file containing your app's credentials (client_id, client_secret) from Google Cloud Console
- **OAuth2 Token Exchange**: Process where Google exchanges an authorization code for access/refresh tokens
- **Access Token**: Short-lived token (1 hour) used to make API calls
- **Refresh Token**: Long-lived token used to get new access tokens without user interaction
- **Scopes**: Permissions your app requests (gmail.readonly, gmail.modify, gmail.settings.basic)

### Redirect/Callback Endpoints
- **Redirect URI**: Where Google sends users after OAuth consent (e.g., http://localhost:8000/auth/callback)
- **Callback Endpoint**: Your app's endpoint that receives the authorization code from Google
- **State Parameter**: Security token to prevent CSRF attacks during OAuth flow

### Service Accounts vs User Accounts
- **User Account OAuth**: Your personal Gmail account authorizing the app
- **Service Account**: Robot account for server-to-server communication (not used for Gmail push)
- **Gmail API Push**: Uses Google's internal service account (gmail-api-push@system.gserviceaccount.com)

### PubSub Components
- **Topic**: Named resource where messages are published
- **Subscription**: Named resource that receives messages from a topic
- **Publisher**: Service that sends messages to topics
- **Subscriber**: Service that pulls messages from subscriptions

## Troubleshooting Checklist

### 1. OAuth2 Scopes Verification
**Problem**: Missing required scopes for Gmail push notifications

**Check**:
```bash
# View current token scopes
cat "C:\Users\User\Projects\scaled_processing\src\backend\doc_processing_system\services\gmail_email_listener\secerets\token.json"
```

**Required Scopes**:
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.settings.basic` ⚠️ **CRITICAL for push notifications**

**Fix**: If missing gmail.settings.basic, re-authenticate:
1. Delete token.json file
2. Run OAuth flow again via /auth/login endpoint

### 2. Google Cloud Project Configuration

#### APIs Enabled
**Check**:
```bash
gcloud services list --enabled --project=gmail-monitor-project-472511 --filter="name:gmail OR name:pubsub"
```

**Required APIs**:
- gmail.googleapis.com
- pubsub.googleapis.com

**Fix**:
```bash
gcloud services enable gmail.googleapis.com --project=gmail-monitor-project-472511
gcloud services enable pubsub.googleapis.com --project=gmail-monitor-project-472511
```

#### PubSub Topic Exists
**Check**:
```bash
gcloud pubsub topics describe gmail-notifications --project=gmail-monitor-project-472511
```

**Fix if missing**:
```bash
gcloud pubsub topics create gmail-notifications --project=gmail-monitor-project-472511
```

#### PubSub Subscription Exists
**Check**:
```bash
gcloud pubsub subscriptions describe gmail-notifications-processor-sub --project=gmail-monitor-project-472511
```

**Fix if missing**:
```bash
gcloud pubsub subscriptions create gmail-notifications-processor-sub \
  --topic=gmail-notifications \
  --project=gmail-monitor-project-472511
```

### 3. IAM Permissions

#### Gmail Service Account Permissions
**Problem**: Gmail's internal service account can't publish to your topic

**Check**:
```bash
gcloud pubsub topics get-iam-policy gmail-notifications --project=gmail-monitor-project-472511
```

**Required Member**:
- `serviceAccount:gmail-api-push@system.gserviceaccount.com` with role `roles/pubsub.publisher`

**Fix**:
```bash
gcloud pubsub topics add-iam-policy-binding gmail-notifications \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project=gmail-monitor-project-472511
```

### 4. Domain Verification (Most Common Issue)

#### Google Search Console Verification
**Problem**: Gmail requires domain ownership verification for push notifications

**Check**: Go to [Google Search Console](https://search.google.com/search-console)
- Verify if your domain (or gmail.com for personal accounts) is verified
- For personal Gmail: You may need to verify the gmail.com domain or your custom domain

**Fix**:
1. Add property in Search Console
2. Verify ownership via DNS/HTML file/meta tag
3. Wait 24-48 hours for propagation

#### Project Number Registration
**Problem**: Your GCP project isn't registered for Gmail push notifications

**Check your project number**:
```bash
gcloud projects describe gmail-monitor-project-472511 --format="value(projectNumber)"
```

**Manual verification needed**: Contact Google Cloud Support if domain verification doesn't work

### 5. Gmail Watch Configuration

#### Topic Name Format
**Problem**: Incorrect topic name format

**Correct Format**: `projects/PROJECT_ID/topics/TOPIC_NAME`
**Your Format**: `projects/gmail-monitor-project-472511/topics/gmail-notifications`

#### Label Filtering
**Problem**: Too restrictive label filtering

**Test with minimal watch request**:
```json
{
  "topicName": "projects/gmail-monitor-project-472511/topics/gmail-notifications"
}
```

**Avoid initially**:
- labelIds filtering
- labelFilterBehavior restrictions

#### Watch Expiration
**Check current watch status**:
```bash
# Through your Gmail service - no direct API to check active watches
# Watch expires in ~7 days and needs renewal
```

### 6. Network & Firewall Issues

#### Outbound HTTPS Access
**Problem**: Network blocks Google API calls

**Test**:
```bash
curl -I https://gmail.googleapis.com
curl -I https://pubsub.googleapis.com
```

**Corporate Networks**: Check if proxy/firewall blocks Google APIs

### 7. Development vs Production Differences

#### Test Environment Issues
- **Development emails**: Gmail may delay notifications for low-volume senders
- **Personal vs G-Suite**: Different verification requirements
- **Rate limiting**: Too many test emails can trigger rate limits

#### Production Recommendations
- Use G-Suite/Google Workspace accounts
- Implement proper domain verification
- Monitor watch expiration and renewal

### 8. Debugging Commands

#### Check Project Configuration
```bash
# List all resources
gcloud projects list
gcloud pubsub topics list --project=gmail-monitor-project-472511
gcloud pubsub subscriptions list --project=gmail-monitor-project-472511

# Check IAM policies
gcloud projects get-iam-policy gmail-monitor-project-472511
gcloud pubsub topics get-iam-policy gmail-notifications --project=gmail-monitor-project-472511
```

#### Test PubSub Connectivity
```bash
# Publish test message
gcloud pubsub topics publish gmail-notifications \
  --message='{"test": "message"}' \
  --project=gmail-monitor-project-472511

# Pull messages
gcloud pubsub subscriptions pull gmail-notifications-processor-sub \
  --limit=5 --auto-ack --project=gmail-monitor-project-472511
```

#### Monitor PubSub Activity
```bash
# Check subscription metrics in Cloud Console
# Monitor topic publish rates
# Check dead letter queue if configured
```

### 9. Common Error Messages

#### "Requested entity was not found" (404)
- **Cause**: Expired historyId in notification
- **Solution**: Implement fallback to recent messages (already in your code)

#### "Permission denied" (403)
- **Cause**: Missing IAM permissions or OAuth scopes
- **Solution**: Check IAM bindings and re-authenticate with correct scopes

#### "Invalid topic name"
- **Cause**: Malformed topic name in watch request
- **Solution**: Use exact format: projects/PROJECT_ID/topics/TOPIC_NAME

#### Watch setup succeeds but no notifications
- **Cause**: Domain not verified or Gmail internal routing issue
- **Solution**: Domain verification in Search Console

### 10. Step-by-Step Verification Process

1. **Verify OAuth scopes** (include gmail.settings.basic)
2. **Test PubSub manually** (publish/pull test messages)
3. **Check IAM permissions** (gmail-api-push service account)
4. **Verify domain ownership** (Search Console)
5. **Use minimal watch request** (no label filtering)
6. **Wait 5-10 minutes** after setup (Gmail propagation delay)
7. **Send test email** and monitor PubSub
8. **Check dead letter queue** for failed notifications

### 11. Advanced Troubleshooting

#### Enable Audit Logging
```bash
# Enable PubSub audit logs to see if Gmail is attempting to publish
gcloud logging read 'resource.type="pubsub_topic" AND resource.labels.topic_id="gmail-notifications"' \
  --project=gmail-monitor-project-472511 --limit=50
```

#### Monitor Gmail API Quotas
- Check Gmail API quota usage in Cloud Console
- Look for rate limiting or quota exceeded errors

#### Alternative Testing Methods
- Use Gmail API's `history` endpoint directly
- Implement polling fallback for critical applications
- Test with different Gmail accounts (personal vs workspace)

## Success Indicators

✅ **Push notifications working when**:
- OAuth token has gmail.settings.basic scope
- PubSub topic has gmail-api-push@system.gserviceaccount.com publisher permission
- Domain is verified in Google Search Console
- Watch setup returns valid expiration timestamp
- New emails trigger JSON notifications in PubSub subscription

## Next Steps if Still Not Working

1. **Contact Google Cloud Support** with your project number
2. **Try different Gmail account** (workspace vs personal)
3. **Implement polling fallback** while troubleshooting push
4. **Check Google's Gmail Push Notifications documentation** for updates

## Testing Script

Save this as `test_gmail_push.py`:

```python
import json
import time
from google.cloud import pubsub_v1

def test_gmail_push_setup():
    """Comprehensive test of Gmail push notification setup"""

    # 1. Test PubSub connectivity
    project_id = "gmail-monitor-project-472511"
    subscription_name = "gmail-notifications-processor-sub"

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    # 2. Check subscription exists
    try:
        subscription = subscriber.get_subscription(request={"subscription": subscription_path})
        print(f"✅ Subscription exists: {subscription.name}")
    except Exception as e:
        print(f"❌ Subscription error: {e}")
        return False

    # 3. Pull any existing messages
    try:
        response = subscriber.pull(
            request={"subscription": subscription_path, "max_messages": 5}
        )
        print(f"📨 Found {len(response.received_messages)} pending messages")

        for msg in response.received_messages:
            try:
                data = json.loads(msg.message.data.decode())
                print(f"📧 Valid Gmail notification: {data}")
            except json.JSONDecodeError:
                print(f"🔍 Non-JSON message (test message): {msg.message.data.decode()}")

            # Acknowledge message
            subscriber.acknowledge(
                request={"subscription": subscription_path, "ack_ids": [msg.ack_id]}
            )

    except Exception as e:
        print(f"❌ Pull error: {e}")

    return True

if __name__ == "__main__":
    test_gmail_push_setup()
```

## Final Notes

Gmail push notifications are complex and require multiple components to work correctly. The most common issue is **domain verification** - even if everything else is configured perfectly, Gmail won't send notifications without proper domain ownership verification.

**Remember**: Gmail can take 5-10 minutes to start sending notifications after watch setup, and verification propagation can take 24-48 hours.