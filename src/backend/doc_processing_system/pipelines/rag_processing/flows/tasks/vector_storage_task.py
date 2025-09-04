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
from .....core_deps.weaviate.weaviate_ingestion_engine import WeaviateIngestionEngine


@task(
    name="vector_storage",
    description="Store embeddings in Weaviate vector database",
    retries=MAX_RETRIES,
    retry_delay_seconds=RETRY_DELAY,
    timeout_seconds=STORAGE_TIMEOUT,
    tags=["storage", "weaviate", "vectors"]
)
async def store_vectors_task(
    embeddings_file_path: str,
    collection_name: str = "rag_documents"
) -> Dict[str, Any]:
    """Store embeddings in Weaviate vector database.
    
    Args:
        embeddings_file_path: Path to embeddings JSON file 
        collection_name: Weaviate collection name
        
    Returns:
        Dict containing storage results and ingestion stats
        
    Raises:
        Exception: If Weaviate storage fails
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
        # Verify file exists, if not try to find the latest embeddings file for the document
        import os
        from pathlib import Path
        
        if not os.path.exists(embeddings_file_path):
            logger.warning(f"⚠️ Exact embeddings file not found: {embeddings_file_path}")
            
            # Extract document ID from the file path to find latest file
            file_path_obj = Path(embeddings_file_path)
            filename_parts = file_path_obj.stem.split('_')
            
            if len(filename_parts) >= 2:  # Format: embeddings_FILENAME.json
                # Try to extract document ID from filename
                if filename_parts[0] == "embeddings":
                    # For new format: embeddings_filename.json (where filename is original file stem)
                    document_id_part = "_".join(filename_parts[1:])  # Everything after "embeddings_"
                    
                    # Search for exact embeddings file matching this document
                    embeddings_dir = file_path_obj.parent
                    pattern = f"embeddings_{document_id_part}.json"
                    
                    logger.info(f"🔍 Searching for exact file: {pattern} in {embeddings_dir}")
                    exact_file = embeddings_dir / pattern
                    
                    if exact_file.exists():
                        embeddings_file_path = str(exact_file)
                        logger.info(f"✅ Found exact embeddings file: {embeddings_file_path}")
                    else:
                        # Fallback: search for any file with similar document ID pattern
                        fallback_pattern = f"embeddings_{document_id_part}*.json"
                        matching_files = list(embeddings_dir.glob(fallback_pattern))
                        
                        if matching_files:
                            latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
                            embeddings_file_path = str(latest_file)
                            logger.info(f"✅ Found fallback embeddings file: {embeddings_file_path}")
                        else:
                            raise FileNotFoundError(f"No embeddings files found for document pattern: {fallback_pattern}")
                else:
                    raise FileNotFoundError(f"Embeddings file not found and unable to parse document ID from: {embeddings_file_path}")
            else:
                raise FileNotFoundError(f"Embeddings file not found and filename format unrecognized: {embeddings_file_path}")
        
        file_size = os.path.getsize(embeddings_file_path)
        logger.info(f"📊 Using embeddings file: {embeddings_file_path}")
        logger.info(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # Initialize Weaviate ingestion engine directly (no isolation needed!)
        logger.info("🚀 Initializing Weaviate ingestion engine...")
        weaviate_engine = WeaviateIngestionEngine()
        
        logger.info("✅ Weaviate ingestion engine ready")
        logger.info("🔧 Direct ingestion - no process isolation needed with Weaviate!")
        
        # Use Weaviate engine to store embeddings directly
        logger.info("🚀 Starting Weaviate ingestion process...")
        success = weaviate_engine.ingest_from_embeddings_file(
            embeddings_file_path=embeddings_file_path,
            collection_name=collection_name
        )
        
        if not success:
            logger.error(f"❌ Weaviate ingestion failed")
        else:
            logger.info(f"✅ Weaviate ingestion completed successfully")
        
        processing_time = time.time() - start_time
        
        if success:
            logger.info("✅ Weaviate ingestion completed successfully!")
            
            # Get ingestion stats from Weaviate engine
            logger.info("📊 Getting ingestion statistics...")
            stats = weaviate_engine.get_ingestion_stats(collection_name)
            
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
            logger.error(f"❌ WEAVIATE STORAGE FAILED")
            logger.error("❌" + "="*80 + "❌")
            result = {
                "storage_status": "failed",
                "collection_name": collection_name,
                "embeddings_file_path": embeddings_file_path,
                "vectors_stored": False,
                "error": "Weaviate ingestion failed",
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
    

if __name__ == "__main__":
    import asyncio
    # For direct testing
    test_file = "path/to/embeddings_testdoc.json"
    asyncio.run(store_vectors_task(test_file, collection_name="test_collection"))