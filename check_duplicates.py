#!/usr/bin/env python3
"""
Check if duplicate detection is working properly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.backend.doc_processing_system.core_deps.database.CRUD.document_crud import DocumentCRUD
from src.backend.doc_processing_system.core_deps.database.connection_manager import ConnectionManager

def check_duplicates():
    """Check duplicate detection for the test file."""
    print("🔍 Checking duplicate detection...")
    
    # Test file path
    test_file = "data/documents/raw/gemini-for-google-workspace-prompting-guide-101.pdf"
    
    try:
        # Initialize database components
        connection_manager = ConnectionManager()
        document_crud = DocumentCRUD(connection_manager)
        
        # Generate file hash
        print(f"📁 File: {test_file}")
        file_hash = document_crud.generate_file_hash(test_file)
        print(f"🔢 File hash: {file_hash}")
        
        # Check if document exists
        existing_doc = document_crud.get_by_hash(file_hash)
        if existing_doc:
            print(f"✅ Document found in database: {existing_doc.get_id()}")
            print(f"   Filename: {existing_doc.filename}")
            print(f"   Status: {existing_doc.processing_status}")
            print(f"   User: {existing_doc.user_id}")
        else:
            print("❌ Document NOT found in database")
        
        # Test duplicate check method
        is_duplicate, doc_id = document_crud.check_duplicate_by_raw_file(test_file)
        print(f"🔄 Duplicate check result: is_duplicate={is_duplicate}, doc_id={doc_id}")
        
        return is_duplicate
        
    except Exception as e:
        print(f"❌ Error checking duplicates: {e}")
        return False

if __name__ == "__main__":
    check_duplicates()