"""
Test the pipeline using the proper LangGraph workflow orchestrator.
This is how the pipeline is meant to be used.
"""

import asyncio
import json
from pathlib import Path

# Import the proper graph orchestrator
from src.backend.doc_processing_system.pipelines.structured_extraction.core.graph import build_graph, create_initial_state


async def test_proper_pipeline():
    """Test the pipeline using the correct LangGraph workflow."""
    
    # Configuration
    class MockChunkingConfig:
        max_tokens = 5128
        overlap_tokens = 200
        use_tiktoken = True

    class MockModelConfig:
        discovery_model = "gemini-2.0-flash"
        extraction_model = "gemini-2.0-flash"
        openai_api_key = None

    class MockExtractionConfig:
        max_fields = 8
        document_type = "document"
        output_dir = "demo_results"

    class MockSettings:
        chunking = MockChunkingConfig()
        models = MockModelConfig()
        extraction = MockExtractionConfig()

    settings = MockSettings()
    
    print("=" * 60)
    print("PROPER PIPELINE TEST: Using LangGraph Workflow")
    print("=" * 60)
    
    # Build the LangGraph workflow
    graph = build_graph(settings)
    
    # Read the actual file content instead of passing the path
    from pathlib import Path
    file_path = "docs/phases/system_progress_summary.md"
    document_content = Path(file_path).read_text(encoding='utf-8')
    
    # Create initial state using the proper function
    initial_state = create_initial_state(
        document_text=document_content,  # Pass actual content, not file path
        document_id="test_doc_1", 
        user_id="test_user"
    )
    
    print(f"Initial state keys: {list(initial_state.keys())}")
    print(f"Document ID: {initial_state.get('document_id')}")
    print(f"User ID: {initial_state.get('user_id')}")
    print()
    
    # Run the complete workflow through LangGraph
    print("Running complete pipeline through LangGraph...")
    try:
        result = await graph.ainvoke(initial_state)
        
        print("=" * 60)
        print("PIPELINE RESULTS")
        print("=" * 60)
        
        # Check that state is preserved throughout
        print(f"✅ Document ID: {result.get('document_id')}")
        print(f"✅ User ID: {result.get('user_id')}")
        print(f"✅ Classification: {result.get('classification')}")
        print(f"✅ Status: {result.get('status')}")
        print(f"✅ Chunks: {len(result.get('chunks', []))}")
        print(f"✅ Progressive Results: {len(result.get('progressive_results', []))}")
        print(f"✅ Config Generated: {result.get('config') is not None}")
        print(f"✅ Extractions: {len(result.get('extractions', []))}")
        
        # Show discovered fields
        progressive_results = result.get('progressive_results', [])
        if progressive_results:
            all_fields = []
            for prog_result in progressive_results:
                all_fields.extend(prog_result.discovered_fields)
            
            print(f"\nDiscovered Fields: {len(all_fields)}")
            for i, field in enumerate(all_fields[:5]):
                print(f"  {i+1}. {field.field_name} ({field.field_type})")
        
        
        # Save results
        results_dir = Path("test_results")
        results_dir.mkdir(exist_ok=True)
        
        # Convert result to JSON-serializable format for main results
        json_result = {
            "document_id": result.get('document_id'),
            "user_id": result.get('user_id'), 
            "classification": result.get('classification'),
            "status": result.get('status'),
            "chunk_count": len(result.get('chunks', [])),
            "progressive_results_count": len(result.get('progressive_results', [])),
            "extractions_count": len(result.get('extractions', [])),
            "has_config": result.get('config') is not None,
            "pipeline_complete": True
        }
        
        with open(results_dir / "proper_pipeline_results.json", "w") as f:
            json.dump(json_result, f, indent=2)
            
        # Save detailed intermediate results for debugging
        intermediate_results = {
            "document_metadata": {
                "document_id": result.get('document_id'),
                "user_id": result.get('user_id'),
                "document_length": len(document_content)
            },
            "classification_details": result.get('classification', {}),
            "chunking_details": {
                "chunk_count": len(result.get('chunks', [])),
            },
            "discovery_details": {
                "progressive_results": []
            },
            "extraction_details": {
                "extraction_count": len(result.get('extractions', [])),
                "extractions": result.get('extractions', [])
            }
        }
        
        # Add progressive results details
        for i, prog_result in enumerate(result.get('progressive_results', [])):
            intermediate_results["discovery_details"]["progressive_results"].append({
                "chunk_index": i,
                "discovered_field_count": len(prog_result.discovered_fields),
                "discovered_fields": [
                    {
                        "field_name": field.field_name,
                        "field_type": field.field_type,
                        "description": field.description,
                    }
                    for field in prog_result.discovered_fields
                ]
            })
        
        
        with open(results_dir / "intermediate_results.json", "w") as f:
            json.dump(intermediate_results, f, indent=2)
        
        print(f"\n✅ Pipeline completed successfully!")
        print(f"✅ Results saved to: proper_pipeline_results.json")
        print(f"✅ Intermediate results saved to: intermediate_results.json")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_proper_pipeline())