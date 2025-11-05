from pathlib import Path
from typing import Dict, Any, Optional, cast

from src.backend.doc_processing_system.pipelines.document_processing.tasks_core.pdf_validation_tasks import (
    cleanup_pdf_processing_temp,
)
from src.backend.doc_processing_system.pipelines.document_processing.flows.utils import (
    get_markdown_path_for_processing,
    handle_duplicate_detection,
    handle_pdf_processing,
    handle_document_extraction,
    handle_chunking_disabled,
    handle_document_saving_and_completion,
    logger,
)


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
        duplicate_result = await handle_duplicate_detection(raw_file_path)

        if duplicate_result["status"] in ("duplicate", "error"):
            return duplicate_result

        document_id_result = duplicate_result["document_id"]
        document_id = cast(str, document_id_result)  # Safe cast after validation

        # STEP 2: PDF Validation and Repair
        final_file_path, pdf_processing_steps = await handle_pdf_processing(
            raw_file_path,
            document_id,
            enable_pdf_validation,
            force_pdf_repair,
        )

        # STEP 3: Document Extraction
        docling_result = await handle_document_extraction(final_file_path, document_id)

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
            return await handle_chunking_disabled(
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
        return await handle_document_saving_and_completion(
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
