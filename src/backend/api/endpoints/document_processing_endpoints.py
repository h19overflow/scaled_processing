"""
Document processing API endpoints.

Provides REST API for uploading and processing Malaysian utility bills.
Integrates with Kafka-based document processing pipeline.
"""
# TODO , processing times out need to figure out how to handle it 
import os
import uuid
import asyncio
import shutil
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
from src.backend.doc_processing_system.core_deps.database.models import JobModel
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends, Response

from src.backend.api.schemas import (
    ProcessResponse,
    AsyncProcessResponse,
    StatusResponse
)
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.messaging.message_schemas import create_message
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
from src.backend.doc_processing_system.core_deps.database.models import BillModel
from src.backend.api.endpoints.utils import _validate_file, _wait_for_completion, _fetch_bill_data, get_kafka_producer, get_db_manager,UPLOAD_DIR,logger
from src.backend.doc_processing_system.core_deps.database.CRUD.job_CRUD import JobCRUD

router = APIRouter(prefix="/document_processing", tags=["Document Processing"])


@router.post("/process/async", response_model=AsyncProcessResponse, status_code=202)
async def process_document_async(
    response: Response,
    file: UploadFile = File(...),
    kafka_producer: ProducerHandler = Depends(get_kafka_producer),
    db_manager: ConnectionManager = Depends(get_db_manager)
):
    """
    Process document asynchronously.

    Uploads file, creates job record, publishes to Kafka, returns job ID immediately.
    Client polls /status/{job_id} for completion every 5 seconds (see Retry-After header).

    Args:
        file: Uploaded document file (PDF/image)
        kafka_producer: Kafka message producer
        db_manager: Database connection manager

    Returns:
        AsyncProcessResponse with job_id (HTTP 202 Accepted)

    Raises:
        HTTPException: For validation errors or Kafka failures
    """
    logger.info(f"Received async processing request for: {file.filename}")

    # Validate file
    validation_error = await _validate_file(file)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    # Generate job ID and save file
    saved_filename = f"{file.filename}"
    file_path = UPLOAD_DIR / saved_filename
    job_created = None

    try:
        # Save uploaded file
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved to: {file_path}")
        # Create job record in database
        job_created, success = JobCRUD(db_manager).create_job(
            document_name=file.filename,
            file_path=str(file_path.absolute())
        )
        response.headers["Retry-After"] = "5"

        if not success:
            raise HTTPException(status_code=500, detail="Failed to create job record")
        return AsyncProcessResponse(
            job_id=job_created[0],
            status="queued",
            message=f"Document queued for processing. Poll GET /api/v1/status/{job_created[0]} every 5 seconds."
        )

    except Exception as e:
        job_id_str = f" {job_created[0]}" if job_created else ""
        logger.error(f"Error queuing job{job_id_str}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")

# TODO , Setup up tracking such that we can use it to fetch the bill when it's done 
@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_job_status(
    job_id: str,
    db_manager: ConnectionManager = Depends(get_db_manager)
):
    """
    Check processing status and retrieve results.

    Args:
        job_id: Job identifier from async processing request
        db_manager: Database connection manager

    Returns:
        StatusResponse with current status and results if completed

    Raises:
        HTTPException: If job not found
    """
    logger.info(f"Status check for job: {job_id}")

    job = JobCRUD(db_manager).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # If completed, try to fetch bill data from database
    bill_data = None
    if job.get("status") == "completed" and not job.get("bill_data"):
        bill_data = await _fetch_bill_data(job.get("document_name"), db_manager)
        if bill_data:
            job.get("bill_data") == bill_data
            job.get("status") == "completed"

    return StatusResponse(
        job_id=job_id,
        status=job.get("status"),
        document_name=job.get("document_name"),
        bill_data=job.get("bill_data"),
        error=job.get("error"),
        created_at=job.get("created_at"),
        completed_at=job.get("completed_at")    
    )


