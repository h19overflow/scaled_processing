"""
Semantic Chunking Task - Stage 1 of RAG Processing Pipeline

Handles semantic chunking of documents using similarity-based text splitting.
Part of the modular RAG processing pipeline.
"""

import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger
from .config import MAX_RETRIES, RETRY_DELAY, CHUNKING_TIMEOUT


@task(
    name="semantic_chunking",
    description="Process document through semantic chunking (Stage 1)",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=CHUNKING_TIMEOUT // 2,  # Half timeout for Stage 1
    tags=["chunking", "stage1", "semantic"]
)
def semantic_chunking_task(
    file_path: str, 
    document_id: str,
    chunk_size: int = 700,
    semantic_threshold: float = 0.75
) -> Dict[str, Any]:
    """Execute semantic chunking on document file (Stage 1).
    
    Args:
        file_path: Path to markdown document file
        document_id: Unique document identifier
        chunk_size: Target chunk size for semantic chunking
        semantic_threshold: Similarity threshold for semantic splits
        
    Returns:
        Dict containing initial chunks and metadata
        
    Raises:
        FileNotFoundError: If document file doesn't exist
        ValueError: If chunking fails
    """
    logger = get_run_logger()
    start_time = time.time()
    
    logger.info(f"🔄 Starting semantic chunking task (Stage 1) for {document_id}")
    logger.info(f"📁 File path: {file_path}")
    
    try:
        # Read document content
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text.strip():
            raise ValueError(f"Document file is empty: {file_path}")
        
        logger.info(f"📖 Document loaded: {len(text)} characters")
        
        # Import and initialize semantic chunker
        from ...components.chunking.semantic_chunker import SemanticChunker
        
        semantic_chunker = SemanticChunker(
            chunk_size=chunk_size,
            threshold=semantic_threshold
        )
        
        # Perform semantic chunking
        stage1_result = semantic_chunker.chunk_text(text, document_id)
        initial_chunks = stage1_result["chunks"]
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Semantic chunking complete: {len(initial_chunks)} chunks in {processing_time:.2f}s")
        
        # Return stage 1 results
        result = {
            "document_id": document_id,
            "source_file_path": file_path,
            "original_text": text,
            "initial_chunks": initial_chunks,
            "chunk_count": len(initial_chunks),
            "stage1_metadata": stage1_result,
            "task_name": "semantic_chunking",
            "task_processing_time": round(processing_time, 3),
            "task_completed_at": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Semantic chunking task failed after {processing_time:.2f}s: {e}")
        raise