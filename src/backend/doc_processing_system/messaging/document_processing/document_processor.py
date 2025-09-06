"""
Simple document processor that handles file processing and Kafka events.
Does the actual work without unnecessary abstractions.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any

from .kafka_handler import KafkaHandler
from ...pipelines.document_processing.flows.document_processing_flow import document_processing_flow
from ..file_ingestion.file_watcher import FileWatcherService


# TODO  | INFO    | Task run 'docling-processing-a3d' - 📄 Starting Docling processing for document: Covering Letter - AHMED HAMZA KHALED MAHMOUD
# 17:50:06.868 | ERROR   | src.backend.doc_processing_system.pipelines.document_processing.utils.docling_processor - ❌ Docling extraction failed: [WinError 3] The system cannot find the path specified: 'data\\temp\\docling\\Covering Letter - AHMED HAMZA KHALED MAHMOUD \\images'
# 17:50:06.868 | ERROR   | Task run 'docling-processing-a3d' - ❌ Docling processing failed for Covering Letter - AHMED HAMZA KHALED MAHMOUD : Extraction failed
# 17:50:06.870 | INFO    | Task run 'docling-processing-a3d' - Finished in state Completed()
# 17:50:07.140 | INFO    | Flow run 'bald-wolverine' - Finished in state Completed()
# 2025-09-06 17:50:07,141 - __main__ - ERROR - ❌ Failed: Docling processing failed: Extraction failed
# 17:50:07.141 | ERROR   | __main__ - ❌ Failed: Docling processing failed: Extraction failed

class DocumentProcessor:
    """Processes documents and handles messaging - simple and direct."""
    
    def __init__(self, watch_directory: str = None):
        self.logger = self._setup_logging()
        
        # EXPENSIVE STUFF - Build models once at startup (following your principle)
        self.logger.info("🔧 Loading ML models (this takes a moment)...")
        try:
            from ...pipelines.document_processing.chonkie_processor import ChonkieProcessor
            self._cached_processor = ChonkieProcessor()
            self.logger.info("✅ ML models loaded successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to load ML models: {e}")
            self._cached_processor = None
        
        self.kafka = KafkaHandler()
        self.file_watcher = FileWatcherService(watch_directory) if watch_directory else None
        
        # Subscribe to file events
        if self.file_watcher:
            self.kafka.subscribe_to_file_events(self._handle_file_detected)
    
    def process_document(self, file_path: str, user_id: str = "default") -> Dict[str, Any]:
        """Process a single document."""
        try:
            self.logger.info(f"🔄 Processing document: {file_path}")
            
            # Check if models loaded successfully
            if not self._cached_processor:
                return {
                    "status": "error", 
                    "error": "ML models not loaded",
                    "message": "Cannot process document - ML models failed to load at startup"
                }
            
            # Use the pre-loaded processor (super fast - no model loading!)
            result = asyncio.run(document_processing_flow(raw_file_path=file_path))
            
            # Send completion events if successful
            if result.get("status") == "completed":
                self._send_completion_events(result, file_path, user_id)
                self.logger.info(f"✅ Completed: {result.get('document_id')}")
            else:
                self.logger.error(f"❌ Failed: {result.get('message')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed for {file_path}: {e}")
            return {"status": "error", "error": str(e)}
    
    def start_service(self):
        """Start the full service with file watching."""
        try:
            self.logger.info("🚀 Starting document processing service...")
            
            if self.file_watcher:
                self.file_watcher.start()
                self.logger.info("📂 File watcher started")
            
            self.kafka.start_consuming()
            self.logger.info("📨 Kafka consumer started")
            
            self.logger.info("✅ Service ready")
            
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            self.stop_service()
            raise
    
    def stop_service(self):
        """Stop all services."""
        try:
            self.logger.info("🛑 Stopping service...")
            
            if self.file_watcher:
                self.file_watcher.stop()
            
            self.kafka.stop_consuming()
            self.logger.info("✅ Stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping: {e}")
    
    def run_forever(self):
        """Run the service until interrupted."""
        try:
            self.start_service()
            self.logger.info("🔄 Running... Press Ctrl+C to stop")
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("👋 Interrupted")
        finally:
            self.stop_service()
    
    def _handle_file_detected(self, event_data: Dict[str, Any]) -> bool:
        """Handle file detected events from Kafka."""
        try:
            file_path = event_data.get("file_path")
            if not file_path:
                self.logger.error("No file_path in event")
                return False
            
            result = self.process_document(file_path, "file_watcher")
            return result.get("status") == "completed"
            
        except Exception as e:
            self.logger.error(f"Error handling file event: {e}")
            return False
    
    def _send_completion_events(self, result: Dict[str, Any], file_path: str, user_id: str):
        """Send events when processing completes."""
        try:
            document_id = result.get("document_id")
            steps = result.get("processing_steps", {})
            
            # Document ready event
            if steps.get("duplicate_detection") == "ready_for_processing":
                self.kafka.send_document_ready(document_id, file_path, user_id)
            
            # Workflow initialized
            if steps.get("docling_extraction") == "completed":
                self.kafka.send_workflow_ready(document_id, ["rag", "extraction"])
            
            # Chunking complete
            chunking = result.get("chunking_result", {})
            if chunking.get("status") == "completed":
                self.kafka.send_chunking_complete(chunking)
            
            # Storage complete
            storage = result.get("weaviate_storage", {})
            if storage.get("status") == "completed":
                self.kafka.send_storage_complete(storage, document_id)
                
        except Exception as e:
            self.logger.error(f"Error sending events: {e}")
    
    # HELPER FUNCTIONS
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the processor."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


def main():
    """Run the document processor service."""
    processor = DocumentProcessor('data/documents/raw')
    processor.run_forever()


if __name__ == "__main__":
    main()