"""
ChonkieProcessor - Complete replacement for DoclingProcessor using unified Chonkie pipeline.
Integrates document processing + chunking + embeddings + Weaviate storage in a single pipeline.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from chonkie import SentenceTransformerEmbeddings, OpenAIEmbeddings, CohereEmbeddings
from chonkie import WeaviateHandshake
from chonkie import TextChef

from .two_stage_chunking.chonkie_two_stage_chunker import ChonkieTwoStageChunker
from ...data_models.document import ParsedDocument, DocumentMetadata, FileType


class ChonkieProcessor:
    """Complete replacement for DoclingProcessor using Chonkie pipeline."""
    
    def __init__(self, 
                 enable_vision: bool = True,
                 embedding_model: str = "BAAI/bge-large-en-v1.5",
                 chunk_size: int = 700,
                 semantic_threshold: float = 0.75,
                 concurrent_agents: int = 10,
                 chunking_model: str = "gemini-2.0-flash",
                 weaviate_collection: str = "rag_documents",
                 weaviate_url: str = None,
                 weaviate_api_key: str = None):
        """Initialize ChonkieProcessor with unified pipeline.
        
        Args:
            enable_vision: Enable vision processing (for compatibility)
            embedding_model: Embedding model (supports multiple providers)
            chunk_size: Target chunk size for chunking
            semantic_threshold: Similarity threshold for semantic splits
            concurrent_agents: Number of concurrent boundary agents
            chunking_model: LLM model for boundary decisions
            weaviate_collection: Weaviate collection name
            weaviate_url: Weaviate server URL
            weaviate_api_key: Weaviate API key
        """
        self.enable_vision = enable_vision
        self.embedding_model = embedding_model
        self.weaviate_collection = weaviate_collection
        
        # Initialize output manager for compatibility (lazy loaded)
        self.output_manager = None
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Configure embeddings based on model type
        self.embeddings = self._initialize_embeddings(embedding_model)
        
        # Initialize our custom two-stage chunker
        self.chunker = ChonkieTwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=200,  # Fixed boundary context
            concurrent_agents=concurrent_agents,
            model_name=chunking_model
        )
        
        # Configure Weaviate handshake for direct storage
        self.weaviate_handshake = WeaviateHandshake(
            embedding_model=self.embeddings,  # Changed from 'embeddings' to 'embedding_model'
            collection_name=weaviate_collection,
            url=weaviate_url or os.getenv("WEAVIATE_URL", "http://localhost:8080"),
            api_key=weaviate_api_key or os.getenv("WEAVIATE_API_KEY")
        )
        
        # Initialize complete Chonkie TextChef (pipeline orchestrator)
        self.chef = TextChef()
        
        self.logger.info("ChonkieProcessor initialized - complete DoclingProcessor replacement")
        self.logger.info(f"Configuration: embedding_model={embedding_model}, collection={weaviate_collection}")


    def get_output_manager(self):
        return self.output_manager
    
    async def process_and_refine_chunks(self, text: str, document_id: str) -> Dict[str, Any]:
        """Process document text with chunking and refinement.
        
        Args:
            text: Document text to process
            document_id: Document identifier
            
        Returns:
            Dict containing refined chunks and metadata
        """
        try:
            # Use our chunker which already includes OverlapRefinery
            refined_chunks = await self.chunker.chunk_async(text, document_id)
            
            self.logger.info(f"Processed {len(refined_chunks)} refined chunks for document: {document_id}")
            
            return {
                "status": "completed",
                "document_id": document_id,
                "refined_chunks": refined_chunks,
                "chunk_count": len(refined_chunks),
                "total_tokens": sum(chunk.token_count for chunk in refined_chunks)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing chunks for {document_id}: {e}")
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e)
            }

   
