from pathlib import Path
from typing import Dict, Any

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.backend.doc_processing_system.messaging.producer import ProducerHandler
from src.backend.doc_processing_system.messaging.message_schemas import create_message
from datetime import datetime

from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import (
    duplicate_detection_task,
    docling_processing_task,
    document_saving_task,
)


def get_markdown_path_for_processing(docling_result: Dict[str, Any]) -> str:
    """
    Get the markdown file path from docling processing result.

    Args:
        docling_result: Result from docling processing task

    Returns:
        Path to the markdown file to use for further processing
    """
    return docling_result["processed_markdown_path"]


def send_completion_message(document_id: str, raw_file_path: str, user_id: str, processing_steps: Dict[str, Any], processed_content: str = "") -> None:
    """Send document_pipeline_completed message."""
    try:
        # Create metadata for completion message
        file_path_obj = Path(raw_file_path)
        metadata = {
            "filename": file_path_obj.name,  # Match the field name from document_saving_task
            "document_id": document_id,
            "user_id": user_id,
            "raw_file_path": raw_file_path,
            "processed_content": processed_content,  # Add the missing processed content
            "processing_steps": processing_steps,
            "completed_at": str(datetime.now())
        }
        
        # Send completion message
        kafka_producer = ProducerHandler("localhost:9092")
        message = create_message(event_type="document_pipeline_completed", data=metadata, source="document_processing")
        result = kafka_producer.produce_message(topic="document_pipeline_completed", key=file_path_obj.name, value=message)
        
        if result:
            logger = get_run_logger()
            logger.info(f"✅ Sent document_pipeline_completed message for: {document_id}")
        
        kafka_producer.close()
        
    except Exception as e:
        logger = get_run_logger()
        logger.error(f"Failed to send completion message: {e}")


@flow(
    name="invoice-processing-pipeline",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
    retries=1,
    retry_delay_seconds=10
)
async def document_processing_flow(
    raw_file_path: str,
    user_id: str = "default",
    enable_chunking: bool = True
) -> Dict[str, Any]:
    logger = get_run_logger()
    logger.info(f"🚀 Starting document processing flow for: {Path(raw_file_path).name}")
    
    try:
        duplicate_result = duplicate_detection_task(raw_file_path)
        
        if duplicate_result["status"] == "duplicate":
            return {
                "status": "duplicate",
                "document_id": duplicate_result["document_id"],
                "message": f"Document already exists: {duplicate_result['document_id']}"
            }
        
        if duplicate_result["status"] == "error":
            return duplicate_result
        
        document_id = duplicate_result["document_id"]
        
        logger.info(f"📄 STEP 2: Starting Docling processing for {document_id}")
        docling_result = docling_processing_task(raw_file_path, document_id)
        logger.info(f"✅ STEP 2 COMPLETE: Docling processing - Status: {docling_result.get('status')}")
        if docling_result["status"] != "completed":
            return docling_result

        # Get markdown path for processing
        markdown_path = get_markdown_path_for_processing(docling_result)

        # Read content from the markdown file
        content_path = Path(markdown_path)
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get page count and content length from docling result
        page_count = docling_result["file_info"]["page_count"]
        content_length = len(content)

        # Early return if chunking is disabled
        logger.info(f"🔄 STEP 3: Checking chunking enabled: {enable_chunking}")
        if not enable_chunking:
            logger.info(f"⏭️ STEP 3 SKIPPED: Chunking disabled - preparing early return")

            processing_steps = {
                "duplicate_detection": duplicate_result.get("status"),
                "docling_extraction": docling_result.get("status"),
                "chunking": "disabled",
                "document_saving": "disabled"
            }

            # Send completion message with processed content
            send_completion_message(document_id, raw_file_path, user_id, processing_steps, content)

            return {
                "status": "completed",
                "document_id": document_id,
                "chunking_result": {"status": "disabled", "message": "Chunking disabled"},
                "processing_steps": processing_steps
            }



        logger.info("🔄 STEP 4: Saving document metadata...")
        save_result = document_saving_task(
            vision_enhanced_markdown_path=markdown_path,
            document_id=document_id,
            content_length=content_length,
            page_count=page_count,
            raw_file_path=raw_file_path,
            user_id=user_id
        )
        if save_result.get("save_result", {}).get("status") != "saved":
            return save_result

        processing_steps = {
            "duplicate_detection": duplicate_result.get("status"),
            "docling_extraction": docling_result.get("status"),
            "document_saving": save_result.get("save_result", {}).get("status")
        }

        # Send completion message with processed content
        send_completion_message(document_id, raw_file_path, user_id, processing_steps, content)

        return {
            "status": "completed",
            "document_id": document_id,
            "processing_steps": processing_steps
        }
            
    except Exception as e:
        logger.error(f"❌ Document processing flow failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Document processing flow failed: {e}"
        }


async def process_document_with_flow(
    raw_file_path: str,
    user_id: str = "default",
    enable_chunking: bool = True
) -> Dict[str, Any]:
    return await document_processing_flow(
        raw_file_path,
        user_id,
        enable_chunking
    )

if __name__ == "__main__":
    import asyncio
    test_file_path = "C:\\Users\\User\\Projects\\scaled_processing\\data\\invoices\\batch1-0499.jpg"
    result = asyncio.run(process_document_with_flow(test_file_path, user_id="test_user", enable_chunking=True))
