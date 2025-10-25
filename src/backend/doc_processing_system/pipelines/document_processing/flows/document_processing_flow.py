from pathlib import Path
from typing import Dict, Any, Optional, Tuple, cast

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
from src.backend.doc_processing_system.pipelines.document_processing.flows.utils import (
    get_markdown_path_for_processing,
    send_completion_message,
    logger,
)


async def _handle_duplicate_detection(raw_file_path: str) -> Dict[str, Any]:
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


async def _handle_pdf_processing(
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
        final_file_path = _repair_and_clean_pdf(
            raw_file_path,
            document_id,
            pdf_processing_steps,
        )
    else:
        logger.info("✅ PDF validation passed, no repair needed")

    return final_file_path, pdf_processing_steps


def _repair_and_clean_pdf(
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


async def _handle_document_extraction(
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


async def _handle_chunking_disabled(
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


async def _handle_document_saving_and_completion(
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


async def process_document_with_flow(
    raw_file_path: str,
    user_id: str = "default",
    enable_chunking: bool = True,
    enable_pdf_validation: bool = True,
    force_pdf_repair: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orchestrate document processing flow.

    Coordinates duplicate detection, PDF validation, document extraction,
    saving, and cleanup across the entire pipeline.

    Args:
        raw_file_path: Path to document file to process
        user_id: User ID for document ownership
        enable_chunking: Whether to save document chunks
        enable_pdf_validation: Whether to validate/repair PDFs
        force_pdf_repair: Force PDF repair regardless of validation
        job_id: Optional job ID for tracking

    Returns:
        Dict with status ('completed', 'duplicate', or 'error') and processing details
    """
    logger.info(f"🚀 Starting document processing flow for: {Path(raw_file_path).name}")

    document_id_result: Optional[str] = None

    try:
        # STEP 1: Duplicate Detection
        duplicate_result = await _handle_duplicate_detection(raw_file_path)

        if duplicate_result["status"] in ("duplicate", "error"):
            return duplicate_result

        document_id_result = duplicate_result["document_id"]
        document_id = cast(str, document_id_result)  # Safe cast after validation

        # STEP 2: PDF Validation and Repair
        final_file_path, pdf_processing_steps = await _handle_pdf_processing(
            raw_file_path,
            document_id,
            enable_pdf_validation,
            force_pdf_repair,
        )

        # STEP 3: Document Extraction
        docling_result = await _handle_document_extraction(final_file_path, document_id)

        if docling_result["status"] != "completed":
            cleanup_pdf_processing_temp(document_id)
            return docling_result

        # Read extracted content
        markdown_path = get_markdown_path_for_processing(docling_result)
        content_path = Path(markdown_path)
        with open(content_path, "r", encoding="utf-8") as f:
            content = f.read()

        # STEP 4: Check if chunking is enabled
        logger.info(f"🔄 STEP 4: Checking chunking enabled: {enable_chunking}")
        if not enable_chunking:
            return await _handle_chunking_disabled(
                document_id,
                duplicate_result,
                pdf_processing_steps,
                docling_result,
                content,
                raw_file_path,
                user_id,
                job_id,
            )

        # STEP 5: Save document metadata and completion
        return await _handle_document_saving_and_completion(
            markdown_path,
            document_id,
            raw_file_path,
            user_id,
            duplicate_result,
            pdf_processing_steps,
            docling_result,
            content,
            job_id,
        )

    except Exception as e:
        logger.error(f"❌ Document processing flow failed: {e}")

        # Attempt cleanup on error if document_id is available
        if document_id_result:
            try:
                cleanup_pdf_processing_temp(document_id_result)
            except Exception:
                pass

        return {
            "status": "error",
            "error": str(e),
            "message": f"Document processing flow failed: {e}",
        }


if __name__ == "__main__":
    import asyncio

    test_file_path = (
        "C:\\Users\\User\\Projects\\scaled_processing\\data\\invoices\\batch1-0499.jpg"
    )
    result = asyncio.run(
        process_document_with_flow(
            test_file_path, user_id="test_user", enable_chunking=True
        )
    )

