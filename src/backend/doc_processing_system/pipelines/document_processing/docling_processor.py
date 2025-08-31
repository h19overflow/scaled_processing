"""
DoclingProcessor - Unified document processing using IBM Docling.
Enhanced with vision processing for AI-powered image descriptions.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from ...data_models.document import ParsedDocument
from .utils import VisionProcessor, VisionConfig




class DoclingProcessor:
    """
    Unified document processor using IBM Docling for structured extraction.
    Enhanced with vision processing for AI-powered image descriptions.
    """
    
    def __init__(self, enable_vision: bool = True):
        """Initialize the DoclingProcessor with optional vision processing.
        
        Args:
            enable_vision: Whether to enable AI vision processing for images
        """
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize Docling converter with image extraction
        try:
            IMAGE_RESOLUTION_SCALE = 2.0
            
            # Set up pipeline options exactly like the example
            pipeline_options = PdfPipelineOptions()
            pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
            pipeline_options.generate_page_images = True
            pipeline_options.generate_picture_images = True
            
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            
            self.logger.info("DoclingProcessor initialized successfully with image extraction")
        except Exception as e:
            self.logger.error(f"Failed to initialize DoclingProcessor: {e}")
            raise
        
        # Initialize vision processing (optional)
        self.enable_vision = enable_vision
        if self.enable_vision:
            try:
                self.vision_processor = VisionProcessor(VisionConfig.from_env())
                self.logger.info("Vision processing enabled")
            except Exception as e:
                self.logger.warning(f"Vision processing disabled due to error: {e}")
                self.enable_vision = False
                self.vision_processor = None
        else:
            self.vision_processor = None
            self.logger.info("Vision processing disabled")
    
    async def process_document_with_vision(self, file_path: str, document_id: str, user_id: str = "default") -> ParsedDocument:
        """
        Process document with vision AI enhancement.
        
        Args:
            file_path: Path to the document file
            document_id: Unique document identifier
            user_id: User who uploaded the document
            
        Returns:
            ParsedDocument: Document with AI-enhanced image descriptions
        """
        try:
            file_path_obj = Path(file_path)
            
            # Validate file exists
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
            
            self.logger.info(f"Processing document with vision AI: {file_path_obj.name}")
            
            # Convert document using Docling
            result = self.converter.convert(file_path)
            
            # Extract images first
            extracted_images = self._extract_images_to_dict(result, file_path_obj)
            
            # Get base content
            content = result.document.export_to_markdown()
            page_count = len(result.pages)
            confidence_report = result.confidence
            
            # Enhance with vision AI if enabled and images exist
            if self.enable_vision and self.vision_processor and extracted_images:
                try:
                    # Extract document context for better AI analysis
                    context = self._extract_document_context(content)
                    
                    # Process images with vision AI
                    enhanced_content = await self.vision_processor.process_document_images(
                        extracted_images, content, context
                    )
                    
                    self.logger.info(f"Vision processing completed for {len(extracted_images)} images")
                    content = enhanced_content
                    
                except Exception as e:
                    self.logger.warning(f"Vision processing failed, using original content: {e}")
            
            # Create ParsedDocument
            parsed_doc = ParsedDocument(
                document_id=document_id,
                content=content,
                page_count=page_count,
                confidence_report=confidence_report,
            )
            
            self.logger.info(f"Successfully processed {file_path_obj.name}: {len(content)} chars, {page_count} pages")
            return parsed_doc
            
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            raise
    def process_document(self, file_path: str, document_id: str = None, user_id: str = "default") -> ParsedDocument:
        """
        Process document using Docling (sync version for compatibility).
        
        Args:
            file_path: Path to the document file
            document_id: Unique document identifier  
            user_id: User who uploaded the document
            
        Returns:
            ParsedDocument: Structured document with content and metadata
        """
        # Use async version with event loop
        if document_id is None:
            document_id = Path(file_path).stem
            
        try:
            # Run async version
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.process_document_with_vision(file_path, document_id, user_id)
                )
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            raise
    
    def _extract_images_to_dict(self, result, file_path_obj: Path) -> Dict[str, str]:
        """Extract images and return dict of {image_id: image_path}."""
        extracted_images = {}
        picture_counter = 0
        
        # Create output directory for images
        output_dir = file_path_obj.parent / "extracted_images" / file_path_obj.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract images using Docling
        for element, _level in result.document.iterate_items():
            if isinstance(element, PictureItem):
                picture_counter += 1
                image_filename = output_dir / f"picture-{picture_counter}.png"
                
                try:
                    with image_filename.open("wb") as fp:
                        element.get_image(result.document).save(fp, "PNG")
                    
                    # Store in dict for vision processing
                    extracted_images[str(picture_counter)] = str(image_filename)
                    self.logger.debug(f"Saved image: {image_filename}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to save image {picture_counter}: {e}")
        
        self.logger.info(f"Extracted {len(extracted_images)} images to {output_dir}")
        return extracted_images
    
    def _extract_document_context(self, content: str) -> str:
        """Extract relevant context from document for vision AI."""
        # Simple implementation: get first 500 characters as context
        context_length = 500
        context = content[:context_length].replace('\n', ' ').strip()
        
        # Add document type info if available
        if 'table' in content.lower() or 'chart' in content.lower():
            context += " [Document contains tables/charts]"
        if 'figure' in content.lower() or 'diagram' in content.lower():
            context += " [Document contains figures/diagrams]"
            
        return context
    
    def analyze_document_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze document structure without full processing.
        Useful for quick document inspection.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dict containing document structure analysis
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
            
            self.logger.info(f"Analyzing structure: {file_path_obj.name}")
            
            # Convert document
            result = self.converter.convert(file_path)
            
            # Simple structure analysis
            analysis = {
                "filename": file_path_obj.name,
                "content_length": len(result.document.export_to_markdown()),
                "processing_time": "now"
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze document structure {file_path}: {e}")
            raise
    
    def extract_markdown(self, file_path: str) -> str:
        """
        Extract document content as clean markdown.
        Perfect for LLM processing while preserving structure.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            str: Document content in markdown format
        """
        try:
            result = self.converter.convert(file_path)
            
            # Extract images and save them
            picture_counter = 0
            output_dir = Path("extracted_images")
            output_dir.mkdir(exist_ok=True)
            
            # Extract images using the exact pattern from the example
            for element, _level in result.document.iterate_items():
                if isinstance(element, PictureItem):
                    picture_counter += 1
                    image_filename = output_dir / f"picture-{picture_counter}.png"
                    try:
                        with image_filename.open("wb") as fp:
                            element.get_image(result.document).save(fp, "PNG")
                        self.logger.info(f"Saved image: {image_filename}")
                    except Exception as e:
                        self.logger.warning(f"Failed to save image {picture_counter}: {e}")

            self.logger.info(f"Found {picture_counter} images (extracted to {output_dir})")
            
            # Get markdown content
            markdown_content = result.document.export_to_markdown()
            self.logger.info(f"Extracted markdown: {len(markdown_content)} characters")
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"Failed to extract markdown from {file_path}: {e}")
            raise