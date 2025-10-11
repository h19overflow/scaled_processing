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

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends

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


router = APIRouter(prefix="/api/v1", tags=["Document Processing"])
logger = logging.getLogger(__name__)



@router.post("/process", response_model=ProcessResponse)
async def process_document_sync(
    file: UploadFile = File(...),
    kafka_producer: ProducerHandler = Depends(get_kafka_producer),
    db_manager: ConnectionManager = Depends(get_db_manager)
):
    """
    Process document synchronously.

    Uploads file, publishes to Kafka, waits for completion (max 120s).
    Returns extracted bill data or timeout/error.

    Args:
        file: Uploaded document file (PDF/image)
        kafka_producer: Kafka message producer
        db_manager: Database connection manager

    Returns:
        ProcessResponse with bill data or error

    Raises:
        HTTPException: For validation errors, timeouts, or processing failures
    """
    logger.info(f"Received sync processing request for: {file.filename}")

    # Validate file
    validation_error = await _validate_file(file)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    # Generate job ID and save file
    job_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    saved_filename = f"{job_id}{file_extension}"
    file_path = UPLOAD_DIR / saved_filename

    try:
        # Save uploaded file
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved to: {file_path}")

        # Create job in tracker

        # Create metadata matching file_watcher structure
        file_stat = os.stat(file_path)
        metadata = {
            "file_path": str(file_path.absolute()),
            "file_name": file.filename,
            "file_size": file_stat.st_size,
            "file_extension": file_path.suffix.lower(),
            "created_time": file_stat.st_ctime
        }

        # Create standardized message
        message = create_message("file_detected", metadata, "api_upload")

        # Publish to Kafka (key is file_name, not job_id)
        success = kafka_producer.produce_message(
            topic="file_detected",
            key=metadata["file_name"],
            value=message
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to publish message to Kafka")

        logger.info(f"Published message to Kafka for job: {job_id}")

        # Wait for completion (with timeout)
        bill_data = await _wait_for_completion(job_id, db_manager, file.filename)

        return ProcessResponse(
            status="completed",
            document_name=file.filename,
            job_id=job_id,
            bill_data=bill_data,
            error=None,
            processed_at=datetime.utcnow()
        )

    except asyncio.TimeoutError:
        logger.warning(f"Processing timeout for job: {job_id}")
        return ProcessResponse(
            status="processing",
            document_name=file.filename,
            job_id=job_id,
            bill_data=None,
            error="Processing timeout - job still running. Use job_id to check status.",
            processed_at=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Processing error for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process/async", response_model=AsyncProcessResponse)
async def process_document_async(
    file: UploadFile = File(...),
    kafka_producer: ProducerHandler = Depends(get_kafka_producer)
):
    """
    Process document asynchronously.

    Uploads file, publishes to Kafka, returns job ID immediately.
    Client polls /status/{job_id} for completion.

    Args:
        file: Uploaded document file (PDF/image)
        kafka_producer: Kafka message producer

    Returns:
        AsyncProcessResponse with job_id

    Raises:
        HTTPException: For validation errors or Kafka failures
    """
    logger.info(f"Received async processing request for: {file.filename}")

    # Validate file
    validation_error = await _validate_file(file)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    # Generate job ID and save file
    job_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    saved_filename = f"{job_id}{file_extension}"
    file_path = UPLOAD_DIR / saved_filename

    try:
        # Save uploaded file
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved to: {file_path}")

        # Create job in tracker

        # Create metadata matching file_watcher structure
        file_stat = os.stat(file_path)
        metadata = {
            "file_path": str(file_path.absolute()),
            "file_name": file.filename,
            "file_size": file_stat.st_size,
            "file_extension": file_path.suffix.lower(),
            "created_time": file_stat.st_ctime
        }

        # Create standardized message
        message = create_message("file_detected", metadata, "api_upload")

        # Publish to Kafka (key is file_name, not job_id)
        success = kafka_producer.produce_message(
            topic="file_detected",
            key=metadata["file_name"],
            value=message
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to publish message to Kafka")

        logger.info(f"Published message to Kafka for job: {job_id}")

        return AsyncProcessResponse(
            job_id=job_id,
            status="queued",
            message=f"Document queued for processing. Use GET /api/v1/status/{job_id} to check progress."
        )

    except Exception as e:
        logger.error(f"Error queuing job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")


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

    job = db_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # If completed, try to fetch bill data from database
    bill_data = None
    if job.status == "completed" and not job.bill_data:
        bill_data = await _fetch_bill_data(job.document_name, db_manager)
        if bill_data:
            job.bill_data = bill_data

    return StatusResponse(
        job_id=job_id,
        status=job.status,
        document_name=job.document_name,
        bill_data=job.bill_data,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


