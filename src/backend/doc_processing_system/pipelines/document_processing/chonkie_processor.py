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
from .utils.document_output_manager import DocumentOutputManager


class ChonkieProcessor:
    """Complete replacement for DoclingProcessor using Chonkie pipeline."""
    
    def __init__(self, 
                 enable_vision: bool = True,
                 embedding_model: str = "BAAI/bge-small-en-v1.5",
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
        
        # Initialize output manager for compatibility
        self.output_manager = DocumentOutputManager()
        
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
    
    def _setup_logging(self):
        """Setup logging configuration for ChonkieProcessor.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Create logger with class-specific name
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Set logging level (can be made configurable via env var)
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Avoid adding multiple handlers if logger already exists
        if not logger.handlers:
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logger.level)
            
            # Create detailed formatter for ChonkieProcessor operations
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - [ChonkieProcessor] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            
            # Add handler to logger
            logger.addHandler(console_handler)
            
            # Optional: Add file handler if LOG_FILE env var is set
            log_file = os.getenv("LOG_FILE")
            if log_file:
                try:
                    # Ensure log directory exists
                    log_path = Path(log_file)
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create file handler
                    file_handler = logging.FileHandler(log_file)
                    file_handler.setLevel(logger.level)
                    file_handler.setFormatter(formatter)
                    logger.addHandler(file_handler)
                    
                    logger.info(f"File logging enabled: {log_file}")
                except Exception as e:
                    logger.warning(f"Failed to setup file logging: {e}")
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
        
        return logger

    def get_output_manager(self):
        """Lazy load DocumentOutputManager for compatibility."""
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
    def _initialize_embeddings(self, embedding_model: str):
        """Initialize embeddings based on model type and provider.
        
        Args:
            embedding_model: Embedding model name/path
            
        Returns:
            Embedding instance compatible with Chonkie
        """
        try:
            self.logger.info(f"Initializing embeddings with model: {embedding_model}")
            
            # Detect embedding provider based on model name
            if "openai" in embedding_model.lower() or embedding_model.startswith("text-embedding"):
                # OpenAI embeddings
                self.logger.info("Using OpenAI embeddings")
                return OpenAIEmbeddings(
                    model=embedding_model,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            
            elif "cohere" in embedding_model.lower() or embedding_model.startswith("embed-"):
                # Cohere embeddings
                self.logger.info("Using Cohere embeddings")
                return CohereEmbeddings(
                    model=embedding_model,
                    api_key=os.getenv("COHERE_API_KEY")
                )
            
            else:
                # Default to SentenceTransformer (local/HuggingFace models)
                self.logger.info("Using SentenceTransformer embeddings")
                return SentenceTransformerEmbeddings(
                    model=embedding_model,
                    trust_remote_code=True,
                    device="cuda"  # Automatically choose GPU if available
                )
                
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings with {embedding_model}: {e}")
            self.logger.info("Falling back to default embedding model: BAAI/bge-small-en-v1.5")
            
            # Fallback to a smaller, more reliable model
            try:
                return SentenceTransformerEmbeddings(
                    model="BAAI/bge-small-en-v1.5",
                    trust_remote_code=True,
                    device="auto"
                )
            except Exception as fallback_error:
                self.logger.error(f"Fallback embedding initialization also failed: {fallback_error}")
                raise RuntimeError(f"Could not initialize any embedding model. Original error: {e}")

   
if __name__ == "__main__":
    # Example usage
    processor = ChonkieProcessor(
        enable_vision=True,
        embedding_model="BAAI/bge-large-en-v1.5",
        chunk_size=700,
        semantic_threshold=0.75,
        concurrent_agents=10,
        chunking_model="gemini-2.0-flash",
        weaviate_collection="rag_documents"
    )
    
    import asyncio
    result = asyncio.run(processor.process_document_with_duplicate_check("data\\documents\\raw\\Hamza_CV_Updated.pdf", user_id="user123"))
    print(result)