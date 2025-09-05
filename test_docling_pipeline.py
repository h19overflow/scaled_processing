"""
Test script for the new Docling processing pipeline.
Tests the complete path-based communication flow.
"""

import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_docling_pipeline():
    """Test the complete Docling processing pipeline."""
    
    # Import the flow function
    try:
        from src.backend.doc_processing_system.pipelines.document_processing.flows.document_processing_flow import document_processing_flow
        print("✅ Successfully imported document_processing_flow")
    except ImportError as e:
        print(f"❌ Failed to import document_processing_flow: {e}")
        return
    
    # Test with a sample PDF file (you'll need to provide a real file path)
    test_file_path = "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\raw\\Hamza_CV_Updated.pdf"
    test_file = Path(test_file_path)
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file_path}")
        print("Please provide a valid PDF file path for testing")
        return
    
    print(f"🧪 Testing Docling pipeline with: {test_file.name}")
    print(f"📁 File size: {test_file.stat().st_size / 1024:.1f} KB")
    
    try:
        # Run the complete pipeline
        result = await document_processing_flow(
            raw_file_path=str(test_file),
            user_id="test_user"
        )
        
        print("\n🎉 Pipeline execution completed!")
        print(f"Status: {result.get('status')}")
        
        if result.get('status') == 'completed':
            print(f"✅ Document ID: {result.get('document_id')}")
            print(f"✅ Processed file: {result.get('processed_file_path')}")
            print(f"✅ Content length: {result.get('content_length')}")
            print(f"✅ Page count: {result.get('page_count')}")
        elif result.get('status') == 'duplicate':
            print(f"📋 Document was duplicate: {result.get('document_id')}")
        else:
            print(f"❌ Pipeline failed: {result.get('message')}")
            print(f"❌ Error: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()

def test_docling_processor_only():
    """Test just the DoclingProcessor component."""
    
    try:
        from src.backend.doc_processing_system.pipelines.document_processing.utils.docling_processor import DoclingProcessor
        print("✅ Successfully imported DoclingProcessor")
    except ImportError as e:
        print(f"❌ Failed to import DoclingProcessor: {e}")
        return
    
    # Test file
    test_file_path = "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\raw\\Hamza_CV_Updated.pdf"
    test_file = Path(test_file_path)
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    print(f"🧪 Testing DoclingProcessor with: {test_file.name}")
    
    try:
        processor = DoclingProcessor()
        result = processor.extract_document(
            raw_file_path=str(test_file),
            document_id="test_doc",
            user_id="test_user"
        )
        
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'completed':
            print(f"✅ Markdown path: {result.get('processed_markdown_path')}")
            print(f"✅ Images dir: {result.get('extracted_images_dir')}")
            print(f"✅ File info: {result.get('file_info')}")
        else:
            print(f"❌ Extraction failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ DoclingProcessor test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Testing Docling Pipeline Integration")
    print("=" * 50)
    
    # First test just the DoclingProcessor
    print("\n1. Testing DoclingProcessor component:")
    test_docling_processor_only()
    
    # Then test the complete pipeline
    print("\n2. Testing complete pipeline:")
    asyncio.run(test_docling_pipeline())
    
    print("\n✅ Testing completed!")