"""
Chunk CRUD operations.
Handles all database operations related to text chunks.
"""

from typing import List
from uuid import UUID
from sqlalchemy import and_

from .base_repository import BaseRepository
from ..models import ChunkModel
from ....data_models.chunk import TextChunk


class ChunkCRUD(BaseRepository):
    """CRUD operations for chunk entities."""
    
    def create_multiple(self, chunks: List[TextChunk]) -> List[str]:
        """Create multiple chunks and return their IDs.
        
        Args:
            chunks: List of TextChunk objects to create
            
        Returns:
            List[str]: List of created chunk IDs
            
        Raises:
            Exception: If chunk creation fails
        """
        try:
            chunk_ids = []
            
            with self.connection_manager.get_session() as session:
                for chunk in chunks:
                    chunk_model = ChunkModel(
                        document_id=self._validate_uuid(chunk.document_id),
                        chunk_id=chunk.chunk_id,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        metadata=chunk.metadata
                    )
                    
                    session.add(chunk_model)
                    session.flush()
                    chunk_ids.append(str(chunk_model.id))
                
                self._log_operation("Created chunks", details=f"count: {len(chunks)}")
                return chunk_ids
        
        except Exception as e:
            self.logger.error(f"Failed to create chunks: {e}")
            raise
    
    def create_single(self, chunk: TextChunk) -> str:
        """Create a single chunk and return its ID.
        
        Args:
            chunk: TextChunk object to create
            
        Returns:
            str: Created chunk ID
        """
        return self.create_multiple([chunk])[0]
    
    def get_by_document(self, document_id: str) -> List[TextChunk]:
        """Get all chunks for a document.
        
        Args:
            document_id: Document ID to get chunks for
            
        Returns:
            List[TextChunk]: List of chunks for the document
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                chunk_models = session.query(ChunkModel).filter(
                    ChunkModel.document_id == uuid_id
                ).order_by(ChunkModel.chunk_index).all()
                
                chunks = [self._model_to_chunk(chunk) for chunk in chunk_models]
                
                self._log_operation("Retrieved chunks by document", document_id, f"count: {len(chunks)}")
                return chunks
        
        except Exception as e:
            self.logger.error(f"Failed to get chunks for document {document_id}: {e}")
            raise
    
    def get_by_page(self, document_id: str, page_number: int) -> List[TextChunk]:
        """Get chunks for a specific page.
        
        Args:
            document_id: Document ID
            page_number: Page number to get chunks for
            
        Returns:
            List[TextChunk]: List of chunks for the page
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                chunk_models = session.query(ChunkModel).filter(
                    and_(
                        ChunkModel.document_id == uuid_id,
                        ChunkModel.page_number == page_number
                    )
                ).order_by(ChunkModel.chunk_index).all()
                
                chunks = [self._model_to_chunk(chunk) for chunk in chunk_models]
                
                self._log_operation("Retrieved chunks by page", document_id, f"page: {page_number}, count: {len(chunks)}")
                return chunks
        
        except Exception as e:
            self.logger.error(f"Failed to get chunks for document {document_id}, page {page_number}: {e}")
            raise
    
    def update_embedding(self, chunk_id: str, embedding: List[float]) -> bool:
        """Update chunk with embedding vector.
        
        Args:
            chunk_id: Chunk ID to update
            embedding: Embedding vector to store
            
        Returns:
            bool: True if update was successful
        """
        try:
            with self.connection_manager.get_session() as session:
                updated_rows = session.query(ChunkModel).filter(
                    ChunkModel.chunk_id == chunk_id
                ).update({'embedding_vector': embedding})
                
                success = updated_rows > 0
                if success:
                    self._log_operation("Updated chunk embedding", chunk_id, f"embedding_dim: {len(embedding)}")
                else:
                    self.logger.warning(f"No chunk found to update embedding: {chunk_id}")
                
                return success
        
        except Exception as e:
            self.logger.error(f"Failed to update embedding for chunk {chunk_id}: {e}")
            raise
    
    def get_by_chunk_id(self, chunk_id: str) -> TextChunk:
        """Get chunk by chunk ID.
        
        Args:
            chunk_id: Chunk ID to retrieve
            
        Returns:
            TextChunk: Chunk object if found
            
        Raises:
            ValueError: If chunk not found
        """
        try:
            with self.connection_manager.get_session() as session:
                chunk_model = session.query(ChunkModel).filter(
                    ChunkModel.chunk_id == chunk_id
                ).first()
                
                if not chunk_model:
                    raise ValueError(f"Chunk not found: {chunk_id}")
                
                return self._model_to_chunk(chunk_model)
        
        except Exception as e:
            self.logger.error(f"Failed to get chunk {chunk_id}: {e}")
            raise
    
    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.
        
        Args:
            document_id: Document ID to delete chunks for
            
        Returns:
            int: Number of chunks deleted
        """
        try:
            uuid_id = self._validate_uuid(document_id)
            
            with self.connection_manager.get_session() as session:
                deleted_count = session.query(ChunkModel).filter(
                    ChunkModel.document_id == uuid_id
                ).delete()
                
                self._log_operation("Deleted chunks by document", document_id, f"count: {deleted_count}")
                return deleted_count
        
        except Exception as e:
            self.logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            raise
    
    def _model_to_chunk(self, chunk_model: ChunkModel) -> TextChunk:
        """Convert ChunkModel to TextChunk.
        
        Args:
            chunk_model: ChunkModel instance
            
        Returns:
            TextChunk: Converted TextChunk object
        """
        return TextChunk(
            chunk_id=chunk_model.chunk_id,
            document_id=str(chunk_model.document_id),
            content=chunk_model.content,
            page_number=chunk_model.page_number,
            chunk_index=chunk_model.chunk_index,
            chunk_metadata=chunk_model.metadata or {}
        )
