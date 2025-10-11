from typing import Optional
from doc_processing_system.messaging.producer import ProducerHandler
from fastapi import Request
from fastapi.datastructures import UploadFile
from pathlib import Path
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager
import asyncio
from src.backend.doc_processing_system.core_deps.database.models import BillModel
import logging
from src.backend.doc_processing_system.core_deps.database.CRUD.job_CRUD import JobCRUD



MAX_FILE_SIZE_MB = 50
PROCESSING_TIMEOUT_SECONDS = 120
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("./data/temp/uploads")


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
    db_manager: ConnectionManager,
    document_name: str,
    timeout: int = PROCESSING_TIMEOUT_SECONDS
) -> dict:
    """
    Wait for job completion with timeout.

    Polls job status and database for completion.

    Args:
        job_id: Job identifier
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
        job = JobCRUD(db_manager).get_job(job_id)
        if job and job.get("status") == "failed":
            raise Exception(job.get("error") or "Processing failed")

        # Check database for bill data
        bill_data = await _fetch_bill_data(document_name, db_manager)
        if bill_data:
            return bill_data

        # Wait before next poll
        await asyncio.sleep(2)

# TODO , Make test cases for this function and check what happens if the bill is not found , or if the bill is found but the data is not in the database
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



def get_kafka_producer(request: Request) -> ProducerHandler:
    """Dependency to get Kafka producer from app state."""
    return request.app.state.kafka_producer


def get_db_manager(request: Request) -> ConnectionManager:
    """Dependency to get database manager from app state."""
    return request.app.state.db_manager

