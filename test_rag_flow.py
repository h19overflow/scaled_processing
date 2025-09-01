#!/usr/bin/env python3
"""
Test script for RAG Processing Prefect Flow

Tests the complete pipeline orchestration with retry and timeout logic.
Verifies integration between chunking, embeddings, and storage components.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append('src/backend')

from doc_processing_system.pipelines.rag_processing.flows import rag_processing_flow, process_document_via_rag_pipeline


async def test_rag_flow():
    """Test the complete RAG processing flow."""
    
    print("🧪 Testing RAG Processing Prefect Flow")
    print("=" * 50)
    
    # Test document setup
    test_document_id = "test_flow_doc_001"
    test_file_path = f"data/documents/processed/{test_document_id}.md"
    
    # Create test markdown content
    test_content = """# RAG Pipeline Test Document

## Introduction
This document tests the complete RAG processing pipeline using Prefect orchestration.

The pipeline consists of three coordinated stages:
1. Two-stage chunking with semantic analysis
2. Embeddings generation with validated models 
3. Vector storage preparation for ChromaDB

## Processing Details
Each stage is implemented as a Prefect task with comprehensive error handling.

### Chunking Stage
- Semantic chunking using LangChain integration
- Boundary refinement with concurrent LLM agents
- TextChunk model output for database consistency

### Embeddings Stage  
- Batch processing for efficiency
- ValidatedEmbedding model adherence
- ChromaDB-ready format generation

### Storage Stage
- Currently a placeholder implementation
- Will integrate with ChromaDB in Phase 3
- Maintains data model consistency throughout

## Quality Assurance
The pipeline includes retry logic, timeout protection, and comprehensive logging.
All components output validated data models for seamless integration.

## Conclusion
This test verifies the complete orchestration of the RAG processing pipeline.
"""
    
    # Create test file
    Path(test_file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print(f"📝 Created test document: {test_file_path}")
    print(f"📊 Document length: {len(test_content)} characters")
    
    # Test the flow
    try:
        print(f"\n🚀 Starting RAG processing flow for {test_document_id}")
        
        result = await rag_processing_flow(
            file_path=test_file_path,
            document_id=test_document_id,
            chunk_size=300,  # Smaller chunks for testing
            semantic_threshold=0.7,
            concurrent_agents=3,  # Reduced for testing
            chunking_model="gemini-2.0-flash",
            embedding_model="BAAI/bge-large-en-v1.5",
            batch_size=16
        )
        
        print(f"\n🎯 Flow Execution Results:")
        print(f"Status: {result['pipeline_status']}")
        
        if result['pipeline_status'] == 'success':
            print(f"✅ Pipeline completed successfully!")
            print(f"⏱️ Total time: {result['total_processing_time']}s")
            print(f"📁 Source: {result['source_file_path']}")
            
            # Stage details
            stages = result['stages']
            
            print(f"\n📝 Chunking Results:")
            print(f"   Chunks created: {stages['chunking']['chunk_count']}")
            print(f"   Processing time: {stages['chunking']['processing_time']}s")
            print(f"   Output file: {stages['chunking']['chunks_file_path']}")
            
            print(f"\n🔢 Embeddings Results:")
            print(f"   Vectors generated: {stages['embeddings']['embeddings_count']}")
            print(f"   Processing time: {stages['embeddings']['processing_time']}s")
            print(f"   Model used: {stages['embeddings']['model_used']}")
            print(f"   Output file: {stages['embeddings']['embeddings_file_path']}")
            
            print(f"\n🗄️ Storage Results:")
            print(f"   Status: {stages['storage']['status']}")
            print(f"   Collection: {stages['storage']['collection_name']}")
            print(f"   Note: {stages['storage']['note']}")
            
            # Verify outputs
            chunks_file = Path(stages['chunking']['chunks_file_path'])
            embeddings_file = Path(stages['embeddings']['embeddings_file_path'])
            
            print(f"\n🔍 Output Verification:")
            print(f"   Chunks file exists: {chunks_file.exists()}")
            print(f"   Embeddings file exists: {embeddings_file.exists()}")
            
            if chunks_file.exists():
                print(f"   Chunks file size: {chunks_file.stat().st_size} bytes")
            
            if embeddings_file.exists():
                print(f"   Embeddings file size: {embeddings_file.stat().st_size} bytes")
        
        else:
            print(f"❌ Pipeline failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Error type: {result.get('error_type', 'Unknown')}")
            print(f"Failed at: {result.get('pipeline_failed_at', 'Unknown time')}")
        
    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏁 RAG Flow Test Complete")
    print("=" * 50)


async def test_convenience_function():
    """Test the convenience function for external integration."""
    
    print("\n🔧 Testing Convenience Function")
    print("-" * 30)
    
    test_document_id = "test_convenience_001"
    test_file_path = f"data/documents/processed/{test_document_id}.md"
    
    # Simple test content
    simple_content = """# Simple Test

This is a minimal test for the convenience function.

It should process quickly and demonstrate the pipeline functionality.
"""
    
    Path(test_file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(simple_content)
    
    try:
        result = await process_document_via_rag_pipeline(
            file_path=test_file_path,
            document_id=test_document_id,
            chunk_size=150,
            concurrent_agents=2
        )
        
        print(f"✅ Convenience function result: {result['pipeline_status']}")
        if result['pipeline_status'] == 'success':
            print(f"⏱️ Processing time: {result['total_processing_time']}s")
            print(f"📊 Chunks: {result['stages']['chunking']['chunk_count']}")
        
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_rag_flow())
    asyncio.run(test_convenience_function())