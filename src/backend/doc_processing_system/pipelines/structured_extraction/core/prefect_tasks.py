"""
Prefect tasks for structured extraction pipeline.
Converts LangGraph nodes to Prefect tasks with proper state management.

🚀 DEMO COMMANDS:
    # Quick demo (single document, ~30 seconds):
    python -m src.backend.doc_processing_system.pipelines.structured_extraction.core.quick_demo
    
    # Full demo (3 document types, ~2 minutes):
    python -m src.backend.doc_processing_system.pipelines.structured_extraction.core.demo_pipeline

📁 RESULTS LOCATION:
    demo_results/ (created automatically)
    - Contains JSON files with intermediate results for each step
    - Detailed task execution logs and processing stats

✨ FEATURES SHOWCASED:
    • Generic task wrapper reducing boilerplate from ~20 lines to 3 lines per task
    • Centralized state management in PipelineState model
    • Prefect native logging with get_run_logger()
    • Async standardization across all tasks
    • Critical vs non-critical task distinction
    • Enhanced error handling and monitoring
    • Task execution logging for debugging

📊 PIPELINE STEPS:
    1. Document Classification (non-critical)
    2. Context Loading (non-critical) 
    3. Preference Injection (non-critical)
    4. Document Chunking (critical)
    5. Sequential Discovery (critical)
    6. Config Generation (critical)
    7. Data Extraction (critical)

💡 ARCHITECTURE IMPROVEMENTS:
    • Eliminated redundant helper functions (_convert_state_to_langgraph, _update_state_from_result)
    • Moved state transformation logic to model methods (to_langgraph(), update_from_langgraph())
    • Added standardized error handling with state.fail() method
    • Implemented task execution monitoring with log_task_execution()
"""

import logging
from typing import Dict, Any, Callable, Union, Optional
from functools import wraps
from prefect import task, flow, get_run_logger

from ..config.settings import Settings
from ..models.state import PipelineState
from ..nodes.chunking import chunk_document as _chunk_document
from ..nodes.classification import classify_document as _classify_document
from ..nodes.context_loading import load_feedback_context as _load_feedback_context
from ..nodes.preference_injection import inject_user_preferences as _inject_user_preferences
from ..nodes.discovery import sequential_discovery as _sequential_discovery
from ..nodes.config_gen import generate_config as _generate_config
from ..nodes.extraction import extract_data as _extract_data
from ..services.field_template_manager import FieldTemplateManager
from ....core_deps.database.connection_manager import ConnectionManager


def create_pipeline_task(
    func: Callable,
    task_name: str,
    is_async: bool = True,
    critical: bool = False
):
    """Generic task wrapper to reduce boilerplate and standardize task patterns.
    
    Args:
        func: The underlying function to call (LangGraph node)
        task_name: Name of the task for logging and monitoring
        is_async: Whether the underlying function is async
        critical: Whether failure should stop the pipeline
    """
    def task_decorator(prefect_task_func):
        @wraps(prefect_task_func)
        async def wrapper(state: PipelineState, *args, **kwargs) -> PipelineState:
            logger = get_run_logger()
            
            try:
                logger.info(f"Starting {task_name}")
                state.log_task_execution(task_name, "started")
                
                # Convert to LangGraph format using centralized method
                langgraph_state = state.to_langgraph()
                
                # Call the underlying function
                if is_async:
                    result = await func(langgraph_state, *args, **kwargs)
                else:
                    result = func(langgraph_state, *args, **kwargs)
                
                # Update state using centralized method
                state.update_from_langgraph(result)
                
                # Log success
                state.log_task_execution(task_name, "completed")
                logger.info(f"{task_name} completed successfully")
                
                return state
                
            except Exception as e:
                error_msg = f"{task_name} failed: {e}"
                logger.error(error_msg)
                
                # Use centralized error handling
                state.fail(
                    error_msg, 
                    f"{task_name.lower().replace(' ', '_')}_failed"
                )
                state.log_task_execution(task_name, "failed", error=str(e))
                
                # Re-raise if critical, otherwise continue
                if critical:
                    raise
                
                return state
                
        return wrapper
    return task_decorator


@task
@create_pipeline_task(_classify_document, "Document Classification", is_async=True, critical=False)
async def classify_document_task(state: PipelineState) -> PipelineState:
    """Classify document type using classification service."""
    pass  # Implementation handled by decorator


@task
@create_pipeline_task(_load_feedback_context, "Context Loading", is_async=True, critical=False)
async def load_feedback_context_task(state: PipelineState) -> PipelineState:
    """Load user feedback context for enhanced extraction."""
    pass  # Implementation handled by decorator


@task
@create_pipeline_task(_inject_user_preferences, "Preference Injection", is_async=True, critical=False)
async def inject_user_preferences_task(state: PipelineState) -> PipelineState:
    """Inject user preferences into the extraction pipeline."""
    pass  # Implementation handled by decorator


@task
@create_pipeline_task(_chunk_document, "Document Chunking", is_async=False, critical=True)
async def chunk_document_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Chunk document into processing batches."""
    pass  # Implementation handled by decorator


async def _template_based_discovery(state: PipelineState, settings: Settings) -> PipelineState:
    """Create schema from user template, bypassing Sequential Discovery."""
    logger = get_run_logger()
    
    try:
        user_id = state.user_id
        classification = getattr(state, "classification", "unknown")
        chunks = getattr(state, "chunks", [])
        
        # Initialize template manager
        connection_manager = ConnectionManager()
        template_manager = FieldTemplateManager(connection_manager)
        
        # Create progressive results from template
        progressive_results = template_manager.create_schema_from_template(
            user_id=user_id, 
            classification=classification,
            chunks=chunks
        )
        
        if progressive_results:
            logger.info(f"Generated schema from template with {len(progressive_results[0].discovered_fields)} fields")
            return {
                **state.to_langgraph(),
                "progressive_results": progressive_results,
                "status": "discovery_complete",
                "discovery_method": "template_based"
            }
        else:
            logger.warning("Failed to generate schema from template, falling back to sequential discovery")
            # Fall back to sequential discovery
            return await _sequential_discovery(state.to_langgraph(), settings)
            
    except Exception as e:
        logger.error(f"Template-based discovery failed: {e}, falling back to sequential discovery")
        # Fall back to sequential discovery
        return await _sequential_discovery(state.to_langgraph(), settings)


@task
@create_pipeline_task(_sequential_discovery, "Sequential Discovery", is_async=True, critical=True)
async def sequential_discovery_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Process chunks sequentially to discover schemas or use template if available."""
    logger = get_run_logger()
    
    # Check if user has a template for this classification
    try:
        user_id = state.user_id
        classification = getattr(state, "classification", "unknown")
        
        logger.info(f"🔍 Template check: user_id={user_id}, classification={classification}")
        
        if classification != "unknown":
            connection_manager = ConnectionManager()
            template_manager = FieldTemplateManager(connection_manager)
            
            has_template = template_manager.has_template(user_id, classification)
            logger.info(f"🔍 Has template for {user_id}/{classification}: {has_template}")
            
            if has_template:
                logger.info(f"✅ Using field template for {classification}, bypassing Sequential Discovery")
                return await _template_based_discovery(state, settings)
        
        logger.info("❌ No template found, proceeding with Sequential Discovery")
    except Exception as e:
        logger.warning(f"❌ Template check failed: {e}, proceeding with Sequential Discovery")
        import traceback
        traceback.print_exc()
    
    # Original sequential discovery implementation handled by decorator
    pass


@task
@create_pipeline_task(_generate_config, "Config Generation", is_async=False, critical=True)
async def generate_config_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Generate extraction configuration from discovered schemas."""
    pass  # Implementation handled by decorator


@task
@create_pipeline_task(_extract_data, "Data Extraction", is_async=False, critical=True)
async def extract_data_task(state: PipelineState, settings: Settings) -> PipelineState:
    """Extract structured data using generated configuration."""
    pass  # Implementation handled by decorator


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
    logger = get_run_logger()
    
    # Create initial state
    state = PipelineState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        status="started"
    )
    
    logger.info(f"Starting structured extraction pipeline for document {document_id}")
    
    try:
        # Step 1: Document Classification (non-critical)
        state = await classify_document_task(state)
        
        # Step 2: Load Feedback Context (non-critical)
        state = await load_feedback_context_task(state)
        
        # Step 3: Inject User Preferences (non-critical)
        state = await inject_user_preferences_task(state)
        
        # Step 4: Document Chunking (critical)
        state = await chunk_document_task(state, settings)
        if state.status.endswith("_failed"):
            return state
        
        # Step 5: Sequential Discovery (critical)
        state = await sequential_discovery_task(state, settings)
        if state.status.endswith("_failed"):
            return state
        
        # Step 6: Generate Config (critical)
        state = await generate_config_task(state, settings)
        if state.status.endswith("_failed"):
            return state
        
        # Step 7: Extract Data (critical)
        state = await extract_data_task(state, settings)
        if state.status.endswith("_failed"):
            return state
        
        # Mark as completed
        state.status = "completed"
        logger.info(f"Pipeline completed successfully for document {document_id}")
        
        return state
        
    except Exception as e:
        logger.error(f"Pipeline failed with unexpected error: {e}")
        return state.fail(str(e), "pipeline_failed")


def create_initial_state(document_text: str, document_id: str, user_id: str = "default_user") -> PipelineState:
    """Create initial state for the Prefect workflow."""
    return PipelineState(
        document_text=document_text,
        document_id=document_id,
        user_id=user_id,
        status="started"
    )