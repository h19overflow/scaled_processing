# Gmail Integration Architecture

This directory contains PlantUML diagrams explaining the Gmail integration architecture and flow.

## Key Concepts

### Two Different Authentication Methods

1. **Service Account** (`gmail-monitor-project-472511-3f40fb6f0855.json`)
   - Used for: Pub/Sub publisher permissions only
   - Purpose: Allows Google to send notifications to your topic
   - Does NOT access Gmail directly

2. **OAuth2 Client** (`client_secret_xxx.json`)
   - Used for: Gmail API access (reading emails, attachments)
   - Purpose: Allows your app to access user's Gmail on their behalf
   - Requires user consent and creates `token.json`

### The Flow

1. **Setup**: Service account gets Pub/Sub permissions, OAuth2 client gets Gmail permissions
2. **First Run**: User must authorize OAuth2 flow in browser (creates `token.json`)
3. **Normal Operation**: App uses `token.json` to access Gmail, service account handles Pub/Sub
4. **Email Processing**: Gmail sends notifications via Pub/Sub, app fetches emails via OAuth2

## Files

- `gmail_architecture_diagram.puml` - High-level architecture overview
- `gmail_flow_sequence.puml` - Detailed sequence flow from setup to processing
- `gmail_auth_manager.py` - Handles OAuth2 token management
- `gmail_service.py` - Gmail API operations using OAuth2 tokens
- `models.py` - Pydantic models for data structures

## Environment Variables

```bash
GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"  # For Pub/Sub
GMAIL_CLIENT_SECRETS_PATH="path/to/client_secret.json"        # For OAuth2
GMAIL_TOKEN_PATH="path/to/token.json"                         # OAuth2 tokens (auto-created)
```

## Why Two Different Auth Methods?

- **Gmail API**: Requires user consent (OAuth2) because you're accessing their personal emails
- **Pub/Sub**: Uses service account because it's just infrastructure - no personal data involved

The service account can't read emails, and OAuth2 tokens can't be used for Pub/Sub infrastructure.