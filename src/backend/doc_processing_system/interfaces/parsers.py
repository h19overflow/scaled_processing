"""
Parser interfaces from the class diagram.
"""

from abc import ABC, abstractmethod
from typing import List
from .models import IDocument, IChunk


class IDocumentParser(ABC):
    """Interface for document parsers."""
    
    @abstractmethod
    def parse(self, file_path: str) -> IDocument:
        """Parse document from file path."""
        pass
        
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """Check if parser supports file format."""
        pass


class IChunker(ABC):
    """Interface for document chunking."""
    
    @abstractmethod
    def chunk(self, document: IDocument) -> List[IChunk]:
        """Chunk document into smaller pieces."""
        pass
        
    @abstractmethod
    def create_embeddings(self, chunks: List[IChunk]) -> bool:
        """Create embeddings for chunks."""
        pass