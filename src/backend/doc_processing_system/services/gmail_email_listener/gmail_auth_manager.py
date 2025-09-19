import os
from google.auth.transport.requests import Request          # Used to make authorized HTTP requests (for refreshing tokens)
from google.oauth2.credentials import Credentials           # Manages OAuth2 tokens (access/refresh), loads/saves and refreshes as needed
from google_auth_oauthlib.flow import Flow                  # Handles the interactive OAuth2 flow for user consent and token exchange
from googleapiclient.discovery import build                 # Dynamically creates API clients for Google services (like Gmail)
from dotenv import load_dotenv
load_dotenv()

class GmailAuthManager:
    """
    Handles Gmail API OAuth2 authentication, token management, and credential refresh.

    Key responsibilities:
    - Loading client secrets file (the 'ID card' for the app—client ID/secret).
    - Attempting to load existing, cached OAuth2 tokens for the user (from disk).
    - If token is missing/expired, refresh it or trigger interactive OAuth2 browser flow.
    - Provides helper to create an authorized Gmail API service client.

    Used as a dependency by the GmailService, ensuring all Gmail API calls are authorized.
    """
    def __init__(self, client_secrets_path: str, token_path: str = os.getenv("GMAIL_CLIENT_SECRETS_PATH")):
        self.client_secrets_path = client_secrets_path    # Path to client_secret.json (generated in Google Cloud console)
        self.token_path = token_path                      # Path where access/refresh tokens are stored (JSON)
        # The OAuth2 scopes (permissions) this app will request from the user—for Gmail read and modify access
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]

    def get_credentials(self) -> Credentials:
        """
        Ensures valid Gmail API OAuth2 credentials:
        - Loads from saved token file if available.
        - Refreshes token if expired and a refresh token exists (uses requests transport).
        - Runs interactive OAuth2 flow if no valid credentials, requiring user consent.
        - Always updates and saves tokens for future sessions.

        Returns:
            google.oauth2.credentials.Credentials: the valid, active credentials
        """
        creds = None

        # 1. Try loading an existing, saved OAuth2 token
        if os.path.exists(self.token_path):
            # Loads credentials from file, token-scoped for this app
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        # 2. If credentials are missing or invalid, refresh or start new OAuth2 flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # If the access token is expired and a refresh token is available, request a fresh access token
                creds.refresh(Request())   # Uses transport.Request to perform the secure HTTPS token exchange
            else:
                # No tokens present or can't be refreshed; must run browser-based OAuth2 consent (manual, first run)
                flow = Flow.from_client_secrets_file(
                    self.client_secrets_path,     # Uses client_secret.json for app identification
                    scopes=self.SCOPES,           # Requests the necessary Gmail permissions
                    redirect_uri='http://localhost:8000/auth/callback' # Redirect URI for web server (must match Google Cloud config)
                )
                # In production, you may automate or expose the flow differently;
                # here, we explicitly block and raise for manual handling.
                raise Exception("Manual OAuth flow required: Run this locally in an interactive environment.")

        # 3. Save any updated/obtained tokens to disk for future reuse
        with open(self.token_path, 'w') as token:
            token.write(creds.to_json())

        return creds

    def get_gmail_service(self):
        """
        Builds an authorized Gmail API client instance, ready to make authenticated API calls.

        Returns:
            googleapiclient.discovery.Resource: Gmail API client object
        """
        credentials = self.get_credentials()    # Ensures we have valid, refreshed credentials
        return build('gmail', 'v1', credentials=credentials)  # Constructs Gmail service client, ready for use

    def get_authorization_url(self, redirect_uri: str = 'http://localhost:8000/auth/callback'):
        """
        Get OAuth2 authorization URL for web-based flows.

        Args:
            redirect_uri: Where Google should redirect after user consent

        Returns:
            tuple: (authorization_url, state) for the OAuth flow
        """
        flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Enable refresh tokens
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to get refresh token
        )

        return authorization_url, state

    def exchange_code_for_tokens(self, code: str, state: str, redirect_uri: str = 'http://localhost:8000/auth/callback'):
        """
        Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code from Google
            state: State parameter for security
            redirect_uri: Must match the one used in get_authorization_url

        Returns:
            google.oauth2.credentials.Credentials: The obtained credentials

        Raises:
            Exception: If no refresh token received or other OAuth errors
        """
        flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Check if we got a refresh token
        if not credentials.refresh_token:
            raise Exception("No refresh token received. User may have already authorized this app. Please revoke permissions and try again.")

        # Save tokens to file
        with open(self.token_path, 'w') as token_file:
            token_file.write(credentials.to_json())

        return credentials
