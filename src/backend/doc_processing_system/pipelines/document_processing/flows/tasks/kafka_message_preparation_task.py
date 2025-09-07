"""
Kafka message preparation task for document processing flow.
"""

from typing import Dict, Any
from datetime import datetime

from prefect import task, get_run_logger

from src.backend.doc_processing_system.messaging.document_processing.kafka_handler import KafkaHandler

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
    
    logger.info(f"📤 Preparing Kafka messages for: {document_id}")
    
    try:
        # Initialize Kafka handler
        kafka_handler = KafkaHandler()
        
        # Send document ready event
        document_ready_success = kafka_handler.send_document_ready(
            document_id=document_id,
            file_path=processed_file_path,
            user_id=user_id
        )
        
        # Send workflow initialized event
        workflow_ready_success = kafka_handler.send_workflow_ready(
            document_id=document_id,
            workflow_types=["rag", "extraction"]
        )
        
        if document_ready_success and workflow_ready_success:
            logger.info(f"✅ Kafka messages sent successfully for: {document_id}")
            logger.info(f"📨 Messages sent to: document-available, workflow-initialized")
            
            message_result = {
                "status": "sent",
                "document_ready": document_ready_success,
                "workflow_ready": workflow_ready_success,
                "topics": ["document-available", "workflow-initialized"]
            }
        else:
            logger.error(f"❌ Failed to send some Kafka messages for: {document_id}")
            message_result = {
                "status": "partial_failure",
                "document_ready": document_ready_success,
                "workflow_ready": workflow_ready_success,
                "error": "Some messages failed to send"
            }
            
        return {
            **save_result,
            "kafka_message_result": message_result,
            "kafka_messages_sent": message_result.get("status") == "sent"
        }
        
    except Exception as e:
        logger.error(f"❌ Kafka message preparation failed for {document_id}: {e}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "message": f"Kafka message preparation failed: {e}"
        }