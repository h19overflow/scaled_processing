#!/usr/bin/env python3
"""
Test just the duplicate detection logic without full processing.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.backend.doc_processing_system.pipelines.document_processing.utils.document_output_manager import DocumentOutputManager

def test_duplicate_logic():
    """Test the duplicate check and immediate database save."""
    print("🧪 Testing duplicate detection logic...")
    
    # Initialize output manager
    output_manager = DocumentOutputManager()
    
    # Test file
    test_file = "data/documents/raw/gemini-for-google-workspace-prompting-guide-101.pdf"
    
    # Test the check_and_process_document method
    print(f"📁 Processing: {test_file}")
    result = output_manager.check_and_process_document(test_file, "test_user")
    
    print(f"📊 Result: {result}")
    
    if result["status"] == "ready_for_processing":
        print("✅ Document processed and saved to database")
        print(f"📄 Document ID: {result['document_id']}")
        if "db_document_id" in result:
            print(f"🗃️  Database ID: {result['db_document_id']}")
    elif result["status"] == "duplicate":
        print("✅ Duplicate detected!")
        print(f"📄 Existing Document ID: {result['document_id']}")
    else:
        print(f"❌ Unexpected status: {result['status']}")
    
    # Test again to see if duplicate is now detected
    print("\n🔄 Testing duplicate detection on second run...")
    result2 = output_manager.check_and_process_document(test_file, "test_user")
    print(f"📊 Second Result: {result2}")
    
    if result2["status"] == "duplicate":
        print("✅ Duplicate correctly detected on second run!")
    else:
        print("❌ Duplicate detection failed on second run")

if __name__ == "__main__":
    test_duplicate_logic()