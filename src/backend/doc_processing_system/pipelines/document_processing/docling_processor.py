"""
DoclingProcessor - Unified document processing using IBM Docling.
Refactored to use modular components for clean separation of concerns.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from docling.document_converter import DocumentConverter

from ...data_models.document import ParsedDocument
from .utils import (
    SerializationStrategy,
)


class DoclingProcessor:
    """
    Unified document processor using IBM Docling for structured extraction.
    Refactored to use modular components for table/image serialization,
    content extraction, structure analysis, and validation.
    """
    
    def __init__(self, 
                 table_strategy: SerializationStrategy = SerializationStrategy.STRUCTURED,
                 image_strategy: SerializationStrategy = SerializationStrategy.DETAILED):
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
        
        # Initialize Docling converter
        try:
            self.converter = DocumentConverter()
            self.logger.info(f"DoclingProcessor initialized successfully with table_strategy={table_strategy.value}, image_strategy={image_strategy.value}")
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
            
            # Validate file before processing
            file_validation = self.content_validator.validate_file_path(file_path)
            if not file_validation["is_valid"]:
                raise ValueError(f"File validation failed: {file_validation['issues']}")
            
            self.logger.info(f"Processing document: {file_path_obj.name}")
            
            # Convert document using Docling
            result = self.converter.convert(file_path)
            
            # Extract content and metadata using utility components
            content = self.content_extractor.extract_content(result)
            metadata = self.content_extractor.create_metadata(file_path_obj, document_id, user_id, result)
            page_count = self.content_extractor.get_page_count(result)
            extracted_images = self.content_extractor.extract_images(result)
            tables = self.content_extractor.extract_tables(result)
            
            # Create ParsedDocument
            parsed_doc = ParsedDocument(
                document_id=document_id,
                content=content,
                metadata=metadata,
                page_count=page_count,
                extracted_images=extracted_images,
                tables=tables
            )
            
            # Validate the processed document
            validation_result = self.content_validator.validate_document(parsed_doc)
            if not validation_result["is_valid"]:
                self.logger.warning(f"Document validation issues: {validation_result['issues']}")
                # Continue processing but log the issues
            
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
            
            # Use structure analyzer utility
            analysis = self.structure_analyzer.analyze_document_structure(file_path, result)
            
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
            markdown_content = self.content_extractor.extract_content(result)
            
            self.logger.info(f"Extracted markdown: {len(markdown_content)} characters")
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"Failed to extract markdown from {file_path}: {e}")
            raise