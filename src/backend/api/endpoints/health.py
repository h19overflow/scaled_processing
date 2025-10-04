"""
Health check and monitoring endpoints.

Simple endpoints to check if the API is running and get basic metrics.
Used by load balancers, monitoring tools, and for debugging.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel


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


@router.get("/health/ready")
async def readiness_check(
    request: Request
):
    """Readiness check - is the API ready to serve requests?"""
    # Check if critical components are initialized
    auth_manager_ready = hasattr(request.app.state, 'auth_manager') and request.app.state.auth_manager is not None

    if auth_manager_ready:
        return {"status": "ready", "message": "API is ready to serve requests"}
    else:
        return {"status": "not_ready", "message": "API is starting up"}, 503


@router.get("/health/live")
async def liveness_check():
    """Liveness check - is the API process alive?"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc)}
