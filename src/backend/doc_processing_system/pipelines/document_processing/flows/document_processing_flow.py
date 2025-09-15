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
    chonkie_chunking_task,
    weaviate_storage_task
)
from src.backend.doc_processing_system.pipelines.document_processing.tasks_core import markdown_vision_task


def get_markdown_path_for_processing(docling_result: Dict[str, Any], vision_result: Dict[str, Any] = None, enable_vision: bool = True) -> str:
    """
    Get the correct markdown file path based on vision enhancement setting.
    
    Args:
        docling_result: Result from docling processing task
        vision_result: Result from vision enhancement task (optional)
        enable_vision: Whether vision enhancement is enabled
        
    Returns:
        Path to the markdown file to use for further processing
    """
    if enable_vision and vision_result and vision_result.get("status") == "completed":
        return vision_result["vision_enhanced_markdown_path"]
    else:
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
    name="document-processing-pipeline",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
    retries=1,
    retry_delay_seconds=10
)
async def document_processing_flow(
    raw_file_path: str,
    user_id: str = "default",
    enable_weaviate_storage: bool = True,
    weaviate_collection: str = "rag_documents",
    enable_vision_enhancement: bool = True,
    enable_chunking: bool = True
) -> Dict[str, Any]:
    logger = get_run_logger()
    logger.info(f"🚀 Starting document processing flow for: {Path(raw_file_path).name}")
    
    try:
        duplicate_result = duplicate_detection_task(raw_file_path, user_id)
        
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
        
        # Vision enhancement (optional)
        vision_result = None
        if enable_vision_enhancement:
            logger.info(f"👁️ STEP 3: Starting vision enhancement for {document_id}")
            vision_result = await markdown_vision_task(
                processed_markdown_path=docling_result["processed_markdown_path"],
                document_id=document_id,
                file_info=docling_result["file_info"]
            )
            logger.info(f"✅ STEP 3 COMPLETE: Vision enhancement - Status: {vision_result.get('status') if vision_result else 'None'}")
            if vision_result["status"] != "completed":
                return vision_result
        else:
            logger.info(f"⏭️ STEP 3 SKIPPED: Vision enhancement disabled")

        # Early return if chunking is disabled
        logger.info(f"🔄 STEP 4: Checking chunking enabled: {enable_chunking}")
        if not enable_chunking:
            logger.info(f"⏭️ STEP 4 SKIPPED: Chunking disabled - preparing early return")
            # Get the processed content from the docling result
            markdown_path = get_markdown_path_for_processing(docling_result, vision_result, enable_vision_enhancement)
            content_path = Path(markdown_path)
            with open(content_path, 'r', encoding='utf-8') as f:
                processed_content = f.read()

            processing_steps = {
                "duplicate_detection": duplicate_result.get("status"),
                "docling_extraction": docling_result.get("status"),
                "vision_enhancement": vision_result.get("status") if vision_result else "disabled",
                "chunking": "disabled",
                "document_saving": "disabled",
                "weaviate_storage": "disabled"
            }

            # Send completion message with processed content
            send_completion_message(document_id, raw_file_path, user_id, processing_steps, processed_content)
            
            return {
                "status": "completed",
                "document_id": document_id,
                "chunking_result": {"status": "disabled", "message": "Chunking disabled"},
                "weaviate_storage": {"status": "disabled", "message": "Weaviate storage disabled (chunking disabled)"},
                "processing_steps": processing_steps
            }

        # Get correct markdown path for processing
        markdown_path = get_markdown_path_for_processing(docling_result, vision_result, enable_vision_enhancement)
        
        # Read content from the selected markdown file
        content_path = Path(markdown_path)
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Use appropriate page count and content length
        if enable_vision_enhancement and vision_result:
            page_count = vision_result["page_count"]
            content_length = vision_result["content_length"]
        else:
            page_count = docling_result["file_info"]["page_count"]
            content_length = len(content)

        logger.info("🔄 Chunking enabled - processing text into chunks...")
        chunking_result = chonkie_chunking_task(
            text_content=content,
            document_id=document_id,
            page_count=page_count,
            raw_file_path=raw_file_path
        )
        if chunking_result["status"] != "completed":
            return chunking_result

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


        if enable_weaviate_storage and chunking_result.get("embedded_chunks"):
            weaviate_result = weaviate_storage_task(
                embedded_chunks=chunking_result["embedded_chunks"],
                document_id=document_id,
                collection_name=weaviate_collection,
                user_id=user_id
            )
        else:
            weaviate_result = {
                "status": "skipped" if enable_weaviate_storage else "disabled",
                "message": "No embedded chunks available" if enable_weaviate_storage else "Weaviate storage disabled"
            }

        return {
            "status": "completed",
            "document_id": document_id,
            "chunking_result": chunking_result,
            "weaviate_storage": weaviate_result,
            "processing_steps": {
                "duplicate_detection": duplicate_result.get("status"),
                "docling_extraction": docling_result.get("status"),
                "vision_enhancement": vision_result.get("status") if vision_result else "disabled",
                "chunking": chunking_result.get("status"),
                "document_saving": save_result.get("save_result", {}).get("status"),
                "weaviate_storage": weaviate_result.get("status")
            }
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
    enable_weaviate_storage: bool = True,
    weaviate_collection: str = "rag_documents",
    enable_vision_enhancement: bool = True,
    enable_chunking: bool = True
) -> Dict[str, Any]:
    return await document_processing_flow(
        raw_file_path, 
        user_id, 
        enable_weaviate_storage, 
        weaviate_collection,
        enable_vision_enhancement,
        enable_chunking
    )

if __name__ == "__main__":
    import asyncio
    test_file_path = "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\raw\\Covering Letter - AHMED HAMZA KHALED MAHMOUD .pdf"
    result = asyncio.run(process_document_with_flow(test_file_path, user_id="test_user", enable_weaviate_storage=True))
