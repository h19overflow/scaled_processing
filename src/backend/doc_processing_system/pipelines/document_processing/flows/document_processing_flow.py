"""
Prefect flow for document processing with vision AI integration.
Wraps DoclingProcessor operations in a robust, observable workflow.
"""

from pathlib import Path
from typing import Dict, Any

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from .tasks import (
    duplicate_detection_task,
    docling_processing_task,
    chunking_task,
    document_saving_task,
    kafka_message_preparation_task
)


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
    2. Docling extraction (markdown + images) if document is new
    3. Vision enhancement and chunking processing
    4. Structured document saving
    5. Kafka message preparation for downstream pipelines
    
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
        
        # Step 2: Docling extraction (extract rich markdown + images)
        document_id = duplicate_result["document_id"]
        logger.info(f"🔄 Step 2: Docling extraction for: {document_id}")
        docling_result = docling_processing_task(raw_file_path, document_id, user_id)
        
        if not docling_result or docling_result["status"] != "completed":
            logger.error(f"❌ Docling extraction failed, aborting flow")
            return docling_result or {"status": "error", "message": "Docling extraction returned None"}
        
        # Step 3: Vision enhancement and chunking (process extracted content)
        logger.info(f"🔄 Step 3: Vision enhancement and chunking for: {document_id}")
        vision_result = await chunking_task(
            processed_markdown_path=docling_result["processed_markdown_path"],
            extracted_images_dir=docling_result["extracted_images_dir"],
            document_id=document_id,
            file_info=docling_result["file_info"],
            user_id=user_id
        )
        
        if not vision_result or vision_result["status"] != "completed":
            logger.error(f"❌ Vision enhancement failed, aborting flow")
            return vision_result or {"status": "error", "message": "Vision enhancement returned None"}
        
        # Step 4: Document saving  
        logger.info(f"🔄 Step 4: Saving processed document: {document_id}")
        save_result = document_saving_task(
            vision_enhanced_markdown_path=vision_result["vision_enhanced_markdown_path"],
            document_id=document_id,
            content_length=vision_result["content_length"], 
            page_count=vision_result["page_count"],
            raw_file_path=raw_file_path,
            user_id=user_id
        )

        if save_result.get("save_result", {}).get("status") != "saved":
            logger.error(f"❌ Document saving failed, aborting flow")
            return save_result
        
        # Step 5: Kafka message preparation
        logger.info(f"🔄 Step 5: Preparing Kafka messages: {document_id}")
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