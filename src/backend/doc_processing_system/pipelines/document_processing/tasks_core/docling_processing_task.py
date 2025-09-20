"""
Docling processing task for document processing flow.
Extracts rich Markdown and images using DoclingProcessor with strict path-based I/O.
"""

from typing import Dict, Any
import sys

from prefect import task, get_run_logger

# Clear any cached DoclingProcessor modules to ensure we get the right one
modules_to_clear = [k for k in sys.modules.keys() if 'docling_processor' in k.lower()]
for module in modules_to_clear:
    del sys.modules[module]

from src.backend.doc_processing_system.pipelines.document_processing.utils.docling_processor import DoclingProcessor

@task(name="docling-processing", retries=2)
def docling_processing_task(
    raw_file_path: str,
    document_id: str,
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
        logger.info(f"🔥 BEFORE DoclingProcessor() init")
        processor = DoclingProcessor()
        logger.info(f"🔥 AFTER DoclingProcessor() init SUCCESS")

        logger.info(f"📄 Processing document: {document_id}")
        logger.info(f"📄 Raw file path received: {raw_file_path}")

        # Use Path to handle normalization properly - avoids escape sequence issues
        from pathlib import Path
        path_obj = Path(raw_file_path)
        final_path = str(path_obj.resolve())
        logger.info(f"📄 Original file path: {raw_file_path}")
        logger.info(f"📄 Normalized file path: {final_path}")
        logger.info(f"📄 Path exists: {path_obj.exists()}")

        # Extract document with Docling
        logger.info(f"🔥 BEFORE processor.extract_document() call")
        extraction_result = processor.extract_document(
            raw_file_path=final_path,
            document_id=document_id,
        )
        logger.info(f"🔥 AFTER processor.extract_document() call - Status: {extraction_result.get('status')}")
        
        if extraction_result["status"] == "completed":
            logger.info(f"✅ Docling processing completed for: {document_id}")
            logger.info(f"📝 Markdown saved to: {extraction_result['processed_markdown_path']}")

            return {
                "status": "completed",
                "document_id": document_id,
                "processed_markdown_path": extraction_result["processed_markdown_path"],
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