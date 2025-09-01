"""
Embeddings Generator - Convert chunks to vectors for ChromaDB storage

Reads chunk files from data/rag/chunks/ and generates embeddings with metadata.
Outputs ChromaDB-ready format with IDs, vectors, and source metadata using ValidatedEmbedding models.

Dependencies: sentence-transformers, json, pathlib
Integration: Processes TwoStageChunker output for vector storage
"""

import json
import logging
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingsGenerator:
    """Converts chunk files to ChromaDB-ready embeddings with metadata."""
    
    def __init__(self, 
                 model_name: str = "jinaai/jina-embeddings-v3",
                 batch_size: int = 32,
                 chunks_directory: str = "data/rag/chunks",
                 embeddings_directory: str = "data/rag/embeddings"):
        """Initialize the embeddings generator.
        
        Args:
            model_name: Sentence transformer model for embeddings
            batch_size: Number of chunks to process in each batch
            chunks_directory: Directory containing chunk files
            embeddings_directory: Directory to save embeddings output
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.chunks_directory = Path(chunks_directory)
        self.embeddings_directory = Path(embeddings_directory)
        
        # Create output directory
        self.embeddings_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize embedding model (cached for performance)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._cached_embedding_model = SentenceTransformer(model_name, trust_remote_code=True)
                self.logger.info(f"🤖 Embeddings model loaded: {model_name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to load embedding model {model_name}: {e}")
                # Fallback to a reliable model
                try:
                    self._cached_embedding_model = SentenceTransformer('BAAI/bge-large-en-v1.5')
                    self.model_name = 'BAAI/bge-large-en-v1.5'
                    self.logger.info(f"✅ Using fallback model: {self.model_name}")
                except Exception as e2:
                    self.logger.error(f"❌ Fallback model also failed: {e2}")
                    self._cached_embedding_model = None
        else:
            self.logger.error("❌ sentence-transformers not available")
            self._cached_embedding_model = None
        
        self.logger.info(f"🚀 Embeddings Generator initialized (model={self.model_name}, batch_size={batch_size})")
    
    def process_chunks_file(self, chunks_file_path: str) -> Dict[str, Any]:
        """Process a single chunks file and generate embeddings.
        
        Args:
            chunks_file_path: Path to the chunks JSON file
            
        Returns:
            Dict containing ChromaDB-ready data with IDs, vectors, and metadata
        """
        start_time = time.time()
        chunks_path = Path(chunks_file_path)
        
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunks file not found: {chunks_path}")
        
        self.logger.info(f"📄 Processing chunks file: {chunks_path.name}")
        
        # Read chunks data
        try:
            with open(chunks_path, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to read chunks file: {e}")
        
        document_id = chunks_data.get("document_id")
        chunks = chunks_data.get("chunks", [])
        
        if not chunks:
            self.logger.warning(f"⚠️ No chunks found in {chunks_path.name}")
            return self._empty_result(document_id)
        
        # Filter out empty chunks
        valid_chunks = [chunk for chunk in chunks if chunk.get("content", "").strip()]
        if not valid_chunks:
            self.logger.warning(f"⚠️ No valid chunks with content in {chunks_path.name}")
            return self._empty_result(document_id)
        
        self.logger.info(f"📊 Processing {len(valid_chunks)} valid TextChunk models")
        
        # Generate ValidatedEmbedding models
        validated_embeddings = self._generate_validated_embeddings(valid_chunks, document_id)
        
        # Create ChromaDB-ready format from ValidatedEmbedding models
        chromadb_data = self._create_chromadb_format(validated_embeddings)
        
        # Save embeddings to file
        embeddings_path = self._save_embeddings(chromadb_data, validated_embeddings, document_id)
        
        processing_time = time.time() - start_time
        
        self.logger.info(f"✅ Embeddings generated: {len(validated_embeddings)} vectors in {processing_time:.3f}s")
        
        return {
            "document_id": document_id,
            "embeddings_count": len(validated_embeddings),
            "embeddings_file_path": str(embeddings_path),
            "processing_time_seconds": round(processing_time, 3),
            "model_used": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "validated_embeddings": validated_embeddings,  # List of ValidatedEmbedding dicts
            "chromadb_ready": chromadb_data
        }
    
    def _generate_validated_embeddings(self, chunks: List[Dict], document_id: str) -> List[Dict[str, Any]]:
        """Generate ValidatedEmbedding dictionaries for chunks in batches.
        
        Args:
            chunks: List of TextChunk dictionaries
            document_id: Source document identifier
            
        Returns:
            List of ValidatedEmbedding dictionaries
        """
        if not self._cached_embedding_model:
            raise RuntimeError("Embedding model not available")
        
        validated_embeddings = []
        
        # Process chunks in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_texts = [chunk["content"] for chunk in batch]
            
            self.logger.debug(f"🔄 Processing batch {i//self.batch_size + 1}/{(len(chunks)-1)//self.batch_size + 1}")
            
            # Generate embeddings for batch
            try:
                batch_embeddings = self._cached_embedding_model.encode(batch_texts, show_progress_bar=False)
                
                # Process each chunk in batch
                for j, chunk in enumerate(batch):
                    # Create ValidatedEmbedding dictionary
                    validated_embedding = {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"], 
                        "embedding_vector": batch_embeddings[j].tolist(),
                        "embedding_model": self.model_name,
                        "chunk_metadata": {
                            "document_id": chunk["document_id"],
                            "chunk_index": chunk["chunk_index"],
                            "chunk_length": len(chunk["content"]),
                            "word_count": len(chunk["content"].split()),
                            "page_number": chunk["page_number"],
                            "model_used": self.model_name,
                            "timestamp": datetime.now().isoformat()
                        },
                        "chunk_content": chunk["content"]  # Store content for ChromaDB documents field
                    }
                    
                    validated_embeddings.append(validated_embedding)
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to generate embeddings for batch: {e}")
                continue
        
        return validated_embeddings
    
    def _create_chromadb_format(self, validated_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create ChromaDB-ready format from ValidatedEmbedding dictionaries.
        
        Args:
            validated_embeddings: List of ValidatedEmbedding dictionaries
            
        Returns:
            ChromaDB-ready format with ids, embeddings, metadatas, documents
        """
        # Extract chunk content from the original chunks for documents field
        documents = []
        for embedding in validated_embeddings:
            # Get the actual chunk content for ChromaDB documents field
            chunk_content = embedding.get("chunk_content", f"Content for chunk {embedding['chunk_id']}")
            documents.append(chunk_content)
        
        return {
            "ids": [embedding["chunk_id"] for embedding in validated_embeddings],
            "embeddings": [embedding["embedding_vector"] for embedding in validated_embeddings],
            "metadatas": [embedding["chunk_metadata"] for embedding in validated_embeddings],
            "documents": documents
        }
    def _save_embeddings(self, chromadb_data: Dict[str, Any], validated_embeddings: List[Dict[str, Any]], document_id: str) -> Path:
        """Save embeddings data to JSON file.
        
        Args:
            chromadb_data: ChromaDB-ready embeddings data
            validated_embeddings: List of ValidatedEmbedding dictionaries
            document_id: Document identifier
            
        Returns:
            Path to saved embeddings file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"embeddings_{document_id}_{timestamp}.json"
        embeddings_path = self.embeddings_directory / filename
        
        try:
            # Create complete embeddings file with both formats
            embeddings_file_data = {
                "document_id": document_id,
                "model_used": self.model_name,
                "timestamp": datetime.now().isoformat(),
                "embeddings_count": len(validated_embeddings),
                "validated_embeddings": validated_embeddings,  # List of ValidatedEmbedding dicts
                "chromadb_ready": chromadb_data,  # ChromaDB format
                "statistics": {
                    "embedding_dimensions": len(validated_embeddings[0]["embedding_vector"]) if validated_embeddings else 0,
                    "total_chunks": len(validated_embeddings),
                    "avg_chunk_length": round(sum(emb["chunk_metadata"]["chunk_length"] for emb in validated_embeddings) / len(validated_embeddings), 1) if validated_embeddings else 0
                }
            }
            
            with open(embeddings_path, 'w', encoding='utf-8') as f:
                json.dump(embeddings_file_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 ValidatedEmbeddings saved: {embeddings_path}")
            return embeddings_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save ValidatedEmbeddings: {e}")
            return embeddings_path
    
    def _empty_result(self, document_id: str) -> Dict[str, Any]:
        """Return empty result structure.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Empty result dictionary
        """
        return {
            "document_id": document_id,
            "embeddings_count": 0,
            "embeddings_file_path": None,
            "processing_time_seconds": 0.0,
            "model_used": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "validated_embeddings": [],  # Empty list of ValidatedEmbedding dicts
            "chromadb_ready": {
                "ids": [],
                "embeddings": [],
                "metadatas": [],
                "documents": []
            }
        }
    
    # HELPER FUNCTIONS
    def get_embeddings_directory(self) -> str:
        """Get the embeddings output directory path."""
        return str(self.embeddings_directory)
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration settings."""
        return {
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "chunks_directory": str(self.chunks_directory),
            "embeddings_directory": str(self.embeddings_directory),
            "model_available": self._cached_embedding_model is not None
        }
    
    def list_chunk_files(self) -> List[str]:
        """List available chunk files for processing."""
        chunk_files = list(self.chunks_directory.glob("chunks_*.json"))
        return [str(f) for f in sorted(chunk_files, key=lambda x: x.stat().st_mtime, reverse=True)]