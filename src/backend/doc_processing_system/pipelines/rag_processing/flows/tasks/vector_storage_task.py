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
    
    logger.info("✨" + "="*80 + "✨")
    logger.info(f"🚀 VECTOR STORAGE TASK STARTED")
    logger.info("✨" + "="*80 + "✨")
    logger.info(f"💾 Embeddings file: {embeddings_file_path}")
    logger.info(f"🗄️ Target collection: {collection_name}")
    logger.info(f"🕰️ Start time: {datetime.now().isoformat()}")
    
    try:
        # Verify file exists before processing
        import os
        if not os.path.exists(embeddings_file_path):
            raise FileNotFoundError(f"Embeddings file not found: {embeddings_file_path}")
        
        file_size = os.path.getsize(embeddings_file_path)
        logger.info(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # Get chunk ingestion engine instance
        logger.info("🔧 Initializing chunk ingestion engine...")
        ingestion_engine = get_chunk_ingestion_engine()
        
        if not ingestion_engine:
            raise Exception("Failed to get chunk ingestion engine instance")
        
        logger.info("✅ Chunk ingestion engine ready")
        
        # Use chunk ingestion engine to store in ChromaDB
        logger.info("🚀 Starting ChromaDB ingestion process...")
        success = ingestion_engine.ingest_from_chromadb_ready_file(
            embeddings_file_path=embeddings_file_path,
            collection_name=collection_name
        )
        
        processing_time = time.time() - start_time
        
        if success:
            logger.info("✅ ChromaDB ingestion completed successfully!")
            
            # Get ingestion stats for confirmation
            logger.info("📊 Retrieving ingestion statistics...")
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
            
            logger.info("✨" + "="*80 + "✨")
            logger.info(f"✅ VECTOR STORAGE TASK COMPLETED SUCCESSFULLY")
            logger.info(f"⏱️ Processing time: {processing_time:.2f}s")
            if stats.get("document_count"):
                logger.info(f"📊 Total documents in collection: {stats['document_count']}")
            logger.info(f"💾 File processed: {embeddings_file_path}")
            logger.info("✨" + "="*80 + "✨")
        else:
            logger.error("❌" + "="*80 + "❌")
            logger.error(f"❌ CHROMADB STORAGE FAILED")
            logger.error("❌" + "="*80 + "❌")
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
        logger.error("❌" + "="*80 + "❌")
        logger.error(f"❌ VECTOR STORAGE TASK FAILED")
        logger.error("❌" + "="*80 + "❌")
        logger.error(f"⏱️ Processing time: {processing_time:.2f}s")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        logger.error(f"🔍 Error message: {e}")
        logger.error(f"💾 File: {embeddings_file_path}")
        logger.error(f"🗄️ Collection: {collection_name}")
        
        import traceback
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        
        logger.error("❌" + "="*80 + "❌")
        raise