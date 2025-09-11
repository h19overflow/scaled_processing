"""
Debug script to test the extraction issue in isolation.
"""

import asyncio
import logging
from ..config.settings import Settings
from ..models.state import PipelineState
from ..models.document import DocumentChunk
from ..models.schema import FieldSchema, ProgressiveSchema
from .prefect_tasks import extract_data_task

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')


def create_test_state():
    """Create a test state with proper objects."""
    
    # Create test chunks
    chunk = DocumentChunk(
        chunk_id=0,
        text="Test document with author Jane Smith and email jane@example.com",
        start_char=0,
        end_char=50,
        token_count=15
    )
    
    # Create test fields with sample_values
    field1 = FieldSchema(
        field_name="author_name",
        field_type="text",
        description="Author's full name", 
        example_text="Dr. Jane Smith",
        category="personal",
        subcategory="identity"
    )
    
    field2 = FieldSchema(
        field_name="email_address",
        field_type="email",
        description="Contact email",
        example_text="jane.smith@example.com", 
        category="contact",
        subcategory="digital"
    )
    
    # Create progressive schema
    progressive_schema = ProgressiveSchema(
        discovered_fields=[field1, field2],
        document_type="document",
        confidence_level="high",
        chunk_coverage=1
    )
    
    # Create mock config
    config = {
        "prompt": "Extract author and email from document",
        "examples": [{"example": "test"}],
        "model_id": "gpt-4"
    }
    
    # Create longer test document to meet minimum length requirement
    document_text = """
    This is a comprehensive test document for extraction validation.
    
    Author Information:
    - Name: Dr. Jane Smith
    - Email: jane.smith@example.com
    - Institution: AI Research University
    - Title: Senior Research Scientist
    
    Document Details:
    This document contains structured information that should be extractable
    using the configured extraction pipeline. The document includes personal
    information, contact details, and professional credentials that can be
    identified and extracted systematically.
    
    Additional Content:
    The extraction system should be able to identify key fields like names,
    email addresses, institutions, and professional titles from documents
    like this one that contain sufficient context and length.
    """
    
    # Update chunk with longer text
    chunk.text = document_text.strip()
    chunk.end_char = len(document_text)
    chunk.token_count = len(document_text.split())

    # Create pipeline state
    state = PipelineState(
        document_text=document_text.strip(),
        document_id="test_extraction",
        user_id="debug_user",
        chunks=[chunk],
        progressive_results=[progressive_schema],
        config=config,
        status="ready_for_extraction"
    )
    
    return state


async def test_extraction():
    """Test extraction in isolation."""
    
    print("🔧 Testing Extraction in Isolation")
    print("=" * 40)
    
    # Create test state
    state = create_test_state()
    settings = Settings.create_default()
    
    print(f"✅ Test state created:")
    print(f"   - Document: {state.document_text[:50]}...")
    print(f"   - Chunks: {len(state.chunks)}")
    print(f"   - Progressive results: {len(state.progressive_results)}")
    print(f"   - Config: {bool(state.config)}")
    
    # Test types
    print(f"\n🔍 Object Types:")
    print(f"   - State type: {type(state)}")
    print(f"   - Progressive results[0] type: {type(state.progressive_results[0])}")
    print(f"   - Progressive results[0].discovered_fields type: {type(state.progressive_results[0].discovered_fields)}")
    print(f"   - Field[0] type: {type(state.progressive_results[0].discovered_fields[0])}")
    
    # Test extraction
    print(f"\n🚀 Running Extraction Task...")
    
    try:
        result_state = extract_data_task(state, settings)
        
        print(f"✅ Extraction Result:")
        print(f"   - Status: {result_state.status}")
        print(f"   - Error: {result_state.error}")
        print(f"   - Extractions: {len(result_state.extractions or [])}")
        
        if result_state.extractions:
            for i, extraction in enumerate(result_state.extractions):
                print(f"   - Extraction {i}: {extraction}")
                
    except Exception as e:
        print(f"❌ Extraction Failed: {e}")
        import traceback
        traceback.print_exc()
    

if __name__ == "__main__":
    asyncio.run(test_extraction())