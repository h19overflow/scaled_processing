"""
Core data model interfaces from the class diagram.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class IDocument(ABC):
    """Interface for document objects."""
    
    @abstractmethod
    def get_id(self) -> str:
        """Get document ID."""
        pass
        
    @abstractmethod
    def get_content(self) -> str:
        """Get document content."""
        pass
        
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Get document metadata."""
        pass
        
    @abstractmethod
    def validate(self) -> bool:
        """Validate document structure and content."""
        pass


class IChunk(ABC):
    """Interface for document chunk objects."""
    
    @abstractmethod
    def get_text(self) -> str:
        """Get chunk text content."""
        pass
        
    @abstractmethod
    def get_embedding(self) -> List[float]:
        """Get chunk embedding vector."""
        pass
        
    @abstractmethod
    def get_document_id(self) -> str:
        """Get parent document ID."""
        pass