from typing import Dict, Any, Optional
import json
from pathlib import Path

from ..base.base_consumer import BaseKafkaConsumer
from .document_producer import DocumentProducer


class DocumentProcessingConsumer(BaseKafkaConsumer):
    def __init__(self, group_id: str = "document_processing_group_v2"):
        super().__init__(group_id)
        self.document_producer = DocumentProducer()
        self._orchestrator = None
    
    def get_subscribed_topics(self) -> list:
        return ["file-detected"]
    
    def set_orchestrator(self, orchestrator):
        self._orchestrator = orchestrator
    
    def process_message(self, message_data: Dict[str, Any], topic: str, key: Optional[str] = None) -> bool:
        try:
            if topic == "file-detected":
                return self._handle_file_detected(message_data)
            else:
                self.logger.warning(f"Unhandled topic: {topic}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing message from {topic}: {e}")
            return False
    
    def _handle_file_detected(self, event_data: Dict[str, Any]) -> bool:
        try:
            file_path = event_data.get("file_path")
            filename = event_data.get("filename")
            
            if not file_path or not filename:
                self.logger.error("Missing file_path or filename in FILE_DETECTED event")
                return False
            
            self.logger.info(f"🔍 Processing file detected event: {filename}")
            
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            if self._orchestrator:
                result = self._orchestrator.process_document(
                    raw_file_path=file_path,
                    user_id="file_watcher"
                )
                
                if result.get("status") == "completed":
                    self.logger.info(f"✅ Document processing completed: {result.get('document_id')}")
                    return True
                else:
                    self.logger.error(f"❌ Document processing failed: {result.get('message')}")
                    return False
            else:
                self.logger.error("No orchestrator configured")
                return False
                
        except Exception as e:
            self.logger.error(f"Error handling FILE_DETECTED event: {e}")
            return False


def create_document_processing_consumer(orchestrator=None) -> DocumentProcessingConsumer:
    consumer = DocumentProcessingConsumer()
    if orchestrator:
        consumer.set_orchestrator(orchestrator)
    return consumer