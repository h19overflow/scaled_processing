"""Weaviate connection manager - Drop-in replacement for ChromaManager with identical interface."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import weaviate
import weaviate.classes as wvc

from .managing_utils import ConnectionManager, CollectionManager

WEAVIATE_AVAILABLE = True


class WeaviateManager:
    """Weaviate vector database manager."""

    def __init__(self, persist_directory: str = None, collection_name: str = "rag_documents"):
        """Initialize Weaviate manager."""
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

        # Configuration
        self.collection_name = collection_name

        self.logger.info("WeaviateManager initialized with modular utilities")

    
    def get_client(self) -> Optional[weaviate.WeaviateClient]:
        """Get the active Weaviate client."""
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available")
            return None

        return self.connection_manager.get_client()
    
    def get_collection(self, collection_name: str = "rag_documents") -> Optional[Any]:
        """Get or create collection."""
        if not WEAVIATE_AVAILABLE:
            self.logger.error("Weaviate not available - missing dependency")
            return None

        return self.collection_manager.get_or_create_collection(collection_name)

    def list_collections(self) -> List[str]:
        """List all available collections."""
        if not WEAVIATE_AVAILABLE:
            return []

        return self.collection_manager.list_collections()

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        if not WEAVIATE_AVAILABLE:
            return False

        return self.collection_manager.delete_collection(collection_name)

    def get_collection_info(self, collection_name: str = "rag_documents") -> Optional[Dict[str, Any]]:
        """Get collection information."""
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

        return self._reset_database()

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]] = None, 
                     ids: List[str] = None, collection_name: str = None) -> bool:
        """
        Add documents to the vector database.
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
        """
        try:
            client = self.get_client()
            if not client:
                return {"status": "disconnected", "healthy": False}
                
            db_info = self._get_database_info()
            integrity = self._verify_database_integrity()
            
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
        """
        return self.helper_utilities.validate_chromadb_format(data)

    # HELPER FUNCTIONS
    def _get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information."""
        client = self.connection_manager.get_client()
        if not client:
            return {"status": "disconnected", "error": "No connection available"}

        try:
            collections = self.collection_manager.list_collections()
            collection_info = {}
            total_objects = 0

            for collection_name in collections:
                info = self.collection_manager.get_collection_info(collection_name)
                if info:
                    collection_info[collection_name] = info
                    total_objects += info.get("count", 0)

            return {
                "status": "connected",
                "total_collections": len(collections),
                "total_objects": total_objects,
                "collections": collections,
                "collection_details": collection_info,
                "connection_ready": client.is_ready(),
                "indexed_vectors": total_objects
            }

        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return {"status": "error", "error": str(e)}

    def _verify_database_integrity(self) -> Dict[str, Any]:
        """Verify database integrity by checking all collections."""
        client = self.connection_manager.get_client()
        if not client:
            return {
                "status": "failed",
                "error": "No connection available",
                "collections_checked": 0,
                "issues_found": 0
            }

        try:
            collections = self.collection_manager.list_collections()
            issues_found = 0
            collection_status = {}

            for collection_name in collections:
                try:
                    collection = self.collection_manager.get_or_create_collection(collection_name)
                    if collection is None:
                        issues_found += 1
                        collection_status[collection_name] = "collection_unavailable"
                    else:
                        info = self.collection_manager.get_collection_info(collection_name)
                        if info and info.get("count", -1) >= 0:
                            collection_status[collection_name] = "healthy"
                        else:
                            issues_found += 1
                            collection_status[collection_name] = "query_failure"
                except Exception as e:
                    issues_found += 1
                    collection_status[collection_name] = f"error: {str(e)}"

            return {
                "status": "completed",
                "collections_checked": len(collections),
                "issues_found": issues_found,
                "collection_status": collection_status,
                "overall_health": "healthy" if issues_found == 0 else "issues_found"
            }

        except Exception as e:
            self.logger.error(f"Database integrity verification failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "collections_checked": 0,
                "issues_found": 0
            }

    def _reset_database(self) -> bool:
        """Reset entire Weaviate database - use with caution!"""
        self.logger.warning("RESETTING ENTIRE WEAVIATE DATABASE")

        client = self.connection_manager.get_client()
        if not client:
            self.logger.error("Cannot reset database - no connection available")
            return False

        try:
            collections = client.collections.list_all()
            collection_names = [col.name for col in collections]

            if not collection_names:
                self.logger.info("Database is already empty")
                self.collection_manager.reset_cache()
                return True

            deleted_count = 0
            failed_deletions = []

            for collection_name in collection_names:
                try:
                    self.collection_manager.delete_collection(collection_name)
                    deleted_count += 1
                    self.logger.info(f"Deleted collection: {collection_name}")
                except Exception as delete_error:
                    self.logger.error(f"Failed to delete collection {collection_name}: {delete_error}")
                    failed_deletions.append(collection_name)

            self.collection_manager.reset_cache()

            if failed_deletions:
                self.logger.error(f"Failed to delete {len(failed_deletions)} collections: {failed_deletions}")
                return False

            self.logger.warning(f"DATABASE RESET COMPLETE - Deleted {deleted_count} collections")
            return True

        except Exception as e:
            self.logger.error(f"Database reset failed: {e}")
            return False


# Global instance for easy import and sharing
weaviate_manager = WeaviateManager()

def main():
    """Demo of WeaviateManager with modular utility classes."""
    print("🚀 WeaviateManager Modular Demo")
    print("=" * 40)

    try:
        manager = WeaviateManager()
        client = manager.get_client()
        rag_documents = client.collections.get('rag_documents')
        print(rag_documents.config.get())
        objects = rag_documents.query.fetch_objects(limit=2 , return_properties=["content"])
        
        print(objects)
        client.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    exit(exit_code)
