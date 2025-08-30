"""
Document-related data models for the document processing system.
Contains models for document upload, metadata, and processing status.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel


class FileType(str, Enum):
    """Supported file types for document processing."""
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    TEXT = "text"


class UploadFile(BaseModel):
    """Model for uploaded file information."""
    filename: str
    content_type: str
    size: int
    file_data: bytes


class DocumentMetadata(BaseModel):
    """Model for document metadata."""
    document_id: str
    file_type: FileType
    upload_timestamp: datetime
    user_id: str
    file_size: int


class ParsedDocument(BaseModel):
    """Model for parsed document content."""
    document_id: str
    content: str
    metadata: DocumentMetadata
    page_count: int
    extracted_images: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []


class ProcessingStatus(str, Enum):
    """Document processing status values."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Core document model for database storage."""
    id: Optional[UUID] = None
    filename: str
    file_type: str
    upload_timestamp: datetime
    user_id: str
    processing_status: ProcessingStatus = ProcessingStatus.UPLOADED
    file_size: int
    page_count: Optional[int] = None
    
    def get_id(self) -> str:
        """Get document ID as string."""
        return str(self.id) if self.id else ""
    
    def get_content(self) -> str:
        """Get document content - to be implemented by specific storage layer."""
        raise NotImplementedError("Content retrieval must be implemented by storage layer")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get document metadata as dictionary."""
        return {
            "filename": self.filename,
            "file_type": self.file_type,
            "upload_timestamp": self.upload_timestamp.isoformat(),
            "user_id": self.user_id,
            "file_size": self.file_size,
            "page_count": self.page_count
        }
    
    def validate(self) -> bool:
        """Validate document data."""
        return (
            bool(self.filename) and
            bool(self.user_id) and
            self.file_size > 0
        )
    
    def update_metadata(self, new_metadata: Dict[str, Any]) -> bool:
        """Update document metadata."""
        try:
            for key, value in new_metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False