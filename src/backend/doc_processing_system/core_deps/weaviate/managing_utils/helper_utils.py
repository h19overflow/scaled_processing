"""
Helper utilities for Weaviate operations.
Contains validation functions, format conversions, and utility methods.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class HelperUtilities:
    """
    Collection of utility functions for Weaviate operations.
    """

    def __init__(self):
        """Initialize helper utilities."""
        self.logger = logging.getLogger(__name__)

        # Setup logger if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def validate_chromadb_format(self, data: Dict[str, Any]) -> bool:
        """
        Validate ChromaDB-ready format structure.
        This is the expected format for data ingested into Weaviate.

        Args:
            data: Data to validate

        Returns:
            bool: True if valid ChromaDB format
        """
        required_keys = ["ids", "embeddings", "metadatas", "documents"]

        if not all(key in data for key in required_keys):
            self.logger.error(f"Missing required keys in ChromaDB format. Expected: {required_keys}")
            self.logger.error(f"Found keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            return False

        # Check all arrays have same length
        lengths = []
        for key in required_keys:
            if isinstance(data[key], list):
                lengths.append(len(data[key]))
            else:
                self.logger.error(f"Expected list for '{key}', got {type(data[key])}")
                return False

        if len(set(lengths)) != 1:
            self.logger.error(f"Array length mismatch in ChromaDB format: {dict(zip(required_keys, lengths))}")
            for i, key in enumerate(required_keys):
                self.logger.debug(f"  {key}: {lengths[i]} items")
            return False

        self.logger.debug(f"ChromaDB format validation passed: {lengths[0]} items")
        return True

    def get_default_persist_dir(self) -> str:
        """
        Get default persistence directory in project data folder.

        Returns:
            str: Path to default persistence directory
        """
        project_root = Path(__file__).parent.parent.parent.parent.parent
        data_dir = project_root / "data" / "weaviate_db"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def validate_weaviate_object_format(self, objects: List[Dict[str, Any]]) -> bool:
        """
        Validate Weaviate object format.

        Args:
            objects: List of objects to validate

        Returns:
            bool: True if valid Weaviate format
        """
        if not isinstance(objects, list):
            self.logger.error(f"Expected list of objects, got {type(objects)}")
            return False

        if not objects:
            self.logger.debug("Object list is empty")
            return True  # Empty list is valid

        required_keys = ["properties", "vector"]
        for i, obj in enumerate(objects):
            if not isinstance(obj, dict):
                self.logger.error(f"Object {i} is not a dictionary, got {type(obj)}")
                return False

            missing_keys = [key for key in required_keys if key not in obj]
            if missing_keys:
                self.logger.error(f"Object {i} missing required keys: {missing_keys}")
                return False

        self.logger.debug(f"Weaviate object format validation passed: {len(objects)} objects")
        return True

    def safe_get_nested_value(self, data: Dict[str, Any], key_path: str, default=None) -> Any:
        """
        Safely get nested dictionary values using dot notation.

        Args:
            data: Dictionary to extract from
            key_path: Dot-separated key path (e.g., "chromadb_ready.ids")
            default: Default value if key path not found

        Returns:
            Value at key path or default
        """
        keys = key_path.split('.')
        current = data

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except Exception as e:
            self.logger.debug(f"Safe get failed for key_path '{key_path}': {e}")
            return default

    def format_collection_stats(self, collection_info: Dict[str, Any]) -> str:
        """
        Format collection information for logging/display.

        Args:
            collection_info: Collection information dictionary

        Returns:
            str: Formatted string for display
        """
        if not collection_info:
            return "No collection information available"

        name = collection_info.get("name", "unknown")
        count = collection_info.get("count", 0)
        status = collection_info.get("status", "unknown")

        return f"Collection '{name}': {count} objects, status: {status}"

    def calculate_batch_sizes(self, total_items: int, max_batch_size: int = 100) -> List[int]:
        """
        Calculate optimal batch sizes for processing items.

        Args:
            total_items: Total number of items to batch
            max_batch_size: Maximum items per batch

        Returns:
            List of batch sizes
        """
        if total_items <= 0:
            return []

        batch_sizes = []
        remaining = total_items

        while remaining > 0:
            batch_size = min(remaining, max_batch_size)
            batch_sizes.append(batch_size)
            remaining -= batch_size

        return batch_sizes

    def validate_embedding_dimensions(self, embeddings: List[List[float]], expected_dim: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate embedding dimensions consistency.

        Args:
            embeddings: List of embedding vectors
            expected_dim: Expected dimension (optional)

        Returns:
            Dict with validation results
        """
        if not embeddings:
            return {"valid": False, "error": "Empty embeddings list"}

        dimensions = []
        total_embeddings = len(embeddings)

        for i, embedding in enumerate(embeddings):
            if not isinstance(embedding, list):
                return {"valid": False, "error": f"Embedding {i} is not a list"}

            if not embedding:
                return {"valid": False, "error": f"Embedding {i} is empty"}

            dimensions.append(len(embedding))

        unique_dims = set(dimensions)
        if len(unique_dims) != 1:
            return {
                "valid": False,
                "error": f"Inconsistent dimensions: {unique_dims}",
                "dimension_counts": {dim: dimensions.count(dim) for dim in unique_dims}
            }

        dimension = list(unique_dims)[0]

        if expected_dim and dimension != expected_dim:
            return {
                "valid": False,
                "error": f"Dimension mismatch: expected {expected_dim}, got {dimension}"
            }

        return {
            "valid": True,
            "dimension": dimension,
            "total_embeddings": total_embeddings,
            "uniform_dimension": True
        }

    def format_error_message(self, error: Exception, context: str = "") -> str:
        """
        Format error messages for consistent logging.

        Args:
            error: Exception object
            context: Additional context information

        Returns:
            str: Formatted error message
        """
        error_type = type(error).__name__
        error_msg = str(error)

        if context:
            return f"{error_type} in {context}: {error_msg}"
        else:
            return f"{error_type}: {error_msg}"

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information for debugging and monitoring.

        Returns:
            Dict with system information
        """
        import sys
        from platform import platform

        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform(),
            "current_time": datetime.now().isoformat(),
            "working_directory": str(Path.cwd())
        }

    def safe_file_operation(self, operation_func, file_path: str, *args, **kwargs):
        """
        Safely execute file operations with error handling.

        Args:
            operation_func: Function to execute (e.g., open, os.path.exists)
            file_path: File path for operation
            *args: Additional positional arguments for operation_func
            **kwargs: Additional keyword arguments for operation_func

        Returns:
            Tuple of (success: bool, result: Any, error: str)
        """
        try:
            result = operation_func(file_path, *args, **kwargs)
            return True, result, ""
        except Exception as e:
            error_msg = self.format_error_message(e, f"file operation on '{file_path}'")
            return False, None, error_msg


# Global helper utilities instance
helper_utilities = HelperUtilities()
