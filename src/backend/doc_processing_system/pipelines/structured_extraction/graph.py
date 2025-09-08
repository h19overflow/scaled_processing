"""
Graph orchestrator for multi-agent structured extraction.
Minimal abstraction LangGraph builder for Prefect integration.
"""

from langgraph.graph import StateGraph, END
from functools import partial

from .models.state import MultiAgentState
from .config.settings import Settings
from .nodes import (
    chunk_document,
    sequential_discovery,
    consolidate_schema,
    generate_config,
    extract_data
)
from .nodes.classification import classify_document
from .nodes.context_loading import load_feedback_context
from .nodes.preference_injection import inject_user_preferences


# Flow validated: classification -> feedback -> preferences -> chunking -> discovery -> consolidation -> config -> extraction
def build_graph(settings: Settings):
    """Build and compile the multi-agent extraction graph."""

    # Create workflow with state type
    workflow = StateGraph(MultiAgentState)

    # Create node functions with settings bound
    chunk_node = partial(chunk_document, settings=settings)
    discovery_node = partial(sequential_discovery, settings=settings)
    consolidation_node = partial(consolidate_schema, settings=settings)
    config_node = partial(generate_config, settings=settings)
    extraction_node = partial(extract_data, settings=settings)

    # Add enhancement nodes
    workflow.add_node("classify_document", classify_document)
    workflow.add_node("load_feedback_context", load_feedback_context)
    workflow.add_node("inject_user_preferences", inject_user_preferences)

    # Add original nodes
    workflow.add_node("chunk_document", chunk_node)
    workflow.add_node("sequential_discovery", discovery_node)
    workflow.add_node("consolidate_schema", consolidation_node)
    workflow.add_node("generate_config", config_node)
    workflow.add_node("extract_data", extraction_node)

    # Define workflow edges - enhancement steps first
    workflow.set_entry_point("classify_document")
    workflow.add_edge("classify_document", "load_feedback_context")
    workflow.add_edge("load_feedback_context", "inject_user_preferences")
    workflow.add_edge("inject_user_preferences", "chunk_document")

    # Original workflow continues
    workflow.add_edge("chunk_document", "sequential_discovery")
    workflow.add_edge("sequential_discovery", "consolidate_schema")
    workflow.add_edge("consolidate_schema", "generate_config")
    workflow.add_edge("generate_config", "extract_data")
    workflow.add_edge("extract_data", END)

    # Compile and return
    return workflow.compile()


def create_initial_state(document_text: str, document_id: str, user_id: str = "default_user") -> MultiAgentState:
    """Create initial state for the enhanced workflow."""
    return MultiAgentState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        chunks=[],
        progressive_results=[],
        consolidated_schema=None,
        final_schema=None,
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
