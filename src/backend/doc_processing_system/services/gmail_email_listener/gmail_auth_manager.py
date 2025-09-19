"""
auth_manager.py

Manages Gmail API OAuth2 authentication and credential refresh.

- Loads client secrets and token file.
- Refreshes or obtains tokens (manual OAuth first time).
- Exposes helpers to get valid Gmail API credentials and service client.

Used by: GmailService (to authorize all Gmail API calls)
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

class GmailAuthManager:
    def __init__(self, client_secrets_path: str, token_path: str = "src/backend/doc_processing_system/services/gmail_email_listener/secerets/client_secret_504172449061-r0o6bi19rpqd2ccm9jacobfvue85j92e.apps.googleusercontent.com.json"):
        self.client_secrets_path = client_secrets_path
        self.token_path = token_path
        # API permission scopes
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]

    def get_credentials(self) -> Credentials:
        """Return valid Gmail API credentials (load, refresh, or require manual OAuth if none exist)"""
        creds = None

        # 1. Try to load saved token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        # 2. Refresh token or run OAuth flow if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # First run or no valid token: needs user browser interaction
                flow = Flow.from_client_secrets_file(
                    self.client_secrets_path,
                    scopes=self.SCOPES,
                    redirect_uri='http://localhost:8000/auth/callback'
                )
                raise Exception("Manual OAuth flow required: Run this locally in an interactive environment.")

        # 3. Save new/updated token for future use
        with open(self.token_path, 'w') as token:
            token.write(creds.to_json())

        return creds

    def get_gmail_service(self):
        """Builds an authenticated Gmail API client"""
        credentials = self.get_credentials()
        return build('gmail', 'v1', credentials=credentials)
