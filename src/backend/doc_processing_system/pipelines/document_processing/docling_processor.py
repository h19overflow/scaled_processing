"""
DoclingProcessor - Unified document processing using IBM Docling.
Enhanced with vision processing for AI-powered image descriptions.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from ...data_models.document import ParsedDocument, DocumentMetadata, FileType
from .utils.vision_processor import VisionProcessor
from .utils.vision_config import VisionConfig




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
        
        # Initialize DocumentOutputManager lazily to avoid circular imports
        self.output_manager = None
        
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
    
    def _get_output_manager(self):
        """Lazy initialization of DocumentOutputManager to avoid circular imports."""
        if self.output_manager is None:
            from .utils.document_output_manager import DocumentOutputManager
            self.output_manager = DocumentOutputManager()
        return self.output_manager
    
    async def process_document_with_duplicate_check(self, raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Complete workflow: check duplicates, process if new, save with robust paths, prepare Kafka message.
        
        Args:
            raw_file_path: Path to the raw document file
            user_id: User who uploaded the document
            
        Returns:
            Dict containing processing results and message data
        """
        try:
            # Step 1: Check for duplicates using DocumentOutputManager
            output_manager = self._get_output_manager()
            check_result = output_manager.check_and_process_document(raw_file_path, user_id)
            
            if check_result["status"] == "duplicate":
                return check_result
            elif check_result["status"] == "error":
                return check_result
            
            # Step 2: Extract info for processing
            document_id = check_result["document_id"]
            
            # Step 3: Process document with vision AI
            parsed_document = await self.process_document_with_vision(
                raw_file_path, document_id, user_id
            )
            
            # Step 4: Prepare metadata for saving
            file_path_obj = Path(raw_file_path)
            metadata = {
                "filename": file_path_obj.name,
                "page_count": parsed_document.page_count,
                "content_length": len(parsed_document.content),
                "file_type": parsed_document.metadata.file_type,
                "file_size": parsed_document.metadata.file_size,
                "processed_content": parsed_document.content,
                "vision_processing": self.enable_vision
            }
            
            # Step 5: Save processed document with robust file paths
            save_result = output_manager.save_processed_document(
                document_id, parsed_document.content, metadata, user_id
            )
            
            if save_result["status"] == "error":
                return save_result
            
            # Step 6: Prepare Kafka message for downstream processing
            message_result = output_manager.prepare_kafka_message(
                document_id, save_result["processed_file_path"], metadata, user_id
            )
            
            # Step 7: Combine all results
            complete_result = {
                "status": "completed",
                "document_id": document_id,
                "processed_file_path": save_result["processed_file_path"],
                "document_directory": save_result["document_directory"],
                "kafka_message": message_result.get("kafka_message"),
                "parsed_document": parsed_document,
                "message": f"Document processed successfully: {document_id}"
            }
            
            self.logger.info(f"Complete document processing workflow finished: {document_id}")
            return complete_result
            
        except Exception as e:
            self.logger.error(f"Error in complete document processing: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Complete processing failed: {e}"
            }
    
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
            
            # Create metadata
            file_stats = file_path_obj.stat()
            metadata = DocumentMetadata(
                document_id=document_id,
                file_type=self._get_file_type(file_path_obj).value,
                file_size=file_stats.st_size,
                upload_timestamp=datetime.now(),
                user_id=user_id
            )
            
            # Create ParsedDocument
            parsed_doc = ParsedDocument(
                document_id=document_id,
                content=content,
                page_count=page_count,
                metadata=metadata
            )
            
            self.logger.info(f"Successfully processed {file_path_obj.name}: {len(content)} chars, {page_count} pages")
            return parsed_doc
            
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
    # HELPER FUNCTIONS
    def _get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from file extension."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return FileType.PDF
        elif suffix in ['.docx', '.doc']:
            return FileType.DOCX
        elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return FileType.IMAGE
        elif suffix in ['.txt', '.md']:
            return FileType.TEXT
        else:
            # Default to PDF for unsupported types
            return FileType.PDF