from pathlib import Path
from typing import Dict, Any

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from .tasks import (
    duplicate_detection_task,
    docling_processing_task,
    document_saving_task,
    chonkie_chunking_task,
    weaviate_storage_task
)
from .tasks.vision_enriching_task import markdown_vision_task
# TODO 30:14.712 | INFO    | Task run 'duplicate-detection-5ec' - 🔍 Starting duplicate detection for: Monthly-Report-Aug.docx
# 2025-09-11 21:30:14,723 - src.backend.doc_processing_system.core_deps.database.connection_manager - INFO - Connection manager initialized with database: postgresql://postgres:***@localhost:5444/document_processing
# 21:30:14.723 | INFO    | src.backend.doc_processing_system.core_deps.database.connection_manager - Connection manager initialized with database: postgresql://postgres:***@localhost:5444/document_processing
# 2025-09-11 21:30:14 - src.backend.doc_processing_system.pipelines.document_processing.chonkie_processor.ChonkieProcessor - INFO - [ChonkieProcessor] Initializing embeddings with model: BAAI/bge-small-en-v1.5
# 2025-09-11 21:30:14 - src.backend.doc_processing_system.pipelines.document_processing.chonkie_processor.ChonkieProcessor - INFO - [ChonkieProcessor] Using SentenceTransformer embeddings
# 21:30:28.341 | INFO    | Task run 'duplicate-detection-5ec' - ✅ Successfully loaded embedding model: BAAI/bge-small-en-v1.5
# 2025-09-11 21:30:28,342 - INFO - ✅ Semantic chunker initialized (threshold=0.75, min_size=500)
# 21:30:28.342 | INFO    | src.backend.doc_processing_system.pipelines.document_processing.two_stage_chunking.components.chunking.semantic_chunker - ✅ Semantic chunker initialized (threshold=0.75, min_size=500)
# C:\Users\User\Projects\scaled_processing\.venv\Lib\site-packages\pydantic\json_schema.py:2324: PydanticJsonSchemaWarning: Default value typing.Literal['MERGE', 'KEEP'] is not JSON serializable; excluding default from JSON schema [non-serializable-default]
#   warnings.warn(message, PydanticJsonSchemaWarning)
# 2025-09-11 21:30:28,595 - INFO - 🤖 Boundary review agent initialized (context_window=200, model=gemini-2.0-flash)
# 21:30:28.595 | INFO    | src.backend.doc_processing_system.pipelines.document_processing.two_stage_chunking.components.chunking.boundary_agent - 🤖 Boundary review agent initialized (context_window=200, model=gemini-2.0-flash)
# 2025-09-11 21:30:28,595 - INFO - 🚀 2-Stage Chunker initialized (chunk_size=700, threshold=0.75, concurrent_agents=10, model=gemini-2.0-flash)
# 21:30:28.595 | INFO    | src.backend.doc_processing_system.pipelines.document_processing.two_stage_chunking.components.chunking.two_stage_chunker - 🚀 2-Stage Chunker initialized (chunk_size=700, threshold=0.75, concurrent_agents=10, model=gemini-2.0-flash)
# 2025-09-11 21:30:35 - src.backend.doc_processing_system.pipelines.document_processing.chonkie_processor.ChonkieProcessor - INFO - [ChonkieProcessor] ChonkieProcessor initialized - complete DoclingProcessor replacement
# 2025-09-11 21:30:35 - src.backend.doc_processing_system.pipelines.document_processing.chonkie_processor.ChonkieProcessor - INFO - [ChonkieProcessor] Configuration: embedding_model=BAAI/bge-small-en-v1.5, collection=rag_documents
# 21:30:35.985 | ERROR   | src.backend.doc_processing_system.core_deps.database.CRUD.base_repository - Failed to check duplicate for file C:\Users\Use\Projects\scaled_processing\data\documents\raw\Monthly-Report-Aug.docx: File not found: C:\Users\Use\Projects\scaled_processing\data\documents\raw\Monthly-Report-Aug.docx
# 21:30:35.986 | ERROR   | Task run 'duplicate-detection-5ec' - ❌ Duplicate detection failed: File not found: C:\Users\Use\Projects\scaled_processing\data\documents\raw\Monthly-Report-Aug.docx
# 21:30:35.987 | INFO    | Task run 'duplicate-detection-5ec' - Finished in state Completed()
# 21:30:36.254 | INFO    | Flow run 'auspicious-chihuahua' - Finished in state Completed()
# {'status': 'error', 'error': 'File not found: C:\\Users\\Use\\Projects\\scaled_processing\\data\\documents\\raw\\Monthly-Report-Aug.docx', 'message': 'Duplicate detection failed: File not found: C:\\Users\\Use\\Projects\\scaled_processing\\data\\documents\\raw\\Monthly-Report-Aug.docx'}
# C:\Users\User\Projects\scaled_processing\.venv\Lib\site-packages\weaviate\warnings.py:302: ResourceWarning: Con004: The connection to Weaviate was not closed properly. This can lead to memory leaks.
#             Please make sure to close the connection using `client.close()`.
#   warnings.warn(
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
                "vision_enhancement": vision_result.get("status"),
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
    test_file_path = "C:\\Users\\Use\\Projects\\scaled_processing\\data\\documents\\raw\\Monthly-Report-Aug.docx"
    result = asyncio.run(process_document_with_flow(test_file_path, user_id="test_user", enable_weaviate_storage=True))
    print(result)