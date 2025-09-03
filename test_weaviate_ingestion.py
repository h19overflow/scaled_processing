#!/usr/bin/env python3
"""Test script for Weaviate ingestion."""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.backend.doc_processing_system.pipelines.rag_processing.flows.tasks.vector_storage_task import store_vectors_task

async def test_ingestion():
    """Test the Weaviate ingestion with the L40S embeddings file."""
    print("🚀 Testing Weaviate ingestion...")
    
    embeddings_file = "data/rag/embeddings/embeddings_L40S-GPU-Stress-Test-Results.json"
    collection_name = "test_rag_documents"
    
    # Check if file exists
    if not os.path.exists(embeddings_file):
        print(f"❌ Embeddings file not found: {embeddings_file}")
        return False
    
    print(f"📁 Using file: {embeddings_file}")
    print(f"🗄️ Target collection: {collection_name}")
    
    try:
        # Call the storage task
        result = await store_vectors_task(
            embeddings_file_path=embeddings_file,
            collection_name=collection_name
        )
        
        print(f"📊 Result: {result}")
        
        if result.get("storage_status") == "success":
            print("✅ Ingestion test PASSED!")
            return True
        else:
            print("❌ Ingestion test FAILED!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ingestion())
    sys.exit(0 if success else 1)