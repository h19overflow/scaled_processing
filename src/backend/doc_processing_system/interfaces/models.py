"""
Basic model interfaces for the document processing system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class IDocument(ABC):
    """Interface for document models."""
    
    @property
    @abstractmethod
    def document_id(self) -> str:
        """Get document ID."""
        pass
    
    @property 
    @abstractmethod
    def content(self) -> str:
        """Get document content."""
        pass
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Get document metadata."""
        pass


class IChunk(ABC):
    """Interface for document chunks."""
    
    @property
    @abstractmethod
    def chunk_id(self) -> str:
        """Get chunk ID."""
        pass
    
    @property
    @abstractmethod
    def content(self) -> str:
        """Get chunk content."""
        pass


class IExtraction(ABC):
    """Interface for extraction results."""
    
    @property
    @abstractmethod
    def extraction_id(self) -> str:
        """Get extraction ID."""
        pass
    
    @property
    @abstractmethod
    def extracted_data(self) -> Dict[str, Any]:
        """Get extracted data."""
        pass