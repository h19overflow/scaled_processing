"""
Example usage of the migrated Prefect workflow.
Shows how to use the converted LangGraph workflow with Prefect.
"""

import asyncio
from ..core.graph import build_graph, create_initial_state
from ..core.prefect_tasks import structured_extraction_flow
from ..config.settings import Settings


async def run_extraction_example():
    """Example of running the structured extraction pipeline with Prefect."""
    
    # Mock settings (replace with actual settings in real usage)
    class MockSettings:
        class chunking:
            max_tokens = 2048
            overlap_tokens = 200
        class extraction:
            document_type = "research_paper"
        class models:
            discovery_model = "gpt-4"
            config_model = "gpt-4"
            extraction_model = "gpt-4"
    
    settings = MockSettings()
    
    # Sample document
    document_text = """
    Research Paper: Advanced AI Processing
    
    Abstract: This paper presents novel approaches to document processing
    using multi-agent systems and structured extraction techniques.
    
    Authors: Dr. Jane Smith, Dr. John Doe
    Published: 2024
    Conference: AI Research Conference 2024
    
    Introduction:
    The field of document processing has evolved significantly...
    """
    
    document_id = "research_paper_001"
    user_id = "researcher_123"
    
    print("Starting Prefect-based structured extraction pipeline...")
    
    try:
        # Method 1: Use the flow directly
        result = await structured_extraction_flow(document_text, document_id, settings, user_id)
        
        print(f"Pipeline Status: {result.status}")
        print(f"Document processed: {result.document_id}")
        print(f"Chunks created: {len(result.chunks or [])}")
        
        if result.extractions:
            print(f"Extracted {len(result.extractions)} items")
        
        if result.error:
            print(f"Warning: {result.error}")
            
        # Method 2: Use the graph wrapper (maintains backward compatibility)
        print("\nUsing graph wrapper (backward compatibility):")
        flow_func = build_graph(settings)
        result2 = await flow_func(document_text, document_id, user_id)
        
        print(f"Wrapper result status: {result2.status}")
        
    except Exception as e:
        print(f"Pipeline failed: {e}")


if __name__ == "__main__":
    print("Prefect Structured Extraction Pipeline Example")
    print("=" * 50)
    asyncio.run(run_extraction_example())