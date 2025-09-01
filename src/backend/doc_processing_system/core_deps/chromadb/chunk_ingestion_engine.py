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
            chroma_manager: ChromaDB manager instance (creates new if not provided)
        """
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Use provided chroma manager or create new instance
        if chroma_manager:
            self._cached_chroma_manager = chroma_manager
        else:
            # Create a fresh ChromaManager instance
            from .chroma_manager import ChromaManager
            self._cached_chroma_manager = ChromaManager()
            self.logger.info("Created new ChromaManager instance")
        
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
            self.logger.info(f"🚀 Starting ingestion from ChromaDB-ready file: {embeddings_file_path}")
            self.logger.info(f"🗄️ Target collection: {collection_name or 'default'}")
            
            # Load JSON file
            self.logger.info(f"📁 Loading embeddings file...")
            embeddings_data = self._load_json_file(embeddings_file_path)
            if not embeddings_data:
                self.logger.error(f"❌ Failed to load embeddings file: {embeddings_file_path}")
                return False
            
            self.logger.info(f"✅ Loaded embeddings file successfully")
            self.logger.debug(f"🔍 File keys: {list(embeddings_data.keys())}")
            
            # Extract ChromaDB-ready format
            self.logger.info("🔍 Extracting chromadb_ready format...")
            chromadb_data = embeddings_data.get("chromadb_ready")
            if not chromadb_data:
                self.logger.error(f"❌ No chromadb_ready format found in: {embeddings_file_path}")
                self.logger.error(f"🔍 Available keys in file: {list(embeddings_data.keys())}")
                return False
            
            self.logger.info("✅ Found chromadb_ready format")
            self.logger.debug(f"🔍 ChromaDB data keys: {list(chromadb_data.keys())}")
            
            # Validate format
            self.logger.info("🔍 Validating ChromaDB format...")
            if not self._validate_chromadb_format(chromadb_data):
                self.logger.error(f"❌ Invalid ChromaDB format in: {embeddings_file_path}")
                return False
            
            self.logger.info("✅ ChromaDB format validation passed")
            
            # Store in ChromaDB
            self.logger.info("🚀 Proceeding to store in ChromaDB...")
            result = self._store_in_chromadb(chromadb_data, collection_name)
            
            if result:
                self.logger.info(f"✅ Successfully ingested from ChromaDB-ready file")
            else:
                self.logger.error(f"❌ Failed to store data in ChromaDB")
                
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Failed to ingest from ChromaDB-ready file: {embeddings_file_path}")
            self.logger.error(f"🔍 Error type: {type(e).__name__}")
            self.logger.error(f"🔍 Error message: {e}")
            import traceback
            self.logger.error(f"📋 Full traceback: {traceback.format_exc()}")
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
                
                # Combine metadata from chunk and embedding with enhanced filtering fields
                base_metadata = {
                    **chunk.get("metadata", {}),
                    **emb_data.get("chunk_metadata", {}),
                }
                
                # Create enhanced metadata for ChromaDB filtering
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
            
            self.logger.info(f"📦 Prepared ChromaDB format: {len(ids)} items")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to prepare ChromaDB format: {e}")
            return {}
    
    def _store_in_chromadb(self, chromadb_data: Dict[str, List], collection_name: str = None) -> bool:
        """Store data in ChromaDB collection."""
        try:
            self.logger.info(f"🚀 Starting ChromaDB storage process")
            
            # Validate ChromaManager is available
            if not self._cached_chroma_manager:
                self.logger.error("❌ ChromaDB manager not available")
                return False
            
            self.logger.info(f"🔗 Getting ChromaDB collection: {collection_name or 'default'}")
            collection = self._cached_chroma_manager.get_collection(collection_name)
            if not collection:
                self.logger.error(f"❌ Failed to get ChromaDB collection: {collection_name or 'default'}")
                return False
            
            self.logger.info(f"✅ Successfully retrieved collection: {collection.name}")
            
            # Validate format before storing
            self.logger.info("🔍 Validating ChromaDB format...")
            if not self._validate_chromadb_format(chromadb_data):
                self.logger.error("❌ Invalid ChromaDB format")
                return False
            
            self.logger.info("✅ ChromaDB format validation passed")
            
            # Log detailed data stats before storing
            ids_count = len(chromadb_data['ids'])
            embeddings_count = len(chromadb_data['embeddings'])
            metadatas_count = len(chromadb_data['metadatas'])
            documents_count = len(chromadb_data['documents'])
            
            self.logger.info(f"📊 Data counts - IDs: {ids_count}, Embeddings: {embeddings_count}, Metadata: {metadatas_count}, Documents: {documents_count}")
            
            # Sample first few IDs for debugging
            sample_ids = chromadb_data['ids'][:3] if chromadb_data['ids'] else []
            self.logger.debug(f"🔍 Sample IDs: {sample_ids}")
            
            # Check embedding dimensions
            if chromadb_data['embeddings']:
                first_embedding_dim = len(chromadb_data['embeddings'][0]) if chromadb_data['embeddings'][0] else 0
                self.logger.info(f"📐 Embedding dimension: {first_embedding_dim}")
            
            # Store in ChromaDB
            self.logger.info(f"📝 Adding {ids_count} items to ChromaDB collection: {collection.name}")
            self.logger.debug("🔄 Calling collection.add()...")
            self.logger.debug(f"🔍 Data preview - IDs: {chromadb_data['ids'][:2]}, Embeddings: {chromadb_data['embeddings'][:1]}, Metadatas: {chromadb_data['metadatas'][:1]}, Documents: {chromadb_data['documents'][:1]}"
                            )
            self.logger.info('Collection information before add: ' + str(collection.count))
            collection.add(
                ids=chromadb_data["ids"],
                embeddings=chromadb_data["embeddings"],
                metadatas=chromadb_data["metadatas"],
                documents=chromadb_data["documents"]
            )
            
            self.logger.info(f"✅ Successfully added {ids_count} items to ChromaDB collection")
            
            # Verify storage by checking collection count
            try:
                total_count = collection.count()
                self.logger.info(f"📊 Total items in collection after storage: {total_count}")
            except Exception as count_error:
                self.logger.warning(f"⚠️ Could not verify collection count: {count_error}")
            
            self.logger.info(f"✅ ChromaDB storage completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ChromaDB storage failed")
            self.logger.error(f"🔍 Error type: {type(e).__name__}")
            self.logger.error(f"🔍 Error message: {e}")
            
            # Log additional context for debugging
            if chromadb_data:
                self.logger.error(f"🔍 Data keys available: {list(chromadb_data.keys())}")
                for key in ['ids', 'embeddings', 'metadatas', 'documents']:
                    if key in chromadb_data:
                        self.logger.error(f"🔍 {key} length: {len(chromadb_data[key])}")
                        
            import traceback
            self.logger.error(f"📋 Full traceback: {traceback.format_exc()}")
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
# Initialize lazily to avoid circular import issues
chunk_ingestion_engine = None

def get_chunk_ingestion_engine():
    """Get or create global chunk ingestion engine instance."""
    global chunk_ingestion_engine
    if chunk_ingestion_engine is None:
        chunk_ingestion_engine = ChunkIngestionEngine()
    return chunk_ingestion_engine