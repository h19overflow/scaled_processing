"""
Chunk Formatting Task - Stage 3 of RAG Processing Pipeline

Handles formatting of refined chunks into TextChunk models and file storage.
Part of the modular RAG processing pipeline.
"""

import time
import hashlib
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger
from .config import MAX_RETRIES, RETRY_DELAY


@task(
    name="chunk_formatting",
    description="Format final chunks into TextChunk models and save to file",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=60,  # Quick formatting task
    tags=["chunking", "formatting", "textchunk", "models"]
)
async def chunk_formatting_task(
    stage2_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Format refined chunks into TextChunk models and save to file.
    
    Args:
        stage2_result: Results from boundary refinement task
        
    Returns:
        Dict containing formatted TextChunk models and file path
        
    Raises:
        ValueError: If formatting fails
    """
    logger = get_run_logger()
    start_time = time.time()
    
    document_id = stage2_result["document_id"]
    final_chunks = stage2_result["final_chunks"]
    
    logger.info(f"🔄 Starting chunk formatting task for {document_id}")
    logger.info(f"📄 Formatting {len(final_chunks)} chunks into TextChunk models")
    
    try:
        # Create TextChunk models
        text_chunks = []
        chunks_directory = Path("data/rag/chunks")
        chunks_directory.mkdir(parents=True, exist_ok=True)
        
        for i, chunk_content in enumerate(final_chunks):
            # Generate deterministic chunk ID
            id_string = f"{document_id}_{i}"
            chunk_id = hashlib.md5(id_string.encode()).hexdigest()[:16]
            
            # Create TextChunk dictionary matching the model
            text_chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "content": chunk_content,
                "page_number": 0,  # Placeholder until page mapping is implemented
                "chunk_index": i,
                "metadata": {
                    "chunk_length": len(chunk_content),
                    "word_count": len(chunk_content.split()),
                    "created_at": datetime.now().isoformat(),
                    "chunking_strategy": "two_stage_semantic"
                }
            }
            
            text_chunks.append(text_chunk)
        
        # Save TextChunk models to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chunks_{document_id}_{timestamp}.json"
        chunks_path = chunks_directory / filename
        
        chunks_data = {
            "document_id": document_id,
            "timestamp": datetime.now().isoformat(),
            "chunk_count": len(text_chunks),
            "chunks": text_chunks,  # List of TextChunk dictionaries
            "statistics": {
                "total_characters": sum(chunk["metadata"]["chunk_length"] for chunk in text_chunks),
                "total_words": sum(chunk["metadata"]["word_count"] for chunk in text_chunks),
                "avg_chunk_length": round(sum(chunk["metadata"]["chunk_length"] for chunk in text_chunks) / len(text_chunks), 1) if text_chunks else 0,
                "min_chunk_length": min(chunk["metadata"]["chunk_length"] for chunk in text_chunks) if text_chunks else 0,
                "max_chunk_length": max(chunk["metadata"]["chunk_length"] for chunk in text_chunks) if text_chunks else 0
            }
        }
        
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Chunk formatting complete: {len(text_chunks)} TextChunk models saved in {processing_time:.2f}s")
        logger.info(f"📄 Chunks saved to: {chunks_path}")
        
        # Return formatting results
        result = {
            "document_id": document_id,
            "chunk_count": len(text_chunks),
            "chunks_file_path": str(chunks_path),
            "text_chunks": text_chunks,
            "task_name": "chunk_formatting",
            "task_processing_time": round(processing_time, 3),
            "task_completed_at": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Chunk formatting task failed after {processing_time:.2f}s: {e}")
        raise