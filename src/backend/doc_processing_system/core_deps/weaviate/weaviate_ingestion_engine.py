"""
Weaviate ingestion engine for vector storage.
Drop-in replacement for ChunkIngestionEngine with identical interface.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .weaviate_manager import WeaviateManager


class WeaviateIngestionEngine:
    """
    Engine for ingesting processed chunks and embeddings into Weaviate.
    Drop-in replacement for ChunkIngestionEngine with identical interface.
    """
    
    def __init__(self, weaviate_manager: WeaviateManager = None):
        """
        Initialize Weaviate ingestion engine.
        
        Args:
            weaviate_manager: Weaviate manager instance (creates new if not provided)
        """
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        # Use provided manager or create new one
        self.weaviate_manager = weaviate_manager or WeaviateManager()
        
        # Data paths (kept for compatibility)
        self.chunks_dir = Path("data/rag/chunks")
        self.embeddings_dir = Path("data/rag/embeddings")
        
        self.logger.info("WeaviateIngestionEngine initialized with Weaviate integration")
    
    def ingest_document(self, document_id: str, collection_name: str = "rag_documents") -> bool:
        """
        Ingest a complete document's chunks and embeddings into Weaviate.
        
        Args:
            document_id: Document identifier to ingest
            collection_name: Weaviate collection name (defaults to "rag_documents")
            
        Returns:
            bool: True if ingestion successful
        """
        self.logger.info(f"Starting document ingestion: {document_id}")
        
        try:
            # Find latest chunk and embedding files
            chunks_data = self._load_latest_chunks(document_id)
            embeddings_data = self._load_latest_embeddings(document_id)
            
            if not chunks_data or not embeddings_data:
                self.logger.error(f"Missing data files for document: {document_id}")
                return False
            
            # Validate data consistency
            if not self._validate_data_consistency(chunks_data, embeddings_data):
                self.logger.error(f"Data consistency validation failed: {document_id}")
                return False
            
            # Prepare ChromaDB format first, then convert to Weaviate
            chromadb_data = self._prepare_chromadb_format(chunks_data, embeddings_data)
            
            # Store in Weaviate
            success = self._store_in_weaviate(chromadb_data, collection_name)
            
            if success:
                self.logger.info(f"Document ingestion completed: {document_id}")
                self.logger.info(f"Stored {len(chromadb_data['ids'])} chunks in Weaviate")
            else:
                self.logger.error(f"Weaviate storage failed: {document_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Document ingestion failed for {document_id}: {e}")
            return False
    
    def ingest_from_chromadb_ready_file(self, embeddings_file_path: str, collection_name: str = "rag_documents") -> bool:
        """
        Ingest directly from embeddings file with ChromaDB-ready format.
        Renamed to ingest_from_embeddings_file for database-agnostic naming.
        
        Args:
            embeddings_file_path: Path to embeddings JSON file
            collection_name: Weaviate collection name (defaults to "rag_documents")
            
        Returns:
            bool: True if ingestion successful
        """
        return self.ingest_from_embeddings_file(embeddings_file_path, collection_name)
    
    def ingest_from_embeddings_file(self, embeddings_file_path: str, collection_name: str = "rag_documents") -> bool:
        """
        Ingest directly from embeddings file with ChromaDB-ready format.
        
        Args:
            embeddings_file_path: Path to embeddings JSON file
            collection_name: Weaviate collection name (defaults to "rag_documents")
            
        Returns:
            bool: True if ingestion successful
        """
        try:
            self.logger.info(f"Starting ingestion from embeddings file: {embeddings_file_path}")
            self.logger.info(f"Target collection: {collection_name or 'default'}")
            
            # Load JSON file
            self.logger.info(f"Loading embeddings file...")
            embeddings_data = self._load_json_file(embeddings_file_path)
            if not embeddings_data:
                self.logger.error(f"Failed to load embeddings file: {embeddings_file_path}")
                return False
            
            self.logger.info(f"Loaded embeddings file successfully")
            self.logger.debug(f"File keys: {list(embeddings_data.keys())}")
            
            # Extract ChromaDB-ready format
            self.logger.info("Extracting chromadb_ready format...")
            chromadb_data = embeddings_data.get("chromadb_ready")
            if not chromadb_data:
                self.logger.error(f"No chromadb_ready format found in: {embeddings_file_path}")
                self.logger.error(f"Available keys in file: {list(embeddings_data.keys())}")
                return False
            
            self.logger.info("Found chromadb_ready format")
            self.logger.debug(f"ChromaDB data keys: {list(chromadb_data.keys())}")
            
            # Validate format
            self.logger.info("Validating ChromaDB format...")
            if not self._validate_chromadb_format(chromadb_data):
                self.logger.error(f"Invalid ChromaDB format in: {embeddings_file_path}")
                return False
            
            self.logger.info("ChromaDB format validation passed")
            
            # Store in Weaviate
            self.logger.info("Proceeding to store in Weaviate...")
            result = self._store_in_weaviate(chromadb_data, collection_name)
            
            if result:
                self.logger.info(f"Successfully ingested from embeddings file")
            else:
                self.logger.error(f"Failed to store data in Weaviate")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to ingest from embeddings file: {embeddings_file_path}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.error(f"Error message: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
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
            self.logger.info(f"Loading: {latest_file.name}")
            
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
            
            self.logger.info(f"Data consistency validated: {chunk_count} chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Data consistency validation failed: {e}")
            return False
    
    def _prepare_chromadb_format(self, chunks_data: Dict, embeddings_data: Dict) -> Dict[str, List]:
        """Prepare data in ChromaDB format (same as original implementation)."""
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
                
                # Combine metadata from chunk and embedding with enhanced filtering fields
                base_metadata = {
                    **chunk.get("metadata", {}),
                    **emb_data.get("chunk_metadata", {}),
                }
                
                # Create enhanced metadata for filtering
                metadata = {
                    **base_metadata,
                    # Core identifiers
                    "document_id": chunk["document_id"],
                    "chunk_id": chunk_id,
                    "chunk_index": chunk["chunk_index"],
                    "page_number": chunk["page_number"],
                    
                    # Source information for filtering
                    "source_file": base_metadata.get("source_file_path", "unknown"),
                    "original_filename": base_metadata.get("original_filename", chunk["document_id"]),
                    "document_type": base_metadata.get("document_type", "unknown"),
                    
                    # Content characteristics for filtering
                    "chunk_length": len(chunk["content"]),
                    "word_count": len(chunk["content"].split()),
                    "chunk_position": base_metadata.get("chunk_position", "unknown"),
                    
                    # Processing metadata
                    "chunking_strategy": base_metadata.get("chunking_strategy", "unknown"),
                    "embedding_model": emb_data.get("embedding_model", "unknown"),
                    
                    # Timestamps
                    "chunk_created_at": base_metadata.get("created_at", datetime.now().isoformat()),
                    "ingested_at": datetime.now().isoformat()
                }
                metadatas.append(metadata)
            
            result = {
                "ids": ids,
                "embeddings": embeddings,
                "metadatas": metadatas,
                "documents": documents
            }
            
            self.logger.info(f"Prepared ChromaDB format: {len(ids)} items")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to prepare ChromaDB format: {e}")
            return {}
    
    def _convert_chromadb_to_weaviate_format(self, chromadb_data: Dict[str, List]) -> List[Dict[str, Any]]:
        """
        Convert ChromaDB format to Weaviate format.
        
        Args:
            chromadb_data: Data in ChromaDB format
            
        Returns:
            List of objects ready for Weaviate insertion
        """
        weaviate_objects = []
        
        try:
            ids = chromadb_data["ids"]
            embeddings = chromadb_data["embeddings"]
            metadatas = chromadb_data["metadatas"]
            documents = chromadb_data["documents"]
            
            for i, chunk_id in enumerate(ids):
                # Convert metadata to Weaviate properties format
                metadata = metadatas[i]
                
                # Create Weaviate object
                weaviate_object = {
                    "properties": {
                        "content": documents[i],
                        "document_id": metadata.get("document_id", "unknown"),
                        "chunk_id": chunk_id,
                        "chunk_index": metadata.get("chunk_index", 0),
                        "page_number": metadata.get("page_number", 0),
                        "source_file": metadata.get("source_file", "unknown"),
                        "original_filename": metadata.get("original_filename", "unknown"),
                        "document_type": metadata.get("document_type", "unknown"),
                        "chunk_length": metadata.get("chunk_length", 0),
                        "word_count": metadata.get("word_count", 0),
                        "chunk_position": metadata.get("chunk_position", "unknown"),
                        "chunking_strategy": metadata.get("chunking_strategy", "unknown"),
                        "embedding_model": metadata.get("embedding_model", "unknown"),
                        "chunk_created_at": metadata.get("chunk_created_at", datetime.now().isoformat()),
                        "ingested_at": metadata.get("ingested_at", datetime.now().isoformat()),
                    },
                    "vector": embeddings[i]  # Vector goes at top level for BYOV
                }
                
                weaviate_objects.append(weaviate_object)
            
            self.logger.info(f"Converted {len(weaviate_objects)} objects to Weaviate format")
            return weaviate_objects
            
        except Exception as e:
            self.logger.error(f"Failed to convert ChromaDB to Weaviate format: {e}")
            return []
    
    def _store_in_weaviate(self, chromadb_data: Dict[str, List], collection_name: str = "rag_documents") -> bool:
        """Store data in Weaviate collection."""
        try:
            self.logger.info(f"Starting Weaviate storage process")
            self.logger.info(f"Getting Weaviate collection: {collection_name or 'default'}")
            
            # Get collection
            collection = self.weaviate_manager.get_collection(collection_name)
            if collection is None:
                self.logger.error(f"Failed to get Weaviate collection: {collection_name or 'default'}")
                return False
            
            self.logger.info(f"Successfully retrieved collection: {collection.name}")
            
            # Validate ChromaDB format
            self.logger.info("Validating ChromaDB format...")
            if not self._validate_chromadb_format(chromadb_data):
                self.logger.error("Invalid ChromaDB format")
                return False
            
            self.logger.info("ChromaDB format validation passed")
            
            # Convert to Weaviate format
            self.logger.info("Converting ChromaDB format to Weaviate format...")
            weaviate_objects = self._convert_chromadb_to_weaviate_format(chromadb_data)
            if not weaviate_objects:
                self.logger.error("Failed to convert data to Weaviate format")
                return False
            
            # Log data stats
            objects_count = len(weaviate_objects)
            self.logger.info(f"Data counts - Objects: {objects_count}")
            
            # Store in Weaviate using batch insert
            self.logger.info(f"Adding {objects_count} objects to Weaviate collection: {collection.name}")
            
            import time
            start_time = time.time()
            
            try:
                # Use batch context manager for efficient insertion
                with collection.batch.fixed_size(batch_size=100) as batch:
                    for obj in weaviate_objects:
                        batch.add_object(
                            properties=obj["properties"],
                            vector=obj["vector"]
                        )
                        
                        # Stop if too many errors
                        if batch.number_errors > 10:
                            self.logger.error("Batch import stopped due to excessive errors.")
                            break
                
                elapsed_time = time.time() - start_time
                self.logger.info(f"Batch insertion completed successfully in {elapsed_time:.2f}s!")
                
                # Check for failed objects
                failed_objects = collection.batch.failed_objects
                if failed_objects:
                    self.logger.warning(f"Number of failed imports: {len(failed_objects)}")
                    for i, failed_obj in enumerate(failed_objects[:3]):  # Log first 3 failures
                        self.logger.warning(f"Failed object {i+1}: {failed_obj}")
                
            except Exception as batch_error:
                elapsed_time = time.time() - start_time
                self.logger.error(f"Batch insertion failed after {elapsed_time:.2f}s with error: {batch_error}")
                self.logger.error(f"Error type: {type(batch_error).__name__}")
                import traceback
                self.logger.error(f"Batch traceback: {traceback.format_exc()}")
                return False
            
            self.logger.info(f"Successfully added {objects_count} objects to Weaviate collection")
            
            # Verify storage by checking collection count
            try:
                collection_info = self.weaviate_manager.get_collection_info(collection_name)
                if collection_info:
                    total_count = collection_info["count"]
                    self.logger.info(f"Total items in collection after storage: {total_count}")
            except Exception as count_error:
                self.logger.warning(f"Could not verify collection count: {count_error}")
            
            self.logger.info(f"Weaviate storage completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Weaviate storage failed")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.error(f"Error message: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def get_ingestion_stats(self, collection_name: str = "rag_documents") -> Dict[str, Any]:
        """Get ingestion statistics for a collection."""
        try:
            collection_info = self.weaviate_manager.get_collection_info(collection_name)
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
weaviate_ingestion_engine = None

def get_weaviate_ingestion_engine():
    """Get or create global Weaviate ingestion engine instance."""
    global weaviate_ingestion_engine
    if weaviate_ingestion_engine is None:
        weaviate_ingestion_engine = WeaviateIngestionEngine()
    return weaviate_ingestion_engine

# For drop-in replacement compatibility
def get_chunk_ingestion_engine():
    """Get or create global ingestion engine instance (Weaviate implementation)."""
    return get_weaviate_ingestion_engine()