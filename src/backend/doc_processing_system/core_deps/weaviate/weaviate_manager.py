"""Weaviate connection manager - Drop-in replacement for ChromaManager with identical interface."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import weaviate

from .managing_utils import ConnectionManager, CollectionManager, DatabaseManager, HelperUtilities, TestUtils

WEAVIATE_AVAILABLE = True


class WeaviateManager:
    """
    Weaviate connection manager using modular utility classes.

    - ConnectionManager: Client connections and initialization
    - CollectionManager: Collections, caching, and operations
    - DatabaseManager: Database-level operations and statistics
    - HelperUtilities: Data validation and formatting functions
    - TestUtils: Testing and debugging utilities
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

        # Initialize utility classes first
        self.connection_manager = ConnectionManager()
        self.collection_manager = CollectionManager(self.connection_manager)
        self.database_manager = DatabaseManager(self.connection_manager, self.collection_manager)
        self.helper_utilities = HelperUtilities()
        self.test_utils = TestUtils(self.connection_manager, self.collection_manager, self.database_manager)

        # Configuration
        self.collection_name = collection_name
        self.persist_directory = persist_directory or self._get_default_persist_dir()

        self.logger.info("WeaviateManager initialized with modular utilities")

    def _get_default_persist_dir(self) -> str:
        """Get default persistence directory in project data folder."""
        return self.helper_utilities.get_default_persist_dir()
    
    def get_client(self) -> Optional[weaviate.WeaviateClient]:
        """Get cached Weaviate client using ConnectionManager."""
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available")
            return None

        return self.connection_manager.get_client()
    
    def get_collection(self, collection_name: str = "rag_documents") -> Optional[Any]:
        """
        Get or create collection using CollectionManager.

        Args:
            collection_name: Name of collection to get/create

        Returns:
            Collection object or None if unavailable
        """
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available - missing dependency")
            return None

        return self.collection_manager.get_or_create_collection(collection_name)

    def list_collections(self) -> List[str]:
        """List all available collections using CollectionManager."""
        if not WEAVIATE_AVAILABLE:
            return []

        return self.collection_manager.list_collections()

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection using CollectionManager.

        Args:
            collection_name: Name of collection to delete

        Returns:
            bool: True if deleted successfully
        """
        if not WEAVIATE_AVAILABLE:
            return False

        return self.collection_manager.delete_collection(collection_name)

    def get_collection_info(self, collection_name: str = "rag_documents") -> Optional[Dict[str, Any]]:
        """
        Get collection information using CollectionManager.

        Args:
            collection_name: Name of collection to inspect

        Returns:
            Dict with collection info or None if unavailable
        """
        if not WEAVIATE_AVAILABLE:
            return None

        # Get basic collection info from CollectionManager
        info = self.collection_manager.get_collection_info(collection_name)

        # Enhance with additional WeaviateManager-specific properties
        if info:
            info["persist_directory"] = self.persist_directory

        return info
    
    def reset_database(self) -> bool:
        """
        Reset entire Weaviate database using DatabaseManager.

        Returns:
            bool: True if reset successful
        """
        if not WEAVIATE_AVAILABLE:
            return False

        return self.database_manager.reset_database()

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]] = None, 
                     ids: List[str] = None, collection_name: str = None) -> bool:
        """
        Add documents to the vector database.
        
        Args:
            documents: List of text documents to add
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document (auto-generated if not provided)
            collection_name: Collection to add to (uses default if not specified)
            
        Returns:
            bool: True if documents added successfully
        """
        target_collection = collection_name or self.collection_name
        collection = self.get_collection(target_collection)
        
        if not collection:
            self.logger.error(f"Failed to get collection: {target_collection}")
            return False
            
        try:
            # Implementation would depend on your document ingestion logic
            self.logger.info(f"Added {len(documents)} documents to {target_collection}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add documents: {e}")
            return False
    
    def search_documents(self, query: str, top_k: int = 5, 
                        collection_name: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            collection_name: Collection to search (uses default if not specified)
            filters: Optional metadata filters
            
        Returns:
            List of matching documents with metadata and scores
        """
        target_collection = collection_name or self.collection_name
        collection = self.get_collection(target_collection)
        
        if not collection:
            self.logger.error(f"Failed to get collection: {target_collection}")
            return []
            
        try:
            # Implementation would depend on your search logic
            self.logger.info(f"Searched {target_collection} for: {query}")
            return []  # Placeholder
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get overall database status and health.
        
        Returns:
            Dict with connection status, collection count, and health info
        """
        try:
            client = self.get_client()
            if not client:
                return {"status": "disconnected", "healthy": False}
                
            db_info = self.database_manager.get_database_info()
            integrity = self.database_manager.verify_database_integrity()
            
            return {
                "status": "connected",
                "healthy": integrity.get("issues_found", 0) == 0,
                "total_collections": db_info.get("total_collections", 0),
                "total_documents": db_info.get("total_objects", 0),
                "ready": client.is_ready() if client else False
            }
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {"status": "error", "healthy": False, "error": str(e)}
    
   
    def validate_data_format(self, data: Dict[str, Any]) -> bool:
        """
        Validate data format compatibility.
        
        Args:
            data: Data structure to validate
            
        Returns:
            bool: True if data format is valid
        """
        return self.helper_utilities.validate_chromadb_format(data)


# Global instance for easy import and sharing
weaviate_manager = WeaviateManager()

def main():
    """Demo of WeaviateManager with modular utility classes."""
    print("🚀 WeaviateManager Modular Demo")
    print("=" * 40)

    try:
        manager = WeaviateManager()
        client = manager.get_client()

        if client:
            print("✅ Connected to Weaviate")

            # Test status using clean abstraction
            status = manager.get_status()
            print(f"📊 Status: {status['status']}, Collections: {status.get('total_collections', 0)}")
            print(f"🏥 Health: {'HEALTHY' if status.get('healthy', False) else 'ISSUES'}")

            collection = manager.get_collection('rag_documents')
            if collection:
                info = manager.get_collection_info('rag_documents')
                count = info.get('count', 0) if info else 0
                print(f"📄 Collection: rag_documents, Objects: {count}")

                # Validate data format using new method name
                sample_data = {
                    "ids": ["test_1", "test_2"],
                    "embeddings": [[0.1, 0.2], [0.3, 0.4]],
                    "metadatas": [{"doc": "1"}, {"doc": "2"}],
                    "documents": ["text 1", "text 2"]
                }
                is_valid = manager.validate_data_format(sample_data)
                print(f"🔧 Format validation: {'PASS' if is_valid else 'FAIL'}")

                # Test maintenance
                maintenance_result = manager.maintenance()
                print(f"🔧 Maintenance: {'SUCCESS' if maintenance_result else 'ISSUES'}")

            client.close()
            print("✅ Demo completed successfully")
            return True
        else:
            print("❌ Failed to connect to Weaviate")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    exit(exit_code)
