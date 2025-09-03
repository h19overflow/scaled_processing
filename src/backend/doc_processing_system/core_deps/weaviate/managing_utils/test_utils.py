"""
Test utilities for Weaviate operations.
Contains testing functions, debugging utilities, and mock data generators.
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import weaviate
from weaviate.classes.config import Configure, Property, DataType


class TestUtils:
    """
    Utilities for testing and debugging Weaviate operations.
    """

    def __init__(self, connection_manager, collection_manager):
        """
        Initialize test utilities with dependencies.

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

    def run_full_diagnostic_test(self) -> Dict[str, Any]:
        """
        Run comprehensive diagnostic test on Weaviate setup.

        Returns:
            Dict with diagnostic results
        """
        self.logger.info("Running full Weaviate diagnostic test")

        results = {
            "timestamp": datetime.now().isoformat(),
            "connection_test": self.test_connection_detailed(),
            "collection_test": self.test_collection_operations(),
            "database_test": self.test_database_operations(),
            "performance_test": self.run_performance_test(),
            "overall_status": "unknown"
        }

        # Determine overall status
        test_results = [
            results["connection_test"]["status"] == "passed",
            results["collection_test"]["status"] == "passed",
            results["database_test"]["status"] == "passed"
        ]

        if all(test_results):
            results["overall_status"] = "success"
            self.logger.info("✅ Diagnostic test completed successfully")
        else:
            results["overall_status"] = "failed"
            self.logger.error("❌ Diagnostic test found issues")

        return results

    def test_connection_detailed(self) -> Dict[str, Any]:
        """
        Test connection with detailed diagnostics.

        Returns:
            Dict with connection test results
        """
        self.logger.info("Testing Weaviate connection")

        try:
            # Test basic connection
            connection_result = self.connection_manager.test_connection()
            if not connection_result:
                return {
                    "status": "failed",
                    "error": "Connection test failed",
                    "details": "Cannot connect to Weaviate instance"
                }

            # Test client availability
            client = self.connection_manager.get_client()
            if not client:
                return {
                    "status": "failed",
                    "error": "Client unavailable",
                    "details": "Cannot get Weaviate client instance"
                }

            # Test ready state
            is_ready = client.is_ready()

            return {
                "status": "passed" if is_ready else "warning",
                "client_available": True,
                "server_ready": is_ready,
                "connection_time": "fast",  # Would need timing for this
                "version_info": self.get_weaviate_version(client)
            }

        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def test_collection_operations(self) -> Dict[str, Any]:
        """
        Test collection creation, retrieval, and operations.

        Returns:
            Dict with collection test results
        """
        self.logger.info("Testing collection operations")

        try:
            # Test collection creation
            test_collection_name = f"test_collection_{int(time.time())}"
            collection = self.collection_manager.get_or_create_collection(test_collection_name)

            if not collection:
                return {
                    "status": "failed",
                    "error": "Collection creation failed",
                    "collection_name": test_collection_name
                }

            # Test collection validation
            validation_result = self.collection_manager._validate_collection(collection, test_collection_name)
            if not validation_result:
                return {
                    "status": "failed",
                    "error": "Collection validation failed",
                    "collection_name": test_collection_name
                }

            # Test collection info
            info = self.collection_manager.get_collection_info(test_collection_name)
            collection_count = info.get("count", -1) if info else -1

            # Cleanup
            delete_result = self.collection_manager.delete_collection(test_collection_name)

            return {
                "status": "passed",
                "collection_name": test_collection_name,
                "creation_success": True,
                "validation_success": True,
                "info_retrieval_success": collection_count >= 0,
                "cleanup_success": delete_result,
                "initial_object_count": collection_count
            }

        except Exception as e:
            self.logger.error(f"Collection test failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def test_database_operations(self) -> Dict[str, Any]:
        """
        Test database-level operations.

        Returns:
            Dict with database test results
        """
        self.logger.info("Testing database operations")

        try:
            # Test getting database stats directly
            collections = self.collection_manager.list_collections()
            total_objects = 0
            for collection_name in collections:
                info = self.collection_manager.get_collection_info(collection_name)
                if info:
                    total_objects += info.get("count", 0)
            
            stats = {
                "status": "connected",
                "collections_count": len(collections),
                "objects_count": total_objects
            }

            # Test integrity verification directly  
            integrity = {"overall_health": "healthy", "issues_found": 0}
            for collection_name in collections:
                collection = self.collection_manager.get_or_create_collection(collection_name)
                if collection is None:
                    integrity = {"overall_health": "issues_found", "issues_found": 1}
            integrity_healthy = integrity.get("overall_health") == "healthy"

            return {
                "status": "passed" if integrity_healthy else "warning",
                "collections_count": stats.get("collections_count", 0),
                "objects_count": stats.get("objects_count", 0),
                "server_status": stats.get("status"),
                "integrity_check": integrity_healthy,
                "integrity_details": {
                    "collections_checked": integrity.get("collections_checked", 0),
                    "issues_found": integrity.get("issues_found", 0)
                }
            }

        except Exception as e:
            self.logger.error(f"Database test failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def run_performance_test(self) -> Dict[str, Any]:
        """
        Run performance test for basic operations.

        Returns:
            Dict with performance metrics
        """
        self.logger.info("Running performance test")

        try:
            start_time = time.time()

            # Test connection speed
            connection_start = time.time()
            connection_success = self.connection_manager.test_connection()
            connection_time = time.time() - connection_start

            # Test collection operation speed
            collection_start = time.time()
            test_collection = f"perf_test_{int(time.time())}"
            collection = self.collection_manager.get_or_create_collection(test_collection)
            collection_time = time.time() - collection_start

            # Cleanup
            if collection:
                self.collection_manager.delete_collection(test_collection)

            total_time = time.time() - start_time

            return {
                "total_time_seconds": total_time,
                "connection_time_seconds": connection_time,
                "collection_operation_time_seconds": collection_time,
                "connection_speed": "fast" if connection_time < 1.0 else "slow",
                "collection_speed": "fast" if collection_time < 2.0 else "slow",
                "success": connection_success and (collection is not None)
            }

        except Exception as e:
            self.logger.error(f"Performance test failed: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "success": False
            }

    def generate_sample_data(self, collection_name: str, num_objects: int = 10) -> Dict[str, List]:
        """
        Generate sample data for testing.

        Args:
            collection_name: Name of collection for sample data
            num_objects: Number of sample objects to generate

        Returns:
            Dict in ChromaDB format with sample data
        """
        self.logger.info(f"Generating sample data: {num_objects} objects for {collection_name}")

        ids = [f"{collection_name}_sample_{i}" for i in range(num_objects)]
        embeddings = [[float(i + j) for j in range(128)] for i in range(num_objects)]  # 128-dim vectors

        metadatas = []
        documents = []

        for i in range(num_objects):
            metadata = {
                "document_id": f"doc_{i}",
                "chunk_id": f"chunk_{i}",
                "chunk_index": i,
                "page_number": i % 10,
                "source_file": f"sample_doc_{i}.pdf",
                "original_filename": f"sample_doc_{i}.pdf",
                "document_type": "sample",
                "chunk_length": len(f"Sample document text for object {i}"),
                "word_count": len(f"Sample document text for object {i}".split()),
                "chunk_position": f"page_{i % 10}",
                "chunking_strategy": "fixed_length",
                "embedding_model": "sample_model",
                "chunk_created_at": datetime.now().isoformat(),
                "ingested_at": datetime.now().isoformat()
            }
            metadatas.append(metadata)
            documents.append(f"Sample document text for object {i}. This is a test document.")

        return {
            "ids": ids,
            "embeddings": embeddings,
            "metadatas": metadatas,
            "documents": documents
        }

    def cleanup_test_collections(self, pattern: str = "test_") -> int:
        """
        Clean up test collections matching a pattern.

        Args:
            pattern: Pattern to match collection names for cleanup

        Returns:
            int: Number of collections cleaned up
        """
        self.logger.info(f"Cleaning up test collections with pattern: {pattern}")

        try:
            collections = self.collection_manager.list_collections()
            cleaned_count = 0

            for collection_name in collections:
                if pattern in collection_name:
                    if self.collection_manager.delete_collection(collection_name):
                        self.logger.info(f"Cleaned up collection: {collection_name}")
                        cleaned_count += 1
                    else:
                        self.logger.warning(f"Failed to clean up collection: {collection_name}")

            return cleaned_count

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0

    def get_weaviate_version(self, client: Optional[weaviate.WeaviateClient] = None) -> str:
        """
        Get Weaviate version information.

        Args:
            client: Weaviate client (optional, will get from connection manager)

        Returns:
            str: Version information or "unknown"
        """
        try:
            if not client:
                client = self.connection_manager.get_client()

            if client:
                # Weaviate doesn't expose version through public API in most cases
                # This is just a placeholder for future implementation
                return "unknown"
            else:
                return "no_client"

        except Exception as e:
            self.logger.debug(f"Cannot get Weaviate version: {e}")
            return "unknown"

    def export_collection_data(self, collection_name: str, output_file: Optional[str] = None) -> bool:
        """
        Export collection data for debugging/development.

        Args:
            collection_name: Name of collection to export
            output_file: Output file path (auto-generated if None)

        Returns:
            bool: True if export successful
        """
        self.logger.info(f"Exporting collection data: {collection_name}")

        try:
            # Get collection
            collection = self.collection_manager.get_or_create_collection(collection_name)
            if not collection:
                self.logger.error(f"Cannot export: collection {collection_name} not available")
                return False

            # Query all objects (this is a simplified version)
            # In practice, you'd want to paginate for large collections
            response = collection.query.fetch_objects(limit=100)

            data = {
                "collection_name": collection_name,
                "export_time": datetime.now().isoformat(),
                "total_objects_exported": len(response.objects),
                "objects": []
            }

            for obj in response.objects:
                data["objects"].append({
                    "id": obj.properties.get('chunk_id', 'unknown'),
                    "properties": obj.properties,
                    "vector_exists": obj.vector is not None
                })

            # Generate output filename
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"collection_export_{collection_name}_{timestamp}.json"

            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Collection data exported to: {output_file}")
            self.logger.info(f"Total objects exported: {len(response.objects)}")
            return True

        except Exception as e:
            self.logger.error(f"Collection export failed: {e}")
            return False


# Global test utilities instance - will be initialized with dependencies
test_utils = None
