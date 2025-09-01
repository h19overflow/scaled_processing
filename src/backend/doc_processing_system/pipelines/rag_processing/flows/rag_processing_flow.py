"""
RAG Processing Prefect Flow - Complete pipeline orchestration

Orchestrates the full RAG processing pipeline from document files to ChromaDB storage:
1. Two-Stage Chunking: Semantic chunking + boundary refinement
2. Embeddings Generation: Vector creation with ValidatedEmbedding models
3. Vector Storage: ChromaDB ingestion (future implementation)

Features:
- Retry logic for transient failures
- Timeout protection for long-running tasks
- Comprehensive error handling and logging
- Kafka event publishing for pipeline monitoring
- Data model validation throughout pipeline

Dependencies: prefect, asyncio, pathlib
Integration: Consumes Kafka messages for document processing requests
"""

import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

# Import modular task components
from .tasks import (
    semantic_chunking_task,
    boundary_refinement_task,
    chunk_formatting_task,
    generate_embeddings_task,
    store_vectors_task
)


@flow(
    name="rag_processing_pipeline",
    description="Complete RAG processing pipeline from document to vectors",
    task_runner=ConcurrentTaskRunner(),
    flow_run_name="rag-{document_id}",
    retries=1,
    retry_delay_seconds=60,
    timeout_seconds=1800  # 30 minutes total pipeline timeout
)
async def rag_processing_flow(
    file_path: str,
    document_id: str,
    chunk_size: int = 700,
    semantic_threshold: float = 0.75,
    concurrent_agents: int = 10,
    chunking_model: str = "gemini-2.0-flash",
    embedding_model: str = "BAAI/bge-large-en-v1.5",
    batch_size: int = 32,
    collection_name: str = "rag_documents"
) -> Dict[str, Any]:
    """Execute complete RAG processing pipeline.
    
    Args:
        file_path: Path to markdown document file
        document_id: Unique document identifier
        chunk_size: Target chunk size for semantic chunking
        semantic_threshold: Similarity threshold for semantic splits
        concurrent_agents: Number of concurrent boundary review agents
        chunking_model: LLM model for boundary decisions
        embedding_model: Sentence transformer model for embeddings
        batch_size: Embedding batch size
        collection_name: ChromaDB collection name
        
    Returns:
        Dict containing complete pipeline results
        
    Raises:
        Exception: If any pipeline stage fails after retries
    """
    logger = get_run_logger()
    pipeline_start = time.time()
    
    logger.info(f"🚀 Starting RAG processing pipeline for {document_id}")
    logger.info(f"📁 Document: {file_path}")
    logger.info(f"⚙️ Config: chunk_size={chunk_size}, threshold={semantic_threshold}, agents={concurrent_agents}")
    logger.info(f"🤖 Models: chunking={chunking_model}, embedding={embedding_model}")
    
    try:
        # Stage 1: Semantic Chunking
        logger.info("📝 Stage 1: Semantic Chunking")
        stage1_result = await semantic_chunking_task(
            file_path=file_path,
            document_id=document_id,
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold
        )
        
        # Stage 2: Boundary Refinement
        logger.info("🔍 Stage 2: Boundary Refinement")
        stage2_result = await boundary_refinement_task(
            stage1_result=stage1_result,
            concurrent_agents=concurrent_agents,
            model_name=chunking_model,
            boundary_context=200
        )
        
        # Stage 3: Chunk Formatting
        logger.info("📄 Stage 3: Chunk Formatting")
        chunking_result = await chunk_formatting_task(
            stage2_result=stage2_result
        )
        
        # Stage 4: Embeddings Generation
        logger.info("🔢 Stage 4: Embeddings Generation")
        embeddings_result = await generate_embeddings_task(
            chunks_file_path=chunking_result["chunks_file_path"],
            model_name=embedding_model,
            batch_size=batch_size
        )
        
        # Stage 5: Vector Storage (placeholder)
        logger.info("🗄️ Stage 5: Vector Storage")
        storage_result = await store_vectors_task(
            embeddings_file_path=embeddings_result["embeddings_file_path"],
            collection_name=collection_name
        )
        
        # Pipeline completion
        total_processing_time = time.time() - pipeline_start
        
        # Compile pipeline results
        pipeline_result = {
            "pipeline_status": "success",
            "document_id": document_id,
            "source_file_path": file_path,
            "total_processing_time": round(total_processing_time, 3),
            "pipeline_completed_at": datetime.now().isoformat(),
            "stages": {
                "chunking": {
                    "status": "success",
                    "chunk_count": chunking_result["chunk_count"],
                    "chunks_file_path": chunking_result["chunks_file_path"],
                    "processing_time": chunking_result["task_processing_time"]
                },
                "embeddings": {
                    "status": "success", 
                    "embeddings_count": embeddings_result["embeddings_count"],
                    "embeddings_file_path": embeddings_result["embeddings_file_path"],
                    "processing_time": embeddings_result["task_processing_time"],
                    "model_used": embeddings_result["model_used"]
                },
                "storage": {
                    "status": "placeholder",
                    "collection_name": storage_result["collection_name"],
                    "processing_time": storage_result["task_processing_time"],
                    "note": storage_result["note"]
                }
            },
            "configuration": {
                "chunk_size": chunk_size,
                "semantic_threshold": semantic_threshold,
                "concurrent_agents": concurrent_agents,
                "chunking_model": chunking_model,
                "embedding_model": embedding_model,
                "batch_size": batch_size,
                "collection_name": collection_name
            }
        }
        
        logger.info(f"🎯 RAG pipeline completed successfully in {total_processing_time:.2f}s")
        logger.info(f"📊 Results: {chunking_result['chunk_count']} chunks → {embeddings_result['embeddings_count']} vectors")
        
        return pipeline_result
        
    except Exception as e:
        total_processing_time = time.time() - pipeline_start
        logger.error(f"❌ RAG pipeline failed after {total_processing_time:.2f}s: {e}")
        
        # Return failure result
        return {
            "pipeline_status": "failed",
            "document_id": document_id,
            "source_file_path": file_path,
            "total_processing_time": round(total_processing_time, 3),
            "pipeline_failed_at": datetime.now().isoformat(),
            "error": str(e),
            "error_type": type(e).__name__
        }


# Convenience function for external integration
async def process_document_via_rag_pipeline(
    file_path: str,
    document_id: str,
    **kwargs
) -> Dict[str, Any]:
    """Process a document through the complete RAG pipeline.
    
    Args:
        file_path: Path to markdown document file
        document_id: Unique document identifier
        **kwargs: Additional configuration parameters for the pipeline
        
    Returns:
        Dict containing pipeline results
    """
    return await rag_processing_flow(
        file_path=file_path,
        document_id=document_id,
        **kwargs
    )


if __name__ == "__main__":
    # Example usage for testing
    import asyncio
    
    async def test_rag_pipeline():
        """Test the RAG processing pipeline."""
        test_file_path = "data/documents/processed/test_doc_001.md"
        test_document_id = "test_doc_001"
        
        # Create test file if it doesn't exist
        Path(test_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        test_content = """
        # Test Document for RAG Pipeline
        
        This is a test document for verifying the complete RAG processing pipeline.
        
        ## Section 1: Introduction
        The pipeline consists of three main stages: chunking, embeddings, and storage.
        
        ## Section 2: Processing
        Each stage is implemented as a Prefect task with retry and timeout logic.
        
        ## Section 3: Integration
        The pipeline outputs data models compatible with ChromaDB for vector search.
        """
        
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Run pipeline
        result = await rag_processing_flow(
            file_path=test_file_path,
            document_id=test_document_id,
            chunk_size=200,  # Small chunks for testing
            concurrent_agents=2  # Reduced for testing
        )
        
        print("🎯 Pipeline Result:")
        print(f"Status: {result['pipeline_status']}")
        if result['pipeline_status'] == 'success':
            print(f"Total time: {result['total_processing_time']}s")
            print(f"Chunks: {result['stages']['chunking']['chunk_count']}")
            print(f"Embeddings: {result['stages']['embeddings']['embeddings_count']}")
    
    # Run test
    asyncio.run(test_rag_pipeline())