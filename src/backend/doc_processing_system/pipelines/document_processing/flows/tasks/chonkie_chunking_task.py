"""
Chonkie two-stage chunking task for document processing flow.
"""

from typing import Dict, Any, List
from pathlib import Path

from prefect import task, get_run_logger
from chonkie.types import Chunk

from ...two_stage_chunking.chonkie_two_stage_chunker import ChonkieTwoStageChunker


@task(name="chonkie-chunking", retries=2)
def chonkie_chunking_task(
    text_content: str,
    document_id: str,
    page_count: int,
    raw_file_path: str,
    chunk_size: int = 700,
    semantic_threshold: float = 0.75,
    boundary_context: int = 200,
    concurrent_agents: int = 10,
    model_name: str = "gemini-2.0-flash",
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
) -> Dict[str, Any]:
    """
    Process document text using ChonkieTwoStageChunker with embeddings.
    
    Args:
        text_content: Extracted text content from document
        document_id: Document identifier
        page_count: Number of pages in document
        raw_file_path: Original file path
        chunk_size: Target chunk size for semantic chunking
        semantic_threshold: Similarity threshold for semantic splits
        boundary_context: Context window for boundary analysis
        concurrent_agents: Number of concurrent boundary review agents
        model_name: LLM model for boundary decisions
        embedding_model: Hugging Face model for embeddings
        
    Returns:
        Dict containing chunked data with embeddings
    """
    logger = get_run_logger()
    
    if not text_content or not text_content.strip():
        logger.error(f"❌ No text content provided for {document_id}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": "No text content to chunk",
            "embedded_chunks": []
        }
    
    logger.info(f"🔄 Starting two-stage chunking for: {document_id}")
    logger.info(f"📄 Pages: {page_count}, Text length: {len(text_content)} chars")
    
    try:
        # Initialize ChonkieTwoStageChunker
        chunker = ChonkieTwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            concurrent_agents=concurrent_agents,
            model_name=model_name,
            embedding_model=embedding_model
        )
        
        # Process document with embeddings
        embedded_chunks = chunker.chunk_with_embeddings(
            text=text_content,
            document_id=document_id
        )
        
        # Add document-level metadata to each chunk
        embedded_chunks = _prepare_chunks(
            embedded_chunks=embedded_chunks,
            document_id=document_id,
            page_count=page_count,
            raw_file_path=raw_file_path,
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            model_name=model_name,
            embedding_model=embedding_model
        )
        
        logger.info(f"✅ Successfully chunked {document_id} into {len(embedded_chunks)} chunks with embeddings")
        
        return {
            "status": "completed",
            "document_id": document_id,
            "embedded_chunks": embedded_chunks,
            "chunk_count": len(embedded_chunks),
            "page_count": page_count,
            "raw_file_path": raw_file_path,
            "chunking_params": {
                "chunk_size": chunk_size,
                "semantic_threshold": semantic_threshold,
                "boundary_context": boundary_context,
                "concurrent_agents": concurrent_agents,
                "model_name": model_name,
                "embedding_model": embedding_model
            },
            "message": f"Created {len(embedded_chunks)} chunks with embeddings for {document_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Chonkie chunking failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "embedded_chunks": [],
            "message": f"Chonkie chunking failed: {e}"
        }


@task(name="chonkie-chunking-sync", retries=2)
def chonkie_chunking_sync_task(
    text_content: str,
    document_id: str,
    page_count: int,
    raw_file_path: str,
    chunk_size: int = 700,
    semantic_threshold: float = 0.75,
    boundary_context: int = 200,
    concurrent_agents: int = 10,
    model_name: str = "gemini-2.0-flash",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> Dict[str, Any]:
    """
    Synchronous version of chonkie chunking task for compatibility.
    
    Args:
        text_content: Extracted text content from document
        document_id: Document identifier
        page_count: Number of pages in document
        raw_file_path: Original file path
        chunk_size: Target chunk size for semantic chunking
        semantic_threshold: Similarity threshold for semantic splits
        boundary_context: Context window for boundary analysis
        concurrent_agents: Number of concurrent boundary review agents
        model_name: LLM model for boundary decisions
        embedding_model: Hugging Face model for embeddings
        
    Returns:
        Dict containing chunked data with embeddings
    """
    logger = get_run_logger()
    
    if not text_content or not text_content.strip():
        logger.error(f"❌ No text content provided for {document_id}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": "No text content to chunk",
            "embedded_chunks": []
        }
    
    logger.info(f"🔄 Starting sync two-stage chunking for: {document_id}")
    logger.info(f"📄 Pages: {page_count}, Text length: {len(text_content)} chars")
    
    try:
        # Initialize ChonkieTwoStageChunker
        chunker = ChonkieTwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            concurrent_agents=concurrent_agents,
            model_name=model_name,
            embedding_model=embedding_model
        )
        
        # Process document with embeddings (sync version)
        embedded_chunks = chunker.chunk(text_content)
        
        # Generate embeddings
        embedded_chunks = chunker.generate_embeddings(embedded_chunks)
        
        # Add document-level metadata to each chunk
        embedded_chunks = _prepare_chunks(
            embedded_chunks=embedded_chunks,
            document_id=document_id,
            page_count=page_count,
            raw_file_path=raw_file_path,
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            model_name=model_name,
            embedding_model=embedding_model
        )
        
        logger.info(f"✅ Successfully chunked {document_id} into {len(embedded_chunks)} chunks with embeddings")
        
        return {
            "status": "completed",
            "document_id": document_id,
            "embedded_chunks": embedded_chunks,
            "chunk_count": len(embedded_chunks),
            "page_count": page_count,
            "raw_file_path": raw_file_path,
            "chunking_params": {
                "chunk_size": chunk_size,
                "semantic_threshold": semantic_threshold,
                "boundary_context": boundary_context,
                "concurrent_agents": concurrent_agents,
                "model_name": model_name,
                "embedding_model": embedding_model
            },
            "message": f"Created {len(embedded_chunks)} chunks with embeddings for {document_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Sync Chonkie chunking failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "embedded_chunks": [],
            "message": f"Sync Chonkie chunking failed: {e}"
        }
    
    
def _prepare_chunks(embedded_chunks: List[Chunk],
                   document_id: str,
                   page_count: int,
                   raw_file_path: str,
                   chunk_size: int = 700,
                   semantic_threshold: float = 0.75,
                   boundary_context: int = 200,
                   model_name: str = "gemini-2.0-flash",
                   embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[Chunk]:
    """Add document-level metadata to each chunk."""
    for chunk in embedded_chunks:
        chunk.metadata.update({
            "document_id": document_id,
            "page_count": page_count,
            "raw_file_path": raw_file_path,
            "file_name": Path(raw_file_path).name,
            "chunking_strategy": "chonkie_two_stage_semantic_boundary",
            "chunk_size": chunk_size,
            "semantic_threshold": semantic_threshold,
            "boundary_context": boundary_context,
            "model_name": model_name,
            "embedding_model": embedding_model
        })
    return embedded_chunks
        
        