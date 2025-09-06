import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .document_producer import DocumentProducer
from ...pipelines.document_processing.flows.document_processing_flow import document_processing_flow


class DocumentFlowOrchestrator:
    def __init__(self, producer: Optional[DocumentProducer] = None):
        self._producer = producer or DocumentProducer()
        self.logger = self._producer.logger
    
    def process_document(
        self,
        raw_file_path: str,
        user_id: str = "default",
        enable_weaviate_storage: bool = True,
        weaviate_collection: str = "rag_documents"
    ) -> Dict[str, Any]:
        try:
            result = asyncio.run(self._process_document_async(
                raw_file_path, user_id, enable_weaviate_storage, weaviate_collection
            ))
            return result
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "message": f"Document processing orchestration failed: {e}"
            }
            self.logger.error(f"Orchestrator error: {e}")
            return error_result
    
    async def _process_document_async(
        self,
        raw_file_path: str,
        user_id: str,
        enable_weaviate_storage: bool,
        weaviate_collection: str
    ) -> Dict[str, Any]:
        self.logger.info(f"🎼 Starting document processing orchestration for: {raw_file_path}")
        
        try:
            result = await document_processing_flow(
                raw_file_path=raw_file_path,
                user_id=user_id,
                enable_weaviate_storage=enable_weaviate_storage,
                weaviate_collection=weaviate_collection
            )
            
            await self._publish_completion_events(result, raw_file_path, user_id)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Document processing flow failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Document processing flow failed: {e}"
            }
    
    async def _publish_completion_events(self, result: Dict[str, Any], raw_file_path: str, user_id: str):
        if result.get("status") != "completed":
            return
        
        try:
            document_id = result.get("document_id")
            processing_steps = result.get("processing_steps", {})
            
            if processing_steps.get("duplicate_detection") == "ready_for_processing":
                self._producer.send_document_available({
                    "document_id": document_id,
                    "status": "ready_for_processing",
                    "file_path": raw_file_path,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                })
            
            if processing_steps.get("docling_extraction") == "completed":
                self._producer.send_workflow_initialized(
                    document_id=document_id,
                    workflow_types=["rag", "extraction"],
                    status="initialized"
                )
            
            chunking_result = result.get("chunking_result", {})
            if chunking_result.get("status") == "completed":
                self._publish_chunking_events(chunking_result)
            
            weaviate_result = result.get("weaviate_storage", {})
            if weaviate_result.get("status") == "completed":
                self._publish_ingestion_complete_event(weaviate_result, document_id)
            
        except Exception as e:
            self.logger.error(f"Error publishing completion events: {e}")
    
    def _publish_chunking_events(self, chunking_result: Dict[str, Any]):
        document_id = chunking_result.get("document_id")
        chunk_count = chunking_result.get("chunk_count", 0)
        embedded_chunks = chunking_result.get("embedded_chunks", [])
        
        chunking_event = {
            "document_id": document_id,
            "chunk_count": chunk_count,
            "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
            "chunking_strategy": "chonkie_two_stage_semantic_boundary",
            "chunking_params": chunking_result.get("chunking_params", {}),
            "timestamp": datetime.now().isoformat(),
            "event_type": "chunking_complete"
        }
        
        success = self._producer.publish_event(
            topic="chunking-complete",
            event_data=chunking_event,
            key=document_id
        )
        
        if success and embedded_chunks:
            embedding_event = {
                "document_id": document_id,
                "embedded_chunks_count": len(embedded_chunks),
                "embedding_dimensions": 768,
                "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
                "timestamp": datetime.now().isoformat(),
                "event_type": "embedding_ready"
            }
            
            self._producer.publish_event(
                topic="embedding-ready",
                event_data=embedding_event,
                key=document_id
            )
    
    def _publish_ingestion_complete_event(self, weaviate_result: Dict[str, Any], document_id: str):
        ingestion_event = {
            "document_id": document_id,
            "collection_name": weaviate_result.get("collection_name", "rag_documents"),
            "chunks_stored": weaviate_result.get("chunks_stored", 0),
            "weaviate_url": weaviate_result.get("weaviate_url", "http://localhost:8080"),
            "storage_timestamp": datetime.now().isoformat(),
            "event_type": "ingestion_complete"
        }
        
        self._producer.publish_event(
            topic="ingestion-complete",
            event_data=ingestion_event,
            key=document_id
        )