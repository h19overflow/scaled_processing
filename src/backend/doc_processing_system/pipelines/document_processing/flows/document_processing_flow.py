from pathlib import Path
from typing import Dict, Any
import logging

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.messaging.message_schemas import create_message
from datetime import datetime

from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import (
    duplicate_detection_task,
    docling_processing_task,
    document_saving_task,
)
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core.pdf_validation_tasks import (
    validate_pdf_task,
    repair_pdf_task,
    clean_with_pymupdf_task,
    cleanup_pdf_processing_temp,
)


def _get_logger(use_prefect: bool = True):
    """Get appropriate logger based on context."""
    if use_prefect:
        try:
            return get_run_logger()
        except:
            return logging.getLogger(__name__)
    return logging.getLogger(__name__)


def get_markdown_path_for_processing(docling_result: Dict[str, Any]) -> str:
    """
    Get the markdown file path from docling processing result.

    Args:
        docling_result: Result from docling processing task

    Returns:
        Path to the markdown file to use for further processing
    """
    return docling_result["processed_markdown_path"]


def send_completion_message(document_id: str, raw_file_path: str, user_id: str, processing_steps: Dict[str, Any], processed_content: str = "", job_id: str = None, logger = None) -> None:
    """Send document_pipeline_completed message."""
    if logger is None:
        logger = _get_logger(use_prefect=False)

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
            "completed_at": str(datetime.now())
        }

        # Add job_id if provided (for API tracking)
        if job_id:
            metadata["job_id"] = job_id

        # Send completion message (use job_id as key if available)
        kafka_producer = ProducerHandler("localhost:9092")
        message = create_message(event_type="document_pipeline_completed", data=metadata, source="document_processing")
        message_key = job_id if job_id else file_path_obj.name
        result = kafka_producer.produce_message(topic="document_pipeline_completed", key=message_key, value=message)

        if result:
            logger.info(f"✅ Sent document_pipeline_completed message for: {document_id}")

        kafka_producer.close()

    except Exception as e:
        logger.error(f"Failed to send completion message: {e}")


async def _process_document_core(
    raw_file_path: str,
    user_id: str = "default",
    enable_chunking: bool = True,
    enable_pdf_validation: bool = True,
    force_pdf_repair: bool = False,
    job_id: str = None,
    logger = None
) -> Dict[str, Any]:
    """
    Core document processing logic without Prefect orchestration.
    This can be called directly by consumers without triggering Prefect servers.
    """
    if logger is None:
        logger = _get_logger(use_prefect=False)

    logger.info(f"🚀 Starting document processing flow for: {Path(raw_file_path).name}")

    try:
        # STEP 1: Duplicate Detection
        duplicate_result = duplicate_detection_task(raw_file_path)

        if duplicate_result["status"] == "duplicate":
            return {
                "status": "duplicate",
                "document_id": duplicate_result["document_id"],
                "message": f"Document already exists: {duplicate_result['document_id']}"
            }

        if duplicate_result["status"] == "error":
            return duplicate_result

        document_id = duplicate_result["document_id"]

        # STEP 2: PDF Validation and Repair (for PDF files only)
        final_file_path = raw_file_path
        pdf_processing_steps = {}

        if raw_file_path.lower().endswith('.pdf') and enable_pdf_validation:
            logger.info(f"🔍 STEP 2A: PDF Validation for {document_id}")

            validation_result = validate_pdf_task(raw_file_path)
            pdf_processing_steps["validation"] = validation_result["status"]

            needs_repair = validation_result["needs_repair"] or force_pdf_repair

            if needs_repair and validation_result["status"] != "error":
                logger.info(f"🔧 STEP 2B: PDF Repair for {document_id}")
                repair_result = repair_pdf_task(raw_file_path)
                pdf_processing_steps["repair"] = repair_result["status"]

                if repair_result["status"] == "repaired":
                    repaired_path = repair_result["repaired_path"]

                    # STEP 2C: PDF Cleaning with PyMuPDF
                    logger.info(f"🧹 STEP 2C: PDF Cleaning for {document_id}")
                    clean_result = clean_with_pymupdf_task(repaired_path)
                    pdf_processing_steps["cleaning"] = clean_result["status"]

                    if clean_result["status"] == "cleaned":
                        final_file_path = clean_result["clean_path"]
                        logger.info(f"✅ Using cleaned PDF: {Path(final_file_path).name}")
                    else:
                        final_file_path = repaired_path
                        logger.info(f"✅ Using repaired PDF: {Path(final_file_path).name}")
                else:
                    logger.warning(f"⚠️ PDF repair failed, using original file")
            else:
                logger.info(f"✅ PDF validation passed, no repair needed")
        else:
            logger.info(f"⏭️ STEP 2 SKIPPED: Not a PDF or validation disabled")

        # STEP 3: Document Processing (MinerU/Docling)
        logger.info(f"📄 STEP 3: Starting document processing for {document_id}")
        docling_result = docling_processing_task(final_file_path, document_id)
        logger.info(f"✅ STEP 3 COMPLETE: Document processing - Status: {docling_result.get('status')}")
        if docling_result["status"] != "completed":
            # Cleanup temp files before returning error
            cleanup_pdf_processing_temp(document_id)
            return docling_result

        # Get markdown path for processing
        markdown_path = get_markdown_path_for_processing(docling_result)

        # Read content from the markdown file
        content_path = Path(markdown_path)
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get page count and content length from docling result
        page_count = docling_result["file_info"]["page_count"]
        content_length = len(content)

        # Early return if chunking is disabled
        logger.info(f"🔄 STEP 4: Checking chunking enabled: {enable_chunking}")
        if not enable_chunking:
            logger.info(f"⏭️ STEP 4 SKIPPED: Chunking disabled - preparing early return")

            processing_steps = {
                "duplicate_detection": duplicate_result.get("status"),
                "pdf_processing": pdf_processing_steps,
                "document_extraction": docling_result.get("status"),
                "chunking": "disabled",
                "document_saving": "disabled"
            }

            # Cleanup temp files
            cleanup_pdf_processing_temp(document_id)

            # Send completion message with processed content
            send_completion_message(document_id, raw_file_path, user_id, processing_steps, content, job_id, logger)

            return {
                "status": "completed",
                "document_id": document_id,
                "chunking_result": {"status": "disabled", "message": "Chunking disabled"},
                "processing_steps": processing_steps
            }

        logger.info("🔄 STEP 5: Saving document metadata...")
        save_result = document_saving_task(
            vision_enhanced_markdown_path=markdown_path,
            document_id=document_id,
            content_length=content_length,
            page_count=page_count,
            raw_file_path=raw_file_path,
            user_id=user_id
        )
        if save_result.get("save_result", {}).get("status") != "saved":
            # Cleanup temp files before returning error
            cleanup_pdf_processing_temp(document_id)
            return save_result

        processing_steps = {
            "duplicate_detection": duplicate_result.get("status"),
            "pdf_processing": pdf_processing_steps,
            "document_extraction": docling_result.get("status"),
            "document_saving": save_result.get("save_result", {}).get("status")
        }

        # Cleanup temp files after successful processing
        cleanup_pdf_processing_temp(document_id)

        # Send completion message with processed content
        send_completion_message(document_id, raw_file_path, user_id, processing_steps, content, job_id, logger)

        return {
            "status": "completed",
            "document_id": document_id,
            "processing_steps": processing_steps
        }

    except Exception as e:
        logger.error(f"❌ Document processing flow failed: {e}")

        # Attempt cleanup on error if document_id is available
        try:
            if 'document_id' in locals():
                cleanup_pdf_processing_temp(document_id)
        except:
            pass

        return {
            "status": "error",
            "error": str(e),
            "message": f"Document processing flow failed: {e}"
        }


@flow(
    name="invoice-processing-pipeline",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
    retries=1,
    retry_delay_seconds=10
)
async def document_processing_flow(
    raw_file_path: str,
    user_id: str = "default",
    enable_chunking: bool = True,
    enable_pdf_validation: bool = True,
    force_pdf_repair: bool = False,
    job_id: str = None
) -> Dict[str, Any]:
    """Prefect flow wrapper for document processing."""
    logger = get_run_logger()
    return await _process_document_core(
        raw_file_path=raw_file_path,
        user_id=user_id,
        enable_chunking=enable_chunking,
        enable_pdf_validation=enable_pdf_validation,
        force_pdf_repair=force_pdf_repair,
        job_id=job_id,
        logger=logger
    )


async def process_document_with_flow(
    raw_file_path: str,
    user_id: str = "default",
    enable_chunking: bool = True,
    enable_pdf_validation: bool = True,
    force_pdf_repair: bool = False,
    job_id: str = None
) -> Dict[str, Any]:
    """
    Process document without Prefect orchestration.
    This function is used by consumers to avoid triggering Prefect servers.
    """
    return await _process_document_core(
        raw_file_path=raw_file_path,
        user_id=user_id,
        enable_chunking=enable_chunking,
        enable_pdf_validation=enable_pdf_validation,
        force_pdf_repair=force_pdf_repair,
        job_id=job_id,
        logger=None  # Will use standard logging
    )

if __name__ == "__main__":
    import asyncio
    test_file_path = "C:\\Users\\User\\Projects\\scaled_processing\\data\\invoices\\batch1-0499.jpg"
    result = asyncio.run(process_document_with_flow(test_file_path, user_id="test_user", enable_chunking=True))
