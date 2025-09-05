"""
Chunking task for document processing flow.
Processes Docling-extracted markdown with vision enhancement and chunking.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from prefect import task, get_run_logger

from ...utils.vision_processor import VisionProcessor
from ...utils.vision_config import VisionConfig


@task(name="Markdown_VISION", retries=1)
async def markdown_vision_task(
    processed_markdown_path: str,
    extracted_images_dir: str, 
    document_id: str,
    file_info: Dict[str, Any],
    user_id: str = "default"
) -> Optional[Dict[str, Any]]:
    """Process Docling-extracted content with vision enhancement and chunking.
    
    Args:
        processed_markdown_path: Path to Docling-extracted markdown file
        extracted_images_dir: Path to directory containing extracted images
        document_id: Document ID from duplicate check
        file_info: File metadata from docling processing
        user_id: User who uploaded the document
        
    Returns:
        Dict containing path to vision-enhanced markdown: {
            "status": "completed",
            "vision_enhanced_markdown_path": "/path/to/enhanced.md",
            "document_id": "doc_id",
            "content_length": 12345,
            "page_count": 10
        }
    """
    logger = get_run_logger()
    logger.info(f"🔪 Starting vision enhancement and chunking for document: {document_id}")
    
    try:
        # Step 1: Read Docling-extracted markdown content
        logger.info(f"📖 Reading markdown from: {processed_markdown_path}")
        markdown_path = Path(processed_markdown_path)
        if not markdown_path.exists():
            raise FileNotFoundError(f"Processed markdown not found: {processed_markdown_path}")
        
        with open(markdown_path, 'r', encoding='utf-8') as f:
            docling_content = f.read()
        
        logger.info(f"📄 Read {len(docling_content)} characters from Docling markdown")
        
        # Step 2: Collect extracted images for vision processing
        logger.info(f"🖼️ Scanning images in: {extracted_images_dir}")
        images_dir = Path(extracted_images_dir)
        extracted_images = {}
        
        if images_dir.exists():
            for i, img_file in enumerate(sorted(images_dir.glob("*.png"))):
                image_id = str(i)  # Sequential numbering to match markdown placeholders
                extracted_images[image_id] = str(img_file)
            
            logger.info(f"Found {len(extracted_images)} images for vision processing")
        else:
            logger.warning(f"Images directory not found: {extracted_images_dir}")
        
        # Step 3: Initialize vision processor for image enhancement
        vision_config = VisionConfig.from_env()
        vision_processor = VisionProcessor(vision_config)
        
        # Step 4: Process images with vision AI and enhance markdown
        context = f"Document: {file_info.get('filename', 'unknown')} ({file_info.get('file_type', 'pdf')})"
        enhanced_content = await vision_processor.process_document_images(
            extracted_images=extracted_images,
            content=docling_content,
            context=context
        )
        
        # Step 5: Save vision-enhanced markdown to new file
        enhanced_markdown_path = markdown_path.parent / f"{document_id}_vision_enhanced.md"
        
        with open(enhanced_markdown_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
        
        logger.info(f"✅ Vision enhancement completed: {len(enhanced_content)} chars")
        logger.info(f"💾 Enhanced markdown saved to: {enhanced_markdown_path}")
        
        # This can be added later for additional processing
        
        return {
            "status": "completed",
            "document_id": document_id,
            "vision_enhanced_markdown_path": str(enhanced_markdown_path),
            "content_length": len(enhanced_content),
            "page_count": file_info.get("page_count", 0),
            "images_processed": len(extracted_images)
        }
        
    except Exception as e:
        logger.error(f"❌ Chunking/vision processing failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Vision enhancement and chunking failed: {e}"
        }