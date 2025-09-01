#!/usr/bin/env python3
"""
Test script to verify TwoStageChunker and EmbeddingsGenerator output TextChunk and ValidatedEmbedding models correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append('src/backend')

from doc_processing_system.pipelines.rag_processing.components.chunking.two_stage_chunker import TwoStageChunker
from doc_processing_system.pipelines.rag_processing.components.embeddings_generator import EmbeddingsGenerator


async def test_data_model_integration():
    """Test that both components produce correct data model outputs."""
    
    # Create test document file
    test_text = """
    This is a test document for verifying data model integration.
    
    The first paragraph discusses the importance of proper data structures.
    It ensures that our chunking system outputs TextChunk models correctly.
    
    The second paragraph focuses on embeddings generation.
    We need ValidatedEmbedding models for ChromaDB integration.
    This allows for seamless vector storage and retrieval.
    
    The third paragraph examines metadata consistency.
    All chunk IDs must be deterministic and traceable.
    Page numbers are placeholders until document parsing is enhanced.
    """
    
    document_id = "test_doc_001"
    
    # Create test file with markdown content (as provided by upstream processor)
    test_file_path = f"data/documents/processed/test_{document_id}.md"
    Path(test_file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_text)
    
    print("🧪 Testing Data Model Integration with Markdown File Input")
    print("=" * 50)
    
    # Test 1: Two-Stage Chunker Output
    print(f"\n1️⃣ Testing TwoStageChunker with markdown file: {test_file_path}")
    
    chunker = TwoStageChunker(
        chunk_size=200,  # Small chunks for testing
        semantic_threshold=0.7,
        concurrent_agents=2
    )
    
    try:
        result = await chunker.process_document(test_file_path, document_id)
        
        print(f"✅ Chunking complete: {result['chunk_count']} chunks")
        print(f"📁 Source file: {result['source_file_path']}")
        print(f"📄 Chunks file: {result['chunks_file_path']}")
        
        # Verify TextChunk structure
        text_chunks = result['text_chunks']
        
        if text_chunks:
            first_chunk = text_chunks[0]
            required_fields = ["chunk_id", "document_id", "content", "page_number", "chunk_index", "metadata"]
            
            print(f"\n📋 TextChunk Model Verification:")
            for field in required_fields:
                if field in first_chunk:
                    print(f"  ✅ {field}: {type(first_chunk[field]).__name__}")
                else:
                    print(f"  ❌ Missing: {field}")
            
            print(f"  📊 Sample chunk_id: {first_chunk['chunk_id']}")
            print(f"  📊 Content length: {len(first_chunk['content'])}")
            print(f"  📊 Metadata keys: {list(first_chunk['metadata'].keys())}")
        
    except Exception as e:
        print(f"❌ Chunking failed: {e}")
        return
    
    # Test 2: Embeddings Generator Output
    print(f"\n2️⃣ Testing EmbeddingsGenerator ValidatedEmbedding output...")
    
    embedder = EmbeddingsGenerator(
        model_name="BAAI/bge-large-en-v1.5",  # Reliable fallback model
        batch_size=8
    )
    
    try:
        chunks_file_path = result['chunks_file_path']
        
        if Path(chunks_file_path).exists():
            embedding_result = embedder.process_chunks_file(chunks_file_path)
            
            print(f"✅ Embeddings complete: {embedding_result['embeddings_count']} vectors")
            print(f"💾 Embeddings file: {embedding_result['embeddings_file_path']}")
            
            # Verify ValidatedEmbedding structure
            validated_embeddings = embedding_result['validated_embeddings']
            
            if validated_embeddings:
                first_embedding = validated_embeddings[0]
                required_fields = ["chunk_id", "document_id", "embedding_vector", "embedding_model", "chunk_metadata"]
                
                print(f"\n🔍 ValidatedEmbedding Model Verification:")
                for field in required_fields:
                    if field in first_embedding:
                        field_type = type(first_embedding[field]).__name__
                        if field == "embedding_vector":
                            print(f"  ✅ {field}: {field_type} (dim={len(first_embedding[field])})")
                        else:
                            print(f"  ✅ {field}: {field_type}")
                    else:
                        print(f"  ❌ Missing: {field}")
                
                print(f"  📊 Sample embedding_model: {first_embedding['embedding_model']}")
                print(f"  📊 Metadata keys: {list(first_embedding['chunk_metadata'].keys())}")
            
            # Verify ChromaDB format
            chromadb_data = embedding_result['chromadb_ready']
            required_chromadb_fields = ["ids", "embeddings", "metadatas", "documents"]
            
            print(f"\n🗄️ ChromaDB Format Verification:")
            for field in required_chromadb_fields:
                if field in chromadb_data:
                    field_len = len(chromadb_data[field])
                    print(f"  ✅ {field}: {field_len} items")
                else:
                    print(f"  ❌ Missing: {field}")
            
            # Check consistency
            if all(field in chromadb_data for field in required_chromadb_fields):
                lengths = [len(chromadb_data[field]) for field in required_chromadb_fields]
                if len(set(lengths)) == 1:
                    print(f"  ✅ All arrays have consistent length: {lengths[0]}")
                else:
                    print(f"  ⚠️ Inconsistent lengths: {dict(zip(required_chromadb_fields, lengths))}")
        
        else:
            print(f"❌ Chunks file not found: {chunks_file_path}")
            
    except Exception as e:
        print(f"❌ Embeddings generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🎯 Data Model Integration Test Complete")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_data_model_integration())