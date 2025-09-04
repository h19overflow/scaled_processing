"""
Weaviate ingestion engine - Drop-in replacement for ChromaDB ChunkIngestionEngine.
Handles loading chunks and embeddings from JSON files and storing them in Weaviate.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..weaviate_manager import WeaviateManager


class WeaviateIngestionEngine:
    """Drop-in replacement for ChunkIngestionEngine with identical interface."""
    
    def __init__(self, weaviate_manager: WeaviateManager = None):
        """Initialize Weaviate ingestion engine."""
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Use provided manager or create new one
        self._cached_weaviate_manager = weaviate_manager or WeaviateManager()
        
        # Data paths (same as ChromaDB version)
        self.chunks_dir = Path("data/rag/chunks")
        self.embeddings_dir = Path("data/rag/embeddings")
        
        self.logger.info("WeaviateIngestionEngine initialized")
    
    def ingest_document(self, document_id: str, collection_name: str = "rag_documents") -> bool:
        """Ingest a complete document's chunks and embeddings into Weaviate."""
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
            
            # Prepare ChromaDB format first, then convert to Weaviate
            chromadb_data = self._prepare_chromadb_format(chunks_data, embeddings_data)
            
            # Store in Weaviate (converts format internally)
            success = self._store_in_weaviate(chromadb_data, collection_name)
            
            if success:
                self.logger.info(f"✅ Document ingestion completed: {document_id}")
                self.logger.info(f"📊 Stored {len(chromadb_data['ids'])} chunks in Weaviate")
            else:
                self.logger.error(f"❌ Weaviate storage failed: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Document ingestion failed for {document_id}: {e}")
            return False

    def ingest_from_embeddings_file(self, embeddings_file_path: str, collection_name: str = "rag_documents") -> bool:
        """Ingest directly from embeddings file - handles both new format and ChromaDB-ready format."""
        try:
            self.logger.info(f"🚀 Starting ingestion from embeddings file: {embeddings_file_path}")
            self.logger.info(f"🗄️ Target collection: {collection_name or 'default'}")
            
            # Load JSON file
            self.logger.info(f"📁 Loading embeddings file...")
            embeddings_data = self._load_json_file(embeddings_file_path)
            if not embeddings_data:
                self.logger.error(f"❌ Failed to load embeddings file: {embeddings_file_path}")
                return False
            
            self.logger.info(f"✅ Loaded embeddings file successfully")
            self.logger.debug(f"🔍 File keys: {list(embeddings_data.keys())}")
            
            # Check if this is the new validated_embeddings format
            if "validated_embeddings" in embeddings_data:
                self.logger.info("🔍 Found validated_embeddings format - using direct Weaviate ingestion")
                return self._ingest_validated_embeddings(embeddings_data, collection_name)
            
            # Fallback to ChromaDB-ready format
            self.logger.info("🔍 Extracting chromadb_ready format...")
            chromadb_data = embeddings_data.get("chromadb_ready")
            if not chromadb_data:
                self.logger.error(f"❌ No chromadb_ready format found in: {embeddings_file_path}")
                self.logger.error(f"🔍 Available keys in file: {list(embeddings_data.keys())}")
                return False
            
            self.logger.info("✅ Found chromadb_ready format")
            
            # Store in Weaviate using ChromaDB conversion
            self.logger.info("🚀 Proceeding to store in Weaviate...")
            result = self._store_in_weaviate(chromadb_data, collection_name)
            
            if result:
                self.logger.info(f"✅ Successfully ingested from embeddings file")
                return True
            else:
                self.logger.error(f"❌ Failed to store in Weaviate")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ingestion from embeddings file failed: {e}")
            return False
    
    def get_ingestion_stats(self, collection_name: str = "rag_documents") -> Dict[str, Any]:
        """Get ingestion statistics for a collection."""
        try:
            collection_info = self._cached_weaviate_manager.get_collection_info(collection_name)
            if not collection_info:
                return {}
            
            return {
                "collection_name": collection_info["name"],
                "document_count": collection_info["count"],
                "created_at": collection_info.get("metadata", {}).get("created_at"),
                "last_updated": collection_info.get("metadata", {}).get("last_updated"),
                "vector_dimensions": collection_info.get("vector_dimensions"),
                "total_vectors": collection_info["count"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get ingestion stats: {e}")
            return {}

    # HELPER FUNCTIONS
    def _load_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load JSON file and return data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            return None
    
 
    
    def _store_in_weaviate(self, chromadb_data: Dict[str, Any], collection_name: str) -> bool:
        """Convert ChromaDB format to Weaviate format and store."""
        try:
            collection = self._cached_weaviate_manager.get_collection(collection_name)
            if collection is None:
                self.logger.error(f"Failed to get/create collection: {collection_name}")
                return False
            
            # Convert ChromaDB format to Weaviate objects
            weaviate_objects = self._convert_chromadb_to_weaviate(chromadb_data)
            
            # Batch insert into Weaviate
            with collection.batch.fixed_size(batch_size=100) as batch:
                for obj in weaviate_objects:
                    batch.add_object(
                        properties=obj["properties"],
                        vector=obj["vector"],
                    )
                    if batch.number_errors > 10:
                        self.logger.error("Batch import stopped due to excessive errors")
                        return False
            
            failed_objects = collection.batch.failed_objects
            if failed_objects:
                self.logger.warning(f"Number of failed imports: {len(failed_objects)}")
                return len(failed_objects) < len(weaviate_objects) * 0.1  # Allow up to 10% failures
            
            self.logger.info(f"Successfully stored {len(weaviate_objects)} objects in Weaviate")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store in Weaviate: {e}")
            return False
    
    def _convert_chromadb_to_weaviate(self, chromadb_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert ChromaDB format to Weaviate objects format."""
        objects = []
        
        ids = chromadb_data.get("ids", [])
        embeddings = chromadb_data.get("embeddings", [])
        metadatas = chromadb_data.get("metadatas", [])
        documents = chromadb_data.get("documents", [])
        
        for i, doc_id in enumerate(ids):
            obj = {
                "id": doc_id,
                "properties": {
                    "content": documents[i] if i < len(documents) else "",
                    **(metadatas[i] if i < len(metadatas) else {})
                },
                "vector": embeddings[i] if i < len(embeddings) else []
            }
            objects.append(obj)
        
        return objects
    
    def _ingest_validated_embeddings(self, embeddings_data: Dict[str, Any], collection_name: str) -> bool:
        """Ingest from validated_embeddings format directly to Weaviate."""
        try:
            collection = self._cached_weaviate_manager.get_collection(collection_name)
            if collection is None:
                self.logger.error(f"Failed to get/create collection: {collection_name}")
                return False
            
            validated_embeddings = embeddings_data.get("validated_embeddings", [])
            self.logger.info(f"Processing {len(validated_embeddings)} validated embeddings")
            
            # Convert to Weaviate objects
            weaviate_objects = []
            for embedding in validated_embeddings:
                chunk_metadata = embedding.get("chunk_metadata", {})
                
                obj = {
                    "id": embedding.get("chunk_id"),
                    "properties": {
                        "content": embedding.get("chunk_content", ""),
                        "document_id": embedding.get("document_id"),
                        "chunk_id": embedding.get("chunk_id"),
                        "chunk_index": chunk_metadata.get("chunk_index", 0),
                        "page_number": chunk_metadata.get("page_number", 1),
                        "word_count": chunk_metadata.get("word_count", 0),
                        "chunk_length": chunk_metadata.get("chunk_length", 0),
                        "source_file_path": chunk_metadata.get("source_file_path", ""),
                        "original_filename": chunk_metadata.get("original_filename", ""),
                        "document_type": chunk_metadata.get("document_type", "other"),
                        "chunking_strategy": chunk_metadata.get("chunking_strategy", ""),
                        "embedding_model": embedding.get("embedding_model"),
                        "created_at": chunk_metadata.get("created_at"),
                        "timestamp": chunk_metadata.get("timestamp")
                    },
                    "vector": embedding.get("embedding_vector", [])
                }
                weaviate_objects.append(obj)
            
            # Batch insert into Weaviate
            with collection.batch.fixed_size(batch_size=100) as batch:
                for obj in weaviate_objects:
                    batch.add_object(
                        properties=obj["properties"],
                        vector=obj["vector"],
                    )
                    if batch.number_errors > 10:
                        self.logger.error("Batch import stopped due to excessive errors")
                        return False
            
            failed_objects = collection.batch.failed_objects
            if failed_objects:
                self.logger.warning(f"Number of failed imports: {len(failed_objects)}")
                return len(failed_objects) < len(weaviate_objects) * 0.1  # Allow up to 10% failures
            
            self.logger.info(f"Successfully stored {len(weaviate_objects)} objects in Weaviate")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to ingest validated embeddings: {e}")
            return False
    
    def _load_latest_chunks(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load latest chunks file for document."""
        try:
            pattern = f"{document_id}_chunks_*.json"
            chunk_files = list(self.chunks_dir.glob(pattern))
            if not chunk_files:
                return None
            
            # Get most recent file
            latest_file = max(chunk_files, key=lambda f: f.stat().st_mtime)
            return self._load_json_file(str(latest_file))
            
        except Exception as e:
            self.logger.error(f"Failed to load chunks for {document_id}: {e}")
            return None
    
    def _load_latest_embeddings(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load latest embeddings file for document."""
        try:
            pattern = f"{document_id}_embeddings_*.json"
            embedding_files = list(self.embeddings_dir.glob(pattern))
            if not embedding_files:
                return None
            
            # Get most recent file
            latest_file = max(embedding_files, key=lambda f: f.stat().st_mtime)
            return self._load_json_file(str(latest_file))
            
        except Exception as e:
            self.logger.error(f"Failed to load embeddings for {document_id}: {e}")
            return None
    
    def _validate_data_consistency(self, chunks_data: Dict[str, Any], embeddings_data: Dict[str, Any]) -> bool:
        """Validate consistency between chunks and embeddings data."""
        try:
            chunks = chunks_data.get("chunks", [])
            embeddings = embeddings_data.get("embeddings", [])
            
            if len(chunks) != len(embeddings):
                self.logger.error(f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data consistency validation failed: {e}")
            return False
    
    def _prepare_chromadb_format(self, chunks_data: Dict[str, Any], embeddings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data in ChromaDB format."""
        chunks = chunks_data.get("chunks", [])
        embeddings = embeddings_data.get("embeddings", [])
        
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"chunk_index": i, "source": chunks_data.get("source", "unknown")} for i in range(len(chunks))]
        documents = [chunk.get("text", "") for chunk in chunks]
        
        return {
            "ids": ids,
            "embeddings": embeddings,
            "metadatas": metadatas,
            "documents": documents
        }


# Global instance for easy import and sharing  
weaviate_ingestion_engine = WeaviateIngestionEngine()