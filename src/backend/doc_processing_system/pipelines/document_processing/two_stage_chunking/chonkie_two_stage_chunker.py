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
                 embedding_model: str = "BAAI/bge-small-en-v1.5",
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
        # Try to use the existing event loop if available, otherwise create new one
        try:
            # Check if there's already a running event loop
            loop = asyncio.get_running_loop()
            # If we get here, there's already a loop running
            # We need to run this in a thread to avoid the conflict
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_chunk_async, text, **kwargs)
                return future.result()
        except RuntimeError:
            # No running event loop, we can create our own
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.chunk_async(text, **kwargs))
            finally:
                loop.close()
    
    def _run_chunk_async(self, text: str, **kwargs) -> List[Chunk]:
        """Helper method to run chunk_async in a new event loop."""
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

        # Save intermediate result - raw chunk data from TwoStageChunker
        document_id_safe = document_id or "chonkie_doc"
        self._save_intermediate_results("01_raw_text_chunks", result["text_chunks"], document_id_safe)

        # Convert to Chonkie Chunk format
        chonkie_chunks = []
        for i, chunk_data in enumerate(result["text_chunks"]):
            # Add metadata after construction - ensure chunk_data["metadata"] is a dict
            metadata = chunk_data.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            
            # Create Chonkie Chunk object (without metadata parameter)
            chunk = Chunk(
                text=chunk_data["content"],
                start_index=0,  # We don't track character positions in our chunker
                end_index=len(chunk_data["content"]),
                token_count=metadata.get("word_count", len(chunk_data["content"].split())),  # Safe fallback
            )
                
            chunk.context = {
                **metadata,
                "chunk_id": chunk_data["chunk_id"],
                "chunk_index": chunk_data["chunk_index"],
                "document_id": chunk_data["document_id"],
                "chunking_method": "two_stage_semantic_boundary",
                "semantic_threshold": self.semantic_threshold,
                "boundary_context": self.boundary_context,
                "concurrent_agents": self.concurrent_agents,
                "model_name": self.model_name
            }
            chonkie_chunks.append(chunk)

        # Save intermediate result - initial Chonkie chunks
        self._save_intermediate_results("02_initial_chonkie_chunks", chonkie_chunks, document_id_safe)

        # Apply OverlapRefinery post-processing
        refined_chunks = self.refinery(chonkie_chunks)
        
        # Save intermediate result - refined chunks
        self._save_intermediate_results("03_refined_chunks", refined_chunks, document_id_safe)

        return refined_chunks

    def generate_embeddings(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for chunks using SentenceTransformer.
        
        Args:
            chunks: List of Chunk objects to embed
            
        Returns:
            List of Chunk objects with embeddings in metadata
        """
        # Save intermediate result - chunks before embedding
        self._save_intermediate_results("04_chunks_before_embedding", chunks, "embedding_process")
        
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding for chunk text
                vector = self.embeddings.embed(chunk.text)

                # Ensure chunk.context is a dictionary (fix for str assignment error)
                if chunk.context is None or not isinstance(chunk.context, dict):
                    # Save problematic context for debugging
                    if chunk.context is not None:
                        self._save_problematic_context(chunk.context, i)
                    chunk.context = {}
                    
                chunk.context["embedding"] = vector
                chunk.context["embedding_model"] = self.embedding_model

            except Exception as e:
                # Log error but continue processing other chunks
                chunk_id = 'unknown'
                if chunk.context and isinstance(chunk.context, dict):
                    chunk_id = chunk.context.get('chunk_id', 'unknown')
                print(f"Failed to generate embedding for chunk {chunk_id}: {e}")
                
                # Ensure chunk.context is a dictionary before assignment
                if chunk.context is None or not isinstance(chunk.context, dict):
                    if chunk.context is not None:
                        self._save_problematic_context(chunk.context, i)
                    chunk.context = {}
                chunk.context["embedding_error"] = str(e)

        # Save intermediate result - final embedded chunks
        self._save_intermediate_results("05_final_embedded_chunks", chunks, "embedding_process")
        
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
    
    # HELPER FUNCTIONS
    def _save_problematic_context(self, problematic_context, chunk_index: int):
        """Save problematic context data for debugging."""
        import json
        from pathlib import Path
        from datetime import datetime
        
        debug_dir = Path("data/debug/problematic_contexts")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"problematic_context_{timestamp}_chunk_{chunk_index}.json"
        
        debug_data = {
            "chunk_index": chunk_index,
            "context_type": type(problematic_context).__name__,
            "context_value": str(problematic_context),
            "context_repr": repr(problematic_context),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2)
            print(f"🔍 Saved problematic context to: {debug_file}")
        except Exception as e:
            print(f"❌ Failed to save problematic context: {e}")
    
    def _save_intermediate_results(self, step_name: str, data, document_id: str):
        """Save intermediate processing results for debugging."""
        import json
        from pathlib import Path
        from datetime import datetime
        
        debug_dir = Path("data/debug/intermediate_results")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"{document_id}_{step_name}_{timestamp}.json"
        
        # Convert data to JSON-serializable format
        if hasattr(data, '__dict__'):
            serializable_data = data.__dict__
        elif isinstance(data, list):
            serializable_data = []
            for item in data:
                if hasattr(item, '__dict__'):
                    serializable_data.append(item.__dict__)
                else:
                    serializable_data.append(str(item))
        else:
            serializable_data = str(data)
        
        debug_data = {
            "step": step_name,
            "document_id": document_id,
            "data_type": type(data).__name__,
            "data": serializable_data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, default=str)
            print(f"🔍 Saved intermediate results to: {debug_file}")
        except Exception as e:
            print(f"❌ Failed to save intermediate results: {e}")
