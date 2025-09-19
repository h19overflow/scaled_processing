"""
API dependencies for dependency injection.

Provides clean access to app services without global variables.
Used by routers to get Gmail services, auth managers, etc.
"""

from fastapi import HTTPException, Request
from src.backend.doc_processing_system.services.gmail_email_listener.cloud.gmail_service import GmailService
from src.backend.doc_processing_system.services.gmail_email_listener.cloud.gmail_auth_manager import GmailAuthManager


def get_auth_manager(request: Request) -> GmailAuthManager:
    """Get the Gmail auth manager from app state."""
    auth_manager = getattr(request.app.state, 'auth_manager', None)
    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Auth manager not initialized. Check server configuration."
        )
    return auth_manager


def get_gmail_service(request: Request) -> GmailService:
    """Get the Gmail service from app state."""
    gmail_service = getattr(request.app.state, 'gmail_service', None)
    if not gmail_service:
        raise HTTPException(
            status_code=503,
            detail="Gmail service not initialized. Use /auth/login to authenticate first."
        )
    return gmail_service


def get_optional_gmail_service(request: Request) -> GmailService | None:
    """Get Gmail service if available, None if not (no error thrown)."""
    return getattr(request.app.state, 'gmail_service', None)