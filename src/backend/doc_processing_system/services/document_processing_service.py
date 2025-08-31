"""
Document Processing Service Runner
Coordinates file system watcher and message consumers for automated document processing.
"""

import asyncio
import signal
import logging
import threading
from typing import Optional
from pathlib import Path

from ..services.file_watcher import FileWatcherService
from ..messaging.file_ingestion.file_processing_consumer import FileProcessingConsumer
from ..config.settings import get_settings


class DocumentProcessingService:
    """
    Main service that coordinates file watching and document processing.
    Runs file watcher and consumer in parallel for automated document processing.
    """
    
    def __init__(self, watch_directory: Optional[str] = None):
        """
        Initialize document processing service.
        
        Args:
            watch_directory: Directory to watch for new files
        """
        self.logger = self._setup_logging()
        self.settings = get_settings()
        
        # Initialize components
        self.file_watcher = FileWatcherService(watch_directory)
        self.file_consumer = FileProcessingConsumer()
        
        # Control flags
        self.running = False
        self.consumer_thread = None
        
        self.logger.info("Document processing service initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the service."""
        logger = logging.getLogger("DocumentProcessingService")
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
        """Start the document processing service."""
        try:
            self.logger.info("Starting document processing service...")
            self.running = True
            
            # Start file watcher
            self.logger.info("Starting file system watcher...")
            self.file_watcher.start()
            
            # Start consumer in background thread
            self.logger.info("Starting file processing consumer...")
            self.consumer_thread = threading.Thread(
                target=self._run_consumer,
                daemon=True
            )
            self.consumer_thread.start()
            
            self.logger.info("🚀 Document processing service started successfully!")
            self.logger.info(f"📁 Watching directory: {self.file_watcher.watch_directory}")
            self.logger.info("📨 Consuming file-detected events from Kafka")
            
        except Exception as e:
            self.logger.error(f"Failed to start document processing service: {e}")
            self.stop()
            raise
    
    def _run_consumer(self):
        """Run the file processing consumer in a background thread."""
        try:
            self.file_consumer.start_consuming()
            
            # Keep consuming while service is running
            while self.running:
                try:
                    # Process messages
                    messages = self.file_consumer.consume_events()
                    if messages:
                        self.logger.debug(f"Processed {len(messages)} file detection events")
                    
                    # Small sleep to prevent tight loop
                    threading.Event().wait(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error in consumer loop: {e}")
                    if self.running:
                        # Wait before retrying
                        threading.Event().wait(5)
                        
        except Exception as e:
            self.logger.error(f"Consumer thread failed: {e}")
        finally:
            self.logger.info("Consumer thread stopped")
    
    def stop(self):
        """Stop the document processing service."""
        try:
            self.logger.info("Stopping document processing service...")
            self.running = False
            
            # Stop file watcher
            if self.file_watcher.is_running():
                self.logger.info("Stopping file watcher...")
                self.file_watcher.stop()
            
            # Stop consumer
            self.logger.info("Stopping file consumer...")
            self.file_consumer.stop_consuming()
            
            # Wait for consumer thread to finish
            if self.consumer_thread and self.consumer_thread.is_alive():
                self.logger.info("Waiting for consumer thread to finish...")
                self.consumer_thread.join(timeout=5)
            
            self.logger.info("✅ Document processing service stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
    
    def is_running(self) -> bool:
        """Check if the service is running."""
        return (
            self.running and 
            self.file_watcher.is_running() and 
            self.consumer_thread and 
            self.consumer_thread.is_alive()
        )
    
    def get_status(self) -> dict:
        """Get service status information."""
        return {
            "service_running": self.running,
            "file_watcher_running": self.file_watcher.is_running(),
            "consumer_thread_alive": self.consumer_thread.is_alive() if self.consumer_thread else False,
            "watch_directory": str(self.file_watcher.watch_directory),
            "supported_extensions": list(self.file_watcher.event_handler.supported_extensions)
        }


def main():
    """Main entry point for running the document processing service."""
    print("🚀 Starting Document Processing Service...")
    
    # Setup signal handlers for graceful shutdown
    service = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print(f"\n📡 Received signal {signum}, shutting down...")
        if service:
            service.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and start service
        service = DocumentProcessingService()
        service.start()
        
        # Keep main thread alive
        print("✅ Service running. Press Ctrl+C to stop.")
        while service.is_running():
            try:
                # Print status periodically
                status = service.get_status()
                service.logger.debug(f"Service status: {status}")
                
                # Sleep for a bit
                threading.Event().wait(30)  # Status check every 30 seconds
                
            except KeyboardInterrupt:
                print("\n⏹️  Keyboard interrupt received")
                break
    
    except Exception as e:
        print(f"💥 Service failed: {e}")
        return 1
    
    finally:
        if service:
            service.stop()
    
    print("👋 Document processing service shutdown complete")
    return 0


if __name__ == "__main__":
    exit(main())