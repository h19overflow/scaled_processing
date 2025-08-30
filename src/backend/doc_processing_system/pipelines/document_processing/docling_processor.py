"""
DoclingProcessor - Unified document processing using IBM Docling.
Handles PDF, DOCX, Images, HTML, PowerPoint with consistent output format.
Designed for structured extraction pipeline that needs complete context.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult

from ...data_models.document import ParsedDocument, DocumentMetadata, FileType


class DoclingProcessor:
    """
    Unified document processor using IBM Docling for structured extraction.
    Preserves document structure, tables, and formatting for LLM processing.
    """
    
    def __init__(self):
        """Initialize the DoclingProcessor with converter."""
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
            self.logger.info("DoclingProcessor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize DoclingProcessor: {e}")
            raise
    
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
            
            # Extract content and metadata
            content = self._extract_content(result)
            metadata = self._create_metadata(file_path_obj, document_id, user_id, result)
            
            # Create ParsedDocument
            parsed_doc = ParsedDocument(
                document_id=document_id,
                content=content,
                metadata=metadata,
                page_count=self._get_page_count(result),
                extracted_images=self._extract_images(result),
                tables=self._extract_tables(result)
            )
            
            self.logger.info(f"Successfully processed {file_path_obj.name}: {len(content)} chars, {parsed_doc.page_count} pages")
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
            
            # Analyze structure
            analysis = {
                "filename": file_path_obj.name,
                "file_size": file_path_obj.stat().st_size,
                "page_count": self._get_page_count(result),
                "content_length": len(result.document.export_to_markdown()),
                "has_tables": len(self._extract_tables(result)) > 0,
                "table_count": len(self._extract_tables(result)),
                "has_images": len(self._extract_images(result)) > 0,
                "image_count": len(self._extract_images(result)),
                "sections": self._analyze_sections(result),
                "processing_time": datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Structure analysis complete: {analysis['page_count']} pages, {analysis['table_count']} tables")
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
            markdown_content = result.document.export_to_markdown()
            
            self.logger.info(f"Extracted markdown: {len(markdown_content)} characters")
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"Failed to extract markdown from {file_path}: {e}")
            raise
    
    # HELPER FUNCTIONS
    
    def _extract_content(self, result: ConversionResult) -> str:
        """Extract clean text content from conversion result."""
        try:
            # Get markdown format (preserves structure)
            return result.document.export_to_markdown()
        except Exception:
            # Fallback to plain text
            return str(result.document)
    
    def _create_metadata(self, file_path: Path, document_id: str, user_id: str, result: ConversionResult) -> DocumentMetadata:
        """Create document metadata from file and conversion result."""
        file_type = self._determine_file_type(file_path.suffix.lower())
        
        return DocumentMetadata(
            document_id=document_id,
            file_type=file_type,
            upload_timestamp=datetime.utcnow(),
            user_id=user_id,
            file_size=file_path.stat().st_size
        )
    
    def _determine_file_type(self, suffix: str) -> FileType:
        """Determine file type from file extension."""
        suffix_map = {
            '.pdf': FileType.PDF,
            '.docx': FileType.DOCX,
            '.doc': FileType.DOCX,
            '.txt': FileType.TEXT,
            '.png': FileType.IMAGE,
            '.jpg': FileType.IMAGE,
            '.jpeg': FileType.IMAGE,
            '.gif': FileType.IMAGE,
            '.bmp': FileType.IMAGE,
        }
        return suffix_map.get(suffix, FileType.TEXT)
    
    def _get_page_count(self, result: ConversionResult) -> int:
        """Extract page count from conversion result."""
        try:
            # Try to get page count from document structure
            if hasattr(result.document, 'pages') and result.document.pages:
                return len(result.document.pages)
            # Fallback: estimate based on content length
            content_length = len(str(result.document))
            return max(1, content_length // 3000)  # Rough estimate: 3000 chars per page
        except Exception:
            return 1
    
    def _extract_images(self, result: ConversionResult) -> List[Dict[str, Any]]:
        """Extract image information from document."""
        images = []
        try:
            # Docling can extract image references and metadata
            if hasattr(result.document, 'pictures') and result.document.pictures:
                for i, picture in enumerate(result.document.pictures):
                    images.append({
                        "image_id": i,
                        "caption": getattr(picture, 'caption', ''),
                        "position": getattr(picture, 'prov', []),
                        "size": getattr(picture, 'size', {})
                    })
        except Exception as e:
            self.logger.warning(f"Failed to extract images: {e}")
        
        return images
    
    def _extract_tables(self, result: ConversionResult) -> List[Dict[str, Any]]:
        """Extract table information from document."""
        tables = []
        try:
            # Docling can extract table structure and data
            if hasattr(result.document, 'tables') and result.document.tables:
                for i, table in enumerate(result.document.tables):
                    tables.append({
                        "table_id": i,
                        "data": self._table_to_dict(table),
                        "position": getattr(table, 'prov', []),
                        "rows": getattr(table, 'num_rows', 0),
                        "columns": getattr(table, 'num_cols', 0)
                    })
        except Exception as e:
            self.logger.warning(f"Failed to extract tables: {e}")
        
        return tables
    
    def _table_to_dict(self, table) -> Dict[str, Any]:
        """Convert table object to dictionary representation."""
        try:
            # Try to extract table data in a structured format
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                return df.to_dict('records')
            else:
                return {"raw": str(table)}
        except Exception:
            return {"raw": str(table)}
    
    def _analyze_sections(self, result: ConversionResult) -> List[str]:
        """Analyze document sections and headings."""
        sections = []
        try:
            content = result.document.export_to_markdown()
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # Extract heading text
                    heading = line.lstrip('#').strip()
                    if heading:
                        sections.append(heading)
        
        except Exception as e:
            self.logger.warning(f"Failed to analyze sections: {e}")
        
        return sections[:10]  # Return first 10 sections