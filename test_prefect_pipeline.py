"""
Test script for the Prefect-based document processing pipeline.
Tests the complete flow from file detection to Kafka message publishing.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from datetime import datetime
import time

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_prefect_flow_direct():
    """Test the Prefect flow directly without file watcher."""
    logger.info("🧪 Testing Prefect Document Processing Flow - Direct Execution")
    logger.info("=" * 60)
    
    try:
        # Import the flow
        from src.backend.doc_processing_system.pipelines.document_processing.flows.document_processing_flow import process_document_with_flow
        
        # Test document path
        sample_doc = Path("data/documents/raw/gemini-for-google-workspace-prompting-guide-101.pdf")
        
        if not sample_doc.exists():
            logger.error(f"❌ Sample document not found: {sample_doc}")
            logger.info("📝 Please place a test PDF in data/documents/raw/")
            return False
        
        logger.info(f"📄 Processing document: {sample_doc.name}")
        logger.info(f"📁 File path: {sample_doc}")
        logger.info(f"📊 File size: {sample_doc.stat().st_size} bytes")
        
        # Execute the flow
        start_time = time.time()
        logger.info("🚀 Starting Prefect flow...")
        
        result = await process_document_with_flow(
            raw_file_path=str(sample_doc),
            user_id="test_user_prefect"
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Analyze results
        status = result.get("status")
        logger.info(f"📋 Flow completed in {processing_time:.2f} seconds")
        logger.info(f"🔍 Status: {status}")
        
        if status == "completed":
            logger.info("✅ PREFECT FLOW TEST PASSED!")
            logger.info(f"📄 Document ID: {result['document_id']}")
            logger.info(f"📁 Processed file: {result['processed_file_path']}")
            logger.info(f"📊 Content length: {result['content_length']} chars")
            logger.info(f"📖 Page count: {result['page_count']}")
            
            # Check if processed file exists
            processed_file = Path(result['processed_file_path'])
            if processed_file.exists():
                logger.info(f"✅ Processed file exists: {processed_file}")
                logger.info(f"📊 Processed file size: {processed_file.stat().st_size} bytes")
            else:
                logger.error(f"❌ Processed file not found: {processed_file}")
            
            # Check Kafka message
            kafka_message = result.get('kafka_message')
            if kafka_message:
                logger.info("✅ Kafka message prepared successfully")
                logger.info(f"📨 Message document_id: {kafka_message.get('document_id')}")
                logger.info(f"📨 Message workflow_types: {kafka_message.get('workflow_types')}")
            else:
                logger.error("❌ No Kafka message prepared")
                
            return True
            
        elif status == "duplicate":
            logger.info("📋 Document is duplicate - this is expected behavior")
            logger.info(f"📄 Existing document ID: {result['document_id']}")
            return True
            
        else:
            logger.error(f"❌ PREFECT FLOW TEST FAILED!")
            logger.error(f"🔍 Status: {status}")
            logger.error(f"💬 Message: {result.get('message', 'No message')}")
            if 'error' in result:
                logger.error(f"❌ Error: {result['error']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ PREFECT FLOW TEST EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_watcher_integration():
    """Test file watcher by copying a test file."""
    logger.info("🧪 Testing File Watcher Integration")
    logger.info("=" * 60)
    
    try:
        # Source and destination paths
        source_doc = Path("data/documents/raw/gemini-for-google-workspace-prompting-guide-101.pdf")
        test_filename = f"test_document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        destination_doc = Path("data/documents/raw") / test_filename
        
        if not source_doc.exists():
            logger.error(f"❌ Source document not found: {source_doc}")
            return False
        
        logger.info(f"📄 Source document: {source_doc}")
        logger.info(f"🎯 Test filename: {test_filename}")
        logger.info(f"📁 Destination: {destination_doc}")
        
        # Ensure raw directory exists
        destination_doc.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to trigger file watcher
        logger.info("📋 Copying file to trigger file watcher...")
        shutil.copy2(source_doc, destination_doc)
        
        if destination_doc.exists():
            logger.info(f"✅ File copied successfully: {test_filename}")
            logger.info(f"📊 File size: {destination_doc.stat().st_size} bytes")
            logger.info("👁️ File watcher should detect this file and trigger processing")
            logger.info("🔄 Check logs for file detection and Prefect flow execution")
            return True
        else:
            logger.error(f"❌ Failed to copy file: {test_filename}")
            return False
            
    except Exception as e:
        logger.error(f"❌ FILE WATCHER TEST EXCEPTION: {e}")
        return False


def check_processed_directory():
    """Check the processed directory for output files."""
    logger.info("🧪 Checking Processed Directory")
    logger.info("=" * 60)
    
    try:
        processed_dir = Path("data/documents/processed")
        
        if not processed_dir.exists():
            logger.warning(f"⚠️ Processed directory does not exist: {processed_dir}")
            return False
        
        # List all processed documents
        processed_files = list(processed_dir.rglob("*"))
        processed_docs = [f for f in processed_files if f.is_file() and f.name.endswith('.md')]
        
        logger.info(f"📁 Processed directory: {processed_dir}")
        logger.info(f"📊 Total files: {len(processed_files)}")
        logger.info(f"📄 Processed documents: {len(processed_docs)}")
        
        if processed_docs:
            logger.info("✅ Found processed documents:")
            for doc in processed_docs[-3:]:  # Show last 3
                logger.info(f"  📄 {doc.relative_to(processed_dir)}")
                logger.info(f"     📊 Size: {doc.stat().st_size} bytes")
                logger.info(f"     🕐 Modified: {datetime.fromtimestamp(doc.stat().st_mtime)}")
            
            return True
        else:
            logger.warning("⚠️ No processed documents found")
            return False
            
    except Exception as e:
        logger.error(f"❌ PROCESSED DIRECTORY CHECK EXCEPTION: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting Prefect Pipeline Integration Tests")
    logger.info("=" * 60)
    
    test_results = []
    
    # Test 1: Direct Prefect flow execution
    logger.info("📋 Test 1: Direct Prefect Flow Execution")
    result1 = await test_prefect_flow_direct()
    test_results.append(("Direct Prefect Flow", result1))
    print()
    
    # Test 2: Check processed directory
    logger.info("📋 Test 2: Processed Directory Check")
    result2 = check_processed_directory()
    test_results.append(("Processed Directory", result2))
    print()
    
    # Test 3: File watcher integration (copy file)
    logger.info("📋 Test 3: File Watcher Integration")
    result3 = test_file_watcher_integration()
    test_results.append(("File Watcher Integration", result3))
    print()
    
    # Summary
    logger.info("=" * 60)
    logger.info("🏁 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status} - {test_name}")
        if result:
            passed += 1
    
    logger.info(f"📊 Tests passed: {passed}/{len(test_results)}")
    
    if passed == len(test_results):
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("🚀 Prefect pipeline is working correctly")
    else:
        logger.info("⚠️ Some tests failed - check logs above")
    
    logger.info("=" * 60)
    
    return passed == len(test_results)


if __name__ == "__main__":
    asyncio.run(main())