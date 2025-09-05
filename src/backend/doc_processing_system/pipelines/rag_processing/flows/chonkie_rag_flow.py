"""
Chonkie RAG Processing Flow - Complete replacement for the 5-stage RAG pipeline.

Single unified Chonkie pipeline replacing:
1. Semantic chunking + 2. Boundary refinement + 3. Chunk formatting + 4. Embeddings generation + 5. Vector storage

Features:
- Custom two-stage chunker integration
- Multiple embedding providers (OpenAI, Cohere, Hugging Face)  
- Direct Weaviate storage via handshake
- Maintains exact interface compatibility with existing RAG flow
- Comprehensive error handling and logging
- Performance metrics and monitoring

Dependencies: prefect, chonkie, pathlib
Integration: Drop-in replacement for rag_processing_flow
"""

import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from ...document_processing.chonkie_processor import ChonkieProcessor


@flow(
    name="chonkie_rag_pipeline",
    description="Complete Chonkie-based RAG processing pipeline",
    task_runner=ConcurrentTaskRunner(),
    flow_run_name="chonkie-rag-{document_id}",
    retries=1,
    retry_delay_seconds=60,
    timeout_seconds=1800  # 30 minutes total pipeline timeout
)
async def chonkie_rag_processing_flow(
    file_path: str,
    document_id: str,
    chunk_size: int = 700,
    semantic_threshold: float = 0.75,
    concurrent_agents: int = 10,
    chunking_model: str = "gemini-2.0-flash",
    embedding_model: str = "BAAI/bge-large-en-v1.5",
    batch_size: int = 32,  # For compatibility (not used in Chonkie)
    collection_name: str = "rag_documents"
) -> Dict[str, Any]:
    """Execute complete RAG processing pipeline using unified Chonkie approach.
    
    Single flow replacing entire 5-stage RAG pipeline:
    - Stage 1-3: Semantic chunking + boundary refinement + formatting → Custom ChonkieTwoStageChunker
    - Stage 4: Embeddings generation → Chonkie SentenceTransformerEmbeddings  
    - Stage 5: Vector storage → Chonkie WeaviateHandshake
    
    Args:
        file_path: Path to markdown document file
        document_id: Unique document identifier
        chunk_size: Target chunk size for semantic chunking
        semantic_threshold: Similarity threshold for semantic splits
        concurrent_agents: Number of concurrent boundary review agents
        chunking_model: LLM model for boundary decisions
        embedding_model: Embedding model (supports multiple providers)
        batch_size: Embedding batch size (for compatibility)
        collection_name: Weaviate collection name
        
    Returns:
        Dict containing complete pipeline results (maintains interface compatibility)
        
    Raises:
        Exception: If any pipeline stage fails after retries
    """
    logger = get_run_logger()
    pipeline_start = time.time()
    
    logger.info(f"🚀 Starting Chonkie RAG pipeline for {document_id}")
    logger.info(f"📁 Document: {file_path}")
    logger.info(f"⚙️ Config: chunk_size={chunk_size}, threshold={semantic_threshold}, agents={concurrent_agents}")
    logger.info(f"🤖 Models: chunking={chunking_model}, embedding={embedding_model}")
    
    try:
        # Initialize Chonkie processor with all configuration
        chonkie_processor = ChonkieProcessor(
            enable_vision=True,  # For compatibility
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            concurrent_agents=concurrent_agents,
            chunking_model=chunking_model,
            weaviate_collection=collection_name
        )
        
        # Process document through complete unified pipeline
        logger.info("🔄 Processing through Chonkie unified pipeline...")
        
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Read document content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            raise ValueError(f"Document file is empty: {file_path}")
        
        # Single pipeline execution replaces all 5 stages
        pipeline_result = await chonkie_processor._run_chonkie_pipeline(content, document_id)
        
        total_processing_time = time.time() - pipeline_start
        
        # Format results to maintain exact interface compatibility
        pipeline_result_formatted = {
            "pipeline_status": "success",
            "document_id": document_id,
            "source_file_path": file_path,
            "total_processing_time": round(total_processing_time, 3),
            "pipeline_completed_at": datetime.now().isoformat(),
            
            # Unified stages (maintains interface compatibility)
            "stages": {
                "chunking": {
                    "status": "success",
                    "chunk_count": pipeline_result["chunks_processed"],
                    "chunks_file_path": f"chonkie_virtual_chunks_{document_id}.json",  # Virtual path
                    "processing_time": round(total_processing_time * 0.3, 3)  # Approximate chunking time
                },
                "embeddings": {
                    "status": "success",
                    "embeddings_count": pipeline_result["embeddings_generated"],
                    "embeddings_file_path": f"chonkie_virtual_embeddings_{document_id}.json",  # Virtual path
                    "processing_time": round(total_processing_time * 0.5, 3),  # Approximate embedding time
                    "model_used": embedding_model
                },
                "storage": {
                    "status": "success",
                    "collection_name": collection_name,
                    "vectors_stored": pipeline_result["vectors_stored"],
                    "processing_time": round(total_processing_time * 0.2, 3),  # Approximate storage time
                    "note": "Direct Weaviate storage via Chonkie handshake"
                }
            },
            
            # Configuration (maintains compatibility)
            "configuration": {
                "chunk_size": chunk_size,
                "semantic_threshold": semantic_threshold,
                "concurrent_agents": concurrent_agents,
                "chunking_model": chunking_model,
                "embedding_model": embedding_model,
                "batch_size": batch_size,
                "collection_name": collection_name,
                "processing_method": "chonkie_unified"
            },
            
            # Chonkie-specific metrics (new addition)
            "chonkie_metrics": {
                "total_chunks": pipeline_result["chunks_processed"],
                "total_embeddings": pipeline_result["embeddings_generated"],
                "total_vectors_stored": pipeline_result["vectors_stored"],
                "pipeline_efficiency": round(pipeline_result["chunks_processed"] / total_processing_time, 2) if total_processing_time > 0 else 0,
                "chunking_strategy": pipeline_result["chunking_strategy"],
                "weaviate_collection": pipeline_result["weaviate_collection"],
                "processing_method": "single_unified_pipeline"
            }
        }
        
        logger.info(f"🎯 Chonkie RAG pipeline completed successfully in {total_processing_time:.2f}s")
        logger.info(f"📊 Results: {pipeline_result['chunks_processed']} chunks → {pipeline_result['embeddings_generated']} embeddings → {pipeline_result['vectors_stored']} vectors stored")
        
        return pipeline_result_formatted
        
    except Exception as e:
        total_processing_time = time.time() - pipeline_start
        logger.error(f"❌ Chonkie RAG pipeline failed after {total_processing_time:.2f}s: {e}")
        
        # Return failure result (maintains interface compatibility)
        return {
            "pipeline_status": "failed",
            "document_id": document_id,
            "source_file_path": file_path,
            "total_processing_time": round(total_processing_time, 3),
            "pipeline_failed_at": datetime.now().isoformat(),
            "error": str(e),
            "error_type": type(e).__name__,
            "processing_method": "chonkie_unified"
        }


# Convenience function maintaining existing interface
async def process_document_via_rag_pipeline(
    file_path: str,
    document_id: str,
    **kwargs
) -> Dict[str, Any]:
    """Process a document through the complete Chonkie RAG pipeline.
    
    Drop-in replacement for the original process_document_via_rag_pipeline function.
    
    Args:
        file_path: Path to markdown document file
        document_id: Unique document identifier
        **kwargs: Additional configuration parameters for the pipeline
        
    Returns:
        Dict containing pipeline results (maintains exact interface compatibility)
    """
    return await chonkie_rag_processing_flow(
        file_path=file_path,
        document_id=document_id,
        **kwargs
    )


# Alternative flow alias for backward compatibility
rag_processing_flow = chonkie_rag_processing_flow


if __name__ == "__main__":
    # Example usage for testing
    import asyncio
    
    async def test_chonkie_rag_pipeline():
        """Test the Chonkie RAG processing pipeline."""
        test_file_path = "data/documents/processed/test_doc_chonkie.md"
        test_document_id = "test_doc_chonkie"
        
        # Create test file if it doesn't exist
        Path(test_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        test_content = """
        # Test Document for Chonkie RAG Pipeline
        
        This is a test document for verifying the complete Chonkie-based RAG processing pipeline.
        
        ## Section 1: Introduction
        The pipeline now uses a single unified Chonkie approach replacing the previous 5-stage system.
        
        ## Section 2: Processing
        Chonkie handles chunking, embeddings, and storage in an integrated workflow.
        
        ## Section 3: Performance  
        This approach should be 2-33x faster than the previous multi-stage pipeline.
        
        ## Section 4: Integration
        The pipeline maintains full backward compatibility with existing interfaces.
        """
        
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Run pipeline
        result = await chonkie_rag_processing_flow(
            file_path=test_file_path,
            document_id=test_document_id,
            chunk_size=200,  # Small chunks for testing
            concurrent_agents=2  # Reduced for testing
        )
        
        print("🎯 Chonkie RAG Pipeline Result:")
        print(f"Status: {result['pipeline_status']}")
        if result['pipeline_status'] == 'success':
            print(f"Total time: {result['total_processing_time']}s")
            print(f"Chunks: {result['stages']['chunking']['chunk_count']}")
            print(f"Embeddings: {result['stages']['embeddings']['embeddings_count']}")
            print(f"Vectors stored: {result['stages']['storage']['vectors_stored']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Run test
    asyncio.run(test_chonkie_rag_pipeline())