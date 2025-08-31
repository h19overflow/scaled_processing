"""
Kafka consumer that triggers Prefect flows for document processing.
Listens to file-detected events from FileWatcherService and executes document processing workflows.
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..messaging.base.base_consumer import BaseKafkaConsumer
from ..messaging.document_processing.document_producer import DocumentProducer
from ..pipelines.document_processing.flows.document_processing_flow import document_processing_flow


class PrefectFlowConsumer(BaseKafkaConsumer):
    """
    Kafka consumer that triggers Prefect document processing flows.
    
    Consumes 'file-detected' events from FileWatcherService and executes
    the complete document processing workflow via Prefect orchestration.
    """
    
    def __init__(self):
        """Initialize the Prefect flow consumer."""
        super().__init__("prefect_flow_group")
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize document producer for publishing results
        self.document_producer = DocumentProducer()
        
        # Track processing files to avoid duplicates
        self.processing_files = set()
        
        self.logger.info("🚀 PrefectFlowConsumer initialized - ready to process file-detected events")
    
    def get_topic_handlers(self) -> Dict[str, callable]:
        """Define topic handlers for Kafka events."""
        return {
            "file-detected": self._handle_file_detected
        }
    
    async def _handle_file_detected(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle file-detected events by triggering Prefect document processing flows.
        
        Args:
            message_data: File detection event data from FileWatcherService
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        self.logger.info("📨 Received file-detected event")
        
        try:
            # Extract file information from event
            file_path = message_data.get("file_path")
            filename = message_data.get("filename")
            file_size = message_data.get("file_size")
            file_extension = message_data.get("file_extension")
            detected_at = message_data.get("detected_at")
            
            self.logger.info(f"📄 Processing file: {filename}")
            self.logger.info(f"📁 Path: {file_path}")
            self.logger.info(f"📊 Size: {file_size} bytes")
            self.logger.info(f"🕐 Detected: {detected_at}")
            
            # Validate file information
            if not file_path or not filename:
                self.logger.error("❌ Invalid file event: missing file_path or filename")
                return True  # Mark as processed to avoid retry
            
            # Check if file is already being processed
            if file_path in self.processing_files:
                self.logger.warning(f"⏳ File already being processed: {filename}")
                return True
            
            # Validate file still exists and size matches
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                self.logger.warning(f"⚠️ File no longer exists: {file_path}")
                return True  # Mark as processed since file is gone
            
            current_size = file_path_obj.stat().st_size
            if current_size != file_size:
                self.logger.warning(f"⚠️ File size changed ({file_size} → {current_size}): {filename}")
                return True  # Mark as processed to avoid processing incomplete file
            
            # Add to processing set
            self.processing_files.add(file_path)
            
            try:
                # Execute Prefect document processing flow
                self.logger.info(f"🚀 Starting Prefect flow for: {filename}")
                
                flow_result = await document_processing_flow(
                    raw_file_path=file_path,
                    user_id="file_watcher_user"
                )
                
                # Process flow result
                await self._process_flow_result(flow_result, filename, file_path)
                
                return True
                
            except Exception as e:
                self.logger.error(f"❌ Prefect flow execution failed for {filename}: {e}")
                return False
                
            finally:
                # Remove from processing set
                self.processing_files.discard(file_path)
                
        except Exception as e:
            self.logger.error(f"❌ Error handling file-detected event: {e}")
            return False
    
    async def _process_flow_result(self, flow_result: Dict[str, Any], filename: str, file_path: str) -> None:
        """
        Process the result of the Prefect flow and publish downstream events.
        
        Args:
            flow_result: Result from document processing flow
            filename: Original filename for logging
            file_path: Original file path
        """
        status = flow_result.get("status")
        document_id = flow_result.get("document_id")
        
        self.logger.info(f"📋 Flow completed with status: {status}")
        
        if status == "completed":
            # Successful processing - publish document-received event
            self.logger.info(f"✅ Document processing completed successfully: {document_id}")
            self.logger.info(f"📁 Processed file: {flow_result.get('processed_file_path')}")
            self.logger.info(f"📤 Publishing document-received events for downstream pipelines")
            
            # Publish event for downstream processing (RAG & Extraction pipelines)
            kafka_message = flow_result.get("kafka_message")
            if kafka_message:
                success = self.document_producer.send_document_received(kafka_message)
                if success:
                    self.logger.info(f"📨 document-received event published successfully for: {document_id}")
                else:
                    self.logger.error(f"❌ Failed to publish document-received event for: {document_id}")
            else:
                self.logger.error(f"❌ No Kafka message prepared for downstream processing: {document_id}")
                
        elif status == "duplicate":
            # Duplicate document - log and continue
            self.logger.info(f"📋 Document is duplicate: {document_id}")
            self.logger.info(f"⏭️ Skipping downstream processing for duplicate")
            
        elif status == "error":
            # Processing error - log details
            error_message = flow_result.get("message", "Unknown error")
            self.logger.error(f"❌ Document processing failed for {filename}: {error_message}")
            
        else:
            # Unexpected status
            self.logger.warning(f"⚠️ Unexpected flow status: {status} for {filename}")
    
    def start_consuming(self) -> None:
        """
        Start consuming file-detected events and processing them with Prefect flows.
        
        This method starts the Kafka consumer in a blocking manner.
        Use this in the main thread or a dedicated consumer thread.
        """
        self.logger.info("🎯 Starting PrefectFlowConsumer - listening for file-detected events")
        self.logger.info("📂 Monitoring topic: file-detected")
        self.logger.info("🏭 Ready to trigger Prefect document processing flows")
        
        try:
            # Start consuming messages
            super().start_consuming(topics=["file-detected"])
            
        except KeyboardInterrupt:
            self.logger.info("🛑 PrefectFlowConsumer stopped by user")
        except Exception as e:
            self.logger.error(f"❌ PrefectFlowConsumer error: {e}")
            raise
        finally:
            self.logger.info("🔚 PrefectFlowConsumer shutdown complete")
    
    def stop_consuming(self) -> None:
        """Stop the consumer gracefully."""
        self.logger.info("🛑 Stopping PrefectFlowConsumer...")
        super().stop_consuming()

    # HELPER FUNCTIONS
    def _validate_file_event(self, message_data: Dict[str, Any]) -> Optional[str]:
        """
        Validate file event data.
        
        Args:
            message_data: Event data to validate
            
        Returns:
            str: Error message if invalid, None if valid
        """
        required_fields = ["file_path", "filename", "file_size", "file_extension"]
        
        for field in required_fields:
            if field not in message_data or not message_data[field]:
                return f"Missing or empty required field: {field}"
        
        # Validate file extension
        supported_extensions = {'.pdf', '.docx', '.txt', '.md', '.doc'}
        file_extension = message_data["file_extension"].lower()
        if file_extension not in supported_extensions:
            return f"Unsupported file extension: {file_extension}"
        
        return None  # Valid
    
    def _log_processing_stats(self) -> None:
        """Log current processing statistics."""
        processing_count = len(self.processing_files)
        self.logger.info(f"📊 Currently processing {processing_count} files")
        
        if processing_count > 0:
            self.logger.debug(f"📝 Processing files: {list(self.processing_files)}")


# Service instance for easy import and standalone execution
prefect_flow_consumer = PrefectFlowConsumer()


def main():
    """Main function for standalone execution."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down PrefectFlowConsumer...")
        prefect_flow_consumer.stop_consuming()
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting PrefectFlowConsumer service...")
    print("📨 Listening for file-detected events from FileWatcherService")
    print("🏭 Will trigger Prefect document processing flows")
    print("Press Ctrl+C to stop")
    
    try:
        prefect_flow_consumer.start_consuming()
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()