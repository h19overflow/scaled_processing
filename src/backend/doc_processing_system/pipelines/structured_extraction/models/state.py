"""
State models for the multi-agent workflow.
"""

from typing import Dict, Any, List
from typing_extensions import TypedDict, Optional

from .document import DocumentChunk, DocumentSchema
from .schema import ProgressiveSchema, ConsolidatedSchema


class MultiAgentState(TypedDict):
    """State for the multi-agent extraction workflow."""
    document_text: Optional[str]
    document_id: Optional[str]
    chunks: Optional[List[DocumentChunk]]
    progressive_results: Optional[List[ProgressiveSchema]]
    consolidated_schema: Optional[ConsolidatedSchema]
    final_schema: Optional[DocumentSchema]
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
