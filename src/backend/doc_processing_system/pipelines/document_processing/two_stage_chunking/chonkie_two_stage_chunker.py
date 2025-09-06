"""
ChonkieTwoStageChunker - Custom Chonkie chunker wrapping our existing TwoStageChunker.
Integrates our semantic chunking + boundary refinement workflow into the Chonkie framework.
"""

import asyncio
from typing import List, Dict, Any, Optional

from chonkie import BaseChunker, OverlapRefinery, SentenceTransformerEmbeddings
from chonkie.types import Chunk
from .components.chunking.two_stage_chunker import TwoStageChunker


class ChonkieTwoStageChunker(BaseChunker):
    """Custom Chonkie chunker wrapping our existing TwoStageChunker with semantic + boundary refinement."""
    
    def __init__(self, 
                 chunk_size: int = 700,
                 semantic_threshold: float = 0.75,
                 boundary_context: int = 200,
                 concurrent_agents: int = 10,
                 model_name: str = "gemini-2.0-flash",
                 embedding_model: str = "nomic-ai/nomic-embed-text-v1.5",
                 tokenizer_or_token_counter: Optional[Any] = None):
        """Initialize the ChonkieTwoStageChunker.
        
        Args:
            chunk_size: Target chunk size for semantic chunking
            semantic_threshold: Similarity threshold for semantic splits
            boundary_context: Context window for boundary analysis
            concurrent_agents: Number of concurrent boundary review agents
            model_name: LLM model for boundary decisions
            embedding_model: Hugging Face model for embeddings
            tokenizer_or_token_counter: Tokenizer for Chonkie compatibility (not used in our implementation)
        """
        # Simple word-based token counter if none provided
        if tokenizer_or_token_counter is None:
            tokenizer_or_token_counter = lambda text: len(text.split())
        
        super().__init__(tokenizer_or_token_counter)
        
        # Store configuration
        self.chunk_size = chunk_size
        self.semantic_threshold = semantic_threshold
        self.boundary_context = boundary_context
        self.concurrent_agents = concurrent_agents
        self.model_name = model_name
        self.embedding_model = embedding_model
        
        # Initialize our existing two-stage chunker
        self.two_stage_chunker = TwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            concurrent_agents=concurrent_agents,
            model_name=model_name
        )
        
        # Initialize OverlapRefinery for post-processing
        self.refinery = OverlapRefinery(
            tokenizer_or_token_counter="character",
            context_size=0.35,
            merge=True
        )
        
        # Initialize embeddings for chunk embedding generation
        self.embeddings = SentenceTransformerEmbeddings(embedding_model)
    
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """Chonkie interface method using our two-stage chunker (sync version).
        
        Args:
            text: Text to chunk
            **kwargs: Additional keyword arguments
            
        Returns:
            List of Chonkie Chunk objects
        """
        # Run the async version synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.chunk_async(text, **kwargs))
        finally:
            loop.close()
    
    async def chunk_async(self, text: str, document_id: Optional[str] = None, **kwargs) -> List[Chunk]:
        """Async Chonkie interface method using our two-stage chunker.
        
        Args:
            text: Text to chunk
            document_id: Optional document identifier
            **kwargs: Additional keyword arguments
            
        Returns:
            List of Chonkie Chunk objects
        """
        # Use our existing chunker logic
        result = await self.two_stage_chunker.process_document_text(
            text, 
            document_id or "chonkie_doc"
        )
        
        # Convert to Chonkie Chunk format
        chonkie_chunks = []
        for i, chunk_data in enumerate(result["text_chunks"]):
            # Create Chonkie Chunk object
            chunk = Chunk(
                text=chunk_data["content"],
                start_index=0,  # We don't track character positions in our chunker
                end_index=len(chunk_data["content"]),
                token_count=chunk_data["metadata"]["word_count"],  # Approximate
                metadata={
                    **chunk_data["metadata"],
                    "chunk_id": chunk_data["chunk_id"],
                    "chunk_index": chunk_data["chunk_index"],
                    "document_id": chunk_data["document_id"],
                    "chunking_method": "two_stage_semantic_boundary",
                    "semantic_threshold": self.semantic_threshold,
                    "boundary_context": self.boundary_context,
                    "concurrent_agents": self.concurrent_agents,
                    "model_name": self.model_name
                }
            )
            chonkie_chunks.append(chunk)
        
        # Apply OverlapRefinery post-processing
        refined_chunks = self.refinery(chonkie_chunks)
        
        return refined_chunks
    
    def generate_embeddings(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for chunks using SentenceTransformer.
        
        Args:
            chunks: List of Chunk objects to embed
            
        Returns:
            List of Chunk objects with embeddings in metadata
        """
        for chunk in chunks:
            try:
                # Generate embedding for chunk text
                vector = self.embeddings.embed(chunk.text)
                
                # Add embedding to chunk metadata
                chunk.metadata["embedding"] = vector
                chunk.metadata["embedding_model"] = self.embedding_model
                
            except Exception as e:
                # Log error but continue processing other chunks
                print(f"Failed to generate embedding for chunk {chunk.metadata.get('chunk_id', 'unknown')}: {e}")
                chunk.metadata["embedding_error"] = str(e)
        
        return chunks
    
    async def chunk_with_embeddings(self, text: str, document_id: Optional[str] = None, **kwargs) -> List[Chunk]:
        """Generate chunks with embeddings in one step.
        
        Args:
            text: Text to chunk
            document_id: Optional document identifier
            **kwargs: Additional keyword arguments
            
        Returns:
            List of Chunk objects with embeddings
        """
        # First, get refined chunks
        refined_chunks = await self.chunk_async(text, document_id, **kwargs)
        
        # Then generate embeddings
        embedded_chunks = self.generate_embeddings(refined_chunks)
        
        return embedded_chunks
    
    def get_params(self) -> Dict[str, Any]:
        """Return chunker parameters for Chonkie."""
        return {
            "chunk_size": self.chunk_size,
            "semantic_threshold": self.semantic_threshold,
            "boundary_context": self.boundary_context,
            "concurrent_agents": self.concurrent_agents,
            "model_name": self.model_name,
            "chunking_strategy": "two_stage_semantic_boundary"
        }
    
    def __repr__(self) -> str:
        """String representation of the chunker."""
        return (
            f"ChonkieTwoStageChunker("
            f"chunk_size={self.chunk_size}, "
            f"semantic_threshold={self.semantic_threshold}, "
            f"concurrent_agents={self.concurrent_agents}, "
            f"model='{self.model_name}')"
        )