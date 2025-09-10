"""
State models for the multi-agent workflow.
"""

from typing import Dict, Any, List
from typing_extensions import TypedDict, Optional
from pydantic import BaseModel, Field

from .document import DocumentChunk
from .schema import ProgressiveSchema


class MultiAgentState(TypedDict):
    """State for the multi-agent extraction workflow."""
    document_text: Optional[str]
    document_id: Optional[str]
    chunks: Optional[List[DocumentChunk]]
    progressive_results: Optional[List[ProgressiveSchema]]
    config: Optional[Dict[str, Any]]
    extractions: Optional[List[Dict[str, Any]]]
    status: Optional[str]
    error: Optional[str]
    # Enhancement fields
    classification: Optional[str]
    classification_confidence: Optional[float]
    user_id: Optional[str]
    feedback_context: Optional[Dict[str, Any]]
    user_preferences: Optional[Dict[str, Any]]
    # Monitoring fields
    task_execution_log: Optional[List[Dict[str, Any]]]


class PipelineState(BaseModel):
    """Pydantic state model for Prefect workflow."""
    document_text: Optional[str] = None
    document_id: Optional[str] = None
    chunks: Optional[List[DocumentChunk]] = None
    progressive_results: Optional[List[ProgressiveSchema]] = None
    config: Optional[Dict[str, Any]] = None
    extractions: Optional[List[Dict[str, Any]]] = None
    status: str = "started"
    error: str = ""
    # Enhancement fields
    classification: Optional[str] = None
    classification_confidence: Optional[float] = None
    user_id: str = "default_user"
    feedback_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    # Monitoring fields
    task_execution_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
