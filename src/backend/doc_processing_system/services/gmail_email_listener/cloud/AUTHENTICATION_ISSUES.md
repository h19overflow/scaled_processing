# Gmail Authentication Issues Documentation

## Issue: 401 UNAUTHENTICATED Error

**Date:** 2025-09-19
**Component:** Gmail PubSub Subscriber
**Status:** 🔍 INVESTIGATING

### Problem Description

When running the PubSub subscriber test, encountering authentication error:

```json
{
  "error": {
    "code": 401,
    "message": "Request is missing required authentication credential. Expected OAuth 2 access token, login cookie or other valid authentication credential.",
    "errors": [
      {
        "message": "Login Required.",
        "domain": "global",
        "reason": "required",
        "location": "Authorization",
        "locationType": "header"
      }
    ],
    "status": "UNAUTHENTICATED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "reason": "CREDENTIALS_MISSING",
        "domain": "googleapis.com",
        "metadata": {
          "method": "caribou.api.proto.MailboxService.ListHistory",
          "service": "gmail.googleapis.com"
        }
      }
    ]
  }
}
```

### Context

- **Subscriber working:** PubSub subscriber connects successfully to subscription
- **OAuth flow completed:** FastAPI `/auth/login` and `/auth/callback` work
- **Token files exist:** `token.json` is present and contains credentials
- **Issue location:** Error occurs when calling Gmail API methods

### Potential Root Causes

#### 1. **Token Expiration**
- Access token might be expired
- Refresh token might be invalid
- Token refresh mechanism failing

#### 2. **Service Account vs User Account Confusion**
- PubSub subscriber might be using wrong credentials type
- OAuth2 user tokens vs service account tokens mismatch

#### 3. **Credential Loading Issues**
- `GmailAuthManager` not properly loading saved tokens
- Token file format corruption
- Path issues in environment variables

#### 4. **Scope Issues**
- Required Gmail scopes not granted during OAuth flow
- Scopes: `gmail.readonly`, `gmail.modify` needed

#### 5. **Session/Context Issues**
- Different execution context between FastAPI app and standalone script
- Environment variables not loaded properly in test script

### Investigation Steps Needed

1. **Verify Token Content**
   ```python
   # Check token.json structure
   with open(token_path, 'r') as f:
       token_data = json.load(f)
       print(json.dumps(token_data, indent=2))
   ```

2. **Test Token Refresh**
   ```python
   # Manually test credential refresh
   creds = Credentials.from_authorized_user_file(token_path, SCOPES)
   if creds.expired:
       creds.refresh(Request())
   ```

3. **Compare Working vs Non-Working Contexts**
   - FastAPI app context (working)
   - Standalone script context (failing)

4. **Verify Environment Variables**
   ```bash
   echo $GMAIL_CLIENT_SECRETS_PATH
   echo $GMAIL_TOKEN_PATH
   ```

### Current Workarounds

None identified yet.

### Next Steps

1. Add detailed credential debugging to `GmailAuthManager`
2. Compare token loading between FastAPI and standalone contexts
3. Verify OAuth2 scope permissions
4. Test manual token refresh process
5. Consider service account approach for PubSub operations

### Related Files

- `gmail_auth_manager.py` - OAuth2 credential management
- `gmail_service.py` - Gmail API wrapper
- `pubsub_subscriber.py` - Where error occurs
- `token.json` - User OAuth2 credentials
- `client_secret.json` - OAuth2 app credentials

### Notes

- Subscriber successfully connects to Pub/Sub (authentication with Google Cloud works)
- Gmail API calls fail (OAuth2 user authentication fails)
- Suggests issue is specific to Gmail API credential handling, not general Google Cloud auth

---

**TODO:** Investigate credential refresh mechanism and context differences between FastAPI app and standalone execution.