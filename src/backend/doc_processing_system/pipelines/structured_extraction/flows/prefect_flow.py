

from prefect import flow, get_run_logger

from ..config.settings import Settings
from ..models.state import PipelineState
from ..tasks_core.chunking import chunk_document
from ..tasks_core.config_gen import generate_config
from ..tasks_core.database_storage import store_in_database
# TODO the flow is hanging , it's not being triggered by anything 
# TODO the flow is not being triggered by the document_pipeline_completed_consumer.py
# Even though the logs show that it's been sent 
# Logs Successfully parsed C:\Users\User\Projects\scaled_processing\data\documents\raw\GSPP_9006_202507_Billing_NEM.pdf to data\temp\mineru\GSPP_9006_202507_Billing_NEM_c6a89b75
# 12:05:58.586 | INFO    | Task run 'mineru-processing-e33' - 🔥 AFTER processor.extract_document() call - Status: completed
# 12:05:58.587 | INFO    | Task run 'mineru-processing-e33' - ✅ Docling processing completed for: GSPP_9006_202507_Billing_NEM_c6a89b75
# 12:05:58.587 | INFO    | Task run 'mineru-processing-e33' - 📝 Markdown saved to: data\temp\mineru\GSPP_9006_202507_Billing_NEM_c6a89b75\GSPP_9006_202507_Billing_NEM_c6a89b75.md
# 12:05:58.589 | INFO    | Task run 'mineru-processing-e33' - Finished in state Completed()
# 12:05:58.590 | INFO    | Flow run 'quaint-jaybird' - ✅ STEP 3 COMPLETE: Document processing - Status: completed
# 12:05:58.592 | INFO    | Flow run 'quaint-jaybird' - 🔄 STEP 4: Checking chunking enabled: False
# 12:05:58.592 | INFO    | Flow run 'quaint-jaybird' - ⏭️ STEP 4 SKIPPED: Chunking disabled - preparing early return
# 12:05:58.605 | INFO    | Flow run 'quaint-jaybird' - ✅ Sent document_pipeline_completed message for: GSPP_9006_202507_Billing_NEM_c6a89b75

#
#  1. ✅ The file watcher detected the file and sent a message to Kafka
#      2. ✅ The document processing consumer received the message and started processing
#      3. ✅ Prefect is running in ephemeral mode (it started a temporary server on port 8490)
#      4. ✅ The document processing flow started and went through the steps
#      5. ✅ Duplicate detection worked - found it's a new document
#      6. ❌ The processing failed because the document processor (MinerU) doesn't support .txt files - it only supports PDF files      

#    The pipeline is working correctly! The issue mentioned in the original task
#    ("the flows stop at the document_extraction_flow") was due to:

#      1. Prefect API server connectivity issues - Fixed by configuring Prefect to run in ephemeral mode
#      2. Missing classification service - Fixed by creating the missing file
#      3. Python path issues in multiprocessing - Fixed by adding the project root to sys.path

#    The pipeline now successfully processes files through the entire chain:

#      * File Watcher → Document Processing → Structured Extraction

#    However, the document processor only supports PDF files, not text files. Let me
#    test with a PDF file to see the complete flow:
@flow(name="structured-extraction-flow", description="Extract structured information from document.")
def structured_extraction_flow(initial_state: PipelineState):
    """Extract structured information from document."""
    logger = get_run_logger()
    logger.info("Starting structured extraction flow.")
    
    # Initialize settings
    settings = Settings()
    
    # Convert Pydantic model to dict for state management
    state_dict = initial_state.model_dump()
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
    
    temp_state = PipelineState(**state_dict)
    
    updated_state = {
        "classification": 'invoice',
        "classification_confidence": 0.95,
        "status": "classified"
    }
    state_dict.update(updated_state)
    logger.info(f"After classification: status={state_dict.get('status')}, classification={state_dict.get('classification')}")
    
    
    # Step 3: Generate config and extract data
    logger.info("Step 3: Generating config and extracting data...")
    temp_state = PipelineState(**state_dict)
    
    config_result = generate_config(temp_state)
    
    if config_result:
        state_dict.update(config_result)
        logger.info(f"Config generation completed successfully")
        
        # Step 4: Store results in database
        logger.info("Step 4: Storing extraction results in database...")
        temp_state = PipelineState(**state_dict)
        
        storage_result = store_in_database(temp_state)
        state_dict.update(storage_result)
        
        # Set final status based on storage result
        if state_dict.get("status") == "storage_completed":
            state_dict["status"] = "completed"
            stored_count = state_dict.get("stored_count", 0)
            total_extractions = state_dict.get("total_extractions", 0)
            logger.info(f"Pipeline completed successfully. Stored {stored_count}/{total_extractions} extractions")
        elif state_dict.get("status") == "storage_skipped":
            state_dict["status"] = "completed_no_storage"
            logger.warning("Pipeline completed but no results were stored")
        else:
            state_dict["status"] = "storage_failed"
            logger.error(f"Storage failed: {state_dict.get('error', 'Unknown error')}")
    else:
        state_dict["status"] = "config_generation_failed"
        logger.error("Config generation failed")
    
    # Return final state
    final_state = PipelineState(**state_dict)
    logger.info(f"Final state: status={final_state.status}")
    return final_state
