"""
Graph orchestrator for multi-agent structured extraction.
Migrated from LangGraph to Prefect for workflow orchestration.
"""

from ..config.settings import Settings
from ..models.state import MultiAgentState, PipelineState
from .prefect_tasks import structured_extraction_flow


# Flow simplified: classification -> feedback -> preferences -> chunking -> discovery -> config -> extraction
def build_graph(settings: Settings):
    """Build and return the Prefect flow for structured extraction."""
    # Return the Prefect flow function with settings bound
    async def flow_wrapper(document_text: str, document_id: str, user_id: str = "default_user"):
        return await structured_extraction_flow(document_text, document_id, settings, user_id)
    
    return flow_wrapper


def create_flow(settings: Settings):
    """Create Prefect flow for structured extraction pipeline."""
    return build_graph(settings)


def create_initial_state(document_text: str, document_id: str, user_id: str = "default_user") -> PipelineState:
    """Create initial state for the Prefect workflow."""
    return PipelineState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        status="started"
    )


def create_initial_state_legacy(document_text: str, document_id: str, user_id: str = "default_user") -> MultiAgentState:
    """Create initial state for legacy LangGraph compatibility."""
    return MultiAgentState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        chunks=[],
        progressive_results=[],
        config=None,
        extractions=[],
        status="started",
        error="",
        # Enhancement fields
        classification=None,
        classification_confidence=None,
        feedback_context=None,
        user_preferences=None
    )
