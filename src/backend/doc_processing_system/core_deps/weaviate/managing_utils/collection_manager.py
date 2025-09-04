"""Weaviate collection management utilities."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import weaviate
from weaviate.classes.config import Configure, Property, DataType


class CollectionManager:
    """Manages Weaviate collections with caching, validation, and error recovery."""

    def __init__(self, connection_manager):
        """
        Initialize collection manager.

        Args:
            connection_manager: ConnectionManager instance
        """
        self.logger = logging.getLogger(__name__)
        self.connection_manager = connection_manager
        self._cached_collections: Dict[str, Any] = {}

    def get_or_create_collection(self, collection_name: str = "rag_documents") -> Optional[Any]:
        """
        Get existing collection or create new one with caching for performance.

        Args:
            collection_name: Name of collection to get/create

        Returns:
            Collection object or None if unavailable
        """
        # Use client from connection manager
        client = self.connection_manager.get_client()
        if not client:
            self.logger.error("No client available for collection operations")
            return None

        # Return cached collection if available
        if collection_name in self._cached_collections:
            self.logger.debug(f"Using cached collection: {collection_name}")
            return self._cached_collections[collection_name]

        # First, try to get existing collection
        try:
            self.logger.debug(f"Attempting to get existing collection: {collection_name}")
            collection = client.collections.get(collection_name)
            self.logger.info(f"Retrieved existing collection: {collection_name}")

            # Test that the collection can be accessed
            if self._validate_collection(collection, collection_name):
                return collection
            else:
                # Collection exists but is broken - try to recreate it
                return self._create_collection(client, collection_name)

        except Exception as get_error:
            self.logger.debug(f"Collection '{collection_name}' not found, creating new one. Error: {get_error}")
            # Create new collection if it doesn't exist
            return self._create_collection(client, collection_name)

    def _create_collection(self, client: weaviate.WeaviateClient, collection_name: str) -> Optional[Any]:
        """
        Create a new collection with proper error handling.

        Args:
            client: Weaviate client instance
            collection_name: Name for the new collection

        Returns:
            Collection object or None if creation failed
        """
        try:
            self.logger.info(f"Creating new collection: {collection_name}")

            # Create collection with BYOV configuration
            collection = client.collections.create(
                collection_name,
                vector_config=Configure.Vectors.self_provided(),
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
            self.logger.info(f"Created new collection: {collection_name}")

            # Validate creation by testing access
            if self._validate_collection(collection, collection_name):
                # Cache the collection for future use
                self._cached_collections[collection_name] = collection
                self.logger.debug(f"Cached collection: {collection_name}")
                return collection
            else:
                # Clean up failed collection
                try:
                    client.collections.delete(collection_name)
                    self.logger.info(f"Cleaned up failed collection: {collection_name}")
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to cleanup collection {collection_name}: {cleanup_error}")
                return None

        except Exception as create_error:
            self.logger.error(f"Failed to create collection {collection_name}")
            self.logger.error(f"Create error type: {type(create_error).__name__}")
            self.logger.error(f"Create error message: {create_error}")
            import traceback
            self.logger.error(f"Create collection traceback: {traceback.format_exc()}")
            return None

    def _validate_collection(self, collection: Any, collection_name: str) -> bool:
        """
        Validate that a collection can be accessed and queried.

        Args:
            collection: Collection object to validate
            collection_name: Name for logging

        Returns:
            bool: True if collection is valid
        """
        try:
            # Test with a simple aggregate query
            response = collection.aggregate.over_all(total_count=True)
            if response.total_count >= 0:  # Should be 0+ for valid collection
                self.logger.info(f"Collection {collection_name} validated successfully")
                return True
            else:
                self.logger.error(f"Collection {collection_name} validation failed (unexpected count)")
                return False
        except Exception as validation_error:
            self.logger.error(f"Collection {collection_name} validation failed: {validation_error}")
            return False

   

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection and remove from cache.

        Args:
            collection_name: Name of collection to delete

        Returns:
            bool: True if deleted successfully
        """
        client = self.connection_manager.get_client()
        if not client:
            return False

        try:
            client.collections.delete(collection_name)

            # Remove from cache
            if collection_name in self._cached_collections:
                del self._cached_collections[collection_name]

            self.logger.info(f"Deleted collection: {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    def list_collections(self) -> List[str]:
        """
        List all available collections.

        Returns:
            List of collection names
        """
        client = self.connection_manager.get_client()
        if not client:
            return []

        try:
            collections = client.collections.list_all()
            collection_names = [col for col in collections]
            self.logger.debug(f"Found collections: {collection_names}")
            return collection_names
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection information including document count and metadata.

        Args:
            collection_name: Name of collection to inspect

        Returns:
            Dict with collection info or None if unavailable
        """
        collection = self.get_or_create_collection(collection_name)
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
                "status": "active"
            }

        except Exception as e:
            self.logger.warning(f"Could not get exact count for collection {collection_name}, using default: {e}")
            # Return collection info with count 0 if aggregate fails
            return {
                "name": collection_name,
                "count": 0,
                "metadata": {"created_at": datetime.now().isoformat()},
                "status": "active"
            }

    def reset_cache(self):
        """Clear all cached collections."""
        self._cached_collections.clear()
        self.logger.info("Collection cache cleared")


# Global collection manager instance
collection_manager = CollectionManager(None)
