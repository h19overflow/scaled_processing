"""
Weaviate storage task for document processing flow.
"""

import os
from typing import Dict, Any, List
from datetime import datetime

from prefect import task, get_run_logger
from chonkie import WeaviateHandshake
from chonkie.types import Chunk


@task(name="weaviate-storage", retries=2)
def weaviate_storage_task(
    embedded_chunks: List[Chunk],
    document_id: str,
    collection_name: str = "advanced_docs",
    weaviate_url: str = None,
    batch_size: int = 128,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Store embedded chunks in Weaviate using WeaviateHandshake.
    
    Args:
        embedded_chunks: List of Chunk objects with embeddings
        document_id: Document identifier
        collection_name: Weaviate collection name
        weaviate_url: Weaviate server URL
        batch_size: Batch size for storage operations
        user_id: User who uploaded the document
        
    Returns:
        Dict containing storage results
    """
    logger = get_run_logger()
    
    if not embedded_chunks:
        logger.error(f"❌ No embedded chunks provided for {document_id}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": "No embedded chunks to store"
        }
    
    logger.info(f"📤 Storing {len(embedded_chunks)} chunks in Weaviate for: {document_id}")
    
    try:
        # Initialize Weaviate handshake
        handshake = WeaviateHandshake(
            url=weaviate_url or os.getenv("WEAVIATE_URL", "http://localhost:8080"),
            collection_name=collection_name,
            batch_size=batch_size,
            embedding_model="model2vec"  # Match to an embedding pipeline
        )
        
        # Filter chunks that have embeddings
        valid_chunks = []
        for chunk in embedded_chunks:
            if "embedding" in chunk.metadata:
                # Add document-level metadata
                chunk.metadata.update({
                    "document_id": document_id,
                    "user_id": user_id,
                    "storage_timestamp": datetime.now().isoformat(),
                    "collection_name": collection_name
                })
                valid_chunks.append(chunk)
            else:
                logger.warning(f"Chunk {chunk.metadata.get('chunk_id', 'unknown')} has no embedding, skipping")
        
        if not valid_chunks:
            logger.error(f"❌ No valid embedded chunks found for {document_id}")
            return {
                "status": "error",
                "document_id": document_id,
                "error": "No valid embedded chunks to store"
            }
        
        # Write chunks to Weaviate
        storage_result = handshake.write(valid_chunks)
        
        logger.info(f"✅ Successfully stored {len(valid_chunks)} chunks in Weaviate for: {document_id}")
        logger.info(f"📊 Collection: {collection_name}, Batch size: {batch_size}")
        
        return {
            "status": "completed",
            "document_id": document_id,
            "collection_name": collection_name,
            "chunks_stored": len(valid_chunks),
            "chunks_skipped": len(embedded_chunks) - len(valid_chunks),
            "storage_result": storage_result,
            "weaviate_url": handshake.url if hasattr(handshake, 'url') else weaviate_url,
            "batch_size": batch_size,
            "message": f"Stored {len(valid_chunks)} chunks in collection '{collection_name}'"
        }
        
    except Exception as e:
        logger.error(f"❌ Weaviate storage failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Weaviate storage failed: {e}"
        }


@task(name="weaviate-query", retries=1)
def weaviate_query_task(
    query_text: str,
    collection_name: str = "advanced_docs",
    limit: int = 5,
    weaviate_url: str = None,
    weaviate_api_key: str = None,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Query Weaviate for similar chunks.
    
    Args:
        query_text: Text to search for
        collection_name: Weaviate collection name
        limit: Maximum number of results
        weaviate_url: Weaviate server URL
        weaviate_api_key: Weaviate API key
        user_id: User making the query
        
    Returns:
        Dict containing query results
    """
    logger = get_run_logger()
    logger.info(f"🔍 Querying Weaviate for: '{query_text[:50]}...'")
    
    try:
        # Initialize Weaviate handshake for querying
        handshake = WeaviateHandshake(
            url=weaviate_url or os.getenv("WEAVIATE_URL", "http://localhost:8080"),
            api_key=weaviate_api_key or os.getenv("WEAVIATE_API_KEY"),
            collection_name=collection_name,
            embedding_model="model2vec"
        )
        
        # Perform query (assuming handshake has a query method)
        # This is a placeholder - actual implementation depends on WeaviateHandshake API
        query_results = handshake.query(query_text, limit=limit)
        
        logger.info(f"✅ Found {len(query_results) if query_results else 0} results for query")
        
        return {
            "status": "completed",
            "query_text": query_text,
            "collection_name": collection_name,
            "results": query_results,
            "result_count": len(query_results) if query_results else 0,
            "user_id": user_id,
            "query_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Weaviate query failed: {e}")
        return {
            "status": "error",
            "query_text": query_text,
            "error": str(e),
            "message": f"Weaviate query failed: {e}"
        }