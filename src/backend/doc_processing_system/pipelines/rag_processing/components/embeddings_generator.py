"""
Embeddings Generator - Convert chunks to vectors for ChromaDB storage

Reads chunk files from data/rag/chunks/ and generates embeddings with metadata.
Outputs ChromaDB-ready format with IDs, vectors, and source metadata.

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
        
        self.logger.info(f"📊 Processing {len(valid_chunks)} valid chunks")
        
        # Generate embeddings
        embeddings_result = self._generate_embeddings(valid_chunks, document_id)
        
        # Save embeddings to file
        embeddings_path = self._save_embeddings(embeddings_result, document_id)
        
        processing_time = time.time() - start_time
        
        self.logger.info(f"✅ Embeddings generated: {len(embeddings_result['ids'])} vectors in {processing_time:.3f}s")
        
        return {
            "document_id": document_id,
            "embeddings_count": len(embeddings_result['ids']),
            "embeddings_file_path": str(embeddings_path),
            "processing_time_seconds": round(processing_time, 3),
            "model_used": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "chromadb_ready": embeddings_result
        }
    
    def _generate_embeddings(self, chunks: List[Dict], document_id: str) -> Dict[str, Any]:
        """Generate embeddings for chunks in batches.
        
        Args:
            chunks: List of chunk dictionaries
            document_id: Source document identifier
            
        Returns:
            ChromaDB-ready format with IDs, embeddings, metadatas, documents
        """
        if not self._cached_embedding_model:
            raise RuntimeError("Embedding model not available")
        
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
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
                    # Generate unique ID
                    chunk_id = self._generate_chunk_id(document_id, chunk["index"])
                    
                    # Create metadata
                    metadata = {
                        "document_id": document_id,
                        "chunk_index": chunk["index"],
                        "chunk_length": chunk["length"],
                        "word_count": chunk["word_count"],
                        "model_used": self.model_name,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    ids.append(chunk_id)
                    embeddings.append(batch_embeddings[j].tolist())
                    metadatas.append(metadata)
                    documents.append(chunk["content"])
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to generate embeddings for batch: {e}")
                continue
        
        return {
            "ids": ids,
            "embeddings": embeddings,
            "metadatas": metadatas,
            "documents": documents
        }
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique ID for chunk.
        
        Args:
            document_id: Source document identifier
            chunk_index: Index of chunk within document
            
        Returns:
            Unique chunk identifier
        """
        # Create deterministic ID based on document and chunk index
        id_string = f"{document_id}_{chunk_index}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def _save_embeddings(self, embeddings_data: Dict[str, Any], document_id: str) -> Path:
        """Save embeddings data to JSON file.
        
        Args:
            embeddings_data: ChromaDB-ready embeddings data
            document_id: Document identifier
            
        Returns:
            Path to saved embeddings file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"embeddings_{document_id}_{timestamp}.json"
        embeddings_path = self.embeddings_directory / filename
        
        try:
            with open(embeddings_path, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Embeddings saved: {embeddings_path}")
            return embeddings_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save embeddings: {e}")
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