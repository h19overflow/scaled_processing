"""
Fast duplicate detection task using file hash only (no embedding models).
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, Any

from prefect import task, get_run_logger

from src.backend.doc_processing_system.core_deps.database.CRUD.document_crud import DocumentCRUD
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager


@task(name="duplicate-detection", retries=2)
def duplicate_detection_task(raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Fast duplicate detection using file hash only - no heavy ML models.
    
    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        
    Returns:
        Dict containing duplicate check results
    """
    logger = get_run_logger()
    raw_path = Path(raw_file_path)
    logger.info(f"🔍 Fast duplicate detection for: {raw_path.name}")
    
    try:
        # Create lightweight DocumentCRUD directly (no heavy processors)
        connection_manager = ConnectionManager()
        document_crud = DocumentCRUD(connection_manager)
        
        # Fast duplicate check using file hash only
        is_duplicate, existing_doc_id = document_crud.check_duplicate_by_raw_file(str(raw_path))
        
        if is_duplicate:
            logger.info(f"📋 Document is duplicate: {existing_doc_id}")
            return {
                "status": "duplicate",
                "document_id": existing_doc_id,
                "message": f"Document already processed: {existing_doc_id}"
            }
        else:
            # Generate lightweight document ID (no heavy processing)
            document_id = _generate_document_id(raw_path)
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


def _generate_document_id(file_path: Path) -> str:
    """Generate lightweight document ID from file path only."""
    # Clean filename for document ID
    clean_name = re.sub(r'[^\w\s-]', '', file_path.stem).strip()
    clean_name = re.sub(r'[-\s]+', '_', clean_name)
    
    # Add file hash for uniqueness
    file_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:8]
    
    return f"{clean_name}_{file_hash}"