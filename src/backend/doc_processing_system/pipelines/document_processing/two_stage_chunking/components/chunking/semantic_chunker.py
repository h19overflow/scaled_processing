"""
Semantic Chunker - Stage 1 of 2-stage chunking system

Performs initial semantic chunking using LangChain's SemanticChunker with Nomic embeddings.
Creates context-aware chunks that maintain semantic coherence but may have imperfect boundaries.

Dependencies: sentence-transformers, langchain-experimental
Integration: Used by TwoStageChunker for initial pass
"""

import logging
import time
from typing import List, Dict, Any
from pathlib import Path

try:
    from langchain_experimental.text_splitter import SemanticChunker as LangChainSemanticChunker
    from langchain_core.embeddings import Embeddings
    LANGCHAIN_SEMANTIC_AVAILABLE = True
except ImportError:
    LANGCHAIN_SEMANTIC_AVAILABLE = False
    class Embeddings:
        pass


class SentenceTransformerEmbeddings(Embeddings):
    """Wrapper for SentenceTransformer models to work with LangChain."""
    
    def __init__(self, model_name: str = 'BAAI/bge-small-en-v1.5'):
        """Initialize the SentenceTransformer embeddings wrapper.
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        try:
            from sentence_transformers import SentenceTransformer
            # Use a reliable model that doesn't need trust_remote_code
            self.model = SentenceTransformer(model_name)
            print(f"✅ Successfully loaded embedding model: {model_name}")
        except Exception as e:
            print(f"❌ Failed to load {model_name}, trying fallback: {e}")
            # Fallback to a more standard model
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs.
        
        Args:
            texts: List of text to embed.
            
        Returns:
            List of embeddings.
        """
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text.
        
        Args:
            text: Text to embed.
            
        Returns:
            Embedding.
        """
        embedding = self.model.encode([text])
        return embedding[0].tolist()


class SemanticChunker:
    """Stage 1 chunker using semantic similarity for initial document splitting."""

    def __init__(self, chunk_size: int = 8192, threshold: float = 0.75):
        """Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            threshold: Semantic similarity threshold for splits
        """
        self.chunk_size = chunk_size
        self.threshold = threshold
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize semantic chunker once at startup
        self._cached_chunker = self._initialize_chunker()
        
    def _initialize_chunker(self):
        """Initialize semantic chunker with embeddings."""
        try:
            if LANGCHAIN_SEMANTIC_AVAILABLE:
                # Create embeddings wrapper
                embeddings = SentenceTransformerEmbeddings('BAAI/bge-small-en-v1.5')
                
                # Calculate min_chunk_size based on chunk_size
                min_chunk_size = max(500, self.chunk_size // 4)
                
                chunker = LangChainSemanticChunker(
                    embeddings=embeddings, 
                    breakpoint_threshold_amount=self.threshold,
                    min_chunk_size=min_chunk_size
                )
                
                self.logger.info(f"✅ Semantic chunker initialized (threshold={self.threshold}, min_size={min_chunk_size})")
                return chunker
            else:
                self.logger.warning("⚠️ langchain_experimental not available, using fallback")
                return None
                
        except Exception as e:
            self.logger.warning(f"⚠️ Semantic chunker failed to initialize: {e}")
            return None
    
    def chunk_text(self, text: str, document_id: str) -> Dict[str, Any]:
        """Split text into semantic chunks.
        
        Args:
            text: Text content to chunk
            document_id: Document identifier for tracking
            
        Returns:
            Dict containing chunks and metadata
        """
        start_time = time.time()
        
        if self._cached_chunker:
            try:
                # Create semantic chunks using LangChain
                docs = self._cached_chunker.create_documents([text])
                chunks = [d.page_content for d in docs]
                
                if not chunks:
                    self.logger.warning(f"⚠️ Semantic chunker produced no chunks for {document_id}")
                    chunks = self._fallback_chunker(text)
                    method_used = "fallback"
                else:
                    method_used = "semantic"
                    
            except Exception as e:
                self.logger.error(f"❌ Semantic chunking failed for {document_id}: {e}")
                chunks = self._fallback_chunker(text)
                method_used = "fallback"
        else:
            chunks = self._fallback_chunker(text)
            method_used = "fallback"
        
        processing_time = time.time() - start_time
        
        # Calculate chunk statistics
        chunk_lengths = [len(chunk) for chunk in chunks]
        
        result = {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "method_used": method_used,
            "processing_time_seconds": round(processing_time, 3),
            "chunk_statistics": {
                "min_length": min(chunk_lengths) if chunk_lengths else 0,
                "max_length": max(chunk_lengths) if chunk_lengths else 0,
                "avg_length": round(sum(chunk_lengths) / len(chunk_lengths), 1) if chunk_lengths else 0,
                "total_chars": sum(chunk_lengths)
            },
            "configuration": {
                "chunk_size": self.chunk_size,
                "threshold": self.threshold
            }
        }
        
        self.logger.info(f"📊 Stage 1 complete: {len(chunks)} chunks in {processing_time:.3f}s using {method_used}")
        return result
    
    def _fallback_chunker(self, text: str) -> List[str]:
        """Simple fallback chunker when semantic chunking fails."""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks