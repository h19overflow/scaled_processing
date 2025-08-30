"""
Chunk-related data models for the document processing system.
Contains models for text chunks, embeddings, and vector search results.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel


class ChunkingRequest(BaseModel):
    """Model for chunking request parameters."""
    document_id: str
    content: str
    chunk_strategy: str = "semantic"
    max_chunk_size: int = 8192


class TextChunk(BaseModel):
    """Model for text chunks from documents."""
    chunk_id: str
    document_id: str
    content: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any] = {}
    
    def get_text(self) -> str:
        """Get chunk text content."""
        return self.content
    
    def get_document_id(self) -> str:
        """Get associated document ID."""
        return self.document_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata
        }


class ValidatedEmbedding(BaseModel):
    """Model for validated embedding with metadata."""
    chunk_id: str
    document_id: str
    embedding_vector: List[float]
    embedding_model: str
    chunk_metadata: Dict[str, Any] = {}
    
    def get_embedding(self) -> List[float]:
        """Get embedding vector."""
        return self.embedding_vector


class VectorSearchResult(BaseModel):
    """Model for vector search results."""
    chunk_id: str
    similarity_score: float
    chunk_content: str
    document_metadata: Dict[str, Any] = {}


class Chunk(BaseModel):
    """Core chunk model for database storage."""
    id: Optional[UUID] = None
    document_id: UUID
    chunk_id: str
    content: str
    page_number: int
    chunk_index: int
    created_at: Optional[datetime] = None
    
    def get_text(self) -> str:
        """Get chunk text content."""
        return self.content
    
    def get_embedding(self) -> List[float]:
        """Get chunk embedding - to be implemented by storage layer."""
        raise NotImplementedError("Embedding retrieval must be implemented by storage layer")
    
    def get_document_id(self) -> str:
        """Get associated document ID."""
        return str(self.document_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "document_id": str(self.document_id),
            "chunk_id": self.chunk_id,
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }