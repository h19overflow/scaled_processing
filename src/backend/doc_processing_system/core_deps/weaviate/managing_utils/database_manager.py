"""
Weaviate database management utilities.
Handles database-level operations like reset, info gathering, and maintenance.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any


class DatabaseManager:
    """
    Manages database-level Weaviate operations.
    """

    def __init__(self, connection_manager, collection_manager):
        """
        Initialize database manager with dependencies.
        Args:
            connection_manager: ConnectionManager instance
            collection_manager: CollectionManager instance
        """
        self.logger = logging.getLogger(__name__)
        self.connection_manager = connection_manager
        self.collection_manager = collection_manager

        # Setup logger if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive database information.

        Returns:
            Dict with database statistics and info
        """
        self.logger.info("Retrieving database information")

        client = self.connection_manager.get_client()
        if not client:
            return {"status": "disconnected", "error": "No connection available"}

        try:
            collections = self.collection_manager.list_collections()

            # Get info for each collection
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
                "indexed_vectors": total_objects  # Assuming 1 vector per object for BYOV
            }

        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return {"status": "error", "error": str(e)}

    def reset_database(self) -> bool:
        """
        Reset entire Weaviate database - use with caution!
        Deletes all collections and clears all data.

        Returns:
            bool: True if reset successful
        """
        self.logger.warning("RESETTING ENTIRE WEAVIATE DATABASE")

        client = self.connection_manager.get_client()
        if not client:
            self.logger.error("Cannot reset database - no connection available")
            return False

        try:
            # Get list of all collections first
            collections = client.collections.list_all()
            collection_names = [col.name for col in collections]

            if not collection_names:
                self.logger.info("Database is already empty")
                self.collection_manager.reset_cache()  # Clear any cached collections
                return True

            self.logger.info(f"Found {len(collection_names)} collections to delete")

            # Delete each collection
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

            # Clear collection cache
            self.collection_manager.reset_cache()

            if failed_deletions:
                self.logger.error(f"Failed to delete {len(failed_deletions)} collections: {failed_deletions}")
                return False

            self.logger.warning(f"DATABASE RESET COMPLETE - Deleted {deleted_count} collections")
            return True

        except Exception as e:
            self.logger.error(f"Database reset failed: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Reset traceback: {traceback.format_exc()}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get detailed database statistics for monitoring.

        Returns:
            Dict with monitoring statistics
        """
        self.logger.info("Retrieving database statistics")

        client = self.connection_manager.get_client()
        if not client:
            return {
                "status": "disconnected",
                "available": False,
                "collections_count": 0,
                "objects_count": 0,
                "used_memory": "unknown",
                "uptime": "unknown"
            }

        try:
            database_info = self.get_database_info()

            return {
                "status": "connected",
                "available": True,
                "collections_count": database_info.get("total_collections", 0),
                "objects_count": database_info.get("total_objects", 0),
                "used_memory": "not_available",  # Weaviate doesn't expose this through API
                "uptime": "not_available",  # Weaviate doesn't expose this through API
                "collection_names": database_info.get("collections", []),
                "indexed_vectors": database_info.get("total_objects", 0)
            }

        except Exception as e:
            self.logger.error(f"Failed to get database statistics: {e}")
            return {
                "status": "error",
                "available": False,
                "error": str(e),
                "collections_count": 0,
                "objects_count": 0
            }

    def verify_database_integrity(self) -> Dict[str, Any]:
        """
        Verify database integrity by checking all collections and their data.

        Returns:
            Dict with integrity verification results
        """
        self.logger.info("Starting database integrity verification")

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
            self.logger.info(f"Verifying integrity of {len(collections)} collections")

            issues_found = 0
            collection_status = {}

            for collection_name in collections:
                try:
                    self.logger.debug(f"Verifying collection: {collection_name}")
                    collection = self.collection_manager.get_or_create_collection(collection_name)

                    if collection is None:
                        issues_found += 1
                        collection_status[collection_name] = "collection_unavailable"
                    else:
                        # Try to perform a basic operation
                        info = self.collection_manager.get_collection_info(collection_name)
                        if info and info.get("count", -1) >= 0:
                            collection_status[collection_name] = "healthy"
                        else:
                            issues_found += 1
                            collection_status[collection_name] = "query_failure"
                except Exception as e:
                    issues_found += 1
                    collection_status[collection_name] = f"error: {str(e)}"
                    self.logger.error(f"Integrity check failed for {collection_name}: {e}")

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

# Global database manager instance - will be initialized with dependencies
database_manager = None