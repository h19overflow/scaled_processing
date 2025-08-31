"""
Simple vision processing test - extract document with AI vision enhancement.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Simple logging setup
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def process_document_with_vision():
    """Process document with complete workflow: duplicate check, processing, saving, message prep."""
    # Import required modules
    from src.backend.doc_processing_system.pipelines.document_processing.docling_processor import DoclingProcessor
    
    # Initialize processor with vision enabled
    processor = DoclingProcessor(enable_vision=True)
    
    # Process the sample document
    sample_doc = Path("data/documents/raw/gemini-for-google-workspace-prompting-guide-101.pdf")
    
    if not sample_doc.exists():
        logger.error(f"Sample document not found: {sample_doc}")
        return None
    
    logger.info(f"Processing with complete workflow: {sample_doc.name}")
    
    # Use the new complete workflow with duplicate checking, saving, and message preparation
    result = await processor.process_document_with_duplicate_check(
        str(sample_doc), 
        "test_user"
    )
    
    if result["status"] == "completed":
        logger.info(f"✅ Complete workflow finished: {result['document_id']}")
        logger.info(f"📁 Saved to: {result['processed_file_path']}")
        logger.info(f"📤 Kafka message prepared: {bool(result.get('kafka_message'))}")
        return result
    elif result["status"] == "duplicate":
        logger.info(f"📋 Document is duplicate: {result['document_id']}")
        return result
    else:
        logger.error(f"❌ Processing failed: {result.get('message', 'Unknown error')}")
        return None
# DocumentOutputManager now handles all saving - no need for separate save function
async def main():
    """Main function - process document with complete workflow."""
    logger.info("🚀 Vision Processing Test - Complete Workflow")
    
    try:
        # Process document with complete workflow (duplicate check, processing, saving, message prep)
        result = await process_document_with_vision()
        
        if result and result.get("status") in ["completed", "duplicate"]:
            if result["status"] == "completed":
                logger.info(f"📂 Document Directory: {result['document_directory']}")
                if result.get("kafka_message"):
                    logger.info(f"📨 Kafka Message Ready: document_id={result['kafka_message']['document_id']}")
                logger.info("✅ Complete workflow finished successfully!")
            elif result["status"] == "duplicate":
                logger.info("✅ Duplicate detected - no reprocessing needed!")
        else:
            logger.error("❌ Processing workflow failed")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
if __name__ == "__main__":
    asyncio.run(main())