"""
Kafka message preparation task for document processing flow.
"""

from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger

from ...utils.document_output_manager import DocumentOutputManager


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