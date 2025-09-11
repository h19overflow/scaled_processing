"""
Debug the state conversion process step by step.
"""

import logging
from ..config.settings import Settings
from ..models.state import PipelineState
from ..models.document import DocumentChunk
from ..models.schema import FieldSchema, ProgressiveSchema
from .prefect_tasks import _convert_state_to_langgraph
from ..nodes.extraction import extract_data as original_extract_data

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')


def test_conversion():
    """Test the conversion process in detail."""
    
    print("🔧 Testing State Conversion Process")
    print("=" * 40)
    
    # Create test objects
    field = FieldSchema(
        field_name="test_field",
        field_type="text",
        description="Test field", 
        example_text="Test value",
        category="test",
        subcategory="debug"
    )
    
    progressive_schema = ProgressiveSchema(
        discovered_fields=[field],
        document_type="test_doc",
        confidence_level="high",
        chunk_coverage=1
    )
    
    chunk = DocumentChunk(
        chunk_id=0,
        text="This is a test document with enough text to pass the length validation. " * 3,
        start_char=0,
        end_char=100,
        token_count=20
    )
    
    config = {
        "prompt": "Extract test field",
        "examples": [{"example": "test"}],
        "model_id": "gpt-4"
    }
    
    # Create PipelineState
    state = PipelineState(
        document_text="This is a test document with enough text to pass the length validation. " * 3,
        document_id="debug_conversion",
        user_id="debug_user",
        chunks=[chunk],
        progressive_results=[progressive_schema],
        config=config,
        status="ready"
    )
    
    print(f"✅ Original State Types:")
    print(f"   - State: {type(state)}")
    print(f"   - Progressive results[0]: {type(state.progressive_results[0])}")
    print(f"   - Discovered fields[0]: {type(state.progressive_results[0].discovered_fields[0])}")
    print(f"   - Has attribute 'discovered_fields': {hasattr(state.progressive_results[0], 'discovered_fields')}")
    
    # Test conversion
    print(f"\n🔄 Converting State...")
    langgraph_state = _convert_state_to_langgraph(state)
    
    print(f"✅ Converted State Types:")
    print(f"   - LangGraph state: {type(langgraph_state)}")
    print(f"   - Progressive results: {type(langgraph_state.get('progressive_results'))}")
    if langgraph_state.get('progressive_results'):
        print(f"   - Progressive results[0]: {type(langgraph_state['progressive_results'][0])}")
        result = langgraph_state['progressive_results'][0]
        print(f"   - Has attribute 'discovered_fields': {hasattr(result, 'discovered_fields')}")
        if hasattr(result, 'discovered_fields'):
            print(f"   - Discovered fields[0]: {type(result.discovered_fields[0])}")
        elif isinstance(result, dict) and 'discovered_fields' in result:
            print(f"   - Dict discovered fields[0]: {type(result['discovered_fields'][0])}")
    
    # Test extraction with converted state
    print(f"\n🚀 Testing Extraction with Converted State...")
    settings = Settings.create_default()
    
    try:
        result = original_extract_data(langgraph_state, settings)
        print(f"✅ Extraction function returned!")
        print(f"   - Result type: {type(result)}")
        print(f"   - Result: {result}")
        
        if result:
            print(f"   - Status: {result.get('status')}")
            extractions = result.get('extractions', [])
            if extractions is not None:
                print(f"   - Extractions: {len(extractions)}")
                for i, extraction in enumerate(extractions):
                    print(f"   - Extraction {i}: {extraction}")
            else:
                print(f"   - Extractions: None")
                
            if result.get('error'):
                print(f"   - Error: {result['error']}")
        else:
            print("   - Result is None or empty")
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_conversion()