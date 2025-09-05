"""
Document saving task for document processing flow.
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger

from ...utils.document_output_manager import DocumentOutputManager


@task(name="document-saving", retries=2)
def document_saving_task(
    vision_enhanced_markdown_path: str,
    document_id: str,
    content_length: int,
    page_count: int,
    raw_file_path: str,
    user_id: str = "default"
) -> Dict[str, Any]:
    """Save vision-enhanced document to structured directory using path-based I/O.
    
    Args:
        vision_enhanced_markdown_path: Path to vision-enhanced markdown file
        document_id: Document identifier
        content_length: Length of processed content
        page_count: Number of pages in document
        raw_file_path: Original file path for metadata
        user_id: User who uploaded the document
        
    Returns:
        Dict containing save results and file paths
    """
    logger = get_run_logger()
    logger.info(f"💾 Saving processed document: {document_id}")
    
    try:
        # Read vision-enhanced content from file
        enhanced_markdown_path = Path(vision_enhanced_markdown_path)
        if not enhanced_markdown_path.exists():
            raise FileNotFoundError(f"Vision-enhanced markdown not found: {vision_enhanced_markdown_path}")
        
        with open(enhanced_markdown_path, 'r', encoding='utf-8') as f:
            processed_content = f.read()
        
        logger.info(f"📖 Read {len(processed_content)} characters from vision-enhanced markdown")
        
        # Initialize output manager
        output_manager = DocumentOutputManager()
        
        # Prepare metadata for saving
        file_path_obj = Path(raw_file_path)
        metadata = {
            "filename": file_path_obj.name,
            "page_count": page_count,
            "content_length": content_length,
            "file_type": file_path_obj.suffix.lower().replace('.', '') or 'pdf',
            "file_size": file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            "processed_content": processed_content,
            "vision_processing": True,
            "processing_timestamp": datetime.now().isoformat()
        }
        
        # Save processed document
        save_result = output_manager.save_processed_document(
            document_id, processed_content, metadata, user_id
        )
        
        if save_result["status"] == "saved":
            logger.info(f"✅ Document saved successfully: {save_result['processed_file_path']}")
        else:
            logger.error(f"❌ Failed to save document: {save_result.get('error')}")
            
        return {
            "document_id": document_id,
            "save_result": save_result,
            "status": "completed" if save_result["status"] == "saved" else "error",
            "processed_file_path": save_result.get("processed_file_path"),
            "document_directory": save_result.get("document_directory"),
            "content_length": content_length,
            "page_count": page_count
        }
        
    except Exception as e:
        logger.error(f"❌ Document saving failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Document saving failed: {e}"
        }