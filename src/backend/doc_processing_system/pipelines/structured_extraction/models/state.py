"""
State models for the multi-agent workflow.
"""

from typing import Dict, Any, List
from typing_extensions import  Optional
from pydantic import BaseModel

from .document import DocumentChunk
class PipelineState(BaseModel):
    """Pydantic state model for Prefect workflow."""
    document_text: Optional[str] = None
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    chunks: Optional[List[DocumentChunk]] = None
    config: Optional[Dict[str, Any]] = None
    extractions: Optional[List[Dict[str, Any]]] = None
    status: str = "started"
    error: str = ""
    # Enhancement fields
    classification: Optional[str] = None
    classification_confidence: Optional[float] = None
    user_id: str = "test_user"

    class Config:
        arbitrary_types_allowed = True
