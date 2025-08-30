"""
Event data models for Kafka messaging system.
Contains all event models for inter-service communication.
"""

from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel

from .document import ParsedDocument
from .chunk import TextChunk, ValidatedEmbedding
from .extraction import FieldSpecification, AgentScalingConfig, ExtractionResult
from .query import UserQuery, RAGQueryResult, StructuredQueryResult, HybridQueryResult


# Document Upload Events
class DocumentReceivedEvent(BaseModel):
    """Event published when document is received and parsed."""
    document_id: str
    parsed_document: ParsedDocument
    timestamp: datetime
    topic: str = "document-received"


class WorkflowInitializedEvent(BaseModel):
    """Event published when workflows are initialized."""
    document_id: str
    workflow_types: List[str]
    status: str
    topic: str = "workflow-initialized"


# RAG Workflow Events
class ChunkingCompleteEvent(BaseModel):
    """Event published when document chunking is complete."""
    document_id: str
    chunks: List[TextChunk]
    chunk_count: int
    topic: str = "chunking-complete"


class EmbeddingReadyEvent(BaseModel):
    """Event published when embeddings are ready."""
    document_id: str
    validated_embedding: ValidatedEmbedding
    topic: str = "embedding-ready"


class IngestionCompleteEvent(BaseModel):
    """Event published when RAG ingestion is complete."""
    document_id: str
    vector_count: int
    collection_name: str
    topic: str = "ingestion-complete"


# Structured Extraction Events
class FieldInitCompleteEvent(BaseModel):
    """Event published when field initialization is complete."""
    document_id: str
    field_specifications: List[FieldSpecification]
    discovery_method: str
    topic: str = "field-init-complete"


class AgentScalingCompleteEvent(BaseModel):
    """Event published when agent scaling is complete."""
    document_id: str
    scaling_config: AgentScalingConfig
    topic: str = "agent-scaling-complete"


class ExtractionTaskMessage(BaseModel):
    """Message for extraction tasks sent to agents."""
    task_id: str
    document_id: str
    page_range: tuple
    field_specs: List[FieldSpecification]
    agent_id: str
    topic: str = "extraction-tasks"


class ExtractionCompleteEvent(BaseModel):
    """Event published when extraction is complete."""
    document_id: str
    extraction_results: List[ExtractionResult]
    completion_status: str
    topic: str = "extraction-complete"


# Query Processing Events
class QueryReceivedEvent(BaseModel):
    """Event published when query is received."""
    query_id: str
    user_query: UserQuery
    topic: str = "query-received"


class RAGQueryCompleteEvent(BaseModel):
    """Event published when RAG query is complete."""
    query_id: str
    rag_result: RAGQueryResult
    topic: str = "rag-query-complete"


class StructuredQueryCompleteEvent(BaseModel):
    """Event published when structured query is complete."""
    query_id: str
    structured_result: StructuredQueryResult
    topic: str = "structured-query-complete"


class HybridQueryCompleteEvent(BaseModel):
    """Event published when hybrid query is complete."""
    query_id: str
    hybrid_result: HybridQueryResult
    topic: str = "hybrid-query-complete"