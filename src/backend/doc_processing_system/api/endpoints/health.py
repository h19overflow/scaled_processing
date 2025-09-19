"""
Health check and monitoring endpoints.

Simple endpoints to check if the API is running and get basic metrics.
Used by load balancers, monitoring tools, and for debugging.
"""

import time
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.backend.doc_processing_system.api.dependencies import (
    get_optional_gmail_service,
    increment_request_count
)

router = APIRouter(tags=["Health & Monitoring"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    services: dict


class MetricsResponse(BaseModel):
    """Basic metrics response."""
    total_requests: int
    uptime_seconds: float
    services_status: dict
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    gmail_service=Depends(get_optional_gmail_service),
    _: None = Depends(increment_request_count)
):
    """Basic health check - is the API running?"""
    current_time = time.time()
    startup_time = getattr(request.app.state, 'startup_time', current_time)
    uptime = current_time - startup_time

    # Check service status
    services = {
        "gmail_service": gmail_service is not None,
        "auth_manager": hasattr(request.app.state, 'auth_manager') and request.app.state.auth_manager is not None
    }

    # Overall status
    all_critical_services_up = services["auth_manager"]  # Auth manager is critical
    status = "healthy" if all_critical_services_up else "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime,
        services=services
    )


@router.get("/health/ready")
async def readiness_check(
    request: Request,
    _: None = Depends(increment_request_count)
):
    """Readiness check - is the API ready to serve requests?"""
    # Check if critical components are initialized
    auth_manager_ready = hasattr(request.app.state, 'auth_manager') and request.app.state.auth_manager is not None

    if auth_manager_ready:
        return {"status": "ready", "message": "API is ready to serve requests"}
    else:
        return {"status": "not_ready", "message": "API is starting up"}, 503


@router.get("/health/live")
async def liveness_check(_: None = Depends(increment_request_count)):
    """Liveness check - is the API process alive?"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc)}


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    request: Request,
    gmail_service=Depends(get_optional_gmail_service),
    _: None = Depends(increment_request_count)
):
    """Get basic API metrics."""
    current_time = time.time()
    startup_time = getattr(request.app.state, 'startup_time', current_time)
    uptime = current_time - startup_time

    # Get request count
    total_requests = getattr(request.app.state, 'request_count', 0)

    # Service status
    services_status = {
        "gmail_service_active": gmail_service is not None,
        "auth_manager_active": hasattr(request.app.state, 'auth_manager') and request.app.state.auth_manager is not None
    }

    return MetricsResponse(
        total_requests=total_requests,
        uptime_seconds=uptime,
        services_status=services_status,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/debug/state")
async def debug_app_state(request: Request):
    """Debug endpoint to inspect app state (remove in production)."""
    state_info = {}

    # Get all state attributes safely
    for attr in dir(request.app.state):
        if not attr.startswith('_'):
            try:
                value = getattr(request.app.state, attr)
                # Don't serialize complex objects, just show type
                if hasattr(value, '__class__'):
                    state_info[attr] = f"<{value.__class__.__name__}>"
                else:
                    state_info[attr] = value
            except Exception as e:
                state_info[attr] = f"Error accessing: {e}"

    return {
        "app_state": state_info,
        "environment_check": {
            "GMAIL_CLIENT_SECRETS_PATH": "GMAIL_CLIENT_SECRETS_PATH" in __import__('os').environ,
            "GMAIL_TOKEN_PATH": "GMAIL_TOKEN_PATH" in __import__('os').environ,
            "AUTO_SETUP_GMAIL_WATCH": __import__('os').getenv("AUTO_SETUP_GMAIL_WATCH", "not_set")
        }
    }