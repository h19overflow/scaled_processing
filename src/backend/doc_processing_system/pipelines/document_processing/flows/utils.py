from typing import Dict, Any, Optional, Tuple
from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from logging import getLogger
from pathlib import Path
from src.backend.doc_processing_system.messaging.message_utils import create_message
from datetime import datetime
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import (
    duplicate_detection_task,
    document_processing_task,
    document_saving_task,
)
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core.pdf_validation_tasks import (
    validate_pdf_task,
    repair_pdf_task,
    clean_with_pymupdf_task,
    cleanup_pdf_processing_temp,
)

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
    job_id: Optional[str] = None,
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


async def handle_duplicate_detection(raw_file_path: str) -> Dict[str, Any]:
    """
    Check if document is a duplicate.

    Returns:
        Dict with status ('duplicate', 'new', or 'error'), document_id, and optional message.
    """
    logger.info(f"🔍 STEP 1: Duplicate Detection for {Path(raw_file_path).name}")
    duplicate_result = duplicate_detection_task(raw_file_path)

    if duplicate_result["status"] == "duplicate":
        logger.warning(f"⚠️ Document is duplicate: {duplicate_result['document_id']}")

    return duplicate_result


async def handle_pdf_processing(
    raw_file_path: str,
    document_id: str,
    enable_pdf_validation: bool,
    force_pdf_repair: bool,
) -> Tuple[str, Dict[str, str]]:
    """
    Process PDF validation and repair if needed.

    Args:
        raw_file_path: Path to the document file
        document_id: ID of the document
        enable_pdf_validation: Whether to validate PDFs
        force_pdf_repair: Force PDF repair regardless of validation result

    Returns:
        Tuple of (final_file_path, pdf_processing_steps)
    """
    final_file_path = raw_file_path
    pdf_processing_steps = {}

    if not raw_file_path.lower().endswith(".pdf") or not enable_pdf_validation:
        logger.info("⏭️ STEP 2 SKIPPED: Not a PDF or validation disabled")
        return final_file_path, pdf_processing_steps

    logger.info(f"🔍 STEP 2A: PDF Validation for {document_id}")
    validation_result = validate_pdf_task(raw_file_path)
    pdf_processing_steps["validation"] = validation_result["status"]

    needs_repair = validation_result["needs_repair"] or force_pdf_repair

    if needs_repair and validation_result["status"] != "error":
        final_file_path = repair_and_clean_pdf(
            raw_file_path,
            document_id,
            pdf_processing_steps,
        )
    else:
        logger.info("✅ PDF validation passed, no repair needed")

    return final_file_path, pdf_processing_steps


def repair_and_clean_pdf(
    raw_file_path: str,
    document_id: str,
    pdf_processing_steps: Dict[str, str],
) -> str:
    """
    Repair and clean a PDF file.

    Args:
        raw_file_path: Path to the original PDF
        document_id: ID of the document
        pdf_processing_steps: Dict to store processing step results

    Returns:
        Path to the final cleaned/repaired PDF, or original path if repair failed
    """
    logger.info(f"🔧 STEP 2B: PDF Repair for {document_id}")
    repair_result = repair_pdf_task(raw_file_path)
    pdf_processing_steps["repair"] = repair_result["status"]

    if repair_result["status"] != "repaired":
        logger.warning("⚠️ PDF repair failed, using original file")
        return raw_file_path

    repaired_path = repair_result["repaired_path"]

    logger.info(f"🧹 STEP 2C: PDF Cleaning for {document_id}")
    clean_result = clean_with_pymupdf_task(repaired_path)
    pdf_processing_steps["cleaning"] = clean_result["status"]

    if clean_result["status"] == "cleaned":
        final_path = clean_result["clean_path"]
        logger.info(f"✅ Using cleaned PDF: {Path(final_path).name}")
        return final_path
    else:
        logger.info(f"✅ Using repaired PDF: {Path(repaired_path).name}")
        return repaired_path


async def handle_document_extraction(
    final_file_path: str,
    document_id: str,
) -> Dict[str, Any]:
    """
    Extract document content using MinerU/Docling.

    Args:
        final_file_path: Path to the document to process
        document_id: ID of the document

    Returns:
        Dict with extraction results including status and file_info
    """
    logger.info(f"📄 STEP 3: Starting document processing for {document_id}")
    docling_result = document_processing_task(final_file_path, document_id)
    logger.info(
        f"✅ STEP 3 COMPLETE: Document processing - Status: {docling_result.get('status')}"
    )
    return docling_result


async def handle_chunking_disabled(
    document_id: str,
    duplicate_result: Dict[str, Any],
    pdf_processing_steps: Dict[str, str],
    docling_result: Dict[str, Any],
    content: str,
    raw_file_path: str,
    user_id: str,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle early return when chunking is disabled.

    Returns:
        Completion result with status and processing steps
    """
    logger.info("⏭️ STEP 4 SKIPPED: Chunking disabled - preparing early return")

    processing_steps = {
        "duplicate_detection": duplicate_result.get("status"),
        "pdf_processing": pdf_processing_steps,
        "document_extraction": docling_result.get("status"),
        "chunking": "disabled",
        "document_saving": "disabled",
    }

    cleanup_pdf_processing_temp(document_id)
    send_completion_message(
        document_id, raw_file_path, user_id, processing_steps, content, job_id
    )

    return {
        "status": "completed",
        "document_id": document_id,
        "chunking_result": {
            "status": "disabled",
            "message": "Chunking disabled",
        },
        "processing_steps": processing_steps,
    }


async def handle_document_saving_and_completion(
    markdown_path: str,
    document_id: str,
    raw_file_path: str,
    user_id: str,
    duplicate_result: Dict[str, Any],
    pdf_processing_steps: Dict[str, str],
    docling_result: Dict[str, Any],
    content: str,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save document metadata and send completion message.

    Returns:
        Completion result with status and processing steps
    """
    content_length = len(content)
    page_count = docling_result["file_info"]["page_count"]

    logger.info("🔄 STEP 5: Saving document metadata...")
    save_result = document_saving_task(
        markdown_path=markdown_path,
        document_id=document_id,
        content_length=content_length,
        page_count=page_count,
        raw_file_path=raw_file_path,
        user_id=user_id,
    )

    if save_result.get("save_result", {}).get("status") != "saved":
        cleanup_pdf_processing_temp(document_id)
        return save_result

    processing_steps = {
        "duplicate_detection": duplicate_result.get("status"),
        "pdf_processing": pdf_processing_steps,
        "document_extraction": docling_result.get("status"),
        "document_saving": save_result.get("save_result", {}).get("status"),
    }

    cleanup_pdf_processing_temp(document_id)
    send_completion_message(
        document_id, raw_file_path, user_id, processing_steps, content, job_id
    )

    return {
        "status": "completed",
        "document_id": document_id,
        "processing_steps": processing_steps,
    }
