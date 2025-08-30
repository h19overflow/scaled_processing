"""
Query-related data models for query processing and results.
Contains models for user queries, search results, and hybrid responses.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel

from .chunk import VectorSearchResult


class QueryType(str, Enum):
    """Types of queries supported by the system."""
    RAG_ONLY = "rag_only"
    STRUCTURED_ONLY = "structured_only"
    HYBRID = "hybrid"


class UserQuery(BaseModel):
    """Model for user queries."""
    query_id: str
    query_text: str
    query_type: QueryType
    user_id: str
    filters: Dict[str, Any] = {}


class RAGQueryResult(BaseModel):
    """Model for RAG query results."""
    query_id: str
    retrieved_chunks: List[VectorSearchResult]
    generated_response: str
    source_documents: List[str]
    confidence_score: float


class StructuredQueryResult(BaseModel):
    """Model for structured query results."""
    query_id: str
    filtered_data: List[Dict[str, Any]]
    aggregated_results: Dict[str, Any] = {}
    matching_documents: List[str]


class HybridQueryResult(BaseModel):
    """Model for hybrid query results combining RAG and structured data."""
    query_id: str
    rag_result: RAGQueryResult
    structured_result: StructuredQueryResult
    combined_response: str
    confidence_score: float


class QueryLog(BaseModel):
    """Model for query logging."""
    id: Optional[UUID] = None
    query_id: str
    user_id: str
    query_text: str
    query_type: str
    filters: Dict[str, Any] = {}
    response_time_ms: int
    created_at: Optional[datetime] = None


class QueryResult(BaseModel):
    """Model for storing query results."""
    id: Optional[UUID] = None
    query_id: str
    result_type: str
    result_data: Dict[str, Any]
    confidence_score: float
    source_documents: List[str] = []
    created_at: Optional[datetime] = None