"""
Weaviate connection manager with collection lifecycle management.
Drop-in replacement for ChromaManager with identical interface.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import weaviate
from weaviate.classes.config import Configure, Property, DataType

WEAVIATE_AVAILABLE = True


class WeaviateManager:
    """
    Weaviate connection and configuration manager.
    Drop-in replacement for ChromaManager with identical interface.
    """
    
    def __init__(self, persist_directory: str = None, collection_name: str = "rag_documents"):
        """
        Initialize Weaviate manager with connection settings.
        
        Args:
            persist_directory: Directory for data persistence (unused but kept for compatibility)
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
        self._cached_collections: Dict[str, Any] = {}
        
        # Initialize if Weaviate is available
        if WEAVIATE_AVAILABLE:
            self._initialize_weaviate()
        else:
            self.logger.error("Weaviate not available. Install with: uv pip install weaviate-client")
            
    def _get_default_persist_dir(self) -> str:
        """Get default persistence directory in project data folder."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        data_dir = project_root / "data" / "weaviate_db"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)
    
    def _initialize_weaviate(self) -> None:
        """Initialize Weaviate client connection."""
        try:
            self.logger.info(f"Initializing Weaviate connection at localhost:8080")
            
            # Connect to local Weaviate instance
            self._cached_client = weaviate.connect_to_local()
            
            # Test connection
            if self._cached_client.is_ready():
                self.logger.info("Weaviate initialized successfully")
            else:
                self.logger.error("Weaviate is not ready")
                self._cached_client = None
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Weaviate: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self._cached_client = None
    
    def get_client(self) -> Optional[weaviate.WeaviateClient]:
        """Get cached Weaviate client."""
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available")
            return None
            
        if self._cached_client is None:
            self._initialize_weaviate()
            
        return self._cached_client
    
    def get_collection(self, collection_name: str = "rag_documents") -> Optional[Any]:
        """
        Get or create collection with caching for performance.
        
        Args:
            collection_name: Name of collection to get/create
            
        Returns:
            Collection object or None if unavailable
        """
        print("inside get_collection")
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available - missing dependency")
            return None
            
        if self._cached_client is None:
            self.logger.error("Weaviate client is None - initialization failed")
            return None
            
        name = collection_name
        self.logger.debug(f"Getting collection: {name}")
        
        # Return cached collection if available
        if name in self._cached_collections:
            self.logger.debug(f"Using cached collection: {name}")
            return self._cached_collections[name]
        
        try:
            # Try to get existing collection
            self.logger.debug(f"Attempting to get existing collection: {name}")
            collection = self._cached_client.collections.get(name)
            self.logger.info(f"Retrieved existing collection: {name}")
            
        except Exception as get_error:
            self.logger.debug(f"Collection '{name}' not found, creating new one. Error: {get_error}")
            # Create new collection if it doesn't exist
            try:
                self.logger.info(f"Creating new collection: {name}")
                
                # Create collection with BYOV configuration
                collection = self._cached_client.collections.create(
                    name=name,
                    vector_config=[
                        Configure.Vectors.self_provided(),  # Use self-provided vectors
                    ],
                    properties=[
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="document_id", data_type=DataType.TEXT),
                        Property(name="chunk_id", data_type=DataType.TEXT), 
                        Property(name="chunk_index", data_type=DataType.INT),
                        Property(name="page_number", data_type=DataType.INT),
                        Property(name="source_file", data_type=DataType.TEXT),
                        Property(name="original_filename", data_type=DataType.TEXT),
                        Property(name="document_type", data_type=DataType.TEXT),
                        Property(name="chunk_length", data_type=DataType.INT),
                        Property(name="word_count", data_type=DataType.INT),
                        Property(name="chunk_position", data_type=DataType.TEXT),
                        Property(name="chunking_strategy", data_type=DataType.TEXT),
                        Property(name="embedding_model", data_type=DataType.TEXT),
                        Property(name="chunk_created_at", data_type=DataType.DATE),
                        Property(name="ingested_at", data_type=DataType.DATE),
                    ]
                )
                self.logger.info(f"Created new collection: {name}")
                
            except Exception as create_error:
                self.logger.error(f"Failed to create collection {name}")
                self.logger.error(f"Create error type: {type(create_error).__name__}")
                self.logger.error(f"Create error message: {create_error}")
                import traceback
                self.logger.error(f"Create error traceback: {traceback.format_exc()}")
                return None
        
        # Cache the collection for future use
        self._cached_collections[name] = collection
        self.logger.debug(f"Cached collection: {name}")
        return collection
    
    def list_collections(self) -> List[str]:
        """List all available collections."""
        if not WEAVIATE_AVAILABLE or self._cached_client is None:
            return []
            
        try:
            collections = self._cached_client.collections.list_all()
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
        if not WEAVIATE_AVAILABLE or self._cached_client is None:
            return False
            
        try:
            self._cached_client.collections.delete(collection_name)
            
            # Remove from cache
            if collection_name in self._cached_collections:
                del self._cached_collections[collection_name]
                
            self.logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
    
    def get_collection_info(self, collection_name: str = "rag_documents") -> Optional[Dict[str, Any]]:
        """
        Get collection information including document count and metadata.
        
        Args:
            collection_name: Name of collection to inspect
            
        Returns:
            Dict with collection info or None if unavailable
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            return None
            
        try:
            # Try to get count using aggregate query
            response = collection.aggregate.over_all(total_count=True)
            count = response.total_count if hasattr(response, 'total_count') else 0
            
            return {
                "name": collection_name,
                "count": count,
                "metadata": {"created_at": datetime.now().isoformat()},
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            self.logger.warning(f"Could not get exact count for collection {collection_name}, using default: {e}")
            # Return collection info with count 0 if aggregate fails
            return {
                "name": collection_name,
                "count": 0,  # Default to 0 if we can't get the actual count
                "metadata": {"created_at": datetime.now().isoformat()},
                "persist_directory": self.persist_directory
            }
    
    def reset_database(self) -> bool:
        """
        Reset entire Weaviate database. Use with caution.
        
        Returns:
            bool: True if reset successfully
        """
        if not WEAVIATE_AVAILABLE or self._cached_client is None:
            return False
            
        try:
            # Delete all collections
            collections = self._cached_client.collections.list_all()
            for collection in collections:
                self._cached_client.collections.delete(collection.name)
            
            self._cached_collections.clear()
            self.logger.warning("Weaviate database reset completed")
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
weaviate_manager = WeaviateManager()

if __name__ == "__main__":
    # Simple test
    manager = WeaviateManager()
    client = manager.get_client()
    if client:
        print("Weaviate client initialized.")
        collection = manager.get_collection('rag_documents')
        if collection:
            print(f"Collection retrieved: {collection.name}")
            collections = manager.list_collections()
            print(f"Available collections: {collections}")
        client.close()
    else:
        print("Failed to initialize Weaviate client.")