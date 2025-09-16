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


# Extraction models
from .extraction import (
    FieldSpecification,
    FieldInitRequest,
    AgentScalingConfig,
    ExtractionResult,
    ExtractionSchema
)

# Event models
from .events import (
    DocumentReceivedEvent,
    WorkflowInitializedEvent,
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

    # Extraction models
    "FieldSpecification",
    "FieldInitRequest",
    "AgentScalingConfig",
    "ExtractionResult",
    "ExtractionSchema",
    

    # Event models
    "DocumentReceivedEvent",
    "WorkflowInitializedEvent",
]