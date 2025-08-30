"""
Data models package for the document processing system.
Provides all core data structures used across the system.
"""

# Document models
from .document import (
    FileType,
    UploadFile,
    DocumentMetadata,
    ParsedDocument,
    ProcessingStatus,
    Document
)

# Chunk models
from .chunk import (
    ChunkingRequest,
    TextChunk,
    ValidatedEmbedding,
    VectorSearchResult,
    Chunk
)

# Extraction models
from .extraction import (
    FieldSpecification,
    FieldInitRequest,
    AgentScalingConfig,
    ExtractionResult,
    ExtractionSchema
)

# Query models
from .query import (
    QueryType,
    UserQuery,
    RAGQueryResult,
    StructuredQueryResult,
    HybridQueryResult,
    QueryLog,
    QueryResult
)

# Event models
from .events import (
    DocumentReceivedEvent,
    WorkflowInitializedEvent,
    ChunkingCompleteEvent,
    EmbeddingReadyEvent,
    IngestionCompleteEvent,
    FieldInitCompleteEvent,
    AgentScalingCompleteEvent,
    ExtractionTaskMessage,
    ExtractionCompleteEvent,
    QueryReceivedEvent,
    RAGQueryCompleteEvent,
    StructuredQueryCompleteEvent,
    HybridQueryCompleteEvent
)

__all__ = [
    # Document models
    "FileType",
    "UploadFile", 
    "DocumentMetadata",
    "ParsedDocument",
    "ProcessingStatus",
    "Document",
    
    # Chunk models
    "ChunkingRequest",
    "TextChunk",
    "ValidatedEmbedding",
    "VectorSearchResult",
    "Chunk",
    
    # Extraction models
    "FieldSpecification",
    "FieldInitRequest",
    "AgentScalingConfig",
    "ExtractionResult",
    "ExtractionSchema",
    
    # Query models
    "QueryType",
    "UserQuery",
    "RAGQueryResult",
    "StructuredQueryResult",
    "HybridQueryResult",
    "QueryLog",
    "QueryResult",
    
    # Event models
    "DocumentReceivedEvent",
    "WorkflowInitializedEvent",
    "ChunkingCompleteEvent",
    "EmbeddingReadyEvent",
    "IngestionCompleteEvent",
    "FieldInitCompleteEvent",
    "AgentScalingCompleteEvent",
    "ExtractionTaskMessage",
    "ExtractionCompleteEvent",
    "QueryReceivedEvent",
    "RAGQueryCompleteEvent",
    "StructuredQueryCompleteEvent",
    "HybridQueryCompleteEvent"
]