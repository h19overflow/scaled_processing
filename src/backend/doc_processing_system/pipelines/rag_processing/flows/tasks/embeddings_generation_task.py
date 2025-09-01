"""
Embeddings Generation Task - Stage 4 of RAG Processing Pipeline

Handles generation of vector embeddings from processed text chunks.
Part of the modular RAG processing pipeline.
"""

import time
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger
from .config import MAX_RETRIES, RETRY_DELAY, EMBEDDING_TIMEOUT


@task(
    name="embeddings_generation", 
    description="Generate embeddings from chunk files",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=EMBEDDING_TIMEOUT,
    tags=["embeddings", "vectors", "chromadb"]
)
def generate_embeddings_task(
    chunks_file_path: str,
    model_name: str = "BAAI/bge-large-en-v1.5",
    batch_size: int = 32
) -> Dict[str, Any]:
    """Generate embeddings from processed chunks.
    
    Args:
        chunks_file_path: Path to chunks JSON file from chunking task
        model_name: Sentence transformer model for embeddings
        batch_size: Number of chunks to process in each batch
        
    Returns:
        Dict containing embeddings results and ValidatedEmbedding models
        
    Raises:
        FileNotFoundError: If chunks file doesn't exist
        RuntimeError: If embedding model fails to load
    """
    logger = get_run_logger()
    start_time = time.time()
    
    logger.info(f"🔄 Starting embeddings generation task")
    logger.info(f"📄 Chunks file: {chunks_file_path}")
    logger.info(f"🤖 Model: {model_name}")
    
    try:
        # Initialize embeddings generator (import locally to avoid DLL issues)
        from ...components.embeddings_generator import EmbeddingsGenerator
        
        embedder = EmbeddingsGenerator(
            model_name=model_name,
            batch_size=batch_size
        )
        
        # Process chunks file
        result = embedder.process_chunks_file(chunks_file_path)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Embeddings complete: {result['embeddings_count']} vectors in {processing_time:.2f}s")
        logger.info(f"💾 Embeddings saved to: {result['embeddings_file_path']}")
        
        # Add task metadata
        result.update({
            "task_name": "embeddings_generation",
            "task_processing_time": round(processing_time, 3),
            "task_completed_at": datetime.now().isoformat()
        })
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Embeddings task failed after {processing_time:.2f}s: {e}")
        raise