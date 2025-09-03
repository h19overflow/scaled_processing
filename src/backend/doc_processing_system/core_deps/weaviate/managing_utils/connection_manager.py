"""Weaviate connection management utilities."""

import logging
from typing import Optional
import weaviate


class ConnectionManager:
    """Manages Weaviate client connections with caching and error handling."""

    def __init__(self):
        """Initialize the connection manager."""
        self.logger = logging.getLogger(__name__)
        self._cached_client: Optional[weaviate.WeaviateClient] = None
        self._is_initialized = False

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def initialize_connection(self) -> bool:
        """
        Initialize connection to Weaviate if not already done.

        Returns:
            bool: True if connected successfully
        """
        if self._is_initialized:
            return self._cached_client is not None

        try:
            self.logger.info("Initializing Weaviate connection at localhost:8080")

            # Connect to local Weaviate instance
            self._cached_client = weaviate.connect_to_local()

            # Test connection
            if self._cached_client.is_ready():
                self.logger.info("Weaviate connection initialized successfully")
                self._is_initialized = True
                return True
            else:
                self.logger.error("Weaviate client is not ready after connection")
                self._cached_client = None
                return False

        except Exception as e:
            self.logger.error(f"Failed to initialize Weaviate connection: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Connection traceback: {traceback.format_exc()}")
            self._cached_client = None
            return False

    def get_client(self) -> Optional[weaviate.WeaviateClient]:
        """
        Get cached Weaviate client, initializing if necessary.

        Returns:
            Weaviate client instance or None if unavailable
        """
        if not self._is_initialized:
            if not self.initialize_connection():
                return None

        return self._cached_client

    def test_connection(self) -> bool:
        """
        Test current connection to Weaviate.

        Returns:
            bool: True if connection is working
        """
        try:
            client = self.get_client()
            if client is None:
                return False

            return client.is_ready()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def close_connection(self):
        """Close the cached connection."""
        if self._cached_client:
            try:
                self._cached_client.close()
                self.logger.info("Weaviate connection closed")
            except Exception as e:
                self.logger.error(f"Error closing Weaviate connection: {e}")
            finally:
                self._cached_client = None
                self._is_initialized = False

    def reset_connection(self):
        """Force reset of the connection."""
        self.logger.info("Resetting Weaviate connection")
        self.close_connection()
        self.initialize_connection()


# Global connection manager instance
connection_manager = ConnectionManager()
