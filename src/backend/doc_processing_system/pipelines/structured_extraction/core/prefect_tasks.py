

from prefect import flow, get_run_logger
import asyncio

from ..config.settings import Settings
from ..models.state import PipelineState
from ..nodes.chunking import chunk_document
from ..nodes.classification import classify_document
from ..nodes.config_gen import generate_config

@flow(name="structured-extraction-flow", description="Extract structured information from document.")
def structured_extraction_flow(initial_state: PipelineState):
    """Extract structured information from document."""
    logger = get_run_logger()
    logger.info("Starting structured extraction flow.")
    
    # Initialize settings
    settings = Settings()
    
    # Convert Pydantic model to dict for state management
    state_dict = initial_state.dict()
    logger.info(f"Initial state: {state_dict}")
    
    # Step 1: Chunk the document
    logger.info("Step 1: Chunking document...")
    chunk_result = chunk_document(initial_state, settings)
    
    # Update state with chunking results
    state_dict.update(chunk_result)
    chunks = state_dict.get('chunks', [])
    chunks_count = len(chunks) if chunks is not None else 0
    logger.info(f"After chunking: status={state_dict.get('status')}, chunks_count={chunks_count}")
    
    # Check if chunking was successful
    if state_dict.get("status") == "error":
        logger.error(f"Chunking failed: {state_dict.get('error')}")
        return PipelineState(**state_dict)
    
    # Step 2: Classify the document
    logger.info("Step 2: Classifying document...")
    # Create new PipelineState object for classification
    temp_state = PipelineState(**state_dict)
    
    # Run classification (async task)
    classification_result = asyncio.run(classify_document(temp_state))
    
    # Update state with classification results  
    state_dict.update(classification_result)
    logger.info(f"After classification: status={state_dict.get('status')}, classification={state_dict.get('classification')}")
    
    # Check if classification was successful
    if state_dict.get("status") == "classification_failed":
        logger.warning(f"Classification failed: {state_dict.get('error', 'Unknown error')}")
        # Continue with unknown classification
    
    # Step 3: Generate config and extract data
    logger.info("Step 3: Generating config and extracting data...")
    temp_state = PipelineState(**state_dict)
    
    config_result = generate_config(temp_state)
    
    if config_result:
        state_dict.update(config_result)
        state_dict["status"] = "completed"
        logger.info(f"Extraction completed successfully")
    else:
        state_dict["status"] = "config_generation_failed"
        logger.error("Config generation failed")
    
    # Return final state
    final_state = PipelineState(**state_dict)
    logger.info(f"Final state: status={final_state.status}")
    return final_state
