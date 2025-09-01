"""
Prefect flow for document processing with vision AI integration.
Wraps DoclingProcessor operations in a robust, observable workflow.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from ..docling_processor import DoclingProcessor
from ..utils.document_output_manager import DocumentOutputManager


@task(name="duplicate-detection", retries=2)
def duplicate_detection_task(raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Check for duplicate documents using content hash.
    
    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        
    Returns:
        Dict containing duplicate check results
    """
    logger = get_run_logger()
    logger.info(f"🔍 Starting duplicate detection for: {Path(raw_file_path).name}")
    
    try:
        # Initialize processor without vision for fast duplicate check
        processor = DoclingProcessor(enable_vision=False)
        output_manager = processor._get_output_manager()
        
        # Check for duplicates
        result = output_manager.check_and_process_document(raw_file_path, user_id)
        
        if result["status"] == "duplicate":
            logger.info(f"📋 Document is duplicate: {result['document_id']}")
        elif result["status"] == "ready_for_processing":
            logger.info(f"✅ Document is new, ready for processing: {result['document_id']}")
        else:
            logger.warning(f"⚠️ Unexpected status: {result['status']}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ Duplicate detection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Duplicate detection failed: {e}"
        }


@task(name="vision-processing", retries=1)
async def vision_processing_task(
    raw_file_path: str, 
    document_id: str, 
    user_id: str = "default"
) -> Optional[Dict[str, Any]]:
    """
    Process document with AI vision enhancement.
    
    Args:
        raw_file_path: Path to the raw document file
        document_id: Document ID from duplicate check
        user_id: User who uploaded the document
        
    Returns:
        Dict containing processed document results or None if failed
    """
    logger = get_run_logger()
    logger.info(f"👁️ Starting vision processing for document: {document_id}")
    
    try:
        # Initialize processor with vision enabled
        processor = DoclingProcessor(enable_vision=True)
        
        # Process document with vision AI
        parsed_document = await processor.process_document_with_vision(
            raw_file_path, document_id, user_id
        )
        
        logger.info(f"✅ Vision processing completed: {len(parsed_document.content)} chars, {parsed_document.page_count} pages")
        
        return {
            "status": "completed",
            "document_id": document_id,
            "parsed_document": parsed_document,
            "content_length": len(parsed_document.content),
            "page_count": parsed_document.page_count
        }
        
    except Exception as e:
        logger.error(f"❌ Vision processing failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Vision processing failed: {e}"
        }


@task(name="document-saving", retries=2)
def document_saving_task(
    vision_result: Dict[str, Any],
    raw_file_path: str,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Save processed document to structured directory.
    
    Args:
        vision_result: Result from vision processing task
        raw_file_path: Original file path for metadata
        user_id: User who uploaded the document
        
    Returns:
        Dict containing save results and file paths
    """
    logger = get_run_logger()
    
    if vision_result["status"] != "completed":
        logger.error(f"❌ Cannot save document due to vision processing failure: {vision_result.get('error')}")
        return vision_result
    
    document_id = vision_result["document_id"]
    parsed_document = vision_result["parsed_document"]
    
    logger.info(f"💾 Saving processed document: {document_id}")
    
    try:
        # Initialize output manager
        output_manager = DocumentOutputManager()
        
        # Prepare metadata for saving
        file_path_obj = Path(raw_file_path)
        metadata = {
            "filename": file_path_obj.name,
            "page_count": parsed_document.page_count,
            "content_length": len(parsed_document.content),
            "file_type": parsed_document.metadata.file_type,
            "file_size": parsed_document.metadata.file_size,
            "processed_content": parsed_document.content,
            "vision_processing": True,
            "processing_timestamp": datetime.now().isoformat(),
            # Include page mapping for downstream processing
            "page_mapping": getattr(parsed_document, '_page_mapping', {})
        }
        
        # Save processed document
        save_result = output_manager.save_processed_document(
            document_id, parsed_document.content, metadata, user_id
        )
        
        if save_result["status"] == "saved":
            logger.info(f"✅ Document saved successfully: {save_result['processed_file_path']}")
        else:
            logger.error(f"❌ Failed to save document: {save_result.get('error')}")
            
        return {
            **vision_result,
            "save_result": save_result,
            "status": "completed" if save_result["status"] == "saved" else "error",
            "processed_file_path": save_result.get("processed_file_path"),
            "document_directory": save_result.get("document_directory")
        }
        
    except Exception as e:
        logger.error(f"❌ Document saving failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Document saving failed: {e}"
        }


@task(name="kafka-message-preparation", retries=2)
def kafka_message_preparation_task(
    save_result: Dict[str, Any],
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Prepare Kafka messages for downstream pipelines.
    
    Args:
        save_result: Result from document saving task
        user_id: User who uploaded the document
        
    Returns:
        Dict containing prepared Kafka messages
    """
    logger = get_run_logger()
    
    if save_result.get("save_result", {}).get("status") != "saved":
        logger.error(f"❌ Cannot prepare Kafka message due to previous failures")
        return save_result
    
    document_id = save_result["document_id"]
    processed_file_path = save_result["processed_file_path"]
    parsed_document = save_result["parsed_document"]
    
    logger.info(f"📤 Preparing Kafka messages for: {document_id}")
    
    try:
        # Initialize output manager
        output_manager = DocumentOutputManager()
        
        # Prepare metadata for Kafka message
        metadata = {
            "filename": parsed_document.metadata.filename if hasattr(parsed_document.metadata, 'filename') else "unknown",
            "page_count": parsed_document.page_count,
            "content_length": len(parsed_document.content),
            "file_type": parsed_document.metadata.file_type,
            "file_size": parsed_document.metadata.file_size,
            "processing_timestamp": datetime.now().isoformat(),
            "vision_processing": True
        }
        
        # Prepare Kafka message using existing method
        message_result = output_manager.prepare_kafka_message(
            document_id, processed_file_path, metadata, user_id
        )
        
        if message_result.get("status") == "processed":
            logger.info(f"✅ Kafka message prepared successfully for: {document_id}")
            logger.info(f"📨 Message ready for topics: rag, extraction")
        else:
            logger.error(f"❌ Failed to prepare Kafka message: {message_result.get('error')}")
            
        return {
            **save_result,
            "kafka_message_result": message_result,
            "kafka_message": message_result.get("kafka_message")
        }
        
    except Exception as e:
        logger.error(f"❌ Kafka message preparation failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Kafka message preparation failed: {e}"
        }


@flow(
    name="document-processing-pipeline",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
    retries=1,
    retry_delay_seconds=10
)
async def document_processing_flow(
    raw_file_path: str,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Complete document processing workflow with Prefect orchestration.
    
    This flow handles:
    1. Duplicate detection using content hash
    2. Vision AI processing if document is new
    3. Structured document saving
    4. Kafka message preparation for downstream pipelines
    
    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        
    Returns:
        Dict containing complete processing results
    """
    logger = get_run_logger()
    logger.info(f"🚀 Starting document processing flow for: {Path(raw_file_path).name}")
    logger.info(f"👤 User: {user_id}")
    logger.info(f"📁 File path: {raw_file_path}")
    
    try:
        # Step 1: Check for duplicates (fast operation)
        logger.info("🔄 Step 1: Duplicate detection")
        duplicate_result = duplicate_detection_task(raw_file_path, user_id)
        
        # Early exit if duplicate
        if duplicate_result["status"] == "duplicate":
            logger.info(f"📋 Document is duplicate, skipping processing: {duplicate_result['document_id']}")
            return {
                "status": "duplicate",
                "document_id": duplicate_result["document_id"],
                "message": f"Document already exists: {duplicate_result['document_id']}",
                "processing_skipped": True
            }
        
        # Early exit if error
        if duplicate_result["status"] == "error":
            logger.error(f"❌ Duplicate detection failed, aborting flow")
            return duplicate_result
        
        # Step 2: Vision processing (expensive operation)
        document_id = duplicate_result["document_id"]
        logger.info(f"🔄 Step 2: Vision AI processing for: {document_id}")
        vision_result = await vision_processing_task(raw_file_path, document_id, user_id)
        
        if not vision_result or vision_result["status"] != "completed":
            logger.error(f"❌ Vision processing failed, aborting flow")
            return vision_result or {"status": "error", "message": "Vision processing returned None"}
        
        # Step 3: Document saving
        logger.info(f"🔄 Step 3: Saving processed document: {document_id}")
        save_result = document_saving_task(vision_result, raw_file_path, user_id)

        if save_result.get("save_result", {}).get("status") != "saved":
            logger.error(f"❌ Document saving failed, aborting flow")
            return save_result
        
        # Step 4: Kafka message preparation
        logger.info(f"🔄 Step 4: Preparing Kafka messages: {document_id}")
        final_result = kafka_message_preparation_task(save_result, user_id)
        
        # Final status check
        if  final_result.get("kafka_message").get("status") == "processed":
            logger.info(f"✅ Document processing flow completed successfully!")
            logger.info(f"📄 Document ID: {final_result['document_id']}")
            logger.info(f"📁 Processed file: {final_result['processed_file_path']}")
            logger.info(f"📤 Kafka message prepared for downstream pipelines")
            
            return {
                "status": "completed",
                "document_id": final_result["document_id"],
                "processed_file_path": final_result["processed_file_path"],
                "document_directory": final_result["document_directory"],
                "kafka_message": final_result["kafka_message"],
                "content_length": final_result["content_length"],
                "page_count": final_result["page_count"],
                "message": f"Document processing completed: {final_result['document_id']}"
            }
        else:
            logger.error(f"❌ Final step failed or missing Kafka message")
            return final_result
            
    except Exception as e:
        logger.error(f"❌ Document processing flow failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Document processing flow failed: {e}"
        }


# Convenience function for direct flow execution
async def process_document_with_flow(raw_file_path: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Convenience function to run the document processing flow directly.
    
    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        
    Returns:
        Dict containing processing results
    """
    return await document_processing_flow(raw_file_path, user_id)