"""
Unit tests for WeaviateIngestionEngine - drop-in replacement for ChunkIngestionEngine.
Tests interface compatibility and core functionality.
"""

import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime
from src.backend.doc_processing_system.core_deps.weaviate.weaviate_ingestion_engine import WeaviateIngestionEngine


class TestWeaviateIngestionEngine:
    """Test suite for WeaviateIngestionEngine interface compatibility."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.mock_manager = Mock()
        self.mock_collection = Mock()
        self.mock_collection.name = "test_collection"
        self.mock_batch = Mock()
        self.mock_batch.number_errors = 0
        self.mock_batch.failed_objects = []
        
        # Mock batch context manager
        self.mock_collection.batch.fixed_size.return_value.__enter__ = Mock(return_value=self.mock_batch)
        self.mock_collection.batch.fixed_size.return_value.__exit__ = Mock(return_value=None)
        self.mock_collection.batch.failed_objects = []
        
    def test_init_creates_engine_successfully(self):
        """Test that WeaviateIngestionEngine initializes successfully."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        assert engine.weaviate_manager == self.mock_manager
        assert engine.chunks_dir == Path("data/rag/chunks")
        assert engine.embeddings_dir == Path("data/rag/embeddings")
        
    def test_init_creates_default_manager_if_none(self):
        """Test that WeaviateIngestionEngine creates default manager if none provided."""
        with patch('src.backend.doc_processing_system.core_deps.weaviate.weaviate_ingestion_engine.WeaviateManager'):
            engine = WeaviateIngestionEngine()
            
            assert engine.weaviate_manager is not None
            
    def test_load_json_file_success(self):
        """Test that _load_json_file loads JSON successfully."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        test_data = {"key": "value", "number": 123}
        json_content = json.dumps(test_data)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = engine._load_json_file("test_file.json")
            
        assert result == test_data
        
    def test_load_json_file_handles_error(self):
        """Test that _load_json_file handles errors gracefully."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = engine._load_json_file("nonexistent_file.json")
            
        assert result is None
        
    def test_validate_chromadb_format_valid(self):
        """Test that _validate_chromadb_format validates correct format."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        valid_data = {
            "ids": ["id1", "id2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            "metadatas": [{"meta1": "val1"}, {"meta2": "val2"}],
            "documents": ["doc1", "doc2"]
        }
        
        result = engine._validate_chromadb_format(valid_data)
        assert result is True
        
    def test_validate_chromadb_format_invalid(self):
        """Test that _validate_chromadb_format rejects invalid format."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        # Missing required keys
        invalid_data = {
            "ids": ["id1", "id2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }
        
        result = engine._validate_chromadb_format(invalid_data)
        assert result is False
        
        # Length mismatch
        invalid_data = {
            "ids": ["id1", "id2"],
            "embeddings": [[0.1, 0.2]],  # One fewer than ids
            "metadatas": [{"meta1": "val1"}, {"meta2": "val2"}],
            "documents": ["doc1", "doc2"]
        }
        
        result = engine._validate_chromadb_format(invalid_data)
        assert result is False
        
    def test_convert_chromadb_to_weaviate_format(self):
        """Test conversion from ChromaDB to Weaviate format."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chromadb_data = {
            "ids": ["chunk1", "chunk2"],
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            "metadatas": [
                {
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "page_number": 1,
                    "source_file": "test.pdf",
                    "chunk_created_at": "2023-01-01T00:00:00"
                },
                {
                    "document_id": "doc1", 
                    "chunk_index": 1,
                    "page_number": 1,
                    "source_file": "test.pdf",
                    "chunk_created_at": "2023-01-01T00:00:00"
                }
            ],
            "documents": ["First chunk content", "Second chunk content"]
        }
        
        result = engine._convert_chromadb_to_weaviate_format(chromadb_data)
        
        assert len(result) == 2
        
        # Check first object
        obj1 = result[0]
        assert obj1["properties"]["content"] == "First chunk content"
        assert obj1["properties"]["document_id"] == "doc1"
        assert obj1["properties"]["chunk_id"] == "chunk1"
        assert obj1["vector"] == [0.1, 0.2, 0.3]
        
        # Check second object
        obj2 = result[1]
        assert obj2["properties"]["content"] == "Second chunk content"
        assert obj2["properties"]["chunk_id"] == "chunk2"
        assert obj2["vector"] == [0.4, 0.5, 0.6]
        
    def test_convert_chromadb_to_weaviate_format_handles_error(self):
        """Test that format conversion handles errors gracefully."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        # Invalid data structure
        invalid_data = {"invalid": "structure"}
        
        result = engine._convert_chromadb_to_weaviate_format(invalid_data)
        assert result == []
        
    def test_ingest_from_embeddings_file_success(self):
        """Test successful ingestion from embeddings file."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        # Mock file loading
        embeddings_data = {
            "chromadb_ready": {
                "ids": ["chunk1"],
                "embeddings": [[0.1, 0.2, 0.3]],
                "metadatas": [{"document_id": "doc1", "chunk_index": 0}],
                "documents": ["Test content"]
            }
        }
        
        # Mock manager methods
        self.mock_manager.get_collection.return_value = self.mock_collection
        
        with patch.object(engine, '_load_json_file', return_value=embeddings_data):
            with patch.object(engine, '_store_in_weaviate', return_value=True) as mock_store:
                result = engine.ingest_from_embeddings_file("test_file.json", "test_collection")
                
        assert result is True
        # Verify that _store_in_weaviate was called with correct arguments
        mock_store.assert_called_once_with(embeddings_data["chromadb_ready"], "test_collection")
        
    def test_ingest_from_embeddings_file_no_chromadb_ready(self):
        """Test ingestion fails when no chromadb_ready format found."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        # Data without chromadb_ready format
        embeddings_data = {"some_other_format": {"data": "here"}}
        
        with patch.object(engine, '_load_json_file', return_value=embeddings_data):
            result = engine.ingest_from_embeddings_file("test_file.json")
            
        assert result is False
        
    def test_ingest_from_embeddings_file_invalid_format(self):
        """Test ingestion fails with invalid chromadb format."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        embeddings_data = {
            "chromadb_ready": {
                "ids": ["chunk1"],
                # Missing other required fields
            }
        }
        
        with patch.object(engine, '_load_json_file', return_value=embeddings_data):
            result = engine.ingest_from_embeddings_file("test_file.json")
            
        assert result is False
        
    def test_ingest_from_chromadb_ready_file_compatibility(self):
        """Test that ingest_from_chromadb_ready_file calls ingest_from_embeddings_file."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        with patch.object(engine, 'ingest_from_embeddings_file', return_value=True) as mock_ingest:
            result = engine.ingest_from_chromadb_ready_file("test_file.json", "test_collection")
            
        assert result is True
        mock_ingest.assert_called_once_with("test_file.json", "test_collection")
        
    def test_store_in_weaviate_success(self):
        """Test successful storage in Weaviate."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chromadb_data = {
            "ids": ["chunk1"],
            "embeddings": [[0.1, 0.2, 0.3]],
            "metadatas": [{"document_id": "doc1"}],
            "documents": ["Test content"]
        }
        
        # Mock manager and collection
        self.mock_manager.get_collection.return_value = self.mock_collection
        self.mock_manager.get_collection_info.return_value = {"count": 1}
        
        result = engine._store_in_weaviate(chromadb_data, "test_collection")
        
        assert result is True
        self.mock_manager.get_collection.assert_called_with("test_collection")
        
    def test_store_in_weaviate_no_collection(self):
        """Test storage fails when collection cannot be retrieved."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chromadb_data = {
            "ids": ["chunk1"],
            "embeddings": [[0.1, 0.2, 0.3]],
            "metadatas": [{"document_id": "doc1"}],
            "documents": ["Test content"]
        }
        
        self.mock_manager.get_collection.return_value = None
        
        result = engine._store_in_weaviate(chromadb_data, "test_collection")
        
        assert result is False
        
    def test_store_in_weaviate_invalid_format(self):
        """Test storage fails with invalid ChromaDB format."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        invalid_data = {"invalid": "format"}
        
        self.mock_manager.get_collection.return_value = self.mock_collection
        
        result = engine._store_in_weaviate(invalid_data, "test_collection")
        
        assert result is False
        
    def test_get_ingestion_stats_success(self):
        """Test getting ingestion statistics."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        collection_info = {
            "name": "test_collection",
            "count": 42,
            "metadata": {"created_at": "2023-01-01T00:00:00"},
            "persist_directory": "/test/path"
        }
        
        self.mock_manager.get_collection_info.return_value = collection_info
        
        stats = engine.get_ingestion_stats("test_collection")
        
        assert stats["collection_name"] == "test_collection"
        assert stats["document_count"] == 42
        assert stats["created_at"] == "2023-01-01T00:00:00"
        assert stats["persist_directory"] == "/test/path"
        
    def test_get_ingestion_stats_no_collection_info(self):
        """Test getting stats when collection info not available."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        self.mock_manager.get_collection_info.return_value = None
        
        stats = engine.get_ingestion_stats("test_collection")
        
        assert stats == {}
        
    def test_validate_data_consistency_success(self):
        """Test successful data consistency validation."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chunks_data = {
            "document_id": "doc1",
            "chunks": [
                {"chunk_id": "chunk1", "content": "Content 1"},
                {"chunk_id": "chunk2", "content": "Content 2"}
            ]
        }
        
        embeddings_data = {
            "document_id": "doc1",
            "validated_embeddings": [
                {"chunk_id": "chunk1", "embedding_vector": [0.1, 0.2]},
                {"chunk_id": "chunk2", "embedding_vector": [0.3, 0.4]}
            ]
        }
        
        result = engine._validate_data_consistency(chunks_data, embeddings_data)
        assert result is True
        
    def test_validate_data_consistency_doc_id_mismatch(self):
        """Test data consistency validation with document ID mismatch."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chunks_data = {"document_id": "doc1", "chunks": []}
        embeddings_data = {"document_id": "doc2", "validated_embeddings": []}
        
        result = engine._validate_data_consistency(chunks_data, embeddings_data)
        assert result is False
        
    def test_validate_data_consistency_count_mismatch(self):
        """Test data consistency validation with count mismatch."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chunks_data = {
            "document_id": "doc1",
            "chunks": [{"chunk_id": "chunk1"}]  # 1 chunk
        }
        
        embeddings_data = {
            "document_id": "doc1",
            "validated_embeddings": [
                {"chunk_id": "chunk1"},
                {"chunk_id": "chunk2"}  # 2 embeddings
            ]
        }
        
        result = engine._validate_data_consistency(chunks_data, embeddings_data)
        assert result is False
        
    def test_validate_data_consistency_chunk_id_mismatch(self):
        """Test data consistency validation with chunk ID mismatch."""
        engine = WeaviateIngestionEngine(self.mock_manager)
        
        chunks_data = {
            "document_id": "doc1",
            "chunks": [{"chunk_id": "chunk1"}]
        }
        
        embeddings_data = {
            "document_id": "doc1", 
            "validated_embeddings": [{"chunk_id": "chunk2"}]  # Different chunk ID
        }
        
        result = engine._validate_data_consistency(chunks_data, embeddings_data)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])