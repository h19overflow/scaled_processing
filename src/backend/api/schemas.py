"""
Pydantic schemas for API request/response models.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ProcessResponse(BaseModel):
    """Response model for document processing."""
    status: str = Field(..., description="Processing status: completed, failed, processing")
    document_name: str = Field(..., description="Name of processed document")
    job_id: Optional[str] = Field(None, description="Job ID for async tracking")
    bill_data: Optional[Dict[str, Any]] = Field(None, description="Extracted bill data")
    error: Optional[str] = Field(None, description="Error message if failed")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class AsyncProcessResponse(BaseModel):
    """Response model for async document processing."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial status: queued")
    message: str = Field(..., description="Status message")


class StatusResponse(BaseModel):
    """Response model for job status check."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current status: queued, processing, completed, failed")
    document_name: Optional[str] = Field(None, description="Document name")
    bill_data: Optional[Dict[str, Any]] = Field(None, description="Extracted bill data if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(..., description="Status of dependent services")
    version: str = Field(default="1.0.0", description="API version")
