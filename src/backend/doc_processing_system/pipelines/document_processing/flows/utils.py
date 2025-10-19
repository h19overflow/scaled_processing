from typing import Dict, Any
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from logging import getLogger
from pathlib import Path
from src.backend.doc_processing_system.messaging.message_utils import create_message
from datetime import datetime, timezone

logger = getLogger(__name__)


def get_markdown_path_for_processing(docling_result: Dict[str, Any]) -> str:
    """
    Get the markdown file path from docling processing result.

    Args:
        docling_result: Result from docling processing task

    Returns:
        Path to the markdown file to use for further processing
    """
    return docling_result["processed_markdown_path"]


def send_completion_message(
    document_id: str,
    raw_file_path: str,
    user_id: str,
    processing_steps: Dict[str, Any],
    processed_content: str = "",
    job_id: str = None,
) -> None:
    """Send document_pipeline_completed message."""
    try:
        # Create metadata for completion message
        file_path_obj = Path(raw_file_path)
        metadata = {
            "filename": file_path_obj.name,  # Match the field name from document_saving_task
            "document_id": document_id,
            "user_id": user_id,
            "raw_file_path": raw_file_path,
            "processed_content": processed_content,  # Add the missing processed content
            "processing_steps": processing_steps,
            "completed_at": str(datetime.now()),
        }

        # Add job_id if provided (for API tracking)
        if job_id:
            metadata["job_id"] = job_id

        # Send completion message (use job_id as key if available)
        kafka_producer = ProducerHandler("localhost:9092")
        message = create_message(
            event_type="document_pipeline_completed",
            data=metadata,
            source="document_processing",
        )
        message_key = job_id if job_id else file_path_obj.name
        result = kafka_producer.produce_message(
            topic="document_pipeline_completed", key=message_key, value=message
        )

        if result:
            logger.info(
                f"✅ Sent document_pipeline_completed message for: {document_id}"
            )

        kafka_producer.close()

    except Exception as e:
        logger.error(f"Failed to send completion message: {e}")
