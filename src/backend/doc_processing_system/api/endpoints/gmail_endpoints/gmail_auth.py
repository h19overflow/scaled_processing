"""
Gmail authentication endpoints router.

Handles OAuth2 flow for Gmail API access:
- /auth/login: Start OAuth2 flow, redirect to Google
- /auth/callback: Handle OAuth2 callback, exchange code for tokens
- /auth/status: Check authentication status

Dependencies: GmailAuthManager for token management
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

from src.backend.doc_processing_system.api.dependencies import (
    get_auth_manager,
    get_optional_gmail_service,
    increment_request_count
)

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Gmail Authentication"])

# Global state for OAuth flow (in production, use proper session management)
oauth_state = None


@router.get("/login")
async def auth_login(_: None = Depends(increment_request_count)):
    """Start OAuth2 flow - redirect user to Google for consent."""
    global oauth_state
    try:
        client_secrets_path = os.getenv("GMAIL_CLIENT_SECRETS_PATH")
        if not client_secrets_path:
            raise HTTPException(status_code=500, detail="GMAIL_CLIENT_SECRETS_PATH not configured")

        # Create OAuth2 flow
        flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ],
            redirect_uri='http://localhost:8000/auth/callback'
        )

        # Get authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Enable refresh tokens
            include_granted_scopes='true'
        )

        # Store state for verification
        oauth_state = state

        return RedirectResponse(url=authorization_url)

    except Exception as e:
        logger.error(f"OAuth login failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth setup failed: {e}")


@router.get("/callback")
async def auth_callback(
    code: str,
    state: str,
    request: Request,
    auth_manager=Depends(get_auth_manager),
    _: None = Depends(increment_request_count)
):
    """Handle OAuth2 callback - exchange code for tokens."""
    global oauth_state
    try:
        # Verify state parameter (basic security check)
        if state != oauth_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        client_secrets_path = os.getenv("GMAIL_CLIENT_SECRETS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")

        if not client_secrets_path or not token_path:
            raise HTTPException(status_code=500, detail="OAuth paths not configured")

        # Create flow and fetch tokens
        flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ],
            redirect_uri='http://localhost:8000/auth/callback'
        )

        # Exchange authorization code for tokens
        flow.fetch_token(code=code)

        # Save tokens to file
        credentials = flow.credentials
        with open(token_path, 'w') as token_file:
            token_file.write(credentials.to_json())

        # Initialize gmail service now that we have tokens
        if not request.app.state.gmail_service:
            from src.backend.doc_processing_system.services.gmail_email_listener.gmail_service import GmailService
            new_service = GmailService(auth_manager)
            request.app.state.gmail_service = new_service

            # Setup Gmail watch
            from src.backend.doc_processing_system.api.main import setup_gmail_watch
            await setup_gmail_watch(request.app)

        logger.info("OAuth2 flow completed successfully")
        return {"message": "Authentication successful! Gmail monitoring is now active."}

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")


@router.get("/status")
async def auth_status(
    gmail_service=Depends(get_optional_gmail_service),
    _: None = Depends(increment_request_count)
):
    """Check if Gmail authentication is configured."""
    token_path = os.getenv("GMAIL_TOKEN_PATH")

    if token_path and os.path.exists(token_path):
        return {
            "authenticated": True,
            "message": "Gmail tokens found",
            "gmail_service_active": gmail_service is not None,
            "token_file": token_path
        }
    else:
        return {
            "authenticated": False,
            "message": "No Gmail tokens found. Use /auth/login to authenticate.",
            "gmail_service_active": False,
            "login_url": "/auth/login"
        }