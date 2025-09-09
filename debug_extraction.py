"""
Debug the extraction step to see what's failing.
"""

import asyncio
from pathlib import Path

# Import the proper graph orchestrator
from src.backend.doc_processing_system.pipelines.structured_extraction.core.graph import build_graph, create_initial_state


async def debug_extraction():
    """Debug what's failing in the extraction step."""
    
    # Configuration
    class MockChunkingConfig:
        max_tokens = 5128
        overlap_tokens = 200
        use_tiktoken = True

    class MockModelConfig:
        discovery_model = "gemini-2.0-flash"
        consolidation_model = "gemini-2.0-flash"  
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
    
    # Build the LangGraph workflow
    graph = build_graph(settings)
    
    # Read the actual file content instead of passing the path
    from pathlib import Path
    file_path = "docs/phases/system_progress_summary.md"
    document_content = Path(file_path).read_text(encoding='utf-8')
    
    # Create initial state with actual content
    initial_state = create_initial_state(
        document_text=document_content,  # Pass actual content, not file path
        document_id="test_doc_1", 
        user_id="test_user"
    )
    
    print("=" * 60)
    print("DEBUGGING EXTRACTION FAILURE")
    print("=" * 60)
    
    try:
        # Run the pipeline
        result = await graph.ainvoke(initial_state)
        
        # Debug each step
        print("STEP RESULTS:")
        print("-" * 40)
        print(f"Document ID: {result.get('document_id')}")
        print(f"Classification: {result.get('classification')}")
        print(f"Chunks: {len(result.get('chunks', []))}")
        print(f"Progressive Results: {len(result.get('progressive_results', []))}")
        print(f"Has Consolidated Schema: {result.get('consolidated_schema') is not None}")
        print(f"Has Final Schema: {result.get('final_schema') is not None}")
        print(f"Has Config: {result.get('config') is not None}")
        print(f"Final Status: {result.get('status')}")
        print(f"Error: {result.get('error')}")
        print()
        
        # Check document text
        doc_text = result.get('document_text', '')
        if isinstance(doc_text, str) and doc_text.startswith('docs/'):
            # It's still a file path, not the actual text content
            print("❌ PROBLEM: document_text is still a file path, not content!")
            print(f"   document_text: {doc_text}")
            
            # Try to read the file
            try:
                actual_text = Path(doc_text).read_text()
                print(f"✅ File content length: {len(actual_text)} characters")
                print(f"✅ File preview: {actual_text[:200]}...")
            except Exception as e:
                print(f"❌ Could not read file: {e}")
        else:
            print(f"✅ Document text length: {len(doc_text)} characters")
        
        # Check config
        config = result.get('config')
        if config:
            print("\nCONFIG DEBUG:")
            print(f"  Has prompt: {bool(config.get('prompt'))}")
            print(f"  Has examples: {bool(config.get('examples'))}")
            print(f"  Examples count: {len(config.get('examples', []))}")
            print(f"  Model ID: {config.get('model_id')}")
            
            if config.get('examples'):
                example = config['examples'][0]
                print(f"  Example text length: {len(example.text) if hasattr(example, 'text') else 'No text attr'}")
                print(f"  Example extractions: {len(example.extractions) if hasattr(example, 'extractions') else 'No extractions attr'}")
        else:
            print("\n❌ No config generated!")
            
        # Check final schema
        final_schema = result.get('final_schema')
        if final_schema:
            print(f"\nFINAL SCHEMA DEBUG:")
            print(f"  Document type: {final_schema.document_type}")
            print(f"  Extraction classes count: {len(final_schema.extraction_classes)}")
            print(f"  Extraction prompt length: {len(final_schema.extraction_prompt)}")
            
            for i, field in enumerate(final_schema.extraction_classes[:3]):
                print(f"  Field {i+1}: {field.field_name} ({field.field_type})")
        else:
            print("\n❌ No final schema!")
            
    except Exception as e:
        print(f"❌ Pipeline failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_extraction())