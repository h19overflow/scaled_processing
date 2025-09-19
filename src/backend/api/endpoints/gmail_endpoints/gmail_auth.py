"""
Gmail authentication endpoints router.

Handles OAuth2 flow for Gmail API access:
- /auth/login: Start OAuth2 flow, redirect to Google
- /auth/callback: Handle OAuth2 callback, exchange code for tokens
- /auth/status: Check authentication status

Dependencies: GmailAuthManager for token management
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse

from src.backend.api.dependencies import (
    get_auth_manager,
    get_optional_gmail_service
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Gmail Authentication"])

# Global state for OAuth flow (in production, use proper session management)
oauth_state = None


@router.get("/login")
async def auth_login(auth_manager=Depends(get_auth_manager)):
    """Start OAuth2 flow - redirect user to Google for consent."""
    global oauth_state
    try:
        # Use the auth manager's method - no code duplication!
        authorization_url, state = auth_manager.get_authorization_url()

        # Store state for verification
        oauth_state = state

        return RedirectResponse(url=authorization_url)

    except Exception as e:
        logger.error(f"OAuth login failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth setup failed: {e}")

# This has to be defined in the GCP, to handle the callback
@router.get("/callback")
async def auth_callback(
    code: str,
    state: str,
    request: Request,
    auth_manager=Depends(get_auth_manager)
):
    """Handle OAuth2 callback - exchange code for tokens."""
    global oauth_state
    try:
        # Verify state parameter (basic security check)
        if state != oauth_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Use the auth manager's method - no code duplication!
        credentials = auth_manager.exchange_code_for_tokens(code, state)

        logger.info(f"Received tokens - Access token: {'✓' if credentials.token else '✗'}, Refresh token: {'✓' if credentials.refresh_token else '✗'}")

        # Initialize gmail service now that we have tokens
        if not request.app.state.gmail_service:
            from src.backend.doc_processing_system.services.gmail_email_listener.cloud.gmail_service import GmailService
            new_service = GmailService(auth_manager)
            request.app.state.gmail_service = new_service

            # Setup Gmail watch
            from src.backend.api.main import setup_gmail_watch
            await setup_gmail_watch(request.app)

        logger.info("OAuth2 flow completed successfully")
        return {"message": "Authentication successful! Gmail monitoring is now active."}

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")


@router.get("/status")
async def auth_status(
    gmail_service=Depends(get_optional_gmail_service)
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