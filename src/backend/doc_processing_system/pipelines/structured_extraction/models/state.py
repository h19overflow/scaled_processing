"""
State models for the multi-agent workflow.
"""

import logging
from typing import Dict, Any, List
from typing_extensions import TypedDict, Optional
from pydantic import BaseModel, Field

from .document import DocumentChunk
from .schema import ProgressiveSchema, FieldSchema


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
    # Discovery tracking
    discovery_method: Optional[str] = None  # "template_based" or "sequential"
    # Monitoring fields
    task_execution_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_langgraph(self) -> Dict[str, Any]:
        """Convert PipelineState to LangGraph-compatible dict format."""
        logger = logging.getLogger(__name__)
        
        langgraph_state = self.model_dump()
        
        # Debug logging
        logger.debug(f"Converting state - progressive_results type: {type(langgraph_state.get('progressive_results'))}")
        if langgraph_state.get("progressive_results"):
            logger.debug(f"Progressive results count: {len(langgraph_state['progressive_results'])}")
            for i, result in enumerate(langgraph_state['progressive_results']):
                logger.debug(f"Result {i} type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        
        # Ensure chunks are proper DocumentChunk objects
        if langgraph_state.get("chunks") and len(langgraph_state["chunks"]) > 0:
            chunks = []
            for chunk_data in langgraph_state["chunks"]:
                if isinstance(chunk_data, dict):
                    chunks.append(DocumentChunk(**chunk_data))
                else:
                    chunks.append(chunk_data)
            langgraph_state["chunks"] = chunks
        
        # Ensure progressive_results are proper ProgressiveSchema objects
        if langgraph_state.get("progressive_results") and len(langgraph_state["progressive_results"]) > 0:
            progressive_results = []
            for i, result_data in enumerate(langgraph_state["progressive_results"]):
                logger.debug(f"Processing result {i}: type={type(result_data)}")
                
                if isinstance(result_data, dict):
                    # Convert discovered_fields if they're dicts
                    if "discovered_fields" in result_data and result_data["discovered_fields"]:
                        fields = []
                        for field_data in result_data["discovered_fields"]:
                            if isinstance(field_data, dict):
                                fields.append(FieldSchema(**field_data))
                            else:
                                fields.append(field_data)
                        result_data["discovered_fields"] = fields
                    
                    try:
                        progressive_schema = ProgressiveSchema(**result_data)
                        progressive_results.append(progressive_schema)
                        logger.debug(f"Successfully created ProgressiveSchema {i} with {len(progressive_schema.discovered_fields)} fields")
                    except Exception as e:
                        logger.error(f"Failed to create ProgressiveSchema from {result_data}: {e}")
                        progressive_results.append(result_data)  # Fallback to original
                else:
                    progressive_results.append(result_data)
                    
            langgraph_state["progressive_results"] = progressive_results
            logger.debug(f"Final progressive_results count: {len(progressive_results)}")
        
        return langgraph_state
    
    def update_from_langgraph(self, result: Dict[str, Any]) -> "PipelineState":
        """Update PipelineState with results from LangGraph node functions."""
        # Handle chunks specially to maintain DocumentChunk objects
        if result.get("chunks"):
            chunks = []
            for chunk in result["chunks"]:
                if isinstance(chunk, DocumentChunk):
                    chunks.append(chunk)
                elif isinstance(chunk, dict):
                    chunks.append(DocumentChunk(**chunk))
                else:
                    chunks.append(chunk)
            self.chunks = chunks
        
        # Handle progressive_results specially to maintain ProgressiveSchema objects
        if result.get("progressive_results"):
            progressive_results = []
            for result_item in result["progressive_results"]:
                if isinstance(result_item, ProgressiveSchema):
                    progressive_results.append(result_item)
                elif isinstance(result_item, dict):
                    # Convert discovered_fields if they're dicts
                    if "discovered_fields" in result_item and result_item["discovered_fields"]:
                        fields = []
                        for field_data in result_item["discovered_fields"]:
                            if isinstance(field_data, FieldSchema):
                                fields.append(field_data)
                            elif isinstance(field_data, dict):
                                fields.append(FieldSchema(**field_data))
                            else:
                                fields.append(field_data)
                        result_item["discovered_fields"] = fields
                    progressive_results.append(ProgressiveSchema(**result_item))
                else:
                    progressive_results.append(result_item)
            self.progressive_results = progressive_results
        
        # Update other fields
        if result.get("config"):
            self.config = result["config"]
        if result.get("extractions"):
            self.extractions = result["extractions"]
        if result.get("document_text"):
            self.document_text = result["document_text"]
        if result.get("classification"):
            self.classification = result["classification"]
        if result.get("classification_confidence") is not None:
            self.classification_confidence = result["classification_confidence"]
        if result.get("feedback_context"):
            self.feedback_context = result["feedback_context"]
        if result.get("user_preferences"):
            self.user_preferences = result["user_preferences"]
        if result.get("discovery_method"):
            self.discovery_method = result["discovery_method"]
        
        # Always update status and error
        self.status = result.get("status", self.status)
        if result.get("error"):
            self.error = result["error"]
        
        return self
    
    def fail(self, error_message: str, status: str = "failed") -> "PipelineState":
        """Standardized method to mark state as failed with error context."""
        self.status = status
        self.error = error_message
        return self
    
    def log_task_execution(self, task_name: str, status: str, **kwargs) -> None:
        """Log task execution for monitoring and debugging."""
        import time
        log_entry = {
            "task_name": task_name,
            "status": status,
            "timestamp": time.time(),
            **kwargs
        }
        self.task_execution_log.append(log_entry)
