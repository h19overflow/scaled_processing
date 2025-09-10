"""
Test script for the converted Prefect workflow.
Validates that the migration from LangGraph to Prefect works correctly.
"""

import asyncio
import logging
from pathlib import Path

from ..config.settings import Settings
from .prefect_tasks import structured_extraction_flow, create_initial_state
from .graph import build_graph, create_flow


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_test_settings():
    """Create actual Settings instance for testing."""
    return Settings.create_default()


async def test_direct_flow():
    """Test the Prefect flow directly."""
    print("Testing direct Prefect flow...")
    
    settings = create_test_settings()
    
    # Test with simple text
    document_text = """
    This is a test document for validating the Prefect workflow conversion.
    
    The document contains some sample content that should be processed through
    the pipeline steps: classification, context loading, preference injection,
    chunking, discovery, config generation, and extraction.
    
    Key information:
    - Author: Test Author
    - Title: Test Document
    - Year: 2024
    - Category: Testing
    """
    
    document_id = "test_prefect_migration"
    user_id = "test_user"
    
    try:
        result = await structured_extraction_flow(document_text, document_id, settings, user_id)
        
        print(f"Flow completed with status: {result.status}")
        print(f"Document ID: {result.document_id}")
        print(f"User ID: {result.user_id}")
        print(f"Chunks created: {len(result.chunks or [])}")
        print(f"Progressive results: {len(result.progressive_results or [])}")
        print(f"Final extractions: {len(result.extractions or [])}")
        
        if result.error:
            print(f"Error encountered: {result.error}")
        else:
            print("Flow completed successfully!")
            
        return result
        
    except Exception as e:
        print(f"Flow failed with exception: {e}")
        return None


async def test_graph_wrapper():
    """Test the graph wrapper function."""
    print("\nTesting graph wrapper...")
    
    settings = create_test_settings()
    flow_func = build_graph(settings)
    
    document_text = "Simple test document for wrapper validation."
    document_id = "test_wrapper"
    
    try:
        result = await flow_func(document_text, document_id)
        print(f"Wrapper completed with status: {result.status}")
        return result
        
    except Exception as e:
        print(f"Wrapper failed with exception: {e}")
        return None


def test_initial_state():
    """Test initial state creation."""
    print("\nTesting initial state creation...")
    
    try:
        state = create_initial_state("test", "test_id", "test_user")
        print(f"Initial state created successfully:")
        print(f"  Document ID: {state.document_id}")
        print(f"  User ID: {state.user_id}")
        print(f"  Status: {state.status}")
        print(f"  Error: {state.error}")
        return True
        
    except Exception as e:
        print(f"Initial state creation failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("Starting Prefect workflow migration tests...\n")
    
    # Test 1: Initial state
    state_test = test_initial_state()
    
    # Test 2: Direct flow (may fail due to missing services, but should show structure)
    flow_result = await test_direct_flow()
    
    # Test 3: Graph wrapper
    wrapper_result = await test_graph_wrapper()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Initial State Creation: {'✓ PASS' if state_test else '✗ FAIL'}")
    print(f"Direct Flow Test: {'✓ PASS' if flow_result and flow_result.status else '✗ FAIL'}")
    print(f"Graph Wrapper Test: {'✓ PASS' if wrapper_result and wrapper_result.status else '✗ FAIL'}")
    
    if flow_result:
        print(f"\nFlow Status: {flow_result.status}")
        if flow_result.error:
            print(f"Flow Error: {flow_result.error}")


if __name__ == "__main__":
    asyncio.run(main())