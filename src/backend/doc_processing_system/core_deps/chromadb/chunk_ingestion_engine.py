"""
Chunk ingestion engine for ChromaDB vector storage.
Handles loading chunks and embeddings from JSON files and storing them in ChromaDB.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .chroma_manager import ChromaManager, chroma_manager


class ChunkIngestionEngine:
    """
    Engine for ingesting processed chunks and embeddings into ChromaDB.
    Handles file loading, validation, and vector storage operations.
    """
    
    def __init__(self, chroma_manager: ChromaManager = None):
        """
        Initialize chunk ingestion engine.
        
        Args:
            chroma_manager: ChromaDB manager instance (uses global if not provided)
        """
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Use provided or global chroma manager
        self._cached_chroma_manager = chroma_manager or chroma_manager
        
        # Data paths
        self.chunks_dir = Path("data/rag/chunks")
        self.embeddings_dir = Path("data/rag/embeddings")
        
        self.logger.info("ChunkIngestionEngine initialized with ChromaDB integration")
    
    def ingest_document(self, document_id: str, collection_name: str = None) -> bool:
        """
        Ingest a complete document's chunks and embeddings into ChromaDB.
        
        Args:
            document_id: Document identifier to ingest
            collection_name: ChromaDB collection name (optional)
            
        Returns:
            bool: True if ingestion successful
        """
        self.logger.info(f"🚀 Starting document ingestion: {document_id}")
        
        try:
            # Find latest chunk and embedding files
            chunks_data = self._load_latest_chunks(document_id)
            embeddings_data = self._load_latest_embeddings(document_id)
            
            if not chunks_data or not embeddings_data:
                self.logger.error(f"❌ Missing data files for document: {document_id}")
                return False
            
            # Validate data consistency
            if not self._validate_data_consistency(chunks_data, embeddings_data):
                self.logger.error(f"❌ Data consistency validation failed: {document_id}")
                return False
            
            # Prepare ChromaDB format
            chromadb_data = self._prepare_chromadb_format(chunks_data, embeddings_data)
            
            # Store in ChromaDB
            success = self._store_in_chromadb(chromadb_data, collection_name)
            
            if success:
                self.logger.info(f"✅ Document ingestion completed: {document_id}")
                self.logger.info(f"📊 Stored {len(chromadb_data['ids'])} chunks in ChromaDB")
            else:
                self.logger.error(f"❌ ChromaDB storage failed: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Document ingestion failed for {document_id}: {e}")
            return False
    
    def ingest_from_chromadb_ready_file(self, embeddings_file_path: str, collection_name: str = None) -> bool:
        """
        Ingest directly from embeddings file with ChromaDB-ready format.
        
        Args:
            embeddings_file_path: Path to embeddings JSON file
            collection_name: ChromaDB collection name (optional)
            
        Returns:
            bool: True if ingestion successful
        """
        try:
            embeddings_data = self._load_json_file(embeddings_file_path)
            if not embeddings_data:
                return False
            
            # Extract ChromaDB-ready format
            chromadb_data = embeddings_data.get("chromadb_ready")
            if not chromadb_data:
                self.logger.error(f"No chromadb_ready format found in: {embeddings_file_path}")
                return False
            
            # Validate format
            if not self._validate_chromadb_format(chromadb_data):
                self.logger.error(f"Invalid ChromaDB format in: {embeddings_file_path}")
                return False
            
            # Store in ChromaDB
            return self._store_in_chromadb(chromadb_data, collection_name)
            
        except Exception as e:
            self.logger.error(f"Failed to ingest from ChromaDB-ready file: {e}")
            return False
    
    def _load_latest_chunks(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest chunks file for a document."""
        pattern = f"chunks_{document_id}_*.json"
        return self._load_latest_file(self.chunks_dir, pattern)
    
    def _load_latest_embeddings(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest embeddings file for a document."""
        pattern = f"embeddings_{document_id}_*.json"
        return self._load_latest_file(self.embeddings_dir, pattern)
    
    def _load_latest_file(self, directory: Path, pattern: str) -> Optional[Dict[str, Any]]:
        """Load the most recent file matching the pattern."""
        try:
            files = list(directory.glob(pattern))
            if not files:
                self.logger.warning(f"No files found matching pattern: {pattern}")
                return None
            
            # Get most recent file
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            self.logger.info(f"📁 Loading: {latest_file.name}")
            
            return self._load_json_file(str(latest_file))
            
        except Exception as e:
            self.logger.error(f"Failed to load latest file {pattern}: {e}")
            return None
    
    def _load_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load and parse JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            return None
    
    def _validate_data_consistency(self, chunks_data: Dict, embeddings_data: Dict) -> bool:
        """Validate chunks and embeddings data consistency."""
        try:
            # Check document IDs match
            chunks_doc_id = chunks_data.get("document_id")
            embeddings_doc_id = embeddings_data.get("document_id")
            
            if chunks_doc_id != embeddings_doc_id:
                self.logger.error(f"Document ID mismatch: {chunks_doc_id} != {embeddings_doc_id}")
                return False
            
            # Check chunk counts match
            chunk_count = len(chunks_data.get("chunks", []))
            embeddings_count = len(embeddings_data.get("validated_embeddings", []))
            
            if chunk_count != embeddings_count:
                self.logger.error(f"Count mismatch: {chunk_count} chunks != {embeddings_count} embeddings")
                return False
            
            # Check chunk IDs match
            chunk_ids = {chunk["chunk_id"] for chunk in chunks_data.get("chunks", [])}
            embedding_ids = {emb["chunk_id"] for emb in embeddings_data.get("validated_embeddings", [])}
            
            if chunk_ids != embedding_ids:
                self.logger.error("Chunk ID mismatch between chunks and embeddings")
                return False
            
            self.logger.info(f"✅ Data consistency validated: {chunk_count} chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Data consistency validation failed: {e}")
            return False
    
    def _prepare_chromadb_format(self, chunks_data: Dict, embeddings_data: Dict) -> Dict[str, List]:
        """Prepare data in ChromaDB format."""
        try:
            # Check if ChromaDB-ready format already exists
            if "chromadb_ready" in embeddings_data:
                self.logger.info("Using existing ChromaDB-ready format")
                return embeddings_data["chromadb_ready"]
            
            # Build ChromaDB format manually
            ids = []
            embeddings = []
            metadatas = []
            documents = []
            
            # Create chunk ID to data mapping
            chunk_map = {chunk["chunk_id"]: chunk for chunk in chunks_data["chunks"]}
            
            # Process embeddings and match with chunks
            for emb_data in embeddings_data["validated_embeddings"]:
                chunk_id = emb_data["chunk_id"]
                chunk = chunk_map.get(chunk_id)
                
                if not chunk:
                    self.logger.warning(f"No chunk found for embedding: {chunk_id}")
                    continue
                
                ids.append(chunk_id)
                embeddings.append(emb_data["embedding_vector"])
                documents.append(chunk["content"])
                
                # Combine metadata from chunk and embedding
                metadata = {
                    **chunk.get("metadata", {}),
                    **emb_data.get("chunk_metadata", {}),
                    "document_id": chunk["document_id"],
                    "chunk_index": chunk["chunk_index"],
                    "page_number": chunk["page_number"],
                    "ingested_at": datetime.now().isoformat()
                }
                metadatas.append(metadata)
            
            result = {
                "ids": ids,
                "embeddings": embeddings,
                "metadatas": metadatas,
                "documents": documents
            }
            
            self.logger.info(f"📦 Prepared ChromaDB format: {len(ids)} items")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to prepare ChromaDB format: {e}")
            return {}
    
    def _store_in_chromadb(self, chromadb_data: Dict[str, List], collection_name: str = None) -> bool:
        """Store data in ChromaDB collection."""
        try:
            collection = self._cached_chroma_manager.get_collection(collection_name)
            if not collection:
                self.logger.error("Failed to get ChromaDB collection")
                return False
            
            # Validate format before storing
            if not self._validate_chromadb_format(chromadb_data):
                self.logger.error("Invalid ChromaDB format")
                return False
            
            # Store in ChromaDB
            collection.add(
                ids=chromadb_data["ids"],
                embeddings=chromadb_data["embeddings"],
                metadatas=chromadb_data["metadatas"],
                documents=chromadb_data["documents"]
            )
            
            self.logger.info(f"✅ Stored {len(chromadb_data['ids'])} chunks in ChromaDB")
            return True
            
        except Exception as e:
            self.logger.error(f"ChromaDB storage failed: {e}")
            return False
    
    def get_ingestion_stats(self, collection_name: str = None) -> Dict[str, Any]:
        """Get ingestion statistics for a collection."""
        try:
            collection_info = self._cached_chroma_manager.get_collection_info(collection_name)
            if not collection_info:
                return {}
            
            return {
                "collection_name": collection_info["name"],
                "document_count": collection_info["count"],
                "created_at": collection_info.get("metadata", {}).get("created_at"),
                "persist_directory": collection_info["persist_directory"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get ingestion stats: {e}")
            return {}

    # HELPER FUNCTIONS
    def _validate_chromadb_format(self, data: Dict[str, Any]) -> bool:
        """Validate ChromaDB-ready format structure."""
        required_keys = ["ids", "embeddings", "metadatas", "documents"]
        
        if not all(key in data for key in required_keys):
            self.logger.error(f"Missing required keys. Expected: {required_keys}")
            return False
            
        # Check all arrays have same length
        lengths = [len(data[key]) for key in required_keys]
        if len(set(lengths)) != 1:
            self.logger.error(f"Array length mismatch: {dict(zip(required_keys, lengths))}")
            return False
            
        return True


# Global instance for easy import and sharing  
chunk_ingestion_engine = ChunkIngestionEngine()