"""
Simple document processor that handles file processing and Kafka events.
Does the actual work without unnecessary abstractions.
"""

import asyncio
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Set

from .kafka_handler import KafkaHandler
from ...pipelines.document_processing.flows.document_processing_flow import document_processing_flow
from ..file_ingestion.file_watcher import FileWatcherService



class DocumentProcessor:
    """Processes documents and handles messaging - simple and direct."""
    
    def __init__(self, watch_directory: str = None, num_consumers: int = 1):
        self.logger = self._setup_logging()
        self.num_consumers = num_consumers
        
        # Add deduplication tracking
        self._processing_documents: Set[str] = set()
        self._processing_lock = threading.Lock()
        self._consumer_threads = []
        self._shutdown_event = threading.Event()
        
        # EXPENSIVE STUFF - Build models once at startup (following your principle)
        self.logger.info("🔧 Loading ML models (this takes a moment)...")
        try:
            from ...pipelines.document_processing.chonkie_processor import ChonkieProcessor
            self._cached_processor = ChonkieProcessor()
            self.logger.info("✅ ML models loaded successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to load ML models: {e}")
            self._cached_processor = None
        
        # Create multiple consumer instances for scaling
        self.kafka_consumers = []
        for i in range(num_consumers):
            consumer_group = f"document_processing_consumer_{i+1}"
            kafka = KafkaHandler(consumer_group=consumer_group)
            self.kafka_consumers.append(kafka)
            
        self.file_watcher = FileWatcherService(watch_directory) if watch_directory else None
        
        # Subscribe to file events (only first consumer handles file events to avoid duplicates)
        if self.file_watcher and self.kafka_consumers:
            self.kafka_consumers[0].subscribe_to_file_events(self._handle_file_detected)
            
        self.logger.info(f"🚀 DocumentProcessor initialized with {num_consumers} consumer(s)")
    
    def process_document(self, file_path: str, user_id: str = "default") -> Dict[str, Any]:
        """Process a single document."""
        try:
            # Convert to absolute path to ensure DoclingProcessor can find the file
            from pathlib import Path
            absolute_file_path = str(Path(file_path).resolve())
            
            # Check for duplicate processing
            with self._processing_lock:
                if absolute_file_path in self._processing_documents:
                    self.logger.warning(f"🔄 Document already being processed, skipping: {Path(absolute_file_path).name}")
                    return {
                        "status": "duplicate_processing",
                        "message": f"Document already being processed: {Path(absolute_file_path).name}"
                    }
                
                # Add to processing set
                self._processing_documents.add(absolute_file_path)
            
            self.logger.info(f"🔄 Processing document: {absolute_file_path}")
            
            # Verify the file exists
            if not Path(absolute_file_path).exists():
                return {
                    "status": "error",
                    "error": "File not found",
                    "message": f"Cannot find file at path: {absolute_file_path}"
                }
            
            # Check if models loaded successfully
            if not self._cached_processor:
                return {
                    "status": "error", 
                    "error": "ML models not loaded",
                    "message": "Cannot process document - ML models failed to load at startup"
                }
            
            # Use the pre-loaded processor (super fast - no model loading!)
            result = asyncio.run(document_processing_flow(raw_file_path=absolute_file_path))
            
            # Send completion events if successful
            if result.get("status") == "completed":
                self._send_completion_events(result, absolute_file_path, user_id)
                self.logger.info(f"✅ Completed: {result.get('document_id')}")
            else:
                self.logger.error(f"❌ Failed: {result.get('message')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed for {file_path}: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            # Clean up processing set with delay to prevent immediate re-processing
            if 'absolute_file_path' in locals():
                def cleanup():
                    with self._processing_lock:
                        self._processing_documents.discard(absolute_file_path)
                
                threading.Timer(60.0, cleanup).start()  # 60 second delay
    
    def start_service(self):
        """Start the full service with file watching and multiple consumers."""
        try:
            self.logger.info(f"🚀 Starting document processing service with {self.num_consumers} consumer(s)...")
            
            if self.file_watcher:
                self.file_watcher.start()
                self.logger.info("📂 File watcher started")
            
            # Start each Kafka consumer in a separate thread
            for i, kafka_consumer in enumerate(self.kafka_consumers):
                consumer_thread = threading.Thread(
                    target=self._run_consumer,
                    args=(kafka_consumer, i+1),
                    name=f"KafkaConsumer-{i+1}",
                    daemon=True
                )
                consumer_thread.start()
                self._consumer_threads.append(consumer_thread)
                self.logger.info(f"📨 Kafka consumer {i+1} started in thread")
            
            self.logger.info(f"✅ Service ready with {len(self._consumer_threads)} consumer threads")
            
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            self.stop_service()
            raise
    
    def stop_service(self):
        """Stop all services."""
        try:
            self.logger.info("🛑 Stopping service...")
            
            # Signal shutdown
            self._shutdown_event.set()
            
            if self.file_watcher:
                self.file_watcher.stop()
            
            # Stop all Kafka consumers
            for i, kafka_consumer in enumerate(self.kafka_consumers):
                try:
                    kafka_consumer.stop_consuming()
                    self.logger.info(f"📨 Kafka consumer {i+1} stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping consumer {i+1}: {e}")
            
            # Wait for consumer threads to finish (with timeout)
            for thread in self._consumer_threads:
                thread.join(timeout=5.0)
            
            self.logger.info("✅ All services stopped")
            
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
            
            # Use the first Kafka consumer for sending events to avoid duplicates
            kafka_sender = self.kafka_consumers[0] if self.kafka_consumers else None
            if not kafka_sender:
                return
                
            # Document ready event
            if steps.get("duplicate_detection") == "ready_for_processing":
                kafka_sender.send_document_ready(document_id, file_path, user_id)
            
            # Workflow initialized
            if steps.get("docling_extraction") == "completed":
                kafka_sender.send_workflow_ready(document_id, ["rag", "extraction"])
            
            # Chunking complete
            chunking = result.get("chunking_result", {})
            if chunking.get("status") == "completed":
                kafka_sender.send_chunking_complete(chunking)
            
            # Storage complete
            storage = result.get("weaviate_storage", {})
            if storage.get("status") == "completed":
                kafka_sender.send_storage_complete(storage, document_id)
                
        except Exception as e:
            self.logger.error(f"Error sending events: {e}")
    
    def _run_consumer(self, kafka_consumer: KafkaHandler, consumer_id: int):
        """Run a Kafka consumer in a separate thread."""
        try:
            self.logger.info(f"🔄 Consumer {consumer_id} starting...")
            kafka_consumer.start_consuming()
            
            # Keep running until shutdown
            while not self._shutdown_event.is_set():
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Consumer {consumer_id} error: {e}")
        finally:
            self.logger.info(f"🛑 Consumer {consumer_id} stopped")
    
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
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Document Processing Service')
    parser.add_argument('--num-consumers', type=int, default=None, 
                       help='Number of consumer threads (default: from env DOC_PROCESSING_CONSUMERS or 1)')
    parser.add_argument('--watch-directory', type=str, default='data/documents/raw',
                       help='Directory to watch for files (default: data/documents/raw)')
    
    args = parser.parse_args()
    
    # Get number of consumers
    if args.num_consumers:
        num_consumers = args.num_consumers
    else:
        # Check environment variable
        num_consumers = int(os.getenv('DOC_PROCESSING_CONSUMERS', 1))
    
    print(f"🚀 Starting DocumentProcessor with {num_consumers} consumer(s)")
    print(f"📂 Watching directory: {args.watch_directory}")
    
    processor = DocumentProcessor(args.watch_directory, num_consumers)
    processor.run_forever()


if __name__ == "__main__":
    main()