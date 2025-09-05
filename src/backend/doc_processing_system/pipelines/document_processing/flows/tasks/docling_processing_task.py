"""
Docling processing task for document processing flow.
Extracts rich markdown and images using DoclingProcessor with strict path-based I/O.
"""

from typing import Dict, Any

from prefect import task, get_run_logger

from ...utils.docling_processor import DoclingProcessor


@task(name="docling-processing", retries=2)
def docling_processing_task(
    raw_file_path: str,
    document_id: str,
    user_id: str = "default"
) -> Dict[str, Any]:
    """Extract document content using Docling with path-based output.
    
    Args:
        raw_file_path: Path to the raw document file
        document_id: Document ID from duplicate check
        user_id: User who uploaded the document
        
    Returns:
        Dict containing paths to extracted content: {
            "status": "completed",
            "processed_markdown_path": "/path/to/document.md", 
            "extracted_images_dir": "/path/to/images/",
            "document_id": "doc_id",
            "file_info": {...}
        }
    """
    logger = get_run_logger()
    logger.info(f"📄 Starting Docling processing for document: {document_id}")
    
    try:
        # Initialize DoclingProcessor
        processor = DoclingProcessor()
        
        # Extract document with Docling
        extraction_result = processor.extract_document(
            raw_file_path=raw_file_path,
            document_id=document_id,
            user_id=user_id
        )
        
        if extraction_result["status"] == "completed":
            logger.info(f"✅ Docling processing completed for: {document_id}")
            logger.info(f"📝 Markdown saved to: {extraction_result['processed_markdown_path']}")
            logger.info(f"🖼️ Images extracted to: {extraction_result['extracted_images_dir']}")
            
            return {
                "status": "completed",
                "document_id": document_id,
                "processed_markdown_path": extraction_result["processed_markdown_path"],
                "extracted_images_dir": extraction_result["extracted_images_dir"],
                "file_info": extraction_result["file_info"],
                "processing_directory": extraction_result["processing_directory"]
            }
        else:
            logger.error(f"❌ Docling processing failed for {document_id}: {extraction_result.get('error')}")
            return {
                "status": "error",
                "document_id": document_id,
                "error": extraction_result.get("error", "Unknown error"),
                "error_details": extraction_result.get("error_details", ""),
                "message": f"Docling processing failed: {extraction_result.get('error')}"
            }
        
    except Exception as e:
        logger.error(f"❌ Docling processing task failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Docling processing task failed: {e}"
        }