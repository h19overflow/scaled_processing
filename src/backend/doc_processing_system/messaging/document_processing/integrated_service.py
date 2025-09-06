import time
import logging
from pathlib import Path

from .document_flow_orchestrator import DocumentFlowOrchestrator
from .document_processing_consumer import create_document_processing_consumer
from ..file_ingestion.file_watcher import FileWatcherService

# TODO FIX nomic-ai/nomic-bert-2048 You can inspect the repository content at https://hf.co/nomic-ai/nomic-embed-text-v1.5. Please pass the argument `trust_remote_code=True` to allow custom code to be run.
#9-06 11:01:48,297 - __main__ - INFO - 🔄 Service running... Press Ctrl+C to stop
# 11:01:48.297 | INFO    | __main__ - 🔄 Service running... Press Ctrl+C to stop
# 2025-09-06 11:02:19,549 - DocumentProducer - INFO - Published to file-detected:2:37
# 11:02:19.549 | INFO    | DocumentProducer - Published to file-detected:2:37
# 2025-09-06 11:02:19,550 - DocumentProducer - INFO - File detected event sent: C:\Users\User\Projects\scaled_processing\data\documents\raw\Monthly-Report-Aug.docx
# 11:02:19.550 | INFO    | DocumentProducer - File detected event sent: C:\Users\User\Projects\scaled_processing\data\documents\raw\Monthly-Report-Aug.docx
#  TODO the pipeline stops here for some reason, i need to study more about kafka and prefct and the overall system design.

class IntegratedDocumentProcessingService:
    def __init__(self, watch_directory: str = None):
        self.logger = self._setup_logging()
        
        self.orchestrator = DocumentFlowOrchestrator()
        self.consumer = create_document_processing_consumer(self.orchestrator)
        self.file_watcher = FileWatcherService(watch_directory)
        
        self.logger.info("Integrated document processing service initialized")
    
    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def start(self):
        try:
            self.logger.info("🚀 Starting integrated document processing service...")
            
            self.file_watcher.start()
            self.logger.info("📂 File watcher started")
            
            self.consumer.start_consuming()
            self.logger.info("📨 Document processing consumer started")
            
            self.logger.info("✅ All services started successfully")
            self.logger.info(f"📁 Watching directory: {self.file_watcher.watch_directory}")
            self.logger.info("🎯 Ready to process documents!")
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            self.stop()
            raise
    
    def stop(self):
        try:
            self.logger.info("🛑 Stopping integrated document processing service...")
            
            if hasattr(self, 'consumer'):
                self.consumer.stop_consuming()
                self.logger.info("📨 Document processing consumer stopped")
            
            if hasattr(self, 'file_watcher'):
                self.file_watcher.stop()
                self.logger.info("📂 File watcher stopped")
            
            self.logger.info("✅ All services stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
    
    def is_running(self) -> bool:
        return (
            self.file_watcher.is_running() and 
            self.consumer.is_consuming()
        )
    
    def run_forever(self):
        try:
            self.start()
            
            self.logger.info("🔄 Service running... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("👋 Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Service error: {e}")
        finally:
            self.stop()


def main():
    service = IntegratedDocumentProcessingService()
    service.run_forever()


if __name__ == "__main__":
    main()