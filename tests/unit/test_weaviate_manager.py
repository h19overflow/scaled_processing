"""
Unit tests for WeaviateManager - drop-in replacement for ChromaManager.
Tests interface compatibility and core functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager import WeaviateManager


class TestWeaviateManager:
    """Test suite for WeaviateManager interface compatibility."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.mock_client = Mock()
        self.mock_client.is_ready.return_value = True
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_init_creates_manager_successfully(self, mock_connect):
        """Test that WeaviateManager initializes successfully."""
        mock_connect.return_value = self.mock_client
        
        manager = WeaviateManager(collection_name="test_collection")
        
        assert manager.collection_name == "test_collection"
        assert manager._cached_client is not None
        mock_connect.assert_called_once()
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_init_handles_connection_failure(self, mock_connect):
        """Test that WeaviateManager handles connection failures gracefully."""
        mock_connect.side_effect = Exception("Connection failed")
        
        manager = WeaviateManager()
        
        assert manager._cached_client is None
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_get_client_returns_cached_client(self, mock_connect):
        """Test that get_client returns the cached Weaviate client."""
        mock_connect.return_value = self.mock_client
        
        manager = WeaviateManager()
        client = manager.get_client()
        
        assert client == self.mock_client
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_get_client_initializes_if_none(self, mock_connect):
        """Test that get_client initializes client if None."""
        mock_connect.return_value = self.mock_client
        
        manager = WeaviateManager()
        manager._cached_client = None
        
        client = manager.get_client()
        
        assert client == self.mock_client
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_get_collection_creates_new_collection(self, mock_connect):
        """Test that get_collection creates new collection if not exists."""
        mock_connect.return_value = self.mock_client
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        
        # Mock get collection to fail first (not found), then create succeeds
        self.mock_client.collections.get.side_effect = Exception("Not found")
        self.mock_client.collections.create.return_value = mock_collection
        
        manager = WeaviateManager()
        collection = manager.get_collection("test_collection")
        
        assert collection == mock_collection
        assert "test_collection" in manager._cached_collections
        self.mock_client.collections.create.assert_called_once()
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_get_collection_returns_existing_collection(self, mock_connect):
        """Test that get_collection returns existing collection."""
        mock_connect.return_value = self.mock_client
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        
        self.mock_client.collections.get.return_value = mock_collection
        
        manager = WeaviateManager()
        collection = manager.get_collection("test_collection")
        
        assert collection == mock_collection
        self.mock_client.collections.get.assert_called_once_with("test_collection")
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_get_collection_uses_cache(self, mock_connect):
        """Test that get_collection uses cached collection."""
        mock_connect.return_value = self.mock_client
        mock_collection = Mock()
        
        manager = WeaviateManager()
        manager._cached_collections["test_collection"] = mock_collection
        
        collection = manager.get_collection("test_collection")
        
        assert collection == mock_collection
        # Should not call client methods if cached
        self.mock_client.collections.get.assert_not_called()
        self.mock_client.collections.create.assert_not_called()
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_list_collections_returns_collection_names(self, mock_connect):
        """Test that list_collections returns list of collection names."""
        mock_connect.return_value = self.mock_client
        
        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        
        self.mock_client.collections.list_all.return_value = [mock_collection1, mock_collection2]
        
        manager = WeaviateManager()
        collections = manager.list_collections()
        
        assert collections == ["collection1", "collection2"]
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_list_collections_handles_error(self, mock_connect):
        """Test that list_collections handles errors gracefully."""
        mock_connect.return_value = self.mock_client
        self.mock_client.collections.list_all.side_effect = Exception("Connection error")
        
        manager = WeaviateManager()
        collections = manager.list_collections()
        
        assert collections == []
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_delete_collection_removes_collection(self, mock_connect):
        """Test that delete_collection removes collection and cache."""
        mock_connect.return_value = self.mock_client
        mock_collection = Mock()
        
        manager = WeaviateManager()
        manager._cached_collections["test_collection"] = mock_collection
        
        result = manager.delete_collection("test_collection")
        
        assert result is True
        assert "test_collection" not in manager._cached_collections
        self.mock_client.collections.delete.assert_called_once_with("test_collection")
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_delete_collection_handles_error(self, mock_connect):
        """Test that delete_collection handles errors gracefully."""
        mock_connect.return_value = self.mock_client
        self.mock_client.collections.delete.side_effect = Exception("Delete failed")
        
        manager = WeaviateManager()
        result = manager.delete_collection("test_collection")
        
        assert result is False
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_get_collection_info_returns_info_dict(self, mock_connect):
        """Test that get_collection_info returns collection information."""
        mock_connect.return_value = self.mock_client
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        
        # Mock aggregate response
        mock_response = Mock()
        mock_response.total_count = 42
        mock_collection.aggregate.over_all.return_value = mock_response
        
        self.mock_client.collections.get.return_value = mock_collection
        
        manager = WeaviateManager()
        info = manager.get_collection_info("test_collection")
        
        assert info is not None
        assert info["name"] == "test_collection"
        assert info["count"] == 42
        assert "metadata" in info
        assert "persist_directory" in info
        
    @patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager.weaviate.connect_to_local')
    def test_reset_database_deletes_all_collections(self, mock_connect):
        """Test that reset_database removes all collections."""
        mock_connect.return_value = self.mock_client
        
        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        
        self.mock_client.collections.list_all.return_value = [mock_collection1, mock_collection2]
        
        manager = WeaviateManager()
        manager._cached_collections = {"collection1": mock_collection1, "collection2": mock_collection2}
        
        result = manager.reset_database()
        
        assert result is True
        assert len(manager._cached_collections) == 0
        assert self.mock_client.collections.delete.call_count == 2
        
    def test_validate_chromadb_format_valid_data(self):
        """Test that _validate_chromadb_format validates correct format."""
        manager = WeaviateManager()
        
        valid_data = {
            "ids": ["id1", "id2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]], 
            "metadatas": [{"key1": "val1"}, {"key2": "val2"}],
            "documents": ["doc1", "doc2"]
        }
        
        result = manager._validate_chromadb_format(valid_data)
        assert result is True
        
    def test_validate_chromadb_format_missing_keys(self):
        """Test that _validate_chromadb_format rejects missing keys."""
        manager = WeaviateManager()
        
        invalid_data = {
            "ids": ["id1", "id2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
            # Missing metadatas and documents
        }
        
        result = manager._validate_chromadb_format(invalid_data)
        assert result is False
        
    def test_validate_chromadb_format_length_mismatch(self):
        """Test that _validate_chromadb_format rejects length mismatches."""
        manager = WeaviateManager()
        
        invalid_data = {
            "ids": ["id1", "id2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            "metadatas": [{"key1": "val1"}],  # Length mismatch
            "documents": ["doc1", "doc2"]
        }
        
        result = manager._validate_chromadb_format(invalid_data)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])