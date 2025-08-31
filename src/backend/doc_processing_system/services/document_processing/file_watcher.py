"""
File system watcher service for monitoring document uploads.
Watches the raw documents directory and publishes file detection events.
"""

import logging
import asyncio
from pathlib import Path
from typing import Set
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from ...messaging.document_processing.document_producer import DocumentProducer
from ...config.settings import get_settings


class DocumentFileHandler(FileSystemEventHandler):
    """Handler for document file system events."""
    
    def __init__(self, document_producer: DocumentProducer):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.document_producer = document_producer
        self.processing_files: Set[str] = set()  # Prevent duplicate processing
        
        # Supported file extensions
        self.supported_extensions = {'.pdf', '.docx', '.txt', '.md', '.doc'}
        
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._handle_file_event(event.src_path, "created")
    
    def on_modified(self, event):
        """Handle file modification events (for copy operations)."""
        if not event.is_directory:
            self._handle_file_event(event.src_path, "modified")
    
    def _handle_file_event(self, file_path: str, event_type: str):
        """Process file system events for document files."""
        try:
            file_path = Path(file_path).resolve()
            
            # Check if file extension is supported
            if file_path.suffix.lower() not in self.supported_extensions:
                self.logger.debug(f"Ignoring unsupported file type: {file_path}")
                return
            
            # Prevent duplicate processing of the same file
            file_key = str(file_path)
            if file_key in self.processing_files:
                self.logger.debug(f"File already being processed: {file_path}")
                return
            
            # Check if file exists and is complete (not being written)
            if not file_path.exists():
                self.logger.debug(f"File does not exist: {file_path}")
                return
            
            # Add to processing set
            self.processing_files.add(file_key)
            
            self.logger.info(f"File {event_type}: {file_path}")
            
            # Publish file detection event
            self._publish_file_detected(file_path)
            
        except Exception as e:
            self.logger.error(f"Error handling file event for {file_path}: {e}")
        finally:
            # Remove from processing set after a delay (using threading instead of asyncio)
            if 'file_key' in locals():
                import threading
                def delayed_cleanup():
                    import time
                    time.sleep(5)  # 5 second delay
                    self.processing_files.discard(file_key)
                
                cleanup_thread = threading.Thread(target=delayed_cleanup)
                cleanup_thread.daemon = True
                cleanup_thread.start()
    
    def _publish_file_detected(self, file_path: Path):
        """Publish file detection event to Kafka."""
        try:
            file_stats = file_path.stat()
            
            event_data = {
                "file_path": str(file_path),
                "filename": file_path.name,
                "file_size": file_stats.st_size,
                "file_extension": file_path.suffix.lower(),
                "detected_at": datetime.now().isoformat(),
                "event_type": "file_detected"
            }
            
            # Use the existing document producer to send the event
            self.document_producer.send_file_detected(event_data)
            self.logger.info(f"Published file detection event for: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish file detection event: {e}")
    


class FileWatcherService:
    """Service for monitoring document file changes."""
    
    def __init__(self, watch_directory: str = None):
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        # Default to raw documents directory
        if watch_directory:
            self.watch_directory = Path(watch_directory)
        else:
            self.watch_directory = Path("data") / "documents" / "raw"
        self.watch_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.document_producer = DocumentProducer()
        self.event_handler = DocumentFileHandler(self.document_producer)
        self.observer = Observer()
        
        self.logger.info(f"File watcher initialized for directory: {self.watch_directory}")
    
    def start(self):
        """Start the file watcher service."""
        try:
            self.observer.schedule(
                self.event_handler,
                str(self.watch_directory),
                recursive=True
            )
            self.observer.start()
            self.logger.info(f"File watcher started, monitoring: {self.watch_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}")
            raise
    
    def stop(self):
        """Stop the file watcher service."""
        try:
            self.observer.stop()
            self.observer.join()
            self.logger.info("File watcher stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping file watcher: {e}")
    
    def is_running(self) -> bool:
        """Check if the file watcher is running."""
        return self.observer.is_alive()


# Service instance for easy import
file_watcher_service = FileWatcherService()