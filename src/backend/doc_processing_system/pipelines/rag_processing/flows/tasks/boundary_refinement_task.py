"""
Boundary Refinement Task - Stage 2 of RAG Processing Pipeline

Handles boundary refinement using LLM agents for chunk optimization.
Part of the modular RAG processing pipeline.
"""

import time
from typing import Dict, Any, List
from datetime import datetime

from prefect import task, get_run_logger
from .config import MAX_RETRIES, RETRY_DELAY, CHUNKING_TIMEOUT


@task(
    name="boundary_refinement",
    description="Refine chunk boundaries using LLM agents (Stage 2)",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=CHUNKING_TIMEOUT // 2,  # Half timeout for Stage 2
    tags=["chunking", "stage2", "boundary", "agents"]
)
async def boundary_refinement_task(
    stage1_result: Dict[str, Any],
    concurrent_agents: int = 10,
    model_name: str = "gemini-2.0-flash",
    boundary_context: int = 200
) -> Dict[str, Any]:
    """Refine chunk boundaries using concurrent LLM agents (Stage 2).
    
    Args:
        stage1_result: Results from semantic chunking task
        concurrent_agents: Number of concurrent boundary review agents
        model_name: LLM model for boundary decisions
        boundary_context: Context window for boundary analysis
        
    Returns:
        Dict containing refined chunks and boundary decisions
        
    Raises:
        ValueError: If boundary refinement fails
    """
    logger = get_run_logger()
    start_time = time.time()
    
    document_id = stage1_result["document_id"]
    initial_chunks = stage1_result["initial_chunks"]
    
    logger.info(f"🔄 Starting boundary refinement task (Stage 2) for {document_id}")
    logger.info(f"📊 Processing {len(initial_chunks)} initial chunks with {concurrent_agents} agents")
    
    try:
        # Import and initialize boundary agent
        from ...components.chunking.boundary_agent import BoundaryReviewAgent
        
        boundary_agent = BoundaryReviewAgent(
            context_window=boundary_context,
            model_name=model_name
        )
        
        # Stage 2: Boundary Review and Refinement
        if len(initial_chunks) <= 1:
            # No boundaries to review
            final_chunks = initial_chunks
            stage2_result = {
                "boundary_decisions": [],
                "total_boundaries": 0,
                "merge_decisions": 0,
                "keep_decisions": 0,
                "error_decisions": 0,
                "processing_time_seconds": 0.0,
                "avg_confidence": 0.0
            }
            logger.info("⚠️ Only one chunk - skipping boundary review")
        else:
            # Review boundaries and apply refinements with concurrent agents
            stage2_result = await boundary_agent.review_all_boundaries(
                initial_chunks, max_concurrent=concurrent_agents
            )
            final_chunks = _apply_boundary_decisions(initial_chunks, stage2_result["boundary_decisions"])
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Boundary refinement complete: {len(initial_chunks)} → {len(final_chunks)} chunks in {processing_time:.2f}s")
        
        # Return stage 2 results
        result = {
            "document_id": document_id,
            "source_file_path": stage1_result["source_file_path"],
            "initial_chunks": initial_chunks,
            "final_chunks": final_chunks,
            "initial_chunk_count": len(initial_chunks),
            "final_chunk_count": len(final_chunks),
            "stage2_metadata": stage2_result,
            "task_name": "boundary_refinement",
            "task_processing_time": round(processing_time, 3),
            "task_completed_at": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Boundary refinement task failed after {processing_time:.2f}s: {e}")
        raise


def _apply_boundary_decisions(chunks: List[str], decisions: List[Dict[str, Any]]) -> List[str]:
    """Apply boundary decisions to merge chunks where specified.
    
    Args:
        chunks: Original list of chunks
        decisions: List of boundary decisions
        
    Returns:
        List of chunks with merges applied
    """
    if not decisions:
        return chunks
    
    # Create merge map - which chunks to merge
    merge_map = {}
    for decision in decisions:
        if decision["decision"] == "MERGE":
            chunk_idx = decision["chunk_index"]
            merge_map[chunk_idx] = True
    
    refined_chunks = []
    i = 0
    
    while i < len(chunks):
        current_chunk = chunks[i]
        
        # Check if we should merge this chunk with the next one
        if i in merge_map and i + 1 < len(chunks):
            # Merge current chunk with next chunk
            merged_chunk = current_chunk + "\n\n" + chunks[i + 1]
            refined_chunks.append(merged_chunk)
            i += 2  # Skip the next chunk since we merged it
        else:
            # Keep current chunk as is
            refined_chunks.append(current_chunk)
            i += 1
    
    return refined_chunks