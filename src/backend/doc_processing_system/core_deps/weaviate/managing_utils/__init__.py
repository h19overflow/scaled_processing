"""
Weaviate management utilities for connection, collection, and database operations.
Provides modular management utilities for Weaviate operations.
"""

from .connection_manager import ConnectionManager
from .collection_manager import CollectionManager
from .helper_utils import HelperUtilities
from .test_utils import TestUtils

# Initialize utilities with proper dependencies
_connection_manager = ConnectionManager()
_collection_manager = CollectionManager(_connection_manager)
_helper_utilities = HelperUtilities()
_test_utils = TestUtils(_connection_manager, _collection_manager)

# Provide singleton instances for easy access
connection_manager = _connection_manager
collection_manager = _collection_manager
helper_utilities = _helper_utilities
test_utils = _test_utils

# Update global instances in respective modules
from . import connection_manager
from . import collection_manager
from . import test_utils

connection_manager.connection_manager = _connection_manager
collection_manager.collection_manager = _collection_manager
test_utils.test_utils = _test_utils

__all__ = [
    # Classes
    "ConnectionManager",
    "CollectionManager",
    "HelperUtilities",
    "TestUtils",

    # Singleton instances (ready to use)
    "connection_manager",
    "collection_manager",
    "helper_utilities",
    "test_utils"
]
