"""
Prefect flow for document processing with vision AI integration.
Wraps DoclingProcessor operations in a robust, observable workflow.
"""

from pathlib import Path
from typing import Dict, Any

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.backend.doc_processing_system.pipelines.document_processing.flows.tasks.vision_enriching_task import \
    markdown_vision_task
from .tasks import (
    duplicate_detection_task,
    docling_processing_task,
    vision_enriching_task,
    document_saving_task,
    kafka_message_preparation_task,
    weaviate_storage_task
)

# TODO : {'status': 'skipped', 'message': 'No embedded chunks available for storage'}?

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
    weaviate_collection: str = "advanced_docs"
) -> Dict[str, Any]:
    """
    Complete the document processing workflow with Prefect orchestration.

    This flow handles:
    1. Duplicate detection using content hash
    2. Docling extraction (markdown + images) if document is new
    3. Vision enhancement and chunking processing
    4. Structured document saving
    5. Kafka message preparation for downstream pipelines
    6. Optional Weaviate vector storage for RAG capabilities

    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        enable_weaviate_storage: Whether to store chunks in Weaviate for vector search
        weaviate_collection: Weaviate collection name for vector storage

    Returns:
        Dict containing complete processing results including optional Weaviate storage
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
        
        # Step 2: Docling extraction (extract markdown)
        document_id = duplicate_result["document_id"]
        logger.info(f"🔄 Step 2: Docling extraction for: {document_id}")
        docling_result = docling_processing_task(raw_file_path, document_id, user_id)
        
        if not docling_result or docling_result["status"] != "completed":
            logger.error(f"❌ Docling extraction failed, aborting flow")
            return docling_result or {"status": "error", "message": "Docling extraction returned None"}
        
        # Step 3: Vision enhancement and chunking (process extracted content)
        logger.info(f"🔄 Step 3: Vision enhancement: {document_id}")
        vision_result = await markdown_vision_task(
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
        # TODO : ADD CHUNK GENERATION AND  EMBEDDING GENERATION AND CHUNK OVERLAP REFINMENT before the saving.

        # Step 5: Kafka message preparation
        logger.info(f"🔄 Step 5: Preparing Kafka messages: {document_id}")
        kafka_result = kafka_message_preparation_task(save_result, user_id)

        # Validate Kafka message preparation
        if not kafka_result.get("kafka_message") or kafka_result.get("kafka_message", {}).get("status") != "processed":
            logger.error(f"❌ Kafka message preparation failed, aborting flow")
            return kafka_result

        # Step 6: Optional Weaviate vector storage
        weaviate_result = None
        if enable_weaviate_storage:
            logger.info(f"🔄 Step 6: Storing document chunks in Weaviate: {document_id}")

            # For now, we'll create dummy embedded chunks since we don't have the chunking/embedding pipeline
            # In a full implementation, this would come from a previous chunking/embedding step
            try:
                # This is a placeholder - in real implementation, embedded_chunks would come from
                # the chunking task or a separate embedding pipeline
                embedded_chunks = []  # Would contain actual Chunk objects with embeddings

                if embedded_chunks:  # Only proceed if we have embedded chunks
                    weaviate_result = weaviate_storage_task(
                        embedded_chunks=embedded_chunks,
                        document_id=document_id,
                        collection_name=weaviate_collection,
                        user_id=user_id
                    )

                    if weaviate_result.get("status") == "completed":
                        logger.info(f"✅ Weaviate storage completed: {weaviate_result.get('chunks_stored', 0)} chunks stored")
                    else:
                        logger.warning(f"⚠️ Weaviate storage failed: {weaviate_result.get('error', 'Unknown error')}")
                else:
                    logger.info("ℹ️ Skipping Weaviate storage: No embedded chunks available")
                    weaviate_result = {
                        "status": "skipped",
                        "message": "No embedded chunks available for storage"
                    }

            except Exception as e:
                logger.error(f"❌ Weaviate storage error: {e}")
                weaviate_result = {
                    "status": "error",
                    "error": str(e),
                    "message": f"Weaviate storage failed: {e}"
                }
        else:
            logger.info("ℹ️ Weaviate storage disabled, skipping vector storage step")
            weaviate_result = {
                "status": "disabled",
                "message": "Weaviate storage not enabled"
            }

        # Final success logging
        logger.info(f"✅ Document processing flow completed successfully!")
        logger.info(f"📄 Document ID: {kafka_result['document_id']}")
        logger.info(f"📁 Processed file: {kafka_result['processed_file_path']}")
        logger.info(f"📤 Kafka message prepared for downstream pipelines")
        if enable_weaviate_storage and weaviate_result.get("status") == "completed":
            logger.info(f"🗄️ Vector storage: {weaviate_result.get('chunks_stored', 0)} chunks in Weaviate")

        # Enhanced final result with all processing steps
        final_result = {
            "status": "completed",
            "document_id": kafka_result["document_id"],
            "processed_file_path": kafka_result["processed_file_path"],
            "document_directory": kafka_result["document_directory"],
            "kafka_message": kafka_result["kafka_message"],
            "content_length": kafka_result["content_length"],
            "page_count": kafka_result["page_count"],
            "processing_steps": {
                "duplicate_detection": duplicate_result.get("status"),
                "docling_extraction": docling_result.get("status"),
                "vision_enhancement": vision_result.get("status"),
                "document_saving": save_result.get("save_result", {}).get("status"),
                "kafka_preparation": kafka_result.get("kafka_message", {}).get("status"),
                "weaviate_storage": weaviate_result.get("status") if weaviate_result else "disabled"
            },
            "weaviate_storage": weaviate_result,
            "message": f"Document processing completed: {kafka_result['document_id']}"
        }

        return final_result
            
    except Exception as e:
        logger.error(f"❌ Document processing flow failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Document processing flow failed: {e}"
        }


# Convenience function for direct flow execution
async def process_document_with_flow(
    raw_file_path: str, 
    user_id: str = "default",
    enable_weaviate_storage: bool = False,
    weaviate_collection: str = "advanced_docs"
) -> Dict[str, Any]:
    """
    Convenience function to run the document processing flow directly.

    Args:
        raw_file_path: Path to the raw document file
        user_id: User who uploaded the document
        enable_weaviate_storage: Whether to store chunks in Weaviate for vector search
        weaviate_collection: Weaviate collection name for vector storage

    Returns:
        Dict containing processing results
    """
    return await document_processing_flow(
        raw_file_path, 
        user_id, 
        enable_weaviate_storage, 
        weaviate_collection
    )

if __name__ == "__main__":
    import asyncio
    test_file_path = "C:\\Users\\User\Projects\\scaled_processing\\data\documents\\raw\\Hamza_CV_Updated.pdf"  # Replace with an actual file path for testing
    result = asyncio.run(process_document_with_flow(test_file_path, user_id="test_user", enable_weaviate_storage=True))
    print(result)