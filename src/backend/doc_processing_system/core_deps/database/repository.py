"""
Repository pattern implementations using SQLAlchemy for data access.
Provides clean interfaces for database operations following the repository pattern.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .connection_manager import ConnectionManager
from .models import (
    DocumentModel, ChunkModel, ExtractionResultModel,
    QueryLogModel, QueryResultModel
)
from ...data_models.document import Document, ProcessingStatus
from ...data_models.chunk import Chunk, TextChunk
from ...data_models.extraction import ExtractionResult
from ...data_models.query import QueryLog, QueryResult


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize repository with connection manager."""
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository):
    """Repository for document-related database operations."""
    
    def create_document(self, document: Document) -> str:
        """Create a new document and return its ID."""
        with self.connection_manager.get_session() as session:
            doc_model = DocumentModel(
                filename=document.filename,
                file_type=document.file_type,
                upload_timestamp=document.upload_timestamp,
                user_id=document.user_id,
                processing_status=document.processing_status.value,
                file_size=document.file_size,
                page_count=document.page_count
            )
            
            session.add(doc_model)
            session.flush()  # Get the ID without committing
            document_id = str(doc_model.id)
            
            self.logger.info(f"Created document: {document_id}")
            return document_id
    
    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        with self.connection_manager.get_session() as session:
            doc_model = session.query(DocumentModel).filter(
                DocumentModel.id == UUID(document_id)
            ).first()
            
            if not doc_model:
                return None
            
            return Document(
                id=doc_model.id,
                filename=doc_model.filename,
                file_type=doc_model.file_type,
                upload_timestamp=doc_model.upload_timestamp,
                user_id=doc_model.user_id,
                processing_status=ProcessingStatus(doc_model.processing_status),
                file_size=doc_model.file_size,
                page_count=doc_model.page_count
            )
    
    def update_document_status(self, document_id: str, status: ProcessingStatus) -> bool:
        """Update document processing status."""
        with self.connection_manager.get_session() as session:
            updated_rows = session.query(DocumentModel).filter(
                DocumentModel.id == UUID(document_id)
            ).update({
                'processing_status': status.value,
                'updated_at': datetime.utcnow()
            })
            
            success = updated_rows > 0
            if success:
                self.logger.info(f"Updated document {document_id} status to {status.value}")
            
            return success
    
    def get_documents_by_user(self, user_id: str, limit: int = 50) -> List[Document]:
        """Get documents by user ID."""
        with self.connection_manager.get_session() as session:
            doc_models = session.query(DocumentModel).filter(
                DocumentModel.user_id == user_id
            ).order_by(desc(DocumentModel.created_at)).limit(limit).all()
            
            return [
                Document(
                    id=doc.id,
                    filename=doc.filename,
                    file_type=doc.file_type,
                    upload_timestamp=doc.upload_timestamp,
                    user_id=doc.user_id,
                    processing_status=ProcessingStatus(doc.processing_status),
                    file_size=doc.file_size,
                    page_count=doc.page_count
                ) for doc in doc_models
            ]
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document and all related data."""
        with self.connection_manager.get_session() as session:
            deleted_rows = session.query(DocumentModel).filter(
                DocumentModel.id == UUID(document_id)
            ).delete()
            
            success = deleted_rows > 0
            if success:
                self.logger.info(f"Deleted document: {document_id}")
            
            return success
    
    def get_documents_by_status(self, status: ProcessingStatus) -> List[Document]:
        """Get documents by processing status."""
        with self.connection_manager.get_session() as session:
            doc_models = session.query(DocumentModel).filter(
                DocumentModel.processing_status == status.value
            ).all()
            
            return [
                Document(
                    id=doc.id,
                    filename=doc.filename,
                    file_type=doc.file_type,
                    upload_timestamp=doc.upload_timestamp,
                    user_id=doc.user_id,
                    processing_status=ProcessingStatus(doc.processing_status),
                    file_size=doc.file_size,
                    page_count=doc.page_count
                ) for doc in doc_models
            ]


class ChunkRepository(BaseRepository):
    """Repository for chunk-related database operations."""
    
    def create_chunks(self, chunks: List[TextChunk]) -> List[str]:
        """Create multiple chunks and return their IDs."""
        chunk_ids = []
        
        with self.connection_manager.get_session() as session:
            for chunk in chunks:
                chunk_model = ChunkModel(
                    document_id=UUID(chunk.document_id),
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata
                )
                
                session.add(chunk_model)
                session.flush()
                chunk_ids.append(str(chunk_model.id))
            
            self.logger.info(f"Created {len(chunks)} chunks")
            return chunk_ids
    
    def get_chunks_by_document(self, document_id: str) -> List[TextChunk]:
        """Get all chunks for a document."""
        with self.connection_manager.get_session() as session:
            chunk_models = session.query(ChunkModel).filter(
                ChunkModel.document_id == UUID(document_id)
            ).order_by(ChunkModel.chunk_index).all()
            
            return [
                TextChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=str(chunk.document_id),
                    content=chunk.content,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_metadata=chunk.metadata or {}
                ) for chunk in chunk_models
            ]
    
    def update_chunk_embedding(self, chunk_id: str, embedding: List[float]) -> bool:
        """Update chunk with embedding vector."""
        with self.connection_manager.get_session() as session:
            updated_rows = session.query(ChunkModel).filter(
                ChunkModel.chunk_id == chunk_id
            ).update({'embedding_vector': embedding})
            
            success = updated_rows > 0
            if success:
                self.logger.info(f"Updated embedding for chunk: {chunk_id}")
            
            return success
    
    def get_chunks_by_page(self, document_id: str, page_number: int) -> List[TextChunk]:
        """Get chunks for a specific page."""
        with self.connection_manager.get_session() as session:
            chunk_models = session.query(ChunkModel).filter(
                and_(
                    ChunkModel.document_id == UUID(document_id),
                    ChunkModel.page_number == page_number
                )
            ).order_by(ChunkModel.chunk_index).all()
            
            return [
                TextChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=str(chunk.document_id),
                    content=chunk.content,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_metadata=chunk.metadata or {}
                ) for chunk in chunk_models
            ]


class ExtractionRepository(BaseRepository):
    """Repository for extraction result database operations."""
    
    def create_extraction_result(self, result: ExtractionResult) -> str:
        """Create extraction result and return its ID."""
        with self.connection_manager.get_session() as session:
            result_model = ExtractionResultModel(
                document_id=UUID(result.document_id),
                page_range_start=result.page_range[0],
                page_range_end=result.page_range[1],
                extracted_fields=result.extracted_fields,
                confidence_scores=result.confidence_scores,
                agent_id=result.agent_id
            )
            
            session.add(result_model)
            session.flush()
            result_id = str(result_model.id)
            
            self.logger.info(f"Created extraction result: {result_id}")
            return result_id
    
    def get_extraction_results_by_document(self, document_id: str) -> List[ExtractionResult]:
        """Get all extraction results for a document."""
        with self.connection_manager.get_session() as session:
            result_models = session.query(ExtractionResultModel).filter(
                ExtractionResultModel.document_id == UUID(document_id)
            ).order_by(ExtractionResultModel.created_at).all()
            
            return [
                ExtractionResult(
                    document_id=str(result.document_id),
                    page_range=(result.page_range_start, result.page_range_end),
                    extracted_fields=result.extracted_fields or {},
                    confidence_scores=result.confidence_scores or {},
                    agent_id=result.agent_id,
                    timestamp=result.created_at
                ) for result in result_models
            ]
    
    def get_extraction_results_by_page_range(self, document_id: str, start_page: int, end_page: int) -> List[ExtractionResult]:
        """Get extraction results for a specific page range."""
        with self.connection_manager.get_session() as session:
            result_models = session.query(ExtractionResultModel).filter(
                and_(
                    ExtractionResultModel.document_id == UUID(document_id),
                    ExtractionResultModel.page_range_start >= start_page,
                    ExtractionResultModel.page_range_end <= end_page
                )
            ).all()
            
            return [
                ExtractionResult(
                    document_id=str(result.document_id),
                    page_range=(result.page_range_start, result.page_range_end),
                    extracted_fields=result.extracted_fields or {},
                    confidence_scores=result.confidence_scores or {},
                    agent_id=result.agent_id,
                    timestamp=result.created_at
                ) for result in result_models
            ]


class QueryRepository(BaseRepository):
    """Repository for query log and result database operations."""
    
    def create_query_log(self, query_log: QueryLog) -> str:
        """Create query log and return its ID."""
        with self.connection_manager.get_session() as session:
            log_model = QueryLogModel(
                query_id=query_log.query_id,
                user_id=query_log.user_id,
                query_text=query_log.query_text,
                query_type=query_log.query_type,
                filters=query_log.filters,
                response_time_ms=query_log.response_time_ms
            )
            
            session.add(log_model)
            session.flush()
            log_id = str(log_model.id)
            
            self.logger.info(f"Created query log: {log_id}")
            return log_id
    
    def create_query_result(self, query_result: QueryResult) -> str:
        """Create query result and return its ID."""
        with self.connection_manager.get_session() as session:
            result_model = QueryResultModel(
                query_id=query_result.query_id,
                result_type=query_result.result_type,
                result_data=query_result.result_data,
                confidence_score=query_result.confidence_score,
                source_documents=query_result.source_documents
            )
            
            session.add(result_model)
            session.flush()
            result_id = str(result_model.id)
            
            self.logger.info(f"Created query result: {result_id}")
            return result_id
    
    def get_queries_by_user(self, user_id: str, limit: int = 50) -> List[QueryLog]:
        """Get query logs by user ID."""
        with self.connection_manager.get_session() as session:
            log_models = session.query(QueryLogModel).filter(
                QueryLogModel.user_id == user_id
            ).order_by(desc(QueryLogModel.created_at)).limit(limit).all()
            
            return [
                QueryLog(
                    query_id=log.query_id,
                    user_id=log.user_id,
                    query_text=log.query_text,
                    query_type=log.query_type,
                    filters=log.filters or {},
                    response_time_ms=log.response_time_ms,
                    created_at=log.created_at
                ) for log in log_models
            ]
    
    def get_query_results(self, query_id: str) -> List[QueryResult]:
        """Get all results for a query."""
        with self.connection_manager.get_session() as session:
            result_models = session.query(QueryResultModel).filter(
                QueryResultModel.query_id == query_id
            ).order_by(QueryResultModel.created_at).all()
            
            return [
                QueryResult(
                    query_id=result.query_id,
                    result_type=result.result_type,
                    result_data=result.result_data or {},
                    confidence_score=result.confidence_score,
                    source_documents=result.source_documents or [],
                    created_at=result.created_at
                ) for result in result_models
            ]