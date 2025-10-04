"""
Document processing API endpoints.

Provides REST API for uploading and processing Malaysian utility bills.
Integrates with Kafka-based document processing pipeline.
"""

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
from src.backend.api.job_tracker import JobTracker
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
from src.backend.doc_processing_system.core_deps.database.models import BillModel


router = APIRouter(prefix="/api/v1", tags=["Document Processing"])
logger = logging.getLogger(__name__)


# File upload configuration
UPLOAD_DIR = Path("./data/temp/uploads")
MAX_FILE_SIZE_MB = 50
PROCESSING_TIMEOUT_SECONDS = 120
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def get_job_tracker(request: Request) -> JobTracker:
    """Dependency to get job tracker from app state."""
    return request.app.state.job_tracker


def get_kafka_producer(request: Request) -> ProducerHandler:
    """Dependency to get Kafka producer from app state."""
    return request.app.state.kafka_producer


def get_db_manager(request: Request) -> ConnectionManager:
    """Dependency to get database manager from app state."""
    return request.app.state.db_manager


@router.post("/process", response_model=ProcessResponse)
async def process_document_sync(
    file: UploadFile = File(...),
    job_tracker: JobTracker = Depends(get_job_tracker),
    kafka_producer: ProducerHandler = Depends(get_kafka_producer),
    db_manager: ConnectionManager = Depends(get_db_manager)
):
    """
    Process document synchronously.

    Uploads file, publishes to Kafka, waits for completion (max 120s).
    Returns extracted bill data or timeout/error.

    Args:
        file: Uploaded document file (PDF/image)
        job_tracker: Job tracking service
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
        job_tracker.create_job(job_id, file.filename, str(file_path))

        # Publish to Kafka
        success = kafka_producer.produce_message(
            topic="file_detected",
            key=job_id,
            value={
                "job_id": job_id,
                "file_path": str(file_path.absolute()),
                "filename": file.filename,
                "user_id": "api_user",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to publish message to Kafka")

        logger.info(f"Published message to Kafka for job: {job_id}")

        # Wait for completion (with timeout)
        bill_data = await _wait_for_completion(job_id, job_tracker, db_manager, file.filename)

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
        job_tracker.set_error(job_id, str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process/async", response_model=AsyncProcessResponse)
async def process_document_async(
    file: UploadFile = File(...),
    job_tracker: JobTracker = Depends(get_job_tracker),
    kafka_producer: ProducerHandler = Depends(get_kafka_producer)
):
    """
    Process document asynchronously.

    Uploads file, publishes to Kafka, returns job ID immediately.
    Client polls /status/{job_id} for completion.

    Args:
        file: Uploaded document file (PDF/image)
        job_tracker: Job tracking service
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
        job_tracker.create_job(job_id, file.filename, str(file_path))

        # Publish to Kafka
        success = kafka_producer.produce_message(
            topic="file_detected",
            key=job_id,
            value={
                "job_id": job_id,
                "file_path": str(file_path.absolute()),
                "filename": file.filename,
                "user_id": "api_user",
                "timestamp": datetime.utcnow().isoformat()
            }
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
    job_tracker: JobTracker = Depends(get_job_tracker),
    db_manager: ConnectionManager = Depends(get_db_manager)
):
    """
    Check processing status and retrieve results.

    Args:
        job_id: Job identifier from async processing request
        job_tracker: Job tracking service
        db_manager: Database connection manager

    Returns:
        StatusResponse with current status and results if completed

    Raises:
        HTTPException: If job not found
    """
    logger.info(f"Status check for job: {job_id}")

    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # If completed, try to fetch bill data from database
    bill_data = None
    if job.status == "completed" and not job.bill_data:
        bill_data = await _fetch_bill_data(job.document_name, db_manager)
        if bill_data:
            job_tracker.set_result(job_id, bill_data)
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


# HELPER FUNCTIONS

async def _validate_file(file: UploadFile) -> Optional[str]:
    """
    Validate uploaded file.

    Checks file extension and size limits.

    Args:
        file: Uploaded file

    Returns:
        Error message if validation fails, None otherwise
    """
    # Check extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type: {file_extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return f"File too large: {file_size / 1024 / 1024:.2f}MB. Max: {MAX_FILE_SIZE_MB}MB"

    return None


async def _wait_for_completion(
    job_id: str,
    job_tracker: JobTracker,
    db_manager: ConnectionManager,
    document_name: str,
    timeout: int = PROCESSING_TIMEOUT_SECONDS
) -> dict:
    """
    Wait for job completion with timeout.

    Polls job status and database for completion.

    Args:
        job_id: Job identifier
        job_tracker: Job tracking service
        db_manager: Database connection manager
        document_name: Original filename
        timeout: Maximum wait time in seconds

    Returns:
        Bill data dictionary if completed

    Raises:
        asyncio.TimeoutError: If processing exceeds timeout
        Exception: If processing fails
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            raise asyncio.TimeoutError()

        # Check job tracker status
        job = job_tracker.get_job(job_id)
        if job and job.status == "failed":
            raise Exception(job.error or "Processing failed")

        # Check database for bill data
        bill_data = await _fetch_bill_data(document_name, db_manager)
        if bill_data:
            job_tracker.set_result(job_id, bill_data)
            return bill_data

        # Wait before next poll
        await asyncio.sleep(2)


async def _fetch_bill_data(document_name: str, db_manager: ConnectionManager) -> Optional[dict]:
    """
    Fetch bill data from database.

    Args:
        document_name: Document filename
        db_manager: Database connection manager

    Returns:
        Bill data dictionary if found, None otherwise
    """
    try:
        with db_manager.get_session() as session:
            bill = session.query(BillModel).filter(
                BillModel.document_name == document_name
            ).order_by(BillModel.created_at.desc()).first()

            if bill:
                return bill.to_dict()

    except Exception as e:
        logger.error(f"Error fetching bill data for {document_name}: {e}")

    return None
