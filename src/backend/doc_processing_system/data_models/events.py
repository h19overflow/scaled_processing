"""
Event data models for Kafka messaging system.
Contains all event models for inter-service communication.
"""

from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel

from .document import ParsedDocument


# Document Upload Events
class FileDetectedEvent(BaseModel):
    """Event published when a new file is detected in the raw directory."""
    file_path: str
    filename: str
    file_size: int
    file_extension: str
    detected_at: str
    event_type: str
    topic: str = "file-detected"


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



