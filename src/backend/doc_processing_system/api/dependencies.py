"""
API dependencies for dependency injection.

Provides clean access to app services without global variables.
Used by routers to get Gmail services, auth managers, etc.
"""

from fastapi import Depends, HTTPException, Request
from src.backend.doc_processing_system.services.gmail_email_listener.gmail_service import GmailService
from src.backend.doc_processing_system.services.gmail_email_listener.gmail_auth_manager import GmailAuthManager


def get_app_request(request: Request) -> Request:
    """Get the current request object (gives access to app.state)."""
    return request


def get_auth_manager(request: Request = Depends(get_app_request)) -> GmailAuthManager:
    """Get the Gmail auth manager from app state."""
    auth_manager = getattr(request.app.state, 'auth_manager', None)
    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Auth manager not initialized. Check server configuration."
        )
    return auth_manager


def get_gmail_service(request: Request = Depends(get_app_request)) -> GmailService:
    """Get the Gmail service from app state."""
    gmail_service = getattr(request.app.state, 'gmail_service', None)
    if not gmail_service:
        raise HTTPException(
            status_code=503,
            detail="Gmail service not initialized. Use /auth/login to authenticate first."
        )
    return gmail_service


def get_optional_gmail_service(request: Request = Depends(get_app_request)) -> GmailService | None:
    """Get Gmail service if available, None if not (no error thrown)."""
    return getattr(request.app.state, 'gmail_service', None)


def increment_request_count(request: Request = Depends(get_app_request)) -> None:
    """Increment the request counter for basic metrics."""
    current_count = getattr(request.app.state, 'request_count', 0)
    request.app.state.request_count = current_count + 1