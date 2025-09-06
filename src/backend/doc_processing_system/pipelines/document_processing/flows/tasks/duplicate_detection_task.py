"""
Duplicate detection task for document processing flow.
"""

from pathlib import Path
from typing import Dict, Any

from prefect import task, get_run_logger

from ...chonkie_processor import ChonkieProcessor


@task(name="duplicate-detection", retries=2)
def duplicate_detection_task(raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Check for duplicate documents using content hash.
    
    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        
    Returns:
        Dict containing duplicate check results
    """
    logger = get_run_logger()
    logger.info(f"🔍 Starting duplicate detection for: {Path(raw_file_path).name}")
    
    try:
        # Initialize a processor without vision for a fast duplicate check
        processor = ChonkieProcessor(enable_vision=False)
        output_manager = processor.get_output_manager()
        
        # Only check for duplicates, don't do the full processing
        raw_path = Path(raw_file_path)
        is_duplicate, existing_doc_id = output_manager.document_crud.check_duplicate_by_raw_file(str(raw_path))
        
        if is_duplicate:
            logger.info(f"📋 Document is duplicate: {existing_doc_id}")
            return {
                "status": "duplicate",
                "document_id": existing_doc_id,
                "message": f"Document already processed: {existing_doc_id}"
            }
        else:
            # Generate safe document ID for new document
            document_id = output_manager._generate_document_id(raw_path)
            logger.info(f"✅ Document is new, ready for processing: {document_id}")
            return {
                "status": "ready_for_processing",
                "document_id": document_id,
                "message": f"Document ready for processing: {document_id}"
            }
        
    except Exception as e:
        logger.error(f"❌ Duplicate detection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Duplicate detection failed: {e}"
        }