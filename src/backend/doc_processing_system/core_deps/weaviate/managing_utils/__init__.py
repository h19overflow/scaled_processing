"""
Weaviate management utilities for connection, collection, and database operations.
Provides modular management utilities for Weaviate operations.
"""

from .connection_manager import ConnectionManager
from .collection_manager import CollectionManager

# Initialize utilities with proper dependencies
_connection_manager = ConnectionManager()
_collection_manager = CollectionManager(_connection_manager)

# Provide singleton instances for easy access
connection_manager = _connection_manager
collection_manager = _collection_manager

# Update global instances in respective modules
from . import connection_manager
from . import collection_manager

connection_manager.connection_manager = _connection_manager
collection_manager.collection_manager = _collection_manager

__all__ = [
    # Classes
    "ConnectionManager",
    "CollectionManager",
    
    # Singleton instances (ready to use)
    "connection_manager",
    "collection_manager",
]
