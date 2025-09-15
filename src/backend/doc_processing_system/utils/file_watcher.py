import os
import logging
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..messaging import ProducerHandler, create_message

class FileDetectionHandler(FileSystemEventHandler):
    def __init__(self, producer: ProducerHandler):
        self.producer = producer
        self.logger = logging.getLogger(__name__)
        
    def on_created(self, event):
        if event.is_directory:
            return

        # Normalize path to use consistent separators
        raw_path = event.src_path
        file_path = str(Path(raw_path).resolve())  # This converts to OS-appropriate format
        self.logger.info(f"File detected (raw): {raw_path}")
        self.logger.info(f"File detected (normalized): {file_path}")

        try:
            # Get file metadata
            stat = os.stat(file_path)
            metadata = {
                "file_path": file_path,  # Use normalized path
                "file_name": os.path.basename(file_path),
                "file_size": stat.st_size,
                "file_extension": Path(file_path).suffix.lower(),
                "created_time": stat.st_ctime
            }
            
            # Create and send message
            message = create_message("file_detected", metadata, "file_watcher")
            success = self.producer.produce_message("file_detected", metadata["file_name"], message)
            
            if success:
                self.logger.info(f"Message sent for file: {metadata['file_name']}")
            else:
                self.logger.error(f"Failed to send message for file: {metadata['file_name']}")
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")

class FileWatcher:
    def __init__(self, watch_directory: str, broker: str = "localhost:9092"):
        self.watch_directory = watch_directory
        self.broker = broker
        self.observer = None
        self.producer = None
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
    def start(self):
        """Start watching for files."""
        # Validate watch directory
        if not os.path.exists(self.watch_directory):
            raise ValueError(f"Watch directory does not exist: {self.watch_directory}")
            
        # Initialize producer
        try:
            self.producer = ProducerHandler(self.broker)
            self.logger.info(f"Producer connected to {self.broker}")
        except Exception as e:
            self.logger.error(f"Failed to connect producer: {e}")
            raise
            
        # Setup file watcher
        event_handler = FileDetectionHandler(self.producer)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.watch_directory, recursive=True)
        
        self.observer.start()
        self.logger.info(f"File watcher started on directory: {self.watch_directory}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("File watcher stopped")
            
        if self.producer:
            self.producer.close()
            self.logger.info("Producer closed")

def main():
    watcher = FileWatcher("C:/Users/User/Projects/scaled_processing/data/documents/raw")
    watcher.start()

if __name__ == "__main__":
    main()