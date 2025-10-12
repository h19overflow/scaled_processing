"""
Data models package for the document processing system.
Provides all flows data structures used across the system.
"""

# Document models
from .document import (
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



__all__ = [
    # Document models
    "ProcessingStatus",
    "Document",
    
    # Chunk models

    # Extraction models
    "FieldSpecification",
    "FieldInitRequest",
    "AgentScalingConfig",
    "ExtractionResult",
    "ExtractionSchema",
    

]