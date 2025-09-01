"""
ChromaDB connection manager with collection lifecycle management.
Handles vector database operations with configuration and caching for performance.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import chromadb
    from chromadb.api.models.Collection import Collection
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    Collection = None


class ChromaManager:
    """
    ChromaDB connection and configuration manager.
    Provides cached connections and collection management for vector operations.
    """
    
    def __init__(self, persist_directory: str = None, collection_name: str = "rag_documents"):
        """
        Initialize ChromaDB manager with persistent storage.
        
        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Default collection name for documents
        """
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Configuration
        self.collection_name = collection_name
        self.persist_directory = persist_directory or self._get_default_persist_dir()
        
        # Cached components - created once for performance
        self._cached_client = None
        self._cached_collections: Dict[str, Collection] = {}
        
        # Initialize if ChromaDB is available
        if CHROMADB_AVAILABLE:
            self._initialize_chroma()
        else:
            self.logger.error("ChromaDB not available. Install with: pip install chromadb")
            
    def _get_default_persist_dir(self) -> str:
        """Get default persistence directory in project data folder."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        data_dir = project_root / "data" / "chroma_db"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)
    
    def _initialize_chroma(self) -> None:
        """Initialize ChromaDB client with persistence."""
        try:
            # Ensure persist directory exists
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            
            # Create client with persistent storage
            self._cached_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self.logger.info(f"ChromaDB initialized with persistence: {self.persist_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            self._cached_client = None
    
    def get_client(self) -> Optional[chromadb.PersistentClient]:
        """Get cached ChromaDB client."""
        if not CHROMADB_AVAILABLE:
            self.logger.error("ChromaDB not available")
            return None
            
        if self._cached_client is None:
            self._initialize_chroma()
            
        return self._cached_client
    
    def get_collection(self, collection_name: str = None) -> Optional[Collection]:
        """
        Get or create collection with caching for performance.
        
        Args:
            collection_name: Name of collection to get/create
            
        Returns:
            Collection object or None if unavailable
        """
        if not CHROMADB_AVAILABLE or self._cached_client is None:
            return None
            
        name = collection_name or self.collection_name
        
        # Return cached collection if available
        if name in self._cached_collections:
            return self._cached_collections[name]
        
        try:
            # Try to get existing collection
            collection = self._cached_client.get_collection(name=name)
            self.logger.info(f"Retrieved existing collection: {name}")
            
        except Exception:
            # Create new collection if it doesn't exist
            try:
                collection = self._cached_client.create_collection(
                    name=name,
                    metadata={"created_at": datetime.now().isoformat()}
                )
                self.logger.info(f"Created new collection: {name}")
                
            except Exception as e:
                self.logger.error(f"Failed to create collection {name}: {e}")
                return None
        
        # Cache the collection for future use
        self._cached_collections[name] = collection
        return collection
    
    def list_collections(self) -> List[str]:
        """List all available collections."""
        if not CHROMADB_AVAILABLE or self._cached_client is None:
            return []
            
        try:
            collections = self._cached_client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection and remove from cache.
        
        Args:
            collection_name: Name of collection to delete
            
        Returns:
            bool: True if deleted successfully
        """
        if not CHROMADB_AVAILABLE or self._cached_client is None:
            return False
            
        try:
            self._cached_client.delete_collection(name=collection_name)
            
            # Remove from cache
            if collection_name in self._cached_collections:
                del self._cached_collections[collection_name]
                
            self.logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
    
    def get_collection_info(self, collection_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Get collection information including document count and metadata.
        
        Args:
            collection_name: Name of collection to inspect
            
        Returns:
            Dict with collection info or None if unavailable
        """
        collection = self.get_collection(collection_name)
        if not collection:
            return None
            
        try:
            count = collection.count()
            metadata = collection.metadata or {}
            
            return {
                "name": collection.name,
                "count": count,
                "metadata": metadata,
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection info: {e}")
            return None
    
    def reset_database(self) -> bool:
        """
        Reset entire ChromaDB database. Use with caution.
        
        Returns:
            bool: True if reset successfully
        """
        if not CHROMADB_AVAILABLE or self._cached_client is None:
            return False
            
        try:
            self._cached_client.reset()
            self._cached_collections.clear()
            self.logger.warning("ChromaDB database reset completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            return False

    # HELPER FUNCTIONS
    def _validate_chromadb_format(self, data: Dict[str, Any]) -> bool:
        """
        Validate ChromaDB-ready format structure.
        
        Args:
            data: Data to validate
            
        Returns:
            bool: True if valid ChromaDB format
        """
        required_keys = ["ids", "embeddings", "metadatas", "documents"]
        
        if not all(key in data for key in required_keys):
            return False
            
        # Check all arrays have same length
        lengths = [len(data[key]) for key in required_keys]
        return len(set(lengths)) == 1  # All lengths are the same


# Global instance for easy import and sharing
chroma_manager = ChromaManager()