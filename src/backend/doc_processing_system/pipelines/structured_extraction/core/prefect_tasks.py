"""
Prefect tasks for structured extraction pipeline.
Converts LangGraph nodes to Prefect tasks with proper state management.
"""

import logging
from typing import Dict, Any
from prefect import task, flow

from ..config.settings import Settings
from ..models.state import PipelineState
from ..nodes.chunking import chunk_document as _chunk_document
from ..nodes.classification import classify_document as _classify_document
from ..nodes.context_loading import load_feedback_context as _load_feedback_context
from ..nodes.preference_injection import inject_user_preferences as _inject_user_preferences
from ..nodes.discovery import sequential_discovery as _sequential_discovery
from ..nodes.config_gen import generate_config as _generate_config
from ..nodes.extraction import extract_data as _extract_data


@task
async def classify_document_task(state: PipelineState) -> PipelineState:
    """Classify document type using classification service."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original classification function
        result = await _classify_document(langgraph_state)
        
        # Update state with results
        state.classification = result.get("classification")
        state.classification_confidence = result.get("classification_confidence")
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Document classified as '{state.classification}' with confidence {state.classification_confidence}")
        return state
        
    except Exception as e:
        logger.error(f"Classification task failed: {e}")
        state.classification = "unknown"
        state.classification_confidence = 0.0
        state.status = "classification_failed"
        state.error = str(e)
        return state


@task
async def load_feedback_context_task(state: PipelineState) -> PipelineState:
    """Load user feedback context for enhanced extraction."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original context loading function
        result = await _load_feedback_context(langgraph_state)
        
        # Update state with results
        state.feedback_context = result.get("feedback_context")
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Loaded feedback context: {bool(state.feedback_context)}")
        return state
        
    except Exception as e:
        logger.error(f"Context loading task failed: {e}")
        state.status = "context_loading_failed"
        state.error = str(e)
        return state


@task  
async def inject_user_preferences_task(state: PipelineState) -> PipelineState:
    """Inject user preferences into the extraction pipeline."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original preference injection function
        result = await _inject_user_preferences(langgraph_state)
        
        # Update state with results
        state.user_preferences = result.get("user_preferences")
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Injected user preferences: {bool(state.user_preferences)}")
        return state
        
    except Exception as e:
        logger.error(f"Preference injection task failed: {e}")
        state.status = "preference_injection_failed"
        state.error = str(e)
        return state


@task
def chunk_document_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Chunk document into processing batches."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original chunking function
        result = _chunk_document(langgraph_state, settings)
        
        # Update state with results
        if result.get("chunks"):
            state.chunks = result["chunks"]
        if result.get("document_text"):
            state.document_text = result["document_text"]
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Created {len(state.chunks or [])} chunks")
        return state
        
    except Exception as e:
        logger.error(f"Chunking task failed: {e}")
        state.status = "chunking_failed"
        state.error = str(e)
        return state


@task
async def sequential_discovery_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Process chunks sequentially to discover schemas."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original discovery function
        result = await _sequential_discovery(langgraph_state, settings)
        
        # Update state with results
        if result.get("progressive_results"):
            state.progressive_results = result["progressive_results"]
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Discovery completed with {len(state.progressive_results or [])} results")
        return state
        
    except Exception as e:
        logger.error(f"Discovery task failed: {e}")
        state.status = "discovery_failed"
        state.error = str(e)
        return state


@task
async def generate_config_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Generate extraction configuration from discovered schemas."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original config generation function
        result = await _generate_config(langgraph_state, settings)
        
        # Update state with results
        if result.get("config"):
            state.config = result["config"]
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Generated extraction config: {bool(state.config)}")
        return state
        
    except Exception as e:
        logger.error(f"Config generation task failed: {e}")
        state.status = "config_generation_failed"
        state.error = str(e)
        return state


@task
async def extract_data_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Extract structured data using generated configuration."""
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to LangGraph format for compatibility
        langgraph_state = state.model_dump()
        
        # Call original extraction function
        result = await _extract_data(langgraph_state, settings)
        
        # Update state with results
        if result.get("extractions"):
            state.extractions = result["extractions"]
        state.status = result.get("status", state.status)
        if result.get("error"):
            state.error = result["error"]
            
        logger.info(f"Extracted {len(state.extractions or [])} data items")
        return state
        
    except Exception as e:
        logger.error(f"Extraction task failed: {e}")
        state.status = "extraction_failed"
        state.error = str(e)
        return state


@flow(name="structured-extraction-pipeline")
async def structured_extraction_flow(
    document_text: str, 
    document_id: str, 
    settings: Settings,
    user_id: str = "default_user"
) -> PipelineState:
    """
    Prefect flow for structured extraction pipeline.
    
    Replaces the LangGraph workflow with sequential Prefect task execution.
    Maintains the same processing order as the original workflow.
    """
    logger = logging.getLogger(__name__)
    
    # Create initial state
    state = PipelineState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        status="started"
    )
    
    logger.info(f"Starting structured extraction pipeline for document {document_id}")
    
    try:
        # Step 1: Document Classification
        state = await classify_document_task(state)
        if state.error:
            logger.warning(f"Classification failed but continuing: {state.error}")
        
        # Step 2: Load Feedback Context
        state = await load_feedback_context_task(state)
        if state.error:
            logger.warning(f"Context loading failed but continuing: {state.error}")
        
        # Step 3: Inject User Preferences
        state = await inject_user_preferences_task(state)
        if state.error:
            logger.warning(f"Preference injection failed but continuing: {state.error}")
        
        # Step 4: Document Chunking
        state = chunk_document_task(state, settings)
        if state.error:
            logger.error(f"Chunking failed: {state.error}")
            state.status = "failed"
            return state
        
        # Step 5: Sequential Discovery
        state = await sequential_discovery_task(state, settings)
        if state.error:
            logger.error(f"Discovery failed: {state.error}")
            state.status = "failed"
            return state
        
        # Step 6: Generate Config
        state = await generate_config_task(state, settings)
        if state.error:
            logger.error(f"Config generation failed: {state.error}")
            state.status = "failed"
            return state
        
        # Step 7: Extract Data
        state = await extract_data_task(state, settings)
        if state.error:
            logger.error(f"Data extraction failed: {state.error}")
            state.status = "failed"
            return state
        
        # Mark as completed
        state.status = "completed"
        logger.info(f"Pipeline completed successfully for document {document_id}")
        
        return state
        
    except Exception as e:
        logger.error(f"Pipeline failed with unexpected error: {e}")
        state.error = str(e)
        state.status = "failed"
        return state


def create_initial_state(document_text: str, document_id: str, user_id: str = "default_user") -> PipelineState:
    """Create initial state for the Prefect workflow."""
    return PipelineState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        status="started"
    )