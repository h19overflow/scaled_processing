"""
Chunking task for document processing flow.
Processes Docling-extracted markdown with vision enhancement and chunking.
"""

import re
import base64
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO
from PIL import Image

from prefect import task, get_run_logger

# Conditional imports - only load heavy vision components when needed


@task(name="Markdown_VISION", retries=1)
async def markdown_vision_task(
    processed_markdown_path: str,
    document_id: str,
    file_info: Dict[str, Any],
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
        
        # Step 2: Extract base64 images from markdown and process them
        logger.info(f"🖼️ Extracting base64 images from markdown")
        extracted_images = _extract_base64_images_from_markdown(docling_content, document_id, logger)
        
        logger.info(f"Found {len(extracted_images)} images for vision processing")
        
        # Step 3: Initialize vision processor with conditional import (lazy loading)
        try:
            # Only import heavy vision components when actually needed
            from ...utils.vision_processor import VisionProcessor
            from ...utils.vision_config import VisionConfig
            
            logger.info("🔄 Loading vision processing components...")
            vision_config = VisionConfig.from_env()
            vision_processor = VisionProcessor(vision_config)
            
        except ImportError as e:
            logger.error(f"❌ Vision components not available: {e}")
            return {
                "status": "error",
                "error": "Vision processing components not available",
                "message": f"Failed to load vision components: {e}"
            }
        
        # Step 4: Process images with vision AI and enhance markdown
        context = f"Document: {file_info.get('filename', 'unknown')} ({file_info.get('file_type', 'pdf')})"
        enhanced_content = await _process_base64_images_in_markdown(
            content=docling_content,
            extracted_images=extracted_images,
            vision_processor=vision_processor,
            context=context,
            logger=logger
        )
        
        # Step 5: Save vision-enhanced markdown to new file
        enhanced_markdown_path = markdown_path.parent / f"{document_id}_vision_enhanced.md"
        
        with open(enhanced_markdown_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
        
        logger.info(f"✅ Vision enhancement completed: {len(enhanced_content)} chars")
        logger.info(f"💾 Enhanced markdown saved to: {enhanced_markdown_path}")
        
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


# HELPER FUNCTIONS
def _extract_base64_images_from_markdown(content: str, document_id: str, logger) -> Dict[str, str]:
    """Extract base64 images from markdown and save them as temporary files."""
    
    # Pattern to match base64 image data in markdown
    base64_image_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    
    matches = list(re.finditer(base64_image_pattern, content))
    extracted_images = {}
    
    # Create temporary directory for images
    temp_dir = Path(tempfile.gettempdir()) / "vision_images" / document_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for i, match in enumerate(matches):
        try:
            alt_text = match.group(1)
            image_format = match.group(2)  # png, jpg, etc.
            base64_data = match.group(3)
            
            # Decode base64 data
            image_bytes = base64.b64decode(base64_data)
            
            # Create PIL Image and save as temporary file
            image = Image.open(BytesIO(image_bytes))
            image_path = temp_dir / f"image_{i}.{image_format}"
            image.save(image_path)
            
            extracted_images[str(i)] = str(image_path)
            logger.debug(f"Extracted image {i}: {alt_text} -> {image_path}")
            
        except Exception as e:
            logger.warning(f"Failed to extract base64 image {i}: {e}")
    
    return extracted_images


async def _process_base64_images_in_markdown(content: str, extracted_images: Dict[str, str], 
                                           vision_processor, context: str, logger) -> str:
    """Process base64 images with vision AI and enhance markdown."""
    
    if not extracted_images:
        logger.info("No images found to process with vision AI")
        return content
    
    # Process images with vision AI (using existing VisionProcessor)
    descriptions = {}
    if extracted_images:
        # Use the existing vision processor but we need to adapt it for base64 images
        for img_id, img_path in extracted_images.items():
            try:
                # Load the image
                img_obj = Image.open(img_path)
                
                # Use the vision agent directly for description
                description = await vision_processor.vision_agent.describe_image_async(img_obj, context)
                
                descriptions[img_id] = {
                    'description': description,
                    'classification': {'action': 'analyze', 'confidence': 1.0},
                    'image_path': img_path
                }
                logger.debug(f"Generated description for image {img_id}: {description[:50]}...")
                
            except Exception as e:
                logger.warning(f"Failed to process image {img_id} with vision AI: {e}")
    
    # Enhance the content by replacing base64 images with enhanced versions
    enhanced_content = _replace_base64_images_with_descriptions(content, descriptions, logger)
    
    # Clean up temporary files
    for img_path in extracted_images.values():
        try:
            Path(img_path).unlink()
        except Exception as e:
            logger.warning(f"Failed to clean up temp image {img_path}: {e}")
    
    return enhanced_content


def _replace_base64_images_with_descriptions(content: str, descriptions: Dict[str, Dict], logger) -> str:
    """Replace base64 images in markdown with enhanced versions including AI descriptions."""
    
    # Pattern to match base64 image data in markdown
    base64_image_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    
    def replace_image(match, img_index):
        alt_text = match.group(1)
        image_format = match.group(2)
        base64_data = match.group(3)
        
        # Get description for this image
        img_id = str(img_index)
        desc_data = descriptions.get(img_id, {})
        description = desc_data.get('description', '')
        
        # Keep the original base64 image
        original_image = match.group(0)
        
        if description and "Failed" not in description:
            # Add AI description after the image
            enhanced = f"{original_image}\n\n**AI Analysis**: {description}\n"
            logger.debug(f"Enhanced image {img_index} with AI description")
        else:
            # No valid description, keep original
            enhanced = original_image
            logger.debug(f"No valid description for image {img_index}, keeping original")
        
        return enhanced
    
    # Replace images with enhanced versions
    enhanced_content = content
    matches = list(re.finditer(base64_image_pattern, content))
    
    # Process matches in reverse order to avoid offset issues
    for i in reversed(range(len(matches))):
        match = matches[i]
        enhanced_text = replace_image(match, i)
        
        start, end = match.span()
        enhanced_content = (
            enhanced_content[:start] + 
            enhanced_text + 
            enhanced_content[end:]
        )
    
    logger.info(f"Enhanced {len(matches)} base64 images with AI descriptions")
    return enhanced_content