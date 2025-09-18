# auth_manager.py
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


class GmailAuthManager:
    def __init__(self, client_secrets_path: str, token_path: str = "token.json"):
        self.client_secrets_path = client_secrets_path
        self.token_path = token_path
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]

    def get_credentials(self) -> Credentials:
        """Get valid credentials for Gmail API"""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # This requires user interaction - implement OAuth flow
                flow = Flow.from_client_secrets_file(
                    self.client_secrets_path,
                    scopes=self.SCOPES,
                    redirect_uri='http://localhost:8000/auth/callback'
                )
                # In production, implement proper OAuth flow
                raise Exception("Manual OAuth flow required")

        # Save credentials for next run
        with open(self.token_path, 'w') as token:
            token.write(creds.to_json())

        return creds

    def get_gmail_service(self):
        """Build Gmail service with authenticated credentials"""
        credentials = self.get_credentials()
        return build('gmail', 'v1', credentials=credentials)
