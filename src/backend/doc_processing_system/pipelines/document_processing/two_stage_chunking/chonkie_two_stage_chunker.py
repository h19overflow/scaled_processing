"""
ChonkieTwoStageChunker - Custom Chonkie chunker wrapping our existing TwoStageChunker.
Integrates our semantic chunking + boundary refinement workflow into the Chonkie framework.
"""

import asyncio
from typing import List, Dict, Any, Optional

from chonkie import BaseChunker
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
                 tokenizer_or_token_counter: Optional[Any] = None):
        """Initialize the ChonkieTwoStageChunker.
        
        Args:
            chunk_size: Target chunk size for semantic chunking
            semantic_threshold: Similarity threshold for semantic splits
            boundary_context: Context window for boundary analysis
            concurrent_agents: Number of concurrent boundary review agents
            model_name: LLM model for boundary decisions
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
        
        # Initialize our existing two-stage chunker
        self.two_stage_chunker = TwoStageChunker(
            chunk_size=chunk_size,
            semantic_threshold=semantic_threshold,
            boundary_context=boundary_context,
            concurrent_agents=concurrent_agents,
            model_name=model_name
        )
    
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
        
        return chonkie_chunks
    
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