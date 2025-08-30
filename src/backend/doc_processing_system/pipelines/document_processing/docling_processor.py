"""
DoclingProcessor - Unified document processing using IBM Docling.
Refactored to use modular components for clean separation of concerns.
"""

import logging
from pathlib import Path
from typing import Dict, Any
from unittest import result

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from matplotlib.dates import _log
from ...data_models.document import ParsedDocument




class DoclingProcessor:
    """
    Unified document processor using IBM Docling for structured extraction.
    Refactored to use modular components for table/image serialization,
    content extraction, structure analysis, and validation.
    """
    
    def __init__(self):
        """Initialize the DoclingProcessor with converter and serialization strategies.
        
        Args:
            table_strategy: Strategy for table serialization
            image_strategy: Strategy for image serialization
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
        
        # Initialize utility components
    
    def process_document(self, file_path: str, document_id: str, user_id: str = "default") -> ParsedDocument:
        """
        Process document using Docling and return ParsedDocument.
        
        Args:
            file_path: Path to the document file
            document_id: Unique document identifier
            user_id: User who uploaded the document
            
        Returns:
            ParsedDocument: Structured document with content and metadata
            
        Raises:
            Exception: If document processing fails
        """
        try:
            file_path_obj = Path(file_path)
            
            # Validate file exists
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
            
            self.logger.info(f"Processing document: {file_path_obj.name}")
            
            # Convert document using Docling
            result = self.converter.convert(file_path)
            
            # Extract content directly
            content = result.document.export_to_markdown()
            page_count = len(result.pages)  
            confidence_report = result.confidence  
            
            # Create ParsedDocument
            parsed_doc = ParsedDocument(
                document_id=document_id,
                content=content,
                page_count=page_count,
                confidence_report=confidence_report,
            )
            
            # Skip validation for now
            
            self.logger.info(f"Successfully processed {file_path_obj.name}: {len(content)} chars, {page_count} pages")
            return parsed_doc
            
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            raise
    
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