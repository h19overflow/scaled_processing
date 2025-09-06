from pathlib import Path
from typing import Dict, Any

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from .tasks import (
    duplicate_detection_task,
    docling_processing_task,
    document_saving_task,
    kafka_message_preparation_task,
    chonkie_chunking_task,
    weaviate_storage_task
)
from .tasks.vision_enriching_task import markdown_vision_task

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
    weaviate_collection: str = "rag_documents"
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
        
        docling_result = docling_processing_task(raw_file_path, document_id, user_id)
        if docling_result["status"] != "completed":
            return docling_result
        
        vision_result = await markdown_vision_task(
            processed_markdown_path=docling_result["processed_markdown_path"],
            extracted_images_dir=docling_result["extracted_images_dir"],
            document_id=document_id,
            file_info=docling_result["file_info"],
            user_id=user_id
        )
        if vision_result["status"] != "completed":
            return vision_result

        vision_enhanced_path = Path(vision_result["vision_enhanced_markdown_path"])
        with open(vision_enhanced_path, 'r', encoding='utf-8') as f:
            enhanced_content = f.read()

        chunking_result = chonkie_chunking_task(
            text_content=enhanced_content,
            document_id=document_id,
            page_count=vision_result["page_count"],
            raw_file_path=raw_file_path
        )
        if chunking_result["status"] != "completed":
            return chunking_result

        save_result = document_saving_task(
            vision_enhanced_markdown_path=vision_result["vision_enhanced_markdown_path"],
            document_id=document_id,
            content_length=vision_result["content_length"], 
            page_count=vision_result["page_count"],
            raw_file_path=raw_file_path,
            user_id=user_id
        )
        if save_result.get("save_result", {}).get("status") != "saved":
            return save_result

        kafka_result = kafka_message_preparation_task(save_result, user_id)
        if kafka_result.get("kafka_message", {}).get("status") != "processed":
            return kafka_result

        weaviate_result = None
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
            "processed_file_path": kafka_result["processed_file_path"],
            "document_directory": kafka_result["document_directory"],
            "kafka_message": kafka_result["kafka_message"],
            "content_length": kafka_result["content_length"],
            "page_count": kafka_result["page_count"],
            "chunking_result": chunking_result,
            "weaviate_storage": weaviate_result,
            "processing_steps": {
                "duplicate_detection": duplicate_result.get("status"),
                "docling_extraction": docling_result.get("status"),
                "vision_enhancement": vision_result.get("status"),
                "chunking": chunking_result.get("status"),
                "document_saving": save_result.get("save_result", {}).get("status"),
                "kafka_preparation": kafka_result.get("kafka_message", {}).get("status"),
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
    weaviate_collection: str = "rag_documents"
) -> Dict[str, Any]:
    return await document_processing_flow(
        raw_file_path, 
        user_id, 
        enable_weaviate_storage, 
        weaviate_collection
    )

if __name__ == "__main__":
    import asyncio
    test_file_path = "C:\\Users\\User\\Projects\\scaled_processing\\data\\documents\\raw\\Hamza_CV_Updated.pdf"
    result = asyncio.run(process_document_with_flow(test_file_path, user_id="test_user", enable_weaviate_storage=True))
    print(result)