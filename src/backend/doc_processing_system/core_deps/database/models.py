"""
SQLAlchemy models for the document processing system.
Defines database tables using SQLAlchemy ORM for PostgreSQL.
"""

from typing import Dict, Any
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, DateTime, Float, Text, Boolean,
    ForeignKey, JSON, ARRAY, UniqueConstraint, DECIMAL, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class BillStatus(enum.Enum):
    """Bill processing status enum."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAID = "PAID"


class BillModel(Base):
    """SQLAlchemy model for bills table."""
    __tablename__ = "bill"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bill_account_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    billing_period_start = Column(DateTime(timezone=True), nullable=True)
    billing_period_end = Column(DateTime(timezone=True), nullable=True)
    issue_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    currency = Column(String(3), nullable=False)
    amount_due = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Enum(BillStatus), nullable=False, default=BillStatus.PENDING)
    extracted_jsonb = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    version = Column(Integer, nullable=False, default=1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "bill_account_id": str(self.bill_account_id),
            "billing_period_start": self.billing_period_start.isoformat() if self.billing_period_start else None,
            "billing_period_end": self.billing_period_end.isoformat() if self.billing_period_end else None,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "currency": self.currency,
            "amount_due": float(self.amount_due) if self.amount_due else None,
            "status": self.status.value if self.status else None,
            "extracted_jsonb": self.extracted_jsonb or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "version": self.version
        }


class DocumentModel(Base):
    """SQLAlchemy model for documents table."""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), default=func.now())
    user_id = Column(String(255), nullable=False, index=True)
    processing_status = Column(String(50), default="uploaded", index=True)
    file_size = Column(Integer, nullable=False)
    page_count = Column(Integer)
    content_path = Column(String(500))
    content_hash = Column(String(64), nullable=False, index=True, unique=True)  # SHA-256 hash for duplicate detection
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "file_type": self.file_type,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "user_id": self.user_id,
            "processing_status": self.processing_status,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "content_path": self.content_path,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ChunkModel(Base):
    """SQLAlchemy model for chunks table."""
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    embedding_vector = Column(ARRAY(Float))
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    document = relationship("DocumentModel", back_populates="chunks")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_id": self.chunk_id,
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "embedding_vector": self.embedding_vector,
            "metadata": self.chunk_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StructuredDocumentModel(Base):
    """SQLAlchemy model for structured document extractions table."""
    __tablename__ = "structured_documents"
    
    document_id = Column(UUID(as_uuid=True), primary_key=True)
    extraction_index = Column(Integer, primary_key=True)
    document_name = Column(String(255), nullable=False, index=True)
    extraction_class = Column(String(100), nullable=False, index=True)
    extraction_text = Column(Text, nullable=False)
    attributes = Column(JSON, nullable=False)
    alignment_status = Column(String(50), nullable=False)
    group_index = Column(Integer, nullable=False)
    description = Column(Text)
    char_start_pos = Column(Integer, nullable=False)
    char_end_pos = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "document_id": str(self.document_id),
            "document_name": self.document_name,
            "extraction_class": self.extraction_class,
            "extraction_text": self.extraction_text,
            "attributes": self.attributes or {},
            "alignment_status": self.alignment_status,
            "extraction_index": self.extraction_index,
            "group_index": self.group_index,
            "description": self.description,
            "char_start_pos": self.char_start_pos,
            "char_end_pos": self.char_end_pos,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class QueryLogModel(Base):
    """SQLAlchemy model for query logs table."""
    __tablename__ = "query_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=False)
    filters = Column(JSON, default=dict)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    results = relationship("QueryResultModel", back_populates="query_log", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "query_id": self.query_id,
            "user_id": self.user_id,
            "query_text": self.query_text,
            "query_type": self.query_type,
            "filters": self.filters or {},
            "response_time_ms": self.response_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class QueryResultModel(Base):
    """SQLAlchemy model for query results table."""
    __tablename__ = "query_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id = Column(String(255), ForeignKey("query_logs.query_id", ondelete="CASCADE"), nullable=False, index=True)
    result_type = Column(String(50), nullable=False)
    result_data = Column(JSON, nullable=False)
    confidence_score = Column(Float, default=0.0)
    source_documents = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    query_log = relationship("QueryLogModel", back_populates="results")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "query_id": self.query_id,
            "result_type": self.result_type,
            "result_data": self.result_data or {},
            "confidence_score": self.confidence_score,
            "source_documents": self.source_documents or [],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


