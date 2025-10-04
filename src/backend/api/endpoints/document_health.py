"""
Health check endpoints for document processing microservice.

Checks status of Kafka, database, and file system for document processing.
"""

import os
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from src.backend.api.schemas import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def document_processing_health(request: Request):
    """
    Health check for document processing microservice.

    Checks connectivity to Kafka, database, and file system.

    Returns:
        HealthResponse with service status
    """
    services = {}

    # Check Kafka
    try:
        kafka_producer = getattr(request.app.state, 'kafka_producer', None)
        services["kafka"] = "connected" if kafka_producer else "disconnected"
    except Exception:
        services["kafka"] = "disconnected"

    # Check Database
    try:
        db_manager = getattr(request.app.state, 'db_manager', None)
        if db_manager and db_manager.health_check():
            services["database"] = "connected"
        else:
            services["database"] = "disconnected"
    except Exception:
        services["database"] = "disconnected"

    # Check File System
    try:
        upload_dir = "./data/temp/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        services["file_system"] = "accessible" if os.access(upload_dir, os.W_OK) else "inaccessible"
    except Exception:
        services["file_system"] = "inaccessible"

    # Determine overall status
    all_healthy = all(
        status in ("connected", "accessible")
        for status in services.values()
    )
    status = "healthy" if all_healthy else "degraded"
    status_code = 200 if all_healthy else 503

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        services=services,
        version="1.0.0"
    )
