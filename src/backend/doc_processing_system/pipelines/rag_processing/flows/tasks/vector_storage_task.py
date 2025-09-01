"""
Vector Storage Task - Stage 5 of RAG Processing Pipeline

Handles storage of embeddings in ChromaDB vector database.
Part of the modular RAG processing pipeline.
"""

import time
from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger
from .config import MAX_RETRIES, RETRY_DELAY, STORAGE_TIMEOUT
from .....core_deps.chromadb.chunk_ingestion_engine import get_chunk_ingestion_engine


@task(
    name="vector_storage",
    description="Store embeddings in ChromaDB vector database",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=STORAGE_TIMEOUT,
    tags=["storage", "chromadb", "vectors"]
)
async def store_vectors_task(
    embeddings_file_path: str,
    collection_name: str = "rag_documents"
) -> Dict[str, Any]:
    """Store embeddings in ChromaDB vector database.
    
    Args:
        embeddings_file_path: Path to embeddings JSON file with chromadb_ready format
        collection_name: ChromaDB collection name
        
    Returns:
        Dict containing storage results and ingestion stats
        
    Raises:
        Exception: If ChromaDB storage fails
    """
    logger = get_run_logger()
    start_time = time.time()
    
    logger.info(f"🔄 Starting vector storage task")
    logger.info(f"💾 Embeddings file: {embeddings_file_path}")
    logger.info(f"🗄️ Collection: {collection_name}")
    
    try:
        # Get chunk ingestion engine instance
        ingestion_engine = get_chunk_ingestion_engine()
        
        # Use chunk ingestion engine to store in ChromaDB
        success = ingestion_engine.ingest_from_chromadb_ready_file(
            embeddings_file_path=embeddings_file_path,
            collection_name=collection_name
        )
        
        processing_time = time.time() - start_time
        
        if success:
            # Get ingestion stats for confirmation
            stats = ingestion_engine.get_ingestion_stats(collection_name)
            
            result = {
                "storage_status": "success",
                "collection_name": collection_name,
                "embeddings_file_path": embeddings_file_path,
                "vectors_stored": True,
                "ingestion_stats": stats,
                "task_name": "vector_storage",
                "task_processing_time": round(processing_time, 3),
                "task_completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Vector storage completed successfully in {processing_time:.2f}s")
            if stats.get("document_count"):
                logger.info(f"📊 Total documents in collection: {stats['document_count']}")
        else:
            logger.error(f"❌ ChromaDB storage failed")
            result = {
                "storage_status": "failed",
                "collection_name": collection_name,
                "embeddings_file_path": embeddings_file_path,
                "vectors_stored": False,
                "error": "ChromaDB ingestion failed",
                "task_name": "vector_storage",
                "task_processing_time": round(processing_time, 3),
                "task_completed_at": datetime.now().isoformat()
            }
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Storage task failed after {processing_time:.2f}s: {e}")
        raise