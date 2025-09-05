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
        # Initialize processor without vision for fast duplicate check
        processor = ChonkieProcessor(enable_vision=False)
        output_manager = processor._get_output_manager()
        
        # Check for duplicates
        result = output_manager.check_and_process_document(raw_file_path, user_id)
        
        if result["status"] == "duplicate":
            logger.info(f"📋 Document is duplicate: {result['document_id']}")
        elif result["status"] == "ready_for_processing":
            logger.info(f"✅ Document is new, ready for processing: {result['document_id']}")
        else:
            logger.warning(f"⚠️ Unexpected status: {result['status']}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ Duplicate detection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Duplicate detection failed: {e}"
        }